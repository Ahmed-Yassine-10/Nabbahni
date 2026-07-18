"""Export the OpenAPI spec to docs/api/openapi.json."""
from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def main() -> None:
    spec = app.openapi()
    out = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OpenAPI spec written to {out}")


if __name__ == "__main__":
    main()
