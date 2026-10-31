"""Subcommands register themselves via cli.command."""
import json
from pathlib import Path

from .cli import command


def _ingest_cfg(p):
    p.add_argument("folder")
    p.add_argument("--out", default="work/sources.json")


@command("ingest")
def cmd_ingest(a):
    from .ingest import ingest

    r = ingest(Path(a.folder))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(f.get("items", [])) for f in r["files"])
    print(f"{len(r['files'])} files, {n} parsed items, {len(r['images'])} images, {len(r['skipped'])} skipped -> {out}")
    return 0


cmd_ingest.configure = _ingest_cfg


def _check_cfg(p):
    p.add_argument("spec")
    p.add_argument("--formats", default="long,short")


@command("check")
def cmd_check(a):
    from .checks import check

    r = check(Path(a.spec), tuple(a.formats.split(",")))
    r.pop("visible_text", None)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    clean = r["ok"] and not r["warnings"]
    marker = Path(a.spec).with_name("check.ok")
    if clean:
        from .status import spec_sha

        marker.write_text(json.dumps({"spec_sha": spec_sha(Path(a.spec)), "est_seconds": r["est_seconds"]}), encoding="utf-8")
    else:
        marker.unlink(missing_ok=True)
    return 0 if clean else 1


cmd_check.configure = _check_cfg


def _render_cfg(p):
    p.add_argument("spec")
    p.add_argument("--format", choices=["long", "short", "thumb"], required=True)
    p.add_argument("--quality", choices=["preview", "final"], default="final")
    p.add_argument("--workspace", default=".")
    p.add_argument("--channel-name", default="")
    p.add_argument("--channel-url", default="")
    p.add_argument("--logo", default="")
    p.add_argument("--voice", default="")


def brand_from_args(a):
    from .brand import load

    return load(Path(a.workspace), {"channel_name": a.channel_name, "channel_url": a.channel_url, "logo": a.logo, "voice": a.voice})


@command("render")
def cmd_render(a):
    from .render import render

    spec = Path(a.spec)
    out = render(spec, a.format, a.quality, brand_from_args(a), spec.parent)
    print(f"rendered {a.format} ({a.quality}) -> {out}")
    return 0


cmd_render.configure = _render_cfg


def _package_cfg(p):
    _render_cfg_common(p)
    p.add_argument("item_dir")
    p.add_argument("--out", required=True)
    p.add_argument("--outputs", default="long,short,thumb")


def _render_cfg_common(p):
    p.add_argument("--workspace", default=".")
    p.add_argument("--channel-name", default="")
    p.add_argument("--channel-url", default="")
    p.add_argument("--logo", default="")
    p.add_argument("--voice", default="")


@command("package")
def cmd_package(a):
    from .post import package

    res = package(Path(a.item_dir), Path(a.out), brand_from_args(a), a.outputs.split(","))
    print(json.dumps(res))
    return 0


cmd_package.configure = _package_cfg


def _verify_cfg(p):
    p.add_argument("checks", help="JSON list of checks, e.g. work/<id>/verify.json")


@command("verify")
def cmd_verify(a):
    from .verify import verify_file

    res = verify_file(Path(a.checks))
    print(json.dumps(res, indent=1))
    return 0 if res["ok"] else 1


cmd_verify.configure = _verify_cfg


@command("models")
def cmd_models(a):
    from .models import download

    download()
    return 0


def _doctor_cfg(p):
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true", help="skip the test render")


@command("doctor")
def cmd_doctor(a):
    from .doctor import run

    rep = run(quick=a.quick)
    if a.json:
        print(json.dumps(rep, indent=1))
    else:
        for c in rep["checks"]:
            print(("OK   " if c["ok"] else "FAIL ") + c["name"] + (f"  {c['detail']}" if c["detail"] else ""))
            if not c["ok"]:
                print("     fix: " + c["fix"])
    return 0 if rep["ok"] else 1


cmd_doctor.configure = _doctor_cfg


def _status_cfg(p):
    p.add_argument("workspace", nargs="?", default=".")
    p.add_argument("--json", action="store_true")


@command("status")
def cmd_status(a):
    from .status import states

    rows = states(Path(a.workspace))
    if a.json:
        print(json.dumps(rows))
    else:
        for r in rows:
            print(f"{r['state']:<16} {r['id']:<28} {','.join(r['outputs'])}")
    return 0


cmd_status.configure = _status_cfg


TEMPLATES = {"worked-problem", "concept-explainer", "quiz", "facts-list", "timeline", "compare"}


def _plan_check_cfg(p):
    p.add_argument("plan")


@command("plan-check")
def cmd_plan_check(a):
    import re

    from .spec import SpecError, load_plan

    try:
        plan = load_plan(Path(a.plan))
    except SpecError as e:
        print("\n".join(e.messages))
        return 1
    errors, seen = [], set()
    for it in plan.items:
        if it.id in seen:
            errors.append(f"duplicate id '{it.id}'")
        seen.add(it.id)
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", it.id):
            errors.append(f"id '{it.id}' must be a lowercase slug (a-z, 0-9, -)")
        if it.template not in TEMPLATES:
            errors.append(f"unknown template '{it.template}' (use one of {', '.join(sorted(TEMPLATES))})")
    print("\n".join(errors) if errors else f"plan ok: {len(plan.items)} items")
    return 1 if errors else 0


cmd_plan_check.configure = _plan_check_cfg


def _sheet_cfg(p):
    p.add_argument("video")
    p.add_argument("--out", default=None)


@command("sheet")
def cmd_sheet(a):
    from .sheet import contact_sheet

    v = Path(a.video)
    out = contact_sheet(v, Path(a.out) if a.out else v.with_suffix(".sheet.png"))
    print(out)
    return 0


cmd_sheet.configure = _sheet_cfg
