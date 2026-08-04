"""
CodePane -- syntax-highlighted Python with live line highlighting.

The highlighting is what makes it a teaching tool rather than a text box: pages
call `pane.mark(lines, colour)` while an algorithm runs, so you see exactly which
statement is executing on the current sweep. On the comparison pages, two panes
sit side by side with the differing lines flagged.
"""

from __future__ import annotations

import keyword
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


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.rules = []

        for kw in keyword.kwlist:
            self.rules.append((QRegularExpression(rf"\b{kw}\b"),
                               _fmt(C_KEYWORD, bold=True)))

        builtins = ("range len max min sum abs sorted enumerate zip list dict set "
                    "tuple float int str bool print any all reversed").split()
        for b in builtins:
            self.rules.append((QRegularExpression(rf"\b{b}\b"), _fmt(C_BUILTIN)))

        self.rules += [
            (QRegularExpression(r"\bself\b"), _fmt(C_SELF, italic=True)),
            (QRegularExpression(r"\b\d+\.?\d*(e-?\d+)?\b"), _fmt(C_NUMBER)),
            (QRegularExpression(r"(?<=def\s)\w+"), _fmt(C_DEF, bold=True)),
            (QRegularExpression(r"(?<=class\s)\w+"), _fmt(C_DEF, bold=True)),
            (QRegularExpression(r"@\w+"), _fmt(C_DECOR)),
            (QRegularExpression(r"'[^']*'"), _fmt(C_STRING)),
            (QRegularExpression(r'"[^"]*"'), _fmt(C_STRING)),
            (QRegularExpression(r"#[^\n]*"), _fmt(C_COMMENT, italic=True)),
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
        self._hl = PythonHighlighter(self.document())
        self._marks: list[tuple[int, str]] = []
        self.set_code(code)

    def set_code(self, code: str):
        self.setPlainText(code.strip("\n"))
        self._marks = []
        self._apply()

    def mark(self, lines, colour=theme.ACCENT_DIM, replace=True):
        """
        Highlight 1-indexed source lines.
        `lines` may be an int or an iterable of ints.
        """
        if isinstance(lines, int):
            lines = [lines]
        new = [(int(n), colour) for n in lines]
        self._marks = new if replace else self._marks + new
        self._apply()

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
        block = self.document().findBlockByLineNumber(max(0, line_no - 1))
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
# Source extraction -- show the REAL rlcore source, never a copy
# --------------------------------------------------------------------------

def get_source(func) -> str:
    """
    Pull a function's actual source out of rlcore with inspect.

    This matters: the code on screen is literally the code that just ran. There
    is no second copy to drift out of sync with the algorithms.
    """
    import inspect
    import textwrap
    try:
        return textwrap.dedent(inspect.getsource(func))
    except (OSError, TypeError):
        return f"# source unavailable for {getattr(func, '__name__', func)}"


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
