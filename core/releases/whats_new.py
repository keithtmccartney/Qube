"""Post-update What's New orchestration."""

from __future__ import annotations

import logging

from core.__version__ import __version__
from core.releases.loader import get_unseen_releases
from core.releases.model import ReleaseManifest
from core.releases.seen_state import ReleaseSeenState, get_release_seen_state

logger = logging.getLogger("Qube.Releases")


def pending_whats_new_manifests(
    *,
    current_version: str | None = None,
    seen_state: ReleaseSeenState | None = None,
) -> list[ReleaseManifest]:
    version = str(current_version or __version__).strip()
    state = seen_state or get_release_seen_state()
    try:
        unseen = get_unseen_releases(
            current_version=version,
            last_seen_version=state.get_last_seen_version(),
        )
    except FileNotFoundError:
        logger.debug("[Releases] bundled release corpus unavailable")
        return []
    except Exception as exc:
        logger.warning("[Releases] could not load unseen releases: %s", exc)
        return []

    if not unseen:
        return []

    # First launch: highlight the running version only (not entire bundled history).
    if state.get_last_seen_version() is None:
        for manifest in reversed(unseen):
            if manifest.version == version:
                return [manifest]
        return [unseen[-1]]

    return unseen


def acknowledge_whats_new(
    *,
    current_version: str | None = None,
    seen_state: ReleaseSeenState | None = None,
) -> None:
    version = str(current_version or __version__).strip()
    if version:
        (seen_state or get_release_seen_state()).mark_seen_up_to(version)
