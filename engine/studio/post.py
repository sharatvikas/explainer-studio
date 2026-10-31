"""Post-production: music ducked under the voice, loudness, watermark, Short captions,
subtitles, chapters and a paste-ready description. Outputs are atomic: every file is
written under a temporary name and `done.json` is written last, so an interrupted
run is never mistaken for a finished one.
"""
import json
import os
import re
import subprocess
from pathlib import Path

import av
import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

from . import __version__, fonts
from .brand import Brand
from .sfx import music
from .voice import caption_chunks

FINAL_SIZE = {"long": (1920, 1080), "short": (1080, 1920)}
CAPTION_HIGHLIGHT = {}  # word -> colour; filled per spec by the caller if wanted


class QualityError(RuntimeError):
    pass


def ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(path: Path) -> tuple[int, int, float]:
    with av.open(str(path)) as c:
        v = c.streams.video[0]
        dur = float(c.duration / av.time_base) if c.duration else float(v.duration * v.time_base)
        return v.width, v.height, dur


def _run(args):
    r = subprocess.run([ffmpeg(), "-y", "-loglevel", "error", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"ffmpeg failed: {r.stderr.strip()[-800:]}")


# ---- test helpers (also handy for smoke tests) ----------------------------------------
def make_test_clip(path: Path, seconds=2, size=(1920, 1080)):
    path.parent.mkdir(parents=True, exist_ok=True)
    _run(["-f", "lavfi", "-i", f"color=c=0x0B0E14:s={size[0]}x{size[1]}:r=30:d={seconds}",
          "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo", "-t", seconds, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path])
    return path


def make_test_tone(path: Path, seconds=1.0):
    t = np.arange(int(24000 * seconds)) / 24000
    sf.write(path, 0.2 * np.sin(2 * np.pi * 220 * t), 24000)


# ---- text outputs -------------------------------------------------------------------------
def _ts(x):
    h, rem = divmod(x, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"


def write_srt(tl, path):
    lines = []
    for i, v in enumerate(tl["voice"], 1):
        lines += [str(i), f"{_ts(v['t'])} --> {_ts(v['t'] + v['dur'])}", v.get("caption") or v["text"], ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def chapter_lines(tl):
    out = []
    for c in tl.get("chapters", []):
        if c["title"].lower() == "title":
            continue
        t = 0 if not out else c["t"]
        out.append(f"{int(t // 60)}:{int(t % 60):02d} {c['title']}")
    return out


def write_chapters(tl, path):
    Path(path).write_text("\n".join(chapter_lines(tl)) + "\n", encoding="utf-8")


def _sources(item_dir: Path) -> list[str]:
    f = item_dir / "research.md"
    if not f.exists():
        return []
    return [l.strip().lstrip("-* ").strip() for l in f.read_text(encoding="utf-8").splitlines() if re.search(r"https?://", l)][:6]


def write_description(item_dir: Path, tl, brand: Brand, path: Path):
    spec = {}
    if (item_dir / "spec.json").exists():
        spec = json.loads((item_dir / "spec.json").read_text(encoding="utf-8"))
    title = spec.get("title") or item_dir.name.replace("-", " ").title()
    hook = (spec.get("beats") or [{}])[0].get("say", "")
    parts = [title, ""]
    if hook:
        parts += [hook, ""]
    ch = chapter_lines(tl) if tl else []
    if ch:
        parts += ["Chapters", *ch, ""]
    src = _sources(item_dir)
    if src:
        parts += ["Sources", *[f"- {s}" for s in src], ""]
    if brand.channel_url:
        parts += [f"More: {brand.channel_url}", ""]
    words = [w for w in re.findall(r"[A-Za-z]+", title) if len(w) > 3][:3]
    tags = ["#" + k for k in spec.get("kits", [])] + ["#" + w.lower() for w in words] + ["#education"]
    parts.append(" ".join(dict.fromkeys(tags)))
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


# ---- overlays -------------------------------------------------------------------------------
def _monogram(name: str, size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, size - 1, size - 1), fill=(244, 207, 107, 255))
    initials = "".join(w[0] for w in name.split()[:2]).upper() or "•"
    f = fonts.pil("heading", int(size * 0.42), initials)
    d.text((size / 2, size / 2), initials, font=f, fill=(11, 14, 20, 255), anchor="mm")
    return img


def hud_png(path: Path, width: int, brand: Brand):
    s = width / 1920
    size = int(54 * s)
    if brand.logo and Path(brand.logo).exists():
        logo = Image.open(brand.logo).convert("RGBA").resize((size, size), Image.LANCZOS)
    else:
        logo = _monogram(brand.channel_name, size)
    text = brand.channel_url or brand.channel_name
    f = fonts.pil("medium", int(24 * s), text)
    tw = int(f.getlength(text))
    img = Image.new("RGBA", (size + int(14 * s) + tw + 4, size), (0, 0, 0, 0))
    img.paste(logo, (0, 0), logo)
    ImageDraw.Draw(img).text((size + int(14 * s), size // 2), text, font=f, fill=(200, 205, 215, 170), anchor="lm")
    img.putalpha(img.getchannel("A").point(lambda a: int(a * 0.85)))
    img.save(path)


def caption_pngs(tl, outdir: Path, width: int, highlight: dict, size=68, max_words=3):
    """One transparent PNG per caption chunk. Each word gets a font that has its glyphs
    (Devanagari and Greek can sit in the same caption). Long chunks shrink to fit."""
    items, k = [], 0
    for v in tl["voice"]:
        t = v["t"]
        for chunk, frac in caption_chunks(v.get("caption") or v["text"], max_words):
            end = t + v["dur"] * frac
            words = chunk.split()
            px = size
            while True:
                wf = [fonts.pil("heading", px, w) for w in words]
                widths = [f.getlength(w) for f, w in zip(wf, words)]
                space = wf[0].getlength(" ") if wf else 0
                total = sum(widths) + space * (len(words) - 1)
                if total <= width * 0.9 or px <= 24:
                    break
                px = int(px * 0.9)  # long words never run off the edge
            img = Image.new("RGBA", (width, int(size * 1.9)), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            x = (width - total) / 2
            for f, wd, wtxt in zip(wf, widths, words):
                key = "".join(ch for ch in wtxt.lower() if ch.isalnum() or ch in "'!.≠")
                col = highlight.get(key, highlight.get(key.rstrip(".!,"), "#FFFFFF"))
                d.text((x, size * 0.95), wtxt, font=f, fill=col, anchor="lm", stroke_width=7, stroke_fill="#000000")
                x += wd + space
            p = outdir / f"cap_{k:03d}.png"
            img.save(p)
            items.append((p, t, end + 0.05))
            t, k = end, k + 1
    return items


# ---- mixing ----------------------------------------------------------------------------------
def voice_track(tl, duration, path):
    if not tl["voice"]:
        sf.write(path, np.zeros(int(24000 * max(duration, 0.1))), 24000)
        return
    sr = sf.info(tl["voice"][0]["wav"]).samplerate
    out = np.zeros(int(sr * (duration + 1)))
    for v in tl["voice"]:
        x, _ = sf.read(v["wav"])
        if x.ndim > 1:
            x = x.mean(axis=1)
        i = int(v["t"] * sr)
        out[i : i + len(x)] += x[: max(0, len(out) - i)]
    sf.write(path, out, sr)


def finish_video(raw: Path, tl: dict, fmt: str, brand: Brand, work: Path, target: Path, highlight=None):
    w, h, dur = probe(raw)
    if (w, h) != FINAL_SIZE[fmt]:
        want = "x".join(map(str, FINAL_SIZE[fmt]))
        raise QualityError(f"{fmt} render is {w}x{h}; final videos must be {want}. Re-render with --quality final.")
    work.mkdir(parents=True, exist_ok=True)
    voice_track(tl, dur, work / f"{fmt}_voice.wav")
    inputs = ["-i", raw]
    if brand.music:
        music(max(dur, 1.0), str(work / f"{fmt}_music.wav"), bpm=92 if fmt == "short" else 84)
        inputs += ["-i", work / f"{fmt}_music.wav", "-i", work / f"{fmt}_voice.wav"]
        audio = ("[1:a]volume=-17dB[m];[2:a]aresample=44100,pan=stereo|c0=c0|c1=c0[sc];"
                 "[m][sc]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=500:makeup=1[md];"
                 "[0:a][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
        n = 3
    else:
        audio = "[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
        n = 1
    video, last = "[0:v]null[v0]", "v0"
    if fmt == "long":
        hud_png(work / "hud.png", w, brand)
        inputs += ["-i", work / "hud.png"]
        end = max(0.0, dur - 3.5)  # hide during the end card, which shows the brand itself
        video += f";[v0][{n}:v]overlay=W-w-{int(w * 0.025)}:H-h-{int(h * 0.035)}:enable='lt(t,{end:.2f})'[v1]"
        last, n = "v1", n + 1
    else:
        caps = caption_pngs(tl, work, w, highlight or CAPTION_HIGHLIGHT)
        y = int(h * 0.79)
        for i, (p, t0, t1) in enumerate(caps):
            inputs += ["-i", p]
            video += f";[{last}][{n}:v]overlay=0:{y}:enable='between(t,{t0:.3f},{t1:.3f})'[c{i}]"
            last, n = f"c{i}", n + 1
    graph = work / f"{fmt}_graph.txt"
    graph.write_text(audio + ";" + video, encoding="utf-8")
    tmp = target.with_name(target.stem + ".tmp.mp4")
    _run([*inputs, "-filter_complex_script", graph, "-map", f"[{last}]", "-map", "[aout]",
          "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp])
    os.replace(tmp, target)
    return probe(target)[2]


def is_done(out_dir: Path, outputs: list[str]) -> bool:
    f = Path(out_dir) / "done.json"
    if not f.exists():
        return False
    done = set(json.loads(f.read_text(encoding="utf-8")).get("outputs", []))
    names = {"long": "long.mp4", "short": "short.mp4", "thumb": "thumbnail.png"}
    return all(o in done and (Path(out_dir) / names[o]).exists() for o in outputs)


def package(item_dir: Path, out_dir: Path, brand: Brand, outputs: list[str], highlight=None) -> dict:
    item_dir, out_dir = Path(item_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "done.json").unlink(missing_ok=True)
    work = item_dir / "post"
    res = {"outputs": [], "durations": {}, "version": __version__}
    tl_long = None
    for fmt in ("long", "short"):
        if fmt not in outputs:
            continue
        tl = json.loads((item_dir / f"{fmt}.timeline.json").read_text(encoding="utf-8"))
        res["durations"][fmt] = round(finish_video(item_dir / f"{fmt}.raw.mp4", tl, fmt, brand, work, out_dir / f"{fmt}.mp4", highlight), 2)
        res["outputs"].append(fmt)
        if fmt == "long":
            tl_long = tl
            write_srt(tl, out_dir / "subtitles.srt")
            write_chapters(tl, out_dir / "chapters.txt")
    if "thumb" in outputs:
        thumb = item_dir / "thumb.png"
        Image.open(thumb).convert("RGB").save(out_dir / "thumbnail.tmp.png")
        os.replace(out_dir / "thumbnail.tmp.png", out_dir / "thumbnail.png")
        res["outputs"].append("thumb")
    write_description(item_dir, tl_long, brand, out_dir / "description.txt")
    (out_dir / "done.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res
