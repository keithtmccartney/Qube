"""Structured release manifest types (single source for multi-audience changelog views)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MANIFEST_SCHEMA = "qube.release_manifest.v1"
INDEX_SCHEMA = "qube.release_index.v1"

RELEASE_CATEGORIES = frozenset(
    {"new", "improved", "fixed", "deprecated", "breaking", "migration"}
)


@dataclass(frozen=True)
class ReleaseProvenance:
    commits: tuple[str, ...] = ()
    pull_requests: tuple[str, ...] = ()
    ado_work_items: tuple[int, ...] = ()

    @classmethod
    def from_dict(cls, raw: Any) -> ReleaseProvenance:
        if not isinstance(raw, dict):
            return cls()
        return cls(
            commits=_str_tuple(raw.get("commits")),
            pull_requests=_str_tuple(raw.get("pull_requests")),
            ado_work_items=_int_tuple(raw.get("ado_work_items")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.commits:
            payload["commits"] = list(self.commits)
        if self.pull_requests:
            payload["pull_requests"] = list(self.pull_requests)
        if self.ado_work_items:
            payload["ado_work_items"] = list(self.ado_work_items)
        return payload


@dataclass(frozen=True)
class ReleaseChangeItem:
    id: str
    category: str
    title: str
    summary: str
    user_impact: tuple[str, ...] = ()
    developer_notes: tuple[str, ...] = ()
    capabilities_affected: tuple[str, ...] = ()
    documentation: tuple[str, ...] = ()
    breaking: bool = False
    migration: str | None = None
    ado_feature_ids: tuple[int, ...] = ()
    provenance: ReleaseProvenance = field(default_factory=ReleaseProvenance)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ReleaseChangeItem:
        category = str(raw.get("category") or "").strip().lower()
        return cls(
            id=str(raw.get("id") or "").strip(),
            category=category,
            title=str(raw.get("title") or "").strip(),
            summary=str(raw.get("summary") or "").strip(),
            user_impact=_str_tuple(raw.get("user_impact")),
            developer_notes=_str_tuple(raw.get("developer_notes")),
            capabilities_affected=_str_tuple(raw.get("capabilities_affected")),
            documentation=_str_tuple(raw.get("documentation")),
            breaking=bool(raw.get("breaking")),
            migration=_optional_str(raw.get("migration")),
            ado_feature_ids=_int_tuple(raw.get("ado_feature_ids")),
            provenance=ReleaseProvenance.from_dict(raw.get("provenance")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "summary": self.summary,
        }
        if self.user_impact:
            payload["user_impact"] = list(self.user_impact)
        if self.developer_notes:
            payload["developer_notes"] = list(self.developer_notes)
        if self.capabilities_affected:
            payload["capabilities_affected"] = list(self.capabilities_affected)
        if self.documentation:
            payload["documentation"] = list(self.documentation)
        if self.breaking:
            payload["breaking"] = True
        if self.migration:
            payload["migration"] = self.migration
        if self.ado_feature_ids:
            payload["ado_feature_ids"] = list(self.ado_feature_ids)
        prov = self.provenance.to_dict()
        if prov:
            payload["provenance"] = prov
        return payload


@dataclass(frozen=True)
class ReleaseManifest:
    version: str
    date: str
    summary: str
    changes: tuple[ReleaseChangeItem, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ReleaseManifest:
        changes_raw = raw.get("changes")
        changes: list[ReleaseChangeItem] = []
        if isinstance(changes_raw, list):
            for row in changes_raw:
                if isinstance(row, dict):
                    changes.append(ReleaseChangeItem.from_dict(row))
        return cls(
            version=str(raw.get("version") or "").strip(),
            date=str(raw.get("date") or "").strip(),
            summary=str(raw.get("summary") or "").strip(),
            changes=tuple(changes),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": MANIFEST_SCHEMA,
            "version": self.version,
            "date": self.date,
            "summary": self.summary,
            "changes": [item.to_dict() for item in self.changes],
        }


def _str_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return tuple(out)


def _int_tuple(value: Any) -> tuple[int, ...]:
    if not isinstance(value, list):
        return ()
    out: list[int] = []
    for item in value:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return tuple(out)


def _optional_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
