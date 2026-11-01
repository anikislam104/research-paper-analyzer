from typing import Callable

from . import llm
from .sections import find, split_sections

Progress = Callable[[str], None]

MODES = {
    "summary": "Summarize",
    "sections": "Section-by-section summary",
    "oneline": "One-line summary",
    "diagram": "Methodology diagram",
    "slides": "Presentation slides",
    "scope": "Problem scope and contribution",
    "results": "Key results",
    "dataset": "Dataset info",
    "limitations": "Limitations",
}


def _section_summaries(paper: dict, progress: Progress) -> list[dict]:
    sections = split_sections(paper["text"])
    items = []
    for i, s in enumerate(sections, 1):
        progress(f"Summarizing section {i}/{len(sections)}: {s['title']}")
        items.append({"section": s["title"], "summary": llm.summarize_text(s["text"])})
    return items


def summary(paper: dict, progress: Progress) -> dict:
    items = _section_summaries(paper, progress)
    progress("Writing overall summary")
    notes = "\n".join(f"{i['section']}: {i['summary']}" for i in items)
    text = llm.chat(
        "Using these section summaries of a research paper, write a coherent summary of the whole paper "
        "in Markdown: a short overview paragraph, then bullets for problem, approach, and findings.\n\n" + llm.clip(notes, 9000)
    )
    return {"type": "markdown", "content": text}


def sections(paper: dict, progress: Progress) -> dict:
    return {"type": "sections", "items": _section_summaries(paper, progress)}


def oneline(paper: dict, progress: Progress) -> dict:
    secs = split_sections(paper["text"])
    source = find(secs, "abstract") or secs[0]["text"]
    concl = find(secs, "conclusion")
    progress("Writing one-line summary")
    text = llm.chat(
        "Write ONE sentence (max 35 words) stating what this paper does and its main finding.\n\n"
        f"Abstract/opening:\n{llm.clip(source, 3500)}\n\nConclusion:\n{llm.clip(concl, 2500)}"
    )
    return {"type": "markdown", "content": text.splitlines()[0]}


SCOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "problem": {"type": "string"},
        "scope": {"type": "string"},
        "contributions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["problem", "scope", "contributions"],
}


def scope(paper: dict, progress: Progress) -> dict:
    secs = split_sections(paper["text"])
    progress("Extracting problem scope and contributions")
    source = (
        find(secs, "abstract")[:2000] + "\n\n" + find(secs, "introduction")[:3500] + "\n\n" + find(secs, "conclusion")[:1500]
    ).strip() or llm.clip(paper["text"])
    data = llm.chat_json(
        "From this paper text, extract: 'problem' (what problem it tackles), 'scope' (what is covered and what is "
        "explicitly out of scope; 'Not stated' if unclear), and 'contributions' (list of the paper's claimed "
        f"contributions, short phrases).\n\n{source}",
        SCOPE_SCHEMA,
    )
    return {"type": "scope", **data}


def _source(paper: dict, names: tuple[str, ...], limit: int = 6500) -> str:
    secs = split_sections(paper["text"])
    text = find(secs, *names)
    return llm.clip(text or paper["text"], limit)


def _obj_list(props: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {"type": "object", "properties": {p: {"type": "string"} for p in props}, "required": props},
            }
        },
        "required": ["items"],
    }


def results(paper: dict, progress: Progress) -> dict:
    progress("Extracting key results")
    cols = ["metric", "value", "comparison"]
    data = llm.chat_json(
        "List the key quantitative results reported in this paper. For each: 'metric' (name incl. dataset/task), "
        "'value' (the paper's number), 'comparison' (baseline or prior result it is compared with, or 'Not stated'). "
        "Only include numbers that appear in the text.\n\n" + _source(paper, ("result", "experiment", "evaluation", "abstract")),
        _obj_list(cols),
    )
    return {"type": "table", "columns": cols, "rows": data["items"]}


def dataset(paper: dict, progress: Progress) -> dict:
    progress("Extracting dataset info")
    cols = ["name", "size", "source", "split", "notes"]
    data = llm.chat_json(
        "List every dataset used or introduced in this paper (data collections only, NOT models, methods or baselines). "
        "For each: 'name', 'size' (samples/scale), 'source' "
        "(where it comes from), 'split' (train/val/test), 'notes'. Use 'Not stated' for missing details.\n\n"
        + _source(paper, ("dataset", "experiment", "evaluation", "data")),
        _obj_list(cols),
    )
    return {"type": "table", "columns": cols, "rows": data["items"]}


LIMITS_SCHEMA = {
    "type": "object",
    "properties": {"stated": {"type": "array", "items": {"type": "string"}}, "inferred": {"type": "array", "items": {"type": "string"}}},
    "required": ["stated", "inferred"],
}


def limitations(paper: dict, progress: Progress) -> dict:
    progress("Finding limitations")
    data = llm.chat_json(
        "'stated': limitations the authors explicitly admit (empty list if none). 'inferred': additional likely "
        "limitations you infer from the method and evaluation (e.g. narrow datasets, missing baselines, cost). "
        "Keep each to one sentence.\n\n" + _source(paper, ("limitation", "discussion", "conclusion", "future")),
        LIMITS_SCHEMA,
    )
    return {"type": "limitations", **data}


DIAGRAM_SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {"type": "object", "properties": {"id": {"type": "string"}, "label": {"type": "string"}}, "required": ["id", "label"]},
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"from": {"type": "string"}, "to": {"type": "string"}, "label": {"type": "string"}},
                "required": ["from", "to"],
            },
        },
    },
    "required": ["steps", "edges"],
}


def build_mermaid(steps: list[dict], edges: list[dict]) -> str:
    """Build valid Mermaid from structured steps so model syntax errors can't break rendering."""
    ids = {}
    lines = ["flowchart TD"]
    for i, s in enumerate(steps[:12]):
        ids[s["id"]] = f"N{i}"
        label = " ".join(s["label"].replace('"', "'").split())[:60]
        lines.append(f'    N{i}["{label}"]')
    linked = False
    for e in edges:
        a, b = ids.get(e["from"]), ids.get(e["to"])
        if a and b and a != b:
            label = " ".join((e.get("label") or "").replace('"', "'").replace("|", "/").split())[:30]
            lines.append(f"    {a} -->|{label}| {b}" if label else f"    {a} --> {b}")
            linked = True
    if not linked:
        nodes = list(ids.values())
        lines += [f"    {a} --> {b}" for a, b in zip(nodes, nodes[1:])]
    return "\n".join(lines)


def diagram(paper: dict, progress: Progress) -> dict:
    progress("Extracting methodology steps")
    data = llm.chat_json(
        "Describe this paper's methodology as a flow diagram: 'steps' (4-10 nodes with short ids like s1 and labels "
        "of at most 6 words) and 'edges' (from/to ids, optional short label). Follow the method's actual data flow.\n\n"
        + _source(paper, ("method", "approach", "model", "framework", "proposed")),
        DIAGRAM_SCHEMA,
    )
    if not data["steps"]:
        raise llm.LLMError("The model could not identify methodology steps.")
    return {"type": "diagram", "mermaid": build_mermaid(data["steps"], data["edges"])}


SLIDES_SCHEMA = {
    "type": "object",
    "properties": {
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "bullets": {"type": "array", "items": {"type": "string"}}},
                "required": ["title", "bullets"],
            },
        }
    },
    "required": ["slides"],
}


def slides(paper: dict, progress: Progress) -> dict:
    items = _section_summaries(paper, progress)
    progress("Designing slides")
    notes = "\n".join(f"{i['section']}: {i['summary']}" for i in items)
    data = llm.chat_json(
        "Create a presentation of 7-9 slides for this paper: title/motivation, problem, key idea, method, "
        "experiments, results, limitations, conclusion. Each slide has a 'title' and 3-4 concise 'bullets' "
        f"(max 15 words each).\n\n{llm.clip(notes, 9000)}",
        SLIDES_SCHEMA,
    )
    deck = [s for s in data["slides"] if s["title"].strip()]
    if not deck:
        raise llm.LLMError("The model returned no slides.")
    first_line = paper["text"].strip().splitlines()[0][:100]
    return {"type": "slides", "title": paper.get("title") or first_line, "slides": deck}


HANDLERS: dict[str, Callable[[dict, Progress], dict]] = {
    "summary": summary,
    "sections": sections,
    "oneline": oneline,
    "scope": scope,
    "results": results,
    "dataset": dataset,
    "limitations": limitations,
    "diagram": diagram,
    "slides": slides,
}
