from io import BytesIO

from pptx import Presentation

from app.modes import build_mermaid
from app.pptx_export import build_pptx


def test_mermaid_sanitizes_and_links():
    steps = [{"id": "a", "label": 'Encode "parts"'}, {"id": "b", "label": "Attend"}]
    out = build_mermaid(steps, [{"from": "a", "to": "b", "label": "x|y"}, {"from": "a", "to": "zzz"}])
    assert out.startswith("flowchart TD")
    assert 'N0["Encode \'parts\'"]' in out and "N0 -->|x/y| N1" in out and "zzz" not in out


def test_mermaid_falls_back_to_chain():
    out = build_mermaid([{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], [])
    assert "N0 --> N1" in out


def test_pptx_roundtrip():
    data = build_pptx("T", [{"title": "S1", "bullets": ["one", "two"]}])
    prs = Presentation(BytesIO(data))
    assert len(prs.slides) == 2
