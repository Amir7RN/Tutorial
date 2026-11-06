"""
CppEditor -- a small code editor that behaves like one.

Typing:
    Tab / Shift+Tab        indent / dedent (the current line, or every selected line)
    Enter                  keep the indentation; one level deeper after { ( [ or a label:
                           between {} it opens the block and puts } on its own line
    }                      on an empty line, dedents before it is typed
    Backspace              in leading spaces, back to the previous tab stop;
                           between an empty pair () [] {} "" '' deletes both
    ( [ { " '              auto-close; typing the closer over an auto-closed one steps over it
    Home                   first non-space character, then column 0
    Ctrl+/                 toggle // on the line or selection
    Ctrl+D                 duplicate the line
    Alt+Up / Alt+Down      move the line or selection
    Ctrl+= / Ctrl+- / Ctrl+wheel   zoom
    Ctrl+Enter             `run_requested` (the exercise card checks your code)
    Ctrl+S                 `save_requested`

The gutter shows line numbers and a red dot on any line the compiler complained
about (hover it for the message). The current line, the bracket matching the
one at the cursor, and compiler error lines are highlighted.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QRect, QRegularExpression, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QKeySequence, QPainter, QSyntaxHighlighter,
                           QTextCharFormat, QTextCursor, QTextFormat)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QToolTip, QWidget

from .. import theme

INDENT = 4
PAIRS = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
CLOSERS = set(PAIRS.values())


def mono_font(size=11) -> QFont:
    for fam in ("Cascadia Mono", "Cascadia Code", "JetBrains Mono", "Consolas"):
        f = QFont(fam, size)
        if f.exactMatch() or fam == "Consolas":
            f.setStyleHint(QFont.Monospace)
            f.setFixedPitch(True)
            return f
    return QFont("monospace", size)


# =====================================================================
# syntax highlighting
# =====================================================================

def _fmt(colour, bold=False, italic=False):
    f = QTextCharFormat()
    f.setForeground(QColor(colour))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class CppSyntax(QSyntaxHighlighter):
    KEYWORDS = ("alignas alignof auto bool break case catch char class const constexpr const_cast "
                "continue decltype default delete do double else enum explicit extern false final float "
                "for friend if inline int long mutable namespace new noexcept nullptr operator override "
                "private protected public return short signed sizeof static static_assert static_cast "
                "struct switch template this thread_local throw true try typedef typename union unsigned "
                "using virtual void volatile while reinterpret_cast dynamic_cast")
    TYPES = ("std size_t uint8_t uint16_t uint32_t uint64_t int8_t int32_t int64_t string vector array map "
             "set unordered_map unique_ptr shared_ptr weak_ptr make_unique make_shared move forward "
             "atomic thread mutex lock_guard function optional variant pair tuple chrono")

    def __init__(self, doc):
        super().__init__(doc)
        kw = _fmt("#ff7b72", bold=True)
        ty = _fmt("#79c0ff")
        self.rules = [
            (QRegularExpression(r"\b(" + "|".join(self.KEYWORDS.split()) + r")\b"), kw),
            (QRegularExpression(r"\b(" + "|".join(self.TYPES.split()) + r")\b"), ty),
            (QRegularExpression(r"\b[A-Z][A-Za-z0-9_]*\b"), _fmt("#ffa657")),          # Types
            (QRegularExpression(r"\b[A-Za-z_]\w*(?=\s*\()"), _fmt("#d2a8ff")),         # calls
            (QRegularExpression(r"\b(0x[0-9a-fA-F]+|\d+\.?\d*([eE][-+]?\d+)?)[fFuUlL]*\b"), _fmt("#79c0ff")),
            (QRegularExpression(r"\b\w+_\b"), _fmt("#e6c07b")),                         # members_
            (QRegularExpression(r"^\s*#\s*\w+[^\n]*"), _fmt("#7ee787")),
            (QRegularExpression(r"'(\\.|[^'\\])*'"), _fmt("#a5d6ff")),
            (QRegularExpression(r'"(\\.|[^"\\])*"'), _fmt("#a5d6ff")),
            (QRegularExpression(r"//[^\n]*"), _fmt("#8b949e", italic=True)),
        ]
        self.todo = (QRegularExpression(r"\bTODO\b[^\n]*"), _fmt("#f0b72f", bold=True))
        self.comment = _fmt("#8b949e", italic=True)
        self.c_start = QRegularExpression(r"/\*")
        self.c_end = QRegularExpression(r"\*/")

    def highlightBlock(self, text):
        for pat, fmt in self.rules:
            it = pat.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
        it = self.todo[0].globalMatch(text)
        while it.hasNext():
            m = it.next()
            self.setFormat(m.capturedStart(), m.capturedLength(), self.todo[1])
        # /* block comments */ that may span lines
        self.setCurrentBlockState(0)
        cont = self.previousBlockState() == 1
        start = 0 if cont else text.find("/*")
        while start >= 0:
            line_comment = text.find("//")
            if not cont and 0 <= line_comment < start:
                break                            # the /* is inside a // comment
            endi = text.find("*/", start if cont else start + 2)
            cont = False
            if endi < 0:
                self.setCurrentBlockState(1)
                end = len(text)
            else:
                end = endi + 2
            self.setFormat(start, end - start, self.comment)
            start = text.find("/*", end)


# =====================================================================
# the editor
# =====================================================================

class _Gutter(QWidget):
    def __init__(self, ed):
        super().__init__(ed)
        self.ed = ed
        self.setMouseTracking(True)

    def sizeHint(self):
        return QSize(self.ed.gutter_width(), 0)

    def paintEvent(self, ev):
        self.ed.paint_gutter(self, ev)

    def mouseMoveEvent(self, ev):
        line = self.ed.line_at_y(ev.position().y())
        msg = self.ed.diags.get(line)
        if msg:
            QToolTip.showText(ev.globalPosition().toPoint(), msg, self)
        else:
            QToolTip.hideText()


class CppEditor(QPlainTextEdit):
    run_requested = Signal()
    save_requested = Signal()

    def __init__(self, text="", read_only=False, parent=None):
        super().__init__(parent)
        self.setFont(mono_font(11))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabChangesFocus(False)
        self._update_tab_stop()
        self.diags = {}                  # 0-based line -> message
        self.syntax = CppSyntax(self.document())
        self.gutter = _Gutter(self)
        self.setPlainText(text)
        self.setReadOnly(read_only)
        bg = theme.BG_INPUT if not read_only else "#0d1219"
        self.setStyleSheet(f"QPlainTextEdit {{ background:{bg}; color:{theme.TEXT}; "
                           f"border:1px solid {theme.BORDER}; border-radius:6px; "
                           f"selection-background-color:#264f78; }}")
        self.blockCountChanged.connect(self._update_margin)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._highlight)
        self._update_margin()
        self._highlight()

    # ---- geometry ------------------------------------------------------
    def _update_tab_stop(self):
        self.setTabStopDistance(QFontMetricsF(self.font()).horizontalAdvance(" ") * INDENT)

    def gutter_width(self):
        digits = max(3, len(str(self.blockCount())))
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits + 8

    def _update_margin(self, *_):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _update_gutter(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def line_at_y(self, y):
        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        while block.isValid():
            h = self.blockBoundingRect(block).height()
            if top <= y < top + h:
                return block.blockNumber()
            top += h
            block = block.next()
        return -1

    def paint_gutter(self, w, ev):
        p = QPainter(w)
        p.fillRect(ev.rect(), QColor("#0a0e14"))
        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        cur = self.textCursor().blockNumber()
        fh = self.fontMetrics().height()
        p.setFont(self.font())
        while block.isValid() and top <= ev.rect().bottom():
            h = self.blockBoundingRect(block).height()
            if block.isVisible() and top + h >= ev.rect().top():
                n = block.blockNumber()
                if n in self.diags:
                    p.setBrush(QColor(theme.BAD))
                    p.setPen(Qt.NoPen)
                    r = max(3, fh // 4)
                    p.drawEllipse(5, int(top + fh / 2 - r), 2 * r, 2 * r)
                p.setPen(QColor(theme.TEXT if n == cur else theme.TEXT_FAINT))
                p.drawText(0, int(top), w.width() - 6, fh, Qt.AlignRight, str(n + 1))
            top += h
            block = block.next()

    # ---- highlights ----------------------------------------------------
    def set_diagnostics(self, diags: dict):
        """{0-based line: message}. Pass {} to clear."""
        self.diags = dict(diags)
        self.gutter.update()
        self._highlight()

    def goto_line(self, line: int, col: int = 0):
        block = self.document().findBlockByNumber(max(0, line))
        if not block.isValid():
            return
        cur = QTextCursor(block)
        cur.movePosition(QTextCursor.Right, n=max(0, min(col, block.length() - 1)))
        self.setTextCursor(cur)
        self.centerCursor()
        self.setFocus()

    def _highlight(self):
        s = QTextEdit.ExtraSelection()
        s.format.setBackground(QColor("#161d29"))
        s.format.setProperty(QTextFormat.FullWidthSelection, True)
        s.cursor = self.textCursor()
        s.cursor.clearSelection()
        sels = [s]
        for line in self.diags:
            block = self.document().findBlockByNumber(line)
            if block.isValid():
                s = QTextEdit.ExtraSelection()
                c = QColor(theme.BAD)
                c.setAlpha(55)
                s.format.setBackground(c)
                s.format.setProperty(QTextFormat.FullWidthSelection, True)
                s.cursor = QTextCursor(block)
                sels.append(s)
        sels += self._bracket_match()
        self.setExtraSelections(sels)

    def _bracket_match(self):
        doc = self.toPlainText()
        pos = self.textCursor().position()
        opens, closes = "([{", ")]}"
        for p in (pos, pos - 1):
            if 0 <= p < len(doc) and doc[p] in opens + closes:
                ch = doc[p]
                if ch in opens:
                    want, step, other = closes[opens.index(ch)], 1, ch
                else:
                    want, step, other = opens[closes.index(ch)], -1, ch
                depth, q = 0, p
                while 0 <= q < len(doc):
                    if doc[q] == other:
                        depth += 1
                    elif doc[q] == want:
                        depth -= 1
                        if depth == 0:
                            return [self._mark(p), self._mark(q)]
                    q += step
                return [self._mark(p, bad=True)]
        return []

    def _mark(self, p, bad=False):
        s = QTextEdit.ExtraSelection()
        s.format.setBackground(QColor("#5c2b2b" if bad else "#2b4a6b"))
        s.format.setForeground(QColor("#ffffff"))
        c = self.textCursor()
        c.setPosition(p)
        c.setPosition(p + 1, QTextCursor.KeepAnchor)
        s.cursor = c
        return s

    # ---- zoom ----------------------------------------------------------
    def zoom(self, d):
        f = self.font()
        f.setPointSize(max(7, min(28, f.pointSize() + d)))
        self.setFont(f)
        self._update_tab_stop()
        self._update_margin()
        self.gutter.update()

    def wheelEvent(self, ev):
        if ev.modifiers() & Qt.ControlModifier:
            self.zoom(1 if ev.angleDelta().y() > 0 else -1)
            return
        super().wheelEvent(ev)

    # ---- editing -------------------------------------------------------
    def _line_text(self, cur=None):
        cur = cur or self.textCursor()
        return cur.block().text()

    @staticmethod
    def _indent_of(text):
        return len(text) - len(text.lstrip(" "))

    def _selected_blocks(self):
        cur = self.textCursor()
        doc = self.document()
        a, b = sorted((cur.anchor(), cur.position()))
        first = doc.findBlock(a)
        last = doc.findBlock(b)
        if cur.hasSelection() and b == last.position() and last != first:
            last = last.previous()      # a selection ending at column 0 does not include that line
        return first, last

    def _for_lines(self, fn):
        first, last = self._selected_blocks()
        cur = self.textCursor()
        cur.beginEditBlock()
        block = first
        while True:
            fn(block)
            if block == last:
                break
            block = block.next()
        cur.endEditBlock()
        # reselect the whole lines so repeated Tab keeps working on them
        if self.textCursor().hasSelection():
            c = self.textCursor()
            c.setPosition(first.position())
            c.setPosition(last.position() + len(last.text()), QTextCursor.KeepAnchor)
            self.setTextCursor(c)

    def indent_lines(self):
        def f(block):
            c = QTextCursor(block)
            c.insertText(" " * INDENT)
        self._for_lines(f)

    def dedent_lines(self):
        def f(block):
            n = min(INDENT, self._indent_of(block.text()))
            if n:
                c = QTextCursor(block)
                c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, n)
                c.removeSelectedText()
        self._for_lines(f)

    def toggle_comment(self):
        first, last = self._selected_blocks()
        blocks, b = [], first
        while True:
            blocks.append(b)
            if b == last:
                break
            b = b.next()
        texts = [x.text() for x in blocks if x.text().strip()]
        uncomment = bool(texts) and all(t.lstrip().startswith("//") for t in texts)
        col = min((self._indent_of(t) for t in texts), default=0)

        def f(block):
            t = block.text()
            if not t.strip():
                return
            c = QTextCursor(block)
            if uncomment:
                i = t.index("//")
                n = 3 if t[i:i + 3] == "// " else 2
                c.setPosition(block.position() + i)
                c.setPosition(block.position() + i + n, QTextCursor.KeepAnchor)
                c.removeSelectedText()
            else:
                c.setPosition(block.position() + col)
                c.insertText("// ")
        self._for_lines(f)

    def duplicate_line(self):
        cur = self.textCursor()
        text = cur.block().text()
        col = cur.positionInBlock()
        cur.beginEditBlock()
        cur.movePosition(QTextCursor.EndOfBlock)
        cur.insertText("\n" + text)
        cur.endEditBlock()
        cur.movePosition(QTextCursor.StartOfBlock)
        cur.movePosition(QTextCursor.Right, n=col)
        self.setTextCursor(cur)

    def move_lines(self, d):
        first, last = self._selected_blocks()
        if (d < 0 and not first.previous().isValid()) or (d > 0 and not last.next().isValid()):
            return
        cur = self.textCursor()
        rel_a = cur.anchor() - first.position()
        rel_p = cur.position() - first.position()
        c = QTextCursor(self.document())
        c.beginEditBlock()
        c.setPosition(first.position())
        c.setPosition(last.position() + len(last.text()), QTextCursor.KeepAnchor)
        chunk = c.selectedText().replace(" ", "\n")
        if d < 0:
            prev = first.previous()
            c.setPosition(prev.position())
            c.setPosition(last.position() + len(last.text()), QTextCursor.KeepAnchor)
            c.insertText(chunk + "\n" + prev.text())
            start = prev.position()
        else:
            nxt = last.next()
            c.setPosition(first.position())
            c.setPosition(nxt.position() + len(nxt.text()), QTextCursor.KeepAnchor)
            c.insertText(nxt.text() + "\n" + chunk)
            start = first.position() + len(nxt.text()) + 1
        c.endEditBlock()
        nc = self.textCursor()
        nc.setPosition(start + rel_a)
        nc.setPosition(start + rel_p, QTextCursor.KeepAnchor)
        self.setTextCursor(nc)

    def _newline(self):
        cur = self.textCursor()
        line = cur.block().text()
        col = cur.positionInBlock()
        before, after = line[:col], line[col:]
        base = self._indent_of(line)
        stripped = before.rstrip()
        deeper = stripped.endswith(("{", "(", "[")) or (
            re.search(r"\b(public|private|protected|default)\s*:$|\bcase\b.*:$", stripped) is not None)
        ind = base + (INDENT if deeper else 0)
        if re.search(r"\b(public|private|protected)\s*:$", stripped):
            ind = base + INDENT
        cur.beginEditBlock()
        cur.insertText("\n" + " " * ind)
        if deeper and after.lstrip()[:1] in ("}", ")", "]"):
            pos = cur.position()
            cur.insertText("\n" + " " * base)
            cur.setPosition(pos)
        cur.endEditBlock()
        self.setTextCursor(cur)

    def keyPressEvent(self, ev):
        if self.isReadOnly():
            return super().keyPressEvent(ev)
        key, mod, text = ev.key(), ev.modifiers(), ev.text()
        ctrl = bool(mod & Qt.ControlModifier)
        cur = self.textCursor()

        if ctrl and key in (Qt.Key_Return, Qt.Key_Enter):
            self.run_requested.emit()
            return
        if ev.matches(QKeySequence.Save):
            self.save_requested.emit()
            return
        if ctrl and key == Qt.Key_Slash:
            self.toggle_comment()
            return
        if ctrl and key == Qt.Key_D:
            self.duplicate_line()
            return
        if ctrl and key in (Qt.Key_Equal, Qt.Key_Plus):
            self.zoom(1)
            return
        if ctrl and key == Qt.Key_Minus:
            self.zoom(-1)
            return
        if (mod & Qt.AltModifier) and key in (Qt.Key_Up, Qt.Key_Down):
            self.move_lines(-1 if key == Qt.Key_Up else 1)
            return
        if key == Qt.Key_Backtab:
            self.dedent_lines()
            return
        if key == Qt.Key_Tab and not ctrl:
            if cur.hasSelection() and cur.block() != self.document().findBlock(cur.anchor()):
                self.indent_lines()
            else:
                col = cur.positionInBlock()
                cur.insertText(" " * (INDENT - col % INDENT))
            return
        if key in (Qt.Key_Return, Qt.Key_Enter) and not (mod & Qt.ShiftModifier):
            self._newline()
            return
        if key == Qt.Key_Home and not ctrl:
            line = cur.block().text()
            first = self._indent_of(line)
            target = 0 if cur.positionInBlock() == first else first
            mode = QTextCursor.KeepAnchor if mod & Qt.ShiftModifier else QTextCursor.MoveAnchor
            cur.setPosition(cur.block().position() + target, mode)
            self.setTextCursor(cur)
            return
        if key == Qt.Key_Backspace and not cur.hasSelection() and not ctrl:
            line = cur.block().text()
            col = cur.positionInBlock()
            if col > 0 and line[:col].strip() == "":
                n = (col - 1) % INDENT + 1
                cur.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, n)
                cur.removeSelectedText()
                return
            if 0 < col < len(line) and PAIRS.get(line[col - 1]) == line[col]:
                cur.movePosition(QTextCursor.Left)
                cur.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 2)
                cur.removeSelectedText()
                return
        if text and not ctrl:
            line = cur.block().text()
            col = cur.positionInBlock()
            nxt = line[col:col + 1]
            # step over a closer that is already there
            if text in CLOSERS and nxt == text and not cur.hasSelection():
                cur.movePosition(QTextCursor.Right)
                self.setTextCursor(cur)
                return
            # a } on a blank line goes back one level first
            if text == "}" and line.strip() == "" and col == len(line):
                n = min(INDENT, self._indent_of(line))
                cur.beginEditBlock()
                cur.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, n)
                cur.insertText("}")
                cur.endEditBlock()
                return
            if text in PAIRS:
                prev = line[col - 1:col] if col else ""
                quote = text in "\"'"
                if cur.hasSelection():
                    sel = cur.selectedText()
                    cur.insertText(text + sel + PAIRS[text])
                    return
                if (nxt == "" or nxt in " \t)]};,") and not (quote and (prev.isalnum() or prev == "\\")):
                    cur.insertText(text + PAIRS[text])
                    cur.movePosition(QTextCursor.Left)
                    self.setTextCursor(cur)
                    return
        super().keyPressEvent(ev)
