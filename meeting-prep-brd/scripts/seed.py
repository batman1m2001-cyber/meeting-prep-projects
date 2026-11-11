"""Create the `brd` schema and its seed rows (src/stores/seed.py). Idempotent.

    uv run python scripts/seed.py            create what is missing, upsert the seed rows
    uv run python scripts/seed.py --reset    drop the `brd` schema first (never `public`)

Needs PREP_DB_URL set explicitly: the world's default port belongs to another database.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stores.seed import seed  # noqa: E402


def main() -> int:
    if not os.environ.get("PREP_DB_URL"):
        print("set PREP_DB_URL (e.g. postgresql://prep:prep@127.0.0.1:5434/prep)", file=sys.stderr)
        return 2
    print(json.dumps(seed(reset="--reset" in sys.argv[1:])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
