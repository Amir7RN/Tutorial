"""
RL Tutor -- interactive Reinforcement Learning workbench.

Run from the project root:   python -m app.main      (or double-click run.bat)
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import theme


def build_pages():
    """Import and instantiate every page, in order."""
    from app.pages import PAGE_CLASSES
    return [cls() for cls in PAGE_CLASSES]


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control & RL Tutor — actuators, impedance, Frozen Lake")
        self.resize(1560, 980)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------------- sidebar ----------------
        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(260)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 10)
        sl.setSpacing(0)

        t = QLabel("Control & RL Tutor")
        t.setObjectName("SidebarTitle")
        sl.addWidget(t)
        s = QLabel("dynamics · control · impedance · RL")
        s.setObjectName("SidebarSub")
        sl.addWidget(s)

        self.filter = QLineEdit()
        self.filter.setObjectName("NavFilter")
        self.filter.setPlaceholderText("filter pages…   (Ctrl+F)")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        sl.addWidget(self.filter)

        self.nav = QTreeWidget()
        self.nav.setHeaderHidden(True)
        self.nav.setIndentation(11)
        self.nav.setRootIsDecorated(True)
        self.nav.setExpandsOnDoubleClick(False)
        self.nav.setVerticalScrollMode(QTreeWidget.ScrollPerPixel)
        sl.addWidget(self.nav, 1)

        hint = QLabel("Ctrl+← / Ctrl+→   prev / next page\n"
                      "click a section to expand it")
        hint.setStyleSheet(
            f"color:{theme.TEXT_FAINT}; font-size:10px; padding:8px 16px;"
            f"background:transparent;")
        sl.addWidget(hint)

        root.addWidget(side)

        # ---------------- pages ----------------
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.pages = build_pages()
        self._class_indices = {type(page).__name__: i for i, page in enumerate(self.pages)}
        for page in self.pages:
            page.navigate_requested.connect(self._navigate_lesson)
        self._page_items = {}        # stack index  -> QTreeWidgetItem
        self._section_items = {}     # section name -> QTreeWidgetItem

        sec_font = QFont("Segoe UI", 8)
        sec_font.setBold(True)
        sec_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.1)

        for i, page in enumerate(self.pages):
            self.stack.addWidget(page)
            sec = page.SECTION
            top = self._section_items.get(sec)
            if top is None:
                top = QTreeWidgetItem(self.nav, [sec.upper()])
                # a section header groups; it never navigates anywhere itself
                top.setFlags(Qt.ItemIsEnabled)
                top.setFont(0, sec_font)
                top.setForeground(0, QColor(
                    theme.SECTION_COLORS.get(sec, theme.TEXT_FAINT)))
                top.setData(0, Qt.UserRole, None)
                self._section_items[sec] = top
            label = f"{page.NUM} · {page.TITLE}" if page.NUM else page.TITLE
            item = QTreeWidgetItem(top, [label])
            item.setData(0, Qt.UserRole, i)
            self._page_items[i] = item

        # page counts on the headers, now that every page has been placed
        for sec, top in self._section_items.items():
            top.setText(0, f"{sec.upper()}   ({top.childCount()})")

        self.nav.collapseAll()
        self.nav.currentItemChanged.connect(self._nav_changed)
        self.nav.itemClicked.connect(self._item_clicked)

        self._current = 0
        self.select_page(0)

        QShortcut(QKeySequence("Ctrl+Right"), self, self.next_page)
        QShortcut(QKeySequence("Ctrl+Left"), self, self.prev_page)
        QShortcut(QKeySequence("Ctrl+F"), self, self.filter.setFocus)

    # ------------------------------------------------------------------
    def _navigate_lesson(self, key):
        idx = self._class_indices.get(key)
        if idx is not None:
            self.select_page(idx)

    def select_page(self, idx: int):
        """Navigate to a page by stack index, expanding its section."""
        item = self._page_items.get(idx)
        if item is None:
            return
        parent = item.parent()
        if parent is not None and not parent.isExpanded():
            parent.setExpanded(True)
        self.nav.setCurrentItem(item)
        self.nav.scrollToItem(item)

    def _item_clicked(self, item, _column):
        """Clicking a section header toggles it -- headers are not selectable,
        so this is the only way they respond."""
        if item.data(0, Qt.UserRole) is None:
            item.setExpanded(not item.isExpanded())

    def _nav_changed(self, cur, _prev):
        if cur is None:
            return
        idx = cur.data(0, Qt.UserRole)
        if idx is None or idx == self._current:
            return
        self.pages[self._current].on_hide()
        self._current = idx
        self.stack.setCurrentIndex(idx)
        self.pages[idx].on_show()

    def _apply_filter(self, text: str):
        """Hide pages that do not match; hide sections left with no matches."""
        q = text.strip().lower()
        for sec, top in self._section_items.items():
            shown = 0
            for k in range(top.childCount()):
                child = top.child(k)
                hit = (not q
                       or q in child.text(0).lower()
                       or q in sec.lower())
                child.setHidden(not hit)
                shown += 1 if hit else 0
            top.setHidden(shown == 0)
            if q:
                top.setExpanded(shown > 0)
        if not q:
            # restore the accordion, keeping the section you are reading open
            self.nav.collapseAll()
            item = self._page_items.get(self._current)
            if item is not None and item.parent() is not None:
                item.parent().setExpanded(True)
                self.nav.scrollToItem(item)

    def next_page(self):
        if self._current + 1 < len(self.pages):
            self.select_page(self._current + 1)

    def prev_page(self):
        if self._current > 0:
            self.select_page(self._current - 1)

    def closeEvent(self, ev):
        for p in self.pages:
            try:
                p.on_hide()
            except Exception:
                pass
        super().closeEvent(ev)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.QSS)
    app.setFont(QFont("Segoe UI", 9))
    w = MainWindow()
    w.show()

    # --selftest: open the real window, click through every page, save a
    # screenshot of each, then quit. Used to verify the app end to end.
    if "--selftest" in sys.argv:
        from PySide6.QtCore import QTimer
        out = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "_shots_app")
        os.makedirs(out, exist_ok=True)
        state = {"i": 0}

        def tick():
            i = state["i"]
            if i >= len(w.pages):
                print(f"selftest OK: {len(w.pages)} pages -> {out}")
                app.quit()
                return
            w.select_page(i)
            app.processEvents()
            w.grab().save(os.path.join(out, f"{i+1:02d}_{w.pages[i].TITLE[:2].strip()}.png"))
            state["i"] += 1
            QTimer.singleShot(120, tick)

        QTimer.singleShot(700, tick)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
