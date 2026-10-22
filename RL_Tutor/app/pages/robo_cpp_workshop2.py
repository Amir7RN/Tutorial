"""
Page 131 -- C++ workshop 2: statics, eigenvalues, manipulability, inverse
kinematics and the null space, on the same RRPR arm as page 125.

The learner edits cpp/workshop/my_rrpr2.cpp, which includes rrpr_lib.hpp (a
ready-made FK / Jacobian library). Compiling, grading and the exercise cards
reuse the page-125 machinery with ctrlcore/rrpr2_check.py as the checker. A
lab runs the learner's ikNewton and manipulability at slider poses.
"""

from __future__ import annotations

import html
import math
import subprocess

import numpy as np
from PySide6.QtWidgets import QHBoxLayout, QPushButton

from ctrlcore import robokin as rk
from ctrlcore import rrpr2_check as r2
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, stat_row
from .base import Page
from .robo_common import SEC_KIN, deg, labelled_slider, plain, playlist_badge, start_here
from .robo_cpp_workshop import ExerciseCard, WorkbenchCard, Workshop, _small_mat
from .robo_space_rigid import _block_html, _frame3d, in_words
from .robo_space_topo import _clear, _layout
from . import rrpr_render as rr

EXERCISES = [
    dict(ex=1, why=(
        "Page 126: τ = JᵀF. A payload of m kg hangs from the tool. To hold it "
        "still the hand must push up on it with f = (0, 0, mg). A force applied "
        "at the tool point p is, seen from the {s} origin, also a moment p × f, "
        "so the wrench in {s} is F<sub>s</sub> = (p × f, f). Each joint then "
        "feels its own column dotted with that wrench."),
        formula=_block_html("f = (0, 0, m·9.81)", "F<sub>s</sub> = (p × f, f)",
                            "τ = J<sub>s</sub>ᵀ F<sub>s</sub>", "τᵢ = J[i] · F<sub>s</sub>"),
        sig="Joints holdPayload(const Joints& th, double mass);",
        hint=("<code>toolPosition(th)</code>, <code>cross</code>, <code>stack</code> and "
              "<code>dotN(J[i], Fs)</code> are all available. Check yourself: the slide "
              "(joint 3) is horizontal at θ₂ = 0, so it should feel no weight there.")),
    dict(ex=2, why=(
        "Pages 126–127: the determinant is the volume factor of a matrix, zero "
        "exactly when a direction is crushed. You need it for μ₃ = √det(JJᵀ)."),
        formula=_block_html("det A = a₀₀(a₁₁a₂₂ − a₁₂a₂₁)", "− a₀₁(a₁₀a₂₂ − a₁₂a₂₀)",
                            "+ a₀₂(a₁₀a₂₁ − a₁₁a₂₀)", "det = λ₁λ₂λ₃"),
        sig="double det3(const Mat3& A);",
        hint="Expand along row 0, alternating signs + − +. One return statement is enough."),
    dict(ex=3, why=(
        "Page 127: an eigenvector is a direction A only stretches. Apply A over "
        "and over: every component gets multiplied by its own λ each time, so "
        "the component with the biggest λ wins and v swings onto the top "
        "eigenvector. Normalise each time so the numbers stay finite. This is "
        "the power method, the simplest eigenvalue algorithm there is."),
        formula=_block_html("v ← A v / ‖A v‖", "repeat 2000 times",
                            "λ = vᵀ A v", "(for symmetric PSD A)"),
        sig="double powerIteration(const Mat3& A, Vec3& v);",
        hint=("v is passed by reference: it comes in as the starting guess and must "
              "go out as the eigenvector. Normalise v once before the loop too.")),
    dict(ex=4, why=(
        "Page 127, all three eigenvalues of a symmetric 3 × 3. After finding λ₁ "
        "and v₁, subtract that piece out: A₂ = A − λ₁v₁v₁ᵀ has the same "
        "eigenvectors, but λ₁ replaced by 0 (deflation). Power iteration on A₂ "
        "then finds λ₂. The last one is free: the eigenvalues add up to the trace."),
        formula=_block_html("λ₁ = power(A)", "A₂ = A − λ₁ v₁v₁ᵀ",
                            "λ₂ = power(A₂)", "λ₃ = trace A − λ₁ − λ₂"),
        sig="Vec3 eigSym3(const Mat3& A);",
        hint=("Use the given start vectors (1, 0.7, 0.4) and (−0.4, 1, 0.7). "
              "(v₁v₁ᵀ)[i][j] = v₁[i]·v₁[j]. Return the largest first.")),
    dict(ex=5, why=(
        "Page 128: do not mix rad/s and m/s in one ellipsoid. Rows 3..5 of J<sub>b</sub> "
        "give the tool's linear velocity in its own axes; the ellipsoid of tool "
        "speeds uses A = J<sub>bv</sub>J<sub>bv</sub>ᵀ (3 × 3)."),
        formula=_block_html("J<sub>bv</sub> = rows 3, 4, 5 of J<sub>b</sub> (3 × 4)",
                            "A = J<sub>bv</sub> J<sub>bv</sub>ᵀ",
                            "A[r][c] = Σᵢ J[i][3+r] · J[i][3+c]", "Jac stores columns"),
        sig="Mat3 linearAAT(const Jac& Jb);",
        hint="Three nested loops: r, c over 0..2 and i over the 4 joints."),
    dict(ex=6, why=(
        "Page 128: three numbers for the shape of the tool-speed ellipsoid. μ₁ "
        "is the axis ratio (1 = round, ∞ = singular), μ₂ = μ₁² the condition "
        "number of A, μ₃ = σ₁σ₂σ₃ the volume. Uses exercises 2, 4 and 5."),
        formula=_block_html("λ = eigSym3(A)", "μ₁ = √(λ₁/λ₃)",
                            "μ₂ = λ₁/λ₃", "μ₃ = √det A"),
        sig="Vec3 manipulability(const Joints& th);",
        hint=("<code>linearAAT(jacobianBody(th))</code>. Try it at θ₂ = 90° in your main(): "
              "μ₁ jumps, because joints 1 and 4 line up.")),
    dict(ex=7, why=(
        "Every pseudoinverse, damped or not, ends in 'solve a small linear "
        "system'. Gaussian elimination turns A into an upper-triangular matrix "
        "row by row; back substitution then reads x off from the bottom up. "
        "Partial pivoting (swap the largest entry into the pivot) keeps it "
        "from dividing by zero; the first test has A[0][0] = 0 on purpose."),
        formula=_block_html("for each column k: pick the largest |A[i][k]|, swap",
                            "eliminate below: row i −= (A[i][k]/A[k][k]) row k",
                            "back-substitute from i = 3 down", "swap b with the rows"),
        sig="Vec4 solve4(Mat4 A, Vec4 b);",
        hint=("A and b are passed by value, so you can overwrite them. "
              "<code>std::swap(A[k], A[piv])</code> swaps whole rows.")),
    dict(ex=8, why=(
        "Pages 129–130: the RRPR Jacobian is tall (6 × 4): four joints cannot make "
        "every twist. The pseudoinverse then gives the least-squares θ̇, the one "
        "whose twist is closest to V: the normal equations JᵀJ θ̇ = JᵀV. Damping "
        "adds λ²I so the system stays solvable near a singularity."),
        formula=_block_html("θ̇ = (JᵀJ + λ²I)⁻¹ JᵀV", "(JᵀJ)ᵢⱼ = J[i] · J[j]",
                            "(JᵀV)ᵢ = J[i] · V", "λ = 0: plain J⁺"),
        sig="Joints pinvSolve(const Jac& J, const Vec6& V, double lambda);",
        hint="Build G and r with dotN, add λ² on G's diagonal, return solve4(G, r)."),
    dict(ex=9, why=(
        "Page 129: Newton for poses needs the error as a twist: [V<sub>b</sub>] = "
        "log T<sub>bd</sub>. The log undoes e<sup>[S]θ</sup> (page 122): first the "
        "rotation's angle and axis, then G⁻¹(θ) turns the position back into v."),
        formula=_block_html("θ = acos((tr R − 1)/2), &nbsp;[ω̂] = (R − Rᵀ)/(2 sin θ)",
                            "G⁻¹ = I/θ − [ω̂]/2 + (1/θ − cot(θ/2)/2)[ω̂]²",
                            "θ ≈ 0: return (0, p)", "return (ω̂θ, (G⁻¹p)θ)"),
        sig="Vec6 logT(const Mat4& T);",
        hint=("Clamp the cosine to [−1, 1] before acos. cot(x) = 1/tan(x). "
              "<code>unskew</code>, <code>skew</code> and <code>transpose</code> come with the library.")),
    dict(ex=10, why=(
        "Page 129, the video 6.2 algorithm: where is the hand (fkBody), how far "
        "from the target as a body twist (logT), which joint step fixes that "
        "best (pinvSolve with J<sub>b</sub>), repeat. Four or five steps from a "
        "good guess."),
        formula=_block_html("V<sub>b</sub> = log(T<sub>sb</sub>⁻¹(θ) T<sub>sd</sub>)",
                            "stop: ‖ω<sub>b</sub>‖, ‖v<sub>b</sub>‖ &lt; 1e-10",
                            "θ ← θ + J<sub>b</sub>⁺ V<sub>b</sub>", "at most 100 iterations"),
        sig="Joints ikNewton(const Mat4& Tsd, const Joints& guess);",
        hint="Copy the guess into a working θ, loop, and return θ. Uses exercises 7, 8 and 9."),
    dict(ex=11, why=(
        "Page 130: with only the tool's position as the task (3 numbers) the "
        "arm has 4 joints, one too many: a 1-D null space. N = I − J⁺J removes "
        "from any joint motion q₀ the part that would move the tool. First "
        "build the tool-point Jacobian: J<sub>s</sub>'s linear rows are the "
        "velocity of the point at the {s} origin, so move them to p."),
        formula=_block_html("column i of J<sub>p</sub> = vᵢ + ωᵢ × p",
                            "J⁺ = J<sub>p</sub>ᵀ(J<sub>p</sub>J<sub>p</sub>ᵀ)⁻¹ (fat)",
                            "N q₀ = q₀ − J<sub>p</sub>ᵀ (J<sub>p</sub>J<sub>p</sub>ᵀ)⁻¹ J<sub>p</sub> q₀",
                            "check: J<sub>p</sub> N q₀ = 0"),
        sig="Joints nullMotion(const Joints& th, const Joints& q0);",
        hint=("<code>Mat&lt;3, 4&gt; Jp{};</code> then <code>Jp * transpose(Jp)</code>, "
              "<code>inv3</code>, <code>Jp * q0</code> and <code>transpose(Jp) * y</code> "
              "all work with mrlite's operators.")),
]


def method_card() -> Card:
    c = Card("how this workshop works")
    c.add(in_words(
        "Same page-125 loop: read a card, go to its TODO, write it, press check. "
        "The difference: the arm itself (FK, both Jacobians, the adjoint, …) "
        "is given to you in rrpr_lib.hpp, so this workshop is only about pages "
        "126–130, and it works even if your page-125 file is unfinished."))
    c.add(body(_block_html(
        "<b>page 126</b><br>1 · statics: τ = J<sub>s</sub>ᵀF<sub>s</sub><br>2 · det3",
        "<b>page 127</b><br>3 · power iteration<br>4 · eigenvalues of a symmetric 3 × 3",
        "<b>page 128</b><br>5 · linear half of J<sub>b</sub><br>6 · μ₁, μ₂, μ₃",
        "<b>pages 129–130</b><br>7 · solve4 &nbsp; 8 · damped J⁺ &nbsp; 9 · log T<br>"
        "10 · Newton IK &nbsp; 11 · null-space motion")))
    c.add(plain(
        "<b>Given to you</b> (rrpr_lib.hpp): fkSpace, fkBody, jacobianSpace, jacobianBody, "
        "adjoint, invT, makeT, skew, unskew, expRot, expTwist, toolPosition, inv3, "
        "dotN / normN for any length, and Vec4 (= Joints). <b>Your file</b> is "
        f"<code>{html.escape(r2.WORKBOOK)}</code>; edit it here or in VS Code.<br>"
        "<b>Order matters:</b> 6 uses 2, 4, 5; 4 uses 3; 8 uses 7; 10 uses 8 and 9. The "
        "page tells you when an earlier exercise is the real cause."))
    return c


class IKRunLab:
    """Run the learner's ikNewton and manipulability at slider poses."""

    def __init__(self, ws: Workshop):
        self.ws = ws
        c = self.card = Card("lab (3-D): run MY inverse kinematics")
        c.add(in_words(
            "Pose a target arm and a starting guess. The page asks your compiled "
            "ikNewton for the joints that reach the target, and draws your answer "
            "solid with the target frame dashed. The reference answer and your "
            "manipulability at the guess pose are shown next to yours."))
        self.qd = [labelled_slider(c, "target θ1", -180, 180, 40, deg, self._draw),
                   labelled_slider(c, "target θ2", -20, 80, 35, deg, self._draw),
                   labelled_slider(c, "target d3", 0, 60, 30, lambda v: f"{v/100:.2f} m", self._draw),
                   labelled_slider(c, "target θ4", -180, 180, 50, deg, self._draw)]
        self.g = [labelled_slider(c, "guess θ1", -180, 180, 10, deg, self._draw),
                  labelled_slider(c, "guess θ2", -20, 80, 15, deg, self._draw),
                  labelled_slider(c, "guess d3", 0, 60, 10, lambda v: f"{v/100:.2f} m", self._draw),
                  labelled_slider(c, "guess θ4", -180, 180, 0, deg, self._draw)]
        row = QHBoxLayout()
        b = QPushButton("compile (if needed) and run my code here")
        b.clicked.connect(lambda: ws.build(lambda ok: self._draw()))
        row.addWidget(b)
        row.addStretch(1)
        c.add_layout(row)
        self.st_ik = Stat("my IK result", "--", theme.CYAN)
        self.st_err = Stat("pose error of my result", "--", theme.GOOD)
        self.st_mu = Stat("my μ at the guess (ref)", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_ik, self.st_err, self.st_mu))
        self.msg = body("")
        c.add(self.msg)
        self.cv = MplCanvas(width=7.6, height=4.6)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Default: your result should match the reference and the pose "
            "error should be ~1e-12. (2) Move the guess far (θ1 guess −150°): Newton may find "
            "a different θ that gives the same pose (θ₄ ± 2π), which is still a correct "
            "answer: the pose error tells you. (3) Set the guess θ2 near 80° (close to the "
            "θ₂ = 90° singularity) and watch μ₁ of your manipulability grow."))
        self._draw()

    @staticmethod
    def _vals(sl):
        v = [s.value() for s in sl]
        return np.array([math.radians(v[0]), math.radians(v[1]), v[2] / 100, math.radians(v[3])])

    def _run_mine(self, qd, g):
        try:
            r = subprocess.run([self.ws.exe] + [repr(float(x)) for x in (*qd, *g)],
                               capture_output=True, text=True, timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            return None
        vals, _ = r2.parse_output(r.stdout)
        if "pose_ik" not in vals or "pose_mu" not in vals:
            return None
        return vals["pose_ik"], vals["pose_mu"]

    def _draw(self, *_):
        qd, g = self._vals(self.qd), self._vals(self.g)
        Tsd = rk.fk_body(r2.M_HOME, r2.B_LIST, qd)
        ref = r2.ik_newton(Tsd, g)
        mu_ref = r2.manip(g)
        mine = self._run_mine(qd, g) if self.ws.up_to_date() else None
        q_show = ref if mine is None or not np.all(np.isfinite(mine[0])) else mine[0]
        _clear(self.cv)
        ax = self.cv.ax
        rr.draw_robot(ax, q_show, focus=-1, show_joints=False, frames=False)
        T = rk.fk_body(r2.M_HOME, r2.B_LIST, q_show)
        _frame3d(ax, T[:3, :3], T[:3, 3], scale=0.32, lw=2.2, name="b")
        _frame3d(ax, Tsd[:3, :3], Tsd[:3, 3], scale=0.5, lw=1.4, ls="--", name="d")
        ax.view_init(elev=22, azim=-60)
        ax.set_title(("your" if mine is not None else "reference") + " IK answer; dashed = target {d}",
                     color=theme.TEXT, fontsize=9)
        self.cv.refresh()
        fmt = lambda v: "(" + ", ".join(f"{x:+.3f}" for x in v) + ")"
        if mine is None:
            self.st_ik.set("not run")
            self.st_err.set("—")
            self.st_mu.set(f"— ({mu_ref[0]:.2f}, {mu_ref[1]:.2f}, {mu_ref[2]:.3f})")
            self.msg.setText(f"<span style='color:{theme.TEXT_DIM}'>Showing the reference. "
                             f"Reference IK: {fmt(ref)}. Press the button to run your code.</span>")
            return
        q, mu = mine
        Tm = rk.fk_body(r2.M_HOME, r2.B_LIST, q) if np.all(np.isfinite(q)) else np.full((4, 4), np.nan)
        err = float(np.max(np.abs(Tm - Tsd))) if np.all(np.isfinite(Tm)) else math.inf
        self.st_ik.set(fmt(q))
        self.st_err.set(f"{err:.1e}")
        self.st_err.set_color(theme.GOOD if err < 1e-6 else theme.BAD)
        self.st_mu.set(f"({mu[0]:.2f}, {mu[1]:.2f}, {mu[2]:.3f})")
        same = np.allclose(mu, mu_ref, rtol=1e-5, atol=1e-8)
        self.msg.setText(
            f"Reference IK: {fmt(ref)} · reference μ: ({mu_ref[0]:.2f}, {mu_ref[1]:.2f}, "
            f"{mu_ref[2]:.3f}) <span style='color:{theme.GOOD if same else theme.BAD}'>"
            f"{'μ matches' if same else 'μ differs'}</span>"
            f"<br><table><tr><td>target T<sub>sd</sub></td><td width='14'></td><td>T(your θ)</td></tr>"
            f"<tr><td>{_small_mat(Tsd)}</td><td></td><td>{_small_mat(Tm, Tsd)}</td></tr></table>")


def next_card() -> Card:
    c = Card("when everything is green: what you have built, and stretch goals")
    c.add(in_words(
        "With page 125 you now own a complete kinematics stack for a real arm: "
        "forward kinematics, Jacobians, statics, singularity measures, inverse "
        "kinematics and redundancy resolution. That is the core of every robot "
        "arm driver."))
    c.add(body(
        "<b>1. Damped IK.</b> Make ikNewton take λ and pass it to pinvSolve. Start a target "
        "at θ₂ = 89° and compare iteration counts with λ = 0 and λ = 0.05.<br>"
        "<b>2. Force ellipsoid.</b> The half-lengths are 1/√λᵢ of the same A. Print them "
        "at a few poses; where is the tool strongest?<br>"
        "<b>3. Manipulability map.</b> Scan θ₂ from −20° to 89° and print μ₁: where is the "
        "arm most isotropic?<br>"
        "<b>4. Track a path.</b> Move T<sub>sd</sub> along a line in small steps and call "
        "ikNewton from the previous answer each time (the video's controller idea): count "
        "iterations per step.<br>"
        "<b>5. Use the null space.</b> Keep the tool point fixed and add "
        "nullMotion(θ, −θ) to drive the joints towards zero: integrate θ ← θ + 0.05·N(−θ) "
        "and print toolPosition every step. It must not move."))
    return c


class RRPRWorkshop2Page(Page):
    TITLE = "C++ Workshop 2: Statics, Eigenvalues, IK and the Null Space"
    SUBTITLE = ("Eleven exercises on the same RRPR arm: hold a payload, write a determinant "
                "and an eigenvalue solver, measure manipulability, solve linear systems, "
                "take the log of a pose, run Newton–Raphson IK and move in the null space.")
    SECTION = SEC_KIN
    NOTES = playlist_badge(5)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "Pages 126–130 in code. The arm's kinematics comes ready-made, so every line "
            "you write is about the new ideas: τ = JᵀF (126), determinants and eigenvalues "
            "(127), the manipulability ellipsoid (128), Newton–Raphson IK with the body "
            "twist and the pseudoinverse (129), and null-space motion (130). Press "
            "<b>check my code</b> and the page compiles your file, runs 22 tests against a "
            "reference and names the mistake when it recognises it."))
        self.add(method_card())
        self.ws = Workshop(r2)
        self.bench = WorkbenchCard(self.ws)
        self.add(self.bench.card)
        self.ex_cards = [ExerciseCard(self.ws, spec, self._to_bench) for spec in EXERCISES]
        for e in self.ex_cards:
            self.add(e.card)
        self.ik_lab = IKRunLab(self.ws)
        self.add(self.ik_lab.card)
        self.add(next_card())

    def _to_bench(self):
        area = self.bench.card
        while area is not None and not hasattr(area, "ensureWidgetVisible"):
            area = area.parentWidget()
        if area is not None:
            area.ensureWidgetVisible(self.bench.card, 0, 0)
            area.ensureWidgetVisible(self.ws.editor, 0, 40)
