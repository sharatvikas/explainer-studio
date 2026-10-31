import pytest

from studio import expr, spec


def test_expression_math_and_refs():
    env = expr.Env({"x": 1.0}, {"A": (1.0, 4.6)})
    assert expr.evaluate("A.x + 3*x", env) == pytest.approx(4.0)
    assert expr.evaluate("sqrt(4)+pi*0", env) == 2
    assert expr.evaluate(2.5, env) == 2.5


@pytest.mark.parametrize("bad", ["__import__('os')", "open('f')", "x.__class__", "[1,2]", "lambda: 1", "A.z", "nope + 1"])
def test_expression_rejects_unsafe(bad):
    with pytest.raises(expr.ExprError):
        expr.evaluate(bad, expr.Env({"x": 1}, {"A": (0, 0)}))


def test_object_order_and_cycle():
    objs = [{"id": "C", "type": "point", "at": ["A.x+1", 0]}, {"id": "A", "type": "point", "at": [0, 0]},
            {"id": "s", "type": "segment", "from": "A", "to": "C"}]
    assert [o["id"] for o in expr.order_objects(objs)] == ["A", "C", "s"]
    with pytest.raises(expr.ExprError, match="cycle"):
        expr.order_objects([{"id": "P", "type": "point", "at": ["Q.x", 0]}, {"id": "Q", "type": "point", "at": ["P.x", 0]}])


def test_params_used_detects_dependencies():
    assert expr.params_used({"id": "C", "at": ["A.x + 3*x", 4.6]}, {"x", "y"}) == {"x"}


def test_spec_errors_are_readable(tmp_path):
    f = tmp_path / "s.json"
    f.write_text('{"id": "x", "beats": [{"do": []}]}', encoding="utf-8")
    with pytest.raises(spec.SpecError) as e:
        spec.load(f)
    assert any("say" in m for m in e.value.messages) and any("title" in m for m in e.value.messages)


def test_spec_op_for_alias(tmp_path):
    f = tmp_path / "s.json"
    f.write_text('{"id":"x","title":"T","beats":[{"say":"hi","do":[{"op":"show","ids":["A"],"at":0.2,"for":0.5}]}]}', encoding="utf-8")
    op = spec.load(f).beats[0].do[0]
    assert op.at == 0.2 and op.for_ == 0.5 and op.model_extra["ids"] == ["A"]


def test_plan_validates_outputs(tmp_path):
    f = tmp_path / "p.json"
    f.write_text('{"items":[{"id":"a","title":"A","template":"quiz","outputs":["video"]}]}', encoding="utf-8")
    with pytest.raises(spec.SpecError):
        spec.load_plan(f)


def test_invalid_json_message(tmp_path):
    f = tmp_path / "s.json"
    f.write_text('{"id": ', encoding="utf-8")
    with pytest.raises(spec.SpecError, match="invalid JSON"):
        spec.load(f)
