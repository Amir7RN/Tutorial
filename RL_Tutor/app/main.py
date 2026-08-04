"""
RL Tutor -- interactive Reinforcement Learning workbench.

Run from the project root:   python -m app.main      (or double-click run.bat)
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
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
        s = QLabel("dynamics · impedance · RL · from your notes")
        s.setObjectName("SidebarSub")
        sl.addWidget(s)

        self.nav = QListWidget()
        self.nav.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        sl.addWidget(self.nav, 1)

        hint = QLabel("Ctrl+← / Ctrl+→   prev / next page")
        hint.setStyleSheet(
            f"color:{theme.TEXT_FAINT}; font-size:10px; padding:8px 16px;"
            f"background:transparent;")
        sl.addWidget(hint)

        root.addWidget(side)

        # ---------------- pages ----------------
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.pages = build_pages()
        current_section = None
        self._index_map = {}     # nav row -> stack index

        for i, page in enumerate(self.pages):
            self.stack.addWidget(page)
            if page.SECTION != current_section:
                current_section = page.SECTION
                hdr = QListWidgetItem(current_section.upper())
                hdr.setFlags(Qt.NoItemFlags)
                f = QFont("Segoe UI", 8)
                f.setBold(True)
                f.setLetterSpacing(QFont.AbsoluteSpacing, 1.1)
                hdr.setFont(f)
                from PySide6.QtGui import QColor
                hdr.setForeground(QColor(
                    theme.SECTION_COLORS.get(current_section, theme.TEXT_FAINT)))
                self.nav.addItem(hdr)
            item = QListWidgetItem(f"{page.NUM} · {page.TITLE}")
            self.nav.addItem(item)
            self._index_map[self.nav.row(item)] = i

        self.nav.currentRowChanged.connect(self._nav_changed)
        self._current = 0
        first = next(r for r in self._index_map)
        self.nav.setCurrentRow(first)

        QShortcut(QKeySequence("Ctrl+Right"), self, self.next_page)
        QShortcut(QKeySequence("Ctrl+Left"), self, self.prev_page)

    def _nav_changed(self, row):
        if row not in self._index_map:
            return
        idx = self._index_map[row]
        if idx == self._current:
            return
        self.pages[self._current].on_hide()
        self._current = idx
        self.stack.setCurrentIndex(idx)
        self.pages[idx].on_show()

    def _row_for_page(self, page_idx):
        for row, idx in self._index_map.items():
            if idx == page_idx:
                return row
        return None

    def next_page(self):
        if self._current + 1 < len(self.pages):
            r = self._row_for_page(self._current + 1)
            if r is not None:
                self.nav.setCurrentRow(r)

    def prev_page(self):
        if self._current > 0:
            r = self._row_for_page(self._current - 1)
            if r is not None:
                self.nav.setCurrentRow(r)

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
            row = w._row_for_page(i)
            if row is not None:
                w.nav.setCurrentRow(row)
            app.processEvents()
            w.grab().save(os.path.join(out, f"{i+1:02d}_{w.pages[i].TITLE[:2].strip()}.png"))
            state["i"] += 1
            QTimer.singleShot(120, tick)

        QTimer.singleShot(700, tick)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
