from app.sections import find, split_sections

SAMPLE = """Deep Widgets
Some Authors

Abstract
We propose a widget method that improves widget accuracy substantially across many benchmarks and settings.

1 Introduction
Widgets are important in industry. Existing methods fail on large widgets because of scaling problems here.

2 Method
We introduce a scaled widget network with attention over parts of widgets for better results overall.

3. Conclusion
Our method works well and we plan to extend it further to other kinds of gadgets in future work.

References
[1] A. Author. Widgets. 2020.
"""


def test_split_and_find():
    secs = split_sections(SAMPLE)
    titles = [s["title"].lower() for s in secs]
    assert titles == ["abstract", "introduction", "method", "conclusion"]
    assert "widget method" in find(secs, "abstract")
    assert all("A. Author" not in s["text"] for s in secs)


def test_fallback_without_headings():
    secs = split_sections("plain text without headings " * 20)
    assert secs[0]["title"] == "Full text"
