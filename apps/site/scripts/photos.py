"""The hall photos of the site (BEFUNDE-4 U48, src/components/hall-photo.tsx).

    python3 scripts/photos.py <folder with the originals>

Originals (free stock, Unsplash/Pexels licence, picked by the owner on 18.11.2026; kept outside
the repo): tor-ball.jpg (ball in front of an empty goal), sprungwurf.jpg (jump shot, red #14).
Writes WebP in the widths HallPhoto lists to public/media, metadata stripped.
"""

import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "public" / "media"
# name: (crop box on the original or None, [(width, quality)])
PHOTOS = {
    "tor-ball": (None, [(900, 62), (1400, 60), (2000, 55)]),
    "sprungwurf": ((260, 20, 1560, 1120), [(600, 66), (900, 64), (1300, 62)]),
}


def main(src: Path) -> None:
    for name, (box, widths) in PHOTOS.items():
        im = Image.open(src / f"{name}.jpg").convert("RGB")
        if box:
            im = im.crop(box)
        for w, q in widths:
            out = OUT / f"{name}-{w}.webp"
            small = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            small.save(out, quality=q, method=6)
            print(out.name, out.stat().st_size)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
