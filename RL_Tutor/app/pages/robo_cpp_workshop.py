"""
Page 125 -- C++ workshop: implement the RRPR arm yourself.

Ten exercises take one spatial RRPR robot from [ω] to Jacobians, statics and a
finite-difference check. The learner edits cpp/workshop/my_rrpr.cpp (here or in
any editor); "check my code" compiles it with g++ and a generated test main(),
grades every number against ctrlcore.robokin (ctrlcore/rrpr_check.py) and names
the mistake when it recognises one. A last lab runs the learner's fkSpace and
jacobianSpace at a slider pose and draws them over the true arm.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import subprocess
import time

import numpy as np
from PySide6.QtCore import QFileSystemWatcher, QProcess, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextEdit,
                               QWidget)

from ctrlcore import robokin as rk
from ctrlcore import rrpr_check as rc
from .. import theme
from ..widgets import Card, CodePane, MplCanvas, body
from ..widgets.code import CppHighlighter
from .base import Page
from .robo_common import SEC_KIN, deg, labelled_slider, plain, playlist_badge, start_here
from .robo_space_rigid import PINK, _block_html, _frame3d, in_words
from .robo_space_topo import _clear, _layout
from . import rrpr_render as rr

MONO = "font-family:Consolas"


def _mono_font(size=11):
    f = QFont("Cascadia Mono", size)
    if not f.exactMatch():
        f = QFont("Consolas", size)
    f.setStyleHint(QFont.Monospace)
    return f


def _small_mat(A, ref=None, tol=1e-6):
    """A compact HTML matrix; entries that differ from `ref` in red."""
    A = np.atleast_2d(A)
    if ref is not None:
        ref = np.atleast_2d(ref)
    rows = ""
    for i, r in enumerate(A):
        cells = ""
        for j, x in enumerate(r):
            bad = ref is not None and (not np.isfinite(x) or abs(x - ref[i, j]) > tol * (1 + abs(ref[i, j])))
            col = theme.BAD if bad else theme.TEXT
            cells += f"<td style='padding:0 5px; text-align:right; color:{col}'>{x + 0.0:+.4f}</td>"
        rows += f"<tr>{cells}</tr>"
    return (f"<table style='{MONO}; border-left:1px solid {theme.BORDER}; "
            f"border-right:1px solid {theme.BORDER}'>{rows}</table>")


def _side_by_side(exp, got):
    e = np.atleast_2d(exp) if np.ndim(exp) == 2 else np.atleast_2d(exp).T
    g = np.atleast_2d(got) if np.ndim(got) == 2 else np.atleast_2d(got).T
    return (f"<table><tr><td style='color:{theme.TEXT_DIM}'>expected</td><td></td>"
            f"<td style='color:{theme.TEXT_DIM}'>yours (wrong entries red)</td></tr>"
            f"<tr><td>{_small_mat(e)}</td><td width='18'></td><td>{_small_mat(g, e)}</td></tr></table>")


# ==========================================================================
# the exercises, as text
# ==========================================================================

EXERCISES = [
    dict(ex=1, why=(
        "[ω] turns a cross product into a matrix product: ω × x = [ω]x. "
        "Rodrigues, G(θ), the adjoint and the 4 × 4 twist matrix [V] are all "
        "built out of it, so it comes first. unskew is the reverse trip, and "
        "you will need it in exercise 10 to read ω out of a matrix."),
        formula=_block_html("[ω] = ⎡  0  −ω₃   ω₂ ⎤", "skew(w) * x == cross(w, x)",
                            "      ⎢ ω₃    0  −ω₁ ⎥<br>      ⎣−ω₂   ω₁    0 ⎦",
                            "unskew(skew(w)) == w"),
        sig="Mat3 skew(const Vec3& w);\nVec3 unskew(const Mat3& W);",
        hint=("Build the matrix with a brace list, row by row: "
              "<code>return {{{0.0, -w[2], w[1]}, {...}, {...}}};</code>. The diagonal is "
              "zero and the matrix is antisymmetric (Wᵀ = −W), so you only need to "
              "think about three numbers.")),
    dict(ex=2, why=(
        "A rotation by θ about a unit axis ω̂ (page 120). The formula only needs "
        "[ω̂] and [ω̂]²; no angles about x, y, z and no gimbal lock. Check "
        "yourself: expRot(z, 90°) must send the x-axis to the y-axis."),
        formula=_block_html("R = e<sup>[ω̂]θ</sup>", "= I + sin θ [ω̂] + (1 − cos θ) [ω̂]²",
                            "RᵀR = I, det R = 1", "θ = 0 ⇒ R = I"),
        sig="Mat3 expRot(const Vec3& omegaHat, double theta);",
        hint=("mrlite gives you <code>eye&lt;3&gt;()</code>, <code>A * B</code>, "
              "<code>A + B</code> and <code>s * A</code>, so the C++ reads like the "
              "formula: <code>eye&lt;3&gt;() + std::sin(theta) * K + ...</code>.")),
    dict(ex=3, why=(
        "T = (R, p) holds a whole pose in one 4 × 4 matrix (page 121). Its "
        "inverse never needs a general matrix inverse: R is orthogonal, so "
        "R⁻¹ = Rᵀ, and the shift has to be undone in the rotated frame."),
        formula=_block_html("T = ⎡ R  p ⎤<br>&nbsp;&nbsp;&nbsp;&nbsp;⎣ 0  1 ⎦",
                            "T⁻¹ = ⎡ Rᵀ  −Rᵀp ⎤<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;⎣ 0     1 ⎦",
                            "T[i][3] = p[i]", "rotPart(T), posPart(T) are in mrlite"),
        sig="Mat4 makeT(const Mat3& R, const Vec3& p);\nMat4 invT(const Mat4& T);",
        hint=("Start from <code>Mat4 T = eye&lt;4&gt;();</code> so the bottom row is "
              "already (0, 0, 0, 1), then copy R and p in with two loops. For invT, "
              "<code>transpose(rotPart(T))</code> and <code>-(Rt * posPart(T))</code>.")),
    dict(ex=4, why=(
        "One 6-vector per joint says everything that joint can do (pages "
        "121–123). A revolute joint spinning at 1 rad/s about a unit axis ω "
        "through q moves the point at the {s} origin with velocity −ω × q. A "
        "prismatic joint does not spin at all. Read the four axes and M off "
        "the robot card above and type them in."),
        formula=_block_html("revolute: S = (ω, −ω × q)", "prismatic: S = (0, v)",
                            "S₁ … S₄ from the robot card", "M = (diag(1, −1, −1), (1.5, 0, 0.8))"),
        sig=("Vec6 revoluteAxis(const Vec3& omega, const Vec3& q);\nVec6 prismaticAxis(const Vec3& v);\n"
             "std::array<Vec6, 4> rrprScrewsSpace();\nMat4 rrprHome();"),
        hint=("<code>stack(a, b)</code> glues two Vec3 into a Vec6 and <code>cross</code> "
              "is in mrlite. Work out S₂ by hand once: ω = (0, −1, 0), q = (0, 0, 1) gives "
              "ω × q = (−1, 0, 0), so S₂ = (0, −1, 0, 1, 0, 0).")),
    dict(ex=5, why=(
        "The adjoint changes which frame a twist is written in: "
        "V<sub>s</sub> = [Ad<sub>T<sub>sb</sub></sub>] V<sub>b</sub>. The same "
        "matrix gives the body screw axes, the joint axes as the tool sees "
        "them at home: Bᵢ = [Ad<sub>M⁻¹</sub>] Sᵢ."),
        formula=_block_html("[Ad<sub>T</sub>] = ⎡  R    0 ⎤<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;⎣ [p]R  R ⎦",
                            "6 × 6, four 3 × 3 blocks",
                            "Bᵢ = [Ad<sub>M⁻¹</sub>] Sᵢ", "uses invT, skew, rrprHome"),
        sig="Mat6 adjoint(const Mat4& T);\nstd::array<Vec6, 4> rrprScrewsBody();",
        hint=("Fill the blocks with index offsets: A[i][j] = R, A[i+3][j+3] = R, "
              "A[i+3][j] = ([p]R)[i][j] for i, j in 0..2. Remember <code>Mat6 A{};</code> "
              "starts as all zeros.")),
    dict(ex=6, why=(
        "e<sup>[S]θ</sup> is the rigid motion you get by turning one joint by "
        "θ: the building block of the product of exponentials (page 122). The "
        "rotation is Rodrigues; the translation is G(θ)v, the origin swept "
        "along an arc. A prismatic joint (ω = 0) is just a slide."),
        formula=_block_html("ω = 0: e<sup>[S]θ</sup> = (I, vθ)",
                            "else: (e<sup>[ω]θ</sup>, G(θ)v)",
                            "G(θ) = Iθ + (1 − cos θ)[ω] + (θ − sin θ)[ω]²",
                            "θ = 0 ⇒ identity"),
        sig="Mat4 expTwist(const Vec6& S, double theta);",
        hint=("Branch first on <code>norm(top(S)) &lt; 1e-12</code>. The test includes a "
              "screw with pitch 0.1 (ω and v not perpendicular); the same formula "
              "handles it.")),
    dict(ex=7, why=(
        "Where is the tool? Two equivalent answers (page 123). Space form: "
        "start at M and apply the joints from the last one back to the first, "
        "every axis in {s}. Body form: start at M and apply the joints with "
        "axes seen from the tool. Both must give the same T."),
        formula=_block_html("T = e<sup>[S₁]θ₁</sup> e<sup>[S₂]θ₂</sup> e<sup>[S₃]θ₃</sup> e<sup>[S₄]θ₄</sup> M",
                            "T = M e<sup>[B₁]θ₁</sup> e<sup>[B₂]θ₂</sup> e<sup>[B₃]θ₃</sup> e<sup>[B₄]θ₄</sup>",
                            "M on the RIGHT", "M on the LEFT"),
        sig="Mat4 fkSpace(const Joints& th);\nMat4 fkBody(const Joints& th);",
        hint=("A loop: <code>T = T * expTwist(S[i], th[i]);</code> for i = 0..3, then "
              "multiply by M on the correct side. th[2] is a length in metres "
              "(the slide), the others are angles.")),
    dict(ex=8, why=(
        "Column i is the twist when only joint i turns at unit speed (page "
        "124). In space form only the joints before it can move axis i, so "
        "carry Sᵢ with the adjoint of their exponentials. In body form only "
        "the joints after it matter, undone with minus signs."),
        formula=_block_html("J<sub>s1</sub> = S₁,&nbsp; J<sub>si</sub> = [Ad<sub>e<sup>[S₁]θ₁</sup>⋯e<sup>[S<sub>i−1</sub>]θ<sub>i−1</sub></sup></sub>] Sᵢ",
                            "J<sub>b4</sub> = B₄,&nbsp; J<sub>bi</sub> = [Ad<sub>e<sup>−[B₄]θ₄</sup>⋯e<sup>−[B<sub>i+1</sub>]θ<sub>i+1</sub></sup></sub>] Bᵢ",
                            "Jac J; J[i] is column i (0-based)",
                            "self-check: J<sub>s</sub> = [Ad<sub>T<sub>sb</sub></sub>] J<sub>b</sub>"),
        sig="Jac jacobianSpace(const Joints& th);\nJac jacobianBody(const Joints& th);",
        hint=("Space: keep a running T = I. In the loop, FIRST store "
              "<code>J[i] = adjoint(T) * S[i]</code>, THEN update "
              "<code>T = T * expTwist(S[i], th[i])</code>. Body: run i from 3 down to 0 "
              "and update with <code>expTwist(-B[i], th[i])</code>.")),
    dict(ex=9, why=(
        "Use the Jacobian both ways round. Velocity: V<sub>s</sub> = J<sub>s</sub>θ̇. "
        "Statics (page 126): to make the hand push with wrench F<sub>s</sub> the "
        "motors need τ = J<sub>s</sub>ᵀF<sub>s</sub>. Wrenches change frame with the "
        "transpose of the adjoint, which keeps power VᵀF the same in every frame."),
        formula=_block_html("V<sub>s</sub> = Σ θ̇ᵢ J[i]", "τᵢ = J[i] · F<sub>s</sub>",
                            "F<sub>b</sub> = [Ad<sub>T<sub>sb</sub></sub>]ᵀ F<sub>s</sub>",
                            "check: V<sub>s</sub>ᵀF<sub>s</sub> = θ̇ᵀτ"),
        sig=("Vec6 handTwistSpace(const Joints& th, const Joints& thdot);\n"
             "Joints jointTorques(const Joints& th, const Vec6& Fs);\n"
             "Vec6 wrenchToBody(const Mat4& Tsb, const Vec6& Fs);"),
        hint=("Jac stores columns, so Jᵀ F needs no transpose call at all: entry i of τ is "
              "the dot product of column J[i] with F. For the wrench, "
              "<code>transpose(adjoint(Tsb)) * Fs</code>.")),
    dict(ex=10, why=(
        "How professionals test a Jacobian: never trust it, differentiate "
        "the forward kinematics numerically and compare. Move the joints a "
        "tiny step along θ̇, take Ṫ ≈ (T(θ + hθ̇) − T(θ − hθ̇)) / 2h, and "
        "[V<sub>s</sub>] = ṪT⁻¹. Your answer must equal J<sub>s</sub>θ̇ to about "
        "five digits."),
        formula=_block_html("[V<sub>s</sub>] = Ṫ T⁻¹ = ⎡ [ω]  v ⎤<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;⎣  0   0 ⎦",
                            "(T⁻¹Ṫ would be [V<sub>b</sub>])",
                            "ω = (X[2][1], X[0][2], X[1][0])", "v = (X[0][3], X[1][3], X[2][3])"),
        sig="Vec6 twistFromFK(const Joints& th, const Joints& thdot);",
        hint=("h = 1e-6 works well with a central difference. mrlite lets you write "
              "<code>(1.0 / (2 * h)) * (fkSpace(a) - fkSpace(b))</code> directly.")),
]


# ==========================================================================
# compile + run
# ==========================================================================

class Workshop:
    """Owns the editor, the file on disk, g++, and who gets told about results."""

    def __init__(self):
        self.path = rc.ensure_workbook()
        self.harness = os.path.join(rc.BUILD, "harness.cpp")
        self.exe = os.path.join(rc.BUILD, "harness.exe" if os.name == "nt" else "harness")
        self.gxx = rc.find_gxx()
        self._built = None          # hash of the source the exe was built from
        self._proc = None
        self._then = None
        self.listeners = []         # f(results, passed) after every graded run
        self.passed = {}

        self.editor = QPlainTextEdit()
        self.editor.setFont(_mono_font(11))
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.setTabStopDistance(4 * self.editor.fontMetrics().horizontalAdvance(" "))
        self.editor.setMinimumHeight(int(self.editor.fontMetrics().height() * 26 + 20))
        self._hl = CppHighlighter(self.editor.document())
        self._load()

        self.watch = QFileSystemWatcher([self.path])
        self.watch.fileChanged.connect(self._disk_changed)

        self.status = body("")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(_mono_font(9))
        self.log.setMaximumHeight(170)
        self.log.hide()
        self.chips = []

    # ---- file ----------------------------------------------------------
    def _read(self):
        with open(self.path, encoding="utf-8") as f:
            return f.read()

    def _load(self):
        bar = self.editor.verticalScrollBar().value()
        self.editor.setPlainText(self._read())
        self.editor.document().setModified(False)
        self.editor.verticalScrollBar().setValue(bar)

    def save(self):
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.editor.toPlainText())
        self.editor.document().setModified(False)

    def _disk_changed(self, *_):
        if self.path not in self.watch.files() and os.path.exists(self.path):
            self.watch.addPath(self.path)       # editors that replace the file drop the watch
        if not os.path.exists(self.path):
            return
        if self._read() == self.editor.toPlainText():
            return
        if self.editor.document().isModified():
            self.set_status("The file changed on disk, but you have unsaved edits here; "
                            "press <b>reload</b> to take the disk version.", theme.WARN)
        else:
            self._load()
            self.set_status("Reloaded: the file changed on disk.", theme.TEXT_DIM)

    def sync(self):
        """Editor edits win; otherwise take whatever is on disk."""
        if self.editor.document().isModified():
            self.save()
        elif self._read() != self.editor.toPlainText():
            self._load()

    def reset(self):
        with open(rc.STARTER, encoding="utf-8") as f:
            self.editor.setPlainText(f.read())
        self.save()

    def goto_ex(self, ex):
        line = rc.marker_line(self.editor.toPlainText(), ex)
        if line >= 0:
            self._goto(line)

    def _goto(self, line, mark=False):
        block = self.editor.document().findBlockByLineNumber(line)
        if not block.isValid():
            return
        cur = QTextCursor(block)
        self.editor.setTextCursor(cur)
        self.editor.centerCursor()
        sels = []
        if mark:
            sel = QTextEdit.ExtraSelection()
            fmt = QTextCharFormat()
            c = QColor(theme.BAD)
            c.setAlpha(80)
            fmt.setBackground(c)
            fmt.setProperty(QTextFormat.FullWidthSelection, True)
            sel.format = fmt
            sel.cursor = cur
            sels.append(sel)
        self.editor.setExtraSelections(sels)
        self.editor.setFocus()

    def set_status(self, text, colour=None):
        self.status.setText(f"<span style='color:{colour or theme.TEXT}'>{text}</span>")

    # ---- build ---------------------------------------------------------
    def _hash(self, harness_src):
        h = hashlib.sha1()
        h.update(self._read().encode("utf-8"))
        h.update(harness_src.encode("utf-8"))
        with open(os.path.join(rc.ROOT, "mrlite.hpp"), "rb") as f:
            h.update(f.read())
        return h.hexdigest()

    def up_to_date(self):
        return (self._built is not None and os.path.exists(self.exe)
                and not self.editor.document().isModified()
                and self._built == self._hash(rc.harness_source(self.path)))

    def build(self, then):
        """Compile if the source changed, then call then(ok)."""
        if self._proc is not None:
            return
        if self.gxx is None:
            self.set_status("No C++ compiler found. Install MinGW-w64 (g++) and put its "
                            "<code>bin</code> folder on PATH, then restart the app.", theme.BAD)
            then(False)
            return
        self.sync()
        src = rc.harness_source(self.path)
        key = self._hash(src)
        if key == self._built and os.path.exists(self.exe):
            then(True)
            return
        with open(self.harness, "w", encoding="utf-8") as f:
            f.write(src)
        self.editor.setExtraSelections([])
        self.set_status("compiling with g++ …", theme.CYAN)
        self._t0 = time.perf_counter()
        self._then, self._key = then, key
        p = self._proc = QProcess()
        cmd = rc.compile_command(self.gxx, self.harness, self.exe)
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.finished.connect(self._compiled)
        p.errorOccurred.connect(lambda *_: self._compiled(-1, None))
        p.start(cmd[0], cmd[1:])

    def _compiled(self, code, _status):
        p, self._proc = self._proc, None
        if p is None:
            return
        out = bytes(p.readAll()).decode("utf-8", "replace")
        dt = time.perf_counter() - self._t0
        then = self._then
        if code != 0:
            self._built = None
            self._show_errors(out)
            then(False)
            return
        self._built = self._key
        self.log.hide()
        self.set_status(f"compiled in {dt:.1f} s", theme.TEXT_DIM)
        then(True)

    def _show_errors(self, out):
        base = os.path.basename(self.path)
        lines = [ln.replace(rc.ROOT.replace("\\", "/") + "/", "").replace(rc.ROOT + os.sep, "")
                 for ln in out.splitlines()]
        self.log.setPlainText("\n".join(lines[:80]))
        self.log.show()
        m = re.search(re.escape(base) + r":(\d+):\d+: (?:fatal )?error: (.*)", out)
        if m:
            self._goto(int(m.group(1)) - 1, mark=True)
            self.set_status(f"<b>Compile error</b> on line {m.group(1)}: "
                            f"{html.escape(m.group(2))} (line marked in red; full message below).",
                            theme.BAD)
        else:
            self.set_status("<b>Compile error</b>; the compiler's message is below.", theme.BAD)

    # ---- run -----------------------------------------------------------
    def check(self):
        self.build(self._after_build_tests)

    def _after_build_tests(self, ok):
        if not ok:
            return
        try:
            r = subprocess.run([self.exe], capture_output=True, text=True, timeout=10,
                               encoding="utf-8", errors="replace")
            out, crashed = r.stdout, r.returncode != 0
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            crashed = True
        vals, other = rc.parse_output(out)
        results = rc.grade_all(vals)
        by_ex = {}
        for res in results:
            by_ex.setdefault(res.test.ex, []).append(res.ok)
        self.passed = {ex: all(v) for ex, v in by_ex.items()}
        n = sum(r.ok for r in results)
        msg = f"<b>{n} / {len(results)} tests pass.</b>"
        if crashed and "done" not in vals:
            msg += (" <span style='color:%s'>The program crashed or hung before the end "
                    "(an out-of-range index, or a loop that never stops?).</span>" % theme.BAD)
        self.set_status(msg + " Results are in each exercise card below.",
                        theme.GOOD if n == len(results) else theme.TEXT)
        if other.strip():
            self.log.setPlainText("Your code printed:\n" + other[:4000])
            self.log.show()
        self._paint_chips()
        for f in self.listeners:
            f(results, self.passed)

    def run_pose(self, q):
        """(fks, fkb, js, jb) from the learner's code at pose q, or None."""
        try:
            r = subprocess.run([self.exe] + [repr(float(x)) for x in q], capture_output=True,
                               text=True, timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            return None
        vals, _ = rc.parse_output(r.stdout)
        try:
            return (vals["pose_fks"].reshape(4, 4), vals["pose_fkb"].reshape(4, 4),
                    vals["pose_js"].reshape(4, 6).T, vals["pose_jb"].reshape(4, 6).T)
        except (KeyError, ValueError):
            return None

    def _paint_chips(self):
        for ex, lb in self.chips:
            ok = self.passed.get(ex)
            col = theme.GOOD if ok else theme.BAD if ok is False else theme.TEXT_FAINT
            mark = "✓" if ok else "✗" if ok is False else "·"
            lb.setText(f"<span style='color:{col}'><b>{ex} {mark}</b></span>")
            lb.setToolTip(rc.EXERCISES[ex])


# ==========================================================================
# drawing the arm
# ==========================================================================

def draw_rrpr(ax, q, T_mine=None):
    """The pose lab's view: the solid arm, joint arrows dimmed, your frame dotted."""
    rr.draw_robot(ax, q, focus=-1, T_mine=T_mine)


# ==========================================================================
# cards
# ==========================================================================

class RobotView:
    """The robot card: a solid 3-D arm you can pose, and one joint at a time animated."""

    HOME = (30, 25, 25, 40)

    def __init__(self):
        c = self.card = Card("the robot: an RRPR arm in 3-D")
        c.add(in_words(
            "Four joints: a waist (R), a shoulder (R), a telescoping slide (P) and "
            "a wrist roll (R). Small enough to check by hand, rich enough to use "
            "every tool from pages 118–124: a prismatic joint (ω = 0), axes that "
            "do not pass through the origin, and a tool frame that is rotated at "
            "home. Press a ▶ button to watch one joint move on its own."))
        cell = f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}'"
        mono = f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}; {MONO}; color:{theme.CYAN}'"
        rows = [("1", "R  waist", "ω = (0, 0, 1)", "q = (0, 0, 0)", "(0, 0, 1,  0, 0, 0)",
                 "turns the whole arm about the vertical column"),
                ("2", "R  shoulder", "ω = (0, −1, 0)", "q = (0, 0, 1)", "(0, −1, 0,  1, 0, 0)",
                 "tilts the arm up (+) and down, about a horizontal axis"),
                ("3", "P  slide", "v = (1, 0, 0)", "—", "(0, 0, 0,  1, 0, 0)",
                 "pushes the inner tube out along the arm; no rotation"),
                ("4", "R  wrist roll", "ω = (1, 0, 0)", "q = (1, 0, 1)", "(1, 0, 0,  0, 1, 0)",
                 "spins the hand about the arm's own axis")]
        html_rows = "".join(
            f"<tr><td {cell}><b style='color:{rr.JOINT_COLS[i]}'>■ {a}</b></td>"
            f"<td {cell}><b style='color:{rr.JOINT_COLS[i]}'>{b}</b></td><td {mono}>{d}</td>"
            f"<td {mono}>{e}</td><td {mono}>{s}</td><td {cell}>{w}</td></tr>"
            for i, (a, b, d, e, s, w) in enumerate(rows))
        c.add(body(f"<table style='border-collapse:collapse'><tr><th {cell} align='left'>joint</th>"
                   f"<th {cell} align='left'>type</th><th {cell} align='left'>axis</th>"
                   f"<th {cell} align='left'>through</th><th {cell} align='left'>Sᵢ = (ω, v) in {{s}}</th>"
                   f"<th {cell} align='left'>what it does</th></tr>{html_rows}</table>"))
        c.add(body(
            "<b>Home pose</b> (all joints zero): the arm points along +x at height 1, the "
            "tool sits at p = (1.5, 0, 0.8), hanging 0.2 below the roll axis, with its z-axis "
            "pointing down: R = diag(1, −1, −1). Units: metres and radians; d₃ is a length. "
            "The Sᵢ column is a check for exercise 4; derive S₂ and S₄ from −ω × q first."))
        self.q = [labelled_slider(c, "θ1 waist", -180, 180, self.HOME[0], deg, self._draw),
                  labelled_slider(c, "θ2 shoulder", -20, 80, self.HOME[1], deg, self._draw),
                  labelled_slider(c, "d3 slide", 0, 60, self.HOME[2], lambda v: f"{v/100:.2f} m", self._draw),
                  labelled_slider(c, "θ4 roll", -180, 180, self.HOME[3], deg, self._draw)]
        row = QHBoxLayout()
        self.btns = []
        for i, name in enumerate(rr.JOINT_LABELS):
            b = QPushButton(f"▶  {name}")
            b.setStyleSheet(f"color:{rr.JOINT_COLS[i]}; font-weight:bold;")
            b.clicked.connect(lambda _=False, i=i: self._animate(i))
            row.addWidget(b)
            self.btns.append(b)
        b_home = QPushButton("home pose")
        b_home.clicked.connect(self._home)
        row.addWidget(b_home)
        row.addStretch(1)
        c.add_layout(row)
        self.msg = body("")
        c.add(self.msg)
        self.cv = MplCanvas(width=8.4, height=6.0)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>How to read the picture.</b> Each joint has one colour, the same as in the "
            "table. A curved arrow circles each revolute axis and points the way <b>+θ</b> "
            "turns (right-hand rule: thumb along ω, fingers curl the + way). The straight teal "
            "arrow is the slide's +d₃. Grey parts are links; a coloured part is the joint "
            "itself: the orange turntable, the violet shoulder drum, the teal inner tube and the "
            "pink roll drum. The hand hangs off the roll axis, so θ₄ swings it in a circle. "
            "While a joint is animated its axis is drawn as a long dashed line and the dotted "
            "curve is the path the tool point traces. Notice: the waist path is a horizontal "
            "circle, the shoulder path an arc in a vertical plane, the slide path a straight "
            "line, the roll path a small circle around the arm."))
        self.focus = None
        self._ticking = False
        self.phase = 0.0
        self.timer = QTimer()
        self.timer.setInterval(60)
        self.timer.timeout.connect(self._tick)
        self._draw()

    def _pose(self):
        v = [s.value() for s in self.q]
        return np.array([np.radians(v[0]), np.radians(v[1]), v[2] / 100, np.radians(v[3])])

    def _home(self):
        self._stop()
        for s, v in zip(self.q, (0, 0, 0, 0)):
            s.blockSignals(True)
            s.setValue(v)
            s.blockSignals(False)
        self._draw()

    def _animate(self, i):
        if self.focus == i and self.timer.isActive():
            self._stop()
            self._draw()
            return
        self.focus = i
        self.center = self.q[i].value()
        self.phase = 0.0
        self.trail = rr.tool_path(self._pose(), i)
        for k, b in enumerate(self.btns):
            b.setText(("■  stop " if k == i else "▶  ") + rr.JOINT_LABELS[k])
        self.timer.start()

    def _stop(self):
        self.timer.stop()
        self.focus = None
        for k, b in enumerate(self.btns):
            b.setText("▶  " + rr.JOINT_LABELS[k])

    def _tick(self):
        i = self.focus
        self.phase += 0.09
        s = self.q[i]
        lo, hi = rr.SWEEP[i](np.radians(self.center) if i != 2 else self.center / 100)
        mid, amp = 0.5 * (lo + hi), 0.5 * (hi - lo)
        val = mid + amp * np.sin(self.phase)
        raw = val * 100 if i == 2 else np.degrees(val)
        raw = max(s.minimum(), min(s.maximum(), raw))
        self._ticking = True
        s.setValue(int(round(raw)))
        self._ticking = False
        self._draw(animating=True)

    def _draw(self, *_, animating=False):
        if self._ticking:
            return
        if not animating and self.timer.isActive():
            self._stop()
        q = self._pose()
        _clear(self.cv)
        ax = self.cv.ax
        trail = self.trail if self.focus is not None else None
        rr.draw_robot(ax, q, focus=self.focus, trail=trail)
        ax.view_init(elev=24, azim=-58)
        if self.focus is None:
            ax.set_title("drag the sliders, or press ▶ to animate one joint", color=theme.TEXT,
                         fontsize=9)
            self.msg.setText(f"<span style='color:{theme.TEXT_DIM}'>θ = ({q[0]:+.2f}, "
                             f"{q[1]:+.2f}, {q[2]:.2f} m, {q[3]:+.2f})</span>")
        else:
            i = self.focus
            what = ("the whole arm turns about the column; the tool draws a horizontal circle",
                    "the arm tilts about the shoulder axis; the tool draws a vertical arc",
                    "only the inner tube moves, straight out along the arm; nothing rotates",
                    "the hand spins about the arm's axis; the tool point circles that axis")[i]
            ax.set_title(f"{rr.JOINT_LABELS[i]} moving alone", color=rr.JOINT_COLS[i], fontsize=10)
            self.msg.setText(f"<b style='color:{rr.JOINT_COLS[i]}'>{rr.JOINT_LABELS[i]}:</b> {what}. "
                             f"<span style='color:{theme.TEXT_DIM}'>Press the button again to stop.</span>")
        self.cv.refresh()


def method_card() -> Card:
    c = Card("how this page works: from notation to code")
    c.add(in_words(
        "Reading a formula and typing it are different skills. Typing forces "
        "every choice the notation hides: which index is the row, which side "
        "M goes on, where the minus sign lives. Each exercise below is one "
        "idea, a test suite checks your numbers against a reference, and when "
        "a known mistake explains your answer, the page says which."))
    c.add(body(_block_html(
        "<b>notation</b><br>ω̂, p, a twist V, a wrench F<br>[ω], R, T<br>[Ad<sub>T</sub>]<br>"
        "J, column i<br>Jᵀ F", "<b>C++ (mrlite.hpp)</b><br>Vec3, Vec3, Vec6 (ω first), Vec6 (m first)<br>"
        "Mat3 skew(w), Mat3, Mat4 &nbsp;(A[row][col])<br>Mat6<br>Jac J; J[i] is a Vec6<br>"
        "a loop of dot products",
        "<b>given to you</b><br>A * B, A * x, A + B, s * A, transpose,<br>eye&lt;N&gt;(), cross, dot, "
        "norm,<br>top/bottom/stack, rotPart/posPart, print",
        "<b>you write</b><br>skew, expRot, makeT, invT, screw axes, adjoint,<br>expTwist, "
        "fkSpace/fkBody, Jacobians, statics,<br>a finite-difference check")))
    c.add(plain(
        "<b>The loop.</b> (1) Read the exercise card. (2) Press <b>go to</b> to jump to its "
        "TODO in the editor. (3) Write the function. (4) Press <b>check my code</b> "
        "(or Ctrl+S then check). Every test runs every time, so one press shows the whole "
        "picture. (5) Red? Read the diagnosis and compare the expected and your matrix "
        "entry by entry. Stuck for real? <b>show solution</b> reveals that exercise only.<br>"
        "<b>Order matters.</b> Exercise 7 calls your exercise 6, which calls 2, which calls 1. "
        "If an early one fails the page tells you to fix that first, instead of drowning you "
        "in follow-on errors.<br>"
        "<b>Your own editor.</b> The file is " + f"<code>{html.escape(rc.WORKBOOK)}</code>"
        ". Edit it in VS Code if you prefer; the page reloads it when it changes. It has its "
        "own main() for experiments, and the top of the file shows the g++ command."))
    return c


class WorkbenchCard:
    def __init__(self, ws: Workshop):
        self.ws = ws
        c = self.card = Card("workbench: my_rrpr.cpp")
        row = QHBoxLayout()
        self.b_check = QPushButton("▶  check my code")
        self.b_check.setStyleSheet(f"font-weight:bold; color:{theme.GOOD};")
        self.b_check.clicked.connect(ws.check)
        b_save = QPushButton("save")
        b_save.clicked.connect(lambda: (ws.save(), ws.set_status("saved", theme.TEXT_DIM)))
        b_reload = QPushButton("reload from disk")
        b_reload.clicked.connect(lambda: (ws._load(), ws.set_status("reloaded", theme.TEXT_DIM)))
        b_open = QPushButton("open in my editor")
        b_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(ws.path)))
        self.b_reset = QPushButton("reset to starter")
        self.b_reset.clicked.connect(self._reset)
        self._armed = False
        for b in (self.b_check, b_save, b_reload, b_open, self.b_reset):
            row.addWidget(b)
        row.addStretch(1)
        c.add_layout(row)
        chips = QHBoxLayout()
        chips.addWidget(body(f"<span style='color:{theme.TEXT_DIM}'>exercises:</span>"))
        for ex in rc.EXERCISES:
            lb = QLabel()
            ws.chips.append((ex, lb))
            chips.addWidget(lb)
        chips.addStretch(1)
        c.add_layout(chips)
        ws._paint_chips()
        c.add(ws.status)
        ws.set_status("Edit below (or in your own editor), then press <b>check my code</b>. "
                      + ("" if ws.gxx else "<b>No g++ found on PATH.</b>"),
                      theme.TEXT_DIM if ws.gxx else theme.BAD)
        c.add(ws.editor)
        c.add(ws.log)
        from PySide6.QtGui import QKeySequence, QShortcut
        sc = QShortcut(QKeySequence.Save, ws.editor)
        sc.activated.connect(lambda: (ws.save(), ws.set_status("saved", theme.TEXT_DIM)))

    def _reset(self):
        if not self._armed:
            self._armed = True
            self.b_reset.setText("click again: erase my code")
            self.b_reset.setStyleSheet(f"color:{theme.BAD};")
            QTimer.singleShot(4000, self._disarm)
            return
        self._disarm()
        self.ws.reset()
        self.ws.set_status("Reset to the starter file.", theme.WARN)

    def _disarm(self):
        self._armed = False
        self.b_reset.setText("reset to starter")
        self.b_reset.setStyleSheet("")


class ExerciseCard:
    def __init__(self, ws: Workshop, spec: dict, scroll_to_bench):
        self.ws, self.ex = ws, spec["ex"]
        c = self.card = Card(f"exercise {self.ex} — {rc.EXERCISES[self.ex]}")
        c.add(in_words(spec["why"]))
        c.add(body(spec["formula"]))
        sig = CodePane(spec["sig"], font_size=10)
        sig.setPlainText(spec["sig"])
        sig.sizeHintLine(spec["sig"].count("\n") + 1)
        c.add(sig)
        c.add(plain("<b>Hint.</b> " + spec["hint"]))
        row = QHBoxLayout()
        b_go = QPushButton("go to it in the editor")
        b_go.clicked.connect(lambda: (scroll_to_bench(), ws.goto_ex(self.ex)))
        b_chk = QPushButton("check my code")
        b_chk.clicked.connect(ws.check)
        self.b_sol = QPushButton("show solution")
        self.b_sol.clicked.connect(self._toggle)
        for b in (b_go, b_chk, self.b_sol):
            row.addWidget(b)
        row.addStretch(1)
        c.add_layout(row)
        self.res = body(f"<span style='color:{theme.TEXT_DIM}'>not checked yet</span>")
        c.add(self.res)
        code = rc.solution_block(self.ex)
        self.sol = CodePane(code, font_size=10)
        self.sol.setPlainText(code)
        self.sol.sizeHintLine(min(code.count("\n") + 2, 30))
        self.sol.hide()
        c.add(self.sol)
        ws.listeners.append(self.update)

    def _toggle(self):
        show = not self.sol.isVisible()
        self.sol.setVisible(show)
        self.b_sol.setText("hide solution" if show else "show solution")

    def update(self, results, passed):
        mine = [r for r in results if r.test.ex == self.ex]
        blockers = rc.blocking(self.ex, passed)
        n = sum(r.ok for r in mine)
        head_col = theme.GOOD if n == len(mine) else theme.BAD
        out = [f"<b style='color:{head_col}'>{n} / {len(mine)} tests pass</b>"]
        if n == len(mine):
            out.append(f" <span style='color:{theme.GOOD}'>— done.</span>")
        elif blockers:
            out.append(f"<br><span style='color:{theme.WARN}'>This exercise calls your code from "
                       f"exercise {', '.join(map(str, blockers))}, which is not passing yet. "
                       f"Fix that first; these failures may disappear with it.</span>")
        rows = ""
        shown = False
        for r in mine:
            mark = (f"<span style='color:{theme.GOOD}'>✓</span>" if r.ok
                    else f"<span style='color:{theme.BAD}'>✗</span>")
            why = f"<span style='color:{theme.WARN}'>{html.escape(r.why)}</span>" if r.why else ""
            err = "" if r.ok or not np.isfinite(r.err) else f"max error {r.err:.2e}"
            rows += (f"<tr><td>{mark}</td><td style='{MONO}; padding-right:12px'>"
                     f"{html.escape(r.test.label)}</td><td style='color:{theme.TEXT_DIM}; "
                     f"padding-right:12px'>{err}</td><td>{why}</td></tr>")
            if not r.ok and not shown and r.got is not None and np.any(r.got):
                rows += f"<tr><td></td><td colspan='3'>{_side_by_side(r.test.expected, r.got)}</td></tr>"
                shown = True
        out.append(f"<table style='margin-top:4px'>{rows}</table>")
        self.res.setText("".join(out))


class PoseLab:
    """Run the learner's fkSpace / jacobianSpace at a slider pose and draw them."""

    def __init__(self, ws: Workshop):
        self.ws = ws
        c = self.card = Card("lab (3-D): run MY code at any pose")
        c.add(in_words(
            "The tests use fixed poses. Here you pick the pose. The page runs "
            "your compiled fkSpace, fkBody, jacobianSpace and jacobianBody "
            "and draws your tool frame (dotted, 'yours') over the true one. "
            "Wrong entries are red. Good for questions like 'is my body "
            "Jacobian only wrong when θ₄ ≠ 0?'"))
        self.q = [labelled_slider(c, "θ1 waist", -180, 180, 30, deg, self._draw),
                  labelled_slider(c, "θ2 shoulder", -90, 120, 25, deg, self._draw),
                  labelled_slider(c, "d3 slide", 0, 80, 20, lambda v: f"{v/100:.2f} m", self._draw),
                  labelled_slider(c, "θ4 roll", -180, 180, 40, deg, self._draw)]
        row = QHBoxLayout()
        b = QPushButton("compile (if needed) and run my code here")
        b.clicked.connect(lambda: ws.build(lambda ok: self._draw()))
        row.addWidget(b)
        row.addStretch(1)
        c.add_layout(row)
        self.msg = body("")
        c.add(self.msg)
        self.cv = MplCanvas(width=7.6, height=4.6)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        self.txt = body("")
        c.add(self.txt)
        c.add(plain(
            "<b>Try.</b> (1) Home pose (all zero): your T must be M exactly. (2) Move only "
            "d₃: the tool slides along the arm and nothing rotates; in J<sub>s</sub> only "
            "column 4 should change (the slide carries the wrist axis). (3) Move only θ₄: "
            "J<sub>s</sub> does not change at all, because column i of J<sub>s</sub> depends "
            "on θ₁ … θ<sub>i−1</sub> only, so θ₄ appears nowhere. (4) In J<sub>b</sub> it is "
            "θ₁ that appears nowhere. (5) Set θ₂ = 90°: the arm points straight up, the roll "
            "axis lies on the waist axis, and columns 1 and 4 of J<sub>s</sub> become equal. "
            "That is a singularity, the subject of page 126."))
        self._draw()

    def _pose(self):
        v = [s.value() for s in self.q]
        return np.array([np.radians(v[0]), np.radians(v[1]), v[2] / 100, np.radians(v[3])])

    def _draw(self, *_):
        q = self._pose()
        T = rk.fk_space(rc.M_HOME, rc.S_LIST, q)
        Js = rk.jacobian_space(rc.S_LIST, q)
        Jb = rk.jacobian_body(rc.B_LIST, q)
        mine = self.ws.run_pose(q) if self.ws.up_to_date() else None
        _clear(self.cv)
        draw_rrpr(self.cv.ax, q, None if mine is None else mine[0])
        self.cv.ax.view_init(elev=22, azim=-60)
        self.cv.ax.set_title("solid frame = true tool pose · dotted (x′y′z′) = your fkSpace",
                             color=theme.TEXT, fontsize=9)
        self.cv.refresh()
        if mine is None:
            self.msg.setText(f"<span style='color:{theme.TEXT_DIM}'>Showing the reference only. "
                             "Press the button to compile and run your code at this pose; "
                             "after that it re-runs as you move the sliders.</span>")
            self.txt.setText(
                f"<table><tr><td>true T<sub>sb</sub></td><td width='18'></td><td>true J<sub>s</sub></td></tr>"
                f"<tr><td>{_small_mat(T)}</td><td></td><td>{_small_mat(Js)}</td></tr></table>")
            return
        fks, fkb, js, jb = mine
        good = [np.allclose(a, b, atol=1e-6) for a, b in ((fks, T), (fkb, T), (js, Js), (jb, Jb))]
        names = ("fkSpace", "fkBody", "jacobianSpace", "jacobianBody")
        summary = " · ".join(
            f"<span style='color:{theme.GOOD if g else theme.BAD}'>{n} {'✓' if g else '✗'}</span>"
            for n, g in zip(names, good))
        self.msg.setText(f"<b>Your code at this pose:</b> {summary}")
        self.txt.setText(
            f"<table><tr><td>your fkSpace</td><td width='14'></td><td>your fkBody</td></tr>"
            f"<tr><td>{_small_mat(fks, T)}</td><td></td><td>{_small_mat(fkb, T)}</td></tr>"
            f"<tr><td>your J<sub>s</sub></td><td></td><td>your J<sub>b</sub></td></tr>"
            f"<tr><td>{_small_mat(js, Js)}</td><td></td><td>{_small_mat(jb, Jb)}</td></tr></table>")


def next_card() -> Card:
    c = Card("when everything is green: stretch goals, and what comes next")
    c.add(in_words(
        "You now own a small robotics library: FK, both Jacobians, statics. "
        "The next three pages use exactly these functions, so the extensions "
        "below are worth doing in the main() of your file."))
    c.add(body(
        "<b>1. Two Jacobians, one robot.</b> In main(), check J<sub>s</sub> = "
        "[Ad<sub>T<sub>sb</sub></sub>] J<sub>b</sub> column by column at a random pose.<br>"
        "<b>2. Power is frame-free.</b> Pick θ̇ and a wrench F<sub>s</sub>; print "
        "V<sub>s</sub>ᵀF<sub>s</sub>, θ̇ᵀτ and V<sub>b</sub>ᵀF<sub>b</sub>. All three must agree.<br>"
        "<b>3. Hunt a singularity (page 126).</b> Joints 1 and 4 can line up: when is the "
        "wrist roll axis parallel to the waist axis? Print the 6 × 4 J<sub>s</sub> at "
        "θ₂ = 90° and look for two columns that are multiples of each other. Then write "
        "<code>double det4(Mat4)</code> and scan θ₂ for where det(J<sub>s</sub>ᵀJ<sub>s</sub>) "
        "drops to zero.<br>"
        "<b>4. One Newton step of inverse kinematics (page 127).</b> Target pose T<sub>d</sub>: "
        "the error twist is log(T⁻¹T<sub>d</sub>) and the step is Δθ = J<sub>b</sub>⁺ V<sub>b</sub>. "
        "You have fkBody and jacobianBody already; page 127 adds the log and the pseudo-inverse.<br>"
        "<b>5. Redundancy (page 128).</b> This arm has 4 joints and 6 hand directions: too few. "
        "Restrict the task to the tool position (3 numbers, the bottom rows of J after moving to "
        "the tool point) and you get a 3 × 4 Jacobian with a one-dimensional null space: "
        "a motion of the joints that leaves the tool where it is."))
    return c


# ==========================================================================
# the page
# ==========================================================================

class RRPRWorkshopPage(Page):
    TITLE = "C++ Workshop: Build the RRPR Arm Yourself"
    SUBTITLE = ("Ten exercises, one 3-D RRPR robot: skew, Rodrigues, transforms, "
                "screw axes, adjoint, e^[S]θ, forward kinematics, both Jacobians, "
                "statics, and a numerical check. Your C++ is compiled, run and "
                "graded on the page.")
    SECTION = SEC_KIN
    NOTES = playlist_badge(4)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "Pages 118–124 gave you the notation. This page makes you <b>implement</b> it: a "
            "small C++ library for one RRPR arm, built one function at a time. You write "
            "each function, press <b>check my code</b>, and the page compiles it, runs 35 "
            "tests, compares every number with a reference and, when it recognises the "
            "mistake (a transposed matrix, the wrong sign on −ω × q, M on the wrong side, an "
            "off-by-one Jacobian column), tells you which one. When all ten pass you have "
            "everything the next pages build on: singularities (126), inverse kinematics "
            "(127) and redundancy (128)."))
        self.robot = RobotView()
        self.add(self.robot.card)
        self.add(method_card())
        self.ws = Workshop()
        self.bench = WorkbenchCard(self.ws)
        self.add(self.bench.card)
        self.ex_cards = [ExerciseCard(self.ws, spec, self._to_bench) for spec in EXERCISES]
        for e in self.ex_cards:
            self.add(e.card)
        self.pose_lab = PoseLab(self.ws)
        self.add(self.pose_lab.card)
        self.add(next_card())

    def _to_bench(self):
        area = self.bench.card
        while area is not None and not hasattr(area, "ensureWidgetVisible"):
            area = area.parentWidget()
        if area is not None:
            area.ensureWidgetVisible(self.bench.card, 0, 0)
            area.ensureWidgetVisible(self.ws.editor, 0, 40)
