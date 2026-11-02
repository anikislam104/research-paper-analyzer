from app import jobs
from app.modes import sections


def test_section_progress_counts_calls(monkeypatch):
    from app import llm

    monkeypatch.setattr(llm, "chat", lambda *a, **k: "s")
    text = "Abstract\n" + "We study things. " * 20 + "\n1 Introduction\n" + "More text here. " * 20
    seen = []
    sections({"text": text}, lambda msg, done=None, total=None: seen.append((done, total)))
    totals = {t for _, t in seen}
    assert totals == {2}
    assert seen[-1][0] == 1 or max(d for d, _ in seen) == 2


def test_job_exposes_progress(monkeypatch):
    def handler(paper, progress):
        progress("working", 1, 4)
        return {"type": "markdown", "content": "x"}

    monkeypatch.setitem(jobs.HANDLERS, "oneline", handler)
    job_id = jobs.create("p", "oneline")
    jobs.run(job_id, {})
    job = jobs.get(job_id)
    assert (job["done"], job["total"], job["status"]) == (1, 4, "done")
