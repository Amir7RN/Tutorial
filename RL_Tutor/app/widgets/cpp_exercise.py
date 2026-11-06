"""
ExerciseCard -- one graded C++ exercise: task, editor tabs, check/run, results.

The learner's files live in cpp/learn/work/<id>/ and are saved as they type,
so any outside editor (VS Code, CLion) works on the same files; a change made
outside is picked up when the editor here has no unsaved typing.

Builds run in QProcess, one step at a time, so the window never freezes:
compile -> run -> parse PASS/FAIL lines -> next step (mutation exercises have
five). Compiler errors become red dots in the gutter and clickable links that
jump to the line.
"""

from __future__ import annotations

import html
import os
import time

from PySide6.QtCore import QFileSystemWatcher, QProcess, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTabWidget,
                               QVBoxLayout, QWidget)

from ctrlcore import cpp_course as cc
from .. import theme
from .common import Card, body
from .cpp_editor import CppEditor, mono_font

RUN_TIMEOUT_MS = 20000


def _btn(text, primary=False, tip=""):
    b = QPushButton(text)
    if primary:
        b.setObjectName("Primary")
    if tip:
        b.setToolTip(tip)
    return b


class _Chain:
    """Run a list of argv lists one after another; call done(list_of_(rc, out))."""

    def __init__(self, parent, cmds, done, timeout_ms=RUN_TIMEOUT_MS):
        self.parent, self.cmds, self.done, self.timeout = parent, list(cmds), done, timeout_ms
        self.out = []
        self.proc = None
        self._next()

    def _next(self):
        if not self.cmds:
            self.done(self.out)
            return
        argv = self.cmds.pop(0)
        p = self.proc = QProcess(self.parent)
        p.setProcessChannelMode(QProcess.MergedChannels)
        self.timer = QTimer(self.parent)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(p.kill)
        p.finished.connect(self._finished)
        p.errorOccurred.connect(self._error)
        p.start(argv[0], argv[1:])
        self.timer.start(self.timeout)

    def _error(self, err):
        if err == QProcess.FailedToStart:
            self.timer.stop()
            self.out.append((-1, f"could not start {self.proc.program()}"))
            self.cmds = []
            self.done(self.out)

    def _finished(self, code, status):
        self.timer.stop()
        text = bytes(self.proc.readAll()).decode("utf-8", "replace")
        if status == QProcess.CrashExit and not text:
            text = ""
        self.out.append((code if status == QProcess.NormalExit else -1, text))
        self.proc.deleteLater()
        self._next()


class ExerciseCard(Card):
    """Everything for one exercise. Emits `passed(ex_id, ok)` after each check."""

    passed = Signal(str, bool)

    def __init__(self, ex_id: str, number: str = "", parent=None):
        self.ex = cc.EXERCISES[ex_id]
        super().__init__(f"Exercise {number} · {self.ex.title}" if number else self.ex.title, parent)
        self.gxx = cc.find_gxx()
        self.dir = cc.ensure_work(self.ex)
        self._busy = False
        self._hint = 0
        self._saved = {}

        top = QHBoxLayout()
        self.chip = QLabel()
        top.addWidget(self.chip)
        top.addStretch(1)
        self.add_layout(top)

        self.add(body(self.ex.task))

        # ---- toolbar -----------------------------------------------------
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.b_check = _btn("Check  (Ctrl+Enter)", True, "compile with the tests and grade")
        self.b_run = _btn("Run main", tip="build your files with your main.cpp and show what it prints")
        self.b_hint = _btn("Hint")
        self.b_sol = _btn("Show solution")
        self.b_reset = _btn("Reset this file", tip="put the starter version of the open file back")
        self.b_folder = _btn("Open folder", tip="the files are on disk -- edit them in VS Code if you prefer")
        for b in (self.b_check, self.b_run, self.b_hint, self.b_sol, self.b_reset, self.b_folder):
            bar.addWidget(b)
        bar.addStretch(1)
        self.add_layout(bar)
        names = cc.editable_names(self.ex)
        self.b_run.setVisible("main.cpp" in names)

        if self.ex.tools:
            tools = QHBoxLayout()
            tools.setSpacing(6)
            lb = QLabel("What the compiler sees, for the open file:")
            lb.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
            tools.addWidget(lb)
            self.b_pre = _btn("after the preprocessor  (g++ -E)")
            self.b_sym = _btn("symbols in its object file  (nm -C)")
            tools.addWidget(self.b_pre)
            tools.addWidget(self.b_sym)
            tools.addStretch(1)
            self.add_layout(tools)
            self.b_pre.clicked.connect(lambda: self._tool("preprocess"))
            self.b_sym.clicked.connect(lambda: self._tool("symbols"))

        # ---- editors -----------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.editors = {}
        for n in names:
            text = self._read(n)
            ed = CppEditor(text)
            ed.run_requested.connect(self.check)
            ed.save_requested.connect(self.save_all)
            ed.textChanged.connect(self._schedule_save)
            self.editors[n] = ed
            self._saved[n] = text
            self.tabs.addTab(ed, n)
        for n, path in cc.given_files(self.ex).items():
            with open(path, encoding="utf-8") as f:
                ed = CppEditor(f.read(), read_only=True)
            self.tabs.addTab(ed, f"{n}  (given)")
        h = max(320, min(620, 22 * max(len(t.splitlines()) for t in self._saved.values()) + 30))
        self.tabs.setMinimumHeight(h)
        self.add(self.tabs)
        keys = body("<span style='color:%s'>Tab / Shift+Tab indent · Enter keeps indentation · "
                    "Ctrl+/ comment · Ctrl+D duplicate line · Alt+↑/↓ move line · Ctrl+wheel zoom · "
                    "files save as you type to <code>cpp/learn/work/%s/</code></span>"
                    % (theme.TEXT_FAINT, self.ex.id))
        self.add(keys)

        # ---- feedback ----------------------------------------------------
        self.status = body("")
        self.add(self.status)
        self.results = body("")
        self.results.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.results.linkActivated.connect(self._jump)
        self.results.hide()
        self.add(self.results)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(mono_font(9))
        self.log.setMaximumHeight(240)
        self.log.hide()
        self.add(self.log)
        self.hints = body("")
        self.hints.hide()
        self.add(self.hints)

        self.sol_box = QWidget()
        sl = QVBoxLayout(self.sol_box)
        sl.setContentsMargins(0, 4, 0, 0)
        sl.addWidget(body(f"<b style='color:{theme.GOOD}'>Why it is written this way.</b> {self.ex.explain}"))
        st = QTabWidget()
        st.setDocumentMode(True)
        for n, text in cc.solution_files(self.ex).items():
            if text != cc.starter_files(self.ex).get(n) or n not in ("main.cpp",):
                ed = CppEditor(text, read_only=True)
                st.addTab(ed, n + "  (reference)")
        st.setMinimumHeight(h)
        sl.addWidget(st)
        self.sol_box.hide()
        self.add(self.sol_box)

        # ---- wiring --------------------------------------------------------
        self.b_check.clicked.connect(self.check)
        self.b_run.clicked.connect(self.run_main)
        self.b_hint.clicked.connect(self._next_hint)
        self.b_sol.clicked.connect(self._toggle_solution)
        self.b_reset.clicked.connect(self._reset_current)
        self.b_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.dir)))
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self.save_all)
        self.watch = QFileSystemWatcher([os.path.join(self.dir, n) for n in names], self)
        self.watch.fileChanged.connect(self._disk_changed)

        self._paint_chip(cc.load_progress().get(self.ex.id))
        if self.gxx is None:
            self._status("No C++ compiler found. Install MinGW-w64 (g++), put its <code>bin</code> folder "
                         "on PATH, and restart the tutor. You can still read and edit the files.", theme.BAD)

    # ---- files -----------------------------------------------------------
    def _read(self, n):
        with open(os.path.join(self.dir, n), encoding="utf-8") as f:
            return f.read()

    def _schedule_save(self):
        self._save_timer.start()

    def save_all(self):
        self._save_timer.stop()
        for n, ed in self.editors.items():
            text = ed.toPlainText()
            if text != self._saved.get(n):
                p = os.path.join(self.dir, n)
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                self._saved[n] = text
                if p not in self.watch.files():
                    self.watch.addPath(p)

    def _disk_changed(self, path):
        n = os.path.basename(path)
        if path not in self.watch.files() and os.path.exists(path):
            self.watch.addPath(path)
        if n not in self.editors or not os.path.exists(path):
            return
        disk = self._read(n)
        ed = self.editors[n]
        if disk == self._saved.get(n):
            return
        if ed.toPlainText() == self._saved.get(n):      # nothing typed here since the last save
            bar = ed.verticalScrollBar().value()
            ed.blockSignals(True)
            ed.setPlainText(disk)
            ed.blockSignals(False)
            ed.verticalScrollBar().setValue(bar)
            self._saved[n] = disk
            self._status(f"Reloaded {n}: it changed on disk.", theme.TEXT_DIM)

    def _reset_current(self):
        i = self.tabs.currentIndex()
        names = list(self.editors)
        if i >= len(names):
            return
        n = names[i]
        text = cc.reset_file(self.ex, n)
        self._saved[n] = text
        self.editors[n].setPlainText(text)
        self._status(f"{n} is back to the starter version.", theme.TEXT_DIM)

    # ---- feedback ----------------------------------------------------------
    def _status(self, text, colour=None):
        self.status.setText(f"<span style='color:{colour or theme.TEXT}'>{text}</span>")

    def _paint_chip(self, ok):
        if ok:
            t, c = "✓ PASSED", theme.GOOD
        elif ok is False:
            t, c = "not yet", theme.WARN
        else:
            t, c = "not tried", theme.TEXT_FAINT
        self.chip.setText(f"<span style='color:{c}; font-weight:700'>{t}</span>")

    def _next_hint(self):
        hs = self.ex.hints
        self._hint = min(self._hint + 1, len(hs))
        self.hints.setText("<br>".join(f"<b style='color:{theme.WARN}'>Hint {i + 1}.</b> {h}"
                                       for i, h in enumerate(hs[:self._hint])))
        self.hints.show()
        self.b_hint.setText("Hint" if self._hint < len(hs) else "All hints shown")
        self.b_hint.setEnabled(self._hint < len(hs))

    def _toggle_solution(self):
        vis = not self.sol_box.isVisible()
        self.sol_box.setVisible(vis)
        self.b_sol.setText("Hide solution" if vis else "Show solution")

    def _set_busy(self, busy, msg=""):
        self._busy = busy
        for b in (self.b_check, self.b_run):
            b.setEnabled(not busy)
        if msg:
            self._status(msg, theme.CYAN)

    def _clear_marks(self):
        for ed in self.editors.values():
            ed.set_diagnostics({})

    def _show_compile_errors(self, log):
        log = cc.clean_log(log)
        diags = cc.diagnostics(log)
        per_file = {}
        links = []
        for f, line, col, kind, msg in diags:
            if kind in ("error", "fatal error") and f in self.editors:
                per_file.setdefault(f, {}).setdefault(line - 1, msg)
            if kind in ("error", "fatal error", "link") and len(links) < 8:
                where = (f"<a style='color:{theme.CYAN}' href='{f}:{line}:{col}'>{f}:{line}</a> "
                         if f else f"<b style='color:{theme.ORANGE}'>linker</b> ")
                links.append(f"{where}{html.escape(msg)}")
        for f, ed in self.editors.items():
            ed.set_diagnostics(per_file.get(f, {}))
        stage = "Linker error" if diags and all(d[3] == "link" for d in diags if d[3] != "note") and \
            any(d[3] == "link" for d in diags) else "Compile error"
        self._status(f"<b>{stage}.</b> Click a location to jump there; the full message is below.", theme.BAD)
        self.results.setText("<br>".join(links) if links else "")
        self.results.setVisible(bool(links))
        self.log.setPlainText(log[-12000:])
        self.log.show()
        if per_file:
            f = next(iter(per_file))
            self._jump_to(f, min(per_file[f]) + 1, 1)

    def _jump(self, target):
        f, line, col = target.rsplit(":", 2)
        self._jump_to(f, int(line), int(col))

    def _jump_to(self, f, line, col):
        if f in self.editors:
            self.tabs.setCurrentWidget(self.editors[f])
            self.editors[f].goto_line(line - 1, col - 1)

    # ---- check --------------------------------------------------------------
    def check(self):
        if self._busy or self.gxx is None:
            return
        self.save_all()
        self._clear_marks()
        self.log.hide()
        self.results.hide()
        self.steps = cc.plan(self.ex, self.dir, "check", gxx=self.gxx)
        self.report = cc.Report()
        self._t0 = time.perf_counter()
        n = len(self.steps)
        self._set_busy(True, "compiling with g++ …" if n == 1 else f"building your tests {n} times …")
        self._run_step(0)

    def _run_step(self, i):
        if i >= len(self.steps):
            self._finish_check()
            return
        step = self.steps[i]

        def after_compile(out):
            rc, text = out[0]
            if rc != 0:
                self.report.compiled = False
                self._set_busy(False)
                self._show_compile_errors(text)
                self._record(False)
                return
            if len(self.steps) > 1:
                self._status(f"running against {step.label} …", theme.CYAN)
            self._chain = _Chain(self, [[step.exe]], lambda o: after_run(o))

        def after_run(out):
            rc, text = out[0]
            cc.grade_step(step, rc, text, self.report)
            self._run_step(i + 1)

        self._chain = _Chain(self, [step.compile], after_compile, timeout_ms=120000)

    def _finish_check(self):
        rep = self.report
        rep.results += cc.check_rules(self.ex, self.dir)
        self._set_busy(False)
        n_ok = sum(r.ok for r in rep.results)
        rows = []
        for r in rep.results:
            mark = f"<span style='color:{theme.GOOD}'>✓</span>" if r.ok else f"<span style='color:{theme.BAD}'>✗</span>"
            why = "" if r.ok or not r.why else f" <span style='color:{theme.TEXT_DIM}'>— {html.escape(r.why)}</span>"
            rows.append(f"{mark} {html.escape(r.name)}{why}")
        self.results.setText("<br>".join(rows))
        self.results.show()
        dt = time.perf_counter() - self._t0
        if rep.passed:
            self._status(f"<b>All {n_ok} checks pass</b> ({dt:.1f} s). Open the solution and compare: "
                         "every difference is a decision worth a sentence.", theme.GOOD)
        else:
            self._status(f"<b>{n_ok} / {len(rep.results)} checks pass.</b> Read the first ✗; it is "
                         "usually the cause of the others.", theme.WARN)
        if rep.output.strip():
            self.log.setPlainText("Your code printed:\n" + rep.output[-6000:])
            self.log.show()
        self._record(rep.passed)

    def _record(self, ok):
        cc.mark_passed(self.ex.id, ok)
        self._paint_chip(cc.load_progress().get(self.ex.id))
        self.passed.emit(self.ex.id, ok)

    # ---- run your main -------------------------------------------------------
    def run_main(self):
        if self._busy or self.gxx is None:
            return
        self.save_all()
        self._clear_marks()
        self.results.hide()
        step = cc.plan(self.ex, self.dir, "run", gxx=self.gxx)[0]
        self._set_busy(True, "compiling your main.cpp …")

        def after_compile(out):
            rc, text = out[0]
            if rc != 0:
                self._set_busy(False)
                self._show_compile_errors(text)
                return
            self._status("running …", theme.CYAN)
            self._chain = _Chain(self, [[step.exe]], after_run, timeout_ms=10000)

        def after_run(out):
            rc, text = out[0]
            self._set_busy(False)
            self.log.setPlainText(text[-20000:] + f"\n[exit code {rc}]")
            self.log.show()
            self._status("Your program ran. Its output is below." if rc == 0 else
                         f"Your program exited with code {rc} (a crash shows as a large number).",
                         theme.TEXT if rc == 0 else theme.WARN)

        self._chain = _Chain(self, [step.compile], after_compile, timeout_ms=120000)

    # ---- compiler's-eye tools --------------------------------------------------
    def _tool(self, which):
        if self._busy or self.gxx is None:
            return
        i = self.tabs.currentIndex()
        names = list(self.editors)
        n = names[i] if i < len(names) else names[0]
        self.save_all()
        cmds = cc.tool_command(self.ex, self.dir, n, which)
        self._set_busy(True, f"running {'g++ -E' if which == 'preprocess' else 'g++ -c, then nm -C'} on {n} …")

        def done(out):
            self._set_busy(False)
            rc, text = out[-1]
            if any(o[0] != 0 for o in out):
                self._show_compile_errors("\n".join(t for _, t in out))
                return
            text = cc.clean_log(text)
            if which == "preprocess":
                lines = [ln for ln in text.splitlines() if ln.strip()]
                head = (f"// {n} after the preprocessor: every #include pasted in, every macro expanded.\n"
                        f"// This is the ONE translation unit the compiler actually compiles. "
                        f"{len(lines)} non-blank lines.\n\n")
                text = head + "\n".join(lines[-1500:])
            else:
                head = (f"symbols in {os.path.splitext(n)[0]}.o\n"
                        "  T = function defined here     B/D = variable defined here\n"
                        "  U = used here, defined in some OTHER object (the linker must find it)\n"
                        "  W/V = weak: inline/template code; duplicates are merged, not an error\n\n")
                keep = [ln for ln in text.splitlines()
                        if not any(s in ln for s in ("__", ".refptr", "std::", "_Z", "atexit", "operator new",
                                                     "operator delete"))]
                text = head + "\n".join(keep)
            self.log.setPlainText(text)
            self.log.show()
            self._status(f"Shown below: {n} as the {'compiler' if which == 'preprocess' else 'linker'} sees it.",
                         theme.TEXT_DIM)

        self._chain = _Chain(self, cmds, done, timeout_ms=60000)
