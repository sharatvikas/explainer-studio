import json

import pytest

from studio import cli
from studio.verify import verify


def test_irodov_checks_pass():
    r = verify([
        {"kind": "equal", "a": "l/sqrt(eta**2-1)", "b": "1/sqrt(3)", "subs": {"l": 1, "eta": 2}},
        {"kind": "minimum", "f": "x + 2*sqrt((2-x)**2+1)", "var": "x", "range": [0, 2], "expect_at": 1.4226, "tol": 1e-3},
        {"kind": "symbolic_equal", "a": "d + l*sqrt(eta**2-1)", "b": "d + sqrt(l**2*(eta**2-1))", "assume_positive": True},
        {"kind": "value", "expr": "2 + sqrt(3)", "expect": 3.732, "tol": 1e-3},
    ])
    assert r["ok"], r


def test_wrong_answer_fails():
    r = verify([{"kind": "value", "expr": "2 + sqrt(3)", "expect": 4.0, "tol": 1e-3}])
    assert not r["ok"] and abs(r["results"][0]["got"] - 3.7320508) < 1e-6


def test_wrong_minimum_location_fails():
    r = verify([{"kind": "minimum", "f": "x + 2*sqrt((2-x)**2+1)", "var": "x", "range": [0, 2], "expect_at": 1.0, "tol": 1e-3}])
    assert not r["ok"]


@pytest.mark.parametrize("bad", ["__import__('os').system('echo hi')", "open('x')", "eval('1')"])
def test_rejects_code(bad):
    r = verify([{"kind": "value", "expr": bad, "expect": 0}])
    assert not r["ok"] and "error" in r["results"][0]


def test_cli_writes_result(tmp_path):
    f = tmp_path / "verify.json"
    f.write_text(json.dumps([{"kind": "value", "expr": "1+1", "expect": 2}]), encoding="utf-8")
    assert cli.main(["verify", str(f)]) == 0
    assert json.loads((tmp_path / "verify.result.json").read_text(encoding="utf-8"))["ok"]
