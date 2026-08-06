"""Render release manifests as user-facing Markdown."""

from __future__ import annotations

from core.releases.model import RELEASE_CATEGORIES, ReleaseChangeItem, ReleaseManifest
from core.releases.query import filter_manifest_changes

CATEGORY_ORDER: tuple[str, ...] = (
    "breaking",
    "migration",
    "new",
    "improved",
    "fixed",
    "deprecated",
)

CATEGORY_HEADINGS: dict[str, str] = {
    "breaking": "Breaking changes",
    "migration": "Migration",
    "new": "New",
    "improved": "Improved",
    "fixed": "Fixed",
    "deprecated": "Deprecated",
}


def category_heading(category: str) -> str:
    return CATEGORY_HEADINGS.get(category, category.replace("_", " ").title())


def _escape_md_inline(text: str) -> str:
    return str(text or "").replace("`", "\\`")


def render_change_item_markdown(
    item: ReleaseChangeItem,
    *,
    include_details: bool = False,
) -> str:
    lines: list[str] = []
    lines.append(f"### {_escape_md_inline(item.title)}")
    lines.append("")
    lines.append(item.summary.strip())
    if item.user_impact:
        lines.append("")
        for bullet in item.user_impact:
            lines.append(f"- {bullet}")
    if include_details:
        if item.capabilities_affected:
            lines.append("")
            lines.append(
                "**Capabilities:** "
                + ", ".join(f"`{cap}`" for cap in item.capabilities_affected)
            )
        if item.developer_notes:
            lines.append("")
            lines.append("**Developer notes:**")
            for note in item.developer_notes:
                lines.append(f"- `{note}`")
        prov = item.provenance
        prov_bits: list[str] = []
        if prov.pull_requests:
            prov_bits.append("PRs: " + ", ".join(prov.pull_requests))
        if prov.commits:
            prov_bits.append("Commits: " + ", ".join(prov.commits))
        if prov.ado_work_items:
            prov_bits.append("ADO: " + ", ".join(f"#{wid}" for wid in prov.ado_work_items))
        if item.ado_feature_ids:
            prov_bits.append(
                "Features: " + ", ".join(f"#{fid}" for fid in item.ado_feature_ids)
            )
        if prov_bits:
            lines.append("")
            lines.append("*" + " · ".join(prov_bits) + "*")
        if item.migration:
            lines.append("")
            lines.append(f"**Migration:** {item.migration}")
    lines.append("")
    return "\n".join(lines)


def render_release_markdown(
    manifest: ReleaseManifest,
    *,
    query: str = "",
    category: str | None = None,
    include_details: bool = False,
) -> str:
    lines: list[str] = [
        f"# Qube {manifest.version}",
        "",
        f"*{manifest.date}*",
        "",
        manifest.summary.strip(),
        "",
    ]
    items = filter_manifest_changes(manifest, query=query, category=category)
    if not items:
        lines.append("_No changes match the current filters._")
        lines.append("")
        return "\n".join(lines)

    grouped: dict[str, list[ReleaseChangeItem]] = {cat: [] for cat in CATEGORY_ORDER}
    for item in items:
        grouped.setdefault(item.category, []).append(item)

    for cat in CATEGORY_ORDER:
        bucket = grouped.get(cat) or []
        if not bucket:
            continue
        lines.append(f"## {category_heading(cat)}")
        lines.append("")
        for item in bucket:
            lines.append(render_change_item_markdown(item, include_details=include_details))
    return "\n".join(lines).strip() + "\n"


def render_releases_markdown(
    manifests: list[ReleaseManifest],
    *,
    query: str = "",
    category: str | None = None,
    include_details: bool = False,
) -> str:
    if not manifests:
        return "_No release notes are available._\n"
    parts = [
        render_release_markdown(
            manifest,
            query=query,
            category=category,
            include_details=include_details,
        )
        for manifest in manifests
    ]
    return "\n---\n\n".join(parts).strip() + "\n"


def build_latest_release_help_markdown(
    manifest: ReleaseManifest | None = None,
) -> str:
    """Markdown for @help — latest app release user_impact summary."""
    if manifest is None:
        from core.releases.loader import load_release_corpus

        corpus = load_release_corpus()
        manifest = corpus[0] if corpus else None
    if manifest is None:
        return (
            "# What's new in Qube\n\n"
            "Open **Settings → About → Version history** to browse release notes.\n"
        )

    lines = [
        f"# What's new in Qube {manifest.version}",
        "",
        "## Common questions",
        "",
        "- What's new in Qube?",
        "- What changed in the latest Qube update?",
        "- Where do I see version history?",
        "",
        manifest.summary.strip(),
        "",
        "## Highlights",
        "",
    ]
    for item in manifest.changes:
        if not item.user_impact and item.category not in {"new", "improved"}:
            continue
        lines.append(f"### {item.title}")
        lines.append("")
        lines.append(item.summary.strip())
        for bullet in item.user_impact:
            lines.append(f"- {bullet}")
        lines.append("")

    lines.extend(
        [
            "## Where to find it",
            "",
            "Open **Settings → About → Version history** for the full searchable changelog.",
            "",
            "## Also called",
            "",
            "app release notes, version history, what's new in qube, qube changelog",
        ]
    )
    return "\n".join(lines).strip() + "\n"
