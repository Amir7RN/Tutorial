"""
Page 123 extras -- the three Chapter 4 videos worked one by one.

    4.1.1  PoE in the space frame   planar RPR, axes read with the turntable
    4.1.2  PoE in the body frame    same RPR, axes read from the hand
    4      worked example           RRRP (SCARA-type) arm, axes by inspection

Each video gets a video_tag(), a WHAT IS GOING ON box, the numbers from the
video, and a lab where the numbers can be checked against a drawing.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QComboBox

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, body, math_label
from .robo_common import deg, labelled_slider, mat_html, plain
from .robo_space_rigid import (
    PINK,
    _block_html,
    _frame2d,
    _frame3d,
    _square2d,
    _vec,
    in_words,
    video_tag,
)
from .robo_space_topo import _clear, _layout


def _screw_table(rows, head=("joint", "screw axis (ω | v)", "how to read it")) -> str:
    """Rows of (joint, 6-vector, reason) as an HTML table."""
    cell = f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}'"
    mono = (f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}; "
            f"font-family:Consolas; color:{PINK}'")
    h = "".join(f"<th {cell} align='left'>{x}</th>" for x in head)
    r = "".join(
        f"<tr><td {cell}>{j}</td><td {mono}>{_vec(S[:3], 0)} | {_vec(S[3:], 0)}"
        f"</td><td {cell}>{why}</td></tr>" for j, S, why in rows)
    return f"<table style='border-collapse:collapse'><tr>{h}</tr>{r}</table>"


# ==========================================================================
# the planar RPR robot of videos 4.1.1 and 4.1.2
# ==========================================================================
# Joint 1 turns about z at the origin, joint 2 slides along the arm, joint 3
# turns about z two units out, and the hand {b} sits one unit past joint 3.
# At home everything lies on the x_s-axis, so M is a pure shift of 3 in x.

RPR_M = rk.rp_to_T(np.eye(3), [3.0, 0, 0])
RPR_S = np.array([[0, 0, 1, 0, 0, 0],
                  [0, 0, 0, 1, 0, 0],
                  [0, 0, 1, 0, -2, 0]], float).T
RPR_B = np.array([[0, 0, 1, 0, 3, 0],
                  [0, 0, 0, 1, 0, 0],
                  [0, 0, 1, 0, 1, 0]], float).T


def rpr_points(q):
    """Joint 1, joint 3 and hand positions in the plane, from plain trig."""
    t1, d, t3 = q
    j3 = (2 + d) * np.array([math.cos(t1), math.sin(t1)])
    hand = j3 + np.array([math.cos(t1 + t3), math.sin(t1 + t3)])
    return np.array([[0.0, 0.0], j3, hand])


def space_card() -> Card:
    c = Card("video 4.1.1 — product of exponentials in the space frame")
    c.add(video_tag(
        "4.1.1", "PoE in the space frame",
        "A planar RPR arm (turn, slide, turn). Find the hand's home pose M, "
        "read each joint's screw axis in {s}, then move the joints one at a "
        "time, last joint first, and pile the exponentials on the left of M."))
    c.add(in_words(
        "Forward kinematics asks: the joints read θ, where is the hand frame "
        "{b} as seen from the fixed frame {s}? The answer is the 4×4 matrix "
        "T(θ) = T<sub>sb</sub>(θ). The trick is to never look at a bent arm. "
        "Start straight (home), and every time you move one joint, describe "
        "that move as a screw motion written in {s}."))
    c.add(body(
        "<b>The robot.</b> θ₁ is the angle of joint 1 from horizontal, θ₂ is "
        "how far the slider is pulled out, θ₃ the angle of joint 3. At home "
        "(all zero) joint 1 is at the origin, joint 3 is 2 units out, the hand "
        "is 3 units out, and {b} points the same way as {s}:"))
    c.add(body("M = T(0) =" + mat_html(RPR_M, 0)))
    c.add(body(
        "<b>The turntable picture for v.</b> To read the linear part of a "
        "screw axis, imagine all of space bolted to a turntable spinning about "
        "that joint at 1 rad/s (or, for a slider, all of space sliding at 1 "
        "unit/s). v is the velocity of whatever point is passing through the "
        "{s} origin right now. The formula −ω̂ × q (q any point on the axis) "
        "gives the same thing."))
    c.add(body(_block_html(
        "<b>step 1</b>: θ = (0, 0, π/4)<br>T = e<sup>[S₃]π/4</sup> M",
        "<b>step 2</b>: θ = (0, 0.5, π/4)<br>T = e<sup>[S₂]0.5</sup> e<sup>[S₃]π/4</sup> M",
        "<b>step 3</b>: θ = (π/6, 0.5, π/4)<br>T = e<sup>[S₁]π/6</sup> e<sup>[S₂]0.5</sup>"
        " e<sup>[S₃]π/4</sup> M",
        "each new move is a <b>space-frame</b> motion,<br>so it multiplies on the "
        "<b>left</b>")))
    c.add(body(_screw_table([
        ("3 (revolute)", RPR_S[:, 2],
         "turns about +z out of the screen, so ω̂ = (0,0,1). The axis is 2 units "
         "along x, so the turntable carries the origin downward: v = (0,−2,0)."),
        ("2 (prismatic)", RPR_S[:, 1],
         "no rotation, so ω = 0 and v must be a unit vector: the slide "
         "direction (1,0,0)."),
        ("1 (revolute)", RPR_S[:, 0],
         "turns about +z through the origin; the origin does not move, "
         "so v = 0."),
    ])))
    c.add(plain(
        "<b>Why S₂ is still the home axis after joint 3 has moved.</b> Joint 3 "
        "sits beyond joint 2 (further from the base), so turning it cannot "
        "move joint 2's slide. Only joints between a joint and {s} can move "
        "its axis. Moving the joints from the tip inward means every joint "
        "you move next still has all the joints between it and the base at "
        "home. That is why you only ever need axes at home.<br>"
        "<b>The recipe for any serial arm.</b> (1) Write M. (2) Write "
        "S₁ … Sₙ in {s} with the arm at home. (3) T(θ) = e<sup>[S₁]θ₁</sup> ⋯ "
        "e<sup>[Sₙ]θₙ</sup> M."))
    return c


def body_card() -> Card:
    c = Card("video 4.1.2 — product of exponentials in the end-effector frame")
    c.add(video_tag(
        "4.1.2", "PoE in the body frame",
        "Same RPR arm, same M. Now each screw axis is written in the hand "
        "frame {b}, the joints are moved first joint first, and each "
        "exponential goes on the right of M."))
    c.add(in_words(
        "Same robot, same final pose, different bookkeeping. Stand on the hand "
        "instead of on the floor. Each joint's axis is now read as 'what does "
        "this joint look like from {b} at home', and each motion is a "
        "body-frame motion, so it multiplies on the right."))
    c.add(math_label(r"T(\theta)=M\,e^{[\mathcal{B}_1]\theta_1}"
                     r"e^{[\mathcal{B}_2]\theta_2}e^{[\mathcal{B}_3]\theta_3}", 15))
    c.add(body(_screw_table([
        ("1 (revolute)", RPR_B[:, 0],
         "axis along z<sub>b</sub>; joint 1 is 3 units behind the hand, so the "
         "turntable sweeps the {b} origin along +y<sub>b</sub>: v = (0,3,0)."),
        ("2 (prismatic)", RPR_B[:, 1],
         "slides along x<sub>b</sub>: v = (1,0,0), ω = 0."),
        ("3 (revolute)", RPR_B[:, 2],
         "axis along z<sub>b</sub>, 1 unit behind the hand: v = (0,1,0)."),
    ])))
    c.add(body(
        "Joint 1 moves first now. Is B₂ still the home value afterwards? Yes: "
        "joint 1 is not between joint 2 and {b}, so it cannot change how "
        "joint 2 looks from the hand. Same argument as before, mirrored.",
        dim=True))
    c.add(body(_block_html(
        "<b>space form</b><br>axes S<sub>i</sub> written in {s}<br>"
        "M on the <b>right</b>: e<sup>[S₁]θ₁</sup>⋯e<sup>[Sₙ]θₙ</sup>M<br>"
        "picture: move joint n first, then n−1, … 1",
        "<b>body form</b><br>axes B<sub>i</sub> written in {b}<br>"
        "M on the <b>left</b>: Me<sup>[B₁]θ₁</sup>⋯e<sup>[Bₙ]θₙ</sup><br>"
        "picture: move joint 1 first, then 2, … n",
        "same joint, two descriptions:<br>B<sub>i</sub> = [Ad<sub>M⁻¹</sub>]S<sub>i</sub>",
        "same answer: both products give<br>the same T(θ) for every θ")))
    c.add(plain(
        "Only two things change between the formulas: which frame the screw "
        "axes are written in, and which side M sits on. Check B₃ with the "
        "adjoint: M only shifts by 3 in x, so v<sub>b</sub> = v<sub>s</sub> + "
        "p × ω with p = (−3,0,0): (0,−2,0) + (0,3,0) = (0,1,0). The lab below "
        "computes both products and shows they agree."))
    return c


class RPRLab:
    """Step through the space or body product on the RPR arm."""

    MODES = ("space form: left-multiply, joints 3 → 2 → 1",
             "body form: right-multiply, joints 1 → 2 → 3")

    def __init__(self):
        c = self.card = Card("lab: RPR arm, watch the product build up")
        c.add(in_words(
            "Set the three joints. The coloured ghosts are the partial "
            "products: in space form you first see only θ₃ applied, then θ₂ "
            "and θ₃, then all three. In body form the order flips. Every "
            "partial product is itself a real pose of the arm, and both "
            "orders end in the same place."))
        self.mode = QComboBox()
        self.mode.addItems(self.MODES)
        self.mode.currentIndexChanged.connect(self._draw)
        c.add(self.mode)
        self.s1 = labelled_slider(c, "θ₁ (joint 1)", -180, 180, 30, deg, self._draw)
        self.s2 = labelled_slider(c, "θ₂ (slide)", 0, 150, 50,
                                  lambda v: f"{v/100:.2f}", self._draw)
        self.s3 = labelled_slider(c, "θ₃ (joint 3)", -180, 180, 45, deg, self._draw)
        self.txt = body("")
        c.add(self.txt)
        self.cv = MplCanvas(width=7.4, height=4.0)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Set the video's numbers: θ₁ = 30°, θ₂ = 0.50, "
            "θ₃ = 45°. (2) In space form, look at stage 1: only joint 3 has "
            "turned, about the pink dot at (2,0), which is where S₃ said the "
            "axis is. (3) Switch to body form: stage 1 is now joint 1 alone. "
            "(4) The two T matrices in the readout are equal to every printed "
            "digit; the 'difference' line shows it."))
        self._draw()

    def q(self):
        return np.array([math.radians(self.s1.value()), self.s2.value() / 100,
                         math.radians(self.s3.value())])

    def _draw(self, *_):
        q = self.q()
        Ts = rk.fk_space(RPR_M, RPR_S, q)
        Tb = rk.fk_body(RPR_M, RPR_B, q)
        body_mode = self.mode.currentIndex() == 1
        if body_mode:
            stages = [np.r_[q[:k], np.zeros(3 - k)] for k in (1, 2, 3)]
            names = ("M e^[B1]θ1", "… e^[B2]θ2", "… e^[B3]θ3")
            T, other = Tb, "space"
        else:
            stages = [np.r_[np.zeros(3 - k), q[3 - k:]] for k in (1, 2, 3)]
            names = ("e^[S3]θ3 M", "e^[S2]θ2 …", "e^[S1]θ1 …")
            T, other = Ts, "body"
        err = np.abs(Ts - Tb).max()
        self.txt.setText(
            "T(θ) =" + mat_html(T) +
            f"<span style='color:{theme.TEXT_DIM}'>hand at ({T[0,3]:.3f}, "
            f"{T[1,3]:.3f}), angle {math.degrees(math.atan2(T[1,0], T[0,0])):.1f}° "
            f"(θ₁+θ₃ = {math.degrees(q[0] + q[2]):.1f}°) · difference from the "
            f"{other} form: {err:.1e}</span>")
        ax = self.cv.ax
        self.cv.clear()
        home = rpr_points(np.zeros(3))
        ax.plot(home[:, 0], home[:, 1], "-", color=theme.TEXT_DIM, lw=1.5, alpha=0.4)
        ax.plot([0, 2], [0, 0], "o", color=PINK, ms=8, alpha=0.6)
        ax.annotate("", xy=(1.6, -0.35), xytext=(0.6, -0.35),
                    arrowprops=dict(arrowstyle="-|>", color=PINK, alpha=0.6))
        ax.text(0.05, -0.65, "home axes: S₁ at 0, S₂ slide, S₃ at 2",
                color=PINK, fontsize=8)
        for k, (qq, col, nm) in enumerate(zip(stages, (theme.VIOLET, theme.ACCENT,
                                                       theme.CYAN), names)):
            p = rpr_points(qq)
            ax.plot(p[:, 0], p[:, 1], "-", color=col, lw=2 + 1.5 * k,
                    alpha=0.35 + 0.3 * k, solid_capstyle="round",
                    label=f"stage {k+1}: {nm}")
            ax.plot(p[:2, 0], p[:2, 1], "o", color=theme.WARN, ms=5,
                    alpha=0.35 + 0.3 * k)
        _frame2d(ax, np.eye(4), scale=0.6, name="{s}")
        _frame2d(ax, T, scale=0.6, name="{b}")
        _square2d(ax, (-4, 4), (-4, 4))
        self.cv.legend(ax, loc="lower left")
        ax.set_title("grey = home (M); stages = partial products; last stage = T(θ)")
        self.cv.refresh()


# ==========================================================================
# video 4 -- the RRRP worked example
# ==========================================================================
# Joints 1-3 turn about vertical axes at x = 0, 10, 19; joint 4 slides
# vertically. At home {b} sits at (19, 0, -3) with x_b = -y_s, y_b = -x_s,
# z_b = -z_s (the tool points down).

RRRP_M = rk.rp_to_T(np.array([[0, -1, 0], [-1, 0, 0], [0, 0, -1.0]]), [19, 0, -3])
RRRP_S = np.array([[0, 0, 1, 0, 0, 0],
                   [0, 0, 1, 0, -10, 0],
                   [0, 0, 1, 0, -19, 0],
                   [0, 0, 0, 0, 0, 1]], float).T
RRRP_B = np.array([[0, 0, -1, -19, 0, 0],
                   [0, 0, -1, -9, 0, 0],
                   [0, 0, -1, 0, 0, 0],
                   [0, 0, 0, 0, 0, -1]], float).T
RRRP_JOINTS = np.array([[0, 0, 0], [10, 0, 0], [19, 0, 0]], float)


def rrrp_card() -> Card:
    c = Card("video 4 — worked example: the RRRP assembly arm")
    c.add(video_tag(
        "4", "forward kinematics example",
        "A four-joint arm used for assembly: three vertical hinges and a "
        "vertical slide. Write M from the drawing, then every S and B by "
        "looking, with no algebra."))
    c.add(in_words(
        "This is the whole chapter on one real robot. The drawing at home "
        "gives you everything: M from where the tool frame sits and which "
        "way its axes point, and each screw axis from where its hinge is. "
        "The video's point is that for most arms you can do this by "
        "inspection."))
    c.add(body(
        "<b>M, orientation.</b> Read each {b} axis as an {s} direction: "
        "x<sub>b</sub> = −y<sub>s</sub>, y<sub>b</sub> = −x<sub>s</sub>, "
        "z<sub>b</sub> = −z<sub>s</sub> (tool points down). Those three "
        "vectors are the columns of R. <b>M, position.</b> {b} is 19 units "
        "along x<sub>s</sub> and 3 units down. Add the bottom row 0 0 0 1:"))
    c.add(body("M =" + mat_html(RRRP_M, 0)))
    c.add(body(_screw_table([
        ("S₁", RRRP_S[:, 0], "hinge on z<sub>s</sub> through the origin: "
         "the origin does not move."),
        ("S₂", RRRP_S[:, 1], "vertical hinge 10 out along x: spinning it "
         "sweeps the origin at 10 along −y<sub>s</sub>."),
        ("S₃", RRRP_S[:, 2], "vertical hinge 19 out: a large velocity at "
         "the {s} origin, 19 along −y<sub>s</sub>."),
        ("S₄", RRRP_S[:, 3], "slide along z<sub>s</sub>: ω = 0, v is the "
         "unit slide direction."),
    ], head=("space", "S (ω | v)", "read off the drawing"))))
    c.add(body(_screw_table([
        ("B₁", RRRP_B[:, 0], "z<sub>s</sub> is −z<sub>b</sub>; the hinge is "
         "19 behind the tool, so the tool origin moves 19 along −x<sub>b</sub>."),
        ("B₂", RRRP_B[:, 1], "same direction; 9 behind the tool: 9 along "
         "−x<sub>b</sub>."),
        ("B₃", RRRP_B[:, 2], "the hinge passes through the {b} origin: zero "
         "linear velocity there."),
        ("B₄", RRRP_B[:, 3], "the slide is along −z<sub>b</sub>."),
    ], head=("body", "B (ω | v)", "read off the drawing"))))
    c.add(plain(
        "<b>The pattern.</b> Joint 3 has a big v in {s} and zero v in {b}; "
        "joint 1 is the other way round. v is just 'how fast the origin "
        "you chose is carried by this hinge', so it is large when the hinge "
        "is far from that origin and zero when the hinge passes through it. "
        "A prismatic joint has no hinge: ω = 0 and v is the slide direction "
        "in whichever frame you write. Stuck? Check any row with "
        "B = [Ad<sub>M⁻¹</sub>]S, or with v = −ω̂ × q."))
    return c


class RRRPLab:
    """3-D view of the RRRP arm, joints placed by partial PoE products."""

    def __init__(self):
        c = self.card = Card("lab (3-D): RRRP arm, space and body product side by side")
        c.add(in_words(
            "Drag the joints. Each joint's position is found the PoE way: "
            "its home position, moved by the exponentials of the joints "
            "before it. The tool frame comes from e<sup>[S₁]θ₁</sup>⋯"
            "e<sup>[S₄]θ₄</sup>M, and the readout checks it against "
            "Me<sup>[B₁]θ₁</sup>⋯e<sup>[B₄]θ₄</sup>."))
        self.s = [labelled_slider(c, f"θ{i+1}", -150, 150, v, deg, self._draw)
                  for i, v in enumerate((30, -60, 45))]
        self.s.append(labelled_slider(c, "θ4 (slide, + is up along z_s)", -40, 30, -10,
                                      lambda v: f"{v/10:+.1f}", self._draw))
        self.txt = body("")
        c.add(self.txt)
        self.cv = MplCanvas(width=7.6, height=4.6)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Set every slider to 0: the tool sits at "
            "(19, 0, −3) with its z pointing down, as in M. (2) Move only θ₃: "
            "the tool frame spins in place, because joint 3's axis goes "
            "through the {b} origin (B₃ has v = 0). (3) Move only θ₁: the "
            "whole arm swings about the base, and the tool traces a circle of "
            "radius 19, the 19 in B₁. (4) Move θ₄: the tool slides straight "
            "up or down whatever the hinges do, because a slide along z<sub>s</sub> "
            "is untouched by turns about vertical axes."))
        self._draw()

    def q(self):
        return np.array([math.radians(s.value()) for s in self.s[:3]]
                        + [self.s[3].value() / 10])

    def _draw(self, *_):
        q = self.q()
        T = rk.fk_space(RRRP_M, RRRP_S, q)
        err = np.abs(T - rk.fk_body(RRRP_M, RRRP_B, q)).max()
        self.txt.setText(
            "T(θ) =" + mat_html(T, 2) +
            f"<span style='color:{theme.TEXT_DIM}'>tool at {_vec(T[:3, 3])} · "
            f"space vs body difference {err:.1e}</span>")
        pts = []
        for i, p in enumerate(RRRP_JOINTS):
            Ti = rk.fk_space(np.eye(4), RRRP_S[:, :i], q[:i])
            pts.append(Ti[:3, :3] @ p + Ti[:3, 3])
        pts = np.array(pts)
        _clear(self.cv)
        ax = self.cv.ax
        home = np.vstack([RRRP_JOINTS, RRRP_M[:3, 3]])
        ax.plot(*home.T, "-", color=theme.TEXT_DIM, lw=1.2, alpha=0.4)
        for p in pts[:3]:
            ax.plot([p[0]] * 2, [p[1]] * 2, [-5, 3], "--", color=PINK, lw=1.2,
                    alpha=0.8)
        tool = T[:3, 3]
        arm = np.vstack([[0, 0, -5], pts[:3], tool])
        ax.plot(*arm[:2].T, "-", color=theme.TEXT_DIM, lw=5, alpha=0.8)
        ax.plot(*arm[1:4].T, "-", color=theme.CYAN, lw=5, solid_capstyle="round")
        ax.plot(*np.vstack([pts[2], tool]).T, "-", color=theme.ACCENT, lw=3)
        ax.plot(*pts[:3].T, "o", color=theme.WARN, ms=7)
        _frame3d(ax, np.eye(3), (0, 0, 0), scale=5, name="s", lw=2)
        _frame3d(ax, T[:3, :3], tool, scale=5, name="b", lw=2.4)
        for s in ("x", "y"):
            getattr(ax, f"set_{s}lim")(-21, 21)
        ax.set_zlim(-7, 5)
        ax.set_box_aspect((1, 1, 0.45), zoom=1.5)
        ax.view_init(elev=28, azim=-60)
        ax.set_title("pink dashed = joint axes (all vertical)  ·  grey = home",
                     color=theme.TEXT, fontsize=9)
        self.cv.refresh()
