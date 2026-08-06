"""Persist which release version the user has already seen (What's New gate)."""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from core.help_corpus_manifest import parse_version, version_at_least
from core.paths import user_data_root

logger = logging.getLogger("Qube.Releases")


def default_release_seen_path() -> Path:
    return user_data_root() / "release_seen.json"


class ReleaseSeenState:
    """Tracks the newest release manifest version the user has acknowledged."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_release_seen_path()
        self._lock = threading.RLock()
        self._last_seen_version: str | None = None
        self._updated_at: str | None = None
        self._load()

    def _load(self) -> None:
        with self._lock:
            if not self.path.is_file():
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("[Releases] seen_state load failed: %s", exc)
                return
            if not isinstance(raw, dict):
                return
            version = str(raw.get("last_seen_version") or "").strip()
            self._last_seen_version = version or None
            updated = str(raw.get("updated_at") or "").strip()
            self._updated_at = updated or None

    def _save(self) -> None:
        payload: dict[str, Any] = {}
        if self._last_seen_version:
            payload["last_seen_version"] = self._last_seen_version
        if self._updated_at:
            payload["updated_at"] = self._updated_at
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def get_last_seen_version(self) -> str | None:
        with self._lock:
            return self._last_seen_version

    def mark_seen(self, version: str) -> None:
        version = str(version or "").strip()
        if not version:
            return
        with self._lock:
            if self._last_seen_version and version_at_least(
                self._last_seen_version, version
            ):
                return
            self._last_seen_version = version
            self._updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._save()

    def mark_seen_up_to(self, version: str) -> None:
        """Record that the user has seen this version and all older bundled releases."""
        self.mark_seen(version)

    def should_show_version(self, version: str, *, current_app_version: str) -> bool:
        if parse_version(version) > parse_version(current_app_version):
            return False
        last_seen = self.get_last_seen_version()
        if not last_seen:
            return True
        return parse_version(version) > parse_version(last_seen)


_store: ReleaseSeenState | None = None
_store_lock = threading.Lock()


def get_release_seen_state() -> ReleaseSeenState:
    global _store
    with _store_lock:
        if _store is None:
            _store = ReleaseSeenState()
        return _store


def reset_release_seen_state_for_tests() -> None:
    global _store
    with _store_lock:
        _store = None
