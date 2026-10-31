import pytest

from studio import layout, objects
from studio import spec as S


def mk(objs, params=None, fmt="long"):
    sp = S.Spec(id="t", title="t", beats=[S.Beat(say="x")], params=params or {}, objects=[S.Obj(**o) for o in objs])
    w = objects.World(sp, layout.Layout(fmt))
    w.build()
    return w


def test_points_map_into_stage():
    w = mk([{"id": "A", "type": "point", "at": [0, 0]}, {"id": "B", "type": "point", "at": [10, 6]}])
    st = layout.Layout("long").stage
    assert st.x0 - 1e-6 <= w.point("A")[0] < w.point("B")[0] <= st.x1 + 1e-6
    assert st.y0 - 1e-6 <= w.point("A")[1] < w.point("B")[1] <= st.y1 + 1e-6


def test_param_driven_point_moves():
    w = mk([{"id": "A", "type": "point", "at": [0, 0]}, {"id": "C", "type": "point", "at": ["A.x + 2*x", 0]}], {"x": 1})
    x0 = w.point("C")[0]
    w.params["x"].set_value(2)
    w.get("C").update()
    assert w.point("C")[0] > x0
    assert "C" in w.dynamic and "A" not in w.dynamic


CORE = {
    "segment": {"from": "A", "to": "B"}, "arrow": {"from": "A", "to": "B"}, "vector": {"from": "A", "to": "B", "label": "\\vec F"},
    "polyline": {"path": ["A", "B", [8, 1]]}, "region": {"corners": [[0, 0], [10, 0], [10, 2]], "style": "water"},
    "circle": {"center": "A", "radius": 1}, "arc": {"center": "A", "radius": 1, "start": 0, "end": 90},
    "angle": {"vertex": "A", "from_dir": [1, 0], "to": "B", "label": "\\theta"}, "dimension": {"from": "A", "to": "B", "label": "d"},
    "brace": {"from": "A", "to": "B", "label": "x"}, "label": {"at": "B", "tex": "B"}, "text": {"text": "Hello", "at": [5, 5]},
    "bullet_list": {"items": ["one", "two"]}, "card": {"title": "Fact", "body": "Water boils at 100 °C at sea level"},
    "code": {"code": "print('hi')", "language": "python"}, "table": {"rows": [["a", "b"], ["1", "2"]]},
    "axes": {"x": [0, 5], "y": [0, 10], "x_label": "t", "y_label": "v"}, "bar_chart": {"labels": ["A", "B"], "values": [3, 5]},
    "line_chart": {"x": [0, 1, 2], "y": [1, 4, 9]}, "number_line": {"range": [-3, 3]},
    "timeline": {"events": [{"date": "1526", "text": "Babur"}, {"date": "1857", "text": "End"}]},
    "flow": {"nodes": ["Light", "Chlorophyll", "Glucose"]},
}


@pytest.mark.parametrize("fmt", ["long", "short"])
def test_every_core_type_builds_inside_frame(fmt):
    objs = [{"id": "A", "type": "point", "at": [1, 1]}, {"id": "B", "type": "point", "at": [5, 3]}]
    objs += [{"id": f"o_{t}", "type": t, **f} for t, f in CORE.items()]
    w = mk(objs, fmt=fmt)
    L = layout.Layout(fmt)
    for t in CORE:
        m = w.get(f"o_{t}")
        assert m is not None, t
        assert abs(m.get_center()[0]) <= L.frame_w / 2 and abs(m.get_center()[1]) <= L.frame_h / 2, t


def test_unknown_type_is_clear_error():
    with pytest.raises(objects.ObjectError, match="unknown object type 'blob'"):
        mk([{"id": "z", "type": "blob"}])


def test_fit_shrinks_long_equation():
    from studio.mtex import M

    box = layout.Layout("long").panel
    eq = M(r"t(x)=\dfrac{x}{v}+\dfrac{\eta\sqrt{(d-x)^2+\ell^2}}{v}+\dfrac{\eta\sqrt{(d-x)^2+\ell^2}}{v}+\dfrac{\eta\sqrt{(d-x)^2+\ell^2}}{v}", scale=2)
    layout.fit(eq, box)
    assert eq.width <= box.w + 1e-6


def test_long_text_wraps_in_card():
    w = mk([{"id": "c", "type": "card", "title": "A very long fact", "body": "word " * 60}], fmt="short")
    assert w.get("c").width <= layout.Layout("short").panel.w + 1e-6
