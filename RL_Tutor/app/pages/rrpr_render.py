"""
A solid-looking 3-D drawing of the RRPR workshop arm (page 125).

Every link is a shaded mesh (pedestal, waist turntable, column, shoulder
housing, outer sleeve, telescoping inner tube, roll housing, offset hand with
fingers), and every joint has its own colour, a curved arrow showing which way
+θ turns (right-hand rule about its axis) or a straight arrow for the slide.
All faces go into one Poly3DCollection so matplotlib depth-sorts them together.
"""

from __future__ import annotations

import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import to_rgb

from ctrlcore import robokin as rk
from ctrlcore import rrpr_check as rc
from .. import theme
from .robo_space_rigid import _frame3d

JOINT_COLS = (theme.ORANGE, theme.VIOLET, theme.TEAL, theme.PINK)
JOINT_LABELS = ("θ1 waist", "θ2 shoulder", "d3 slide", "θ4 roll")
LINK = "#7d8a9c"
LINK_DARK = "#4a5566"
HAND = "#c9d1d9"
LIGHT = np.array([-0.35, -0.55, 0.76])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _basis(a):
    a = np.asarray(a, float)
    a = a / np.linalg.norm(a)
    h = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(a, h)
    u /= np.linalg.norm(u)
    return a, u, np.cross(a, u)          # u × v = a


class _Mesh:
    """Collects shaded quads, then adds them to the axes as one collection."""

    def __init__(self):
        self.polys, self.cols = [], []

    def quad(self, pts, col, alpha=1.0):
        pts = np.asarray(pts, float)
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        nn = np.linalg.norm(n)
        f = 0.42 + 0.58 * (abs(n @ LIGHT) / nn if nn > 1e-12 else 0.5)
        r, g, b = to_rgb(col)
        self.polys.append(pts)
        self.cols.append((min(1, r * f), min(1, g * f), min(1, b * f), alpha))

    def cylinder(self, c, axis, r, h, col, n=20, alpha=1.0):
        a, u, v = _basis(axis)
        c = np.asarray(c, float)
        t = np.linspace(0, 2 * np.pi, n + 1)
        ring = [r * (np.cos(x) * u + np.sin(x) * v) for x in t]
        lo, hi = c - 0.5 * h * a, c + 0.5 * h * a
        for k in range(n):
            self.quad([lo + ring[k], lo + ring[k + 1], hi + ring[k + 1], hi + ring[k]], col, alpha)
        for cap in (lo, hi):
            self.polys.append(np.array([cap + p for p in ring[:-1]]))
            r_, g_, b_ = to_rgb(col)
            f = 0.42 + 0.58 * abs(a @ LIGHT)
            self.cols.append((r_ * f, g_ * f, b_ * f, alpha))

    def prism(self, p0, p1, w, side, col, alpha=1.0, depth=None):
        """Box from p0 to p1, cross-section w × depth, one face normal along `side`."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        a = p1 - p0
        L = np.linalg.norm(a)
        if L < 1e-9:
            return
        a /= L
        s = np.asarray(side, float) - (np.asarray(side, float) @ a) * a
        if np.linalg.norm(s) < 1e-9:
            _, s, _ = _basis(a)
        s /= np.linalg.norm(s)
        t = np.cross(a, s)
        d = depth if depth is not None else w
        corners = [0.5 * (i * w * s + j * d * t) for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        bot = [p0 + c for c in corners]
        top = [p1 + c for c in corners]
        for k in range(4):
            self.quad([bot[k], bot[(k + 1) % 4], top[(k + 1) % 4], top[k]], col, alpha)
        self.quad(bot, col, alpha)
        self.quad(top, col, alpha)

    def add_to(self, ax):
        if self.polys:
            pc = Poly3DCollection(self.polys, facecolors=self.cols, edgecolors="none",
                                  linewidths=0)
            ax.add_collection3d(pc)


def _arc(ax, c, axis, r, col, lw, label=None, alpha=1.0, span=1.55 * np.pi, start=0.0):
    a, u, v = _basis(axis)
    t = np.linspace(start, start + span, 48)
    pts = np.array([c + r * (np.cos(x) * u + np.sin(x) * v) for x in t])
    ax.plot(*pts.T, "-", color=col, lw=lw, alpha=alpha, solid_capstyle="round")
    te = t[-1]
    tan = -np.sin(te) * u + np.cos(te) * v
    ax.quiver(*pts[-1], *(0.13 * tan), color=col, lw=lw, alpha=alpha,
              arrow_length_ratio=0.9, normalize=False)
    if label:
        ax.text(*(pts[0] + 0.06 * a), label, color=col, fontsize=9, alpha=alpha,
                fontweight="bold")


def geometry(q):
    """Frames and points needed to draw the arm at q."""
    q = np.asarray(q, float)
    E = [rk.exp6(rc.S_LIST[:, i], q[i]) for i in range(4)]
    T1 = E[0]
    T2 = T1 @ E[1]
    T3 = T2 @ E[2]
    T = rk.fk_space(rc.M_HOME, rc.S_LIST, q)
    shoulder = np.array([0, 0, 1.0])
    arm = T2[:3, :3] @ np.array([1.0, 0, 0])            # arm direction (also roll axis)
    wrist = T3[:3, :3] @ np.array([1.0, 0, 1]) + T3[:3, 3]
    return dict(T1=T1, T2=T2, T3=T3, T=T, shoulder=shoulder, arm=arm, wrist=wrist,
                ax1=np.array([0, 0, 1.0]), ax2=T1[:3, :3] @ np.array([0, -1.0, 0]))


def tool_path(q, joint, n=60):
    """Tool positions when only `joint` sweeps its range."""
    lo, hi = SWEEP[joint](q[joint])
    out = []
    for v in np.linspace(lo, hi, n):
        qq = np.array(q, float)
        qq[joint] = v
        out.append(rk.fk_space(rc.M_HOME, rc.S_LIST, qq)[:3, 3])
    return np.array(out)


SWEEP = (lambda c: (c - 1.2, c + 1.2),
         lambda c: (-0.35, 1.4),
         lambda c: (0.0, 0.6),
         lambda c: (c - np.pi, c + np.pi))


def draw_robot(ax, q, focus=None, show_joints=True, trail=None, T_mine=None, frames=True):
    """The whole arm. focus = joint index to emphasise (0..3) or None."""
    g = geometry(q)
    m = _Mesh()
    R1 = g["T1"][:3, :3]
    sh, arm, wr = g["shoulder"], g["arm"], g["wrist"]

    def jc(i):
        return JOINT_COLS[i]

    # floor tile and pedestal (fixed)
    m.cylinder([0, 0, -0.14], [0, 0, 1], 0.26, 0.24, LINK_DARK)
    # waist: turntable (joint 1 colour) with a notch that shows θ1, then the column
    m.cylinder([0, 0, 0.03], [0, 0, 1], 0.22, 0.06, jc(0))
    m.prism(R1 @ [0.16, 0, 0.065], R1 @ [0.24, 0, 0.065], 0.07, R1 @ [0, 1, 0], HAND, depth=0.03)
    m.prism([0, 0, 0.06], [0, 0, 0.9], 0.15, R1 @ [1, 0, 0], LINK)
    # shoulder housing on joint 2's axis
    m.cylinder(sh, g["ax2"], 0.11, 0.32, jc(1))
    # outer sleeve (part of link 2) and the telescoping inner tube (joint 3)
    sleeve_end = sh + 0.8 * arm
    m.prism(sh, sleeve_end, 0.15, g["ax2"], LINK)
    m.prism(sh + 0.6 * arm, wr, 0.09, g["ax2"], jc(2))
    # roll housing on joint 4's axis
    m.cylinder(wr + 0.07 * arm, arm, 0.1, 0.14, jc(3))
    # hand, rigid with the tool frame {b}: shaft, bracket (off the roll axis), fingers
    T = g["T"]

    def B(p):
        return T[:3, :3] @ np.asarray(p, float) + T[:3, 3]

    m.cylinder(B([-0.27, 0, -0.2]), T[:3, :3] @ [1, 0, 0], 0.045, 0.46, HAND)
    m.prism(B([0, 0, -0.24]), B([0, 0, -0.02]), 0.07, T[:3, :3] @ [1, 0, 0], HAND)
    m.prism(B([-0.02, -0.09, -0.02]), B([-0.02, 0.09, -0.02]), 0.05, T[:3, :3] @ [0, 0, 1], HAND)
    for s in (-1, 1):
        m.prism(B([0, 0.075 * s, -0.02]), B([0, 0.075 * s, 0.12]), 0.035, T[:3, :3] @ [1, 0, 0], HAND)
    m.add_to(ax)

    if show_joints:
        def alpha(i):
            return 1.0 if focus is None or focus == i else 0.3

        def lw(i):
            return 3.2 if focus == i else 2.0
        # long dashed axis lines for the focused joint
        if focus in (0, 1, 3):
            c, a = ((np.zeros(3), g["ax1"]), (sh, g["ax2"]), None, (wr, arm))[focus]
            ax.plot(*np.vstack([c - 0.7 * a, c + 0.9 * a]).T, "--", color=jc(focus), lw=1.4)
        _arc(ax, np.array([0, 0, 0.55]), g["ax1"], 0.27, jc(0), lw(0), "θ1", alpha(0))
        _arc(ax, sh + 0.2 * g["ax2"], g["ax2"], 0.24, jc(1), lw(1), "θ2", alpha(1),
             start=np.pi / 2)
        base = sh + 0.65 * arm + 0.17 * _perp_up(arm)
        ax.quiver(*base, *(0.5 * arm), color=jc(2), lw=lw(2), alpha=alpha(2),
                  arrow_length_ratio=0.25)
        ax.text(*(base + 0.25 * arm + 0.08 * _perp_up(arm)), "d3", color=jc(2), fontsize=9,
                alpha=alpha(2), fontweight="bold")
        _arc(ax, wr + 0.2 * arm, arm, 0.2, jc(3), lw(3), "θ4", alpha(3))
    if trail is not None:
        ax.plot(*trail.T, ":", color=JOINT_COLS[focus] if focus is not None else theme.TEXT, lw=2)
    if frames:
        _frame3d(ax, np.eye(3), (0, 0, -0.02), scale=0.45, name="s", lw=1.6)
        _frame3d(ax, T[:3, :3], T[:3, 3], scale=0.3, name="b" if T_mine is None else None, lw=2.2)
    if T_mine is not None and np.all(np.isfinite(T_mine)) and np.all(np.abs(T_mine[:3, 3]) < 10):
        _frame3d(ax, T_mine[:3, :3], T_mine[:3, 3], scale=0.45, lw=1.5, ls=":", name="′")
        ax.plot(*T_mine[:3, 3], "o", color=theme.TEXT, ms=4)
    style(ax)


def _perp_up(a):
    """A unit vector perpendicular to a, as close to world-up as possible."""
    z = np.array([0, 0, 1.0])
    p = z - (z @ a) * a
    n = np.linalg.norm(p)
    return p / n if n > 1e-6 else np.array([0, 1.0, 0])


def style(ax):
    ax.set_xlim(-1.7, 1.9)
    ax.set_ylim(-1.8, 1.8)
    ax.set_zlim(-0.3, 2.9)
    ax.set_box_aspect((3.6, 3.6, 3.2), zoom=1.2)
    ax.figure.subplots_adjust(left=0, right=1, bottom=0, top=0.95)
    # a faint floor grid at z = -0.26 for depth
    for x in np.linspace(-1.5, 1.5, 7):
        ax.plot([x, x], [-1.5, 1.5], [-0.26, -0.26], color=theme.BORDER, lw=0.6)
        ax.plot([-1.5, 1.5], [x, x], [-0.26, -0.26], color=theme.BORDER, lw=0.6)
