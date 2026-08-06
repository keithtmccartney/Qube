"""Version history / What's New handlers for SettingsView."""

from __future__ import annotations

from ui.components.release_history_dialog import show_version_history_dialog


class ReleaseHandlersMixin:
    def _on_view_version_history_clicked(self) -> None:
        is_dark = getattr(self.window(), "_is_dark_theme", True)
        show_version_history_dialog(self.window(), is_dark=is_dark)
