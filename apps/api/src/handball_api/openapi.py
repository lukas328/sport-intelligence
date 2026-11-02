"""Export the OpenAPI schema (used to generate packages/api-client)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from handball_api.main import create_app


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    out.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
