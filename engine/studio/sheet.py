"""Contact sheet: 12 evenly spaced frames tiled 4x3 into one PNG for quick visual review."""
from pathlib import Path

import av
from PIL import Image


def contact_sheet(video: Path, out: Path, n: int = 12, cols: int = 4, tile_w: int = 480) -> Path:
    with av.open(str(video)) as c:
        s = c.streams.video[0]
        dur = float(c.duration / av.time_base)
        times = [dur * (i + 0.5) / n for i in range(n)]
        frames = []
        for t in times:
            c.seek(int(t / s.time_base), stream=s, any_frame=False, backward=True)
            for fr in c.decode(s):
                if fr.time is None or fr.time >= t - 0.05:
                    frames.append(fr.to_image())
                    break
    if not frames:
        raise RuntimeError("no frames decoded")
    w, h = frames[0].size
    th = int(tile_w * h / w)
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (tile_w * cols, th * rows), "black")
    for i, f in enumerate(frames):
        sheet.paste(f.resize((tile_w, th)), ((i % cols) * tile_w, (i // cols) * th))
    sheet.save(out)
    return Path(out)
