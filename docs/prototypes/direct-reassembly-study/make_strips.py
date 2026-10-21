"""Combine verify.py's stage captures into compact review strips (needs Pillow)."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


CAPTURES = Path(__file__).resolve().parent / "captures"
STEPS = (
    ("00-assembled", "Assembled"),
    ("01-open", "Open"),
    ("02-lifted", "Lifted"),
    ("05-approach-50", "Approach"),
    ("07-at-slot", "At slot"),
    ("08-seating", "Seating"),
    ("09-complete", "Completed"),
)
font = ImageFont.load_default(size=21)

for mode in ("flat", "relief"):
    for width in (390, 320):
        strip = Image.new("RGB", (1440, 780), "white")
        draw = ImageDraw.Draw(strip)
        for index, (slug, label) in enumerate(STEPS):
            frame = Image.open(CAPTURES / f"{mode}-{width}-{slug}-stage.png").convert("RGB")
            frame = frame.resize((360, 360), Image.Resampling.LANCZOS)
            x, y = (index % 4) * 360, (index // 4) * 390
            draw.text((x + 12, y + 2), label, fill="#19383b", font=font)
            strip.paste(frame, (x, y + 30))
        strip.save(CAPTURES / f"{mode}-{width}-sequence.png", optimize=True)
