"""
Pages 129-130 extras -- the three Chapter 6 videos worked one by one.

    6        inverse kinematics of open chains   0 / 1 / many; atan2; law of
                                                 cosines; the 2R γ, α, β recipe
    6.2 (1)  numerical IK, coordinates           Newton–Raphson in 1-D, then
                                                 Δθ = J⁺e; what J⁺ guarantees
    6.2 (2)  numerical IK, poses                 T_bd = T_sb⁻¹T_sd, [V_b] = log T_bd,
                                                 θ ← θ + J_b⁺V_b; inverse velocity
                                                 kinematics θ̇ = J⁺V_d

Labs: the γ/α/β triangle, Newton on a 1R arm (the plateau trap), body-twist
Newton on the 3-D RRPR arm of page 125, and the geometry of the pseudoinverse.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QPushButton

from ctrlcore import robokin as rk
from ctrlcore import rrpr_check as rc
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, math_label, stat_row
from .robo_common import deg, draw_arm, labelled_slider, plain, square
from .robo_space_rigid import _frame3d, in_words, video_tag
from .robo_space_topo import _clear, _layout
from . import rrpr_render as rr

L2R = (1.0, 0.8)


def _table(head, rows):
    cell = f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}'"
    h = "".join(f"<th {cell} align='left'>{x}</th>" for x in head)
    r = "".join("<tr>" + "".join(f"<td {cell}>{x}</td>" for x in row) + "</tr>"
                for row in rows)
    return f"<table style='border-collapse:collapse'><tr>{h}</tr>{r}</table>"


def _arc(ax, c, r, a0, a1, col, label=None):
    t = np.linspace(a0, a1, 40)
    ax.plot(c[0] + r * np.cos(t), c[1] + r * np.sin(t), color=col, lw=1.6)
    if label:
        m = 0.5 * (a0 + a1)
        ax.text(c[0] + 1.35 * r * math.cos(m), c[1] + 1.35 * r * math.sin(m), label,
                color=col, fontsize=10, fontweight="bold", ha="center", va="center")


# ==========================================================================
# video 6: the problem, and the analytic 2R answer
# ==========================================================================

def ik_problem_card() -> Card:
    c = Card("video 6 — inverse kinematics: given the hand, find the joints")
    c.add(video_tag(
        "6", "inverse kinematics of open chains",
        "Forward kinematics (chapter 4): θ → T, always exactly one answer. "
        "Inverse kinematics: T → θ, which may have zero, one or many answers. "
        "Two ways to solve it: a closed-form formula from the robot's geometry, "
        "or an iteration that improves a guess."))
    c.add(in_words(
        "Forward kinematics is a function: every joint setting puts the hand "
        "somewhere definite. Running it backwards is not. Ask for a point "
        "beyond the arm's reach and there is no answer; ask for one at the "
        "very edge and there is exactly one (arm straight); ask for one "
        "inside and a 2R arm has two (elbow up or down). A 6R arm can have "
        "up to 16, and a redundant arm infinitely many."))
    c.add(body(_table(
        ("", "analytic (closed form)", "numerical (iterative)"),
        [("idea", "geometry of this particular robot: triangles, atan2, cosines",
          "guess θ, compare f(θ) with the target, correct with J, repeat"),
         ("works for", "robots whose structure allows it (2R, 6R with a spherical wrist, …)",
          "any robot, any number of joints"),
         ("answers", "<b>all</b> solutions at once", "<b>one</b> solution: the one near the guess"),
         ("needs a guess", "no", "yes, and a bad one can fail or find the other branch"),
         ("time", "fixed, tiny", "a few iterations; usually fast")])))
    return c


def atan2_card() -> Card:
    c = Card("two tools for every analytic solution: atan2 and the law of cosines")
    c.add(body(
        "<b>atan2(y, x)</b> is the angle from the x-axis to the arrow from the "
        "origin to the point (x, y), in (−180°, 180°]. Plain atan(y/x) throws "
        "away the signs when it divides, so it cannot tell opposite points "
        "apart:"))
    c.add(body(_table(
        ("point (x, y)", "atan(y/x)", "atan2(y, x)", "true direction"),
        [("(1, 1)", "45°", "45°", "up-right ✓"),
         ("(−1, −1)", "45° ✗", "−135°", "down-left"),
         ("(−1, 1)", "−45° ✗", "135°", "up-left"),
         ("(0, 1)", "1/0: error", "90°", "straight up")])))
    c.add(body(
        "<b>Law of cosines.</b> A triangle with sides a, b, c, and the interior "
        "angle C opposite side c:"))
    c.add(math_label(r"c^2=a^2+b^2-2ab\cos C\qquad\Rightarrow\qquad"
                     r"C=\arccos\frac{a^2+b^2-c^2}{2ab}", 17))
    c.add(plain(
        "Three side lengths fix a triangle completely, so they fix every angle "
        "in it. For the 2R arm the three sides are known: L₁, L₂, and the "
        "distance r from the shoulder to the target. arccos only returns 0° … "
        "180°, which is exactly right for an interior angle of a triangle; the "
        "± choice of which way the triangle folds is made separately."))
    return c


def triangle_card() -> Card:
    c = Card("the 2R recipe from the video: γ, α, β, and two solutions")
    c.add(body(
        "<b>Workspace.</b> The tip can reach the ring between two circles: inner "
        "radius |L₁ − L₂| (elbow folded back), outer radius L₁ + L₂ (arm "
        "straight). Outside: no solution. On the outer circle: one, θ₂ = 0. On "
        "the inner circle: one, θ₂ = π. Strictly inside: two."))
    c.add(body(
        "<b>The triangle</b> has corners at the shoulder, the elbow and the tip. "
        "Its sides are L₁, L₂ and r = √(x² + y²). Three angles do all the work:"))
    c.add(body(_table(
        ("angle", "what it is", "how to get it"),
        [("γ", "from the x-axis to the line shoulder → tip", "γ = atan2(y, x)"),
         ("α", "interior angle at the shoulder, between link 1 and that line",
          "α = arccos((r² + L₁² − L₂²) / (2L₁r))"),
         ("β", "interior angle at the elbow, between the two links",
          "β = arccos((L₁² + L₂² − r²) / (2L₁L₂))")])))
    c.add(body(_table(
        ("solution", "θ₁", "θ₂", "picture"),
        [("righty (elbow below the line)", "γ − α", "π − β", "θ₂ &gt; 0"),
         ("lefty (elbow above the line)", "γ + α", "β − π", "θ₂ &lt; 0, mirror image")])))
    c.add(body(
        "<b>Worked:</b> L = (1, 0.8), target (1.2, 0.6). r = 1.342, γ = 26.57°, "
        "α = arccos(2.16 / 2.683) = 36.39°, β = arccos(−0.16 / 1.6) = 95.74°. "
        "Righty: θ = (−9.83°, 84.26°). Lefty: θ = (62.96°, −84.26°). Put either "
        "into the forward kinematics and the tip lands on (1.2, 0.6). θ₂ = π − β "
        "because θ₂ is measured from link 1's direction, the exterior angle at "
        "the elbow, while β is the interior one."))
    return c


class TriangleLab:
    """The γ, α, β construction drawn on the arm for either branch."""

    def __init__(self):
        c = self.card = Card("lab: build the triangle, read off θ₁ and θ₂")
        c.add(in_words(
            "Move the target. The faint ring is the workspace. The triangle "
            "shoulder–elbow–tip is drawn for the branch you pick, with γ (pink), "
            "α (cyan) and β (orange) marked. The stats show both solutions."))
        self.tx = labelled_slider(c, "target x", -20, 20, 12, lambda v: f"{v/10:.1f} m", self._draw)
        self.ty = labelled_slider(c, "target y", -20, 20, 6, lambda v: f"{v/10:.1f} m", self._draw)
        self.branch = QComboBox()
        self.branch.addItems(["righty: θ₁ = γ − α, θ₂ = π − β", "lefty: θ₁ = γ + α, θ₂ = β − π"])
        self.branch.currentIndexChanged.connect(self._draw)
        c.add(self.branch)
        self.st_n = Stat("number of solutions", "--", theme.ACCENT)
        self.st_a = Stat("γ, α, β", "--", theme.PINK)
        self.st_r = Stat("righty θ", "--", theme.GOOD)
        self.st_l = Stat("lefty θ", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_n, self.st_a, self.st_r, self.st_l))
        self.cv = MplCanvas(width=6.4, height=4.6)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Drag the target onto the outer circle (e.g. x = 1.8, "
            "y = 0): α and β hit 0° and 180°, both branches merge into one, the "
            "arm is straight: a singular pose. (2) Pull it inside the inner circle "
            "(r &lt; 0.2): the cosines leave [−1, 1] and there is no triangle. "
            "(3) Put the target at negative x: γ jumps past 90°, which only "
            "atan2 gets right."))
        self._draw()

    def _draw(self, *_):
        L1, L2 = L2R
        x, y = self.tx.value() / 10, self.ty.value() / 10
        r = math.hypot(x, y)
        c = self.cv
        c.clear()
        ax = c.ax
        t = np.linspace(0, 2 * math.pi, 200)
        for rad in (L1 + L2, abs(L1 - L2)):
            ax.plot(rad * np.cos(t), rad * np.sin(t), color=theme.BORDER, lw=1)
        ax.fill_between(np.linspace(-1.8, 1.8, 2), -2, 2, color=theme.BG_INPUT, alpha=0)
        ax.plot(x, y, "*", color=theme.WARN, ms=14)
        ok = abs(L1 - L2) - 1e-9 <= r <= L1 + L2 + 1e-9
        if not ok:
            self.st_n.set("0: out of reach")
            for s in (self.st_a, self.st_r, self.st_l):
                s.set("—")
            square(ax, 2.0)
            ax.set_title("no triangle with these three sides")
            c.refresh()
            return
        g = math.atan2(y, x)
        ca = (r * r + L1 * L1 - L2 * L2) / (2 * L1 * max(r, 1e-12))
        cb = (L1 * L1 + L2 * L2 - r * r) / (2 * L1 * L2)
        a = math.acos(min(1, max(-1, ca)))
        b = math.acos(min(1, max(-1, cb)))
        right = np.array([g - a, math.pi - b])
        left = np.array([g + a, b - math.pi])
        one = abs(math.sin(b)) < 1e-6
        self.st_n.set("1 (boundary, singular)" if one else "2")
        self.st_a.set(f"{math.degrees(g):.1f}°, {math.degrees(a):.1f}°, {math.degrees(b):.1f}°")
        self.st_r.set(f"({math.degrees(right[0]):.1f}°, {math.degrees(right[1]):.1f}°)")
        self.st_l.set(f"({math.degrees(left[0]):.1f}°, {math.degrees(left[1]):.1f}°)")
        k = self.branch.currentIndex()
        q, other = (right, left) if k == 0 else (left, right)
        draw_arm(ax, L2R, other, color=theme.TEXT_FAINT, alpha=0.5, lw=2.5)
        pts = draw_arm(ax, L2R, q, color=theme.GOOD if k == 0 else theme.VIOLET)
        elbow = pts[1]
        ax.plot([0, x], [0, y], "--", color=theme.TEXT_DIM, lw=1)
        ax.plot([0, 1.9], [0, 0], color=theme.TEXT_FAINT, lw=0.8)
        _arc(ax, (0, 0), 0.45, 0, g, theme.PINK, "γ")
        sgn = -1 if k == 0 else 1
        _arc(ax, (0, 0), 0.3, g, g + sgn * a, theme.CYAN, "α")
        d1 = math.atan2(-elbow[1], -elbow[0])
        d2 = math.atan2(y - elbow[1], x - elbow[0])
        span = (d2 - d1 + math.pi) % (2 * math.pi) - math.pi
        _arc(ax, elbow, 0.22, d1, d1 + span, theme.ORANGE, "β")
        square(ax, 2.0)
        ax.set_title("righty (green) or lefty (violet); the other branch faint")
        c.refresh()


# ==========================================================================
# video 6.2 part 1: Newton–Raphson
# ==========================================================================

def newton_card() -> Card:
    c = Card("video 6.2, part 1 — numerical IK: Newton–Raphson on x_d − f(θ)")
    c.add(video_tag(
        "6.2", "numerical inverse kinematics (part 1 of 2)",
        "Write the hand pose as a few coordinates x = f(θ). Inverse kinematics "
        "is then root finding: solve g(θ) = x_d − f(θ) = 0. Newton–Raphson "
        "replaces f by its tangent, solves the linear problem, and repeats."))
    c.add(in_words(
        "In one dimension: stand at your guess θ₀ on the curve g(θ). Draw the "
        "tangent line there, slide down it to where it crosses zero, and call "
        "that θ₁. If g were a straight line you would be done in one step. It "
        "is curved, so θ₁ is only closer; repeat until the steps are tiny. "
        "Near a root every step roughly doubles the number of correct digits."))
    c.add(math_label(r"\Delta\theta=\left(\frac{\partial f}{\partial\theta}(\theta^0)\right)^{-1}"
                     r"\left(x_d-f(\theta^0)\right),\qquad\theta^1=\theta^0+\Delta\theta", 16))
    c.add(body(
        "<b>Two warnings from the picture.</b> (1) A curve can have several roots; "
        "Newton finds the one whose basin the guess sits in, not necessarily "
        "the one you wanted. (2) Near a flat stretch (a plateau, slope ≈ 0) "
        "the tangent is almost horizontal, so the step 1/slope is enormous and "
        "the next guess lands far away. Start close to a solution."))
    c.add(body(
        "<b>Many joints.</b> Expand f around the current guess θⁱ (Taylor): "
        "f(θ<sub>d</sub>) = f(θⁱ) + J(θⁱ)Δθ + higher-order terms. Drop the "
        "higher terms and the slope becomes the Jacobian:"))
    c.add(math_label(r"x_d-f(\theta^i)=J(\theta^i)\,\Delta\theta\qquad(1)"
                     r"\qquad\Rightarrow\qquad\Delta\theta=J^{-1}\left(x_d-f(\theta^i)\right)", 16))
    c.add(body(
        "J⁻¹ exists only for a square, non-singular J. The fix is the "
        "<b>pseudoinverse</b> J⁺ (page 127: J⁺ = VΣ⁺Uᵀ, divide by each σ that "
        "is not zero). It equals J⁻¹ when J is invertible and always exists. "
        "What it gives you for equation (1):"))
    c.add(body(_table(
        ("situation", "equation (1) has …", "Δθ* = J⁺e is …"),
        [("square, not singular", "exactly one solution", "that solution (J⁺ = J⁻¹)"),
         ("redundant (more joints than task numbers)", "infinitely many solutions",
          "the one with the <b>smallest ‖Δθ‖</b>: the least joint motion"),
         ("singular, or too few joints", "no exact solution",
          "the one that makes the <b>error ‖JΔθ − e‖ smallest</b> (least squares)")])))
    c.add(body(
        "<b>The algorithm.</b> (a) Guess θ⁰, set i = 0. (b) e = x<sub>d</sub> − f(θⁱ). "
        "If ‖e‖ ≤ ε, stop: θⁱ is the answer. (c) Otherwise θⁱ⁺¹ = θⁱ + J⁺(θⁱ)e, "
        "i ← i + 1, go to (b)."))
    c.add(plain(
        "<b>Inside a controller.</b> A new target x<sub>d</sub> arrives every "
        "millisecond and is only slightly different from the last one. So last "
        "step's answer is an excellent first guess, and one or two Newton "
        "iterations per cycle are enough. The bad-guess problem mostly "
        "disappears when you are always tracking a target that moves smoothly."))
    return c


class NewtonScalarLab:
    """1R arm: put the tip's x-coordinate at x_d. Two roots, a plateau at θ = 0."""

    def __init__(self):
        c = self.card = Card("lab: Newton in one dimension — a 1R arm, two roots and a plateau")
        c.add(in_words(
            "A single link of length 1 turns about the origin; its tip's "
            "x-coordinate is f(θ) = cos θ. Ask for x<sub>d</sub>: two angles "
            "work, ±arccos(x<sub>d</sub>). Left: the curve g(θ) = x<sub>d</sub> − "
            "cos θ with every Newton step drawn as its tangent line. Right: the "
            "arm at each guess. Change the initial guess and watch which root "
            "you get, and what happens near θ = 0, the top of the plateau."))
        self.xd = labelled_slider(c, "target x_d", -9, 9, 5, lambda v: f"{v/10:.1f}", self._draw)
        self.g0 = labelled_slider(c, "initial guess θ⁰", -170, 170, 20, deg, self._draw)
        self.n = labelled_slider(c, "show steps", 0, 8, 3, str, self._draw)
        self.st_r = Stat("roots", "--", theme.GOOD)
        self.st_q = Stat("θ after the shown steps", "--", theme.CYAN)
        self.st_e = Stat("|x_d − f(θ)|", "--", theme.WARN)
        c.add_layout(stat_row(self.st_r, self.st_q, self.st_e))
        self.cv = MplCanvas(width=7.8, height=3.7, ncols=2)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Guess 20°, step by step: 93.7° → 61.3° → 60.008° → "
            "60.0000003°: the digits double each time. (2) Guess −20°: the same "
            "method lands on the other root, −60°. (3) Guess 2°: the slope "
            "sin θ is almost zero, the first step is huge and goes far round the "
            "circle before it settles. (4) Set x<sub>d</sub> = 0.9: the roots move "
            "close to the plateau and good guesses get scarce. (5) The arm "
            "itself (right) shows what 'two solutions' means physically: tip "
            "above or below the x-axis."))
        self._draw()

    def _iterates(self):
        xd = self.xd.value() / 10
        th = math.radians(self.g0.value())
        out = [th]
        for _ in range(self.n.value()):
            s = math.sin(th)
            if abs(s) < 1e-9:
                break
            th = th - (xd - math.cos(th)) / s        # θ − g/g′, with g′ = sin θ
            out.append(th)
        return out

    def _draw(self, *_):
        xd = self.xd.value() / 10
        its = self._iterates()
        root = math.acos(xd)
        self.st_r.set(f"±{math.degrees(root):.2f}°")
        last = its[-1]
        self.st_q.set(f"{math.degrees(last):.5f}°")
        self.st_e.set(f"{abs(xd - math.cos(last)):.1e}")
        c = self.cv
        c.clear()
        a1, a2 = c.axes
        T = np.linspace(-math.pi, math.pi, 400)
        a1.plot(np.degrees(T), xd - np.cos(T), color=theme.ACCENT, lw=1.8, label="g(θ) = x_d − cos θ")
        a1.axhline(0, color=theme.TEXT_DIM, lw=0.8)
        for r in (root, -root):
            a1.plot(math.degrees(r), 0, "o", color=theme.GOOD, ms=7)
        for k, th in enumerate(its[:-1]):
            g, slope = xd - math.cos(th), math.sin(th)
            nxt = its[k + 1]
            a1.plot([math.degrees(th), math.degrees(nxt)], [g, 0], "-", color=theme.WARN, lw=1.2)
            a1.plot([math.degrees(th)] * 2, [0, g], ":", color=theme.TEXT_FAINT, lw=0.8)
            a1.plot(math.degrees(th), g, "o", color=theme.CYAN, ms=5)
            a1.text(math.degrees(th), g + 0.08, f"θ{k}", color=theme.CYAN, fontsize=7, ha="center")
        a1.plot(math.degrees(last), xd - math.cos(last), "o", color=theme.CYAN, ms=7)
        a1.set_xlim(-180, 180)
        a1.set_ylim(-1.2 + xd - 0.5, 1.2 + xd + 0.5)
        a1.set_xlabel("θ (deg)")
        a1.set_title("tangent steps (orange); roots (green)")
        c.legend(a1, loc="lower left")
        t = np.linspace(0, 2 * math.pi, 100)
        a2.plot(np.cos(t), np.sin(t), color=theme.BORDER, lw=1)
        a2.axvline(xd, color=theme.WARN, ls="--", lw=1)
        for k, th in enumerate(its):
            al = 0.25 + 0.75 * (k + 1) / len(its)
            a2.plot([0, math.cos(th)], [0, math.sin(th)], color=theme.CYAN, lw=3 if k == len(its) - 1 else 1.5,
                    alpha=al)
        a2.plot(0, 0, "o", color=theme.WARN, ms=7)
        square(a2, 1.3)
        a2.set_title("the arm at each guess; dashed: x = x_d")
        c.refresh()


# ==========================================================================
# video 6.2 part 2: poses, log, body Jacobian
# ==========================================================================

def pose_newton_card() -> Card:
    c = Card("video 6.2, part 2 — numerical IK for a full pose: T_sd, log and J_b")
    c.add(video_tag(
        "6.2", "numerical inverse kinematics (part 2 of 2)",
        "Targets are poses T_sd, not coordinate lists, so 'x_d − f(θ)' needs a "
        "replacement. The right one: the twist that would carry the current "
        "hand frame to the desired frame in one unit of time. Its matrix is a "
        "matrix logarithm."))
    c.add(in_words(
        "Three frames. {s} is fixed. {d} is where you want the hand, written "
        "T<sub>sd</sub>. {b} is where the hand is now, T<sub>sb</sub>(θⁱ) from "
        "forward kinematics. The desired frame seen from the hand is "
        "T<sub>bd</sub> = T<sub>sb</sub>⁻¹T<sub>sd</sub>. The log of a pose is the "
        "screw motion that produces it (page 122). So [V<sub>b</sub>] = log "
        "T<sub>bd</sub> is the body twist that, followed for 1 s, moves {b} "
        "exactly onto {d}. That twist plays the role of the error e."))
    c.add(math_label(r"T_{bd}(\theta^i)=T_{sb}^{-1}(\theta^i)\,T_{sd},\qquad"
                     r"[\mathcal{V}_b]=\log T_{bd},\qquad"
                     r"\theta^{i+1}=\theta^i+J_b^{\dagger}(\theta^i)\,\mathcal{V}_b", 16))
    c.add(body(
        "<b>Why the body Jacobian?</b> V<sub>b</sub> is written in the hand frame "
        "{b}, and J<sub>b</sub>θ̇ gives twists in {b} too. The two sides of "
        "equation (1) must use the same frame. (The space version works just as "
        "well: V<sub>s</sub> = [Ad<sub>T<sub>sb</sub></sub>]V<sub>b</sub> with "
        "J<sub>s</sub>.)<br>"
        "<b>When to stop.</b> Check the spin and the slide separately, since "
        "rad and m cannot be added: stop when ‖ω<sub>b</sub>‖ &lt; ε<sub>ω</sub> "
        "and ‖v<sub>b</sub>‖ &lt; ε<sub>v</sub> (for example 0.001 rad and 0.1 mm).<br>"
        "<b>The video's example</b> is a 4-joint RRRP arm: four iterations and the "
        "error is invisible. The lab below runs the same algorithm on the "
        "page-125 RRPR arm, four joints too."))
    c.add(plain(
        "A four-joint arm cannot reach every 6-D pose: J<sub>b</sub> is 6 × 4, "
        "two directions are always missing. If the target was made by the arm "
        "itself (some θ<sub>d</sub> exists) Newton converges to it. If it was "
        "not, J<sup>⁺</sup> returns least-squares steps and the iteration "
        "settles where the leftover twist cannot be reduced any further: the "
        "closest reachable pose, in the twist sense. The lab's 'tilt the "
        "target' box shows that."))
    return c


class BodyNewtonLab:
    """θ ← θ + J_b⁺ log(T_sb⁻¹T_sd) on the RRPR arm, iterate by iterate, in 3-D."""

    def __init__(self):
        c = self.card = Card("lab (3-D): body-twist Newton on the RRPR arm")
        c.add(in_words(
            "Choose the target {d} by posing a 'secret' arm (target sliders), "
            "then choose the initial guess. The iteration slider steps through "
            "Newton's guesses: the solid arm is θⁱ, faint frames are earlier "
            "hand frames, the large dashed frame is {d}. Right: ‖ω<sub>b</sub>‖ "
            "and ‖v<sub>b</sub>‖ per iteration, log scale."))
        self.qd = [labelled_slider(c, "target θ1", -180, 180, 50, deg, self._run),
                   labelled_slider(c, "target θ2", -20, 80, 40, deg, self._run),
                   labelled_slider(c, "target d3", 0, 60, 40, lambda v: f"{v/100:.2f} m", self._run),
                   labelled_slider(c, "target θ4", -180, 180, 60, deg, self._run)]
        self.q0 = [labelled_slider(c, "guess θ1", -180, 180, 0, deg, self._run),
                   labelled_slider(c, "guess θ2", -20, 80, 10, deg, self._run),
                   labelled_slider(c, "guess d3", 0, 60, 10, lambda v: f"{v/100:.2f} m", self._run),
                   labelled_slider(c, "guess θ4", -180, 180, 0, deg, self._run)]
        self.tilt = QCheckBox("tilt the target 30° about x_s (a pose this arm cannot reach)")
        self.tilt.stateChanged.connect(self._run)
        c.add(self.tilt)
        self.it = labelled_slider(c, "show iteration i", 0, 15, 15, str, self._draw)
        self.st_w = Stat("‖ω_b‖ (rad)", "--", theme.VIOLET)
        self.st_v = Stat("‖v_b‖ (m)", "--", theme.CYAN)
        self.st_n = Stat("iterations to 1e-8", "--", theme.ACCENT)
        self.st_q = Stat("θⁱ", "--", theme.GOOD)
        c.add_layout(stat_row(self.st_w, self.st_v, self.st_n, self.st_q))
        self.cv = MplCanvas(width=8.4, height=4.8)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Default target and guess: about four to six iterations "
            "to machine precision, the errors falling faster and faster (the curve "
            "bends down). (2) Scrub the iteration slider and watch the arm and its "
            "frame jump onto {d}. (3) Put the guess far away (θ1 guess = −150°): it "
            "may still converge, but slower, or to a different θ that gives the "
            "same pose, e.g. θ₄ off by 360°. (4) Tick 'tilt': the error stops "
            "falling and levels off. The arm got as close as a 4-joint arm can; "
            "J⁺ is now doing least squares. (5) Target θ2 = 90° is out of slider "
            "range on purpose: there joints 1 and 4 line up and J<sub>b</sub> "
            "loses rank."))
        self._run()

    def _vals(self, sl):
        v = [s.value() for s in sl]
        return np.array([math.radians(v[0]), math.radians(v[1]), v[2] / 100, math.radians(v[3])])

    def _run(self, *_):
        qd = self._vals(self.qd)
        Tsd = rk.fk_body(rc.M_HOME, rc.B_LIST, qd)
        if self.tilt.isChecked():
            Rx = rk.rot_exp([math.radians(30), 0, 0])
            Tsd = Tsd.copy()
            Tsd[:3, :3] = Rx @ Tsd[:3, :3]
        self.Tsd = Tsd
        q = self._vals(self.q0)
        self.Q, self.E = [q.copy()], []
        for _ in range(15):
            Tsb = rk.fk_body(rc.M_HOME, rc.B_LIST, q)
            S, th = rk.log6(rk.inv_T(Tsb) @ Tsd)
            Vb = S * th
            self.E.append((np.linalg.norm(Vb[:3]), np.linalg.norm(Vb[3:])))
            Jb = rk.jacobian_body(rc.B_LIST, q)
            q = q + np.linalg.pinv(Jb) @ Vb
            self.Q.append(q.copy())
        Tsb = rk.fk_body(rc.M_HOME, rc.B_LIST, q)
        S, th = rk.log6(rk.inv_T(Tsb) @ Tsd)
        self.E.append((np.linalg.norm(S[:3] * th), np.linalg.norm(S[3:] * th)))
        self.E = np.array(self.E)
        self._draw()

    def _draw(self, *_):
        i = self.it.value()
        q = self.Q[i]
        w, v = self.E[i]
        self.st_w.set(f"{w:.1e}")
        self.st_v.set(f"{v:.1e}")
        conv = [k for k, (a, b) in enumerate(self.E) if a < 1e-8 and b < 1e-8]
        self.st_n.set(str(conv[0]) if conv else "not reached")
        self.st_q.set("(" + ", ".join(f"{x:+.2f}" for x in q) + ")")
        fig = self.cv.fig
        fig.clear()
        ax = fig.add_subplot(1, 2, 1, projection="3d")
        bx = fig.add_subplot(1, 2, 2)
        self.cv.axes = [ax, bx]
        self.cv.ax = ax
        from .robo_space_topo import _style3d
        _style3d(ax)
        ax.set_axis_off()
        MplCanvas.style(bx)
        rr.draw_robot(ax, q, focus=-1, show_joints=False, frames=False)
        for k in range(i):
            T = rk.fk_body(rc.M_HOME, rc.B_LIST, self.Q[k])
            _frame3d(ax, T[:3, :3], T[:3, 3], scale=0.2, lw=1, alpha=0.35)
        T = rk.fk_body(rc.M_HOME, rc.B_LIST, q)
        _frame3d(ax, T[:3, :3], T[:3, 3], scale=0.32, lw=2.2, name="b")
        _frame3d(ax, self.Tsd[:3, :3], self.Tsd[:3, 3], scale=0.5, lw=1.4, ls="--", name="d")
        ax.view_init(elev=22, azim=-60)
        ax.set_title(f"iteration {i}: solid = θⁱ, dashed frame = target {{d}}",
                     color=theme.TEXT, fontsize=9)
        n = np.arange(len(self.E))
        bx.semilogy(n, np.maximum(self.E[:, 0], 1e-16), "o-", color=theme.VIOLET, label="‖ω_b‖")
        bx.semilogy(n, np.maximum(self.E[:, 1], 1e-16), "s-", color=theme.CYAN, label="‖v_b‖")
        bx.axvline(i, color=theme.WARN, ls=":", lw=1.2)
        bx.set_xlabel("iteration i")
        bx.set_title("the error twist V_b = log(T_bd)")
        self.cv.legend(bx, loc="upper right")
        fig.subplots_adjust(left=0.0, right=0.98, bottom=0.12, top=0.92, wspace=0.15)
        self.cv.refresh(layout=False)


# ==========================================================================
# page 130: inverse velocity kinematics and the pseudoinverse
# ==========================================================================

def inverse_velocity_card() -> Card:
    c = Card("video 6.2 (end) — inverse velocity kinematics: θ̇ = J⁺V_d")
    c.add(video_tag(
        "6.2", "inverse velocity kinematics",
        "Sometimes you do not need joint positions, only the joint speeds that "
        "produce a desired hand twist V_d right now. Then θ̇ = J⁺V_d, with V_d and "
        "J written in the same frame ({s} with J_s, or {b} with J_b)."))
    c.add(in_words(
        "This is one Newton step without the iteration: the twist you want is "
        "given directly, so you just undo J once. A controller that does this "
        "every millisecond moves the hand along a path, and it is how the "
        "redundancy formula on this page is used: J⁺V<sub>d</sub> does the task, "
        "the null-space term does whatever else you like."))
    c.add(body(_table(
        ("joints n vs task 6", "J is", "θ̇ = J⁺V_d gives"),
        [("n = 6, not singular", "square, invertible", "the exact and only θ̇ (J⁺ = J⁻¹)"),
         ("n &gt; 6 (redundant)", "fat: 6 × n", "an exact θ̇ with the smallest Σθ̇ᵢ²; add N θ̇₀ for other goals"),
         ("n &lt; 6 (deficient), or singular", "tall, or rank-deficient",
          "the θ̇ whose twist error Σ(V − V_d)ᵢ² is smallest")])))
    c.add(plain(
        "The book also gives weighted inverses that minimise other things, e.g. "
        "θ̇ᵀWθ̇ to make some joints 'expensive', or kinetic energy with W = M(θ) "
        "(page 138). The structure is always the same: among all θ̇ that do the "
        "job, pick the cheapest by your measure."))
    return c


def pinv_card() -> Card:
    c = Card("the pseudoinverse, opened up: two formulas, one SVD")
    c.add(in_words(
        "There are two different reasons J⁻¹ can fail, and the pseudoinverse has "
        "one answer for each. Too many joints: infinitely many θ̇ work, so pick "
        "the shortest. Too few (or singular): none works exactly, so pick the "
        "one that comes closest. Both are 'least squares', applied to "
        "different things."))
    c.add(body(_table(
        ("case", "formula", "it minimises", "tiny example"),
        [("fat, full row rank (redundant)", "J⁺ = Jᵀ(JJᵀ)⁻¹", "‖θ̇‖ among exact solutions",
          "J = [1 2], ẋ = 1: θ̇ = (1, 2)/5 = (0.2, 0.4)"),
         ("tall, full column rank (deficient)", "J⁺ = (JᵀJ)⁻¹Jᵀ", "‖Jθ̇ − v‖",
          "J = [1; 2], v = (1, 1): θ̇ = 3/5 = 0.6, error (0.4, −0.2)"),
         ("any shape, any rank", "J⁺ = VΣ⁺Uᵀ (SVD)", "both at once",
          "Σ⁺: 1/σᵢ for σᵢ &gt; 0, 0 for σᵢ = 0")])))
    c.add(body(
        "<b>Why the fat formula gives the shortest θ̇.</b> Every exact solution "
        "is θ̇* plus something in the null space. θ̇* = Jᵀ(…) is a combination of "
        "J's rows, and rows are perpendicular to the null space (Jn = 0 means "
        "every row dotted with n is 0). So ‖θ̇* + n‖² = ‖θ̇*‖² + ‖n‖²: adding "
        "any null motion only makes it longer. In the example, (0.2, 0.4) ⟂ (2, −1).<br>"
        "<b>Why the tall formula gives the closest twist.</b> The reachable "
        "twists Jθ̇ fill the hand reachable space. The closest point to V<sub>d</sub> is "
        "its perpendicular projection, so the error must be ⟂ every column: "
        "Jᵀ(Jθ̇ − V<sub>d</sub>) = 0, the 'normal equations', which solve to "
        "(JᵀJ)⁻¹JᵀV<sub>d</sub>. In the example (0.4, −0.2) ⟂ (1, 2)."))
    c.add(body(
        "<b>Near a singularity</b> some σ is tiny and 1/σ huge: a small hand "
        "request turns into violent joint speeds. Damped least squares replaces "
        "1/σ by σ/(σ² + λ²), i.e. J⁺ ≈ Jᵀ(JJᵀ + λ²I)⁻¹: nearly exact when σ ≫ λ, "
        "bounded by 1/(2λ) always, at the price of not quite doing the task near "
        "the singularity. The page-131 workshop codes the tall, damped version "
        "(JᵀJ + λ²I)⁻¹Jᵀ for the 6 × 4 RRPR Jacobian."))
    return c


class PinvGeometryLab:
    """The two jobs of J⁺ drawn: shortest exact solution, and closest approximation."""

    def __init__(self):
        c = self.card = Card("lab: what the pseudoinverse picks, in pictures")
        c.add(in_words(
            "Two tiny Jacobians you can see whole. <b>Redundant</b>: two joints, "
            "one task number, J = [a b]. Every θ̇ on the green line does the task "
            "exactly; J⁺ picks the point nearest the origin. Slide along the "
            "line with the null-motion slider: the task stays done, ‖θ̇‖ grows. "
            "<b>Deficient</b>: one joint, two task numbers, J = [a; b]. The joint "
            "can only make velocities along the green line; J⁺ picks the "
            "perpendicular foot below the desired velocity."))
        self.mode = QComboBox()
        self.mode.addItems(["redundant: J = [a b] (1 × 2)", "deficient: J = [a; b] (2 × 1)"])
        self.mode.currentIndexChanged.connect(self._draw)
        c.add(self.mode)
        self.a = labelled_slider(c, "a", -20, 20, 10, lambda v: f"{v/10:+.1f}", self._draw)
        self.b = labelled_slider(c, "b", -20, 20, 20, lambda v: f"{v/10:+.1f}", self._draw)
        self.t = labelled_slider(c, "redundant: desired ẋ · deficient: angle of v_d", -180, 180, 120,
                                 lambda v: f"ẋ {v/60:+.2f} · {v}°", self._draw)
        self.n = labelled_slider(c, "redundant only: add null motion", -20, 20, 0,
                                 lambda v: f"{v/10:+.1f}", self._draw)
        self.st1 = Stat("J⁺ answer", "--", theme.CYAN)
        self.st2 = Stat("its size / error", "--", theme.ACCENT)
        self.st3 = Stat("your point", "--", theme.WARN)
        c.add_layout(stat_row(self.st1, self.st2, self.st3))
        self.cv = MplCanvas(width=6.6, height=4.6)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Redundant mode, null motion 0: the cyan point is "
            "where the dashed circle (constant ‖θ̇‖) first touches the green line; "
            "the cyan arrow is perpendicular to the line. Move the null slider and "
            "the orange point slides along the line, still exact, always longer. "
            "(2) Deficient mode: the dotted red residual is perpendicular to the "
            "green line, the shortest possible miss. (3) Set a = b = 0: J = 0, "
            "rank 0, and J⁺ = 0 too: the pseudoinverse never divides by zero, it "
            "just gives up on directions it cannot do."))
        self._draw()

    def _draw(self, *_):
        a, b = self.a.value() / 10, self.b.value() / 10
        c = self.cv
        c.clear()
        ax = c.ax
        nrm2 = a * a + b * b
        if self.mode.currentIndex() == 0:
            xd = self.t.value() / 60
            sol = np.array([a, b]) * xd / nrm2 if nrm2 > 1e-12 else np.zeros(2)
            nul = np.array([-b, a]) / math.sqrt(nrm2) if nrm2 > 1e-12 else np.zeros(2)
            mine = sol + self.n.value() / 10 * nul
            self.st1.set(f"θ̇* = ({sol[0]:+.2f}, {sol[1]:+.2f})")
            self.st2.set(f"‖θ̇*‖ = {np.linalg.norm(sol):.3f}")
            self.st3.set(f"‖θ̇‖ = {np.linalg.norm(mine):.3f}, Jθ̇ = {a * mine[0] + b * mine[1]:+.2f}")
            if nrm2 > 1e-12:
                s = np.linspace(-6, 6, 2)
                line = sol[:, None] + nul[:, None] * s
                ax.plot(*line, color=theme.GOOD, lw=2, label=f"all exact solutions: aθ̇₁ + bθ̇₂ = {xd:.2f}")
            t = np.linspace(0, 2 * math.pi, 100)
            r = np.linalg.norm(sol)
            ax.plot(r * np.cos(t), r * np.sin(t), "--", color=theme.TEXT_DIM, lw=1)
            ax.annotate("", xy=sol, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=theme.CYAN, lw=2.2))
            ax.plot(*mine, "o", color=theme.WARN, ms=8, label="J⁺ẋ + null motion")
            ax.plot(*sol, "o", color=theme.CYAN, ms=7, label="J⁺ẋ (shortest)")
            ax.set_xlabel("θ̇₁")
            ax.set_ylabel("θ̇₂")
            ax.set_title("joint-speed plane")
        else:
            ang = math.radians(self.t.value())
            vd = 1.5 * np.array([math.cos(ang), math.sin(ang)])
            col = np.array([a, b])
            th = col @ vd / nrm2 if nrm2 > 1e-12 else 0.0
            v = col * th
            self.st1.set(f"θ̇* = {th:+.3f}")
            self.st2.set(f"‖Jθ̇* − v_d‖ = {np.linalg.norm(v - vd):.3f}")
            self.st3.set("—")
            if nrm2 > 1e-12:
                u = col / math.sqrt(nrm2)
                ax.plot(*(u[:, None] * np.linspace(-3, 3, 2)), color=theme.GOOD, lw=2,
                        label="reachable: θ̇ · (a, b)")
            ax.annotate("", xy=vd, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=theme.WARN, lw=2.2))
            ax.annotate("", xy=v, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=theme.CYAN, lw=2.2))
            ax.plot(*np.vstack([v, vd]).T, ":", color=theme.BAD, lw=2, label="error (⟂ the line)")
            ax.plot([], [], color=theme.WARN, label="desired v_d")
            ax.plot([], [], color=theme.CYAN, label="J J⁺ v_d (closest)")
            ax.set_xlabel("v₁")
            ax.set_ylabel("v₂")
            ax.set_title("hand-velocity plane")
        square(ax, 2.5)
        c.legend(ax, loc="lower left")
        c.refresh()
