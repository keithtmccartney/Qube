"""Version History browser and post-update What's New dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.releases.loader import load_release_corpus
from core.releases.model import ReleaseManifest
from core.releases.query import normalize_category
from core.releases.render import CATEGORY_HEADINGS, render_release_markdown
from core.theme.view_theme import view_resolved_theme
from core.theme.widget_styles import (
    PRESTIGE_ACCENT_LABEL,
    PRESTIGE_BODY_LABEL,
    PRESTIGE_GHOST_BUTTON,
    PRESTIGE_SOURCE_CONTAINER,
)
from core.richtext_styles import markdown_document_stylesheet
from ui.components.prestige_dialog import _resolve_is_dark_from_parent


class ReleaseHistoryDialog(QDialog):
    """Searchable version history with optional What's New acknowledgement."""

    def __init__(
        self,
        parent=None,
        *,
        is_dark: bool | None = None,
        mode: str = "browse",
        manifests: list[ReleaseManifest] | None = None,
    ) -> None:
        super().__init__(parent)
        if is_dark is None:
            is_dark = _resolve_is_dark_from_parent(parent)
        self._theme = view_resolved_theme(parent, is_dark=is_dark)
        self._mode = mode if mode in {"browse", "whats_new"} else "browse"
        self._manifests = list(manifests or load_release_corpus())
        self._acknowledged = False
        self._selected_version: str | None = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(760, 560)
        self.resize(920, 680)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        container = QFrame()
        container.setObjectName("ReleaseHistoryContainer")
        container.setStyleSheet(
            self._theme.style(
                PRESTIGE_SOURCE_CONTAINER,
                accent=self._theme.link,
                object_name="ReleaseHistoryContainer",
            )
        )
        inner = QVBoxLayout(container)
        inner.setContentsMargins(28, 26, 28, 22)
        inner.setSpacing(14)

        header = QLabel("WHAT'S NEW" if self._mode == "whats_new" else "VERSION HISTORY")
        header.setStyleSheet(
            self._theme.style(
                PRESTIGE_ACCENT_LABEL, accent=self._theme.link, font_size="11px"
            )
        )
        title_text = (
            "See what's new in this update"
            if self._mode == "whats_new"
            else "Browse Qube release notes"
        )
        title = QLabel(title_text)
        title.setWordWrap(True)
        title.setStyleSheet(self._theme.style(PRESTIGE_BODY_LABEL, font_size="16px"))

        intro = QLabel(
            "User-facing highlights from each release. Technical details stay collapsed unless you expand a section below."
            if self._mode == "browse"
            else "Here's what changed since you last opened Qube. You can browse the full history anytime from Settings → About."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(
            self._theme.style(PRESTIGE_BODY_LABEL, font_size="13px", font_weight="400")
        )

        inner.addWidget(header)
        inner.addWidget(title)
        inner.addWidget(intro)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search releases and changes…")
        self.search_input.textChanged.connect(self._refresh_detail)
        controls.addWidget(self.search_input, stretch=1)

        self.category_combo = QComboBox()
        self.category_combo.addItem("All categories", "")
        for key, label in CATEGORY_HEADINGS.items():
            self.category_combo.addItem(label, key)
        self.category_combo.currentIndexChanged.connect(self._refresh_detail)
        controls.addWidget(self.category_combo)
        inner.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.version_list = QListWidget()
        self.version_list.setMinimumWidth(160)
        self.version_list.currentRowChanged.connect(self._on_version_selected)
        splitter.addWidget(self.version_list)

        self.detail_view = QTextBrowser()
        self.detail_view.setOpenExternalLinks(True)
        self.detail_view.setStyleSheet(
            self._theme.style(PRESTIGE_BODY_LABEL, font_size="13px", font_weight="400")
        )
        doc = self.detail_view.document()
        doc.setDefaultStyleSheet(
            markdown_document_stylesheet(is_dark=is_dark, theme=self._theme)
        )
        splitter.addWidget(self.detail_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        inner.addWidget(splitter, stretch=1)

        self.details_toggle = QPushButton("SHOW TECHNICAL DETAILS")
        self.details_toggle.setCheckable(True)
        self.details_toggle.setStyleSheet(self._theme.style(PRESTIGE_GHOST_BUTTON))
        self.details_toggle.toggled.connect(self._refresh_detail)
        inner.addWidget(self.details_toggle)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        if self._mode == "whats_new":
            history_btn = QPushButton("VERSION HISTORY")
            history_btn.setStyleSheet(self._theme.style(PRESTIGE_GHOST_BUTTON))
            history_btn.clicked.connect(self._switch_to_browse_mode)
            btn_row.addWidget(history_btn)

            not_now_btn = QPushButton("NOT NOW")
            not_now_btn.setStyleSheet(self._theme.style(PRESTIGE_GHOST_BUTTON))
            not_now_btn.clicked.connect(self.reject)
            btn_row.addWidget(not_now_btn)

            got_it_btn = QPushButton("GOT IT")
            got_it_btn.setStyleSheet(self._theme.style(PRESTIGE_GHOST_BUTTON))
            got_it_btn.clicked.connect(self._accept_acknowledged)
            btn_row.addWidget(got_it_btn)
        else:
            close_btn = QPushButton("CLOSE")
            close_btn.setStyleSheet(self._theme.style(PRESTIGE_GHOST_BUTTON))
            close_btn.clicked.connect(self.accept)
            btn_row.addWidget(close_btn)
        inner.addLayout(btn_row)

        outer.addWidget(container)
        self._populate_versions()
        if self.version_list.count():
            self.version_list.setCurrentRow(0)

    @property
    def user_acknowledged(self) -> bool:
        return self._acknowledged

    def _switch_to_browse_mode(self) -> None:
        self._mode = "browse"
        self._populate_versions()
        if self.version_list.count():
            self.version_list.setCurrentRow(0)
        self._refresh_detail()

    def _accept_acknowledged(self) -> None:
        self._acknowledged = True
        self.accept()

    def _populate_versions(self) -> None:
        self.version_list.blockSignals(True)
        self.version_list.clear()
        manifests = self._manifests if self._mode == "whats_new" else load_release_corpus()
        if self._mode == "whats_new" and not manifests:
            manifests = load_release_corpus()
        for manifest in manifests:
            item = QListWidgetItem(f"{manifest.version}  ·  {manifest.date}")
            item.setData(Qt.ItemDataRole.UserRole, manifest.version)
            self.version_list.addItem(item)
        self.version_list.blockSignals(False)

    def _on_version_selected(self, row: int) -> None:
        if row < 0:
            return
        item = self.version_list.item(row)
        if item is None:
            return
        self._selected_version = str(item.data(Qt.ItemDataRole.UserRole) or "")
        self._refresh_detail()

    def _current_manifest(self) -> ReleaseManifest | None:
        version = self._selected_version
        if not version:
            return None
        for manifest in load_release_corpus():
            if manifest.version == version:
                return manifest
        for manifest in self._manifests:
            if manifest.version == version:
                return manifest
        return None

    def _refresh_detail(self) -> None:
        manifest = self._current_manifest()
        if manifest is None:
            self.detail_view.clear()
            return
        category = normalize_category(self.category_combo.currentData())
        markdown = render_release_markdown(
            manifest,
            query=self.search_input.text(),
            category=category,
            include_details=self.details_toggle.isChecked(),
        )
        self.detail_view.setMarkdown(markdown)


def show_whats_new_dialog(
    parent=None,
    manifests: list[ReleaseManifest] | None = None,
    *,
    is_dark: bool | None = None,
) -> bool:
    dialog = ReleaseHistoryDialog(
        parent,
        is_dark=is_dark,
        mode="whats_new",
        manifests=manifests,
    )
    dialog.exec()
    return dialog.user_acknowledged


def show_version_history_dialog(parent=None, *, is_dark: bool | None = None) -> None:
    ReleaseHistoryDialog(parent, is_dark=is_dark, mode="browse").exec()
