"""Kit colour comparison (addendum 01, 4.8): warn when two kits are hard to tell apart.

Distance is CIE76 delta E in CIELAB (D65). Below ~25 colours look alike on typical hall video
(compressed, mixed lighting); the same threshold is used in the web form (packages/court).
"""

from __future__ import annotations

SIMILAR_DELTA_E = 25.0

KIT_PAIRS = (
    ("own", "opponent"),
    ("own", "opponent_gk"),
    ("own_gk", "opponent"),
    ("own", "own_gk"),
    ("opponent", "opponent_gk"),
)


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _f(t: float) -> float:
    return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29


def hex_to_lab(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    r, g, b = (_lin(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    fx, fy, fz = _f(x), _f(y), _f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: str, b: str) -> float:
    la, lb = hex_to_lab(a), hex_to_lab(b)
    return float(sum((p - q) ** 2 for p, q in zip(la, lb, strict=True)) ** 0.5)


def kit_warnings(kits: dict[str, str]) -> list[str]:
    """Pairs like "own/opponent" whose colours are too similar."""
    return [
        f"{a}/{b}"
        for a, b in KIT_PAIRS
        if a in kits and b in kits and delta_e(kits[a], kits[b]) < SIMILAR_DELTA_E
    ]
