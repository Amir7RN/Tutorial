"""
Interactive cards for Modern Robotics chapter 3, one group per video, in the
order the videos play. Page 118 (RotationsPage) takes videos 3.1-3.2.1,
page 119 (AngularVelocityPage) 3.2.2-3.2.3, page 120 (TwistsPage) the
rigid-body ones:

    3.1    intro: frames, right-hand rule     bridge_card, intro_card, FrameHandCard
    3.2.1  rotation matrices (1 of 2)         RotationMatrixCard, count_card,
                                              so3_card, SO3BallCard, CommuteCard
    3.2.1  rotation matrices (2 of 2)         SubscriptCard, RotateOperatorCard
    3.2.2  angular velocities                 check_card, why_rdot_card,
                                              ConstraintMatrixCard, tangent_card,
                                              GimbalRatesCard, axis_speed_card,
                                              ComponentsCard, layers_card,
                                              AngularVelocityCard, body_space_card,
                                              BodySpaceCard
    3.2.3  exponential coordinates (1 of 2)   ExpSeriesCard
    3.2.3  exponential coordinates (2 of 2)   IntegrateCard, AxisAngleCard
    3.3.1  homogeneous transformations        transform_card, HomogeneousCard,
                                              LeftRightCard
    3.3.2  twists (1 of 2)                    twist_card, TurntableCard
    3.3.2  twists (2 of 2)                    adjoint_card
    3.3.3  exponential coordinates of motion  analogy_card, ScrewCard,
                                              ScrewTwoFramesCard
    3.4    wrenches                           wrench_card, AppleCard

Every group opens with a video_tag() and most cards carry a link_back() box
that says which word from pages 115-117 the new idea is a new name for.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QCheckBox, QComboBox

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, callout, math_label, stat_row
from .robo_common import deg, labelled_slider, mat_html, plain
from .robo_space_topo import _clear, _grid_table, _layout

AX_COLS = (theme.BAD, theme.GOOD, theme.ACCENT)   # x red, y green, z blue


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def video_tag(code: str, title: str, text: str):
    """Marks where one video starts: what it covers, in one breath."""
    return callout(text, "key", label=f"VIDEO {code} — {title.upper()}")


def link_back(pages: str, text: str):
    """Says which word from pages 115-117 the new idea renames."""
    return callout(text, "warn", label=f"CONNECTS TO PAGE {pages}")


def rotz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def roty(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1.0, 0], [-s, 0, c]])


def rotx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0, 0], [0, c, -s], [0, s, c]])


def _unit(az, el):
    """Unit vector from azimuth and elevation, both in radians."""
    return np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az),
                     math.sin(el)])


def _vec(v, prec=2) -> str:
    return "(" + ", ".join(f"{x + 0.0:.{prec}f}" for x in v) + ")"


def _cols_html(R, prec=2) -> str:
    """A 3x3 matrix whose columns are coloured like the x, y, z axes."""
    R = np.round(np.asarray(R, float), 9) + 0.0    # no "-0.00"
    rows = "".join(
        "<tr>" + "".join(
            f"<td style='padding:1px 9px; text-align:right; color:{AX_COLS[j]}'>"
            f"{R[i, j]:+.{prec}f}</td>" for j in range(3)) + "</tr>"
        for i in range(3))
    return f"<table style='font-family:Consolas'>{rows}</table>"


def _block_html(top_left, top_right, bot_left, bot_right) -> str:
    """A 2x2 block matrix drawn with words, for formulas mathtext cannot draw."""
    cell = ("style='padding:4px 14px; border:1px solid " + theme.BORDER +
            "; text-align:center; font-family:Consolas'")
    return (f"<table style='border-collapse:collapse'><tr><td {cell}>{top_left}</td>"
            f"<td {cell}>{top_right}</td></tr><tr><td {cell}>{bot_left}</td>"
            f"<td {cell}>{bot_right}</td></tr></table>")


def _frame3d(ax, R, p=(0, 0, 0), scale=1.0, alpha=1.0, lw=2.6, name=None, ls="-"):
    p = np.asarray(p, float)
    for i in range(3):
        e = p + scale * R[:, i]
        ax.plot([p[0], e[0]], [p[1], e[1]], [p[2], e[2]], color=AX_COLS[i],
                lw=lw, alpha=alpha, ls=ls)
        if name and alpha > 0.5:
            ax.text(*(p + 1.12 * scale * R[:, i]), f"{'xyz'[i]}{name}",
                    color=AX_COLS[i], fontsize=8)


def _cube(ax, r=1.1):
    for s in ("x", "y", "z"):
        getattr(ax, f"set_{s}lim")(-r, r)
    ax.set_box_aspect((1, 1, 1))


def _frame2d(ax, T, scale=0.6, alpha=1.0, name=None, lw=2.4):
    """Top view of a frame: x red, y green, from the 4x4 (or 3x3 planar) T."""
    o = T[:2, -1]
    for i in range(2):
        d = scale * T[:2, i]
        ax.annotate("", xy=o + d, xytext=o,
                    arrowprops=dict(arrowstyle="-|>", color=AX_COLS[i], lw=lw,
                                    alpha=alpha))
    if name:
        ax.text(o[0] - 0.25, o[1] - 0.3, name, color=theme.TEXT, fontsize=9,
                alpha=alpha)


def _square2d(ax, xl, yl):
    ax.set_xlim(*xl)
    ax.set_ylim(*yl)
    ax.set_aspect("equal", adjustable="box")


# The three frames of video 3.2.1 part 2: {b} is {s} turned +90 deg about
# z_s; {c} is {b} turned -90 deg about its own y-axis.
R_SB = rotz(math.pi / 2)
R_BC = roty(-math.pi / 2)
R_SC = R_SB @ R_BC


# ==========================================================================
# 3.1  introduction
# ==========================================================================

def bridge_card() -> Card:
    """Chapter 3's words, each next to the page 115-117 word it renames."""
    c = Card("dictionary: chapter 3's new words in the language of pages 115–117")
    c.add(body(
        "Chapter 3 sounds like a new subject, but almost every word in it is a "
        "new name for something you already met on the C-space pages. Keep "
        "this table open while you watch; every card below ends with a box "
        "that points back to the row it uses."))
    c.add(body(_grid_table(
        ("chapter 3 says…", "you met it on page…", "as…"),
        [("the configuration of a rigid body",
          "115",
          "a point in C-space; a body in space has <b>6 DOF</b> (m = 6 in "
          "Grübler): 3 for where it is, 3 for which way it points"),
         ("SO(3), the space of orientations",
          "115, 116",
          "the orientation piece of that C-space: 3-D, but <b>curved and "
          "closed like a sphere</b>, not the flat ℝ³ (topology)"),
         ("rotation matrix R (9 numbers)",
          "116",
          "an <b>implicit representation</b>: more numbers than DOF, tied "
          "together by rules, so it has no bad spots"),
         ("RᵀR = I",
          "117",
          "the rules: <b>6 holonomic constraints</b> g(R) = 0 that trap the "
          "9 numbers on a 3-D surface"),
         ("det R = +1",
          "116, 117",
          "picking one of two <b>disconnected pieces</b>, like choosing the "
          "four-bar's assembly mode"),
         ("angular velocity ω is not the derivative of three angles",
          "116, 117",
          "'velocity ≠ coordinate rate'; differentiating RᵀR = I gives a "
          "<b>Pfaffian velocity constraint</b>, and its null space (3-D) is "
          "where ω lives"),
         ("exponential coordinates ω̂θ (3 numbers)",
          "116",
          "an <b>explicit</b> chart: three numbers, fine almost everywhere, "
          "awkward at θ = 180°"),
         ("T ∈ SE(3), twists, screw axes",
          "115",
          "the full 6-D C-space of a body, R plus position, and its 6-D "
          "velocities"),
         ("wrench, power VᵀF",
          "117",
          "the force side: a constraint force Aᵀλ is a wrench that does "
          "no work, because A q̇ = 0")])))
    c.add(plain(
        "If one row stays foggy, that is fine: the card that uses it repeats "
        "the link in its orange box. The single most important row is the "
        "fourth one. RᵀR = I is the same kind of object as the hoop rule "
        "x² + y² − 1 = 0 on page 117: a violation meter that must read zero. "
        "Everything about angular velocity follows from differentiating it, "
        "exactly as A(q)q̇ = 0 followed from g(q) = 0."))
    return c


def intro_card() -> Card:
    c = Card("what chapter 3 is going to do, sentence by sentence")
    c.add(body(
        "<b>1. 'Representations of configurations, velocities and forces.'</b> "
        "Three things to write down for a rigid body: where it is and which "
        "way it points (configuration), how fast that is changing "
        "(velocity), and what pushes on it (force). Every later chapter "
        "uses these three, so they are chosen with care.<br>"
        "<b>2. 'Implicit representations, the C-space as a surface in a "
        "higher-dimensional space.'</b> This is page 116's choice, made for "
        "you. Orientation has 3 DOF but will be stored as 9 numbers (a "
        "matrix) that must obey rules. The 9 numbers form a 9-D space; the "
        "rules carve out a 3-D surface inside it; real orientations live "
        "only on that surface. Same picture as the bead: 2 numbers (x, y), "
        "1 rule, a 1-D hoop.<br>"
        "<b>3. 'Not a minimum set of coordinates, and velocities are not "
        "time derivatives of coordinates.'</b> Because the 9 numbers are not "
        "independent, 'the velocity' will not be 'the rate of each number'. "
        "It will be a separate 3-vector ω that is <i>not</i> d/dt of any "
        "three numbers. Page 116 warned about this in the 'velocity ≠ "
        "coordinate rate' row; here it becomes the rule.<br>"
        "<b>4. Frames.</b> A frame is an origin plus three unit axes x, y, z "
        "at right angles. To describe a body, glue a frame {b} to it, fix a "
        "frame {s} in space, and describe {b} as seen from {s}: where its "
        "origin is and where its three axes point.<br>"
        "<b>5. Right-handed only.</b> x × y = z. Index finger x, middle "
        "finger y, thumb z. A mirror-image frame would flip one axis and is "
        "never used.<br>"
        "<b>6. Frames are stationary.</b> When the body moves, '{b}' means "
        "the fixed frame that coincides with the body frame <i>at this "
        "instant</i>. It is a snapshot. That is what lets us say 'the "
        "velocity expressed in {b}' without the frame moving under us.<br>"
        "<b>7. Positive rotation by the right-hand rule.</b> Thumb along the "
        "axis, fingers curl the positive way. Every sign in the chapter "
        "comes from this."))
    c.add(link_back("116", (
        "Page 116 ended with: 'plain angles for joints, wrapped; a rotation "
        "matrix for anything that can point in any 3-D direction'. Chapter 3 "
        "is the second half of that sentence worked out in full. Joint "
        "angles q stay explicit; the hand's orientation becomes implicit.")))
    return c


class FrameHandCard:
    """Right-handed vs mirror frames, and which way 'positive' turns."""

    def __init__(self):
        c = self.card = Card("lab: build a frame with your right hand, then turn it")
        c.add(body(
            "Choose where x points. y is then x turned 90° (the slider "
            "'y around x' picks which of the many perpendicular directions). "
            "A right-handed frame takes z = x × y; tick the box to build the "
            "mirror frame z = −x × y instead and watch the determinant flip. "
            "The last slider turns the whole frame about its own z-axis by "
            "the right-hand rule.", dim=True))
        self.s_az = labelled_slider(c, "x-axis azimuth", -180, 180, 20, deg, self._draw)
        self.s_el = labelled_slider(c, "x-axis elevation", -80, 80, 15, deg, self._draw)
        self.s_roll = labelled_slider(c, "y around x", -180, 180, 0, deg, self._draw)
        self.s_turn = labelled_slider(c, "positive turn about own z", -180, 180, 60, deg,
                                      self._draw)
        self.chk = QCheckBox("build the mirror (left-handed) frame instead")
        self.chk.toggled.connect(self._draw)
        c.add(self.chk)
        self.st_det = Stat("det [x y z]", "--", theme.GOOD)
        self.st_cross = Stat("x × y equals z?", "--", theme.ACCENT)
        c.add_layout(stat_row(self.st_det, self.st_cross))
        self.cv = MplCanvas(width=7.4, height=3.6)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try:</b> leave the box empty and check that the readout says "
            "x × y = z and det = +1 wherever you point x. Tick the box: the "
            "blue axis flips, det becomes −1, and no turning of the sliders "
            "will bring it back. A mirror frame cannot be rotated into a "
            "right-handed one; they are two separate pieces. That is the "
            "det = ±1 split of the next video. Then drag 'positive turn': "
            "with your right thumb along the blue axis, your fingers curl the "
            "way the red and green axes sweep."))
        self._draw()

    def _draw(self, *_):
        x = _unit(math.radians(self.s_az.value()), math.radians(self.s_el.value()))
        helper = np.array([0, 0, 1.0]) if abs(x[2]) < 0.95 else np.array([1.0, 0, 0])
        y0 = np.cross(helper, x)
        y0 /= np.linalg.norm(y0)
        y = rk.rot_exp(x * math.radians(self.s_roll.value())) @ y0
        mirror = self.chk.isChecked()
        z = -np.cross(x, y) if mirror else np.cross(x, y)
        F0 = np.column_stack([x, y, z])
        th = math.radians(self.s_turn.value())
        F = rk.rot_exp(z * th) @ F0
        self.st_det.set(f"{np.linalg.det(F):+.0f}")
        self.st_cross.set("no — mirror" if mirror else "yes")
        _clear(self.cv)
        ax = self.cv.ax
        _frame3d(ax, np.eye(3), scale=0.9, alpha=0.18, lw=1.4)
        _frame3d(ax, F0, scale=0.9, alpha=0.3, lw=1.4, ls="--")
        _frame3d(ax, F, scale=1.0, name="", lw=3)
        arc = np.array([rk.rot_exp(z * t) @ (0.55 * x) for t in np.linspace(0, th, 40)])
        ax.plot(arc[:, 0], arc[:, 1], arc[:, 2], color=theme.WARN, lw=1.5)
        ax.plot([0, 1.25 * z[0]], [0, 1.25 * z[1]], [0, 1.25 * z[2]], ":",
                color=theme.ACCENT, lw=1)
        _cube(ax)
        ax.set_title("dashed: before the turn   bold: after   orange: the sweep")
        self.cv.refresh()


# ==========================================================================
# 3.2.1  rotation matrices, part 1
# ==========================================================================

class RotationMatrixCard:
    """R_sb's columns are {b}'s axes; the six rules as a live violation meter."""

    def __init__(self):
        c = self.card = Card("R_sb: write {b}'s three axes in {s} numbers, side by side")
        c.add(body(
            "Ignore position for now and look only at which way {b} points. "
            "Take {b}'s x-axis, write it as three numbers in {s} coordinates, "
            "and make that column 1. Do the same for y<sub>b</sub> (column 2) "
            "and z<sub>b</sub> (column 3). The video's example is {b} turned "
            "90° about z<sub>s</sub>: x<sub>b</sub> points along +y<sub>s</sub> "
            "= (0, 1, 0), y<sub>b</sub> along −x<sub>s</sub> = (−1, 0, 0), "
            "z<sub>b</sub> = z<sub>s</sub> = (0, 0, 1). Stack them: that is "
            "R<sub>sb</sub>. <b>Subscripts:</b> the second one (b) is the "
            "frame being described, the first one (s) is the frame doing the "
            "describing. 'b as seen from s'."))
        c.add(math_label(
            r"R_{sb}=\left[\,\hat x_b\ \ \hat y_b\ \ \hat z_b\,\right]_{\mathrm{in}\ \{s\}},"
            r"\qquad R^TR=I\ \ (6\ \mathrm{rules}),\qquad \det R=+1", 15))
        c.add(body(
            "The sliders below turn {b}. They are only knobs for building a "
            "frame (turn about z<sub>s</sub>, then about the new y, then the "
            "new x); the thing to watch is the matrix. The default is the "
            "video's example. The last slider <b>breaks</b> the matrix on "
            "purpose by adding ε to its top-left entry.", dim=True))
        self.s_y = labelled_slider(c, "turn about z", -180, 180, 90, deg, self._draw)
        self.s_p = labelled_slider(c, "then about new y", -90, 90, 0, deg, self._draw)
        self.s_r = labelled_slider(c, "then about new x", -180, 180, 0, deg, self._draw)
        self.s_eps = labelled_slider(c, "corrupt R₁₁ by ε", -50, 50, 0,
                                     lambda v: f"{v/100:+.2f}", self._draw)
        self.R_txt = body("")
        c.add(self.R_txt)
        self.st_len = Stat("lengths ‖x‖, ‖y‖, ‖z‖", "--", theme.GOOD)
        self.st_dot = Stat("x·y, y·z, z·x", "--", theme.ACCENT)
        self.st_det = Stat("det R", "--", theme.VIOLET)
        self.st_g = Stat("violation ‖RᵀR − I‖", "--", theme.BAD)
        c.add_layout(stat_row(self.st_len, self.st_dot, self.st_det, self.st_g))
        self.cv = MplCanvas(width=7.4, height=3.6)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Read the columns, not the rows.</b> Red column = where "
            "{b}'s red axis points in {s}; green = green; blue = blue. "
            "<b>Try:</b> set the turn about z to 0: R becomes I, because "
            "{b} and {s} agree. Set it back to 90° and read off (0, 1, 0), "
            "(−1, 0, 0), (0, 0, 1), the video's numbers. Turn the other "
            "sliders: the numbers change, but the four stats do not — every "
            "length stays 1, every dot product 0, det +1, violation 0. "
            "<b>Now move ε.</b> Only one of nine numbers changed, yet the x "
            "column is no longer unit length, the violation meter lights up, "
            "and the drawn x-axis stretches. 9 numbers of which only 3 are "
            "free: change one alone and you leave the surface."))
        c.add(link_back("117", (
            "‖RᵀR − I‖ is page 117's violation meter g, built the same way: "
            "zero when the rule holds, growing the farther you are from it. "
            "RᵀR is symmetric, so only its 6 upper entries are separate "
            "rules: 3 say 'each column has length 1', 3 say 'each pair of "
            "columns is at right angles'. ε is a 'nudge one coordinate "
            "alone' experiment, and like the bead nudged off the hoop it "
            "breaks the rule. Real rotations move several entries at once, "
            "in the ratio that keeps the meter at zero.")))
        self._draw()

    def _draw(self, *_):
        R = (rotz(math.radians(self.s_y.value())) @ roty(math.radians(self.s_p.value()))
             @ rotx(math.radians(self.s_r.value())))
        R = R.copy()
        R[0, 0] += self.s_eps.value() / 100
        self.R_txt.setText("R<sub>sb</sub> = " + _cols_html(R))
        n = np.linalg.norm(R, axis=0)
        d = (R[:, 0] @ R[:, 1], R[:, 1] @ R[:, 2], R[:, 2] @ R[:, 0])
        self.st_len.set(", ".join(f"{x:.2f}" for x in n))
        self.st_dot.set(", ".join(f"{x + 0.0:.2f}" for x in d))
        self.st_det.set(f"{np.linalg.det(R):+.3f}")
        self.st_g.set(f"{np.linalg.norm(R.T @ R - np.eye(3)):.3f}")
        _clear(self.cv)
        ax = self.cv.ax
        _frame3d(ax, np.eye(3), alpha=0.25, lw=1.4)
        for i, nm in enumerate(("x_s", "y_s", "z_s")):
            ax.text(*(1.1 * np.eye(3)[:, i]), nm, color=theme.TEXT_FAINT, fontsize=7)
        _frame3d(ax, R, name="_b", lw=3)
        _cube(ax, 1.2)
        ax.set_title("faint: {s}     bold: {b}, drawn from the columns of R")
        self.cv.refresh()


def count_card() -> Card:
    c = Card("9 numbers − 6 rules = 3 freedoms, and the properties that follow")
    c.add(body(
        "<b>The count.</b> Orientation has 3 DOF, R has 9 entries, so the "
        "entries must obey 9 − 3 = 6 independent rules: three unit lengths "
        "and three right angles. Written compactly, RᵀR = I. (Entry (i, j) of "
        "RᵀR is column i · column j, so 'equals I' says 1 on the diagonal, 0 "
        "off it.)<br>"
        "<b>The sign.</b> Those 6 rules allow det R = +1 or −1. +1 are "
        "right-handed frames, −1 mirror frames. We keep only +1. The set of "
        "all 3×3 real matrices with RᵀR = I and det R = +1 is the "
        "<b>special orthogonal group SO(3)</b>: 'orthogonal' for RᵀR = I, "
        "'special' for det = +1."))
    c.add(math_label(
        r"SO(3)=\{R\in\mathbb{R}^{3\times3}:\ R^TR=I,\ \det R=1\}", 16))
    c.add(body(_grid_table(
        ("property", "in symbols", "why it is true, in one line", "what you use it for"),
        [("inverse = transpose", "R⁻¹ = Rᵀ ∈ SO(3)",
          "RᵀR = I is literally the definition of an inverse",
          "undoing a rotation costs nothing: no matrix inversion, ever"),
         ("closed under products", "R₁R₂ ∈ SO(3)",
          "(R₁R₂)ᵀ(R₁R₂) = R₂ᵀ(R₁ᵀR₁)R₂ = I, and det multiplies: 1 · 1",
          "chain frames: s→b→c gives another rotation"),
         ("associative", "(R₁R₂)R₃ = R₁(R₂R₃)",
          "true of all matrix products",
          "group long chains in any order you like"),
         ("not commutative", "R₁R₂ ≠ R₂R₁ in general",
          "turning about x then z ends somewhere other than z then x",
          "the ORDER of joints and of multiplications matters (next lab)"),
         ("keeps lengths", "‖Rx‖ = ‖x‖",
          "‖Rx‖² = xᵀRᵀRx = xᵀx",
          "rotating a vector never stretches it")])))
    c.add(link_back("115, 116, 117", (
        "<b>115:</b> 'numbers − independent rules = DOF' is the same "
        "book-keeping as Grübler (freedoms of the bodies − constraints of "
        "the joints): 9 − 6 = 3. <b>117:</b> RᵀR = I are 6 holonomic "
        "constraints g(R) = 0. They shrink the 9-D space of all 3×3 "
        "matrices to a 3-D surface, just as the hoop shrank the 2-D plane to "
        "a 1-D circle. <b>116:</b> the surface comes in two pieces, det = +1 "
        "and det = −1, with no path between them (the lab above: no slider "
        "turns a mirror frame into a right-handed one). Picking det = +1 is "
        "like picking the four-bar's assembly mode: the rules alone allow "
        "both, a physical fact rules one out. And SO(3) is that 3-D surface: "
        "curved, closed, finite, which is why page 116 said it is not ℝ³ "
        "and cannot be covered by three angles without a bad spot.")))
    return c


def so3_card() -> Card:
    c = Card("so what IS SO(3)? a picture you can actually hold")
    c.add(body(
        "<b>1. The definition, in words.</b> SO(3) is the set of all rotation "
        "matrices — equivalently, the set of <b>every way a rigid body can be "
        "oriented</b>. One point of SO(3) = one orientation. It is the "
        "orientation part of a body's C-space (page 115).<br>"
        "<b>2. Its size.</b> 3-D: you need 3 numbers to pick an "
        "orientation (page 115 counted 6 DOF for a free body: 3 position + "
        "3 orientation).<br>"
        "<b>3. Why you cannot 'see' it.</b> It is a 3-D <i>curved</i> space. "
        "We can draw curved 1-D things (the circle of a joint, page 116) and "
        "curved 2-D things (a sphere's surface) in our 3-D world, but a "
        "curved 3-D thing does not fit. Mathematically it sits inside the "
        "9-D space of all 3×3 matrices, cut out by the 6 rules — just as the "
        "hoop sits inside the 2-D plane, cut out by 1 rule. The video's "
        "sphere is a <b>cartoon</b> meaning 'curved and closed', not the "
        "real shape.<br>"
        "<b>4. The picture that works: a ball with its skin glued.</b> Every "
        "orientation is one turn θ about one axis ω̂ (video 3.2.3 proves "
        "it). Draw it as the point ω̂θ: <i>direction</i> from the centre = "
        "the axis, <i>distance</i> from the centre = the angle. The centre "
        "is 'no rotation'. Angles only go up to 180° (a 200° turn is a 160° "
        "turn the other way), so all orientations fill a <b>solid ball of "
        "radius 180°</b>. One catch: on the skin, 180° about ω̂ and 180° "
        "about −ω̂ are the same orientation, so <b>opposite points of the "
        "skin are the same point</b>. Walk out through the skin and you "
        "re-enter from the opposite side."))
    c.add(link_back("116", (
        "That is the 3-D version of the joint circle on page 116. A joint "
        "angle lives on a segment [0°, 360°) whose two ends are glued "
        "(359° → 0°). SO(3) lives in a ball whose opposite skin points are "
        "glued. Gluing is what makes the space closed with no edge, and it "
        "is also why no single set of 3 numbers covers it smoothly: "
        "somewhere the numbers must jump (axis-angle at 180°) or blow up "
        "(Euler angles at pitch ±90°). So R (implicit) is used for "
        "computing, and 3 numbers only locally.")))
    return c


class SO3BallCard:
    """Orientations as points of a radius-pi ball; antipodal skin glued."""

    def __init__(self):
        c = self.card = Card("lab: walk through SO(3) — the ball of radius 180°")
        c.add(body(
            "Choose a spin axis and turn the body from 0° to 360° about it. "
            "Left: the orientation's point in the ball (orange), with the "
            "path it has travelled. Right: the body itself.", dim=True))
        self.s_az = labelled_slider(c, "axis azimuth", -180, 180, 30, deg, self._draw)
        self.s_el = labelled_slider(c, "axis elevation", -90, 90, 30, deg, self._draw)
        self.s_th = labelled_slider(c, "turn so far", 0, 360, 120, deg, self._draw)
        self.st_p = Stat("point ω̂θ (θ in degrees)", "--", theme.WARN)
        self.st_d = Stat("distance from centre", "--", theme.ACCENT)
        c.add_layout(stat_row(self.st_p, self.st_d))
        self.cv = MplCanvas(width=8.6, height=3.8)
        _layout(self.cv, ["3d", "3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try:</b> drag the turn slowly from 0°. The point leaves the "
            "centre along the axis; at 180° it touches the skin; just past "
            "180° it reappears at the <b>opposite</b> side of the skin and "
            "travels back to the centre, arriving at 360° — the body is back "
            "where it started. The body on the right moved smoothly the "
            "whole time: the 'jump' is only in the drawing, like 359° → 0° "
            "for a joint. Every orientation you can make with the sliders is "
            "somewhere in that ball, which is SO(3)."))
        self._draw()

    @staticmethod
    def _pt(w, th):
        th = th % (2 * math.pi)
        return w * th if th <= math.pi else -w * (2 * math.pi - th)

    def _draw(self, *_):
        w = _unit(math.radians(self.s_az.value()), math.radians(self.s_el.value()))
        th = math.radians(self.s_th.value())
        P = np.degrees(self._pt(w, th))
        self.st_p.set(_vec(P, 0))
        self.st_d.set(f"{np.linalg.norm(P):.0f}° (= angle turned)")
        _clear(self.cv)
        a1, a2 = self.cv.axes
        u, v = np.meshgrid(np.linspace(0, 2 * math.pi, 24), np.linspace(0, math.pi, 12))
        a1.plot_wireframe(180 * np.cos(u) * np.sin(v), 180 * np.sin(u) * np.sin(v),
                          180 * np.cos(v), color=theme.BORDER, lw=0.4, alpha=0.5)
        a1.plot([0], [0], [0], "o", color=theme.TEXT, ms=4)
        ts = np.linspace(0, th, 200)
        pts = np.degrees(np.array([self._pt(w, t) for t in ts]))
        jump = np.where(np.linalg.norm(np.diff(pts, axis=0), axis=1) > 90)[0]
        for seg in np.split(pts, jump + 1):
            a1.plot(seg[:, 0], seg[:, 1], seg[:, 2], color=theme.CYAN, lw=2)
        if len(jump):
            for e in (pts[jump[0]], pts[jump[0] + 1]):
                a1.plot(*[[x] for x in e], "x", color=theme.BAD, ms=9, mew=2)
        a1.plot(*[[x] for x in P], "o", color=theme.WARN, ms=9)
        _cube(a1, 190)
        a1.set_title("SO(3) as a ball: red × = the glued pair it jumped between")
        R = rk.rot_exp(w * th)
        _frame3d(a2, np.eye(3), alpha=0.2, lw=1.2)
        _frame3d(a2, R, lw=3, name="")
        a2.plot(*[[-1.2 * w[i], 1.2 * w[i]] for i in range(3)], "--", color=theme.WARN, lw=2)
        _cube(a2)
        a2.set_title("the body: smooth the whole way")
        self.cv.refresh()


class CommuteCard:
    """Same two turns, two orders, two different results."""

    def __init__(self):
        c = self.card = Card("lab: rotations do not commute")
        c.add(body(
            "A = a turn α about x<sub>s</sub>, B = a turn β about "
            "z<sub>s</sub>. Left panel: AB. Right panel: BA. Same two turns, "
            "opposite order.", dim=True))
        self.s_a = labelled_slider(c, "α about x", -180, 180, 90, deg, self._draw)
        self.s_b = labelled_slider(c, "β about z", -180, 180, 90, deg, self._draw)
        self.st = Stat("‖AB − BA‖", "--", theme.BAD)
        self.st_ang = Stat("angle between results", "--", theme.WARN)
        c.add_layout(stat_row(self.st, self.st_ang))
        self.cv = MplCanvas(width=8.2, height=3.6)
        _layout(self.cv, ["3d", "3d"])
        c.add(self.cv)
        c.add(plain(
            "At 90° and 90° the two results point in visibly different "
            "directions; the stat says they differ by a 120° turn. <b>Try:</b> "
            "set either slider to 0: the difference vanishes, because a turn "
            "and 'no turn' commute. Small turns almost commute — set both to "
            "10° and the gap is under 2°; halve both and it drops about "
            "fourfold. That is why ω can be treated as a "
            "plain 3-vector for an instant (next videos), while finite turns "
            "must be multiplied in the right order."))
        c.add(link_back("117", (
            "This is page 117's car again. Turning 90° about x then 90° about "
            "z, or the other way, uses the same 'amount' of each turn, but "
            "ends at a different orientation. So the orientation is <b>not</b> "
            "a function of 'total turn about x, total turn about y, total "
            "turn about z'. That is exactly what 'nonholonomic' meant: you "
            "cannot integrate the three components of angular velocity into "
            "three position-like numbers, just as you could not integrate the "
            "car's no-slip rule into a g(x, y, φ). Hence video 3.1's warning: "
            "velocities are not derivatives of coordinates.")))
        self._draw()

    def _draw(self, *_):
        A = rotx(math.radians(self.s_a.value()))
        B = rotz(math.radians(self.s_b.value()))
        AB, BA = A @ B, B @ A
        self.st.set(f"{np.linalg.norm(AB - BA):.3f}")
        self.st_ang.set(f"{math.degrees(np.linalg.norm(rk.rot_log(AB.T @ BA))):.1f}°")
        _clear(self.cv)
        for ax, R, t in zip(self.cv.axes, (AB, BA), ("A·B: z-turn first, then x",
                                                        "B·A: x-turn first, then z")):
            _frame3d(ax, np.eye(3), alpha=0.2, lw=1.2)
            _frame3d(ax, R, name="", lw=3)
            _cube(ax)
            ax.set_title(t)
        self.cv.refresh()


# ==========================================================================
# 3.2.1  rotation matrices, part 2: the three uses
# ==========================================================================

_EXPRS = {
    "R_sb  ({b} seen from {s})": (lambda: R_SB, "R_sb", "given"),
    "R_bc  ({c} seen from {b})": (lambda: R_BC, "R_bc", "given"),
    "R_sb · R_bc  (inner b's cancel → R_sc)": (lambda: R_SB @ R_BC, "R_sc", "cancel"),
    "R_bc · R_sb  (c next to s: nothing cancels)": (lambda: R_BC @ R_SB, None, "wrong"),
    "R_scᵀ  (swap subscripts → R_cs)": (lambda: R_SC.T, "R_cs", "transpose"),
    "R_bcᵀ · R_sbᵀ  (walk the path backwards → R_cs)": (lambda: R_BC.T @ R_SB.T, "R_cs",
                                                       "cancel"),
}


class SubscriptCard:
    """Three frames {s}, {b}, {c}; build R_sc by cancelling subscripts."""

    def __init__(self):
        c = self.card = Card("use 1 and 2: represent an orientation, change the reference frame")
        c.add(body(
            "The video's three frames: {s}; {b} = {s} turned 90° about "
            "z<sub>s</sub>; {c} = {b} turned −90° about its own y-axis. "
            "<b>Use 1, represent:</b> R<sub>sc</sub> lists {c}'s axes in {s} "
            "numbers. R<sub>cs</sub>, {s}'s axes in {c} numbers, is its "
            "transpose (= inverse): swapping the subscripts transposes the "
            "matrix. <b>Use 2, change the reference frame:</b> if you know "
            "{c} as seen from {b} (R<sub>bc</sub>) and want it as seen from "
            "{s}, premultiply by R<sub>sb</sub>. The <b>subscript "
            "cancellation rule</b>: in R<sub>sb</sub>R<sub>bc</sub> the "
            "second subscript of the first matrix meets the first subscript "
            "of the second; they match, so they cancel and leave "
            "R<sub>sc</sub>. Vectors obey the same rule: "
            "p<sub>s</sub> = R<sub>sb</sub>p<sub>b</sub>."))
        c.add(math_label(
            r"R_{sb}\,R_{bc}=R_{sc},\qquad R_{cs}=R_{sc}^{-1}=R_{sc}^T,"
            r"\qquad p_s=R_{sb}\,p_b", 15))
        self.combo = QComboBox()
        for k in _EXPRS:
            self.combo.addItem(k)
        self.combo.setCurrentIndex(2)
        self.combo.currentIndexChanged.connect(self._draw)
        c.add(self.combo)
        self.res = body("")
        c.add(self.res)
        c.add(body(
            "Now a vector: a point p written in {b} numbers. The sliders set "
            "p<sub>b</sub>; the readout gives p<sub>s</sub> = "
            "R<sub>sb</sub>p<sub>b</sub>, the <i>same</i> arrow in {s} "
            "numbers.", dim=True))
        self.px = labelled_slider(c, "p_b x", -10, 10, 10, lambda v: f"{v/10:+.1f}", self._draw)
        self.py = labelled_slider(c, "p_b y", -10, 10, 0, lambda v: f"{v/10:+.1f}", self._draw)
        self.pz = labelled_slider(c, "p_b z", -10, 10, 5, lambda v: f"{v/10:+.1f}", self._draw)
        self.st_pb = Stat("p_b (numbers in {b})", "--", theme.ACCENT)
        self.st_ps = Stat("p_s = R_sb p_b", "--", theme.GOOD)
        self.st_len = Stat("length in both", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_pb, self.st_ps, self.st_len))
        self.cv = MplCanvas(width=8.6, height=3.4)
        _layout(self.cv, ["3d", "3d", "3d"])
        c.add(self.cv)
        c.add(plain(
            "Treat subscripts like units in physics: (km/h)·(h) = km. "
            "<b>Try</b> the drop-down. 'R<sub>sb</sub>·R<sub>bc</sub>' gives "
            "R<sub>sc</sub> and the check says it matches the drawn {c}. "
            "'R<sub>bc</sub>·R<sub>sb</sub>' puts c next to s: nothing "
            "cancels, and the check fails — the multiplication is legal "
            "algebra but means nothing. Walking the path backwards "
            "(R<sub>bc</sub>ᵀ then R<sub>sb</sub>ᵀ, i.e. c→b→s) gives "
            "R<sub>cs</sub>. For the vector: with p<sub>b</sub> = (1, 0, "
            "0.5), p<sub>s</sub> = (0, 1, 0.5). The arrow (orange, drawn in "
            "all three panels) did not move; only the frame doing the "
            "describing changed, so the numbers changed and the length did "
            "not."))
        self._draw()

    def _draw(self, *_):
        f, name, kind = _EXPRS[self.combo.currentText()]
        M = f()
        truth = {"R_sb": R_SB, "R_bc": R_BC, "R_sc": R_SC, "R_cs": R_SC.T}
        if kind == "wrong":
            ok = (f"<span style='color:{theme.BAD}'><b>no cancellation</b>: "
                  f"distance from R_sc = {np.linalg.norm(M - R_SC):.2f}. Legal "
                  f"maths, meaningless frame.</span>")
        else:
            err = np.linalg.norm(M - truth[name])
            ok = (f"<span style='color:{theme.GOOD}'>= <b>{name}</b> "
                  f"(error {err:.0e}): columns are {name[-1]}'s axes in "
                  f"{{{name[-2]}}} numbers.</span>")
        self.res.setText(_cols_html(M, 0) + ok)
        pb = np.array([self.px.value(), self.py.value(), self.pz.value()]) / 10
        ps = R_SB @ pb
        self.st_pb.set(_vec(pb, 1))
        self.st_ps.set(_vec(ps, 1))
        self.st_len.set(f"{np.linalg.norm(pb):.2f} = {np.linalg.norm(ps):.2f}")
        _clear(self.cv)
        for ax, R, nm in zip(self.cv.axes, (np.eye(3), R_SB, R_SC), ("{s}", "{b}", "{c}")):
            _frame3d(ax, np.eye(3), alpha=0.15, lw=1)
            _frame3d(ax, R, name="", lw=3)
            ax.plot([0, ps[0]], [0, ps[1]], [0, ps[2]], color=theme.WARN, lw=2.5)
            coords = R.T @ ps
            ax.set_title(f"{nm}: p = {_vec(coords, 1)}")
            _cube(ax)
        self.cv.refresh()


class RotateOperatorCard:
    """Use 3: R as an operator. Premultiply turns about z_s, postmultiply about z_c."""

    def __init__(self):
        c = self.card = Card("use 3: rotate a vector or a frame — and why left vs right matters")
        c.add(body(
            "R<sub>sb</sub> is also 'turn 90° about z', so any rotation "
            "matrix can be read as an <b>operation</b>: R = Rot(ω̂, θ). "
            "<b>On a vector.</b> If the vector is in {b} numbers, "
            "R<sub>sb</sub>p<sub>b</sub> cancels subscripts: that is use 2. "
            "If it is already in {s} numbers, nothing cancels, so the product "
            "is read as a new vector: p′<sub>s</sub> = R p<sub>s</sub> is "
            "p<sub>s</sub> <i>turned</i> about the axis, still written in "
            "{s}.<br><b>On a frame.</b> R<sub>sc</sub> can be multiplied on "
            "either side by Rot(ẑ, θ):<br>"
            "• <b>premultiply</b>, R<sub>sc′</sub> = Rot(ẑ, θ)·R<sub>sc</sub>: "
            "the axis ẑ is read in the frame of the <b>first</b> subscript, "
            "{s}. {c} swings about the fixed z<sub>s</sub>.<br>"
            "• <b>postmultiply</b>, R<sub>sc″</sub> = R<sub>sc</sub>·Rot(ẑ, θ): "
            "the axis is read in the frame of the <b>second</b> subscript, "
            "{c}. {c} spins about its own z<sub>c</sub>.<br>"
            "Both results are still written in {s}. Same matrix, same angle, "
            "different axis — so different frames."))
        c.add(math_label(
            r"\mathrm{left:}\ R_{sc'}=\mathrm{Rot}(\hat z,\theta)\,R_{sc}\ (\hat z=z_s)"
            r"\qquad \mathrm{right:}\ R_{sc''}=R_{sc}\,\mathrm{Rot}(\hat z,\theta)\ (\hat z=z_c)", 14))
        self.s_th = labelled_slider(c, "θ about ẑ", -180, 180, 90, deg, self._draw)
        self.L_txt = body("")
        c.add(self.L_txt)
        self.cv = MplCanvas(width=8.2, height=3.6)
        _layout(self.cv, ["3d", "3d"])
        c.add(self.cv)
        c.add(plain(
            "Faint dashed: the original {c}. Bold: the result. Orange dotted "
            "line: the axis actually used. With {c} from the last card, "
            "z<sub>s</sub> is vertical but z<sub>c</sub> lies flat (it "
            "points along −y<sub>s</sub>). <b>Try:</b> at θ = 90° the left "
            "panel's frame swings around the vertical; the right panel's "
            "spins about the flat axis. Set θ = 0: both agree, nothing "
            "turned. Rule to keep: <b>left = about a fixed (space) axis, "
            "right = about the body's own axis.</b> The same rule returns for "
            "4×4 transforms (page 120) and for forward kinematics (page 121)."))
        self._draw()

    def _draw(self, *_):
        th = math.radians(self.s_th.value())
        Rz = rotz(th)
        left, right = Rz @ R_SC, R_SC @ Rz
        self.L_txt.setText(
            "<table><tr><td>R<sub>sc′</sub> (left) =</td><td>" + _cols_html(left, 2)
            + "</td><td style='padding-left:24px'>R<sub>sc″</sub> (right) =</td><td>"
            + _cols_html(right, 2) + "</td></tr></table>")
        _clear(self.cv)
        for ax, R, axis, t in zip(self.cv.axes, (left, right),
                                  (np.array([0, 0, 1.0]), R_SC[:, 2]),
                                  ("premultiply: turn about z_s", "postmultiply: turn about z_c")):
            _frame3d(ax, np.eye(3), alpha=0.12, lw=1)
            _frame3d(ax, R_SC, alpha=0.35, lw=1.5, ls="--")
            _frame3d(ax, R, name="", lw=3)
            ax.plot(*[[-1.2 * axis[i], 1.2 * axis[i]] for i in range(3)], ":",
                    color=theme.WARN, lw=2)
            _cube(ax)
            ax.set_title(t)
        self.cv.refresh()


# ==========================================================================
# 3.2.2  angular velocities
# ==========================================================================

def check_card() -> Card:
    """The bead-on-a-hoop story retold for R, one claim at a time, checked."""
    c = Card("check your understanding: the bead-on-a-hoop story, retold for R")
    c.add(body(
        "Page 117's story had four steps: a position rule g = 0 → "
        "differentiate it → a velocity rule A q̇ = 0 → the allowed "
        "velocities are the null space of A. Here is the same story for a "
        "rotation, written the way a student first tells it, with each claim "
        "marked. ✓ = right as stated; ◐ = right idea, one detail to fix."))
    ok = f"<b style='color:{theme.GOOD}'>✓</b>"
    half = f"<b style='color:{theme.WARN}'>◐</b>"
    c.add(body(_grid_table(
        ("the claim", "", "what to keep / what to fix"),
        [("'The hand's orientation C-space is 3-D, like a sphere, so an "
          "explicit 3-number representation (Euler angles) fails somewhere.'",
          half,
          "3-D ✓, curved and closed ✓, every 3-number chart fails somewhere ✓. "
          "Two fixes. (1) It is not literally a sphere: a sphere is 2-D. The "
          "video's sphere is a cartoon for 'curved and closed'. The honest "
          "picture is the ball on page 118. (2) Euler angles (ZYX) fail at "
          "<b>pitch ±90°</b> (gimbal lock), not at 180°. 180° is where a "
          "<i>different</i> 3-number chart, axis-angle ω̂θ, gets awkward."),
         ("'So we use an implicit representation: 9 numbers in R, with the "
          "rule RᵀR = I, which says each column has length 1 and each pair "
          "of columns is perpendicular.'",
          ok,
          "Exactly. Add the last rule: det R = +1 (right-handed). The 6 "
          "independent entries of RᵀR − I are the 6 holonomic rules g(R) = 0, "
          "and 9 − 6 = 3 DOF."),
         ("'Differentiate: RṘᵀ + ṘRᵀ = 0, so ṘRᵀ = −(ṘRᵀ)ᵀ is "
          "skew-symmetric: zero diagonal, below = minus above, only 3 "
          "numbers matter — probably the 3 velocities.'",
          ok,
          "Right, and you used RRᵀ = I, which is also true (Rᵀ is R's "
          "inverse, so it works from either side). Differentiating RRᵀ = I "
          "gives ṘRᵀ skew; its 3 numbers are ω written in <b>{s}</b> "
          "components: ṘRᵀ = [ω<sub>s</sub>]. Differentiating RᵀR = I "
          "gives RᵀṘ skew; its 3 numbers are the <i>same</i> spin written in "
          "<b>{b}</b> components: RᵀṘ = [ω<sub>b</sub>]. 'Probably the 3 "
          "velocities' → yes, exactly the angular velocity."),
         ("'The allowed velocities are the null space of some matrix. What "
          "matrix?'",
          half,
          "A good question the video skips. It is a 6×9 matrix A(R), one row "
          "per rule, acting on Ṙ stacked into 9 numbers. Its null space is "
          "3-D and is exactly {[ω]R}. Built and tested in the lab two cards "
          "below.")])))
    return c


def _constraint_A(R):
    """6x9 Jacobian of the six rules of R^T R = I, acting on vec(Rdot)
    (Rdot's columns stacked). Rows: |x|^2, |y|^2, |z|^2, x.y, y.z, z.x."""
    x, y, z = R[:, 0], R[:, 1], R[:, 2]
    Z = np.zeros(3)
    rows = ((2 * x, Z, Z), (Z, 2 * y, Z), (Z, Z, 2 * z),
            (y, x, Z), (Z, z, y), (z, Z, x))
    return np.array([np.r_[a, b, cc] for a, b, cc in rows])


def why_rdot_card() -> Card:
    c = Card("step by step: from the 6 rules to the 3 numbers ω")
    c.add(body(
        "<b>Step 1. The rules.</b> Name R's columns x̂<sub>b</sub>, "
        "ŷ<sub>b</sub>, ẑ<sub>b</sub> (the body's axes in {s} numbers). "
        "RᵀR = I is six violation meters, each reading 0:"))
    c.add(body(_grid_table(
        ("meter", "reads zero when…", "its rate (differentiate)"),
        [("g₁ = x̂·x̂ − 1", "x-axis has length 1", "2 x̂·ẋ"),
         ("g₂ = ŷ·ŷ − 1", "y-axis has length 1", "2 ŷ·ẏ"),
         ("g₃ = ẑ·ẑ − 1", "z-axis has length 1", "2 ẑ·ż"),
         ("g₄ = x̂·ŷ", "x ⟂ y", "ŷ·ẋ + x̂·ẏ"),
         ("g₅ = ŷ·ẑ", "y ⟂ z", "ẑ·ẏ + ŷ·ż"),
         ("g₆ = ẑ·x̂", "z ⟂ x", "x̂·ż + ẑ·ẋ")])))
    c.add(body(
        "<b>Step 2. The velocity rule.</b> Each rate is linear in the 9 "
        "numbers of Ṙ = [ẋ ẏ ż]. Stack Ṙ into one 9-vector and the six rates "
        "become one matrix product: A(R)·vec(Ṙ) = 0, with A a 6×9 matrix "
        "whose rows are the coefficient lists in the right-hand column. "
        "That is the A you asked about — page 117's A(q)q̇ = 0 with "
        "q̇ = vec(Ṙ).<br>"
        "<b>Step 3. Its null space.</b> 9 unknowns − 6 independent rows = "
        "3 free directions. Which ones? Try ẋ = ω × x̂, ẏ = ω × ŷ, ż = ω × ẑ "
        "for any 3-vector ω. Then every meter rate is zero: e.g. "
        "2x̂·(ω × x̂) = 0 because ω × x̂ is perpendicular to x̂. So "
        "Ṙ = [ω × x̂  ω × ŷ  ω × ẑ] is allowed, it has exactly 3 free numbers "
        "(ω's components), and it fills the whole 3-D null space. "
        "<b>The 3 numbers that survive are ω.</b><br>"
        "<b>Step 4. The short way.</b> All six rules in one line: "
        "differentiate RᵀR = I (product rule)."))
    c.add(math_label(
        r"\dot R^TR+R^T\dot R=0\ \Rightarrow\ R^T\dot R=-(R^T\dot R)^T\ "
        r"(\mathrm{skew}),\qquad \dot RR^T=-(\dot RR^T)^T\ (\mathrm{skew})", 15))
    c.add(body(
        "A skew-symmetric 3×3 matrix has zeros on the diagonal (3 of the "
        "rules) and each lower entry equal to minus the upper one (the other "
        "3). Only 3 numbers are left: the same 3 as step 3, packed as a "
        "matrix."))
    c.add(link_back("117", (
        "Side by side with the bead. <b>Numbers:</b> (x, y) → the 9 entries "
        "of R. <b>Rules g = 0:</b> x² + y² − 1 → the 6 meters above. "
        "<b>Space:</b> a 1-D circle → 3-D SO(3). <b>A:</b> the 1×2 row "
        "[2x 2y] → the 6×9 A(R). <b>Allowed velocities = null(A):</b> "
        "(−y, x)·(rate along the hoop), 1 number → [ω]R, 3 numbers. "
        "<b>The surviving numbers:</b> 'how fast along the hoop' → "
        "ω<sub>x</sub>, ω<sub>y</sub>, ω<sub>z</sub>, 'how fast spinning "
        "about each axis'. The drift warning carries over too: step R by a "
        "straight Ṙ·Δt and you leave SO(3), like the dashed tangent line "
        "leaving the hoop. The exponential (video 3.2.3) steps without "
        "leaving.")))
    return c


class ConstraintMatrixCard:
    """Build A(R), find its null space, and test candidate Rdot's against it."""

    def __init__(self):
        c = self.card = Card("lab: the 6×9 matrix A(R) and its 3-D null space")
        c.add(body(
            "Pick an orientation R and a candidate velocity "
            "Ṙ = [ω]R + εR. The [ω]R part is a real spin. The εR part "
            "<i>stretches</i> every axis — something no rotation can do. "
            "The six meter rates A·vec(Ṙ) say which rules the candidate "
            "breaks.", dim=True))
        self.s_o = labelled_slider(c, "orientation (turn about (1,1,0))", -180, 180, 40,
                                   deg, self._draw)
        self.s_w = [labelled_slider(c, f"ω_{a}", -20, 20, v,
                                    lambda v: f"{v/10:+.1f} rad/s", self._draw)
                    for a, v in (("x", 5), ("y", 0), ("z", 10))]
        self.s_e = labelled_slider(c, "stretch ε (not a rotation)", -50, 50, 0,
                                   lambda v: f"{v/100:+.2f}", self._draw)
        self.txt = body("")
        c.add(self.txt)
        self.st_rank = Stat("rank A", "--", theme.ACCENT)
        self.st_null = Stat("dim null(A) = 9 − rank", "--", theme.VIOLET)
        self.st_rate = Stat("meter rates A·vec(Ṙ)", "--", theme.BAD)
        self.st_basis = Stat("‖A·vec([ê_i]R)‖, i = x, y, z", "--", theme.GOOD)
        c.add_layout(stat_row(self.st_rank, self.st_null, self.st_rate, self.st_basis))
        c.add(plain(
            "Rank 6 at every orientation (try the slider): the six rules are "
            "independent, so 9 − 6 = 3 velocity directions survive. The last "
            "stat checks three special candidates, a spin about x̂<sub>s</sub>, "
            "about ŷ<sub>s</sub>, about ẑ<sub>s</sub>: all give zero, so they "
            "are the null space's three directions, and any ω is a mix of "
            "them. <b>Try:</b> move the ω sliders anywhere — the meter rates "
            "stay 0. Now add a little stretch ε: the first three rates (the "
            "length meters) light up at 2ε each and the angle meters stay 0. "
            "That Ṙ is not in the null space, so it is not a velocity any "
            "rotation can have. This is page 117's wall lab in 9 dimensions."))
        self._draw()

    def _draw(self, *_):
        R = rk.rot_exp(np.array([1, 1, 0]) / math.sqrt(2) * math.radians(self.s_o.value()))
        w = np.array([s.value() / 10 for s in self.s_w])
        eps = self.s_e.value() / 100
        Rdot = rk.skew(w) @ R + eps * R
        A = _constraint_A(R)
        vec = lambda M: M.flatten(order="F")
        rates = A @ vec(Rdot)
        basis = [np.linalg.norm(A @ vec(rk.skew(e) @ R)) for e in np.eye(3)]
        rank = np.linalg.matrix_rank(A)
        self.st_rank.set(str(rank))
        self.st_null.set(str(9 - rank))
        self.st_rate.set(_vec(rates, 2))
        self.st_basis.set(", ".join(f"{b:.0e}" for b in basis))
        head = ("<span style='color:" + theme.TEXT_DIM + "'>columns: ẋ (3) | ẏ (3) "
                "| ż (3); rows: g₁ … g₆ as in the table above</span>")
        self.txt.setText("A(R) = " + mat_html(A, 2) + head)


def tangent_card() -> Card:
    c = Card("the tangent space, and why 3 numbers work for velocity but not for orientation")
    c.add(body(
        "<b>1. Count the cartoon correctly.</b> The video draws SO(3) as a "
        "sphere only to say 'curved and closed'. A real sphere is 2-D, so "
        "its tangent plane needs 2 numbers. SO(3) is 3-D, so its tangent "
        "space is a flat <b>3-D</b> space and needs 3 numbers. (The x, y, "
        "heading of a car is a different thing: the 3 numbers of a planar "
        "<i>position</i>, page 117.)<br>"
        "<b>2. Which 3 numbers?</b> Not three angles. The tangent space is "
        "the space of <i>velocities</i>, and the three numbers are three "
        "<b>spin rates</b>: how fast the body spins about x̂<sub>s</sub>, "
        "about ŷ<sub>s</sub>, about ẑ<sub>s</sub>. That is ω = (ω<sub>x</sub>, "
        "ω<sub>y</sub>, ω<sub>z</sub>), in rad/s. A gyroscope measures exactly "
        "these.<br>"
        "<b>3. '3-vector' vs '3 numbers'.</b> Same thing, with one promise "
        "added: a 3-vector is 3 numbers that describe an <i>arrow</i>, so "
        "they rotate like an arrow when you change frame (ω<sub>b</sub> = "
        "Rᵀω<sub>s</sub>, later on this page), and you can add two of them "
        "tip to tail. Euler angles are 3 numbers but not a vector: you "
        "cannot add two sets of Euler angles to compose two rotations.<br>"
        "<b>4. Why velocity has no bad spot but orientation does.</b> Two "
        "different things are both called 'velocity':"))
    c.add(body(_grid_table(
        ("", "what it is", "bad spots?"),
        [("coordinate rates", "time derivatives of the numbers you used for "
          "position: longitude rate, roll/pitch/yaw rates",
          "<b>yes</b> — wherever the position chart is bad. Walking east at "
          "1 m/s near the pole, the longitude rate → ∞; near pitch 90° the "
          "yaw rate → ∞"),
         ("physical velocity", "the motion itself, measured along fixed axes: "
          "m/s in x, y, z; or ω, the gyro's three spin rates",
          "<b>none</b> — it never goes through the position chart")])))
    c.add(body(
        "Orientation lives on curved SO(3): any 3 labels for it are a chart "
        "of a curved closed space, so one bad spot is unavoidable, and the "
        "only escape is implicit (R: 9 numbers + 6 rules). Velocity lives on "
        "the flat tangent space: 3 spin rates along fixed axes label it "
        "everywhere, so velocity does <b>not</b> need the implicit trick — "
        "as long as you never compute it as Euler-angle rates."))
    c.add(body(_grid_table(
        ("representation", "numbers", "bad spots"),
        [("orientation, explicit (Euler, axis-angle)", "3", "always somewhere (theorem)"),
         ("orientation, implicit (R, + 6 rules)", "9", "none"),
         ("velocity as Euler-angle rates", "3", "wherever the Euler chart is bad"),
         ("velocity as Ṙ (+ 6 rules)", "9", "none, but wasteful"),
         ("velocity as ω (spin rates on fixed axes)", "3", "<b>none</b> ← the payoff")])))
    c.add(plain(
        "Rule for code: store orientation as R (or a quaternion), store "
        "velocity as ω. Never store velocity as Euler-angle rates. The lab "
        "below shows why with one steady spin."))
    return c


class GimbalRatesCard:
    """One steady spin; its Euler-angle rates blow up near pitch 90 deg."""

    def __init__(self):
        c = self.card = Card("lab: one steady spin, two descriptions — ω stays calm, Euler rates explode")
        c.add(body(
            "The body starts at {s} and spins at a constant 1 rad/s about an "
            "axis that is ŷ<sub>s</sub> tilted by δ toward x̂<sub>s</sub>. Its "
            "ZYX pitch rises to 90° − δ and comes back. Left: the gyro's "
            "three body spin rates ω<sub>b</sub>. Right: the same motion "
            "described as roll, pitch and yaw rates.", dim=True))
        self.s_d = labelled_slider(c, "δ: how far the path misses pitch 90°", 1, 40, 8, deg,
                                   self._draw)
        self.st_p = Stat("highest pitch reached", "--", theme.ACCENT)
        self.st_w = Stat("|ω| the whole time", "--", theme.GOOD)
        self.st_y = Stat("peak |yaw rate|", "--", theme.BAD)
        c.add_layout(stat_row(self.st_p, self.st_w, self.st_y))
        self.cv = MplCanvas(width=8.4, height=3.4, ncols=2)
        c.add(self.cv)
        c.add(plain(
            "Nothing dramatic happens to the body: |ω| = 1 rad/s throughout "
            "and the left panel is smooth. On the right, roll and yaw rates "
            "spike when pitch nears 90°, because the yaw-rate formula divides "
            "by cos(pitch). <b>Try:</b> δ = 20° — mild bumps. δ = 2° — "
            "spikes near 30 rad/s. δ = 1°: about 56. Exactly through 90° they "
            "are undefined. The explosion lives in the chart, not in the "
            "motion."))
        self._draw()

    def _draw(self, *_):
        d = math.radians(self.s_d.value())
        ws = np.array([math.sin(d), math.cos(d), 0.0])
        ts = np.linspace(0, math.pi, 600)
        wb_all, rates, pitch = [], [], []
        for t in ts:
            R = rk.rot_exp(ws * t)
            wb = R.T @ ws
            th = math.asin(max(-1.0, min(1.0, -R[2, 0])))
            ph = math.atan2(R[2, 1], R[2, 2])
            p, q, r = wb
            yd = (q * math.sin(ph) + r * math.cos(ph)) / math.cos(th)
            rates.append((p + yd * math.sin(th), q * math.cos(ph) - r * math.sin(ph), yd))
            wb_all.append(wb)
            pitch.append(th)
        wb_all, rates = np.array(wb_all), np.array(rates)
        self.st_p.set(f"{math.degrees(max(pitch)):.1f}°")
        self.st_w.set("1.00 rad/s")
        self.st_y.set(f"{np.abs(rates[:, 2]).max():.1f} rad/s")
        self.cv.clear()
        a1, a2 = self.cv.axes
        for i, nm in enumerate(("ω_x (body)", "ω_y (body)", "ω_z (body)")):
            a1.plot(ts, wb_all[:, i], color=AX_COLS[i], lw=2, label=nm)
        a1.plot(ts, np.linalg.norm(wb_all, axis=1), "--", color=theme.TEXT, lw=1, label="|ω|")
        a1.set_ylim(-1.5, 1.5)
        a1.set_xlabel("time (s)")
        a1.set_title("gyro: ω (physical velocity)")
        self.cv.legend(a1, loc="lower left")
        for i, (nm, col) in enumerate((("roll rate", AX_COLS[0]), ("pitch rate", AX_COLS[1]),
                                       ("yaw rate", AX_COLS[2]))):
            a2.plot(ts, rates[:, i], color=col, lw=2, label=nm)
        lim = max(3.0, min(70.0, 1.1 * np.abs(rates).max()))
        a2.set_ylim(-lim, lim)
        a2.set_xlabel("time (s)")
        a2.set_title("Euler-angle rates (coordinate rates)")
        self.cv.legend(a2, loc="lower left")
        self.cv.refresh()


def axis_speed_card() -> Card:
    c = Card("ω = ω̂θ̇ is the same (ω_x, ω_y, ω_z) you grew up with")
    c.add(body(
        "<b>1. Nothing new is being defined.</b> You know angular velocity "
        "as a column (ω<sub>x</sub>; ω<sub>y</sub>; ω<sub>z</sub>). Writing "
        "ω = ω̂θ̇ is the same column, split as <i>direction × size</i>, the "
        "way any vector v = (unit direction) × (length):<br>"
        "&nbsp;&nbsp;ω̂ = ω / |ω|, the spin axis as a unit arrow;<br>"
        "&nbsp;&nbsp;θ̇ = |ω|, how fast the body turns about it, in rad/s.<br>"
        "Example: spin about z at 3 rad/s. ω̂ = (0, 0, 1), θ̇ = 3, so "
        "ω̂θ̇ = (0, 0, 3) = (ω<sub>x</sub>, ω<sub>y</sub>, ω<sub>z</sub>). "
        "Spin at 2 rad/s about an axis halfway between x and z: ω̂ = (0.707, "
        "0, 0.707), so ω = (1.414, 0, 1.414).<br>"
        "<b>2. Why split it at all?</b> Because the next video needs the "
        "two parts separately: 'spin about ω̂ for θ seconds'. θ̇ becomes θ, "
        "the angle, and ω̂θ becomes the exponential coordinates.<br>"
        "<b>3. What the components mean.</b> The body spins about <i>one</i> "
        "axis. ω<sub>x</sub>, ω<sub>y</sub>, ω<sub>z</sub> are that one "
        "arrow's shadows on the s-axes: ω<sub>x</sub> = θ̇ (ω̂ · x̂<sub>s</sub>) = "
        "θ̇ cos(angle between spin axis and x<sub>s</sub>), and so on. If the "
        "axis is along z<sub>s</sub>, all the spin is ω<sub>z</sub>; tilt it "
        "and the spin is shared out.<br>"
        "<b>4. Three spins at once.</b> For one instant, one spin about a "
        "tilted axis does exactly what three simultaneous spins do: "
        "ω<sub>x</sub> about x<sub>s</sub>, ω<sub>y</sub> about y<sub>s</sub>, "
        "ω<sub>z</sub> about z<sub>s</sub>. Tiny turns add like vectors; only "
        "<i>finite</i> turns care about order (the commute lab on page 118)."))
    return c


class ComponentsCard:
    """An arrow glued along x_s: its tip velocity, spin by spin."""

    def __init__(self):
        c = self.card = Card("lab: split the spin into ω_x, ω_y, ω_z and watch one glued arrow")
        c.add(body(
            "An arrow is glued to the body, pointing along x̂<sub>s</sub> right "
            "now. Each of the three component spins pushes its tip a "
            "different way. Defaults: θ̇ = 2 rad/s, axis tilted 45° from "
            "z<sub>s</sub> toward x<sub>s</sub>.", dim=True))
        self.s_t = labelled_slider(c, "axis tilt from z_s", 0, 180, 45, deg, self._draw)
        self.s_a = labelled_slider(c, "axis azimuth (about z_s)", -180, 180, 0, deg, self._draw)
        self.s_r = labelled_slider(c, "spin rate θ̇", 0, 30, 20, lambda v: f"{v/10:.1f} rad/s",
                                   self._draw)
        self.st_w = Stat("ω_s = θ̇ ω̂", "--", theme.WARN)
        self.st_v = Stat("tip velocity (0, ω_z, −ω_y)", "--", theme.VIOLET)
        self.st_c = Stat("|tip v| vs θ̇·sin(angle to x_s)", "--", theme.GOOD)
        c.add_layout(stat_row(self.st_w, self.st_v, self.st_c))
        self.cv = MplCanvas(width=8.4, height=3.6)
        _layout(self.cv, ["2d", "3d"])
        c.add(self.cv)
        c.add(plain(
            "Add the three spins' effects on the arrow along x̂<sub>s</sub>: "
            "the spin about x<sub>s</sub> does <b>nothing</b> (the arrow lies "
            "on that axis); the spin about y<sub>s</sub> swings the tip toward "
            "−z (ŷ × x̂ = −ẑ), giving (0, 0, −ω<sub>y</sub>); the spin about "
            "z<sub>s</sub> swings it toward +y (ẑ × x̂ = ŷ), giving (0, ω<sub>z</sub>, "
            "0). Total (0, ω<sub>z</sub>, −ω<sub>y</sub>): column 1 of "
            "[ω<sub>s</sub>]. <b>Check with defaults:</b> ω<sub>s</sub> = "
            "(1.414, 0, 1.414); tip velocity (0, 1.414, 0). Physically the tip "
            "is 0.707 from the spin axis, so its speed is 2 × 0.707 = 1.414 ✓, "
            "and it moves sideways, perpendicular to both the arrow and the "
            "axis ✓. <b>Try:</b> tilt 90° (axis along x<sub>s</sub>): the tip "
            "velocity is zero. Tilt 0° (axis along z<sub>s</sub>): all of "
            "θ̇ is ω<sub>z</sub> and the tip runs in +y at full speed."))
        self._draw()

    def _draw(self, *_):
        t, a = math.radians(self.s_t.value()), math.radians(self.s_a.value())
        rate = self.s_r.value() / 10
        wh = np.array([math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t)])
        w = rate * wh
        ex = np.array([1.0, 0, 0])
        v = np.cross(w, ex)
        ang = math.acos(max(-1, min(1, wh @ ex)))
        self.st_w.set(_vec(w, 3))
        self.st_v.set(_vec(v, 3))
        self.st_c.set(f"{np.linalg.norm(v):.3f} = {rate * math.sin(ang):.3f}")
        _clear(self.cv)
        a1, a2 = self.cv.axes
        a1.bar(["ω_x", "ω_y", "ω_z"], w, color=AX_COLS)
        a1.axhline(0, color=theme.BORDER, lw=1)
        a1.set_ylim(-3.2, 3.2)
        a1.set_title("one spin, shared over s-axes")
        _frame3d(a2, np.eye(3), alpha=0.25, lw=1.2, name="_s")
        a2.plot(*[[-1.3 * wh[i], 1.3 * wh[i]] for i in range(3)], "--", color=theme.WARN, lw=2)
        a2.plot([0, 1], [0, 0], [0, 0], color=theme.TEXT, lw=4)
        sc = 0.35
        a2.quiver(1, 0, 0, 0, 0, -sc * w[1], color=AX_COLS[1], lw=1.5, arrow_length_ratio=0.2)
        a2.quiver(1, 0, 0, 0, sc * w[2], 0, color=AX_COLS[2], lw=1.5, arrow_length_ratio=0.2)
        a2.quiver(1, 0, 0, *(sc * v), color=theme.VIOLET, lw=2.5, arrow_length_ratio=0.2)
        _cube(a2, 1.0)
        a2.set_title("white: arrow · violet: tip velocity")
        self.cv.refresh()


def layers_card() -> Card:
    c = Card("three layers: the spin (3 numbers) → the machine [ω] → Ṙ (9 numbers)")
    c.add(body(
        "ω<sub>x</sub>, ω<sub>y</sub>, ω<sub>z</sub> and "
        "ω<sub>s</sub> × x̂<sub>b</sub>, ω<sub>s</sub> × ŷ<sub>b</sub>, "
        "ω<sub>s</sub> × ẑ<sub>b</sub> are <b>different things</b>. The "
        "first is the cause (the spin, 3 numbers). The second is the effect "
        "(what the spin does to the body's three axes, 3 arrows = 9 numbers). "
        "The × is the cross product, not multiplication.<br>"
        "<b>Layer 1, the spin.</b> ω<sub>s</sub> = (ω<sub>x</sub>, "
        "ω<sub>y</sub>, ω<sub>z</sub>): the one arrow along the spin axis, "
        "in {s} components.<br>"
        "<b>Layer 2, what it does to the axes.</b> A point at position r on "
        "a spinning body moves at ω × r (school physics). The body's axes "
        "are R's columns, so their tips move at ω<sub>s</sub> × x̂<sub>b</sub>, "
        "ω<sub>s</sub> × ŷ<sub>b</sub>, ω<sub>s</sub> × ẑ<sub>b</sub>. R's "
        "columns are the axes, so Ṙ's columns are how fast the axes move:"))
    c.add(math_label(
        r"\dot R=\left[\ \omega_s\times\hat x_b\ \ \ \omega_s\times\hat y_b\ \ \ "
        r"\omega_s\times\hat z_b\ \right]", 16))
    c.add(body(
        "9 numbers, all made from the same 3 — that is '9 numbers, only 3 "
        "free' once more.<br>"
        "<b>Layer 3, one product does it all.</b> 'Cross with ω' is linear, "
        "so it is a matrix, [ω] (the bracket). It holds no new information, "
        "just ω's three numbers rearranged so that [ω]v = ω × v:"))
    c.add(body(f"<table style='font-family:Consolas'>"
               f"<tr><td style='padding:2px 12px'>0</td><td style='padding:2px 12px'>−ω<sub>z</sub></td>"
               f"<td style='padding:2px 12px'>ω<sub>y</sub></td></tr>"
               f"<tr><td style='padding:2px 12px'>ω<sub>z</sub></td><td style='padding:2px 12px'>0</td>"
               f"<td style='padding:2px 12px'>−ω<sub>x</sub></td></tr>"
               f"<tr><td style='padding:2px 12px'>−ω<sub>y</sub></td><td style='padding:2px 12px'>ω<sub>x</sub></td>"
               f"<td style='padding:2px 12px'>0</td></tr></table>"
               f"<span style='color:{theme.TEXT_DIM}'>[ω]: skew-symmetric "
               f"([ω]ᵀ = −[ω]). The set of all such matrices is so(3).</span>"))
    c.add(body(
        "A matrix times a matrix acts on each column separately, so "
        "[ω<sub>s</sub>]R = [ [ω<sub>s</sub>]x̂<sub>b</sub>  [ω<sub>s</sub>]ŷ<sub>b</sub>  "
        "[ω<sub>s</sub>]ẑ<sub>b</sub> ] = the three tip velocities = Ṙ. "
        "<b>Ṙ = [ω<sub>s</sub>]R</b> is shorthand for 'cross each body axis "
        "with the spin'."))
    c.add(math_label(
        r"\omega_s\ (3\ \mathrm{numbers})\ \longrightarrow\ [\omega_s]\ "
        r"(\mathrm{cross\ machine})\ \longrightarrow\ [\omega_s]R=\dot R\ "
        r"(\mathrm{tip\ velocities})", 15))
    c.add(body(
        "<b>Rows or columns?</b> You compute any matrix product row by row "
        "(that is just how the arithmetic goes), but you <i>read</i> it by "
        "columns, as always on these pages. Column j of [ω] is [ω]ê<sub>j</sub> "
        "= ω × ê<sub>j</sub>: what the spin does to the s-axis j. Column 1 is "
        "(0, ω<sub>z</sub>, −ω<sub>y</sub>), exactly the glued-arrow tip "
        "velocity in the lab above. Column j of [ω]R is what the spin does "
        "to <i>body</i> axis j. When R = I the two are the same arrows."))
    c.add(body(_grid_table(
        ("body axis (R = I)", "tip velocity ω<sub>s</sub> × axis", "physical check"),
        [("x̂<sub>b</sub> = (1, 0, 0)", "(0, 1.414, 0)",
          "45° from the axis: radius 0.707, speed 2 × 0.707, moves +y"),
         ("ŷ<sub>b</sub> = (0, 1, 0)", "(−1.414, 0, 1.414)",
          "90° from the axis: radius 1, the fastest, speed 2"),
         ("ẑ<sub>b</sub> = (0, 0, 1)", "(0, −1.414, 0)",
          "45° from the axis, on the other side: moves −y")])
        + f"<span style='color:{theme.TEXT_DIM}'>ω<sub>s</sub> = (1.414, 0, 1.414). "
          "Stack the three as columns: that is Ṙ, and it equals [ω<sub>s</sub>]·I. "
          "Tilt the body (R ≠ I) and the columns are different arrows, but the "
          "recipe is the same — the next lab.</span>"))
    return c


def body_space_card() -> Card:
    c = Card("ω_b = Rᵀω_s and [ω_b] = RᵀṘ, one step at a time")
    c.add(body(
        "<b>Step 1. One arrow, two sets of shadows.</b> The spin is one "
        "physical arrow ω. ω<sub>s</sub> lists its shadows on the s-axes; "
        "ω<sub>b</sub> lists its shadows on the body's axes. Same arrow, "
        "different rulers.<br>"
        "<b>Step 2. A shadow is a dot product.</b> The body-x component is "
        "x̂<sub>b</sub> · ω<sub>s</sub> (both written in {s} numbers). "
        "Likewise ŷ<sub>b</sub> · ω<sub>s</sub> and ẑ<sub>b</sub> · "
        "ω<sub>s</sub>.<br>"
        "<b>Step 3. Three dot products = one matrix.</b> x̂<sub>b</sub>, "
        "ŷ<sub>b</sub>, ẑ<sub>b</sub> are R's columns, so they are Rᵀ's "
        "<i>rows</i>. Rᵀω<sub>s</sub> computes exactly those three dot "
        "products. Hence ω<sub>b</sub> = Rᵀω<sub>s</sub>. Since Rᵀ = R⁻¹ = "
        "R<sub>bs</sub>, this is also subscript cancellation: "
        "ω<sub>b</sub> = R<sub>bs</sub>ω<sub>s</sub>.<br>"
        "<b>Step 4. Going back, read by columns.</b> ω<sub>s</sub> = "
        "Rω<sub>b</sub> = ω<sub>b,x</sub>x̂<sub>b</sub> + "
        "ω<sub>b,y</sub>ŷ<sub>b</sub> + ω<sub>b,z</sub>ẑ<sub>b</sub>: rebuild "
        "the arrow from its body shadows, each times its body axis.<br>"
        "<b>Example.</b> R = Rot(ẑ, 90°): x̂<sub>b</sub> = (0, 1, 0), "
        "ŷ<sub>b</sub> = (−1, 0, 0), ẑ<sub>b</sub> = (0, 0, 1). Spin about "
        "x<sub>s</sub>: ω<sub>s</sub> = (1, 0, 0). Shadows: x̂<sub>b</sub>·ω = 0, "
        "ŷ<sub>b</sub>·ω = −1, ẑ<sub>b</sub>·ω = 0, so ω<sub>b</sub> = "
        "(0, −1, 0). Sanity: x<sub>s</sub> points along −y<sub>b</sub>, so a "
        "spin about x<sub>s</sub> is a spin about −y<sub>b</sub> ✓.<br>"
        "<b>Step 5. The matrix forms.</b> Start from Ṙ = [ω<sub>s</sub>]R:"))
    c.add(math_label(
        r"\dot R=[\omega_s]R\quad(\mathrm{multiply\ by}\ R^T\ \mathrm{on\ the\ right})"
        r"\quad\Rightarrow\quad\dot RR^T=[\omega_s]", 15))
    c.add(math_label(
        r"R^T\dot R=R^T[\omega_s]R=[R^T\omega_s]=[\omega_b]"
        r"\qquad\Rightarrow\qquad \dot R=R\,[\omega_b]", 15))
    c.add(body(
        "The middle step uses one fact: Rᵀ[ω]R = [Rᵀω]. In words: 'cross with "
        "ω, but with everything turned into body numbers' is the same as "
        "'cross with ω written in body numbers', because rotating two "
        "arrows rotates their cross product too. So ṘRᵀ gives the spin in "
        "{s} numbers and RᵀṘ the spin in {b} numbers — the two skew matrices "
        "from differentiating RRᵀ = I and RᵀR = I. Ṙ = [ω<sub>s</sub>]R "
        "(spin on the left = space axes) and Ṙ = R[ω<sub>b</sub>] (spin on "
        "the right = body axes): page 118's pre/post-multiply rule again."))
    return c


class BodySpaceCard:
    """Same spin arrow: shadows on the s-axes vs shadows on the b-axes."""

    def __init__(self):
        c = self.card = Card("lab: one spin arrow, measured with {s} rulers and with {b} rulers")
        self.s_y = labelled_slider(c, "body turned about z_s", -180, 180, 90, deg, self._draw)
        self.s_p = labelled_slider(c, "then about its own y", -90, 90, 0, deg, self._draw)
        self.s_az = labelled_slider(c, "spin axis azimuth", -180, 180, 0, deg, self._draw)
        self.s_el = labelled_slider(c, "spin axis elevation", -90, 90, 0, deg, self._draw)
        self.txt = body("")
        c.add(self.txt)
        self.st_s = Stat("ω_s", "--", theme.WARN)
        self.st_b = Stat("ω_b = Rᵀω_s", "--", theme.VIOLET)
        self.st_back = Stat("‖R ω_b − ω_s‖", "--", theme.GOOD)
        self.st_m = Stat("‖RᵀṘ − [ω_b]‖", "--", theme.GOOD)
        c.add_layout(stat_row(self.st_s, self.st_b, self.st_back, self.st_m))
        self.cv = MplCanvas(width=7.4, height=3.6)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "Defaults are the worked example: body turned 90° about z, spin "
            "about x<sub>s</sub> at 1 rad/s → ω<sub>b</sub> = (0, −1, 0). "
            "<b>Try:</b> set the body turn to 0: the two lists agree, "
            "because the rulers agree. Point the spin axis along one body "
            "axis: ω<sub>b</sub> has a single nonzero entry while ω<sub>s</sub> "
            "may have several. The arrow (orange) never changes when you turn "
            "the body — only its body shadows do."))
        self._draw()

    def _draw(self, *_):
        R = rotz(math.radians(self.s_y.value())) @ roty(math.radians(self.s_p.value()))
        ws = _unit(math.radians(self.s_az.value()), math.radians(self.s_el.value()))
        wb = R.T @ ws
        Rdot = rk.skew(ws) @ R
        self.st_s.set(_vec(ws))
        self.st_b.set(_vec(wb))
        self.st_back.set(f"{np.linalg.norm(R @ wb - ws):.0e}")
        self.st_m.set(f"{np.linalg.norm(R.T @ Rdot - rk.skew(wb)):.0e}")
        lines = "".join(
            f"{nm}·ω<sub>s</sub> = {_vec(R[:, i])}·{_vec(ws)} = <b>{wb[i]:+.2f}</b><br>"
            for i, nm in enumerate(("x̂<sub>b</sub>", "ŷ<sub>b</sub>", "ẑ<sub>b</sub>")))
        self.txt.setText("Body shadows, one dot product each:<br>" + lines)
        _clear(self.cv)
        ax = self.cv.ax
        _frame3d(ax, np.eye(3), alpha=0.3, lw=1.2, name="_s")
        _frame3d(ax, R, lw=3, name="_b")
        ax.quiver(0, 0, 0, *(1.2 * ws), color=theme.WARN, lw=3, arrow_length_ratio=0.15)
        _cube(ax, 1.3)
        ax.set_title("faint: {s}   bold: {b}   orange: the spin arrow ω")
        self.cv.refresh()


class AngularVelocityCard:
    """Pick an orientation and an angular velocity; see Rdot = [w_s] R."""

    def __init__(self):
        c = self.card = Card("lab: spin a frame — tip velocities, Ṙ = [ω_s]R, and ω_s vs ω_b")
        self.s_o = labelled_slider(c, "current orientation (turn about (1,1,0))", -180, 180, 50,
                                   deg, self._draw)
        self.s_az = labelled_slider(c, "spin axis azimuth", -180, 180, 0, deg, self._draw)
        self.s_el = labelled_slider(c, "spin axis elevation", -90, 90, 90, deg, self._draw)
        self.s_rate = labelled_slider(c, "spin rate θ̇", -20, 20, 10,
                                      lambda v: f"{v/10:+.1f} rad/s", self._draw)
        self.txt = body("")
        c.add(self.txt)
        self.st_ws = Stat("ω_s (in {s})", "--", theme.WARN)
        self.st_wb = Stat("ω_b = Rᵀω_s (in {b})", "--", theme.VIOLET)
        self.st_fd = Stat("‖Ṙ measured − [ω_s]R‖", "--", theme.GOOD)
        self.st_sk = Stat("‖RᵀṘ + (RᵀṘ)ᵀ‖", "--", theme.GOOD)
        c.add_layout(stat_row(self.st_ws, self.st_wb, self.st_fd, self.st_sk))
        self.cv = MplCanvas(width=7.4, height=3.8)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "Orange dashed: the spin axis ω̂. Thin arrows at the tips of "
            "{b}'s axes: their velocities ω × axis. 'Ṙ measured' is computed "
            "by actually turning the frame a tiny bit forward and back and "
            "dividing; it agrees with [ω<sub>s</sub>]R to ~10⁻⁸ (that is "
            "rounding). The skew check reads zero: RᵀṘ really is "
            "skew-symmetric. <b>Try:</b> point the spin axis straight up "
            "(elevation 90°): ω<sub>s</sub> = (0, 0, θ̇) in {s}, but "
            "ω<sub>b</sub> has three nonzero entries, because {b} is tilted — "
            "same arrow, other numbers. Then turn the axis to lie along one "
            "of {b}'s axes: that axis's tip arrow disappears (an axis does "
            "not move when you spin about it), and the other two tips move "
            "fastest when the spin axis is perpendicular to them. Flip the "
            "rate's sign: every arrow reverses (right-hand rule)."))
        self._draw()

    def _draw(self, *_):
        R = rk.rot_exp(np.array([1, 1, 0]) / math.sqrt(2) * math.radians(self.s_o.value()))
        w_hat = _unit(math.radians(self.s_az.value()), math.radians(self.s_el.value()))
        ws = w_hat * self.s_rate.value() / 10
        Rdot = rk.skew(ws) @ R
        h = 1e-6
        fd = (rk.rot_exp(ws * h) @ R - rk.rot_exp(-ws * h) @ R) / (2 * h)
        wb = R.T @ ws
        self.st_ws.set(_vec(ws))
        self.st_wb.set(_vec(wb))
        self.st_fd.set(f"{np.linalg.norm(fd - Rdot):.0e}")
        self.st_sk.set(f"{np.linalg.norm(R.T @ Rdot + (R.T @ Rdot).T):.0e}")
        self.txt.setText(
            "<table><tr><td>[ω<sub>s</sub>] =</td><td>" + mat_html(rk.skew(ws), 2)
            + "</td><td style='padding-left:20px'>Ṙ = [ω<sub>s</sub>]R =</td><td>"
            + _cols_html(Rdot, 2) + "</td></tr></table>"
            "<span style='color:" + theme.TEXT_DIM + "'>Column i of Ṙ is the "
            "velocity of the tip of {b}'s axis i: the arrows in the picture.</span>")
        _clear(self.cv)
        ax = self.cv.ax
        _frame3d(ax, np.eye(3), alpha=0.15, lw=1)
        _frame3d(ax, R, name="_b", lw=3)
        for i in range(3):
            tip, v = R[:, i], 0.5 * Rdot[:, i]
            ax.quiver(*tip, *v, color=AX_COLS[i], lw=1.4, arrow_length_ratio=0.25)
        ax.plot(*[[-1.3 * w_hat[i], 1.3 * w_hat[i]] for i in range(3)], "--",
                color=theme.WARN, lw=2)
        _cube(ax, 1.3)
        ax.set_title("bold: {b}   arrows: tip velocities (½ scale)   dashed: ω̂")
        self.cv.refresh()


# ==========================================================================
# 3.2.3  exponential coordinates, part 1: the matrix exponential
# ==========================================================================

class ExpSeriesCard:
    """e^{at} and e^{[w]theta} as series: how many terms until it is R?"""

    def __init__(self):
        c = self.card = Card("from ẋ = ax to e^{[ω̂]θ}: the matrix exponential, term by term")
        c.add(body(
            "<b>1. Three numbers again.</b> Any orientation can be reached "
            "from {s} by <i>one</i> turn: some unit axis ω̂ by some angle θ. "
            "Multiply them: the 3-vector ω̂θ (direction = axis, length = "
            "angle) is the <b>exponential coordinates</b> of the orientation. "
            "Three numbers, an alternative to the 9 of R.<br>"
            "<b>2. Why 'exponential'.</b> Read ω̂ as an angular velocity of "
            "1 rad/s, kept up for θ seconds. The final orientation is what "
            "you get by integrating that motion from the start. Integrating "
            "a constant-coefficient linear ODE is what exponentials do:<br>"
            "<b>3. One variable.</b> ẋ = a x has solution x(t) = e<sup>at</sup>x(0), "
            "with e<sup>at</sup> = 1 + at + (at)²/2! + (at)³/3! + …<br>"
            "<b>4. Many variables.</b> ẋ = A x with x an n-vector and A a "
            "constant n×n matrix has the same solution with the same series; "
            "only now the powers are matrix powers. That series is the "
            "<b>matrix exponential</b> e<sup>At</sup>. For rotations A will be "
            "[ω̂], so the answer is e<sup>[ω̂]θ</sup>."))
        c.add(math_label(
            r"\dot x=Ax\ \Rightarrow\ x(t)=e^{At}x(0),\qquad "
            r"e^{At}=I+At+\frac{(At)^2}{2!}+\frac{(At)^3}{3!}+\cdots", 16))
        c.add(body(
            "<b>5. Why it collapses for rotations.</b> For a unit axis, "
            "[ω̂]³ = −[ω̂]. So every power folds back onto [ω̂] or [ω̂]²; "
            "collect the terms and the scalar series that remain are exactly "
            "sin θ and 1 − cos θ:"))
        c.add(math_label(
            r"e^{[\hat\omega]\theta}=I+\left(\theta-\frac{\theta^3}{3!}+\cdots\right)[\hat\omega]"
            r"+\left(\frac{\theta^2}{2!}-\frac{\theta^4}{4!}+\cdots\right)[\hat\omega]^2"
            r"=I+\sin\theta\,[\hat\omega]+(1-\cos\theta)[\hat\omega]^2", 14))
        self.s_th = labelled_slider(c, "angle θ", 0, 360, 120, deg, self._draw)
        self.s_n = labelled_slider(c, "series terms kept N", 1, 20, 4, str, self._draw)
        self.st_err = Stat("‖partial sum − Rodrigues‖", "--", theme.BAD)
        self.st_det = Stat("det(partial sum)", "--", theme.VIOLET)
        self.st_orth = Stat("‖SᵀS − I‖ of partial sum", "--", theme.WARN)
        c.add_layout(stat_row(self.st_err, self.st_det, self.st_orth))
        self.cv = MplCanvas(width=8.2, height=3.4, ncols=2)
        c.add(self.cv)
        c.add(plain(
            "Left: the error of the matrix series after N terms (log scale), "
            "the current N circled. Right: the scalar e<sup>θ</sup> "
            "(a = 1, t = θ in radians) with its N-term polynomial, so you "
            "can see the matrix behaves like the familiar number. "
            "<b>Try:</b> at θ = 120° four terms are still visibly wrong (and "
            "the partial sum is not even a rotation: the orthogonality and "
            "det stats are off). Raise N: by 11 terms the error is about "
            "10⁻⁴, by 20 about 10⁻¹². Bigger θ needs more terms. "
            "Rodrigues' formula (next video) is the closed form, so code "
            "never sums the series."))
        self._draw()

    def _draw(self, *_):
        th = math.radians(self.s_th.value())
        N = self.s_n.value()
        w = np.array([1.0, 2.0, 2.0]) / 3
        A = rk.skew(w) * th
        exact = rk.rot_exp(w * th)
        errs, S, term = [], np.zeros((3, 3)), np.eye(3)
        for k in range(20):
            S = S + term
            errs.append(np.linalg.norm(S - exact))
            if k + 1 == N:
                SN = S.copy()
            term = term @ A / (k + 1)
        self.st_err.set(f"{errs[N - 1]:.1e}")
        self.st_det.set(f"{np.linalg.det(SN):.3f}")
        self.st_orth.set(f"{np.linalg.norm(SN.T @ SN - np.eye(3)):.1e}")
        self.cv.clear()
        a1, a2 = self.cv.axes
        ks = np.arange(1, 21)
        a1.semilogy(ks, np.maximum(errs, 1e-17), "o-", color=theme.ACCENT, ms=3)
        a1.semilogy([N], [max(errs[N - 1], 1e-17)], "o", ms=12, mfc="none",
                    color=theme.WARN, mew=2)
        a1.set_xlabel("terms kept N")
        a1.set_ylabel("error")
        a1.set_title("matrix series → e^[ω̂]θ")
        t = np.linspace(0, 2 * math.pi, 200)
        a2.plot(t, np.exp(t), color=theme.GOOD, lw=2, label="e^θ")
        poly = sum(t ** k / math.factorial(k) for k in range(N))
        a2.plot(t, poly, "--", color=theme.WARN, lw=1.6, label=f"{N} terms")
        a2.axvline(th, color=theme.TEXT_FAINT, lw=1)
        a2.set_ylim(0, 560)
        a2.set_xlabel("θ (rad)")
        a2.set_title("scalar e^θ, same truncation")
        self.cv.legend(a2, loc="upper left")
        self.cv.refresh()


# ==========================================================================
# 3.2.3  exponential coordinates, part 2: integrate, Rodrigues, log
# ==========================================================================

class IntegrateCard:
    """p-dot = [w]p: little straight steps vs the exponential."""

    def __init__(self):
        c = self.card = Card("integrate ṗ = ω̂ × p yourself: small steps vs the exponential")
        c.add(body(
            "Follow just one axis of the frame; call it p (the other two "
            "behave the same way). Spinning about the unit axis ω̂ at 1 rad/s, "
            "its tip runs round a circle and its velocity is tangent: "
            "ṗ = ω̂ × p = [ω̂]p. That is ẋ = Ax with A = [ω̂], so after θ "
            "seconds p(θ) = e<sup>[ω̂]θ</sup>p(0). Apply that to all three "
            "axes at once and the matrix of axes goes from I to "
            "R = e<sup>[ω̂]θ</sup>: <b>exponentiating integrates the angular "
            "velocity</b>.<br>The lab integrates the same equation the "
            "naive way, with N straight steps p ← p + Δt·[ω̂]p, and compares.", ))
        self.s_th = labelled_slider(c, "angle θ (= time at 1 rad/s)", 0, 360, 270, deg, self._draw)
        self.s_n = labelled_slider(c, "straight steps N", 3, 200, 12, str, self._draw)
        self.st_err = Stat("endpoint error, steps vs exp", "--", theme.BAD)
        self.st_len = Stat("‖p‖ after steps (should be 1)", "--", theme.WARN)
        self.st_exp = Stat("‖p‖ after exp", "--", theme.GOOD)
        c.add_layout(stat_row(self.st_err, self.st_len, self.st_exp))
        self.cv = MplCanvas(width=7.4, height=3.8)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "Green: the exact circle from e<sup>[ω̂]θ</sup>. Red: the "
            "straight-step path. Every straight step leaves along the "
            "tangent, so it lands slightly <i>outside</i> the circle; the "
            "errors pile up and p grows longer than 1, which no rotation "
            "can do. <b>Try:</b> N = 12 at 270°: p ends more than twice as "
            "long as it started. N = 200: still about 4% too long — better, "
            "never exact. The exponential needs no steps and keeps |p| = 1 "
            "to rounding."))
        c.add(link_back("117", (
            "This is the dashed tangent line on page 117's hoop, run in a "
            "loop: a straight velocity step drifts off the constraint "
            "surface, and the gap meter (here ‖p‖ − 1, for R it is "
            "‖RᵀR − I‖) creeps away from zero. Robot code that integrates "
            "orientation with R ← R + Ṙ Δt has this bug. The fix is "
            "R ← R·e<sup>[ω<sub>b</sub>]Δt</sup>: an exact turn per step, so R "
            "stays on SO(3).")))
        self._draw()

    def _draw(self, *_):
        th = math.radians(self.s_th.value())
        N = self.s_n.value()
        w = np.array([0.3, 0.2, 1.0])
        w /= np.linalg.norm(w)
        K = rk.skew(w)
        p0 = np.array([1.0, 0, 0.2])
        p0 /= np.linalg.norm(p0)
        P = [p0]
        dt = th / N
        for _ in range(N):
            P.append(P[-1] + dt * K @ P[-1])
        P = np.array(P)
        exact = np.array([rk.rot_exp(w * t) @ p0 for t in np.linspace(0, th, 100)])
        self.st_err.set(f"{np.linalg.norm(P[-1] - exact[-1]):.3f}")
        self.st_len.set(f"{np.linalg.norm(P[-1]):.3f}")
        self.st_exp.set(f"{np.linalg.norm(exact[-1]):.6f}")
        _clear(self.cv)
        ax = self.cv.ax
        ax.plot(*[[-1.3 * w[i], 1.3 * w[i]] for i in range(3)], "--", color=theme.WARN, lw=2)
        ax.plot(exact[:, 0], exact[:, 1], exact[:, 2], color=theme.GOOD, lw=2.5)
        ax.plot(P[:, 0], P[:, 1], P[:, 2], "o-", color=theme.BAD, lw=1.2, ms=2.5)
        for q, col in ((exact[-1], theme.GOOD), (P[-1], theme.BAD)):
            ax.plot([0, q[0]], [0, q[1]], [0, q[2]], color=col, lw=2.2)
        _cube(ax, 1.3)
        ax.set_title("green: e^[ω̂]θ p(0)   red: N straight steps   dashed: ω̂")
        self.cv.refresh()


class AxisAngleCard:
    """Rodrigues forward, matrix log back."""

    def __init__(self):
        c = self.card = Card("Rodrigues and the matrix log: axis-angle → R → axis-angle")
        c.add(body(
            "<b>Rodrigues' formula</b> is the closed form of the series: give "
            "it the exponential coordinates ω̂θ (as the skew matrix [ω̂]θ) and "
            "it returns the rotation matrix. <b>The matrix log</b> runs it "
            "backwards: give it R and it returns [ω̂]θ, the axis and the "
            "angle that reach R from the identity. Exponential ≈ "
            "integration (velocity and time → where you end up); log ≈ "
            "differentiation (where you ended up → which constant velocity "
            "and how long)."))
        c.add(math_label(
            r"\mathrm{Rot}(\hat\omega,\theta)=e^{[\hat\omega]\theta}"
            r"=I+\sin\theta\,[\hat\omega]+(1-\cos\theta)[\hat\omega]^2,"
            r"\qquad \log R=[\hat\omega]\theta,\ \ \cos\theta=\frac{\mathrm{tr}R-1}{2}", 15))
        self.sa = labelled_slider(c, "axis azimuth", -180, 180, 30, deg, self._draw)
        self.se = labelled_slider(c, "axis elevation", -90, 90, 50, deg, self._draw)
        self.st = labelled_slider(c, "angle θ", -180, 180, 110, deg, self._draw)
        self.R_txt = body("")
        c.add(self.R_txt)
        self.st_det = Stat("det R", "--", theme.GOOD)
        self.st_orth = Stat("‖RᵀR − I‖", "--", theme.GOOD)
        self.st_log = Stat("θ from log R", "--", theme.ACCENT)
        self.st_ax = Stat("axis from log R", "--", theme.WARN)
        c.add_layout(stat_row(self.st_det, self.st_orth, self.st_log, self.st_ax))
        self.cv = MplCanvas(width=7.4, height=3.6)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "Point the axis (dashed), choose θ. Faint lines: {s}; bold: the "
            "turned frame; dotted: the path of the x-axis tip during the turn. "
            "det stays 1 and the orthogonality error is ~10⁻¹⁶: Rodrigues "
            "always lands on SO(3). <b>Try:</b> a negative θ. The log reports "
            "a positive angle and the <i>opposite</i> axis: −110° about ω̂ is "
            "the same R as +110° about −ω̂, and the log always picks θ in "
            "[0°, 180°]. At exactly 180° both axis signs give the same R, so "
            "the log has to choose one — the single awkward spot of these "
            "three numbers."))
        c.add(link_back("116", (
            "ω̂θ is an <b>explicit</b> representation: 3 numbers for 3 DOF. "
            "Page 116 said every 3-number chart of SO(3) must misbehave "
            "somewhere; for this one the trouble is mild and lives only at "
            "θ = 180° (and the jump from 180° to −180°, which is the same "
            "seam a joint angle has). So: compute with R (implicit, no bad "
            "spots), and use log R when you need 3 numbers for a short "
            "while — an orientation error for a controller, or one joint's "
            "turn. <b>Preview of chapter 4:</b> for a revolute joint, ω̂ is "
            "the joint axis and θ is the joint angle, so each joint's "
            "rotation is literally e<sup>[ω̂]θ</sup>.")))
        self._draw()

    def _draw(self, *_):
        w = _unit(math.radians(self.sa.value()), math.radians(self.se.value()))
        th = math.radians(self.st.value())
        R = rk.rot_exp(w * th)
        self.R_txt.setText("R = e<sup>[ω̂]θ</sup> =" + _cols_html(R, 3))
        self.st_det.set(f"{np.linalg.det(R):.6f}")
        self.st_orth.set(f"{np.linalg.norm(R.T @ R - np.eye(3)):.1e}")
        lg = rk.rot_log(R)
        n = np.linalg.norm(lg)
        self.st_log.set(f"{math.degrees(n):.1f}°")
        self.st_ax.set(_vec(lg / n) if n > 1e-9 else "any")
        _clear(self.cv)
        ax = self.cv.ax
        _frame3d(ax, np.eye(3), alpha=0.2, lw=1.4)
        _frame3d(ax, R, name="", lw=3)
        ax.plot(*[[-w[i], w[i]] for i in range(3)], "--", color=theme.WARN, lw=2)
        arc = np.array([rk.rot_exp(w * t) @ np.array([1.0, 0, 0])
                        for t in np.linspace(0, th, 40)])
        ax.plot(arc[:, 0], arc[:, 1], arc[:, 2], ":", color=theme.BAD, lw=1.4)
        _cube(ax)
        ax.set_title("faint: {s}   bold: e^[ω̂]θ   dashed: ω̂")
        self.cv.refresh()


# ==========================================================================
# 3.3.1  homogeneous transformation matrices
# ==========================================================================

def transform_card() -> Card:
    c = Card("T = (R, p) in one 4×4 matrix: SE(3), its properties, its three uses")
    c.add(body(
        "<b>1. Packing.</b> To place {b} in {s} you need two things, both "
        "in {s} numbers: p, where {b}'s origin is, and R, which way its "
        "axes point. Put R top-left, p top-right, and a bottom row "
        "(0, 0, 0, 1) that is only there to make the algebra work (point 4). "
        "The result is the <b>homogeneous transformation matrix</b> T. The "
        "set of all of them is the <b>special Euclidean group SE(3)</b>."))
    c.add(body(_block_html("R (3×3)", "p (3×1)", "0 0 0", "1")
               + "<span style='color:" + theme.TEXT_DIM + "'>T = [[R, p], [0, 1]]."
               " T<sub>sb</sub> = {b} as seen from {s}.</span>"))
    c.add(body(
        "<b>2. Properties, the same list as for R.</b> Every T has an "
        "inverse, T⁻¹ = [[Rᵀ, −Rᵀp], [0, 1]] (rotate back, then undo the "
        "shift written in the new axes); a product of two T's is a T; "
        "multiplication is associative but not commutative.<br>"
        "<b>3. Three uses, the same list as for R.</b> (a) <i>represent</i> "
        "a configuration: T<sub>sb</sub>; T<sub>bs</sub> = T<sub>sb</sub>⁻¹ "
        "(swapping subscripts inverts). (b) <i>change the reference "
        "frame</i>: T<sub>sb</sub>T<sub>bc</sub> = T<sub>sc</sub>, subscripts "
        "cancel; walking back, T<sub>cs</sub> = T<sub>bc</sub>⁻¹T<sub>sb</sub>⁻¹. "
        "(c) <i>displace</i> a point or frame (the lab after next).<br>"
        "<b>4. Why the extra row and the extra 1.</b> T<sub>sb</sub> is 4×4 "
        "but a point p<sub>b</sub> has 3 numbers: the product does not even "
        "fit. Append a 1 to the point, (p<sub>b</sub>, 1): its "
        "<b>homogeneous coordinates</b>. Then T·(p<sub>b</sub>, 1) = "
        "(R p<sub>b</sub> + p, 1): rotate, then shift, in one product. "
        "The bottom row keeps the 1 a 1, so products chain."))
    c.add(math_label(
        r"(p_s,\,1)=T_{sb}\,(p_b,\,1)\quad\Leftrightarrow\quad "
        r"p_s=R_{sb}\,p_b+p_{sb}", 16))
    c.add(link_back("115, 116", (
        "<b>115:</b> a rigid body in space has m = 6 freedoms. T has 12 "
        "meaningful numbers (9 in R, 3 in p) and 6 rules (RᵀR = I), "
        "12 − 6 = 6. SE(3) <i>is</i> the C-space of one free body, ℝ³ × SO(3): "
        "the flat ℝ³ for position, the curved SO(3) for orientation. "
        "<b>116:</b> T is an implicit representation, chosen for the same "
        "reason as R — no bad spots. The position part p is plain explicit "
        "numbers because ℝ³ is flat; only the orientation needed the "
        "implicit trick.")))
    return c


class HomogeneousCard:
    """Top view: T_sb from (yaw, p); a point in {b} numbers mapped into {s}."""

    def __init__(self):
        c = self.card = Card("lab: one point, two frames, and the 1 at the end")
        c.add(body(
            "Seen from above (z out of the screen). The first three sliders "
            "place {b}: turn ψ about z, origin at (x, y). The next two set a "
            "point in <b>{b} numbers</b>. Tick the box to append 0 instead of "
            "1: that turns the point into a <b>direction</b> (a free "
            "vector), which should turn with the frame but not shift with "
            "it.", dim=True))
        self.s_psi = labelled_slider(c, "ψ ({b} turned about z)", -180, 180, 40, deg, self._draw)
        self.s_x = labelled_slider(c, "{b} origin x", -20, 20, 12, lambda v: f"{v/10:+.1f}", self._draw)
        self.s_y = labelled_slider(c, "{b} origin y", -20, 20, 6, lambda v: f"{v/10:+.1f}", self._draw)
        self.s_bx = labelled_slider(c, "point p_b x", -15, 15, 10, lambda v: f"{v/10:+.1f}", self._draw)
        self.s_by = labelled_slider(c, "point p_b y", -15, 15, 5, lambda v: f"{v/10:+.1f}", self._draw)
        self.chk = QCheckBox("append 0, not 1 (treat it as a direction, not a point)")
        self.chk.toggled.connect(self._draw)
        c.add(self.chk)
        self.txt = body("")
        c.add(self.txt)
        self.st_ps = Stat("p_s", "--", theme.GOOD)
        self.st_back = Stat("T_sb⁻¹ · p_s → p_b again", "--", theme.ACCENT)
        c.add_layout(stat_row(self.st_ps, self.st_back))
        self.cv = MplCanvas(width=7.0, height=3.8)
        c.add(self.cv)
        c.add(plain(
            "The orange dot is one place in space. Its numbers in {b} are "
            "the sliders; its numbers in {s} come out of T<sub>sb</sub>·(p, 1). "
            "<b>Try:</b> move {b}'s origin: p<sub>s</sub> moves by exactly "
            "that much (the shift column at work). Turn ψ: the point swings "
            "with {b}. Tick the box: now moving the origin changes nothing — "
            "a direction like 'forward' or a velocity has no location, so "
            "the 0 switches off the shift column. The 'back' stat applies "
            "T<sub>sb</sub>⁻¹ = T<sub>bs</sub> and recovers p<sub>b</sub>: "
            "inverse = swap subscripts."))
        self._draw()

    def _draw(self, *_):
        psi = math.radians(self.s_psi.value())
        T = rk.rp_to_T(rotz(psi), [self.s_x.value() / 10, self.s_y.value() / 10, 0])
        w = 0.0 if self.chk.isChecked() else 1.0
        pb = np.array([self.s_bx.value() / 10, self.s_by.value() / 10, 0, w])
        ps = T @ pb
        back = rk.inv_T(T) @ ps
        self.txt.setText(
            "<table><tr><td>T<sub>sb</sub> =</td><td>" + mat_html(T, 2)
            + "</td><td style='padding-left:16px'>·</td><td>" + mat_html(pb[:, None], 2)
            + "</td><td>=</td><td>" + mat_html(ps[:, None], 2) + "</td></tr></table>")
        self.st_ps.set(_vec(ps[:3], 2))
        self.st_back.set(_vec(back[:3], 2))
        self.cv.clear()
        ax = self.cv.ax
        _frame2d(ax, np.eye(4), 0.8, name="{s}")
        _frame2d(ax, T, 0.8, name="{b}")
        if w:
            ax.plot(ps[0], ps[1], "o", color=theme.WARN, ms=10)
            ax.plot([T[0, 3], ps[0]], [T[1, 3], ps[1]], ":", color=theme.WARN)
            ax.plot([0, ps[0]], [0, ps[1]], ":", color=theme.TEXT_FAINT)
        else:
            for o in (np.zeros(2), T[:2, 3]):
                ax.annotate("", xy=o + ps[:2], xytext=o,
                            arrowprops=dict(arrowstyle="-|>", color=theme.WARN, lw=2))
        _square2d(ax, (-3, 3.5), (-2.5, 3))
        ax.set_title("orange: the point (or, with 0, the direction)")
        self.cv.refresh()


class LeftRightCard:
    """Video 3.3.1's example: T = Trans(2 along y) Rot(z, 90 deg), on either side of T_sb."""

    T0 = rk.rp_to_T(rotz(math.radians(30)), [1.0, 0.5, 0])

    def __init__(self):
        c = self.card = Card("use 3: displace a frame — T on the left vs T on the right")
        c.add(body(
            "Any configuration can be reached from the start by first "
            "rotating, then translating. The video's T: rotate 90° about ẑ, "
            "translate 2 along ŷ. Where do ẑ and ŷ point? <b>It depends on "
            "the side</b>, by the same rule as for rotations:<br>"
            "• <b>T·T<sub>sb</sub></b> (left): ω̂ and p are read in the "
            "<b>first</b> subscript's frame, {s}. {b} first swings 90° about "
            "z<sub>s</sub> (a vertical line through {s}'s origin), then slides "
            "2 along y<sub>s</sub>. Result {b′}.<br>"
            "• <b>T<sub>sb</sub>·T</b> (right): ω̂ and p are read in the "
            "<b>second</b> subscript's frame, {b}, and the order flips: first "
            "slide 2 along {b}'s own y, then spin 90° about {b}'s own z, "
            "which travelled with the frame. Result {b″}."))
        c.add(math_label(
            r"T=\mathrm{Trans}(2\hat y)\,\mathrm{Rot}(\hat z,90^\circ),\qquad "
            r"T_{sb'}=T\,T_{sb}\ (\mathrm{space\ axes}),\qquad "
            r"T_{sb''}=T_{sb}\,T\ (\mathrm{body\ axes})", 14))
        self.combo = QComboBox()
        for k in ("both", "left only: T · T_sb", "right only: T_sb · T"):
            self.combo.addItem(k)
        self.combo.currentIndexChanged.connect(self._draw)
        c.add(self.combo)
        self.s_t = labelled_slider(c, "animation progress", 0, 100, 100,
                                   lambda v: f"{v}%", self._draw)
        self.txt = body("")
        c.add(self.txt)
        self.cv = MplCanvas(width=7.4, height=4.0)
        c.add(self.cv)
        c.add(plain(
            "Drag the progress slider slowly from 0. <b>Left (blue path):</b> "
            "the first half swings {b} round {s}'s origin — a big arc, "
            "because the axis is far away — then it slides straight 'up' "
            "the page (y<sub>s</sub>). <b>Right (violet path):</b> the first "
            "half slides along {b}'s own green axis, tilted 30°, then {b} "
            "spins in place about its own z, which came along for the ride. "
            "Same T, two different end frames {b′} and {b″}. Remember it "
            "once: <b>left = space-frame recipe, right = body-frame "
            "recipe</b>. Forward kinematics (page 121) uses both forms."))
        self._draw()

    def _path(self, s, left):
        T0 = self.T0
        rot = lambda a: rk.rp_to_T(rotz(a), [0, 0, 0])
        tr = lambda d: rk.rp_to_T(np.eye(3), [0, d, 0])
        if left:
            if s <= 0.5:
                return rot(math.pi / 2 * s / 0.5) @ T0
            return tr(2 * (s - 0.5) / 0.5) @ rot(math.pi / 2) @ T0
        if s <= 0.5:
            return T0 @ tr(2 * s / 0.5)
        return T0 @ tr(2) @ rot(math.pi / 2 * (s - 0.5) / 0.5)

    def _draw(self, *_):
        s = self.s_t.value() / 100
        mode = self.combo.currentIndex()
        self.cv.clear()
        ax = self.cv.ax
        _frame2d(ax, np.eye(4), 0.7, name="{s}", alpha=0.6)
        _frame2d(ax, self.T0, 0.7, name="{b}", alpha=0.45)
        rows = []
        for left, col, nm in ((True, theme.ACCENT, "{b′}"), (False, theme.VIOLET, "{b″}")):
            if (mode == 1 and not left) or (mode == 2 and left):
                continue
            path = np.array([self._path(u, left)[:2, 3] for u in np.linspace(0, s, 60)])
            ax.plot(path[:, 0], path[:, 1], color=col, lw=2, alpha=0.8)
            T = self._path(s, left)
            _frame2d(ax, T, 0.7, name=nm if s > 0.99 else None)
            rows.append(f"<td style='padding-right:20px'>{nm} = "
                        f"{'T·T_sb' if left else 'T_sb·T'} =</td><td>{mat_html(T, 2)}</td>")
        if mode != 2 and 0 < s <= 0.5:      # left: first half turns about z_s
            ax.plot(0, 0, "o", color=theme.WARN, ms=9, mfc="none", mew=2)
        if mode != 1 and s > 0.5:           # right: second half turns about z_b
            o = self._path(s, False)[:2, 3]
            ax.plot(o[0], o[1], "o", color=theme.WARN, ms=9, mfc="none", mew=2)
        self.txt.setText("<table><tr>" + "".join(rows) + "</tr></table>"
                         "<span style='color:" + theme.TEXT_DIM + "'>Orange ring: the "
                         "point the current rotation turns about.</span>")
        _square2d(ax, (-3.2, 2.5), (-1.2, 3.8))
        ax.set_title("blue: T on the left (space axes)   violet: T on the right (body axes)")
        self.cv.refresh()


# ==========================================================================
# 3.3.2  twists, part 1
# ==========================================================================

def twist_card() -> Card:
    c = Card("a rigid body's velocity is a screw: S = (S_ω, S_v), twist V = S θ̇")
    c.add(body(
        "<b>1. Same trick as for ω.</b> Ṫ has 12 moving numbers but a body "
        "has 6 velocity freedoms, so Ṫ is not the representation; just as "
        "Ṙ was not.<br>"
        "<b>2. The fact the whole chapter hangs on.</b> Any instantaneous "
        "rigid-body velocity — any mix of spinning and sliding — is the "
        "same as turning about some line in space while sliding along that "
        "line. A <b>screw motion</b>. The line is the <b>screw axis</b>, "
        "fixed by: a point q on it, a unit direction ŝ, and a <b>pitch</b> "
        "h = (speed along the axis) ÷ (turn rate about it). θ̇ says how fast "
        "you turn.<br>"
        "<b>3. Stored differently.</b> (q, ŝ, h) is a nice picture but "
        "awkward to compute with. Instead choose a reference frame and "
        "store the 6-vector S = (S<sub>ω</sub>, S<sub>v</sub>), both in that "
        "frame's numbers, for a turn rate of θ̇ = 1:<br>"
        "&nbsp;&nbsp;S<sub>ω</sub> = ŝ, the angular velocity;<br>"
        "&nbsp;&nbsp;S<sub>v</sub> = the linear velocity of the point of the "
        "body that is at the frame's <b>origin</b>. It has two parts: "
        "hŝ (sliding along the axis) and −ŝ × q (being carried round the "
        "axis, because the origin is a distance |q| away from it)."))
    c.add(math_label(
        r"\mathcal{S}=(\mathcal{S}_\omega,\ \mathcal{S}_v)"
        r"=(\hat s,\ -\hat s\times q+h\hat s),"
        r"\qquad \mathcal{V}=\mathcal{S}\,\dot\theta=(\omega,\ v)", 16))
    c.add(body(
        "<b>4. Infinite pitch.</b> A pure slide has no turning, so "
        "h = speed/0 = ∞. Then S<sub>ω</sub> = 0, S<sub>v</sub> is a unit "
        "vector along the slide, and θ̇ is the linear speed (m/s) instead of a "
        "turn rate (rad/s). So: either ‖S<sub>ω</sub>‖ = 1, or S<sub>ω</sub> = 0 "
        "and ‖S<sub>v</sub>‖ = 1.<br>"
        "<b>5. The twist.</b> V = S θ̇ is the full velocity: angular part "
        "ω and linear part v. Written in {b} numbers it is the <b>body "
        "twist</b> V<sub>b</sub>; in {s} numbers, the <b>spatial twist</b> "
        "V<sub>s</sub>. Same motion, two descriptions. In both, v means the "
        "velocity of the body point currently at <i>that frame's origin</i> — "
        "for V<sub>s</sub> that is often an imaginary point far outside the "
        "real body. V<sub>b</sub> does not care where {s} is; V<sub>s</sub> "
        "does not care where {b} is."))
    c.add(link_back("117", (
        "On page 117 a velocity q̇ of the joints was a list of rates. For a "
        "free body the 'coordinates' are T, an implicit representation, so "
        "the velocity is not Ṫ but a 6-vector in the tangent space of SE(3), "
        "exactly as ω was the 3-vector in the tangent space of SO(3). "
        "6 = 12 numbers − 6 differentiated rules.")))
    return c


class TurntableCard:
    """Video 3.3.2's turntable: same screw, written in frames at different places."""

    def __init__(self):
        c = self.card = Card("lab: the turntable — one motion, S in three different frames")
        c.add(body(
            "A turntable spins about a vertical axis through the world "
            "origin, coming out of the screen; pitch 0 (pure turning). Place "
            "a reference frame {r} anywhere (sliders) and read S in its "
            "numbers. The violet arrow is S<sub>v</sub>: the velocity, at "
            "θ̇ = 1, of the turntable point sitting under {r}'s origin. "
            "Video defaults: {r} 2 units left of the axis.", dim=True))
        self.s_x = labelled_slider(c, "{r} origin x", -30, 30, -20, lambda v: f"{v/10:+.1f}", self._draw)
        self.s_y = labelled_slider(c, "{r} origin y", -30, 30, 0, lambda v: f"{v/10:+.1f}", self._draw)
        self.s_phi = labelled_slider(c, "{r} turned in the plane", -180, 180, 0, deg, self._draw)
        self.chk = QCheckBox("tip {r} so its y-axis points INTO the screen (video's last case)")
        self.chk.toggled.connect(self._draw)
        c.add(self.chk)
        self.s_th = labelled_slider(c, "turntable angle θ", 0, 360, 30, deg, self._draw)
        self.st_w = Stat("S_ω in {r}", "--", theme.WARN)
        self.st_v = Stat("S_v in {r}", "--", theme.VIOLET)
        self.st_d = Stat("‖S_v‖ = distance to axis", "--", theme.ACCENT)
        c.add_layout(stat_row(self.st_w, self.st_v, self.st_d))
        self.cv = MplCanvas(width=7.0, height=4.0)
        c.add(self.cv)
        c.add(plain(
            "<b>Check the video's three cases.</b> (1) Default, {r} at "
            "(−2, 0): S<sub>ω</sub> = (0, 0, 1) and S<sub>v</sub> = (0, −2, 0): "
            "the disc under {r} moves 2 units/s in −y. (2) Move {r} anywhere "
            "else: S<sub>ω</sub> is unchanged, S<sub>v</sub> is not — it "
            "always has length 'distance from the axis' and points round the "
            "circle. (3) Set x = y = 0 and tick the box: {r} sits on the axis "
            "so S<sub>v</sub> = 0, and because {r}'s y-axis now points into "
            "the screen, the same upward spin reads S<sub>ω</sub> = (0, −1, 0). "
            "The motion never changed; only the frame that describes it. "
            "That is the whole meaning of 'a twist is written in some "
            "frame'. Spin θ: S does not change, because the axis is fixed."))
        self._draw()

    def _draw(self, *_):
        o = np.array([self.s_x.value() / 10, self.s_y.value() / 10, 0])
        R = rotz(math.radians(self.s_phi.value()))
        if self.chk.isChecked():
            R = R @ rotx(-math.pi / 2)
        T_wr = rk.rp_to_T(R, o)
        S_w = np.array([0, 0, 1.0, 0, 0, 0])
        S_r = rk.adjoint(rk.inv_T(T_wr)) @ S_w
        self.st_w.set(_vec(S_r[:3], 1))
        self.st_v.set(_vec(S_r[3:], 2))
        self.st_d.set(f"{np.linalg.norm(S_r[3:]):.2f}")
        self.cv.clear()
        ax = self.cv.ax
        t = np.linspace(0, 2 * math.pi, 200)
        ax.fill(3.2 * np.cos(t), 3.2 * np.sin(t), color=theme.BORDER, alpha=0.35)
        th = math.radians(self.s_th.value())
        for k in range(6):
            a = th + k * math.pi / 3
            ax.plot([0, 3.2 * math.cos(a)], [0, 3.2 * math.sin(a)], color=theme.TEXT_FAINT, lw=0.8)
        ax.plot(3.0 * math.cos(th), 3.0 * math.sin(th), "s", color=theme.CYAN, ms=8)
        ax.plot(0, 0, "o", color=theme.WARN, ms=12, mfc="none", mew=2)
        ax.plot(0, 0, ".", color=theme.WARN, ms=6)
        ax.text(0.15, -0.45, "axis (out of screen)", color=theme.WARN, fontsize=8)
        r = np.linalg.norm(o[:2])
        if r > 1e-6:
            ax.plot(r * np.cos(t), r * np.sin(t), ":", color=theme.VIOLET, lw=1)
        vel = np.cross([0, 0, 1.0], o)
        ax.annotate("", xy=o[:2] + 0.5 * vel[:2], xytext=o[:2],
                    arrowprops=dict(arrowstyle="-|>", color=theme.VIOLET, lw=2.5))
        for i in range(3):
            d = R[:, i]
            if abs(d[2]) > 0.9:
                ax.plot(*o[:2], "x" if d[2] < 0 else "o", color=AX_COLS[i], ms=11,
                        mew=2.5, mfc="none")
                ax.text(o[0] + 0.15, o[1] + 0.15 + 0.3 * i, f"{'xyz'[i]}_r "
                        f"{'into' if d[2] < 0 else 'out of'} screen",
                        color=AX_COLS[i], fontsize=7)
            else:
                ax.annotate("", xy=o[:2] + 0.8 * d[:2], xytext=o[:2],
                            arrowprops=dict(arrowstyle="-|>", color=AX_COLS[i], lw=2.2))
        _square2d(ax, (-3.6, 3.6), (-3.6, 3.6))
        ax.set_title("violet arrow: S_v (θ̇ = 1), drawn in world directions")
        self.cv.refresh()


# ==========================================================================
# 3.3.2  twists, part 2: the adjoint and se(3)
# ==========================================================================

def adjoint_card() -> Card:
    c = Card("changing a twist's frame (the adjoint), and twists as 4×4 matrices (se(3))")
    c.add(body(
        "<b>1. The cancellation rule almost works.</b> We want "
        "V<sub>a</sub> from V<sub>b</sub>. 'T<sub>ab</sub>V<sub>b</sub>' fails: "
        "T is 4×4, V has 6 entries. We need a 6×6 matrix built from "
        "T<sub>ab</sub>: the <b>adjoint</b> [Ad<sub>T</sub>]. With it the "
        "rule is back: V<sub>a</sub> = [Ad<sub>T<sub>ab</sub></sub>]V<sub>b</sub>."))
    c.add(body(_block_html("R", "0", "[p] R", "R")
               + "<span style='color:" + theme.TEXT_DIM + "'>[Ad<sub>T</sub>] for "
               "T = (R, p): each block 3×3. Top row: ω just turns, ω<sub>a</sub> = "
               "Rω<sub>b</sub>. Bottom row: v turns too, plus p × (Rω<sub>b</sub>), "
               "the extra speed a spin produces at a point p away.</span>"))
    c.add(math_label(
        r"\mathcal{V}_a=[\mathrm{Ad}_{T_{ab}}]\,\mathcal{V}_b:\qquad "
        r"\omega_a=R\,\omega_b,\qquad v_a=R\,v_b+p\times(R\,\omega_b)", 15))
    c.add(body(
        "<b>2. Matrix form, as for ω.</b> Angular velocity had a matrix "
        "form: [ω<sub>b</sub>] = R⁻¹Ṙ and [ω<sub>s</sub>] = ṘR⁻¹. Twists have "
        "one too, from T:"))
    c.add(math_label(
        r"[\mathcal{V}_b]=T^{-1}\dot T,\qquad [\mathcal{V}_s]=\dot T\,T^{-1}", 16))
    c.add(body(_block_html("[ω] (3×3 skew)", "v (3×1)", "0 0 0", "0")
               + "<span style='color:" + theme.TEXT_DIM + "'>[V] for V = (ω, v): "
               "a 4×4 matrix in se(3).</span>"))
    c.add(body(
        "Top-left is the skew matrix [ω] you know; top-right is v, the "
        "velocity of the point at the frame's origin; bottom row all zeros. "
        "The set of these 4×4 matrices is <b>se(3)</b>, little se, named "
        "after SE(3) as so(3) was after SO(3). The bracket is now "
        "<b>overloaded</b>: [ω] (3×3) for a 3-vector, [V] (4×4) for a "
        "6-vector. Which one is meant is clear from what is inside. These "
        "matrices are what the rigid-body exponential takes, next video."))
    c.add(plain(
        "Why the [p]R block? Stand on a merry-go-round 2 m from the centre. "
        "In the centre's frame the ride only spins. In your frame you are "
        "also being carried sideways at 2 m × ω. The adjoint adds that "
        "'carried by the spin' velocity whenever you move a twist to a frame "
        "whose origin is somewhere else. In the turntable lab this is exactly "
        "how S<sub>v</sub> appeared: the code there computes S in {r} as "
        "[Ad<sub>T<sub>rw</sub></sub>]·(0, 0, 1, 0, 0, 0)."))
    return c


# ==========================================================================
# 3.3.3  exponential coordinates of rigid-body motion
# ==========================================================================

def analogy_card() -> Card:
    c = Card("rotations → rigid-body motions: the same story with one more row")
    c.add(body(
        "Video 3.3.3 is video 3.2.3 again, with S in place of ω̂. Read the "
        "table across: every right-hand entry is the left-hand idea with "
        "position added."))
    c.add(body(_grid_table(
        ("", "rotations (pages 118–119)", "rigid-body motions (this page)"),
        [("configuration", "R ∈ SO(3), 3×3", "T ∈ SE(3), 4×4"),
         ("unit velocity", "unit axis ω̂", "screw axis S: ‖S<sub>ω</sub>‖ = 1, "
                                          "or S<sub>ω</sub> = 0 and ‖S<sub>v</sub>‖ = 1"),
         ("how far", "θ = angle turned", "θ = angle turned (or distance slid, "
                                         "if pure translation)"),
         ("exponential coordinates", "ω̂θ ∈ ℝ³", "Sθ ∈ ℝ⁶"),
         ("matrix form", "[ω̂]θ ∈ so(3), 3×3 skew", "[S]θ ∈ se(3), 4×4"),
         ("velocity from config.", "[ω<sub>s</sub>] = ṘR⁻¹", "[V<sub>s</sub>] = ṪT⁻¹"),
         ("exp", "so(3) → SO(3) (Rodrigues)", "se(3) → SE(3)"),
         ("log", "SO(3) → so(3)", "SE(3) → se(3)"),
         ("change frame", "ω<sub>s</sub> = Rω<sub>b</sub>",
          "V<sub>s</sub> = [Ad<sub>T</sub>]V<sub>b</sub>")])))
    c.add(body(
        "<b>Closed forms.</b> Pure slide (S<sub>ω</sub> = 0): orientation "
        "unchanged, position = S<sub>v</sub>·θ. With turning "
        "(‖S<sub>ω</sub>‖ = 1): rotation part is plain Rodrigues; position "
        "part is a matrix G(θ) times S<sub>v</sub>:"))
    c.add(math_label(
        r"e^{[\mathcal{S}]\theta}:\quad R=e^{[\omega]\theta},\qquad "
        r"p=\left(I\theta+(1-\cos\theta)[\omega]+(\theta-\sin\theta)[\omega]^2\right)v", 15))
    c.add(body(
        "<b>Which side?</b> To move {b} (at T<sub>sb</sub>) by θ along a "
        "screw: if S is written in {b} numbers, multiply on the "
        "<b>right</b>, T<sub>sb</sub>e<sup>[S<sub>b</sub>]θ</sup>; if in {s} "
        "numbers, on the <b>left</b>, e<sup>[S<sub>s</sub>]θ</sup>T<sub>sb</sub>. "
        "The same left/right rule as for T and R. <b>Why it matters:</b> every "
        "1-DOF joint is a screw — revolute h = 0, prismatic h = ∞, helical "
        "finite h — so chapter 4's forward kinematics is one exponential per "
        "joint, multiplied together."))
    return c


class ScrewCard:
    """A frame twisting along a screw: helix, e^[S]theta, log, and T^-1 Tdot."""

    def __init__(self):
        c = self.card = Card("lab: ride a screw — pitch, exponential, log, and V_b = T⁻¹Ṫ")
        c.add(body(
            "The frame starts at {s} (T = I) and twists about the orange "
            "screw axis at θ̇ = 1. The cyan curve is its origin's path. "
            "θ = 180° and 360° are the video's 'time π' and 'time 2π' "
            "snapshots.", dim=True))
        self.s_qx = labelled_slider(c, "axis point q_x", -15, 15, 8, lambda v: f"{v/10:+.1f}", self._draw)
        self.s_qy = labelled_slider(c, "axis point q_y", -15, 15, 0, lambda v: f"{v/10:+.1f}", self._draw)
        self.s_tilt = labelled_slider(c, "axis tilt from vertical", -60, 60, 0, deg, self._draw)
        self.s_h = labelled_slider(c, "pitch h (m per rad)", -30, 30, 10,
                                   lambda v: f"{v/100:+.2f}", self._draw)
        self.chk = QCheckBox("infinite pitch: pure translation (θ becomes metres, 1 m per 90°)")
        self.chk.toggled.connect(self._draw)
        c.add(self.chk)
        self.s_th = labelled_slider(c, "θ", 0, 720, 180, deg, self._draw)
        self.txt = body("")
        c.add(self.txt)
        self.st_S = Stat("S = (S_ω; S_v) in {s}", "--", theme.WARN)
        self.st_log = Stat("log T → θ", "--", theme.ACCENT)
        self.st_vb = Stat("V_b = Ad(T⁻¹)S", "--", theme.VIOLET)
        self.st_fd = Stat("‖T⁻¹Ṫ − [V_b]‖", "--", theme.GOOD)
        c.add_layout(stat_row(self.st_S, self.st_log, self.st_vb, self.st_fd))
        self.cv = MplCanvas(width=7.4, height=4.0)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try in this order.</b> (1) Pitch 0: a revolute joint. The "
            "origin swings on a flat circle round the axis, and "
            "S<sub>v</sub> = −ŝ × q. (2) Raise the pitch: the circle becomes "
            "a helix, climbing h·θ per turn — a screw going into wood. "
            "(3) Tick infinite pitch: S<sub>ω</sub> = 0, S<sub>v</sub> = ŝ, "
            "and the frame slides without turning (a prismatic joint). "
            "(4) Push θ past 180°: 'log T → θ' stops following and comes back "
            "down. The log returns the <i>shortest</i> screw to the same "
            "pose, with rotation angle in [0°, 180°] — for a revolute joint "
            "360° and 0° are the same pose, so log cannot tell them apart. "
            "With pitch it returns a different screw that still lands on T. "
            "(5) The last stat measures T⁻¹Ṫ numerically and compares with "
            "[V<sub>b</sub>]: zero, so the 4×4 velocity formula is right. "
            "V<sub>b</sub> changes as the frame twists, S (written in {s}) "
            "never does."))
        self._draw()

    def _draw(self, *_):
        q = np.array([self.s_qx.value() / 10, self.s_qy.value() / 10, 0])
        s = rotx(math.radians(self.s_tilt.value())) @ np.array([0, 0, 1.0])
        trans = self.chk.isChecked()
        if trans:
            S = np.r_[np.zeros(3), s]
            th = self.s_th.value() / 90
        else:
            S = rk.screw_axis(q, s, self.s_h.value() / 100)
            th = math.radians(self.s_th.value())
        T = rk.exp6(S, th)
        Vb = rk.adjoint(rk.inv_T(T)) @ S
        h = 1e-6
        Tdot = (rk.exp6(S, th + h) - rk.exp6(S, th - h)) / (2 * h)
        fd = np.linalg.norm(rk.inv_T(T) @ Tdot - rk.twist_hat(Vb))
        Sl, thl = rk.log6(T)
        self.st_S.set(_vec(S[:3], 1) + "; " + _vec(S[3:], 2))
        self.st_log.set(f"{thl:.2f} m" if np.linalg.norm(Sl[:3]) < 1e-9
                        else f"{math.degrees(thl):.0f}°")
        self.st_vb.set(_vec(Vb[:3], 1) + "; " + _vec(Vb[3:], 1))
        self.st_fd.set(f"{fd:.0e}")
        self.txt.setText("e<sup>[S]θ</sup> = " + mat_html(T, 2))
        _clear(self.cv)
        ax = self.cv.ax
        a0, a1 = q - 1.5 * s, q + 1.5 * s
        if not trans:
            ax.plot([a0[0], a1[0]], [a0[1], a1[1]], [a0[2], a1[2]], color=theme.WARN, lw=2.5)
        else:
            ax.quiver(0, 0, 0, *(1.2 * s), color=theme.WARN, lw=2.5)
        path = np.array([rk.exp6(S, t)[:3, 3] for t in np.linspace(0, th, 120)])
        ax.plot(path[:, 0], path[:, 1], path[:, 2], color=theme.CYAN, lw=2)
        _frame3d(ax, np.eye(3), scale=0.6, alpha=0.35, lw=1.4)
        for t in np.linspace(0, th, 5)[1:-1]:
            Ti = rk.exp6(S, t)
            _frame3d(ax, Ti[:3, :3], Ti[:3, 3], scale=0.45, alpha=0.3, lw=1)
        _frame3d(ax, T[:3, :3], T[:3, 3], scale=0.7, lw=3)
        _cube(ax, 1.5)
        ax.set_title("orange: screw axis   cyan: origin path   bold: e^[S]θ")
        self.cv.refresh()


class ScrewTwoFramesCard:
    """Same screw in {s} and {b} numbers: right-multiply S_b, left-multiply S_s."""

    T_SB = rk.rp_to_T(rotz(math.radians(40)), [1.6, 0.6, 0])

    def __init__(self):
        c = self.card = Card("lab: one screw, two sets of numbers, two sides of T_sb")
        c.add(body(
            "A hinge (vertical screw axis, pitch 0) through point q swings "
            "{b}. Write the axis in {s} numbers, S<sub>s</sub>, and in {b} "
            "numbers, S<sub>b</sub> = [Ad<sub>T<sub>bs</sub></sub>]S<sub>s</sub>. "
            "Three candidate answers are drawn:<br>"
            "• blue: e<sup>[S<sub>s</sub>]θ</sup>T<sub>sb</sub> (space numbers, "
            "left) — correct;<br>"
            "• cyan dashed: T<sub>sb</sub>e<sup>[S<sub>b</sub>]θ</sup> (body "
            "numbers, right) — correct;<br>"
            "• red: e<sup>[S<sub>b</sub>]θ</sup>T<sub>sb</sub> (body numbers on "
            "the wrong side) — the classic bug.", dim=True))
        self.s_qx = labelled_slider(c, "hinge point q_x (in {s})", -20, 30, 5,
                                    lambda v: f"{v/10:+.1f}", self._draw)
        self.s_qy = labelled_slider(c, "hinge point q_y (in {s})", -20, 30, 20,
                                    lambda v: f"{v/10:+.1f}", self._draw)
        self.s_th = labelled_slider(c, "θ", -180, 180, 70, deg, self._draw)
        self.st_ss = Stat("S_s", "--", theme.ACCENT)
        self.st_sb = Stat("S_b", "--", theme.CYAN)
        self.st_ok = Stat("blue vs cyan", "--", theme.GOOD)
        self.st_bad = Stat("red is off by", "--", theme.BAD)
        c.add_layout(stat_row(self.st_ss, self.st_sb, self.st_ok, self.st_bad))
        self.cv = MplCanvas(width=7.0, height=4.0)
        c.add(self.cv)
        c.add(plain(
            "Blue and cyan always coincide: one physical screw, described "
            "twice, used on the matching side. Red puts {b}-numbers where "
            "{s}-numbers belong, so it swings about the wrong hinge point "
            "(drawn as a red ×: the point that has q's {b}-coordinates "
            "but read in {s}). <b>Try:</b> move q onto {b}'s origin "
            "(1.6, 0.6): S<sub>b</sub>'s linear part becomes 0 and {b} "
            "spins in place. The red one still flies off, round {s}'s origin. "
            "This is the space-form vs body-form choice of page 121."))
        self._draw()

    def _draw(self, *_):
        q = np.array([self.s_qx.value() / 10, self.s_qy.value() / 10, 0])
        th = math.radians(self.s_th.value())
        Ss = rk.screw_axis(q, [0, 0, 1])
        Sb = rk.adjoint(rk.inv_T(self.T_SB)) @ Ss
        A = rk.exp6(Ss, th) @ self.T_SB
        B = self.T_SB @ rk.exp6(Sb, th)
        C = rk.exp6(Sb, th) @ self.T_SB
        self.st_ss.set(_vec(Ss[3:], 2) + " lin.")
        self.st_sb.set(_vec(Sb[3:], 2) + " lin.")
        self.st_ok.set(f"differ by {np.linalg.norm(A - B):.0e}")
        self.st_bad.set(f"{np.linalg.norm(C[:3, 3] - A[:3, 3]):.2f} m")
        self.cv.clear()
        ax = self.cv.ax
        _frame2d(ax, np.eye(4), 0.6, name="{s}", alpha=0.6)
        _frame2d(ax, self.T_SB, 0.6, name="{b}", alpha=0.4)
        ax.plot(q[0], q[1], "x", color=theme.ACCENT, ms=12, mew=3)
        qb = rk.inv_T(self.T_SB) @ np.r_[q, 1]
        ax.plot(qb[0], qb[1], "x", color=theme.BAD, ms=10, mew=2)
        for M, col, ls in ((A, theme.ACCENT, "-"), (C, theme.BAD, "-")):
            S_use = Ss if M is A else Sb
            arc = np.array([(rk.exp6(S_use, t) @ self.T_SB)[:2, 3]
                            for t in np.linspace(0, th, 50)])
            ax.plot(arc[:, 0], arc[:, 1], ls, color=col, lw=1.2, alpha=0.7)
        _frame2d(ax, A, 0.7)
        _frame2d(ax, C, 0.7, alpha=0.6)
        o = B[:2, 3]
        ax.plot(o[0], o[1], "o", color=theme.CYAN, ms=14, mfc="none", mew=2, ls="--")
        ax.text(A[0, 3] + 0.1, A[1, 3] + 0.15, "blue = cyan", color=theme.ACCENT, fontsize=8)
        ax.text(C[0, 3] + 0.1, C[1, 3] + 0.15, "red (wrong)", color=theme.BAD, fontsize=8)
        _square2d(ax, (-3.5, 4.5), (-3, 4))
        ax.set_title("× blue: real hinge q    × red: q's {b}-numbers misread in {s}")
        self.cv.refresh()


# ==========================================================================
# 3.4  wrenches
# ==========================================================================

def wrench_card() -> Card:
    c = Card("a wrench F = (m, f), and why it changes frame with the adjoint transpose")
    c.add(body(
        "<b>1. The question.</b> A robot hand holds an apple; a force-torque "
        "sensor at the wrist reads in its own frame {f}. Knowing the apple's "
        "mass, the direction of gravity and where the apple sits, what does "
        "the sensor read? We need a way to write forces and torques, and to "
        "move them between frames.<br>"
        "<b>2. Force and moment.</b> A force f<sub>b</sub> (3 numbers, in "
        "{b}) acting along a line through the point r<sub>b</sub> creates a "
        "moment (torque) about {b}'s origin: m<sub>b</sub> = r<sub>b</sub> × "
        "f<sub>b</sub>. Stack them, moment first: the 6-vector "
        "<b>wrench</b> F<sub>b</sub> = (m<sub>b</sub>, f<sub>b</sub>). Same "
        "packing as the twist (ω, v): angular thing on top, linear below.<br>"
        "<b>3. The one fact used.</b> Twist · wrench = power: "
        "VᵀF = ω·m + v·f (watts). Power is physical — a motor either "
        "spends 5 W or it does not — so it cannot depend on which frame "
        "you write V and F in:"))
    c.add(math_label(
        r"\mathcal{V}_b^T\mathcal{F}_b=\mathcal{V}_s^T\mathcal{F}_s", 16))
    c.add(body(
        "<b>4. Derive the rule in three lines.</b> Change the twist's frame "
        "with the adjoint, use (AB)ᵀ = BᵀAᵀ, and notice the result must hold "
        "for <i>every</i> twist V<sub>s</sub>, so the two vectors it is "
        "dotted with must be equal:"))
    c.add(math_label(
        r"\mathcal{V}_s^T\mathcal{F}_s=\mathcal{V}_b^T\mathcal{F}_b="
        r"\left([\mathrm{Ad}_{T_{bs}}]\mathcal{V}_s\right)^T\mathcal{F}_b="
        r"\mathcal{V}_s^T\left([\mathrm{Ad}_{T_{bs}}]^T\mathcal{F}_b\right)"
        r"\ \Rightarrow\ \mathcal{F}_s=[\mathrm{Ad}_{T_{bs}}]^T\mathcal{F}_b", 15))
    c.add(body(
        "Twists go across with Ad, wrenches with Adᵀ <b>of the reverse "
        "transform</b>. Written out: f just turns, f<sub>s</sub> = "
        "R<sub>sb</sub>f<sub>b</sub>; the moment turns and picks up the lever "
        "arm, m<sub>s</sub> = R<sub>sb</sub>m<sub>b</sub> + p<sub>sb</sub> × "
        "f<sub>s</sub>. That is 'moment = r × f' from school, applied to the "
        "shift between the two origins."))
    c.add(link_back("117", (
        "Page 117 said a constraint force Aᵀλ does no work because the "
        "allowed motions satisfy A q̇ = 0: power = q̇ᵀAᵀλ = (A q̇)ᵀλ = 0. "
        "That was this card's argument in joint coordinates — a force paired "
        "with a velocity through a dot product, and the dot product (power) "
        "as the thing that is physical. On page 123 the same argument, with "
        "the Jacobian in place of Ad, gives τ = JᵀF.")))
    return c


class AppleCard:
    """Video 3.4's apple: gravity in the apple frame, read by the wrist sensor."""

    def __init__(self):
        c = self.card = Card("lab: what does the wrist sensor read when the hand holds an apple?")
        c.add(body(
            "Frame {a} sits at the apple's centre of mass with y<sub>a</sub> "
            "up. There gravity is simply F<sub>a</sub> = (0, 0, 0, 0, −mg, 0): "
            "no moment, since the force passes through {a}'s origin. The "
            "sensor frame {f} sits a distance L from the apple along its own "
            "x-axis and can be tilted (wrist angle). Then "
            "F<sub>f</sub> = [Ad<sub>T<sub>af</sub></sub>]ᵀF<sub>a</sub>.",
            dim=True))
        self.s_m = labelled_slider(c, "apple mass m", 5, 50, 20, lambda v: f"{v/100:.2f} kg", self._draw)
        self.s_L = labelled_slider(c, "distance L", 2, 30, 10, lambda v: f"{v} cm", self._draw)
        self.s_phi = labelled_slider(c, "wrist angle (tilt of {f})", -90, 90, 0, deg, self._draw)
        self.txt = body("")
        c.add(self.txt)
        self.st_mz = Stat("moment about z_f", "--", theme.BAD)
        self.st_f = Stat("force (x_f, y_f)", "--", theme.GOOD)
        self.st_p = Stat("power check V·F in {a} vs {f}", "--", theme.ACCENT)
        c.add_layout(stat_row(self.st_mz, self.st_f, self.st_p))
        self.cv = MplCanvas(width=7.0, height=3.8)
        c.add(self.cv)
        c.add(plain(
            "At wrist angle 0 you get the video's answer: moment −mgL about "
            "z<sub>f</sub> and force −mg along y<sub>f</sub>. With m = 0.2 kg "
            "and L = 10 cm: f = −1.96 N, m<sub>z</sub> = −0.196 N·m. "
            "<b>Try:</b> double L — the force is unchanged, the moment "
            "doubles (lever arm). Tilt the wrist to +90° so the apple sits "
            "straight above the sensor: the moment vanishes (gravity's line "
            "now passes through {f}'s origin) and the whole −mg shows up "
            "along −x<sub>f</sub>. The power check pairs one fixed twist with "
            "the wrench in both frames: always the same number. That is the "
            "rule the derivation rested on."))
        self._draw()

    def _draw(self, *_):
        m, L = self.s_m.value() / 100, self.s_L.value() / 100
        phi = math.radians(self.s_phi.value())
        g = 9.81
        R_af = rotz(phi)
        p_af = -L * R_af[:, 0]
        T_af = rk.rp_to_T(R_af, p_af)
        Fa = np.array([0, 0, 0, 0, -m * g, 0])
        Ff = rk.adjoint(T_af).T @ Fa
        Vf = np.array([0.3, -0.2, 0.5, 0.1, 0.4, -0.3])
        Va = rk.adjoint(T_af) @ Vf
        self.st_mz.set(f"{Ff[2]:+.3f} N·m")
        self.st_f.set(f"({Ff[3]:+.2f}, {Ff[4]:+.2f}) N")
        self.st_p.set(f"{Va @ Fa:+.4f} = {Vf @ Ff:+.4f} W")
        self.txt.setText(
            "F<sub>f</sub> = (m<sub>x</sub>, m<sub>y</sub>, m<sub>z</sub>, "
            "f<sub>x</sub>, f<sub>y</sub>, f<sub>z</sub>) = " + _vec(Ff, 3))
        self.cv.clear()
        ax = self.cv.ax
        sc = 1 / max(L, 0.05)
        A = np.zeros(2)
        Fo = p_af[:2] * sc
        ax.plot([Fo[0], A[0]], [Fo[1], A[1]], color=theme.TEXT_DIM, lw=6, alpha=0.6,
                solid_capstyle="round")
        circ = np.linspace(0, 2 * math.pi, 60)
        ax.fill(0.25 * np.cos(circ), 0.25 * np.sin(circ), color=theme.BAD, alpha=0.8)
        ax.annotate("", xy=(0, -0.9), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color=theme.WARN, lw=2.5))
        ax.text(0.08, -0.85, "mg", color=theme.WARN, fontsize=9)
        T2 = np.eye(3)
        T2[:2, :2] = R_af[:2, :2]
        T2[:2, 2] = Fo
        _frame2d(ax, T2, 0.45, name="{f}")
        T2a = np.eye(3)
        _frame2d(ax, T2a, 0.35, alpha=0.5)
        ax.text(0.3, 0.3, "{a}", color=theme.TEXT_DIM, fontsize=9)
        if abs(Ff[2]) > 1e-6:
            a = np.linspace(0.3, 1.9, 30) * (1 if Ff[2] > 0 else -1)
            ax.plot(Fo[0] + 0.35 * np.cos(a), Fo[1] + 0.35 * np.sin(a), color=theme.BAD, lw=2)
        _square2d(ax, (-2, 1.2), (-1.4, 1.4))
        ax.set_title("grey bar: hand from sensor {f} to apple {a} (scaled to L)")
        self.cv.refresh()
