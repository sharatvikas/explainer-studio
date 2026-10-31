"""Read any source folder into work/sources.json — text formats by code, images listed for Claude."""
import csv
import json
import re
from pathlib import Path

IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
TEXT = {".md", ".txt", ".pdf", ".docx", ".pptx"}
SPLIT = r"(?m)^(?=#{1,3}\s|Q\s*\d+[.)]|Question\s*\d*[:.])"
HEAD = re.compile(r"^(#{1,3}\s+)?(Q\s*\d+[.)]|Question\s*\d*[:.])?\s*", re.I)
FIELD = re.compile(r"\s*\**\s*(Answer|Solution|Source|Title|Notes)\s*:?\s*\**\s*:?\s*(.*)", re.I)


def split_markdown(text: str) -> list[dict]:
    items = []
    for block in (b for b in re.split(SPLIT, text) if b.strip()):
        item, body = {}, []
        for line in block.strip().splitlines():
            m = FIELD.match(line)
            if m:
                item[m.group(1).lower()] = m.group(2).strip()
            else:
                body.append(line)
        q = HEAD.sub("", "\n".join(body).strip(), count=1).strip()
        if q or item:
            item["question"] = q
            items.append(item)
    return items


def _rows(rows) -> list[dict]:
    out = []
    for r in rows:
        r = {str(k).strip().lower(): (str(v).strip() if v is not None else "") for k, v in r.items()}
        if r.get("question") or r.get("title"):
            out.append({k: v for k, v in r.items() if v})
    return out


def _text(path: Path) -> str:
    s = path.suffix.lower()
    if s == ".pdf":
        from pypdf import PdfReader

        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    if s == ".docx":
        import docx

        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    if s == ".pptx":
        from pptx import Presentation

        return "\n".join(sh.text_frame.text for sl in Presentation(path).slides for sh in sl.shapes if sh.has_text_frame)
    return path.read_text(encoding="utf-8", errors="replace")


def ingest(folder: Path) -> dict:
    folder = Path(folder)
    res = {"folder": str(folder), "files": [], "images": [], "skipped": []}
    for p in sorted(x for x in folder.rglob("*") if x.is_file() and not x.name.startswith(".")):
        s = p.suffix.lower()
        try:
            if s in IMAGES:
                res["images"].append(str(p))
                res["files"].append({"path": str(p), "kind": "image"})
            elif s == ".json":
                data = json.loads(p.read_text(encoding="utf-8"))
                rows = data if isinstance(data, list) else data.get("items", [])
                res["files"].append({"path": str(p), "kind": "table", "items": _rows(rows)})
            elif s == ".csv":
                with p.open(encoding="utf-8-sig", newline="") as f:
                    res["files"].append({"path": str(p), "kind": "table", "items": _rows(csv.DictReader(f))})
            elif s in TEXT:
                text = _text(p)
                entry = {"path": str(p), "kind": "text", "text": text}
                if s in {".md", ".txt"}:
                    items = split_markdown(text)
                    if len(items) > 1 or (items and "answer" in items[0]):
                        entry["items"] = items
                res["files"].append(entry)
            else:
                res["skipped"].append(str(p))
        except Exception as e:  # one bad file never stops the batch
            res["skipped"].append(f"{p} ({type(e).__name__}: {e})")
    return res
