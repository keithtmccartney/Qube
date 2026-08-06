#!/usr/bin/env python3
"""Validate bundled release manifests under assets/releases/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.releases.loader import bundled_releases_dir, clear_release_loader_cache
from core.releases.validate import ReleaseManifestValidationError, validate_release_corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--releases-dir",
        type=Path,
        default=None,
        help="Override bundled releases directory (default: assets/releases)",
    )
    args = parser.parse_args(argv)
    releases_dir = args.releases_dir or bundled_releases_dir()
    clear_release_loader_cache()
    try:
        validate_release_corpus(releases_dir)
    except ReleaseManifestValidationError as exc:
        print(f"release manifest validation failed: {exc}", file=sys.stderr)
        return 1
    import json

    index = json.loads((releases_dir / "manifest.json").read_text(encoding="utf-8"))
    n = len(index.get("releases") or [])
    print(f"OK: validated {n} release manifest(s) in {releases_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
