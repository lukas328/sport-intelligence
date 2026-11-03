"""Writes packages/plans/plans.json from the API's plan catalogue (single source of truth).

Used by the marketing site (prices page) so app and site always show the same plans (addendum 01,
4.13). `--check` fails when the file is out of date (CI).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from handball_api.core.config import Settings
from handball_api.services.plans import GOALKEEPER_ADDON_CHF, PLANS

OUT = Path(__file__).with_name("plans.json")


def build() -> str:
    s = Settings()
    data = {
        "currency": "CHF",
        "annual_months": s.invoice_annual_months,
        "goalkeeper_addon_chf_month": GOALKEEPER_ADDON_CHF,
        "plans": [
            {
                "plan": p.plan.value,
                "price_chf_month": p.price_chf_month,
                "price_chf_year": p.price_chf_month * s.invoice_annual_months,
                "teams": p.teams,
                "matches_per_season": p.matches_per_season,
                "storage_gb": p.storage_gb,
                "analysis": "tracking" in p.features,
                "features": sorted(p.features),
                "trial_days": p.trial_days,
            }
            for p in PLANS.values()
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    text = build()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            sys.exit("packages/plans/plans.json is out of date: run `make plans`")
        return
    OUT.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
