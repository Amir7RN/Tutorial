"""
CodePane -- syntax-highlighted C++17 with live line highlighting.

The highlighting is what makes it a teaching tool rather than a text box: pages
call `pane.mark(lines, colour)` while an algorithm runs, so you see exactly which
statement is executing on the current sweep. On the comparison pages, two panes
sit side by side with the differing lines flagged.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit

from .. import theme

# --------------------------------------------------------------------------

C_KEYWORD  = "#ff7b72"
C_BUILTIN  = "#79c0ff"
C_STRING   = "#a5d6ff"
C_COMMENT  = "#8b949e"
C_NUMBER   = "#79c0ff"
C_DEF      = "#d2a8ff"
C_SELF     = "#ffa657"
C_DECOR    = "#7ee787"


def _fmt(colour, bold=False, italic=False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(colour))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class CppHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.rules = []

        for kw in "alignas auto bool break case catch char class const constexpr continue decltype default delete do double else enum explicit false float for if inline int long namespace new nullptr operator private protected public return short signed sizeof static struct switch template this throw true try typedef typename union unsigned using virtual void volatile while".split():
            self.rules.append((QRegularExpression(rf"\b{kw}\b"),
                               _fmt(C_KEYWORD, bold=True)))

        builtins = "std vector array string pair tuple map size_t Matrix Vec Model Values Policy QTable".split()
        for b in builtins:
            self.rules.append((QRegularExpression(rf"\b{b}\b"), _fmt(C_BUILTIN)))

        self.rules += [
            (QRegularExpression(r"\bthis\b"), _fmt(C_SELF, italic=True)),
            (QRegularExpression(r"\b\d+\.?\d*(e-?\d+)?\b"), _fmt(C_NUMBER)),
            (QRegularExpression(r"\b[A-Za-z_]\w*(?=\s*\()"), _fmt(C_DEF, bold=True)),
            (QRegularExpression(r"(?<=class\s)\w+"), _fmt(C_DEF, bold=True)),
            (QRegularExpression(r"^\s*#\s*\w+"), _fmt(C_DECOR)),
            (QRegularExpression(r"'[^']*'"), _fmt(C_STRING)),
            (QRegularExpression(r'"[^"]*"'), _fmt(C_STRING)),
            (QRegularExpression(r"//[^\n]*"), _fmt(C_COMMENT, italic=True)),
        ]

    def highlightBlock(self, text: str):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


class CodePane(QPlainTextEdit):
    """Read-only code view with `mark()` for run-time line highlighting."""

    def __init__(self, code: str = "", parent=None, font_size=12):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        f = QFont("Cascadia Mono", font_size)
        if not f.exactMatch():
            f = QFont("Consolas", font_size)
        f.setStyleHint(QFont.Monospace)
        self.setFont(f)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self._hl = CppHighlighter(self.document())
        self._marks: list[tuple[int, str]] = []
        self.setToolTip("C++17 teaching example. Shared types and helpers are in cpp/.")
        self.setAccessibleName("C++17 code example")
        self.set_code(code)

    def set_code(self, code: str):
        self.setPlainText("// C++17 teaching example · supporting code in cpp/\n" + code.strip("\n"))
        self._marks = []
        self._apply()

    def mark(self, lines, colour=theme.ACCENT_DIM, replace=True):
        """
        Highlight 1-indexed source lines.
        `lines` may be an int or an iterable of ints.
        """
        if isinstance(lines, int):
            lines = [lines]
        new = [(int(n)+1, colour) for n in lines]
        self._marks = new if replace else self._marks + new
        self._apply()

    def mark_matching(self, needle, colour=theme.ACCENT_DIM):
        line = line_of(self.toPlainText().split("\n",1)[1], needle)
        self.mark(line, colour) if line else self.clear_marks()

    def clear_marks(self):
        self._marks = []
        self._apply()

    def _apply(self):
        sels = []
        doc = self.document()
        for line_no, colour in self._marks:
            block = doc.findBlockByLineNumber(line_no - 1)
            if not block.isValid():
                continue
            sel = QTextEdit.ExtraSelection()
            fmt = QTextCharFormat()
            c = QColor(colour)
            c.setAlpha(90)
            fmt.setBackground(c)
            fmt.setProperty(QTextFormat.FullWidthSelection, True)
            sel.format = fmt
            cur = QTextCursor(block)
            sel.cursor = cur
            sels.append(sel)
        self.setExtraSelections(sels)

    def scroll_to(self, line_no: int):
        block = self.document().findBlockByLineNumber(max(0, line_no))
        if block.isValid():
            cur = QTextCursor(block)
            self.setTextCursor(cur)
            self.centerCursor()

    def sizeHintLine(self, n_lines: int):
        """Set a height that fits roughly n_lines."""
        h = int(self.fontMetrics().height() * n_lines + 22)
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)


# --------------------------------------------------------------------------
# C++ counterparts for the educational code cards
# --------------------------------------------------------------------------

def get_source(func) -> str:
    """Return the reviewed C++ counterpart of a simulation function."""
    from .cpp_source import get_cpp_source
    return get_cpp_source(func)


def strip_docstring(src: str) -> str:
    """Drop the leading triple-quoted docstring, keep the code."""
    m = re.search(r'^(\s*def .*?:\n)(\s*)([ru]?["\']{3})', src, re.S)
    if not m:
        return src
    quote = m.group(3)[-3:]
    start = m.end(3)
    end = src.find(quote, start)
    if end == -1:
        return src
    rest = src[end + 3:]
    return m.group(1) + rest.lstrip("\n")


def line_of(src: str, needle: str, occurrence=1) -> int:
    """1-indexed line number of the nth line containing `needle` (0 if absent)."""
    hits = 0
    for i, line in enumerate(src.split("\n"), start=1):
        if needle in line:
            hits += 1
            if hits == occurrence:
                return i
    return 0
