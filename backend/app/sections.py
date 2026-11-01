import re

KNOWN = (
    "abstract|introduction|related work|background|preliminaries|problem (?:statement|formulation)|"
    "methods?|methodology|approach|proposed (?:method|approach|model)|model|framework|"
    "experiments?|experimental (?:setup|results|evaluation)|evaluation|results?(?: and discussion)?|"
    "datasets?|discussion|limitations?|future work|conclusions?(?: and future work)?|"
    "references|bibliography|acknowledg(?:e)?ments?|appendix"
)
KNOWN_RE = re.compile(rf"^\s*(?:(?:\d+|[IVX]+)(?:\.\d+)*\.?\s+)?(?:{KNOWN})\s*[:.]?\s*$", re.I)
NUMBERED_RE = re.compile(r"^\s*\d{1,2}\.?\s+[A-Z][A-Za-z0-9 ,:\-&/()]{2,60}$")
STOP_RE = re.compile(r"^\s*(?:(?:\d+|[IVX]+)\.?\s+)?(references|bibliography|acknowledg(?:e)?ments?|appendix)\b", re.I)


def _is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 70:
        return False
    return bool(KNOWN_RE.match(line) or NUMBERED_RE.match(line))


def split_sections(text: str) -> list[dict]:
    """Split paper text into [{title, text}], dropping references and later material."""
    sections: list[dict] = [{"title": "Front matter", "lines": []}]
    for line in text.splitlines():
        if _is_heading(line):
            if STOP_RE.match(line) and len(sections) > 1:
                break
            sections.append({"title": re.sub(r"^\s*(?:\d+|[IVX]+)(?:\.\d+)*\.?\s+", "", line.strip()), "lines": []})
        else:
            sections[-1]["lines"].append(line)
    out = []
    for s in sections:
        body = re.sub(r"\s*\n\s*", " ", "\n".join(s["lines"])).strip()
        if len(body) > 80:
            out.append({"title": s["title"], "text": body})
    if not out:
        out = [{"title": "Full text", "text": re.sub(r"\s+", " ", text).strip()}]
    elif len(sections) == 1:
        out[0]["title"] = "Full text"
    return out


def find(sections: list[dict], *names: str) -> str:
    """Concatenate text of sections whose title contains any of the names."""
    hits = [s["text"] for s in sections if any(n in s["title"].lower() for n in names)]
    return "\n\n".join(hits)
