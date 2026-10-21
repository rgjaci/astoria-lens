"""Generate the demo-safe sample photos: a Greek deli menu and a community flyer.

    python tools/make_samples.py

Uses Pillow when available. These images exist so the live demo has a guaranteed
input even if nobody brought a good photo - and so `python server.py` can be
tested end to end without a camera.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "samples"

REGULAR = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
BOLD = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for candidate in BOLD if bold else REGULAR:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def paper(base: tuple[int, int, int], size: tuple[int, int], warmth: int = 6) -> Image.Image:
    img = Image.new("RGB", size, base)
    rng = random.Random(7)
    pixels = img.load()
    width, height = size
    for y in range(height):
        for x in range(0, width, 2):
            jitter = rng.randint(-warmth, warmth)
            r, g, b = pixels[x, y]
            pixels[x, y] = (max(0, min(255, r + jitter)), max(0, min(255, g + jitter)), max(0, min(255, b + jitter)))
    return img


def photograph(img: Image.Image, angle: float) -> Image.Image:
    """Cheap realism: a slight tilt, sitting on a tabletop."""
    tabletop = (208, 202, 191)
    rotated = img.rotate(angle, expand=True, fillcolor=tabletop, resample=Image.BICUBIC)
    frame = Image.new("RGB", (rotated.width + 36, rotated.height + 36), tabletop)
    frame.paste(rotated, (18, 18))
    return frame


def draw_menu() -> Image.Image:
    img = paper((248, 243, 231), (900, 1200))
    draw = ImageDraw.Draw(img)
    draw.rectangle([28, 28, 872, 1172], outline=(120, 96, 62), width=3)
    draw.rectangle([40, 40, 860, 1160], outline=(196, 178, 150), width=1)

    ink = (52, 40, 28)
    red = (140, 42, 32)

    draw.text((450, 130), "ΤΑΒΕΡΝΑ ΑΣΤΟΡΙΑ", font=font(52, True), fill=ink, anchor="mm")
    draw.text((450, 188), "Από το 1979 · 31-05 30th Avenue, Astoria", font=font(23), fill=(96, 82, 66), anchor="mm")
    draw.line([(110, 228), (790, 228)], fill=(150, 130, 104), width=2)
    draw.text((450, 272), "Φ Α Γ Η Τ Ο", font=font(26, True), fill=red, anchor="mm")

    items = [
        ("ΣΟΥΒΛΑΚΙ ΧΟΙΡΙΝΟ", "5.50"),
        ("ΝΤΟΛΜΑΔΕΣ", "4.25"),
        ("ΧΩΡΙΑΤΙΚΗ ΣΑΛΑΤΑ", "6.75"),
        ("ΑΡΝΙ ΚΛΕΦΤΙΚΟ", "12.00"),
        ("ΓΑΛΟΠΟΥΛΑ ΣΤΟ ΦΟΥΡΝΟ", "14.50"),
        ("ΣΠΑΝΑΚΟΠΙΤΑ", "4.00"),
        ("ΦΑΚΕΣ", "5.25"),
        ("ΜΠΑΚΛΑΒΑΣ", "3.75"),
    ]
    y = 340
    for name, price in items:
        name_font = font(29)
        price_font = font(29, True)
        draw.text((110, y), name, font=name_font, fill=ink)
        name_box = draw.textbbox((110, y), name, font=name_font)
        price_box = draw.textbbox((0, 0), price, font=price_font)
        price_x = 790 - price_box[2]
        draw.text((price_x, y), price, font=price_font, fill=ink)
        line_y = (name_box[3] + name_box[1]) // 2 + 6
        x = name_box[2] + 14
        while x < price_x - 12:
            draw.line([(x, line_y), (min(x + 3, price_x - 12), line_y)], fill=(176, 158, 132), width=2)
            x += 9
        y += 62

    draw.line([(110, 880), (790, 880)], fill=(150, 130, 104), width=2)
    draw.text((450, 930), "Παραγγελίες στο ταμείο", font=font(27, True), fill=ink, anchor="mm")
    draw.text((450, 986), "Cash only under $10 · Αλλεργίες; Ρωτήστε μας", font=font(21), fill=(110, 92, 70), anchor="mm")
    draw.text((450, 1100), "ΕΥΧΑΡΙΣΤΟΥΜΕ · THANK YOU", font=font(18), fill=(150, 128, 100), anchor="mm")
    return photograph(img, 1.6)


def draw_flyer() -> Image.Image:
    img = paper((252, 251, 247), (900, 1200), warmth=4)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 900, 168], fill=(20, 74, 120))
    draw.text((450, 62), "ASTORIA COMMUNITY HEALTH DAY", font=font(33, True), fill=(255, 255, 255), anchor="mm")
    draw.text((450, 116), "FREE • ALL AGES • NO APPOINTMENT NEEDED", font=font(19), fill=(184, 216, 240), anchor="mm")

    ink = (24, 32, 44)
    draw.text((450, 250), "FREE FLU SHOTS &", font=font(44, True), fill=ink, anchor="mm")
    draw.text((450, 306), "HEALTH SCREENINGS", font=font(44, True), fill=ink, anchor="mm")

    draw.rectangle([150, 356, 750, 452], fill=(232, 242, 250), outline=(20, 74, 120), width=3)
    draw.text((450, 390), "SATURDAY, OCTOBER 25", font=font(31, True), fill=(20, 74, 120), anchor="mm")
    draw.text((450, 428), "10:00 AM – 2:00 PM", font=font(24), fill=(46, 66, 88), anchor="mm")

    draw.text((450, 510), "Astoria Community Center", font=font(30, True), fill=ink, anchor="mm")
    draw.text((450, 552), "31-05 30th Avenue, Astoria, NY 11106", font=font(24), fill=(70, 82, 96), anchor="mm")

    bullets = [
        "Bring a photo ID",
        "No insurance required",
        "Walk-ins welcome",
        "Interpreters available: Ελληνικά · Español · English",
    ]
    y = 630
    for line in bullets:
        draw.ellipse([150, y + 8, 166, y + 24], fill=(20, 74, 120))
        draw.text((184, y), line, font=font(24), fill=ink)
        y += 50

    draw.rectangle([110, 880, 790, 1010], fill=(255, 244, 214), outline=(212, 160, 40), width=2)
    draw.text((450, 916), "REGISTRATION CLOSES", font=font(20, True), fill=(146, 98, 10), anchor="mm")
    draw.text((450, 956), "FRIDAY, OCTOBER 23 AT 6:00 PM", font=font(27, True), fill=(120, 78, 6), anchor="mm")
    draw.text((450, 990), "Call 718-555-0142 to reserve a spot", font=font(21), fill=(120, 78, 6), anchor="mm")

    draw.line([(110, 1060), (790, 1060)], fill=(200, 206, 214), width=2)
    draw.text((450, 1096), "Sponsored by Astoria Community Health Partners", font=font(18), fill=(96, 108, 122), anchor="mm")
    draw.text((450, 1128), "astoriahealth.org · 718-555-0142", font=font(17), fill=(96, 108, 122), anchor="mm")
    return photograph(img, -1.2)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    menu = draw_menu()
    menu.save(OUT / "menu.png")
    flyer = draw_flyer()
    flyer.save(OUT / "flyer.png")
    for name in ("menu.png", "flyer.png"):
        path = OUT / name
        print("%s  %dx%d  %.0f KB" % (path, *Image.open(path).size, path.stat().st_size / 1024))


if __name__ == "__main__":
    main()
