"""Regenerate binary fixtures: uv run python tests/fixtures/make_fixtures.py"""
from pathlib import Path

import docx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

D = Path(__file__).parent / "input"
d = docx.Document()
d.add_paragraph("Newton's first law: a body stays at rest or in uniform motion unless acted on by a net force.")
d.save(D / "doc.docx")
p = Presentation()
s = p.slides.add_slide(p.slide_layouts[6])
s.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(1)).text_frame.text = "Photosynthesis turns light into chemical energy."
p.save(D / "deck.pptx")
fig = plt.figure(figsize=(6, 2))
fig.text(0.1, 0.5, "Ohm's law: V = I R")
fig.savefig(D / "paper.pdf")
Image.new("RGB", (200, 100), "white").save(D / "shot.png")
