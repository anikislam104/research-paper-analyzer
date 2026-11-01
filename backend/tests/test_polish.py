import time

import pymupdf
from fastapi.testclient import TestClient

from app import jobs
from app.main import app
from app.pdf import extract_text

client = TestClient(app)


def test_running_headers_removed():
    doc = pymupdf.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((50, 30), "Journal of Widgets 2020", fontsize=9)
        page.insert_textbox(pymupdf.Rect(50, 60, 550, 700), f"Unique body paragraph number {i}. " * 15, fontsize=10)
    text = extract_text(doc.tobytes())["text"]
    assert "Journal of Widgets" not in text and "Unique body paragraph number 3" in text


def test_cancel(monkeypatch):
    def slow(paper, progress):
        for _ in range(50):
            time.sleep(0.05)
            progress("working")
        return {"type": "markdown", "content": "x"}

    monkeypatch.setitem(jobs.HANDLERS, "oneline", slow)
    job_id = jobs.create("p", "oneline")
    import threading

    t = threading.Thread(target=jobs.run, args=(job_id, {}))
    t.start()
    time.sleep(0.2)
    assert client.post(f"/api/jobs/{job_id}/cancel").status_code == 200
    t.join(timeout=5)
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "cancelled" and job["result"] is None


def test_cancel_unknown_job():
    assert client.post("/api/jobs/nope/cancel").status_code == 404
