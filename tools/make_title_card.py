#!/usr/bin/env python3
"""Generate the 1280x720 title card for the demo video.

    python tools/make_title_card.py

Writes static/samples/titlecard.png. Uses Pillow, which exists only in the
bundled interpreter (system python has no Pillow). Stdlib + Pillow, no installs.

The card is also the repo's social preview: dark, projector-legible, and it
names the open-weight model so judges can verify it from the video alone.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "samples" / "titlecard.png"
WIDTH, HEIGHT = 1280, 720

BOLD = [
    r"C:\Windows\Fonts\seguibli.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
REGULAR = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

INK = (244, 247, 250)
MUTED = (150, 165, 180)
DIM = (108, 122, 138)
MINT = (110, 231, 183)
AMBER = (251, 191, 36)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for candidate in BOLD if bold else REGULAR:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def background() -> Image.Image:
    """Vertical gradient, darkest at the top; a soft mint glow bottom-right."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (10, 14, 19))
    draw = ImageDraw.Draw(img)
    top, bottom = (9, 13, 18), (18, 26, 34)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        draw.line(
            [(0, y), (WIDTH, y)],
            fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)),
        )
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([WIDTH - 420, HEIGHT - 380, WIDTH + 180, HEIGHT + 220], fill=(110, 231, 183, 18))
    gdraw.ellipse([-260, -260, 320, 260], fill=(251, 191, 36, 8))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    return img.convert("RGB")


def tracked_width(draw: ImageDraw.ImageDraw, text: str, face, tracking: int) -> float:
    return sum(draw.textlength(ch, font=face) for ch in text) + tracking * max(0, len(text) - 1)


def draw_tracked(draw, center_x: float, y: float, text: str, face, fill, tracking: int) -> None:
    x = center_x - tracked_width(draw, text, face, tracking) / 2.0
    for ch in text:
        draw.text((x, y), ch, font=face, fill=fill, anchor="lm")
        x += draw.textlength(ch, font=face) + tracking


def build() -> Image.Image:
    img = background().convert("RGBA")
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    center = WIDTH // 2

    draw_tracked(draw, center, 168, "HACKTOBERFEST HACK DAY  ·  ASTORIA TECH MEETUP",
                 font(15, True), MUTED, 5)
    draw.line([(center - 210, 196), (center + 210, 196)], fill=(60, 74, 88, 255), width=1)

    draw_tracked(draw, center, 300, "ASTORIA LENS", font(104, True), INK, 7)
    draw.line([(center - 84, 356), (center + 84, 356)], fill=(110, 231, 183, 255), width=4)

    draw.text((center, 398), "point at anything. understand it.", font=font(35),
              fill=(206, 216, 226), anchor="mm")

    draw.text((center, 466), "Gemma 4 (open weights) · vision in, plain language out · MIT licensed",
              font=font(21), fill=MUTED, anchor="mm")

    draw.line([(center - 330, 540), (center + 330, 540)], fill=(48, 60, 72, 255), width=1)
    draw.text((center, 578), "Four modes:  Explain  ·  Translate  ·  Read aloud  ·  Ask",
              font=font(22, True), fill=(196, 209, 222), anchor="mm")
    draw.text((center, 616), "Six answer languages  ·  no build step  ·  python server.py",
              font=font(19), fill=DIM, anchor="mm")

    draw.text((center, 664), "Built in one evening at Hacktoberfest Hack Day with the Astoria Tech Meetup",
              font=font(15), fill=DIM, anchor="mm")

    img = Image.alpha_composite(img, layer)
    return img.convert("RGB")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    card = build()
    card.save(OUT, "PNG", optimize=True)
    print("%s  %dx%d  %.0f KB" % (OUT, *card.size, OUT.stat().st_size / 1024.0))


if __name__ == "__main__":
    main()
