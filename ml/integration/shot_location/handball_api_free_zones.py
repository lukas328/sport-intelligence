"""zone_at of handball_api.services.shot_positions, copied without the API's imports."""

from handball_court.zones import shot_zone, spec

GRAPHIC_ZONE = {
    "wing_left": "la",
    "back_left": "rl",
    "half_left": "rl",
    "back_centre": "rm",
    "half_centre": "rm",
    "back_right": "rr",
    "half_right": "rr",
    "wing_right": "ra",
    "circle_left": "kr",
    "circle_centre": "kr",
    "circle_right": "kr",
}


def zone(x, y):
    z = shot_zone(x, y)
    if z == "long_range":
        dy = y - 10.0
        z = (
            "back_centre"
            if abs(dy) < spec()["centre_half_width_m"]["back"]
            else ("back_left" if dy > 0 else "back_right")
        )
    return GRAPHIC_ZONE.get(z, "rm")
