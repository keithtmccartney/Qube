"""Filter and search helpers for release manifests."""

from __future__ import annotations

from core.releases.model import RELEASE_CATEGORIES, ReleaseChangeItem, ReleaseManifest


def normalize_category(category: str | None) -> str | None:
    if category is None:
        return None
    value = str(category or "").strip().lower()
    if not value or value == "all":
        return None
    if value not in RELEASE_CATEGORIES:
        return None
    return value


def filter_change_items(
    items: tuple[ReleaseChangeItem, ...],
    *,
    query: str = "",
    category: str | None = None,
) -> list[ReleaseChangeItem]:
    needle = str(query or "").strip().lower()
    cat = normalize_category(category)
    out: list[ReleaseChangeItem] = []
    for item in items:
        if cat and item.category != cat:
            continue
        if needle and not _item_matches_query(item, needle):
            continue
        out.append(item)
    return out


def _item_matches_query(item: ReleaseChangeItem, needle: str) -> bool:
    parts = [
        item.title,
        item.summary,
        item.category,
        " ".join(item.user_impact),
        " ".join(item.capabilities_affected),
        " ".join(item.developer_notes),
    ]
    haystack = " ".join(parts).lower()
    return needle in haystack


def filter_manifest_changes(
    manifest: ReleaseManifest,
    *,
    query: str = "",
    category: str | None = None,
) -> list[ReleaseChangeItem]:
    return filter_change_items(manifest.changes, query=query, category=category)


def search_release_corpus(
    manifests: list[ReleaseManifest],
    *,
    query: str = "",
    category: str | None = None,
) -> list[tuple[ReleaseManifest, list[ReleaseChangeItem]]]:
    results: list[tuple[ReleaseManifest, list[ReleaseChangeItem]]] = []
    for manifest in manifests:
        matches = filter_manifest_changes(manifest, query=query, category=category)
        if matches:
            results.append((manifest, matches))
    return results
