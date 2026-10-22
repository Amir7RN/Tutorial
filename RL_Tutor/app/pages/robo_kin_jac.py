"""
Pages 124-125 extras -- the six Chapter 5 videos worked one by one.

    5      overview                 x = f(θ), J = ∂f/∂θ, limits -> shapes, τ = JᵀF
    5.1.1  space Jacobian           columns are S_i carried by the joints before
    5.1.2  body Jacobian            columns are B_i carried back by the joints after
    5.2    statics                  τ = Jᵀ F from power, in any frame
    5.3    singularities            rank, tall / square / fat, what the arm loses
    5.4    manipulability           A = J Jᵀ, ellipsoid axes, three measures

Each video gets a video_tag(), a WHAT IS GOING ON box and at least one lab.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QPushButton

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, math_label, stat_row
from .robo_common import deg, draw_arm, labelled_slider, mat_html, plain, square
from .robo_space_rigid import (PINK, _block_html, _frame3d, _vec, in_words, link_back,
                               video_tag)
from .robo_space_topo import _clear, _layout

COLS = (theme.BAD, theme.VIOLET, theme.PINK, theme.GOOD, theme.ACCENT)


def _rad(sliders):
    return np.radians([s.value() for s in sliders])


def _arrow(ax, p, d, col, lw=2.0, ls="-", alpha=1.0):
    ax.annotate("", xy=p + d, xytext=p,
                arrowprops=dict(arrowstyle="-|>", color=col, lw=lw, ls=ls,
                                alpha=alpha, shrinkA=0, shrinkB=0))


def _cross2(a, b):
    """z-component of the planar cross product a × b."""
    return float(a[0] * b[1] - a[1] * b[0])


def _rank(A, tol=1e-6):
    return int(np.sum(np.linalg.svd(A, compute_uv=False) > tol))


def _vec_s(v, prec=2):
    return "(" + ", ".join(f"{x + 0.0:+.{prec}f}" for x in v) + ")"


# ==========================================================================
# connect the dots
# ==========================================================================

def dots_card() -> Card:
    c = Card("connect the dots: why the Jacobian is the hub of robotics")
    c.add(in_words(
        "Chapter 4 gave the pose T(θ). Almost everything after it uses one "
        "more object: the Jacobian J(θ), the matrix that turns small joint "
        "motions into small hand motions. Learn what its columns mean and "
        "most of the remaining chapters become 'J again, used a new way'."))
    rows = [
        ("124", "velocity", "V = J θ̇", "joint speeds → hand twist"),
        ("126", "statics", "τ = Jᵀ F", "hand wrench → joint torques"),
        ("126", "singularity", "rank J drops", "directions the hand loses"),
        ("128", "manipulability", "ellipsoid of J Jᵀ", "how far from singular"),
        ("129", "inverse kinematics", "Δθ = J⁺ e", "Newton steps toward a pose"),
        ("130", "redundancy", "N = I − J⁺J", "arm moves, hand stays put"),
        ("133–139", "dynamics", "τ = M θ̈ + h + JᵀF", "contact forces enter through Jᵀ"),
        ("143–145", "control", "τ = Jᵀ(K e − B V)", "task-space, impedance, force control"),
    ]
    cell = f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}'"
    mono = (f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}; "
            f"font-family:Consolas; color:{theme.CYAN}'")
    html = "".join(f"<tr><td {cell}>{p}</td><td {cell}><b>{t}</b></td>"
                   f"<td {mono}>{f}</td><td {cell}>{w}</td></tr>"
                   for p, t, f, w in rows)
    c.add(body(f"<table style='border-collapse:collapse'><tr><th {cell} align='left'>"
               f"page</th><th {cell} align='left'>topic</th><th {cell} align='left'>"
               f"the J formula</th><th {cell} align='left'>what it does</th></tr>"
               f"{html}</table>"))
    c.add(plain(
        "Two facts carry all of it. <b>(1) Column i of J is what joint i "
        "alone does to the hand</b>, at unit speed, with the other joints "
        "frozen. <b>(2) Power is the same at the joints and at the hand</b>, "
        "so the map for forces is the transpose of the map for velocities. "
        "Every lab on these two pages is one of those facts seen from a new "
        "angle."))
    return c


# ==========================================================================
# video 5 -- the overview, with coordinates instead of twists
# ==========================================================================

def overview_card() -> Card:
    c = Card("video 5 — velocity kinematics and statics in one picture")
    c.add(video_tag(
        "5", "velocity kinematics and statics",
        "The whole chapter with plain coordinates first: differentiate x = "
        "f(θ) to get J, read its columns on a 2R arm, push joint-speed limits "
        "through J, then get τ = Jᵀf from power. Twists and wrenches come in "
        "the later videos."))
    c.add(in_words(
        "Write the hand's position as a list of numbers x = f(θ). Take the "
        "time derivative: ẋ = (∂f/∂θ) θ̇. That matrix of partial derivatives "
        "is the Jacobian. With m hand coordinates and n joints it is m × n, "
        "and it changes as the arm moves."))
    c.add(math_label(r"x=f(\theta)\ \Rightarrow\ \dot x=\frac{\partial f}"
                     r"{\partial\theta}\dot\theta=J(\theta)\dot\theta"
                     r"=J_1\dot\theta_1+J_2\dot\theta_2", 16))
    c.add(body(
        "<b>The 2R arm, one step at a time.</b> Write c₁ = cos θ₁, s₁ = sin θ₁, "
        "c₁₂ = cos(θ₁+θ₂), s₁₂ = sin(θ₁+θ₂).<br>"
        "<b>Step 1, forward kinematics</b> (where the tip is): "
        "x₁ = L₁c₁ + L₂c₁₂,&nbsp; x₂ = L₁s₁ + L₂s₁₂.<br>"
        "<b>Step 2, differentiate in time.</b> Both θ₁ and θ₂ change, so by "
        "the chain rule each coordinate picks up one term per joint:"))
    c.add(math_label(r"\dot x_1=\frac{\partial x_1}{\partial\theta_1}\dot\theta_1"
                     r"+\frac{\partial x_1}{\partial\theta_2}\dot\theta_2,\qquad"
                     r"\dot x_2=\frac{\partial x_2}{\partial\theta_1}\dot\theta_1"
                     r"+\frac{\partial x_2}{\partial\theta_2}\dot\theta_2", 15))
    c.add(body(
        "<b>Step 3, collect the four partial derivatives into a matrix.</b> "
        "Row = which tip coordinate, column = which joint. That matrix is J:"))
    c.add(body(_block_html(
        "∂x₁/∂θ₁ = −L₁s₁ − L₂s₁₂", "∂x₁/∂θ₂ = −L₂s₁₂",
        "∂x₂/∂θ₁ = L₁c₁ + L₂c₁₂", "∂x₂/∂θ₂ = L₂c₁₂")))
    c.add(body(
        "<b>Step 4, read the columns as arrows.</b> Column 1 is "
        "J₁ = (−(L₁s₁ + L₂s₁₂), L₁c₁ + L₂c₁₂) = (−x₂, x₁): the tip position "
        "turned 90°. So J₁ is perpendicular to the line from joint 1 to the "
        "tip and exactly as long as it: the tip swinging on a circle about "
        "joint 1. Column 2 is J₂ = (−L₂s₁₂, L₂c₁₂): link 2 turned 90°, the tip "
        "swinging about the elbow. The derivative and the picture are the "
        "same thing.<br>"
        "<b>Step 5, put it back together:</b> v<sub>tip</sub> = J θ̇ = "
        "J₁θ̇₁ + J₂θ̇₂. Each joint contributes its own arrow, scaled by its "
        "speed, and the arrows add tip-to-tail.<br>"
        "<b>Numbers.</b> L = (1, 0.8), θ = (0°, 90°): tip = (1, 0.8), "
        "J₁ = (−0.8, 1), J₂ = (−0.8, 0). With θ̇ = (1, 1) rad/s the tip moves "
        "at (−1.6, 1.0)."))
    c.add(body(
        "<b>How J₁ and J₂ are related: the angle between them.</b> The "
        "determinant of a 2 × 2 matrix is the signed area of the parallelogram "
        "its columns span, |J₁||J₂| sin α, where α is the angle from J₁ to J₂. "
        "Multiply out the matrix above and the θ₁ terms cancel:"))
    c.add(math_label(r"\det J=|J_1|\,|J_2|\sin\alpha=L_1L_2\sin\theta_2", 15))
    c.add(body(
        "Both columns are lines in the arm turned by 90°, so α is also the "
        "angle between 'base → tip' and 'elbow → tip'. Only the elbow angle "
        "matters, never θ₁ (turning the whole arm turns both arrows together). "
        "At θ₂ = 90° the arrows are as far apart as they can get; at θ₂ = 0° "
        "or 180° sin θ₂ = 0, the arrows are parallel, det J = 0 and the "
        "rank drops from 2 to 1."))
    c.add(body(_block_html(
        "<b>limits on joint speed</b><br>square |θ̇ᵢ| ≤ 1 → <b>parallelogram</b> "
        "of tip speeds<br>circle ‖θ̇‖ ≤ 1 → <b>ellipse</b> (manipulability)",
        "<b>limits on joint torque</b><br>square |τᵢ| ≤ 1 → parallelogram of "
        "tip forces<br>circle ‖τ‖ ≤ 1 → <b>force ellipse</b>",
        "<b>singular pose</b> (θ₂ = 0 or 180°)<br>J₁ ∥ J₂: the tip can move "
        "only along one line;<br>the ellipse is a line segment",
        "<b>power</b>: θ̇ᵀτ = v<sub>tip</sub>ᵀf<sub>tip</sub> = θ̇ᵀJᵀf for "
        "every θ̇<br>⇒ <b>τ = Jᵀ f<sub>tip</sub></b>")))
    c.add(plain(
        "<b>Why draw these shapes at all?</b> Each motor has a top speed. The "
        "shape answers one practical question: <b>with every motor inside its "
        "limit, how fast can the tip go in each direction?</b> Push the "
        "whole square (or circle) of allowed joint speeds through J and you "
        "get every tip velocity the arm can reach right now.<br>"
        "• A <b>long</b> direction of the shape: the tip moves fast that way "
        "with little motor effort.<br>"
        "• A <b>short</b> direction: the tip is slow that way.<br>"
        "• A <b>flat</b> shape (zero width): the tip cannot move that way at "
        "all. That is a singularity.<br>"
        "<b>The chain to remember:</b> J₁ ∥ J₂ ⇔ sin α = 0 ⇔ det J = "
        "L₁L₂ sin θ₂ = 0 ⇔ rank J = 1 ⇔ the shape is flat ⇔ one tip "
        "direction is lost. Sizes, in numbers: the parallelogram's area is "
        "4|det J| and the ellipse's is π|det J|; the ellipse's half-axes are "
        "the singular values σ₁ ≥ σ₂ of J, and σ₂ = 0 exactly at a "
        "singularity. Those same numbers drive page 128 (how close to "
        "singular, video 5.4) and page 129 (inverse kinematics blows up as "
        "σ₂ → 0, because a tiny tip step needs huge joint steps)."))
    c.add(plain(
        "<b>Easy to move = hard to push, and the other way round.</b> A force "
        "whose line passes close to the joints needs little torque, so the arm "
        "is strong that way; it is usually the way the arm moves slowly. Hold "
        "your arm straight out: you can resist a big push along the arm "
        "(it goes through your joints), but holding a book at arm's length "
        "is hard. The velocity limits and force limits are reciprocal. These "
        "formulas assume a static arm where all joint torque goes to the hand "
        "force; gravity is handled separately."))
    return c


class VelocitySetLab:
    """Joint-rate limits (square or circle) pushed through J of a 2R arm."""

    L = (1.0, 0.8)

    def __init__(self):
        c = self.card = Card("lab: joint-speed limits become a shape of tip velocities")
        c.add(in_words(
            "Left: the joint-speed plane. Every allowed pair (θ̇₁, θ̇₂) lies in "
            "the square (each motor at most 1 rad/s) or the circle. Right: the "
            "arm. Your chosen speeds give a tip velocity built tip-to-tail from "
            "θ̇₁J₁ and θ̇₂J₂. The whole allowed set maps to a parallelogram "
            "(square) or an ellipse (circle)."))
        self.limit = QComboBox()
        self.limit.addItems(["square limits: |θ̇₁| ≤ 1, |θ̇₂| ≤ 1",
                             "circle limits: θ̇₁² + θ̇₂² ≤ 1"])
        self.limit.currentIndexChanged.connect(self._draw)
        c.add(self.limit)
        self.q = [labelled_slider(c, f"θ{i+1}", -180, 180, v, deg, self._draw)
                  for i, v in enumerate((30, 75))]
        hund = lambda v: f"{v/100:+.2f} rad/s"
        self.qd = [labelled_slider(c, f"θ̇{i+1}", -100, 100, v, hund, self._draw)
                   for i, v in enumerate((100, 100))]
        self.st_v = Stat("v_tip = J θ̇", "--", theme.CYAN)
        self.st_r = Stat("rank J", "--", theme.WARN)
        self.st_a = Stat("angle between J₁ and J₂", "--", theme.VIOLET)
        self.st_d = Stat("det J = L₁L₂ sin θ₂", "--", theme.GOOD)
        c.add_layout(stat_row(self.st_v, self.st_r, self.st_a, self.st_d))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Leave θ̇ = (1, 1): that is corner A of the square, "
            "both motors flat out forward. Its image A′ is a corner of the "
            "parallelogram. (2) Set θ̇₂ = 0: the cyan tip velocity is exactly "
            "the red arrow J₁, perpendicular to the line from the base to the "
            "tip. (3) Drag θ₂ toward 0°: J₁ and J₂ swing into line, the "
            "parallelogram and ellipse squash flat, and rank J drops to 1: "
            "a singularity. (4) Switch to circle limits and turn θ₂ around: "
            "the ellipse changes shape with the pose; this is the "
            "manipulability ellipse of video 5.4. (5) Move θ₁ alone: the "
            "angle and det J do not change. Move θ₂: det J follows "
            "L₁L₂ sin θ₂ = 0.8 sin θ₂, largest at θ₂ = ±90°, zero at 0° and 180°."))
        self._draw()

    def _draw(self, *_):
        q = _rad(self.q)
        qd = np.array([s.value() / 100 for s in self.qd])
        J = rk.planar_jacobian(self.L, q)
        v = J @ qd
        r = _rank(J)
        cosang = J[:, 0] @ J[:, 1] / (np.linalg.norm(J[:, 0]) * np.linalg.norm(J[:, 1]) + 1e-12)
        self.st_v.set(_vec_s(v))
        self.st_r.set(f"{r}" + ("  (singular)" if r < 2 else ""))
        self.st_r.set_color(theme.BAD if r < 2 else theme.WARN)
        self.st_a.set(f"{math.degrees(math.acos(np.clip(cosang, -1, 1))):.1f}°")
        self.st_d.set(f"{np.linalg.det(J):+.3f}")
        circ = self.limit.currentIndex() == 1
        c = self.cv
        c.clear()
        a0, a1 = c.axes
        sq = np.array([[1, 1], [-1, 1], [-1, -1], [1, -1], [1, 1]], float)
        t = np.linspace(0, 2 * math.pi, 100)
        ci = np.vstack([np.cos(t), np.sin(t)]).T
        a0.plot(*sq.T, color=theme.WARN, lw=2 if not circ else 1, alpha=1 if not circ else 0.35)
        a0.plot(*ci.T, color=theme.GOOD, lw=2 if circ else 1, alpha=1 if circ else 0.35)
        for name, p in zip("ABCD", sq[:4]):
            a0.text(*(1.12 * p), name, color=theme.WARN, ha="center", va="center")
        a0.plot(*qd, "o", color=theme.CYAN, ms=8)
        a0.axhline(0, color=theme.BORDER, lw=0.8)
        a0.axvline(0, color=theme.BORDER, lw=0.8)
        square(a0, 1.5)
        a0.set_xlabel("θ̇₁ (rad/s)")
        a0.set_ylabel("θ̇₂ (rad/s)")
        a0.set_title("joint-speed space")
        pts = draw_arm(a1, self.L, q)
        tip = pts[-1]
        k = 0.5
        if circ:
            E = (J @ ci.T).T
            a1.plot(*(tip + k * E).T, color=theme.GOOD, lw=2)
        else:
            P = (J @ sq.T).T
            a1.plot(*(tip + k * P).T, color=theme.WARN, lw=2)
            for name, p in zip("ABCD", P[:4]):
                a1.text(*(tip + k * 1.12 * p), name + "′", color=theme.WARN,
                        ha="center", va="center", fontsize=8)
        _arrow(a1, tip, k * qd[0] * J[:, 0], theme.BAD)
        _arrow(a1, tip + k * qd[0] * J[:, 0], k * qd[1] * J[:, 1], theme.VIOLET)
        _arrow(a1, tip, k * v, theme.CYAN, lw=2.6)
        a1.plot([0, tip[0]], [0, tip[1]], ":", color=theme.BAD, lw=1)
        a1.plot([pts[1, 0], tip[0]], [pts[1, 1], tip[1]], ":", color=theme.VIOLET, lw=1)
        square(a1, 2.6)
        a1.set_title("red θ̇₁J₁ + violet θ̇₂J₂ = cyan v_tip (×0.5)")
        c.refresh()


# ==========================================================================
# the spatial 5R arm of videos 5.1.1, 5.1.2 and the 3-D ellipsoid lab
# ==========================================================================
# Waist about z at the origin, shoulder / elbow / wrist pitch about -y (so a
# positive angle lifts the arm), wrist roll about x. Hand {b} 0.5 past the
# wrist, aligned with {s} at home.

ARM5_W = np.array([[0, 0, 1], [0, -1, 0], [0, -1, 0], [0, -1, 0], [1, 0, 0]], float)
ARM5_Q = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 1], [1.8, 0, 1], [1.8, 0, 1]], float)
ARM5_S = np.array([rk.screw_axis(q, w) for q, w in zip(ARM5_Q, ARM5_W)]).T
ARM5_M = rk.rp_to_T(np.eye(3), [2.3, 0, 1])
ARM5_B = rk.adjoint(rk.inv_T(ARM5_M)) @ ARM5_S
ARM5_HOME = (20, 30, -50, 40, 30)


def arm5_prefix(q, k):
    """e^[S1]θ1 ⋯ e^[Sk]θk (identity for k = 0)."""
    return rk.fk_space(np.eye(4), ARM5_S[:, :k], q[:k])


def arm5_points(q):
    """Base, joints 2-5 and the hand, in {s}."""
    pts = [np.array([0, 0, -0.3])]
    for i in range(5):
        T = arm5_prefix(q, i)
        pts.append(T[:3, :3] @ ARM5_Q[i] + T[:3, 3])
    pts.append(rk.fk_space(ARM5_M, ARM5_S, q)[:3, 3])
    return np.array(pts)


def draw_arm5(ax, q, color=theme.CYAN, alpha=1.0, lw=5, G=None):
    p = arm5_points(q)
    if G is not None:
        p = (G[:3, :3] @ p.T).T + G[:3, 3]
    ax.plot(*p.T, "-", color=color, lw=lw, alpha=alpha, solid_capstyle="round")
    ax.plot(*p[1:6].T, "o", color=theme.WARN, ms=5 if alpha > 0.5 else 3, alpha=alpha)
    return p


def _style_arm_axes(ax):
    ax.set_xlim(-2.2, 2.2)
    ax.set_ylim(-2.2, 2.2)
    ax.set_zlim(-0.5, 2.5)
    ax.set_box_aspect((1, 1, 0.7))


def space_card() -> Card:
    c = Card("video 5.1.1 — the space Jacobian: columns without differentiating")
    c.add(video_tag(
        "5.1.1", "space Jacobian",
        "Now the hand velocity is a twist V_s in {s}, so J_s is 6 × n. Build "
        "column i by asking which joints can move joint i's axis relative to "
        "{s}: only the ones between it and the base."))
    c.add(link_back("124, VIDEO 5",
        "On the 2R arm, column i was 'the tip velocity when only joint i "
        "turns, at 1 rad/s', and it came out as a line in the arm turned 90°: "
        "ω × r. Two things change in 3-D. (1) The hand also rotates, so a "
        "column must carry an angular part ω as well. (2) Different points of "
        "the hand move at different speeds, so we must say which point. The "
        "twist answers both: V = (ω, v), with v the velocity of the point at "
        "the {s} origin. For a revolute joint with unit axis ω through a point "
        "q, turning at 1 rad/s, that twist is (ω, −ω × q): the screw axis Sᵢ "
        "of page 123."))
    c.add(in_words(
        "So column i of J<sub>s</sub> is joint i's screw axis (ωᵢ, −ωᵢ × qᵢ), "
        "computed from where the axis is <b>right now</b>. At home that is "
        "the Sᵢ you wrote down on page 123. When the arm moves, joints 1 … i−1 "
        "(the ones between joint i and the base) pick axis i up and carry it "
        "to a new place and direction. To get the new column, apply that "
        "same rigid motion to Sᵢ; the adjoint is the tool that moves a twist "
        "by a rigid motion. Joints i … n sit beyond axis i and cannot move it."))
    c.add(math_label(r"\mathcal{V}_s=J_s(\theta)\dot\theta,\quad J_{s1}=\mathcal{S}_1,"
                     r"\quad J_{si}=[\mathrm{Ad}_{e^{[\mathcal{S}_1]\theta_1}\cdots"
                     r" e^{[\mathcal{S}_{i-1}]\theta_{i-1}}}]\,\mathcal{S}_i", 15))
    c.add(body(
        "<b>The argument, for column 3 of a 5R arm.</b> Start at home: "
        "J<sub>s3</sub> = S₃. Turn joint 5, then 4, then 3 itself: none of "
        "them sits between joint 3 and the base, so joint 3's axis does not "
        "move in {s}, and J<sub>s3</sub> is still S₃. Now turn joint 2: the "
        "axis moves. Imagine a frame {s′} that moved along with it, so joint 3 "
        "looks from {s′} exactly as it looked from {s} at home; {s′} sits at "
        "e<sup>[S₂]θ₂</sup>. Turn joint 1 too, giving {s″} at "
        "e<sup>[S₁]θ₁</sup>e<sup>[S₂]θ₂</sup>. In {s″} the axis is still S₃, "
        "so change frames with the adjoint: J<sub>s3</sub> = "
        "[Ad<sub>T<sub>ss″</sub></sub>]S₃."))
    c.add(body(
        "<b>Check it on the 2R arm.</b> Both axes point along z, so ω = (0, 0, 1). "
        "Joint 1 sits at the origin, q₁ = 0: J<sub>s1</sub> = (0, 0, 1, 0, 0, 0), "
        "constant. Joint 2 sits at the elbow, which joint 1 has carried to "
        "q₂ = (L₁c₁, L₁s₁, 0): J<sub>s2</sub> = (0, 0, 1, L₁s₁, −L₁c₁, 0), "
        "depending on θ₁ only. To get the tip velocity from a twist, add the "
        "spin times the tip's lever arm: v<sub>tip</sub> = v + ω × p<sub>tip</sub>. "
        "For column 2 that gives (L₁s₁ − x₂, −L₁c₁ + x₁) = (−L₂s₁₂, L₂c₁₂), "
        "exactly J₂ from video 5. Same column, now stored as a twist."))
    c.add(plain(
        "Three things to notice. (1) <b>No derivatives</b>: each column is a "
        "matrix product of things you already have. (2) J<sub>s1</sub> never "
        "changes, J<sub>s2</sub> depends only on θ₁, J<sub>s3</sub> only on "
        "θ₁ and θ₂, and so on: column i ignores joints i, i+1, …, n. "
        "(3) J<sub>s</sub> does not involve M or the hand frame at all; the "
        "twist V<sub>s</sub> is the hand's motion as seen at the {s} origin."))
    return c


def body_card() -> Card:
    c = Card("video 5.1.2 — the body Jacobian: the same story from the hand")
    c.add(video_tag(
        "5.1.2", "body Jacobian",
        "The hand twist in {b}, V_b = J_b θ̇. Mirror image of the space case: "
        "only joints between joint i and the hand can move joint i's axis "
        "relative to {b}."))
    c.add(link_back("124, VIDEO 5.1.1",
        "Same physical column as in J<sub>s</sub>: the hand's twist when only "
        "joint i turns. Only the observer changes. In {s} the question was "
        "'which joints can move axis i relative to the base?' (those before "
        "it). From the hand the question flips: 'which joints can move axis i "
        "relative to the hand?' (those after it, between axis i and the hand). "
        "Any column converts between the two with one adjoint: "
        "J<sub>bi</sub> = [Ad<sub>T<sub>bs</sub></sub>] J<sub>si</sub>. On the "
        "2R arm with {b} at the tip, the last column J<sub>b2</sub> is joint "
        "2's spin seen from the tip, 'lever arm L₂', and it never changes; "
        "J<sub>b1</sub> depends only on θ₂: the mirror of J<sub>s1</sub> "
        "constant and J<sub>s2</sub> depending only on θ₁."))
    c.add(in_words(
        "Stand on the hand. Joint i's axis looks like Bᵢ from there at home. "
        "Moving joints 1 … i does not change how joint i looks from the hand "
        "(they carry both the axis and the hand along together). Joints "
        "i+1 … n do change it, so column i is Bᵢ carried back through them."))
    c.add(math_label(r"\mathcal{V}_b=J_b(\theta)\dot\theta,\quad J_{bn}=\mathcal{B}_n,"
                     r"\quad J_{bi}=[\mathrm{Ad}_{e^{-[\mathcal{B}_n]\theta_n}\cdots"
                     r" e^{-[\mathcal{B}_{i+1}]\theta_{i+1}}}]\,\mathcal{B}_i", 15))
    c.add(body(
        "<b>Why the minus signs and the reversed order.</b> Call {b″} where "
        "the hand would be if joints i+1 … n were still at zero; in {b″} the "
        "axis is Bᵢ. The real hand is T<sub>b″b</sub> = e<sup>[B<sub>i+1</sub>]"
        "θ<sub>i+1</sub></sup> ⋯ e<sup>[Bₙ]θₙ</sup> away. We need the opposite "
        "direction, T<sub>bb″</sub> = T<sub>b″b</sub>⁻¹, and the inverse of a "
        "product is the product of inverses in reverse order: "
        "e<sup>−[Bₙ]θₙ</sup> ⋯ e<sup>−[B<sub>i+1</sub>]θ<sub>i+1</sub></sup>."))
    c.add(body(_block_html(
        "<b>space</b> J<sub>s</sub><br>first column fixed: J<sub>s1</sub> = S₁<br>"
        "column i uses θ₁ … θ<sub>i−1</sub><br>no hand frame needed",
        "<b>body</b> J<sub>b</sub><br>last column fixed: J<sub>bn</sub> = Bₙ<br>"
        "column i uses θ<sub>i+1</sub> … θₙ<br>no space frame needed",
        "each column is a twist, so whole Jacobians<br>change frame with the adjoint:",
        "J<sub>s</sub> = [Ad<sub>T<sub>sb</sub></sub>] J<sub>b</sub>,&nbsp;&nbsp; "
        "J<sub>b</sub> = [Ad<sub>T<sub>bs</sub></sub>] J<sub>s</sub>")))
    return c


def adjoint_jobs_card() -> Card:
    c = Card("one matrix, two jobs: the adjoint in a change of observer and in a Jacobian column")
    c.add(in_words(
        "[Ad<sub>T</sub>] shows up twice on this page with what look like two "
        "meanings. In one, nothing moves and only the observer changes. In "
        "the other, an axis really has been carried somewhere new by the "
        "joints before it, and we write it in {s} again. The algebra is the "
        "same because both are 'apply a rigid transform to a twist'."))
    c.add(body(_block_html(
        "<b>change of observer</b><br>V<sub>b</sub> = [Ad<sub>T<sub>bs</sub></sub>] V<sub>s</sub>",
        "<b>Jacobian column</b><br>J<sub>si</sub> = [Ad<sub>T<sub>i−1</sub></sub>] Sᵢ,&nbsp; "
        "T<sub>i−1</sub> = e<sup>[S₁]θ₁</sup>⋯e<sup>[S<sub>i−1</sub>]θ<sub>i−1</sub></sup>",
        "same motion, same screw;<br>only who reports it changes",
        "the axis has physically moved;<br>T<sub>i−1</sub> is that motion, written in {s}")))
    c.add(body(
        "<b>A whole Jacobian at once.</b> Each column is a twist, so the "
        "change-of-observer rule applies to all of them in one multiplication: "
        "J<sub>b</sub> = [Ad<sub>T<sub>bs</sub></sub>] J<sub>s</sub>, all 6 × n of it.<br>"
        "<b>Check on the 2R hand</b> (video 5's numbers: L = (1, 0.8), θ = (0°, 90°), "
        "θ̇ = (1, 1)). J<sub>s1</sub> = (0, 0, 1, 0, 0, 0) and J<sub>s2</sub> = "
        "(0, 0, 1, L₁s₁, −L₁c₁, 0) = (0, 0, 1, 0, −1, 0), so"))
    c.add(math_label(
        r"\mathcal{V}_s=J_s\dot\theta=(0,0,2,\ 0,-1,0):\quad"
        r"q=\frac{\omega\times v}{|\omega|^2}=(0.5,0,0),\quad h=0", 15))
    c.add(body(
        "The whole hand is spinning at 2 rad/s about a vertical line through "
        "(0.5, 0), with no slide: a plain hinge at this instant. The tip "
        "(1, 0.8) rides the cylinder of radius √(0.5² + 0.8²) = 0.943, so its "
        "speed is 0.943 × 2 = 1.887 = |(−1.6, 1.0)| ✓, tangent to that circle. "
        "Now change observer to a frame {b} at the tip with axes parallel to {s} "
        "(R = I, p = (1, 0.8, 0)): v<sub>b</sub> = v<sub>s</sub> − p × ω = "
        "(0, −1, 0) − (1.6, −2, 0) = (−1.6, 1, 0). The bottom half of the body "
        "twist is the tip velocity of video 5: the same screw, reported at the "
        "tip's cylinder instead of the origin's."))
    c.add(link_back("121", (
        "The 'cylinder for every point' and 'which way does Ad go' cards on page "
        "121 are the picture behind this: Ad<sub>T<sub>sb</sub></sub> goes "
        "b-numbers → s-numbers, the same direction as T<sub>sb</sub>.")))
    return c


def _jac_html(J, col, changed):
    """6 x n Jacobian; the chosen column tinted, changed entries in orange."""
    n = J.shape[1]
    head = "".join(
        f"<td style='padding:1px 8px; text-align:right; color:{COLS[j]}'>"
        f"<b>col {j+1}</b></td>" for j in range(n))
    rows = ""
    for r in range(6):
        cells = ""
        for j in range(n):
            bg = f"background:{theme.BG_RAISED};" if j == col else ""
            colr = theme.WARN if changed is not None and changed[r, j] else theme.TEXT
            wt = "font-weight:bold;" if changed is not None and changed[r, j] else ""
            cells += (f"<td style='padding:1px 8px; text-align:right; {bg} color:{colr}; "
                      f"{wt}'>{J[r, j] + 0.0:+.3f}</td>")
        lab = ("ωx", "ωy", "ωz", "vx", "vy", "vz")[r]
        rows += (f"<tr><td style='padding:1px 6px; color:{theme.TEXT_DIM}'>{lab}</td>"
                 f"{cells}</tr>")
    return (f"<table style='font-family:Consolas'><tr><td></td>{head}</tr>{rows}</table>")


class JacobianBuilderLab:
    """Live 6 x 5 Jacobian of a spatial 5R arm, with change tracking."""

    def __init__(self):
        c = self.card = Card("lab (3-D): build J column by column, and see which columns a joint can touch")
        c.add(in_words(
            "A 5-joint arm in 3-D with its full 6 × 5 Jacobian printed live. "
            "Move one slider at a time: the entries that just changed light up "
            "in orange. In space form, moving θₖ only changes the columns to "
            "its right; in body form only the columns to its left. The pink "
            "line is the chosen joint's axis right now, and the faint ghost "
            "arm is the pose in which that axis looks exactly as it did at home."))
        row = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems(["space Jacobian J_s (twist in {s})",
                            "body Jacobian J_b (twist in {b})"])
        self.col = QComboBox()
        self.col.addItems([f"look at column {i+1}" for i in range(5)])
        self.col.setCurrentIndex(2)
        row.addWidget(self.mode)
        row.addWidget(self.col)
        row.addStretch(1)
        c.add_layout(row)
        self.mode.currentIndexChanged.connect(self._reset_track)
        self.col.currentIndexChanged.connect(self._draw)
        self.q = [labelled_slider(c, f"θ{i+1}", -150, 150, v, deg, self._draw)
                  for i, v in enumerate(ARM5_HOME)]
        self.msg = body("")
        c.add(self.msg)
        self.txt = body("")
        c.add(self.txt)
        self.chk = body("")
        c.add(self.chk)
        self.cv = MplCanvas(width=7.6, height=5.2)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try, in order.</b> (1) Space form, column 3. Move θ₅, θ₄, θ₃: "
            "nothing in columns 1–3 turns orange. Move θ₂: column 3 changes. "
            "(2) Column 1 never changes at all: it is S₁, the waist axis. "
            "(3) Body form: now column 5 never changes (it is B₅), and moving "
            "θ₁ changes <i>nothing</i>: turning the waist carries the whole "
            "arm and hand together, so no axis moves relative to the hand. "
            "(4) The check line computes column i a second way, by nudging "
            "θᵢ and differentiating T(θ) numerically: the two agree, though "
            "the formula never took a derivative. It also checks "
            "J<sub>s</sub> = [Ad<sub>T<sub>sb</sub></sub>]J<sub>b</sub>."))
        self._prevJ = None
        self._prevq = None
        self._draw()

    def _reset_track(self, *_):
        self._prevJ = None
        self._draw()

    def _draw(self, *_):
        q = _rad(self.q)
        i = self.col.currentIndex()
        body_mode = self.mode.currentIndex() == 1
        Js = rk.jacobian_space(ARM5_S, q)
        Jb = rk.jacobian_body(ARM5_B, q)
        J = Jb if body_mode else Js
        T = rk.fk_space(ARM5_M, ARM5_S, q)
        changed = None
        if self._prevJ is not None and self._prevq is not None:
            changed = np.abs(J - self._prevJ) > 1e-9
            moved = [k for k in range(5) if abs(q[k] - self._prevq[k]) > 1e-12]
            if moved:
                cc = [j + 1 for j in range(5) if changed[:, j].any()]
                k = moved[0] + 1
                rule = (f"space form: θ{k} can only reach columns {k+1}…5"
                        if not body_mode else
                        f"body form: θ{k} can only reach columns 1…{k-1}")
                self.msg.setText(
                    f"<b>You moved θ{k}.</b> Columns that changed: "
                    f"<b style='color:{theme.WARN}'>{cc or 'none'}</b>. "
                    f"<span style='color:{theme.TEXT_DIM}'>({rule})</span>")
        else:
            self.msg.setText("<b>Move one slider</b> to see which columns it can change.")
        self._prevJ, self._prevq = J.copy(), q.copy()
        if body_mode:
            dep = ", ".join(f"θ{k+1}" for k in range(i + 1, 5)) or "nothing"
            f = (f"J<sub>b{i+1}</sub> = [Ad<sub>e<sup>−[B₅]θ₅</sup>⋯e<sup>−[B<sub>{i+2}</sub>]"
                 f"θ<sub>{i+2}</sub></sup></sub>] B<sub>{i+1}</sub>" if i < 4 else
                 "J<sub>b5</sub> = B₅")
        else:
            dep = ", ".join(f"θ{k+1}" for k in range(i)) or "nothing"
            f = (f"J<sub>s{i+1}</sub> = [Ad<sub>e<sup>[S₁]θ₁</sup>⋯e<sup>[S<sub>{i}</sub>]"
                 f"θ<sub>{i}</sub></sup></sub>] S<sub>{i+1}</sub>" if i > 0 else
                 "J<sub>s1</sub> = S₁")
        self.txt.setText(f"{f} — depends on <b>{dep}</b>" + _jac_html(J, i, changed))
        # numerical derivative of T along θ_i
        h = 1e-6
        dq = np.zeros(5)
        dq[i] = h
        Tp = rk.fk_space(ARM5_M, ARM5_S, q + dq)
        Tm = rk.fk_space(ARM5_M, ARM5_S, q - dq)
        Td = (Tp - Tm) / (2 * h)
        X = Td @ rk.inv_T(T) if not body_mode else rk.inv_T(T) @ Td
        Vnum = np.r_[rk.unskew(X[:3, :3]), X[:3, 3]]
        e_num = np.abs(Vnum - J[:, i]).max()
        e_ad = np.abs(Js - rk.adjoint(T) @ Jb).max()
        self.chk.setText(
            f"<span style='color:{theme.TEXT_DIM}'>check: column {i+1} from a "
            f"numerical derivative of T(θ) differs by {e_num:.1e} · "
            f"|J<sub>s</sub> − [Ad<sub>T<sub>sb</sub></sub>]J<sub>b</sub>| = {e_ad:.1e}</span>")
        # ---- picture ----
        _clear(self.cv)
        ax = self.cv.ax
        if body_mode:
            qg = q.copy()
            qg[:i + 1] = 0
            G = T @ rk.inv_T(rk.fk_space(ARM5_M, ARM5_S, qg))
            draw_arm5(ax, qg, color=theme.TEXT_DIM, alpha=0.35, lw=3, G=G)
        else:
            qg = np.r_[q[:i], np.zeros(5 - i)]
            draw_arm5(ax, qg, color=theme.TEXT_DIM, alpha=0.35, lw=3)
        pts = draw_arm5(ax, q)
        Ti = arm5_prefix(q, i)
        a = Ti[:3, :3] @ ARM5_W[i]
        p = pts[i + 1]
        ax.plot(*np.vstack([p - 1.2 * a, p + 1.2 * a]).T, "--", color=PINK, lw=2)
        _frame3d(ax, np.eye(3), (0, 0, 0), scale=0.5, name="s", lw=1.8)
        _frame3d(ax, T[:3, :3], T[:3, 3], scale=0.5, name="b", lw=2.2)
        if not body_mode and i > 0:
            _frame3d(ax, Ti[:3, :3], Ti[:3, 3], scale=0.6, name="s″", lw=1.4, ls=":")
        if body_mode and i < 4:
            Tpp = T @ rk.inv_T(rk.fk_body(np.eye(4), ARM5_B[:, i + 1:], q[i + 1:]))
            _frame3d(ax, Tpp[:3, :3], Tpp[:3, 3], scale=0.6, name="b″", lw=1.4, ls=":")
        _style_arm_axes(ax)
        ax.view_init(elev=22, azim=-58)
        ax.set_title(f"pink: joint {i+1} axis now · ghost: pose where it looks as at home",
                     color=theme.TEXT, fontsize=9)
        self.cv.refresh()


# ==========================================================================
# video 5.2 -- statics
# ==========================================================================

def statics_card() -> Card:
    c = Card("video 5.2 — statics of open chains: τ = Jᵀ F in any frame")
    c.add(video_tag(
        "5.2", "statics of open chains",
        "Someone grabs the hand mid-motion and pushes with a wrench −F. To "
        "stay on its planned path the robot must push back with F, which "
        "costs extra joint torque τ = JᵀF on top of the torque the motion "
        "already needed."))
    c.add(in_words(
        "The robot is following a trajectory and its motors already supply "
        "τ<sub>motion</sub>(t) (chapter 8 computes it). A disturbance wrench "
        "−F lands on the hand. To cancel it the motors must add the torques "
        "that make the hand apply F, so the command becomes τ<sub>motion</sub> "
        "+ JᵀF. Where JᵀF comes from: power at the hand must equal power at "
        "the motors."))
    c.add(math_label(r"\mathcal{F}_b^T\mathcal{V}_b=\tau^T\dot\theta,\quad"
                     r"\mathcal{V}_b=J_b\dot\theta\ \Rightarrow\ \mathcal{F}_b^TJ_b"
                     r"\dot\theta=\tau^T\dot\theta\ \ \forall\dot\theta\ \Rightarrow\ "
                     r"\tau=J_b^T\mathcal{F}_b", 15))
    c.add(body(
        "The same steps in {s} give τ = J<sub>s</sub>ᵀF<sub>s</sub>, and both "
        "give the same τ: it is one physical torque, written with two "
        "bookkeepings. A wrench F = (m, f) is a moment and a force, written "
        "in the same frame as the twist it pairs with, so mᵀω + fᵀv is "
        "power. Use: <b>force control</b>. To make the hand press on a "
        "table with wrench F, command τ = JᵀF (plus gravity "
        "compensation)."))
    c.add(plain(
        "<b>One joint at a time.</b> Joint i feels the hand moment m plus the "
        "force f times its lever arm, the perpendicular distance from joint i "
        "to the line along which f acts: τᵢ = m + (rᵢ × f)<sub>z</sub> in the "
        "plane. That is exactly row i of JᵀF. A joint whose lever arm is long "
        "works hard; a joint that sits on the force line feels no force at "
        "all."))
    return c


class StaticsLab:
    """Planar 3R pushed at the hand: τ from Jᵀ F, lever arms, power check."""

    L = (1.0, 0.8, 0.5)
    QDOT = np.array([0.3, -0.5, 0.8])

    def __init__(self):
        c = self.card = Card("lab: someone pushes the hand — what must each motor add?")
        c.add(in_words(
            "The grey dashed arrow is the push −F someone puts on the hand. "
            "The red arrow is F, what the robot must push back with to stay "
            "put. The thin lines are each joint's lever arm to the force line. "
            "The torques are computed three ways (space Jacobian, body "
            "Jacobian, lever arms) and must agree."))
        self.q = [labelled_slider(c, f"θ{i+1}", -180, 180, v, deg, self._draw)
                  for i, v in enumerate((40, -70, 50))]
        self.fa = labelled_slider(c, "direction of F", -180, 180, 110, deg, self._draw)
        self.fm = labelled_slider(c, "size of F (N)", 0, 40, 20, lambda v: f"{v} N", self._draw)
        self.mm = labelled_slider(c, "moment m at the hand (N·m)", -10, 10, 0,
                                  lambda v: f"{v:+d} N·m", self._draw)
        self.st = [Stat(f"τ{i+1} (N·m)", "--", col) for i, col in
                   enumerate((theme.BAD, theme.VIOLET, theme.PINK))]
        c.add_layout(stat_row(*self.st))
        self.txt = body("")
        c.add(self.txt)
        self.cv = MplCanvas(width=7.6, height=4.2)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Turn F until its line (dotted) passes through "
            "joint 2: τ₂ drops to 0, joint 2 has no lever arm. (2) Stretch the "
            "arm straight (θ₂ = θ₃ = 0) and point F along it: all three "
            "torques vanish; the links take the load in tension or "
            "compression. (3) Add a hand moment m: every joint gets the same "
            "+m on top, because a pure moment has no line of action. (4) The "
            "power line picks a joint speed θ̇ and shows τᵀθ̇ = F<sub>b</sub>ᵀ"
            "V<sub>b</sub>, the identity the whole result rests on."))
        self._draw()

    def _draw(self, *_):
        q = _rad(self.q)
        a = math.radians(self.fa.value())
        f2 = self.fm.value() * np.array([math.cos(a), math.sin(a)])
        m = float(self.mm.value())
        S, M = rk.planar_screws(list(self.L))
        T = rk.fk_space(M, S, q)
        Js = rk.jacobian_space(S, q)
        B = rk.adjoint(rk.inv_T(M)) @ S
        Jb = rk.jacobian_body(B, q)
        pts = rk.planar_points(self.L, q)
        tip = pts[-1]
        f3 = np.r_[f2, 0.0]
        Fs = np.r_[np.array([0, 0, m]) + np.cross(np.r_[tip, 0], f3), f3]
        Fb = rk.adjoint(T).T @ Fs
        tau_s = Js.T @ Fs
        tau_b = Jb.T @ Fb
        tau_g = np.array([m + _cross2(tip - pts[i], f2) for i in range(3)])
        for s, t in zip(self.st, tau_s):
            s.set(f"{t:+.2f}")
        Vb = Jb @ self.QDOT
        self.txt.setText(
            f"F<sub>s</sub> = {_vec_s(Fs)} &nbsp; F<sub>b</sub> = {_vec_s(Fb)}<br>"
            f"J<sub>s</sub>ᵀF<sub>s</sub> = {_vec_s(tau_s)} &nbsp; J<sub>b</sub>ᵀF<sub>b</sub> = "
            f"{_vec_s(tau_b)} &nbsp; lever arms = {_vec_s(tau_g)}<br>"
            f"<span style='color:{theme.TEXT_DIM}'>power check with θ̇ = "
            f"{_vec_s(self.QDOT, 1)}: τᵀθ̇ = {tau_s @ self.QDOT:+.3f}, "
            f"F<sub>b</sub>ᵀV<sub>b</sub> = {Fb @ Vb:+.3f}</span>")
        c = self.cv
        c.clear()
        ax = c.ax
        draw_arm(ax, self.L, q)
        fn = np.linalg.norm(f2)
        if fn > 1e-9:
            u = f2 / fn
            line = np.vstack([tip - 4 * u, tip + 4 * u])
            ax.plot(*line.T, ":", color=theme.BAD, lw=1)
            for i, col in enumerate((theme.BAD, theme.VIOLET, theme.PINK)):
                r = pts[i] - tip
                foot = tip + (r @ u) * u
                ax.plot(*np.vstack([pts[i], foot]).T, "-", color=col, lw=1.3)
                ax.text(*(0.5 * (pts[i] + foot)), f"r{i+1}", color=col, fontsize=8)
            _arrow(ax, tip, f2 / 25, theme.BAD, lw=2.4)
            _arrow(ax, tip + 2 * f2 / 25, -f2 / 25, theme.TEXT_DIM, lw=1.6, ls="--")
            ax.text(*(tip + f2 / 25 * 1.15), "F", color=theme.BAD)
            ax.text(*(tip + 2.1 * f2 / 25), "−F (push)", color=theme.TEXT_DIM, fontsize=8)
        if abs(m) > 0:
            t = np.linspace(0, 1.5 * math.pi, 40) * (1 if m > 0 else -1)
            arc = tip + 0.25 * np.vstack([np.cos(t), np.sin(t)]).T
            ax.plot(*arc.T, color=theme.WARN, lw=1.6)
            ax.text(*(tip + [0.3, 0.3]), f"m = {m:+.0f}", color=theme.WARN, fontsize=8)
        square(ax, 2.6)
        ax.set_title("τᵢ = m + (force) × (perpendicular distance from joint i to its line)")
        c.refresh()


# ==========================================================================
# video 5.3 -- singularities and the shape of J
# ==========================================================================

def singularity_card() -> Card:
    c = Card("video 5.3 — singularities: rank, and tall, square or fat Jacobians")
    c.add(video_tag(
        "5.3", "singularities",
        "J is 6 × n, so its rank is at most min(6, n). Full rank means it hits "
        "that bound. A singular pose is one where the rank drops below the "
        "best the arm ever achieves: the hand loses a direction."))
    c.add(in_words(
        "Rank = how many independent directions the hand can move in right "
        "now. The shape of J says how many joints you have compared with how "
        "many directions you need; the rank says how many of those "
        "directions survive at this pose."))
    c.add(body(_block_html(
        "<b>tall</b>, n &lt; 6 (e.g. 6 × 4 RRRP)<br><b>kinematically deficient</b>: "
        "the hand can never do general 6-D motion; still useful for tasks "
        "that need less",
        "<b>square</b>, n = 6 (6R)<br><b>general purpose</b>: any twist, "
        "unless singular",
        "<b>fat</b>, n &gt; 6 (6 × 7 for a 7R)<br><b>redundant</b>: many θ̇ give "
        "the same hand twist; the arm can move inside while the hand stays "
        "still, like your elbow with your hand on a table",
        "<b>singular</b>: rank below its maximum<br>J θ̇ = V has no solution for "
        "some V; Jᵀ has forces the joints never feel")))
    c.add(body(
        "<b>Asking the questions backwards.</b> Forward is always easy: "
        "v = Jθ̇ and τ = Jᵀf always have an answer. Backward is not: given v, "
        "find θ̇ needs J⁻¹, which does not exist for a non-square or singular "
        "J. A redundant arm has a whole line (more generally a family) of θ̇ "
        "for each v; chapter 6 picks one. Given τ, find f needs (Jᵀ)⁻¹; for a "
        "redundant arm most torque choices do not hold the arm still against "
        "a hand force, they make it move internally."))
    c.add(plain(
        "<b>At a singularity, forces and velocities trade places.</b> The "
        "stretched planar arm can only move its tip sideways to the arm. A "
        "force along the arm passes through every joint, so it needs no "
        "torque: the structure carries it passively. Directions the hand "
        "cannot move are exactly the directions it can resist for free. The "
        "planar labs use tip position only, so J is 2 × n and 'full rank' "
        "means rank 2 (rank 1 for a 1R)."))
    return c


class SingularityLab:
    """Planar 1R / 2R / 3R: shape, rank, null spaces, self-motion, passive forces."""

    ARMS = {"1R — 2 × 1, tall (deficient)": (1.8,),
            "2R — 2 × 2, square": (1.0, 0.8),
            "3R — 2 × 3, fat (redundant)": (1.0, 0.8, 0.5)}

    def __init__(self):
        c = self.card = Card("lab: 1R, 2R, 3R — what a singular or redundant arm can and cannot do")
        c.add(in_words(
            "Pick an arm and a pose. The arrows at the tip are the columns of "
            "J (tip velocity from each joint alone). The red force is applied "
            "at the tip, and the readout gives the torque each joint needs. For "
            "the 3R, the self-motion slider moves the joints along the null "
            "space of J: the arm folds and unfolds while the tip stays fixed."))
        self.arm = QComboBox()
        self.arm.addItems(list(self.ARMS))
        self.arm.setCurrentIndex(2)
        self.arm.currentIndexChanged.connect(self._arm_changed)
        c.add(self.arm)
        self.q = [labelled_slider(c, f"θ{i+1}", -180, 180, v, deg, self._draw)
                  for i, v in enumerate((30, 50, -40))]
        self.fa = labelled_slider(c, "tip force direction", -180, 180, 0, deg, self._draw)
        self.sm = labelled_slider(c, "self-motion along null(J) (3R only)", -100, 100, 0,
                                  lambda v: f"{v/100:+.2f}", self._draw)
        row = QHBoxLayout()
        b1 = QPushButton("Stretch straight")
        b1.clicked.connect(self._straight)
        b2 = QPushButton("Force along the arm")
        b2.clicked.connect(self._along)
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch(1)
        c.add_layout(row)
        self.st_shape = Stat("shape of J", "--", theme.CYAN)
        self.st_rank = Stat("rank / max", "--", theme.WARN)
        self.st_tau = Stat("τ = Jᵀf (unit f)", "--", theme.ACCENT)
        c.add_layout(stat_row(self.st_shape, self.st_rank, self.st_tau))
        self.txt = body("")
        c.add(self.txt)
        self.cv = MplCanvas(width=7.6, height=4.2)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) 3R: drag self-motion. The tip stays on the cross "
            "while the elbow swings: those joint speeds are in null(J) and the "
            "hand never sees them. (2) <b>Stretch straight</b>: every column "
            "points the same way (perpendicular to the arm), rank falls to 1, "
            "and null(Jᵀ) appears. (3) Then <b>force along the arm</b>: τ is "
            "zero at every joint; the structure resists it. Turn the force 90° "
            "and all joints have to work. (4) 2R: same story, but no "
            "self-motion: a square J has an empty null space unless singular. "
            "(5) 1R: rank is always 1. It is never singular, just deficient: "
            "it can only move the tip around a circle."))
        self._arm_changed()

    def _L(self):
        return self.ARMS[self.arm.currentText()]

    def _arm_changed(self, *_):
        n = len(self._L())
        for k, s in enumerate(self.q):
            s.setEnabled(k < n)
        self.sm.setEnabled(n == 3)
        if n != 3:
            self.sm.blockSignals(True)
            self.sm.setValue(0)
            self.sm.blockSignals(False)
        self._draw()

    def _straight(self):
        for s in self.q[1:]:
            s.blockSignals(True)
            s.setValue(0)
            s.blockSignals(False)
        self.sm.blockSignals(True)
        self.sm.setValue(0)
        self.sm.blockSignals(False)
        self._draw()

    def _along(self):
        L = self._L()
        q = self._pose()
        pts = rk.planar_points(L, q)
        d = pts[-1] - pts[-2]
        self.fa.setValue(int(round(math.degrees(math.atan2(d[1], d[0])))))

    def _pose(self):
        L = self._L()
        n = len(L)
        q = _rad(self.q)[:n]
        s = self.sm.value() / 100
        if n == 3 and abs(s) > 0:
            p0 = rk.planar_points(L, q)[-1]
            steps = int(abs(s) * 60) + 1
            h = 1.6 * s / steps
            prev = None
            for _ in range(steps):
                J = rk.planar_jacobian(L, q)
                nv = np.linalg.svd(J)[2][-1]
                if prev is not None and nv @ prev < 0:
                    nv = -nv
                prev = nv
                q = q + h * nv
                J = rk.planar_jacobian(L, q)
                q = q + np.linalg.pinv(J) @ (p0 - rk.planar_points(L, q)[-1])
        return q

    def _draw(self, *_):
        L = self._L()
        n = len(L)
        q = self._pose()
        J = rk.planar_jacobian(L, q)
        a = math.radians(self.fa.value())
        f = np.array([math.cos(a), math.sin(a)])
        tau = J.T @ f
        r = _rank(J, 1e-4)
        rmax = min(2, n)
        shape = {1: "2 × 1 tall", 2: "2 × 2 square", 3: "2 × 3 fat"}[n]
        self.st_shape.set(shape)
        self.st_rank.set(f"{r} / {rmax}" + ("  SINGULAR" if r < rmax else ""))
        self.st_rank.set_color(theme.BAD if r < rmax else theme.WARN)
        self.st_tau.set(_vec_s(tau))
        U, s, Vt = np.linalg.svd(J)
        sv = np.zeros(2)
        sv[:len(s)] = s
        nullJ = [Vt[k] for k in range(n) if k >= len(s) or s[k] < 1e-4]
        nullJT = [U[:, k] for k in range(2) if sv[k] < 1e-4]
        word = {1: "kinematically deficient for 2-D tip motion",
                2: "exactly as many joints as tip directions",
                3: "redundant: one spare joint"}[n]
        self.txt.setText(
            "J =" + mat_html(J) +
            f"<b>{word}</b>. σ = {_vec_s(sv, 3)}.<br>"
            f"null(J), joint speeds the tip cannot see: "
            f"{', '.join(_vec_s(v) for v in nullJ) or 'none'}<br>"
            f"null(Jᵀ), tip forces the joints never feel: "
            f"{', '.join(_vec_s(v) for v in nullJT) or 'none'}")
        c = self.cv
        c.clear()
        ax = c.ax
        if n == 3 and self.sm.value() != 0:
            draw_arm(ax, L, _rad(self.q)[:n], ghost=True)
        pts = draw_arm(ax, L, q)
        tip = pts[-1]
        ax.plot(*tip, "+", color=theme.WARN, ms=16, mew=1.5)
        for i in range(n):
            _arrow(ax, tip, 0.4 * J[:, i], COLS[i], lw=2)
        _arrow(ax, tip, 0.5 * f, theme.BAD, lw=1.4, ls="--")
        line = np.vstack([tip - 4 * f, tip + 4 * f])
        ax.plot(*line.T, ":", color=theme.BAD, lw=0.8)
        for k, v in enumerate(nullJT):
            _arrow(ax, tip, 0.7 * v, theme.GOOD, lw=1.4)
            ax.text(*(tip + 0.8 * v), "free-force dir.", color=theme.GOOD, fontsize=8)
        square(ax, 2.6)
        ax.set_title("solid arrows: columns of J (×0.4); dashed red: unit tip force")
        c.refresh()


# ==========================================================================
# video 5.4 -- manipulability
# ==========================================================================

def manip_card() -> Card:
    c = Card("video 5.4 — manipulability: how close to singular?")
    c.add(video_tag(
        "5.4", "manipulability",
        "A pose is singular or not, but a pose can be nearly singular. The "
        "unit sphere of joint speeds maps to an ellipsoid of hand speeds; how "
        "squashed that ellipsoid is measures how close you are."))
    c.add(in_words(
        "Feed in every joint-speed vector of length 1. The hand speeds you get "
        "fill an ellipsoid. Its long axes are easy directions, its short axes "
        "hard ones. When an axis shrinks to zero the arm is singular. Turn "
        "the shape into one number and you can watch it, plot it, or have a "
        "planner keep it away from trouble."))
    c.add(math_label(r"\dot\theta^T\dot\theta=1,\ \dot\theta=J^{-1}v\ \Rightarrow\ "
                     r"v^T(JJ^T)^{-1}v=1,\qquad A=JJ^T", 16))
    c.add(body(
        "A = JJᵀ is symmetric and positive definite (when J has full row "
        "rank), so xᵀA⁻¹x = 1 is an ellipsoid. <b>Its axes point along the "
        "eigenvectors of A, and its half-lengths are √λᵢ.</b> (J⁻¹ was used "
        "only to make the algebra short; the result holds for any full-rank "
        "J.) Use A⁻¹ = (JJᵀ)⁻¹ instead and the same recipe gives the "
        "<b>force ellipsoid</b> for a unit sphere of joint torques: the same "
        "axes, with half-lengths 1/√λᵢ."))
    c.add(body(_block_html(
        "<b>μ₁ = √(λ<sub>max</sub>/λ<sub>min</sub>)</b><br>longest ÷ shortest axis; "
        "≥ 1; = 1 means <b>isotropic</b> (a sphere)",
        "<b>μ₂ = λ<sub>max</sub>/λ<sub>min</sub> = μ₁²</b><br>the condition "
        "number of A",
        "<b>μ₃ = √(λ₁λ₂⋯) = √det A</b><br>proportional to the ellipsoid's "
        "volume",
        "near a singularity μ₁, μ₂ → ∞ and μ₃ → 0;<br>a large velocity "
        "ellipsoid means a small force one")))
    c.add(plain(
        "<b>Do not mix units.</b> The 6 × n body Jacobian has angular rows "
        "(rad/s) and linear rows (m/s). An ellipsoid that mixes them depends "
        "on whether you measure in metres or millimetres. So split it: "
        "J<sub>bω</sub> (top 3 rows) gives the angular-velocity and moment "
        "ellipsoids, J<sub>bv</sub> (bottom 3 rows) the linear-velocity and "
        "force ellipsoids. The 3-D lab below draws both."))
    return c


def manip_measures(J):
    lam = np.linalg.eigvalsh(J @ J.T)
    lam = np.clip(lam, 0, None)
    lmin, lmax = lam[0], lam[-1]
    mu1 = math.sqrt(lmax / lmin) if lmin > 1e-12 else math.inf
    return lam, mu1, mu1 ** 2, math.sqrt(float(np.prod(lam)))


class ManipulabilityLab:
    """2R: eigen-axes of J Jᵀ, unit-circle samples, measures vs θ₂, sweep."""

    L = (1.0, 0.8)

    def __init__(self):
        c = self.card = Card("lab: squash the ellipse, watch the three measures")
        c.add(in_words(
            "Each dot is J θ̇ for one joint-speed vector on the unit circle; "
            "the dots land exactly on the ellipse. Its axes are the "
            "eigenvectors of A = JJᵀ, labelled with their half-lengths √λ. The "
            "orange curve is the force ellipse, same axes, reciprocal lengths. "
            "Right: the three measures for every elbow angle."))
        self.q1 = labelled_slider(c, "θ₁", -180, 180, 20, deg, self._draw)
        self.q2 = labelled_slider(c, "θ₂ (elbow)", -180, 180, 90, deg, self._draw)
        row = QHBoxLayout()
        self.btn = QPushButton("Sweep the elbow from 90° to 0°")
        self.btn.clicked.connect(self._sweep)
        self.chk = QCheckBox("show force ellipse")
        self.chk.setChecked(True)
        self.chk.stateChanged.connect(self._draw)
        row.addWidget(self.btn)
        row.addWidget(self.chk)
        row.addStretch(1)
        c.add_layout(row)
        self.st_l = Stat("√λ₁, √λ₂ (half-axes)", "--", theme.GOOD)
        self.st_m1 = Stat("μ₁ = axis ratio", "--", theme.CYAN)
        self.st_m2 = Stat("μ₂ = condition no.", "--", theme.VIOLET)
        self.st_m3 = Stat("μ₃ = √det A", "--", theme.ACCENT)
        c.add_layout(stat_row(self.st_l, self.st_m1, self.st_m2, self.st_m3))
        self.cv = MplCanvas(width=7.6, height=3.9, ncols=2)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Press <b>Sweep</b>: the ellipse thins into a "
            "line while μ₁ and μ₂ shoot up and μ₃ falls to zero. The force "
            "ellipse does the opposite and grows without bound along the arm. "
            "(2) Find the elbow angle where μ₁ is smallest (the right plot's "
            "dip). For L = (1.0, 0.8) it is near 135°. That is the most "
            "isotropic pose this arm has. (3) Move θ₁: nothing on the right "
            "changes. The shape only depends on the elbow, the whole ellipse "
            "just turns with the arm."))
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self._draw()

    def _sweep(self):
        self.q2.setValue(90)
        self.timer.start(40)

    def _tick(self):
        v = self.q2.value()
        if v <= 0:
            self.timer.stop()
            return
        self.q2.setValue(v - 2)

    def _draw(self, *_):
        q = np.radians([self.q1.value(), self.q2.value()])
        J = rk.planar_jacobian(self.L, q)
        A = J @ J.T
        lam, vec = np.linalg.eigh(A)
        lam = np.clip(lam, 0, None)
        _, mu1, mu2, mu3 = manip_measures(J)
        fmt = lambda x: "∞" if math.isinf(x) else f"{x:.2f}"
        self.st_l.set(f"{math.sqrt(lam[1]):.2f}, {math.sqrt(lam[0]):.2f}")
        self.st_m1.set(fmt(mu1))
        self.st_m2.set(fmt(mu2))
        self.st_m3.set(f"{mu3:.3f}")
        c = self.cv
        c.clear()
        a1, a2 = c.axes
        pts = draw_arm(a1, self.L, q)
        tip = pts[-1]
        k = 0.6
        t = np.linspace(0, 2 * math.pi, 100)
        E = (vec @ np.diag(np.sqrt(lam)) @ np.vstack([np.cos(t), np.sin(t)])).T
        a1.plot(*(tip + k * E).T, color=theme.GOOD, lw=2, label="velocity ellipse")
        ts = np.linspace(0, 2 * math.pi, 24, endpoint=False)
        D = (J @ np.vstack([np.cos(ts), np.sin(ts)])).T
        a1.plot(*(tip + k * D).T, "o", color=theme.CYAN, ms=3, label="J θ̇ for ‖θ̇‖ = 1")
        for j in range(2):
            d = k * math.sqrt(lam[j]) * vec[:, j]
            a1.plot(*np.vstack([tip - d, tip + d]).T, "-", color=theme.GOOD, lw=0.8)
            a1.text(*(tip + 1.1 * d), f"√λ{2-j}={math.sqrt(lam[j]):.2f}",
                    color=theme.GOOD, fontsize=7)
        if self.chk.isChecked() and lam[0] > 1e-6:
            sf = 0.35
            Fe = (vec @ np.diag(1 / np.sqrt(lam)) @ np.vstack([np.cos(t), np.sin(t)])).T
            Fe = np.clip(Fe, -12, 12)
            a1.plot(*(tip + sf * Fe).T, color=theme.WARN, lw=1.5, label="force ellipse")
        square(a1, 2.2)
        c.legend(a1, loc="lower left")
        a1.set_title("A = JJᵀ: axes = eigenvectors, half-lengths √λ")
        th2 = np.radians(np.linspace(2, 178, 177))
        ms = np.array([manip_measures(rk.planar_jacobian(self.L, [0, b]))[1:] for b in th2])
        a2.semilogy(np.degrees(th2), ms[:, 0], color=theme.CYAN, label="μ₁")
        a2.semilogy(np.degrees(th2), ms[:, 1], color=theme.VIOLET, label="μ₂")
        a2.semilogy(np.degrees(th2), ms[:, 2], color=theme.ACCENT, label="μ₃")
        a2.axvline(abs(self.q2.value()), color=theme.WARN, ls=":", lw=1.2)
        a2.set_xlabel("|θ₂| (deg)")
        a2.set_title("measures vs elbow angle (log scale)")
        c.legend(a2, loc="upper center")
        c.refresh()


class EllipsoidLab:
    """The 5R arm in 3-D: linear and angular ellipsoids from J_bv and J_bω."""

    def __init__(self):
        c = self.card = Card("lab (3-D): split J_b into angular and linear, draw both ellipsoids")
        c.add(in_words(
            "The 5-joint arm again. Its 6 × 5 body Jacobian is split in two. "
            "The bottom three rows J<sub>bv</sub> give the ellipsoid of hand "
            "speeds (left, drawn at the hand). The top three rows "
            "J<sub>bω</sub> give the ellipsoid of hand spin rates (right). "
            "Each comes with its own measures, in its own units."))
        self.q = [labelled_slider(c, f"θ{i+1}", -150, 150, v, deg, self._draw)
                  for i, v in enumerate(ARM5_HOME)]
        self.force = QCheckBox("draw force / moment ellipsoids instead (A⁻¹)")
        self.force.stateChanged.connect(self._draw)
        c.add(self.force)
        self.st_v = Stat("linear: μ₁ · μ₃", "--", theme.GOOD)
        self.st_w = Stat("angular: μ₁ · μ₃", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_v, self.st_w))
        self.cv = MplCanvas(width=7.6, height=4.6)
        _layout(self.cv, ["3d", "3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Set θ₃ = 0 (elbow straight): the linear ellipsoid "
            "goes flat along the forearm and μ₁ jumps. (2) Put θ₃ back and "
            "move only θ₄ or θ₅: the angular ellipsoid turns and changes "
            "shape while the linear one barely moves, because the wrist joints "
            "sit close to the hand. The two halves of J describe different "
            "abilities. (3) Whatever the pose, the angular ellipsoid has one "
            "half-axis of exactly √3 ≈ 1.73: joints 2, 3 and 4 all spin the hand "
            "about the same pitch axis, so their unit rates add up along it. "
            "(4) Tick the force box: the "
            "ellipsoids invert; the flat direction becomes the strong one."))
        self._draw()

    @staticmethod
    def _ellipsoid(ax, A, centre, col, scale, inverse):
        lam, vec = np.linalg.eigh(A)
        lam = np.clip(lam, 1e-9, None)
        r = 1 / np.sqrt(lam) if inverse else np.sqrt(lam)
        if inverse:
            r = np.clip(r, 0, 8)
        u, v = np.meshgrid(np.linspace(0, 2 * math.pi, 20), np.linspace(0, math.pi, 11))
        S = np.stack([np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), np.cos(v)])
        P = np.einsum("ij,jkl->ikl", vec @ np.diag(scale * r), S)
        ax.plot_wireframe(P[0] + centre[0], P[1] + centre[1], P[2] + centre[2],
                          color=col, lw=0.6, alpha=0.8)
        for j in range(3):
            d = scale * r[j] * vec[:, j]
            ax.plot(*np.vstack([centre - d, centre + d]).T, color=col, lw=1.4)

    def _draw(self, *_):
        q = _rad(self.q)
        T = rk.fk_space(ARM5_M, ARM5_S, q)
        R = T[:3, :3]
        Jb = rk.jacobian_body(ARM5_B, q)
        Jw, Jv = R @ Jb[:3], R @ Jb[3:]      # rotate to {s} axes for drawing
        inv = self.force.isChecked()
        fmt = lambda x: "∞" if math.isinf(x) else f"{x:.2f}"
        _, a1, _, a3 = manip_measures(Jv)
        _, b1, _, b3 = manip_measures(Jw)
        self.st_v.set(f"{fmt(a1)} · {a3:.3f}")
        self.st_w.set(f"{fmt(b1)} · {b3:.3f}")
        _clear(self.cv)
        ax, bx = self.cv.axes
        draw_arm5(ax, q)
        _frame3d(ax, R, T[:3, 3], scale=0.4, name="b", lw=2)
        self._ellipsoid(ax, Jv @ Jv.T, T[:3, 3], theme.GOOD, 0.12 if inv else 0.35, inv)
        _style_arm_axes(ax)
        ax.view_init(elev=22, azim=-58)
        ax.set_title("linear: J_bv (m/s) " + ("→ force" if inv else "velocity"),
                     color=theme.TEXT, fontsize=9)
        self._ellipsoid(bx, Jw @ Jw.T, np.zeros(3), theme.VIOLET, 0.25 if inv else 0.5, inv)
        _frame3d(bx, R, (0, 0, 0), scale=1.0, name="b", lw=1.6)
        for s in ("x", "y", "z"):
            getattr(bx, f"set_{s}lim")(-1.6, 1.6)
        bx.set_box_aspect((1, 1, 1))
        bx.view_init(elev=22, azim=-58)
        bx.set_title("angular: J_bω (rad/s) " + ("→ moment" if inv else "velocity"),
                     color=theme.TEXT, fontsize=9)
        self.cv.refresh()
