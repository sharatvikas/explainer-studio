import csv
import json

from studio import catalogue
from studio.cli import main
from studio.ingest import ingest


def _cat(items, **kw):
    return {"series": "Class 11 Kinematics", "items": items, **kw}


GOOD = [
    {"title": "Why a Feather Falls Slower", "kind": "concept", "question": "Why does a feather fall slower than a ball in air?",
     "answer": "Air drag, not gravity, differs", "key_points": ["Same g in vacuum", "Drag depends on area"]},
    {"title": "The 45 Degree Rule", "kind": "problem", "source": "Classic", "question": "At what angle is range greatest?",
     "answer": "45 degrees", "template": "worked-problem", "outputs": ["short"]},
]


def test_valid_catalogue_writes_csv_that_ingest_reads(tmp_path):
    src = tmp_path / "cat.json"
    src.write_text(json.dumps(_cat(GOOD)), encoding="utf-8")
    out = tmp_path / "series" / "kinematics"
    assert main(["catalogue", str(src), "--out", str(out)]) == 0
    rows = list(csv.DictReader((out / "catalogue.csv").open(encoding="utf-8-sig", newline="")))
    assert [r["id"] for r in rows] == ["why-a-feather-falls-slower", "the-45-degree-rule"]
    assert rows[0]["key_points"] == "Same g in vacuum; Drag depends on area"
    assert rows[0]["template"] == "concept-explainer" and rows[1]["outputs"] == "short"
    items = ingest(out)["files"][0]["items"]
    assert items[1]["answer"] == "45 degrees" and items[1]["template"] == "worked-problem"


def test_commas_quotes_and_unicode_survive_csv(tmp_path):
    it = dict(GOOD[0], question='He said "stop", then v = u + at, θ → 0')
    rows = catalogue.write_csv(catalogue.validate(_cat([it]))[0], tmp_path)
    back = list(csv.DictReader(rows.open(encoding="utf-8-sig", newline="")))
    assert back[0]["question"] == it["question"]


def test_errors_reported_together():
    bad = [{"title": "", "kind": "concept", "question": "q"},
           {"title": "Range", "kind": "problem", "question": "q"},
           {"title": "Range", "kind": "story", "question": "q", "answer": "a", "template": "movie"}]
    _, errors, _ = catalogue.validate(_cat(bad))
    text = "\n".join(errors)
    assert "item 1: title is required" in text
    assert "item 2 (range): problems need an answer" in text
    assert "duplicate id 'range'" in text
    assert "kind 'story'" in text and "template 'movie'" in text


def test_existing_topics_are_flagged(tmp_path):
    (tmp_path / "output" / "the-45-degree-rule").mkdir(parents=True)
    (tmp_path / "existing.txt").write_text("Why a feather falls slower?\n", encoding="utf-8")
    _, _, warnings = catalogue.validate(_cat(GOOD), exclude=[tmp_path / "output", tmp_path / "existing.txt"])
    assert len(warnings) == 2 and all("already" in w for w in warnings)


def test_cli_fails_without_writing_on_errors(tmp_path, capsys):
    src = tmp_path / "cat.json"
    src.write_text(json.dumps(_cat([{"title": "x", "kind": "problem", "question": "q"}])), encoding="utf-8")
    assert main(["catalogue", str(src), "--out", str(tmp_path / "s")]) == 1
    assert "answer" in capsys.readouterr().out and not (tmp_path / "s").exists()
