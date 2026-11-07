"""
The C++ chapter's beginner widgets.

TryItCard     a small program that runs as-is: edit it, press Run, read what it
              prints, then make the suggested edits and watch what breaks.
LinkTable     "what goes in the header, what goes in the .cpp": click a cell to
              see what the compiler and linker do with that combination.
ErrorDecoder  paste a g++ message, get what it usually means; or browse them all.
python_table  C++ next to the Python you already know.
"""

from __future__ import annotations

import html
import os

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QGridLayout, QHBoxLayout, QLabel,
                               QPlainTextEdit, QPushButton, QTabWidget, QWidget)

from ctrlcore import cpp_concepts as concepts
from ctrlcore import cpp_course as cc
from .. import theme
from .common import Card, body
from .cpp_editor import CppEditor, mono_font
from .cpp_exercise import _Chain, _btn, decoded_html


def _code_height(ed: CppEditor, lines: int) -> int:
    return int(ed.fontMetrics().height() * (lines + 1.2) + 14)


def _log_box(h=220) -> QPlainTextEdit:
    b = QPlainTextEdit()
    b.setReadOnly(True)
    b.setFont(mono_font(10))
    b.setMaximumHeight(h)
    b.hide()
    return b


# =====================================================================
# Try it
# =====================================================================

class TryItCard(Card):
    """One runnable concept program. Files persist in cpp/learn/work/tryit/<id>/."""

    def __init__(self, tid: str, parent=None):
        self.t = concepts.TRYITS[tid]
        super().__init__(f"Try it · {self.t.title}", parent)
        self.gxx = cc.find_gxx()
        self.dir = concepts.ensure_tryit(self.t)
        self._busy = False
        self._ran = False

        if self.t.intro:
            self.add(body(self.t.intro))
        if self.t.predict:
            self.add(body(f"<b style='color:{theme.WARN}'>Predict first.</b> {self.t.predict}"))

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.b_run = _btn("Run  (Ctrl+Enter)", True, "compile with g++ and run it")
        bar.addWidget(self.b_run)
        self.b_pre = None
        if self.t.preprocess:
            self.b_pre = _btn(f"{self.t.preprocess} after the preprocessor",
                              tip="g++ -E: the one file the compiler actually receives")
            bar.addWidget(self.b_pre)
        self.b_reset = _btn("Reset", tip="put the original program back (all files)")
        self.b_folder = _btn("Open folder")
        bar.addWidget(self.b_reset)
        bar.addWidget(self.b_folder)
        bar.addStretch(1)
        self.add_layout(bar)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.editors = {}
        longest = 0
        for n, _ in self.t.files:
            with open(os.path.join(self.dir, n), encoding="utf-8") as f:
                text = f.read()
            ed = CppEditor(text)
            ed.run_requested.connect(self.run)
            ed.textChanged.connect(self._schedule_save)
            self.editors[n] = ed
            self.tabs.addTab(ed, n)
            longest = max(longest, len(text.splitlines()))
        first = next(iter(self.editors.values()))
        self.tabs.setMinimumHeight(min(_code_height(first, longest) + 34, 640))
        self.add(self.tabs)

        self.status = body("")
        self.add(self.status)
        self.links = body("")
        self.links.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.links.linkActivated.connect(self._jump)
        self.links.hide()
        self.add(self.links)
        self.decoded = body("")
        self.decoded.hide()
        self.add(self.decoded)
        self.out = _log_box(300)
        self.add(self.out)
        self.after = body(f"<b style='color:{theme.GOOD}'>What happened.</b> {self.t.after}")
        self.after.hide()
        self.add(self.after)
        if self.t.tasks:
            items = "".join(f"<li style='margin-bottom:5px'>{x}</li>" for x in self.t.tasks)
            self.tasks = body(f"<b>Then change it and run again:</b><ol style='margin-top:4px'>{items}</ol>"
                              f"<span style='color:{theme.TEXT_FAINT}'>Reset puts the original back.</span>")
            self.add(self.tasks)

        self.b_run.clicked.connect(self.run)
        if self.b_pre:
            self.b_pre.clicked.connect(self.preprocess)
        self.b_reset.clicked.connect(self.reset)
        self.b_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.dir)))
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self.save)
        if self.gxx is None:
            self._status("No C++ compiler found: install MinGW-w64 (g++) and put its bin folder on PATH.",
                         theme.BAD)

    # ---- files ---------------------------------------------------------
    def _schedule_save(self):
        self._save_timer.start()

    def save(self):
        self._save_timer.stop()
        for n, ed in self.editors.items():
            with open(os.path.join(self.dir, n), "w", encoding="utf-8", newline="\n") as f:
                f.write(ed.toPlainText())

    def reset(self):
        files = concepts.reset_tryit(self.t)
        for n, ed in self.editors.items():
            ed.blockSignals(True)
            ed.setPlainText(files[n])
            ed.blockSignals(False)
            ed.set_diagnostics({})
        self.links.hide()
        self.decoded.hide()
        self.out.hide()
        self._status("Back to the original.", theme.TEXT_DIM)

    # ---- feedback ------------------------------------------------------
    def _status(self, text, colour=None):
        self.status.setText(f"<span style='color:{colour or theme.TEXT}'>{text}</span>")

    def _set_busy(self, busy, msg=""):
        self._busy = busy
        self.b_run.setEnabled(not busy)
        if self.b_pre:
            self.b_pre.setEnabled(not busy)
        if msg:
            self._status(msg, theme.CYAN)

    def _jump(self, target):
        f, line = target.rsplit(":", 1)
        if f in self.editors:
            self.tabs.setCurrentWidget(self.editors[f])
            self.editors[f].goto_line(int(line) - 1)

    def _show_errors(self, log):
        log = cc.clean_log(log.replace(self.dir + os.sep, ""))
        per_file, links = {}, []
        for f, line, col, kind, msg in cc.diagnostics(log):
            if kind in ("error", "fatal error") and f in self.editors:
                per_file.setdefault(f, {}).setdefault(line - 1, msg)
            if kind in ("error", "fatal error", "link") and len(links) < 6:
                where = (f"<a style='color:{theme.CYAN}' href='{f}:{line}'>{f}:{line}</a> " if f
                         else f"<b style='color:{theme.ORANGE}'>linker</b> ")
                links.append(where + html.escape(msg))
        for f, ed in self.editors.items():
            ed.set_diagnostics(per_file.get(f, {}))
        linker = "undefined reference" in log or "multiple definition" in log
        self._status("<b>Linker error.</b> Every file compiled; joining them failed." if linker and not per_file
                     else "<b>Compile error.</b> The red line is where g++ noticed; click a location to jump.",
                     theme.BAD)
        self.links.setText("<br>".join(links))
        self.links.setVisible(bool(links))
        d = decoded_html(log)
        self.decoded.setText(d)
        self.decoded.setVisible(bool(d))
        self.out.setPlainText(log[-10000:])
        self.out.show()
        if per_file:
            f = next(iter(per_file))
            self.tabs.setCurrentWidget(self.editors[f])

    def _clear(self):
        for ed in self.editors.values():
            ed.set_diagnostics({})
        self.links.hide()
        self.decoded.hide()

    # ---- actions -------------------------------------------------------
    def run(self):
        if self._busy or self.gxx is None:
            return
        self.save()
        self._clear()
        argv, cwd, exe = concepts.tryit_build(self.t, self.gxx)
        self._set_busy(True, "compiling with g++ …")

        def compiled(out):
            rc, text = out[0]
            if rc != 0:
                self._set_busy(False)
                self._show_errors(text)
                return
            warn = cc.clean_log(text).strip()
            self._status("running …", theme.CYAN)
            self._chain = _Chain(self, [[exe]], lambda o: ran(o, warn), timeout_ms=10000, cwd=cwd)

        def ran(out, warn):
            rc, text = out[0]
            self._set_busy(False)
            shown = text.rstrip("\n")
            if warn:
                shown = "g++ warnings:\n" + warn + "\n\n---- the program printed ----\n" + shown
                d = decoded_html(warn)
                self.decoded.setText(d)
                self.decoded.setVisible(bool(d))
            self.out.setPlainText(shown + ("" if rc == 0 else f"\n[exit code {rc}]"))
            self.out.show()
            if rc == 0:
                self._status("It ran. The output is below." + (" g++ also printed a warning; read it."
                                                                 if warn else ""), theme.GOOD)
            else:
                self._status(f"The program stopped with exit code {rc}: it crashed or aborted.", theme.WARN)
            if not self._ran:
                self._ran = True
                self.after.show()

        self._chain = _Chain(self, [argv], compiled, timeout_ms=120000, cwd=cwd)

    def preprocess(self):
        if self._busy or self.gxx is None:
            return
        self.save()
        self._clear()
        name = self.t.preprocess
        self._set_busy(True, f"g++ -E {name} …")

        def done(out):
            rc, text = out[0]
            self._set_busy(False)
            if rc != 0:
                self._show_errors(text)
                return
            view = concepts.user_view(text, self.dir)
            self.out.setPlainText(f"// {name} as the compiler receives it: every #include replaced by the "
                                  f"text of that file.\n\n" + view)
            self.out.setMaximumHeight(420)
            self.out.show()
            self._status("This is the translation unit. No #include and no #pragma are left: the "
                         "preprocessor has done its pasting.", theme.GOOD)

        self._chain = _Chain(self, [concepts.preprocess_argv(name, self.gxx)], done, timeout_ms=60000,
                             cwd=self.dir)


# =====================================================================
# the linkage table
# =====================================================================

_STAGE_STYLE = {
    "ok": (theme.GOOD, "✓ builds and runs"),
    "wrong": (theme.VIOLET, "runs, WRONG answer"),
    "link": (theme.ORANGE, "linker error"),
    "compile": (theme.BAD, "compile error"),
}


class LinkTable(Card):
    """Pick what helpers.hpp and helpers.cpp contain; see which stage objects and why."""

    def __init__(self, parent=None):
        super().__init__("What goes in the header, what goes in the .cpp?", parent)
        self.add(body(
            "The setup of Exercise 0.2: <code>motor.cpp</code>, <code>sensor.cpp</code> and "
            "<code>main.cpp</code> all <code>#include \"helpers.hpp\"</code>, and all use "
            "<code>g_ticks</code> and <code>clamp</code>. So does <code>helpers.cpp</code>. That makes four "
            "translation units, each compiled alone. Each row is a choice for the <b>header</b> and each "
            "column a choice for <b>helpers.cpp</b>. Click a cell to see what g++ does. Every cell "
            "was produced by the real compiler, and <b>Build it for real</b> runs it again in front of "
            "you."))
        kinds = QHBoxLayout()
        self.kind_btns = {}
        grp = QButtonGroup(self)
        for k in ("var", "fn"):
            b = QPushButton(concepts.LINK[k]["title"])
            b.setCheckable(True)
            grp.addButton(b)
            b.clicked.connect(lambda _=False, k=k: self.set_kind(k))
            kinds.addWidget(b)
            self.kind_btns[k] = b
        kinds.addStretch(1)
        self.add_layout(kinds)

        self.grid_host = QWidget()
        self.grid_host.setStyleSheet("background:transparent;")
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 4, 0, 4)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(6)
        self.add(self.grid_host)

        self.verdict = body("")
        self.add(self.verdict)
        row = QHBoxLayout()
        self.hpp = CppEditor("", read_only=True)
        self.cpp = CppEditor("", read_only=True)
        for title, ed in (("helpers.hpp", self.hpp), ("helpers.cpp", self.cpp)):
            box = Card(title, pad=8, spacing=4)
            ed.setFixedHeight(_code_height(ed, 4))
            box.add(ed)
            row.addWidget(box, 1)
        self.add_layout(row)
        bar = QHBoxLayout()
        self.b_build = _btn("Build it for real", tip="write these five files and run g++ on all four .cpp")
        self.b_build.clicked.connect(self.build)
        bar.addWidget(self.b_build)
        bar.addStretch(1)
        self.add_layout(bar)
        self.real = _log_box(200)
        self.add(self.real)
        self.kind, self.cell = "var", (1, 1)
        self.kind_btns["var"].setChecked(True)
        self.set_kind("var")

    def set_kind(self, kind):
        self.kind = kind
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        spec = concepts.LINK[kind]
        corner = QLabel("helpers.hpp ↓   ·   helpers.cpp →")
        corner.setStyleSheet(f"color:{theme.TEXT_FAINT}; background:transparent;")
        self.grid.addWidget(corner, 0, 0)
        for c, (label, _) in enumerate(spec["cpp"]):
            lb = QLabel(label)
            lb.setFont(mono_font(10))
            lb.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
            self.grid.addWidget(lb, 0, c + 1, alignment=Qt.AlignCenter)
        self.cells = {}
        group = QButtonGroup(self.grid_host)
        for h, (label, _) in enumerate(spec["header"]):
            lb = QLabel(label)
            lb.setFont(mono_font(10))
            lb.setStyleSheet(f"color:{theme.TEXT}; background:transparent;")
            self.grid.addWidget(lb, h + 1, 0)
            for c in range(len(spec["cpp"])):
                cell = spec["cells"][(h, c)]
                colour, text = _STAGE_STYLE[cell.stage]
                b = QPushButton(text)
                b.setCheckable(True)
                b.setMinimumWidth(170)
                b.setStyleSheet(
                    f"QPushButton {{ color:{colour}; border:1px solid {colour}55; border-radius:5px; "
                    f"padding:5px 10px; background:{theme.BG_INPUT}; }}"
                    f"QPushButton:checked {{ background:{colour}33; border:2px solid {colour}; }}")
                b.clicked.connect(lambda _=False, h=h, c=c: self.select(h, c))
                group.addButton(b)
                self.grid.addWidget(b, h + 1, c + 1)
                self.cells[(h, c)] = b
        self.grid.setColumnStretch(len(spec["cpp"]) + 1, 1)
        self.select(1, 1)

    def select(self, h, c):
        self.cell = (h, c)
        self.cells[(h, c)].setChecked(True)
        cell = concepts.LINK[self.kind]["cells"][(h, c)]
        colour, text = _STAGE_STYLE[cell.stage]
        files = concepts.link_files(self.kind, h, c)
        self.hpp.setPlainText(files["helpers.hpp"].rstrip("\n"))
        self.cpp.setPlainText(files["helpers.cpp"].rstrip("\n"))
        who = {"compile": "The compiler stops", "link": "Every file compiles; the linker stops",
               "ok": "It builds and prints", "wrong": "No error at all"}[cell.stage]
        self.verdict.setText(
            f"<b style='color:{colour}'>{text}.</b> {who}: "
            f"<code style='color:{colour}'>{html.escape(cell.message)}</code><br>{cell.why}")
        self.real.hide()

    def build(self):
        gxx = cc.find_gxx()
        if gxx is None:
            return
        d = os.path.join(cc.BUILD, "linktable")
        os.makedirs(d, exist_ok=True)
        for n, text in concepts.link_files(self.kind, *self.cell).items():
            with open(os.path.join(d, n), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        exe = os.path.join(d, "a" + (".exe" if os.name == "nt" else ""))
        if os.path.exists(exe):
            os.remove(exe)
        argv = [gxx, *cc.CXXFLAGS, "helpers.cpp", "motor.cpp", "sensor.cpp", "main.cpp", "-o", exe]
        self.b_build.setEnabled(False)
        self.real.setPlainText("$ g++ helpers.cpp motor.cpp sensor.cpp main.cpp\n…")
        self.real.show()

        def compiled(out):
            rc, text = out[0]
            text = cc.clean_log(text).replace(d + os.sep, "")
            if rc != 0:
                self.b_build.setEnabled(True)
                self.real.setPlainText("$ g++ helpers.cpp motor.cpp sensor.cpp main.cpp\n" + text)
                return
            self._chain = _Chain(self, [[exe]], lambda o: ran(o, text), timeout_ms=10000, cwd=d)

        def ran(out, warn):
            self.b_build.setEnabled(True)
            self.real.setPlainText("$ g++ helpers.cpp motor.cpp sensor.cpp main.cpp\n" + warn
                                   + "(built)\n$ ./a\n" + out[0][1])

        self._chain = _Chain(self, [argv], compiled, timeout_ms=120000, cwd=d)


# =====================================================================
# error decoder
# =====================================================================

class ErrorDecoder(Card):
    """Paste a message, or browse; each entry can compile its own example to show the real text."""

    def __init__(self, parent=None):
        super().__init__("Error decoder: what g++ is really telling you", parent)
        self.add(body(
            "g++ messages are precise but terse. Paste one below (from this tutor, VS Code or a "
            "terminal), or pick one from the list. Each entry says what the message usually means and "
            "has a tiny program that produces it. The exercises and Try-it cards use the same decoder "
            "automatically when your code fails to build. <b>Read the first error first</b>: later ones "
            "are often knock-on effects of it."))
        self.paste = QPlainTextEdit()
        self.paste.setPlaceholderText("paste a g++ error here, e.g.  pid.cpp:20:19: error: qualified-id in "
                                      "declaration before '(' token")
        self.paste.setFont(mono_font(10))
        self.paste.setMaximumHeight(90)
        self.paste.textChanged.connect(self._decode_paste)
        self.add(self.paste)
        self.found = body("")
        self.add(self.found)

        row = QHBoxLayout()
        lb = QLabel("Browse:")
        lb.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
        row.addWidget(lb)
        self.pick = QComboBox()
        for e in concepts.ERRORS.values():
            self.pick.addItem(e.title, e.id)
        self.pick.currentIndexChanged.connect(self._show_pick)
        row.addWidget(self.pick, 1)
        self.b_compile = _btn("Compile this example", tip="run g++ on it and show the real message")
        self.b_compile.clicked.connect(self._compile)
        row.addWidget(self.b_compile)
        self.add_layout(row)
        self.meaning = body("")
        self.add(self.meaning)
        self.example = CppEditor("", read_only=True)
        self.add(self.example)
        self.real = _log_box(220)
        self.add(self.real)
        self._show_pick(0)

    def _decode_paste(self):
        text = self.paste.toPlainText()
        if not text.strip():
            self.found.setText("")
            return
        hints = concepts.decode(text, limit=4)
        self.found.setText(decoded_html(text) if hints else
                           f"<span style='color:{theme.TEXT_DIM}'>Not one I know. Read it from the left: "
                           f"<i>file:line:column: error:</i> then the message. The first error is the one "
                           f"to fix.</span>")

    def _show_pick(self, i):
        e = concepts.ERRORS[self.pick.itemData(i)]
        self.meaning.setText(f"<b style='color:{theme.CYAN}'>{html.escape(e.title)}.</b> {e.meaning}<br>"
                             f"<span style='color:{theme.TEXT_FAINT}'>g++ says something matching: "
                             f"<code>{html.escape(e.pattern)}</code></span>")
        text = "\n\n".join((f"// ---- {n} ----\n" if len(e.example) > 1 else "") + t.rstrip("\n")
                           for n, t in e.example)
        self.example.setPlainText(text)
        self.example.setFixedHeight(_code_height(self.example, len(text.splitlines())))
        self.real.hide()

    def _compile(self):
        gxx = cc.find_gxx()
        if gxx is None:
            return
        e = concepts.ERRORS[self.pick.currentData()]
        d = concepts.example_dir(e)
        os.makedirs(d, exist_ok=True)
        for n, t in e.example:
            with open(os.path.join(d, n), "w", encoding="utf-8", newline="\n") as f:
                f.write(t)
        self.b_compile.setEnabled(False)
        self.real.setPlainText("…")
        self.real.show()

        def done(out):
            self.b_compile.setEnabled(True)
            text = cc.clean_log(out[0][1]).replace(d + os.sep, "")
            self.real.setPlainText(text or "(no output)")

        self._chain = _Chain(self, [concepts.example_argv(e, gxx)], done, timeout_ms=120000, cwd=d)


# =====================================================================
# C++ next to Python
# =====================================================================

_PY = [
    ("import numpy", "#include &lt;vector&gt;",
     "import runs a module once and gives you a name. #include <i>pastes the file's text</i> into this "
     ".cpp, every time, before compiling."),
    ("one .py file", "a .hpp (the contract) + a .cpp (the code)",
     "Other files see only the header. The .cpp is compiled once, on its own."),
    ("x = 1.0", "double x = 1.0;",
     "Every variable has a fixed type, decided at compile time. <code>auto x = 1.0;</code> lets the "
     "compiler write the type for you, and it is still fixed."),
    ("class Pid:", "class Pid { … };",
     "Members (the variables) are declared in the class, not created in <code>__init__</code>. Do not "
     "forget the <code>;</code>."),
    ("def __init__(self, kp):", "Pid(double kp) : kp_(kp) {}",
     "The constructor has the class's name and no return type. Members are set in the "
     "<i>initializer list</i> after the colon."),
    ("self.kp", "kp_  (really this->kp_)",
     "<code>this</code> is a pointer to the current object, passed in hidden. You rarely write it."),
    ("def update(self, e):", "double update(double e);   +   double Pid::update(double e) { … }",
     "Declared in the class (header), defined outside it with <code>Pid::</code> (\"belongs to Pid\")."),
    ("_private (a convention)", "private:",
     "Enforced by the compiler: outside code that touches it does not compile."),
    ("__del__ (some time later)", "~Pid()  (at the closing brace, exactly)",
     "Destructors run at a known line. That is what makes RAII reliable."),
    ("everything is a reference", "values by default; T&amp; and T* when you ask",
     "<code>Pid b = a;</code> makes a <b>copy</b>, a second independent Pid. In Python, "
     "<code>b = a</code> is a second name for one object."),
    ("garbage collector", "owners: stack scope, vector, unique_ptr",
     "No GC: every object has an owner that destroys it. <code>new</code> without an owner is a leak."),
    ("errors when the line runs", "errors before anything runs",
     "Type mistakes, missing members and wrong signatures are found by the compiler and linker."),
]


def python_table() -> Card:
    c = Card("If you know Python: the same ideas, C++ spelling")
    rows = "".join(
        f"<tr><td style='padding:4px 10px 4px 0;color:{theme.TEXT_DIM}'><code>{py}</code></td>"
        f"<td style='padding:4px 10px'><code style='color:{theme.CYAN}'>{cpp}</code></td>"
        f"<td style='padding:4px 0 4px 10px'>{why}</td></tr>" for py, cpp, why in _PY)
    c.add(body(f"<table cellspacing='0'><tr><th align='left'>Python</th><th align='left'>C++</th>"
               f"<th align='left'>the difference that matters</th></tr>{rows}</table>"))
    return c
