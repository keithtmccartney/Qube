"""Validation for bundled release manifest corpus."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.releases.model import INDEX_SCHEMA, MANIFEST_SCHEMA, RELEASE_CATEGORIES

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_INDEX_REQUIRED = ("schema", "releases")
_MANIFEST_REQUIRED = ("schema", "version", "date", "summary", "changes")
_ITEM_REQUIRED = ("id", "category", "title", "summary")


class ReleaseManifestValidationError(ValueError):
    """Raised when a release manifest or index fails validation."""


def validate_release_index(raw: dict[str, Any], *, label: str = "manifest.json") -> None:
    if raw.get("schema") != INDEX_SCHEMA:
        raise ReleaseManifestValidationError(
            f"{label}: unsupported schema {raw.get('schema')!r} (expected {INDEX_SCHEMA})"
        )
    for key in _INDEX_REQUIRED:
        if key not in raw:
            raise ReleaseManifestValidationError(f"{label}: missing required field {key!r}")

    releases = raw.get("releases")
    if not isinstance(releases, list) or not releases:
        raise ReleaseManifestValidationError(f"{label}: releases must be a non-empty list")

    seen_versions: set[str] = set()
    for idx, entry in enumerate(releases):
        prefix = f"{label}: releases[{idx}]"
        if not isinstance(entry, dict):
            raise ReleaseManifestValidationError(f"{prefix} must be an object")
        version = str(entry.get("version") or "").strip()
        file_name = str(entry.get("file") or "").strip()
        date = str(entry.get("date") or "").strip()
        if not version or not _VERSION_RE.fullmatch(version):
            raise ReleaseManifestValidationError(f"{prefix}: invalid version {version!r}")
        if version in seen_versions:
            raise ReleaseManifestValidationError(f"{label}: duplicate version {version!r}")
        seen_versions.add(version)
        if not file_name or "/" in file_name or "\\" in file_name:
            raise ReleaseManifestValidationError(f"{prefix}: invalid file {file_name!r}")
        if date and not _DATE_RE.fullmatch(date):
            raise ReleaseManifestValidationError(f"{prefix}: invalid date {date!r}")


def validate_release_manifest(raw: dict[str, Any], *, label: str) -> None:
    if raw.get("schema") != MANIFEST_SCHEMA:
        raise ReleaseManifestValidationError(
            f"{label}: unsupported schema {raw.get('schema')!r} (expected {MANIFEST_SCHEMA})"
        )
    for key in _MANIFEST_REQUIRED:
        if key not in raw:
            raise ReleaseManifestValidationError(f"{label}: missing required field {key!r}")

    version = str(raw.get("version") or "").strip()
    if not _VERSION_RE.fullmatch(version):
        raise ReleaseManifestValidationError(f"{label}: invalid version {version!r}")

    date = str(raw.get("date") or "").strip()
    if not _DATE_RE.fullmatch(date):
        raise ReleaseManifestValidationError(f"{label}: invalid date {date!r}")

    summary = str(raw.get("summary") or "").strip()
    if not summary:
        raise ReleaseManifestValidationError(f"{label}: summary must be non-empty")

    changes = raw.get("changes")
    if not isinstance(changes, list) or not changes:
        raise ReleaseManifestValidationError(f"{label}: changes must be a non-empty list")

    item_ids: set[str] = set()
    for idx, item in enumerate(changes):
        prefix = f"{label}: changes[{idx}]"
        if not isinstance(item, dict):
            raise ReleaseManifestValidationError(f"{prefix} must be an object")
        for key in _ITEM_REQUIRED:
            if key not in item:
                raise ReleaseManifestValidationError(f"{prefix}: missing required field {key!r}")
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            raise ReleaseManifestValidationError(f"{prefix}: id must be non-empty")
        if item_id in item_ids:
            raise ReleaseManifestValidationError(f"{label}: duplicate change id {item_id!r}")
        item_ids.add(item_id)
        category = str(item.get("category") or "").strip().lower()
        if category not in RELEASE_CATEGORIES:
            raise ReleaseManifestValidationError(
                f"{prefix}: invalid category {category!r} (expected one of {sorted(RELEASE_CATEGORIES)})"
            )
        if not str(item.get("title") or "").strip():
            raise ReleaseManifestValidationError(f"{prefix}: title must be non-empty")
        if not str(item.get("summary") or "").strip():
            raise ReleaseManifestValidationError(f"{prefix}: summary must be non-empty")


def validate_release_corpus(releases_dir: Path) -> None:
    index_path = releases_dir / "manifest.json"
    if not index_path.is_file():
        raise ReleaseManifestValidationError(f"release index not found: {index_path}")

    import json

    index_raw = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(index_raw, dict):
        raise ReleaseManifestValidationError("manifest.json root must be a JSON object")
    validate_release_index(index_raw, label="manifest.json")

    for entry in index_raw["releases"]:
        assert isinstance(entry, dict)
        version = str(entry["version"])
        file_name = str(entry["file"])
        manifest_path = releases_dir / file_name
        label = file_name
        if not manifest_path.is_file():
            raise ReleaseManifestValidationError(f"missing release file for {version}: {file_name}")
        manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest_raw, dict):
            raise ReleaseManifestValidationError(f"{label}: root must be a JSON object")
        validate_release_manifest(manifest_raw, label=label)
        if str(manifest_raw.get("version")) != version:
            raise ReleaseManifestValidationError(
                f"{label}: version mismatch index={version!r} file={manifest_raw.get('version')!r}"
            )
        index_date = str(entry.get("date") or "").strip()
        file_date = str(manifest_raw.get("date") or "").strip()
        if index_date and file_date and index_date != file_date:
            raise ReleaseManifestValidationError(
                f"{label}: date mismatch index={index_date!r} file={file_date!r}"
            )
