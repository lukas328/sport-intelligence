"""Goal mouths in a single frame from the striped posts (no model, no calibration).

NEGATIVE RESULT, kept for the record: on the 720p Magdeburg broadcast the black/white posts are
2 to 4 px wide and the map below fires at least as strongly on spectators, railings and the mixing
desk as on the posts, so `ball_zone` uses the goal-area paint instead (see README).

Handball posts are 8 cm square bars painted in two contrasting colours in 20 cm bands (rules,
1:1 or 2:1 contrast: red/white, black/white, ...). In a 1280-wide broadcast frame a post is 3 to
8 px wide and 50 to 200 px tall, and nothing else in a hall is a thin vertical bar whose brightness
flips every few pixels along its length (wall ads are wide, lines lie on the floor, people are
wide and not periodic).

1. `post_map`: thin-bar contrast (column against the columns +-w beside it, both sides) times
   alternation along the column (|d/dy| of the column profile), both averaged over a post-long
   vertical window.
2. Peaks of the map are post candidates (x, y_top, y_bottom); two candidates at a similar height
   and length, 1 to 3 post lengths apart, make a goal (3 m wide, 2 m high).

usage (look at it): python ml/goals/goalfind.py frame.png out.png
"""

from __future__ import annotations

import sys

import cv2
import numpy as np

U8 = np.ndarray


def post_map(img: U8, w: int = 4, length: int = 41) -> np.ndarray:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # stripes of any two colours: also use saturation (red/white has little grey contrast at times)
    s = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1].astype(np.float32)
    out = np.zeros_like(g)
    for ch in (g, s):
        col = cv2.blur(ch, (2, 1))
        left = np.roll(col, w, axis=1)
        right = np.roll(col, -w, axis=1)
        # a bar differs from BOTH sides (an edge differs from one side only)
        bar = np.minimum(np.abs(col - left), np.abs(col - right))
        dy = np.abs(np.diff(col, axis=0, prepend=col[:1]))
        alt = cv2.blur(dy, (1, length))
        out = np.maximum(out, cv2.blur(bar, (1, length)) * alt)
    # posts are vertical: penalise the same response in the rows (horizontal structures)
    return out


def find_posts(img: U8, n: int = 12, min_score: float = 30.0) -> list[tuple[float, float, float]]:
    """Post candidates (x, y_centre, score), strongest first."""
    m = post_map(img)
    m[int(0.84 * m.shape[0]):] = 0  # overlay band and bottom edge
    m[:, :8] = 0
    m[:, -8:] = 0
    out = []
    mm = m.copy()
    for _ in range(n):
        y, x = np.unravel_index(mm.argmax(), mm.shape)
        v = float(mm[y, x])
        if v < min_score:
            break
        out.append((float(x), float(y), v))
        mm[max(0, y - 60):y + 60, max(0, x - 12):x + 12] = 0
    return out


def find_goals(img: U8) -> list[tuple[float, float, float, float, float]]:
    """Goal-mouth boxes (x1, y1, x2, y2, score) from pairs of posts."""
    posts = find_posts(img)
    goals = []
    for i, (x1, y1, s1) in enumerate(posts):
        for x2, y2, s2 in posts[i + 1:]:
            dx, dy = abs(x2 - x1), abs(y2 - y1)
            if 30 <= dx <= 260 and dy <= 0.35 * dx + 15:
                xa, xb = min(x1, x2), max(x1, x2)
                h = dx * 0.55
                yc = (y1 + y2) / 2
                goals.append((xa, yc - h * 0.6, xb, yc + h * 0.6, min(s1, s2)))
    goals.sort(key=lambda g: -g[4])
    return goals[:2]


def main() -> None:
    img = cv2.imread(sys.argv[1])
    m = post_map(img)
    vis = img.copy()
    for x, y, v in find_posts(img):
        cv2.circle(vis, (int(x), int(y)), 6, (0, 255, 255), 2)
        cv2.putText(vis, f"{v:.0f}", (int(x) + 6, int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    for g in find_goals(img):
        cv2.rectangle(vis, (int(g[0]), int(g[1])), (int(g[2]), int(g[3])), (0, 0, 255), 2)
    heat = cv2.applyColorMap(np.clip(m / max(m.max(), 1) * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)
    cv2.imwrite(sys.argv[2], np.vstack([vis, heat]))


if __name__ == "__main__":
    main()
