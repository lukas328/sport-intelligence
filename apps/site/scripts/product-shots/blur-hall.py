"""Blur a hall frame until only «a hall, a match» is left (BEFUNDE-2 L8): no person, face, shirt
number, text, logo or scoreboard can be recognised.

How assets/halle.webp and public/media/halle.webp were made: one frame (second 80) of a test clip
of a real match, a wide view across the court, taken with ffmpeg into a temporary folder (never into
the repository), then

    python3 apps/site/scripts/product-shots/blur-hall.py frame.png blurred.png 960

The frame is shrunk to a grid of 40 x 22 cells (one cell is 32 x 32 px of a 1280 x 720 frame, a
player is one or two cells, a face or a number a fraction of one), blown up smoothly and blurred
again. Look at the result before using it. Never commit the unblurred frame.
"""

import sys

from PIL import Image, ImageEnhance, ImageFilter

src, out, w = sys.argv[1], sys.argv[2], int(sys.argv[3])
im = Image.open(src).convert("RGB")
tiny = im.resize((40, 22), Image.BOX)
tiny = tiny.filter(ImageFilter.GaussianBlur(0.6))
h = round(w * 9 / 16)
big = tiny.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(w / 90))
big = ImageEnhance.Contrast(big).enhance(1.3)
big = ImageEnhance.Brightness(big).enhance(0.9)
big = ImageEnhance.Color(big).enhance(1.15)
big.save(out, quality=82)
