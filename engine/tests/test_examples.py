from pathlib import Path

import pytest

from studio.checks import check

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "skills" / "spec-authoring" / "examples"
TEMPLATES = ["worked-problem", "concept-explainer", "quiz", "facts-list", "timeline", "compare"]


@pytest.mark.parametrize("name", ["irodov-1-17.json", "photosynthesis-explainer.json", "quiz-short.json"])
def test_examples_check_clean(name, monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path))
    r = check(EX / name)
    assert r["ok"] and not r["warnings"], r["errors"] + r["warnings"]


def test_authoring_docs_exist():
    sa = ROOT / "skills" / "spec-authoring"
    for f in ["SKILL.md", "style-guide.md", "research.md", "kits/physics.md", *[f"templates/{t}.md" for t in TEMPLATES]]:
        assert (sa / f).exists(), f
    body = (sa / "SKILL.md").read_text(encoding="utf-8")
    from studio.objects import BUILDERS
    from studio.ops import OPS

    import studio.kits.physics  # noqa: F401  registers kit types

    for name in [*BUILDERS, *OPS]:
        assert f"`{name}`" in body or f"`{name}`" in (sa / "kits" / "physics.md").read_text(encoding="utf-8"), f"undocumented: {name}"
