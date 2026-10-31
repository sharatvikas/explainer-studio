from pathlib import Path

from studio import cli
from studio.ingest import ingest, split_markdown

FIX = Path(__file__).parent / "fixtures" / "input"


def test_markdown_splits_questions():
    items = split_markdown("## Q1. Find x\nx+1=2\n**Answer:** 1\n\n## Q2. Speed?\n**Answer:** 3 m/s\n**Source:** HCV 2.1")
    assert [i["answer"] for i in items] == ["1", "3 m/s"] and items[1]["source"] == "HCV 2.1"
    assert items[0]["question"].startswith("Find x")


def test_folder_mixed_kinds():
    r = ingest(FIX)
    kinds = {Path(f["path"]).name: f["kind"] for f in r["files"]}
    assert kinds["items.json"] == "table" and kinds["items.csv"] == "table"
    assert kinds["doc.docx"] == "text" and kinds["deck.pptx"] == "text" and kinds["paper.pdf"] == "text"
    texts = {Path(f["path"]).name: f.get("text", "") for f in r["files"]}
    assert "Newton" in texts["doc.docx"] and "Photosynthesis" in texts["deck.pptx"] and "Ohm" in texts["paper.pdf"]
    assert any(p.endswith("shot.png") for p in r["images"])
    assert any(p.endswith("weird.xyz") for p in r["skipped"])
    md = next(f for f in r["files"] if f["path"].endswith("questions.md"))
    assert len(md["items"]) == 2 and md["items"][0]["source"] == "Irodov 1.17"


def test_unicode_and_spaces_in_path(tmp_path):
    d = tmp_path / "मेरे नोट्स folder"
    d.mkdir()
    (d / "q.md").write_text("## प्रश्न 1\nप्रकाश क्या है?\n**Answer:** ऊर्जा", encoding="utf-8")
    r = ingest(d)
    assert r["files"][0]["items"][0]["answer"] == "ऊर्जा"


def test_bad_file_does_not_stop_batch(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "ok.md").write_text("## Q\nHi?\n**Answer:** yes", encoding="utf-8")
    r = ingest(tmp_path)
    assert any("broken.json" in s for s in r["skipped"]) and r["files"][0]["items"][0]["answer"] == "yes"


def test_cli_writes_sources(tmp_path, capsys):
    out = tmp_path / "sources.json"
    assert cli.main(["ingest", str(FIX), "--out", str(out)]) == 0
    assert out.exists() and "parsed items" in capsys.readouterr().out
