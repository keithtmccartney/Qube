"""Load and query the bundled release manifest corpus."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.help_corpus_manifest import parse_version
from core.paths import resource_path
from core.releases.model import ReleaseManifest
from core.releases.validate import ReleaseManifestValidationError, validate_release_corpus

logger = logging.getLogger("Qube.Releases")


def bundled_releases_dir() -> Path:
    return resource_path("assets", "releases")


def load_release_index(*, releases_dir: Path | None = None) -> dict[str, Any]:
    root = releases_dir or bundled_releases_dir()
    index_path = root / "manifest.json"
    if not index_path.is_file():
        raise FileNotFoundError(f"release index not found: {index_path}")
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("release index root must be a JSON object")
    return data


def _manifest_path_for_version(
    version: str,
    *,
    releases_dir: Path,
    index: dict[str, Any] | None = None,
) -> Path:
    idx = index if index is not None else load_release_index(releases_dir=releases_dir)
    for entry in idx.get("releases") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("version") or "").strip() == version:
            file_name = str(entry.get("file") or "").strip()
            if file_name:
                return releases_dir / file_name
    raise FileNotFoundError(f"no release manifest registered for version {version!r}")


def get_release_manifest(
    version: str,
    *,
    releases_dir: Path | None = None,
) -> ReleaseManifest:
    root = releases_dir or bundled_releases_dir()
    path = _manifest_path_for_version(version, releases_dir=root)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name}: root must be a JSON object")
    return ReleaseManifest.from_dict(raw)


def list_release_versions(*, releases_dir: Path | None = None) -> list[str]:
    index = load_release_index(releases_dir=releases_dir)
    versions: list[str] = []
    for entry in index.get("releases") or []:
        if isinstance(entry, dict):
            version = str(entry.get("version") or "").strip()
            if version:
                versions.append(version)
    return sorted(versions, key=parse_version, reverse=True)


def load_release_corpus(*, releases_dir: Path | None = None) -> list[ReleaseManifest]:
    root = releases_dir or bundled_releases_dir()
    manifests: list[ReleaseManifest] = []
    for version in list_release_versions(releases_dir=root):
        try:
            manifests.append(get_release_manifest(version, releases_dir=root))
        except Exception as exc:
            logger.warning("[Releases] skip %s: %s", version, exc)
    return manifests


def get_unseen_releases(
    *,
    current_version: str,
    last_seen_version: str | None,
    releases_dir: Path | None = None,
) -> list[ReleaseManifest]:
    """Return releases newer than last_seen up to and including current_version."""
    root = releases_dir or bundled_releases_dir()
    current = str(current_version or "").strip()
    last_seen = str(last_seen_version or "").strip() or None
    unseen: list[ReleaseManifest] = []
    for version in list_release_versions(releases_dir=root):
        if parse_version(version) > parse_version(current):
            continue
        if last_seen and parse_version(version) <= parse_version(last_seen):
            continue
        unseen.append(get_release_manifest(version, releases_dir=root))
    unseen.sort(key=lambda m: parse_version(m.version))
    return unseen


@lru_cache(maxsize=1)
def _validated_corpus_cached(releases_dir_str: str) -> tuple[ReleaseManifest, ...]:
    root = Path(releases_dir_str)
    validate_release_corpus(root)
    return tuple(load_release_corpus(releases_dir=root))


def load_validated_release_corpus(*, releases_dir: Path | None = None) -> list[ReleaseManifest]:
    root = releases_dir or bundled_releases_dir()
    try:
        return list(_validated_corpus_cached(str(root.resolve())))
    except ReleaseManifestValidationError:
        raise
    except Exception as exc:
        raise ReleaseManifestValidationError(str(exc)) from exc


def clear_release_loader_cache() -> None:
    _validated_corpus_cached.cache_clear()
