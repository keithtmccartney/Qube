"""Tests for release markdown rendering, query, and What's New orchestration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.releases.loader import load_release_corpus
from core.releases.model import ReleaseManifest
from core.releases.query import filter_change_items, search_release_corpus
from core.releases.render import render_release_markdown, render_releases_markdown
from core.releases.seen_state import ReleaseSeenState, reset_release_seen_state_for_tests
from core.releases.whats_new import acknowledge_whats_new, pending_whats_new_manifests


class TestReleaseRenderAndQuery(unittest.TestCase):
    def test_render_release_markdown_groups_categories(self) -> None:
        manifest = get_release_manifest_safe("1.2.6")
        md = render_release_markdown(manifest)
        self.assertIn("# Qube 1.2.6", md)
        self.assertIn("## New", md)
        self.assertIn("MCP capability integration", md)
        self.assertNotIn("Add IntegrationsConsentController", md)

    def test_filter_change_items_by_query_and_category(self) -> None:
        manifest = get_release_manifest_safe("1.2.6")
        matches = filter_change_items(manifest.changes, query="mcp", category="new")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].id, "mcp-capability-integration")

    def test_search_release_corpus(self) -> None:
        corpus = load_release_corpus()
        results = search_release_corpus(corpus, query="turn index")
        self.assertTrue(any(m.version == "1.2.7" for m, _ in results))

    def test_render_multiple_releases(self) -> None:
        corpus = load_release_corpus()[:2]
        md = render_releases_markdown(corpus)
        self.assertIn("# Qube 1.3.0", md)
        self.assertIn("# Qube 1.2.9", md)
        self.assertIn("\n---\n", md)


class TestWhatsNewOrchestration(unittest.TestCase):
    def setUp(self) -> None:
        reset_release_seen_state_for_tests()
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "release_seen.json"
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(reset_release_seen_state_for_tests)

    def test_pending_whats_new_first_launch_shows_current_only(self) -> None:
        state = ReleaseSeenState(self.path)
        pending = pending_whats_new_manifests(
            current_version="1.3.0",
            seen_state=state,
        )
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].version, "1.3.0")

    def test_pending_whats_new_upgrade_includes_intermediate_versions(self) -> None:
        state = ReleaseSeenState(self.path)
        state.mark_seen("1.2.6")
        pending = pending_whats_new_manifests(
            current_version="1.3.0",
            seen_state=state,
        )
        self.assertEqual([m.version for m in pending], ["1.2.7", "1.2.8", "1.2.9", "1.3.0"])

    def test_pending_whats_new_empty_after_acknowledge(self) -> None:
        state = ReleaseSeenState(self.path)
        acknowledge_whats_new(current_version="1.3.0", seen_state=state)
        pending = pending_whats_new_manifests(
            current_version="1.3.0",
            seen_state=state,
        )
        self.assertEqual(pending, [])


def get_release_manifest_safe(version: str) -> ReleaseManifest:
    from core.releases.loader import get_release_manifest

    return get_release_manifest(version)


if __name__ == "__main__":
    unittest.main()
