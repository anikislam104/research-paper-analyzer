import pymupdf
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=11)
    return doc.tobytes()


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_upload_ok():
    pdf = make_pdf("Abstract. " + "We study paper analysis. " * 20)
    r = client.post("/api/papers", files={"file": ("p.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    assert body["page_count"] == 1 and body["paper_id"]


def test_rejects_non_pdf():
    r = client.post("/api/papers", files={"file": ("p.pdf", b"hello", "application/pdf")})
    assert r.status_code == 422
