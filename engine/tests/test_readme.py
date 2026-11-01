from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]


def test_readme_has_flow_and_commands():
    r = (ROOT / "README.md").read_text(encoding="utf-8")
    for s in ["assets/flow.svg", "```mermaid", "/explainer-studio:setup", "/explainer-studio:make", "/explainer-studio:plan-series", "/plugin marketplace add", "1080p"]:
        assert s in r, s


def test_flow_svg_is_valid_and_complete():
    svg = (ROOT / "assets" / "flow.svg").read_text(encoding="utf-8")
    ElementTree.fromstring(svg)  # well-formed XML
    for word in ["Source folder", "Ingest", "Plan", "Research", "Spec", "Check", "Render", "Package", "output/", "needs attention"]:
        assert word in svg, word
