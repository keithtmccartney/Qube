"""Phase 1 — release manifest schema, loader, seen-state, and bundled corpus."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.releases.loader import (
    bundled_releases_dir,
    clear_release_loader_cache,
    get_release_manifest,
    get_unseen_releases,
    list_release_versions,
    load_release_corpus,
    load_validated_release_corpus,
)
from core.releases.model import ReleaseManifest
from core.releases.seen_state import ReleaseSeenState, reset_release_seen_state_for_tests
from core.releases.validate import ReleaseManifestValidationError, validate_release_corpus


class TestBundledReleaseCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        clear_release_loader_cache()

    def test_bundled_corpus_validates(self) -> None:
        validate_release_corpus(bundled_releases_dir())

    def test_load_validated_corpus_has_five_releases(self) -> None:
        corpus = load_validated_release_corpus()
        self.assertEqual(len(corpus), 5)
        versions = [m.version for m in corpus]
        self.assertEqual(
            versions,
            ["1.3.0", "1.2.9", "1.2.8", "1.2.7", "1.2.6"],
        )

    def test_list_release_versions_newest_first(self) -> None:
        self.assertEqual(
            list_release_versions(),
            ["1.3.0", "1.2.9", "1.2.8", "1.2.7", "1.2.6"],
        )

    def test_get_release_manifest_mcp_item_has_user_impact(self) -> None:
        manifest = get_release_manifest("1.2.6")
        mcp = next(item for item in manifest.changes if item.id == "mcp-capability-integration")
        self.assertTrue(mcp.user_impact)
        self.assertIn(57, mcp.ado_feature_ids)
        self.assertIn("cap:provider:mcp", mcp.capabilities_affected)

    def test_primary_items_have_user_impact(self) -> None:
        for manifest in load_release_corpus():
            user_facing = [
                item
                for item in manifest.changes
                if item.category in {"new", "improved", "fixed"}
            ]
            self.assertTrue(user_facing, msg=f"{manifest.version} has no user-facing items")
            with_user_impact = [item for item in user_facing if item.user_impact]
            self.assertGreaterEqual(
                len(with_user_impact),
                1,
                msg=f"{manifest.version} missing user_impact on primary items",
            )


class TestReleaseLoaderEdgeCases(unittest.TestCase):
    def setUp(self) -> None:
        clear_release_loader_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _write(self, relative: str, payload: dict) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def test_missing_release_file_fails_validation(self) -> None:
        self._write(
            "manifest.json",
            {
                "schema": "qube.release_index.v1",
                "releases": [{"version": "9.9.9", "date": "2026-01-01", "file": "9.9.9.json"}],
            },
        )
        with self.assertRaises(ReleaseManifestValidationError):
            validate_release_corpus(self.root)

    def test_get_unseen_releases_respects_last_seen(self) -> None:
        sample = {
            "schema": "qube.release_manifest.v1",
            "summary": "Test release",
            "changes": [
                {
                    "id": "sample",
                    "category": "new",
                    "title": "Sample",
                    "summary": "Sample change",
                    "user_impact": ["Do something new"],
                }
            ],
        }
        for version, date in (("1.0.0", "2026-01-01"), ("1.1.0", "2026-02-01")):
            payload = dict(sample)
            payload["version"] = version
            payload["date"] = date
            self._write(f"{version}.json", payload)
        self._write(
            "manifest.json",
            {
                "schema": "qube.release_index.v1",
                "releases": [
                    {"version": "1.1.0", "date": "2026-02-01", "file": "1.1.0.json"},
                    {"version": "1.0.0", "date": "2026-01-01", "file": "1.0.0.json"},
                ],
            },
        )
        unseen = get_unseen_releases(
            current_version="1.1.0",
            last_seen_version="1.0.0",
            releases_dir=self.root,
        )
        self.assertEqual([m.version for m in unseen], ["1.1.0"])

    def test_round_trip_manifest_dict(self) -> None:
        manifest = ReleaseManifest.from_dict(get_release_manifest("1.3.0").to_dict())
        self.assertEqual(manifest.version, "1.3.0")
        self.assertTrue(manifest.changes)


class TestReleaseSeenState(unittest.TestCase):
    def setUp(self) -> None:
        reset_release_seen_state_for_tests()
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "release_seen.json"
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(reset_release_seen_state_for_tests)

    def test_mark_seen_advances_monotonically(self) -> None:
        state = ReleaseSeenState(self.path)
        state.mark_seen("1.2.6")
        self.assertEqual(state.get_last_seen_version(), "1.2.6")
        state.mark_seen("1.2.5")
        self.assertEqual(state.get_last_seen_version(), "1.2.6")
        state.mark_seen("1.3.0")
        self.assertEqual(state.get_last_seen_version(), "1.3.0")

    def test_should_show_version(self) -> None:
        state = ReleaseSeenState(self.path)
        self.assertTrue(state.should_show_version("1.3.0", current_app_version="1.3.0"))
        state.mark_seen("1.2.9")
        self.assertFalse(state.should_show_version("1.2.9", current_app_version="1.3.0"))
        self.assertTrue(state.should_show_version("1.3.0", current_app_version="1.3.0"))


if __name__ == "__main__":
    unittest.main()
