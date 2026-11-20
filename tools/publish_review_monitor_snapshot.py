"""Publish the crawler's validated monitor feed without changing its provenance."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import tempfile


def publish_snapshot(source: Path, output: Path) -> dict:
    payload = (source / "reviews" / "monitor-data.json").read_bytes()
    snapshot = json.loads(payload)
    if not isinstance(snapshot, dict):
        raise ValueError("Monitor snapshot must be an object")
    generated_at = datetime.fromisoformat(snapshot.get("generated_at", "").replace("Z", "+00:00"))
    if generated_at.tzinfo is None:
        raise ValueError("Monitor snapshot generated_at must include a time zone")
    if not re.fullmatch(r"[0-9a-f]{40}", snapshot.get("commit", "")):
        raise ValueError("Monitor snapshot must identify its source commit")
    years = snapshot.get("years")
    if not isinstance(years, list) or not years:
        raise ValueError("Monitor snapshot must contain year records")
    seen = set()
    for year in years:
        if not isinstance(year, dict) or not isinstance(year.get("year"), int):
            raise ValueError("Invalid monitor year record")
        if year["year"] in seen or not isinstance(year.get("sources"), list):
            raise ValueError("Duplicate year or missing source list")
        if not all(isinstance(item, dict) for item in year["sources"]):
            raise ValueError("Invalid monitor source record")
        seen.add(year["year"])

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/review-monitor.json"))
    args = parser.parse_args()
    try:
        snapshot = publish_snapshot(args.source, args.output)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        parser.error(str(error))
    print(f"Published crawler monitor {snapshot['commit']} generated {snapshot['generated_at']}")


if __name__ == "__main__":
    main()
