"""
Interactive cards for Modern Robotics chapter 2.3-2.5, the four videos the
C-space pages compressed into a paragraph each:

    2.3.1  C-space topology        TopologyExplorer, AngleWrapCard, why_card
    2.3.2  C-space representation  RepresentationCard, choose_rep_card
    2.4    configuration and velocity constraints
                                   HoopConstraintCard, FourBarCard,
                                   CarConstraintCard, constraint_uses_card
    2.5    task space and workspace
                                   TaskSpaceCard, JointLimitWorkspaceCard

Each class builds one Card (``.card``) and owns the state behind it; the
pages in robo_space.py keep a reference and add the card where it belongs.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QComboBox, QLabel

from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, math_label, stat_row
from .motors import slider, slider_row
from .robo_common import deg, draw_arm, labelled_slider, mat_html, plain, square

TAU = 2 * math.pi


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _style3d(ax):
    ax.set_facecolor(theme.BG_INPUT)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_pane_color((0, 0, 0, 0))
        axis.line.set_color(theme.BORDER)
        axis.label.set_color(theme.TEXT_DIM)
        axis.label.set_fontsize(8)
    ax.tick_params(colors=theme.TEXT_FAINT, labelsize=7)
    ax.title.set_color(theme.TEXT)
    ax.title.set_fontsize(10)


def _layout(canvas: MplCanvas, kinds):
    """Rebuild the canvas' axes; kinds is a list of '2d' / '3d'."""
    fig = canvas.fig
    fig.clear()
    axes = []
    for i, k in enumerate(kinds):
        if k == "3d":
            a = fig.add_subplot(1, len(kinds), i + 1, projection="3d")
            _style3d(a)
        else:
            a = fig.add_subplot(1, len(kinds), i + 1)
            MplCanvas.style(a)
        axes.append(a)
    canvas.axes = axes
    canvas.ax = axes[0]


def _clear(canvas: MplCanvas):
    for a in canvas.axes:
        a.clear()
        if a.name == "3d":
            _style3d(a)
            a.set_axis_off()   # the shapes read better without a 3-D grid box
        else:
            MplCanvas.style(a)


def _row(card: Card, lo, hi, val, on_change, tracking=True):
    """A slider row whose name label can be renamed later."""
    s = slider(lo, hi, val)
    read = QLabel()
    lay = slider_row("", s, read)
    name = lay.itemAt(0).widget()
    card.add_layout(lay)
    s.setTracking(tracking)
    s.valueChanged.connect(on_change)
    return s, name, read


def _info_table(rows) -> str:
    """Two-column HTML table: (label, text)."""
    tr = "".join(
        f"<tr><td style='padding:3px 10px 3px 0; color:{theme.WARN}; "
        f"vertical-align:top; white-space:nowrap'><b>{k}</b></td>"
        f"<td style='padding:3px 0'>{v}</td></tr>" for k, v in rows)
    return f"<table>{tr}</table>"


def _grid_table(head, rows, first_colour=None) -> str:
    th = "".join(f"<th style='padding:3px 10px; color:{theme.TEXT_DIM}; "
                 f"text-align:left'>{h}</th>" for h in head)
    body_rows = ""
    for r in rows:
        cells = ""
        for j, x in enumerate(r):
            col = (first_colour or theme.WARN) if j == 0 else theme.TEXT
            cells += (f"<td style='padding:3px 10px; color:{col}; "
                      f"vertical-align:top'>{x}</td>")
        body_rows += f"<tr>{cells}</tr>"
    return f"<table><tr>{th}</tr>{body_rows}</table>"


def _wrap360(d):
    return d % 360.0


def _broken_line(ax, P, period, color, lw=1.4):
    """Plot a 2-D polyline, breaking it (and marking the break) wherever
    consecutive points jump by more than half a period in any coordinate.
    period is a pair; None means that coordinate never wraps. Returns the
    number of breaks."""
    if len(P) < 2:
        return 0
    seg = [P[0]]
    jumps = 0
    for a, b in zip(P[:-1], P[1:]):
        jump = any(p is not None and abs(b[i] - a[i]) > p / 2
                   for i, p in enumerate(period))
        if jump:
            s = np.array(seg)
            ax.plot(s[:, 0], s[:, 1], "-", color=color, lw=lw)
            ax.plot(*a, "x", color=theme.BAD, ms=8, mew=2)
            ax.plot(*b, "x", color=theme.BAD, ms=8, mew=2)
            ax.annotate("", xy=b, xytext=a,
                        arrowprops=dict(arrowstyle="->", color=theme.BAD,
                                        lw=0.8, ls="--", alpha=0.6))
            seg = [b]
            jumps += 1
        else:
            seg.append(b)
    s = np.array(seg)
    ax.plot(s[:, 0], s[:, 1], "-", color=color, lw=lw)
    return jumps


# ==========================================================================
# 2.3.1  C-space topology: one explorer, six systems
# ==========================================================================

# Each system: the two slider ranges and defaults (b is None for 1-D
# systems), slider names, and the facts shown in the info panel.
_TOPO = {
    "point moving in a plane": dict(
        dim=2, a=(-200, 200, 60, "x (cm)"), b=(-200, 200, 40, "y (cm)"),
        system="A point (a puck, a mobile robot's centre ignoring heading) "
               "free to move anywhere on an unbounded flat plane.",
        topo="<b>E²</b> (ℝ²), the 2-D Euclidean plane: flat, infinite, no "
             "edges and nothing wraps around.",
        rep="Two real numbers <b>(x, y)</b>, once you choose an origin and two "
            "orthogonal axes. Ranges: (−∞, ∞) × (−∞, ∞).",
        seam="None. The coordinate map is one-to-one and smooth everywhere: "
             "moving the point a little always changes (x, y) a little. This "
             "is the only system in the list where the representation has the "
             "same topology as the space itself.",
        use="Nothing special. Subtract coordinates to get an error, average "
            "them, differentiate them: everything from the control pages works "
            "unchanged. This is the baseline the other five systems break.",
        extra="Velocity is just (ẋ, ẏ), the time derivative of the coordinates "
              "— which only works this simply because the space is flat. A "
              "planar body that can also turn is E² × S¹ (3-D), not E²."),
    "spherical pendulum": dict(
        dim=2, a=(-360, 360, 30, "swing angle along path"),
        b=(0, 180, 20, "heading of swing plane"),
        system="A rod pivoting freely about a fixed ball joint at the centre "
               "of a sphere; the bob can be anywhere on the sphere (ignore "
               "spin of the rod about its own axis).",
        topo="<b>S²</b>, the 2-D <b>surface</b> of a sphere, not the solid "
             "ball: the rod has a fixed length, so the bob is always exactly "
             "L from the pivot. (A telescoping rod would fill the solid ball, "
             "a 3-D C-space.) Finite area, no edge, and it closes on itself in "
             "every direction. Not equivalent to the plane — flattening it "
             "needs at least one cut.",
        rep="<b>Latitude</b> ∈ [−90°, 90°] and <b>longitude</b> ∈ [−180°, "
            "180°), like a world map.",
        seam="(1) Longitude jumps by 360° when you cross the date line "
             "(±180°). (2) At the <b>poles</b> longitude is undefined: the "
             "whole top edge of the map is one point (the North Pole) and the "
             "whole bottom edge is the South Pole. Step over a pole and "
             "longitude jumps by 180°. Drag the swing angle past 90° to see "
             "it.",
        use="Do not control or estimate it in latitude/longitude near a pole: "
            "a slow, smooth swing there asks for a huge longitude rate (the "
            "representation lab below). Store the bob direction as a unit "
            "vector (x, y, z) with x² + y² + z² = 1 instead. A pan–tilt camera "
            "tracking a bird that flies straight overhead hits the same wall: "
            "the pan motor has to whip round 180°.",
        extra="These are faults of the <i>map</i>, not the sphere — the "
              "sphere looks the same everywhere. A theorem (the hairy-ball "
              "theorem's cousin) says no single pair of numbers can cover S² "
              "smoothly without a bad point, so any explicit chart has one. "
              "Pilots' gimbals and robot wrists inherit the same problem one "
              "dimension up (SO(3))."),
    "2R robot arm": dict(
        dim=2, a=(-360, 360, 60, "joint 1, θ₁ (deg)"),
        b=(-360, 360, 100, "joint 2, θ₂ (deg)"),
        system="A planar arm with two revolute joints that can spin all the "
               "way round (no joint limits).",
        topo="<b>T² = S¹ × S¹</b>, the surface of a torus (doughnut): each "
             "joint angle is a circle, and two independent circles make a "
             "torus. θ₁ goes the long way round the doughnut, θ₂ around the "
             "tube.",
        rep="Two angles <b>(θ₁, θ₂) ∈ [0, 2π) × [0, 2π)</b>, a square. "
            "Obtained by cutting the torus once (giving a cylinder) and again "
            "(giving a flat square).",
        seam="All four edges of the square. Left edge = right edge (θ₁ = 0 is "
             "θ₁ = 2π) and top = bottom. As the robot moves smoothly through "
             "0 or 2π, the coordinates jump to the opposite edge — the red "
             "crosses on the right panel.",
        use="Joint angles are fine as coordinates: they are the q in "
            "τ = M(q)q̈ + c + g on the dynamics pages. But every angle "
            "<i>difference</i> must be wrapped into (−180°, 180°]: a PID error, "
            "a planner's distance, an interpolated path. Otherwise the arm "
            "turns 340° when 20° would do (the next lab). A grid planner on "
            "this C-space must link the right column to the left column, or it "
            "misses short paths through the seam (page 134).",
        extra="Where the zero of each angle is placed is an arbitrary choice; "
              "it moves the seams but cannot remove them. With joint limits "
              "(say ±150°) the C-space is a closed rectangle [−150°, 150°]², "
              "a different topology with real walls instead of seams. A 6R "
              "arm with no limits has C-space T⁶."),
    "rotating & sliding knob": dict(
        dim=2, a=(-360, 360, 45, "knob angle θ (deg)"),
        b=(-100, 100, 20, "slide distance s (cm)"),
        system="A knob that both turns (revolute joint) and slides along its "
               "shaft (prismatic joint) — like a cylindrical joint, or a "
               "screw with the thread removed.",
        topo="<b>ℝ¹ × S¹</b>, the surface of an infinitely long cylinder: the "
             "slide is a line, the turn is a circle.",
        rep="<b>(s, θ)</b>: one real number s for the slide and one angle θ "
            "∈ [0, 2π). Cutting the cylinder once along its length gives a "
            "flat strip of the plane.",
        seam="Only the angle seam: θ jumps between 0 and 2π. The slide "
             "coordinate s is continuous everywhere (it was never cut).",
        use="Treat the two numbers differently: wrap the angle, never wrap the "
            "slide. Mixed spaces like this one (a mobile base's (x, y, φ) is "
            "another) are where code most often wraps the wrong variable or "
            "forgets to wrap one.",
        extra="A real slider has end stops, which makes s a closed interval "
              "and the C-space a finite cylinder [s_min, s_max] × S¹. A "
              "cylindrical joint (f = 2 in Grübler's formula) has exactly "
              "this C-space."),
    "simple pendulum (1-D)": dict(
        dim=1, a=(-720, 720, 30, "pendulum angle θ (deg)"), b=None,
        system="A rod on a single revolute joint that can swing all the way "
               "over the top.",
        topo="<b>S¹</b>, a circle: one-dimensional, finite length, and it "
             "closes on itself.",
        rep="One angle <b>θ ∈ [0, 2π)</b> on a line segment — the circle cut "
            "once and straightened.",
        seam="θ = 0 and θ = 2π are the same pendulum, but opposite ends of "
             "the segment. Swinging over the top makes the number jump.",
        use="The 1-D version of the 2R lesson: wrap every error. A swing-up "
            "controller must also know that upright reached from the left "
            "(θ = 180°) and from the right (θ = −180°) is the same pose.",
        extra="Controllers must compute angle errors modulo 2π: the error "
              "between 359° and 1° is 2°, not 358°. Using an unwrapped "
              "angle (a real number that keeps counting turns) turns S¹ into "
              "its cover ℝ¹ and fixes the jump, at the price of many numbers "
              "meaning the same pose."),
    "bead on a bounded rod (1-D)": dict(
        dim=1, a=(0, 100, 40, "position s (cm)"), b=None,
        system="A bead sliding along a straight rod with an end stop at each "
               "end (a prismatic joint with limits).",
        topo="<b>A closed interval [a, b]</b> of the line: one-dimensional, "
             "with two genuine boundary points.",
        rep="One real number <b>s ∈ [0, 1 m]</b>.",
        seam="None. The ends of the interval are real physical limits, not "
             "artefacts of the map: the bead stops there instead of "
             "reappearing at the other end. Compare with the pendulum.",
        use="Here the ends are real walls: the controller must slow down and "
            "stop before them (saturate, add limit avoidance), not wrap. A "
            "joint with limits loses the 'go the other way round' option, so "
            "limits change which paths exist, not just how long they are.",
        extra="Circle, line and closed interval are the three topologically "
              "different 1-D C-spaces. All have dimension 1; you cannot "
              "deform one into another without cutting or gluing."),
}


class TopologyExplorer:
    """2.3.1: system / topology / representation for six example systems."""

    def __init__(self):
        c = self.card = Card("explore: same dimension, different shape")
        c.add(body(
            "Pick a system. The three panels always show the same moment: "
            "<b>left</b> the physical system, <b>middle</b> its C-space drawn "
            "as a shape (the topology), <b>right</b> the numbers we use to "
            "describe it (the representation). The grey trail is the recent "
            "motion. Drag a slider steadily past a seam: the path on the "
            "middle shape stays smooth while the path in the right panel "
            "breaks and jumps (red crosses).", dim=True))
        self.combo = QComboBox()
        for k in _TOPO:
            self.combo.addItem(k)
        self.combo.setCurrentIndex(2)
        c.add(self.combo)
        self.sa, self.na, self.ra = _row(c, -360, 360, 0, self._moved)
        self.sb, self.nb, self.rb = _row(c, -360, 360, 0, self._moved)
        self.st_dim = Stat("dimension", "--", theme.ACCENT)
        self.st_top = Stat("topology", "--", theme.VIOLET)
        self.st_jump = Stat("jumps in coordinates", "0", theme.BAD)
        c.add_layout(stat_row(self.st_dim, self.st_top, self.st_jump))
        self.cv = MplCanvas(width=9.6, height=3.5, ncols=3)
        c.add(self.cv)
        self.info = body("")
        c.add(self.info)
        c.add(plain(
            "<b>System</b> = the physical thing. <b>Topology</b> = the shape "
            "of the set of all its poses — what you could tell a blind person "
            "by letting them feel it: does it have edges, does it wrap round, "
            "does it have a hole? <b>Representation</b> = the numbers we "
            "choose to write a pose down. The shape is a fact about the "
            "robot; the numbers are our choice. When the shape wraps around "
            "but the numbers live on a flat sheet, somewhere the numbers must "
            "jump or blow up even though the robot moves smoothly.<br>"
            "<b>Try:</b> 2R arm — drag θ₁ from 300° to past 360° and watch "
            "the right-hand dot leap from the right edge to the left edge. "
            "Spherical pendulum — drag the swing angle past 90° (over the "
            "North Pole) and longitude leaps by 180°. Bead on a rod — the "
            "dot just stops at the ends: real walls, no jump."))
        self.combo.currentIndexChanged.connect(self._system)
        self._busy = False
        self._system()

    # -- system switch ----------------------------------------------------
    def _system(self):
        k = self.combo.currentText()
        d = _TOPO[k]
        self._busy = True
        lo, hi, v, name = d["a"]
        self.sa.setRange(lo, hi)
        self.sa.setValue(v)
        self.na.setText(name)
        has_b = d["b"] is not None
        for w in (self.sb, self.nb, self.rb):
            w.setVisible(has_b)
        if has_b:
            lo, hi, v, name = d["b"]
            self.sb.setRange(lo, hi)
            self.sb.setValue(v)
            self.nb.setText(name)
        self._busy = False
        self.st_dim.set(str(d["dim"]))
        self.st_top.set({"point moving in a plane": "E²",
                         "spherical pendulum": "S²",
                         "2R robot arm": "T² = S¹×S¹",
                         "rotating & sliding knob": "ℝ¹×S¹",
                         "simple pendulum (1-D)": "S¹",
                         "bead on a bounded rod (1-D)": "[a, b]"}[k])
        self.info.setText(_info_table([
            ("System", d["system"]), ("Topology", d["topo"]),
            ("Representation", d["rep"]),
            ("Where the numbers misbehave", d["seam"]),
            ("So what — what you do with it", d["use"]),
            ("Beyond the video", d["extra"])]))
        phys3d = k == "spherical pendulum"
        topo3d = k not in ("simple pendulum (1-D)", "bead on a bounded rod (1-D)")
        _layout(self.cv, ["3d" if phys3d else "2d", "3d" if topo3d else "2d", "2d"])
        self._trail = []
        self._moved()

    # -- geometry of each system -------------------------------------------
    def _readouts(self, k, a, b):
        if k == "point moving in a plane":
            return f"{a/100:+.2f} m", f"{b/100:+.2f} m"
        if k == "rotating & sliding knob":
            return f"{a}°", f"{b/100:+.2f} m"
        if k == "bead on a bounded rod (1-D)":
            return f"{a/100:.2f} m", ""
        return f"{a}°", f"{b}°"

    @staticmethod
    def _sphere_pt(a, b):
        e = np.array([math.cos(math.radians(b)), math.sin(math.radians(b)), 0.0])
        ar = math.radians(a)
        return math.cos(ar) * e + math.sin(ar) * np.array([0, 0, 1.0])

    def _topo_pt(self, k, a, b):
        """Point on the drawn C-space shape (3-D, or 2-D for 1-D systems)."""
        if k == "point moving in a plane":
            return np.array([a / 100, b / 100, 0.0])
        if k == "spherical pendulum":
            return self._sphere_pt(a, b)
        if k == "2R robot arm":
            t1, t2 = math.radians(a), math.radians(b)
            R, r = 2.0, 0.8
            return np.array([(R + r * math.cos(t2)) * math.cos(t1),
                             (R + r * math.cos(t2)) * math.sin(t1),
                             r * math.sin(t2)])
        if k == "rotating & sliding knob":
            t = math.radians(a)
            return np.array([math.cos(t), math.sin(t), b / 100])
        if k == "simple pendulum (1-D)":
            t = math.radians(a)
            return np.array([math.cos(t), math.sin(t)])
        return np.array([a / 100, 0.0])

    def _rep_pt(self, k, a, b):
        """Coordinates as the representation writes them."""
        if k == "point moving in a plane":
            return np.array([a / 100, b / 100])
        if k == "spherical pendulum":
            p = self._sphere_pt(a, b)
            lat = math.degrees(math.asin(max(-1.0, min(1.0, p[2]))))
            lon = math.degrees(math.atan2(p[1], p[0]))
            return np.array([lon, lat])
        if k == "2R robot arm":
            return np.array([_wrap360(a), _wrap360(b)])
        if k == "rotating & sliding knob":
            return np.array([_wrap360(a), b / 100])
        if k == "simple pendulum (1-D)":
            return np.array([_wrap360(a), 0.0])
        return np.array([a / 100, 0.0])

    # -- draw ---------------------------------------------------------------
    def _moved(self, *_):
        if self._busy:
            return
        k = self.combo.currentText()
        a = self.sa.value()
        b = self.sb.value() if _TOPO[k]["b"] is not None else 0
        ra, rb = self._readouts(k, a, b)
        self.ra.setText(ra)
        self.rb.setText(rb)
        self._trail = (self._trail + [(a, b)])[-200:]
        _clear(self.cv)
        a1, a2, a3 = self.cv.axes
        self._draw_physical(a1, k, a, b)
        self._draw_topology(a2, k)
        jumps = self._draw_rep(a3, k)
        self.st_jump.set(str(jumps))
        self.cv.refresh()

    def _draw_physical(self, ax, k, a, b):
        if k == "point moving in a plane":
            ax.plot(a / 100, b / 100, "o", color=theme.WARN, ms=12)
            ax.axhline(0, color=theme.BORDER, lw=1)
            ax.axvline(0, color=theme.BORDER, lw=1)
            ax.set_xlim(-2.2, 2.2)
            ax.set_ylim(-2.2, 2.2)
            ax.set_aspect("equal", adjustable="box")
            ax.set_title("system: point on a plane")
        elif k == "spherical pendulum":
            p = self._sphere_pt(a, b)
            u, v = np.mgrid[0:TAU:24j, 0:math.pi:12j]
            ax.plot_wireframe(np.cos(u) * np.sin(v), np.sin(u) * np.sin(v),
                              np.cos(v), color=theme.BORDER, lw=0.4)
            ax.plot([0, p[0]], [0, p[1]], [0, p[2]], color=theme.CYAN, lw=3)
            ax.scatter([0], [0], [0], color=theme.WARN, s=30)
            ax.scatter([p[0]], [p[1]], [p[2]], color=theme.TEXT, s=60)
            ax.set_box_aspect((1, 1, 1))
            ax.set_title("system: pendulum on a ball joint")
        elif k == "2R robot arm":
            draw_arm(ax, [1.0, 0.8], np.radians([a, b]))
            square(ax, 2.0)
            ax.set_title("system: 2R arm")
        elif k == "rotating & sliding knob":
            s = b / 100
            t = math.radians(a)
            ax.plot([0, 0], [-1.4, 1.4], color=theme.TEXT_FAINT, lw=4)
            e = np.linspace(0, TAU, 80)
            ax.fill(0.6 * np.cos(e), s + 0.18 * np.sin(e), color=theme.ACCENT_DIM,
                    alpha=0.7)
            front = math.sin(t) < 0
            ax.plot(0.6 * math.cos(t), s + 0.18 * math.sin(t), "o",
                    color=theme.WARN if front else theme.TEXT_FAINT, ms=10)
            ax.text(0.75, s, f"s = {s:+.2f}", color=theme.TEXT_DIM, fontsize=8,
                    va="center")
            ax.set_xlim(-1.3, 1.6)
            ax.set_ylim(-1.5, 1.5)
            ax.set_title("system: knob turns and slides")
        elif k == "simple pendulum (1-D)":
            t = math.radians(a)
            p = (math.sin(t), -math.cos(t))
            ax.plot([0, p[0]], [0, p[1]], color=theme.CYAN, lw=4)
            ax.plot(0, 0, "o", color=theme.WARN, ms=8)
            ax.plot(*p, "o", color=theme.TEXT, ms=12)
            square(ax, 1.3)
            ax.set_title("system: pendulum, θ from hanging")
        else:
            s = a / 100
            ax.plot([0, 1], [0, 0], color=theme.TEXT_FAINT, lw=4)
            for x in (0, 1):
                ax.plot([x, x], [-0.15, 0.15], color=theme.BAD, lw=4)
            ax.plot(s, 0, "o", color=theme.WARN, ms=16)
            ax.set_xlim(-0.2, 1.2)
            ax.set_ylim(-0.6, 0.6)
            ax.set_title("system: bead between end stops")

    def _draw_topology(self, ax, k):
        P = np.array([self._topo_pt(k, a, b) for a, b in self._trail])
        if k == "point moving in a plane":
            xx, yy = np.meshgrid(np.linspace(-2.2, 2.2, 9), np.linspace(-2.2, 2.2, 9))
            ax.plot_wireframe(xx, yy, 0 * xx, color=theme.BORDER, lw=0.5)
            title = "topology: E², a flat plane"
        elif k == "spherical pendulum":
            u, v = np.mgrid[0:TAU:30j, 0:math.pi:16j]
            ax.plot_surface(np.cos(u) * np.sin(v), np.sin(u) * np.sin(v),
                            np.cos(v), color=theme.ACCENT_DIM, alpha=0.25, lw=0)
            ax.scatter([0, 0], [0, 0], [1, -1], color=theme.PINK, s=25)
            ax.text(0, 0, 1.15, "N", color=theme.PINK, fontsize=8)
            title = "topology: S², a sphere"
        elif k == "2R robot arm":
            u, v = np.mgrid[0:TAU:40j, 0:TAU:20j]
            R, r = 2.0, 0.8
            ax.plot_surface((R + r * np.cos(v)) * np.cos(u),
                            (R + r * np.cos(v)) * np.sin(u), r * np.sin(v),
                            color=theme.ACCENT_DIM, alpha=0.25, lw=0)
            ax.set_zlim(-1.5, 1.5)
            title = "topology: T², a torus"
        elif k == "rotating & sliding knob":
            u, z = np.mgrid[0:TAU:30j, -1:1:8j]
            ax.plot_surface(np.cos(u), np.sin(u), z, color=theme.ACCENT_DIM,
                            alpha=0.25, lw=0)
            title = "topology: ℝ¹×S¹, a cylinder"
        elif k == "simple pendulum (1-D)":
            e = np.linspace(0, TAU, 100)
            ax.plot(np.cos(e), np.sin(e), color=theme.ACCENT_DIM, lw=6, alpha=0.6)
            square(ax, 1.4)
            title = "topology: S¹, a circle"
        else:
            ax.plot([0, 1], [0, 0], color=theme.ACCENT_DIM, lw=6, alpha=0.6)
            ax.plot([0, 1], [0, 0], "|", color=theme.BAD, ms=16, mew=3)
            ax.set_xlim(-0.2, 1.2)
            ax.set_ylim(-0.6, 0.6)
            title = "topology: [a, b], closed interval"
        if P.shape[1] == 3:
            ax.plot(P[:, 0], P[:, 1], P[:, 2], color=theme.TEXT_FAINT, lw=1.4)
            ax.scatter([P[-1, 0]], [P[-1, 1]], [P[-1, 2]], color=theme.WARN, s=60,
                       depthshade=False)
            if k != "2R robot arm":
                ax.set_box_aspect((1, 1, 1))
            else:
                ax.set_box_aspect((1, 1, 0.45))
        else:
            ax.plot(P[:, 0], P[:, 1], color=theme.TEXT_FAINT, lw=1.4)
            ax.plot(*P[-1], "o", color=theme.WARN, ms=10)
        ax.set_title(title)

    def _draw_rep(self, ax, k):
        R = np.array([self._rep_pt(k, a, b) for a, b in self._trail])
        dim1 = _TOPO[k]["b"] is None
        if k == "point moving in a plane":
            period = (None, None)
            ax.set_xlim(-2.2, 2.2)
            ax.set_ylim(-2.2, 2.2)
            ax.set_xlabel("x (m)")
            ax.set_ylabel("y (m)")
        elif k == "spherical pendulum":
            period = (360, None)
            ax.axhspan(88, 92, color=theme.PINK, alpha=0.3)
            ax.axhspan(-92, -88, color=theme.PINK, alpha=0.3)
            ax.text(-175, 80, "whole edge = North Pole", color=theme.PINK, fontsize=7)
            ax.text(-175, -84, "whole edge = South Pole", color=theme.PINK, fontsize=7)
            ax.set_xlim(-180, 180)
            ax.set_ylim(-92, 92)
            ax.set_xlabel("longitude (deg)")
            ax.set_ylabel("latitude (deg)")
        elif k == "2R robot arm":
            period = (360, 360)
            ax.set_xlim(0, 360)
            ax.set_ylim(0, 360)
            ax.set_xlabel("θ₁ ∈ [0°, 360°)")
            ax.set_ylabel("θ₂ ∈ [0°, 360°)")
        elif k == "rotating & sliding knob":
            period = (360, None)
            ax.set_xlim(0, 360)
            ax.set_ylim(-1.1, 1.1)
            ax.set_xlabel("θ ∈ [0°, 360°)")
            ax.set_ylabel("s (m)")
        elif k == "simple pendulum (1-D)":
            period = (360, None)
            ax.set_xlim(-10, 370)
            ax.set_ylim(-1, 1)
            ax.set_yticks([])
            ax.set_xlabel("θ ∈ [0°, 360°)")
        else:
            period = (None, None)
            ax.set_xlim(-0.1, 1.1)
            ax.set_ylim(-1, 1)
            ax.set_yticks([])
            ax.set_xlabel("s (m)")
        if dim1:
            ax.axhline(0, color=theme.BORDER, lw=6, alpha=0.6)
        if k == "spherical pendulum":
            # over a pole longitude jumps by 180 deg: also a break
            jumps = 0
            seg = [R[0]]
            for p0, p1 in zip(R[:-1], R[1:]):
                d = abs(p1[0] - p0[0])
                if d > 90:
                    s = np.array(seg)
                    ax.plot(s[:, 0], s[:, 1], "-", color=theme.TEXT_FAINT, lw=1.4)
                    ax.plot(*p0, "x", color=theme.BAD, ms=8, mew=2)
                    ax.plot(*p1, "x", color=theme.BAD, ms=8, mew=2)
                    seg = [p1]
                    jumps += 1
                else:
                    seg.append(p1)
            s = np.array(seg)
            ax.plot(s[:, 0], s[:, 1], "-", color=theme.TEXT_FAINT, lw=1.4)
        else:
            jumps = _broken_line(ax, R, period, theme.TEXT_FAINT)
        ax.plot(*R[-1], "o", color=theme.WARN, ms=10)
        ax.set_title("representation: the coordinates")
        return jumps


def topology_card() -> Card:
    """2.3.1, the definitions: what topology is and the catalogue of shapes."""
    c = Card("topology: the shape of C-space, independent of coordinates")
    c.add(body(
        "Besides <b>how many</b> numbers (the dimension), a C-space has a "
        "<b>shape</b>, its topology. A plane and the surface of a sphere are "
        "both 2-D, but the sphere wraps round on itself and the plane does "
        "not. Two spaces are <b>topologically equivalent</b> if one can be "
        "smoothly stretched and bent into the other <b>without cutting or "
        "gluing</b>. The classic example: the surface of a doughnut (torus) "
        "can be deformed into a coffee mug — the hole of the doughnut "
        "becomes the hole of the handle — so the two are the same shape. "
        "Neither can become a plane without cutting. Topology is a property "
        "of the space itself; it does not change with how you choose to put "
        "coordinates on it."))
    c.add(body(_grid_table(
        ("dim", "topology", "symbol", "example system", "why that shape"),
        [("1", "circle", "S¹", "revolute joint, no limits",
          "θ and θ + 2π are the same pose"),
         ("1", "line", "E¹ (ℝ)", "prismatic joint, no limits",
          "unbounded, never wraps"),
         ("1", "closed interval", "[a, b] ⊂ E¹", "prismatic joint with stops",
          "two real end points"),
         ("2", "plane", "E²", "point moving in a plane", "two unbounded lines"),
         ("2", "sphere", "S²", "spherical pendulum", "closes in every direction"),
         ("2", "torus", "T² = S¹ × S¹", "2R arm, no joint limits",
          "two independent circles"),
         ("2", "cylinder", "E¹ × S¹", "rotating & sliding knob",
          "one line × one circle"),
         ("3", "—", "E² × S¹", "rigid body moving in a plane",
          "(x, y) plus a heading angle"),
         ("6", "—", "E³ × SO(3)", "rigid body in space",
          "position plus orientation; SO(3) is 3-D"),
         ("n", "—", "Tⁿ", "nR open chain, no limits", "one circle per joint"),
         ("3+n", "—", "E² × S¹ × Tⁿ", "mobile base carrying an nR arm",
          "spaces of parts multiply")])))
    c.add(body(
        "<b>The product rule.</b> When a system is made of independent parts, "
        "its C-space is the <b>Cartesian product</b> of the parts' C-spaces: "
        "pick one point in each and you have a configuration. That is why a "
        "two-joint arm is S¹ × S¹ and a turning-sliding knob is E¹ × S¹. "
        "<b>Why topology matters to an engineer:</b> (1) distances wrap — the "
        "shortest move from θ = 350° to 10° is +20°, not −340°, and a planner "
        "or a PID error that ignores this sends the arm the long way round; "
        "(2) a space that is not flat cannot be covered by one set of "
        "minimal coordinates without a bad spot somewhere (next card); "
        "(3) closed chains can have C-spaces made of separate pieces (the "
        "four-bar's two assembly modes on the next page) that no motion "
        "connects.", dim=True))
    c.add(body(
        "<b>The product rule, slowly.</b> 'Independent' means choosing one "
        "part's value puts no restriction on the others. For the knob: any "
        "turn angle θ ∈ S¹ can go with any push depth z ∈ E¹, so the set of "
        "all knob poses is every pair (z, θ). Picture it: take the line of "
        "depths, and at each depth attach a whole circle of angles. Lines "
        "stacked with circles make a <b>cylinder</b>, E¹ × S¹. For the 2R "
        "arm: at each q₁ on a circle attach a whole circle of q₂ — circles "
        "swept round a circle make a <b>doughnut</b>, S¹ × S¹ = T². The "
        "practical payoff: <b>every rule about one piece holds for that "
        "coordinate on its own</b>. On a torus you wrap q₁ and q₂ "
        "separately, each exactly like a single joint. On E² × S¹ (a "
        "mobile robot) you subtract x and y normally and wrap only the "
        "heading. The rule fails as soon as the parts are <i>not</i> "
        "independent: in a four-bar, choosing the crank angle fixes the "
        "other three angles, so its C-space is not T⁴ but a 1-D curve "
        "inside T⁴."))
    c.add(body(
        "<b>The three engineering consequences, with an example each.</b><br>"
        "<b>(1) Distances wrap.</b> A joint at 350° told to go to 10°. On a "
        "line the gap is −340°; on the circle it is +20°. Any code that "
        "subtracts angles — a PID error, a planner's distance, a velocity "
        "estimate (θₖ − θₖ₋₁)/Δt, a linear interpolation between waypoints — "
        "must use the circle's answer or the arm takes the long way, or the "
        "velocity estimate spikes to −340°/Δt for one sample. The lab two "
        "cards down shows it.<br>"
        "<b>(2) Curved spaces have no perfect coordinates.</b> A circle's "
        "coordinate θ only has a seam (359° → 0°), which wrapping fixes. A "
        "sphere's or a 3-D orientation's coordinates are worse: somewhere "
        "they blow up (latitude–longitude at the pole, Euler angles at "
        "pitch ±90°), and no amount of wrapping repairs that. That is a "
        "theorem about the shape, not a weakness of a particular formula.<br>"
        "<b>(3) Separate pieces.</b> A four-bar assembled 'elbow up' can "
        "never reach 'elbow down' without taking it apart: its C-space is "
        "two disconnected loops. A planner asked to go between them must "
        "report 'impossible', not search forever.", dim=True))
    c.add(plain(
        "Topology is the shape you could feel with your eyes closed: does "
        "it go on forever, does it have edges you bump into, does walking "
        "straight bring you back to where you started, is there a hole "
        "through it? A coffee mug and a doughnut both have exactly one hole, "
        "so to a topologist they are the same; a ball has none, so it is "
        "different. For robots: one free-spinning joint gives a circle "
        "(walk once round, you are back); a joint with stops gives a segment "
        "(you hit a wall); two free joints give a doughnut surface."))
    return c


def why_card() -> Card:
    """The 'so what' of page 115: each idea and the later page that needs it."""
    c = Card("so what? where each idea on this page gets used")
    c.add(body(
        "This page is vocabulary, and vocabulary is hard to care about until "
        "you see the sentence it is used in. The goal of the block is "
        "<b>τ = M(q)q̈ + c(q, q̇) + g(q)</b> and the controllers built on it. "
        "Every idea below answers one question that equation, or the code "
        "around it, cannot avoid:"))
    c.add(body(_grid_table(
        ("idea", "question it answers", "what you actually do with it", "used on"),
        [("degrees of freedom",
          "how many numbers in q?",
          "sets the size of everything: q has n entries, M(q) is n × n, the "
          "Jacobian has n columns; tells you how many motors fully control "
          "the robot, and whether it is redundant for a task",
          "119, 120, 123, 125"),
         ("topology",
          "does the space wrap round, have walls, or have holes?",
          "wrap angle errors (PID, planners, interpolation); treat joint "
          "limits as walls, not seams; know that a closed chain may have "
          "separate pieces you cannot move between",
          "124, 134, 135"),
         ("explicit representation",
          "which minimal numbers do I write a pose with?",
          "joint angles q for an arm: exactly the q in the dynamics. Safe "
          "because a circle only has jumps, never blow-ups (cards below)",
          "119–131"),
         ("implicit representation",
          "what if every minimal set of numbers breaks somewhere?",
          "store the hand's orientation as a rotation matrix R (or a "
          "quaternion), never as Euler angles, so the controller has no "
          "gimbal lock; describe a closed chain by all its joints plus "
          "g(θ) = 0",
          "117, 118, 124, 136"),
         ("velocity ≠ coordinate rate",
          "how fast is it moving?",
          "use angular velocity ω and twists V, not Euler-angle rates; the "
          "Jacobian maps q̇ to a twist, not to rates of some coordinates",
          "117, 118, 120")])))
    c.add(plain(
        "Think of the whole block as a jigsaw whose finished picture is "
        "'compute the motor torques for a motion, and control the arm'. "
        "<b>DOF</b> tells you how many pieces the picture has (the length of "
        "q). <b>Topology</b> tells you the rules for subtracting and "
        "averaging those pieces (angles wrap, limits are walls). "
        "<b>Representation</b> tells you which numbers to store so nothing "
        "explodes: joint angles for the joints, a rotation matrix for the "
        "hand's orientation. You do not need to memorise a catalogue of "
        "shapes: the recipe card further down builds any C-space from its "
        "joints in one line."))
    return c


class AngleWrapCard:
    """Why the circle matters: naive vs wrapped angle error, and averaging."""

    def __init__(self):
        c = self.card = Card("so what? the long-way-round bug that the circle explains")
        c.add(body(
            "A revolute joint's C-space is a circle S¹, but its coordinate θ "
            "is written on a line segment [0°, 360°). The two disagree only "
            "at the seam, and that is enough to break ordinary arithmetic. "
            "Below, a joint sits at θ and must go to θ<sub>d</sub>. A P "
            "controller drives it with the error e. The <b>naive</b> error "
            "θ<sub>d</sub> − θ treats the coordinate as a line; the "
            "<b>wrapped</b> error respects the circle:"))
        c.add(math_label(
            r"e_{\mathrm{naive}}=\theta_d-\theta,\qquad "
            r"e_{\mathrm{wrap}}=\left((\theta_d-\theta+180^\circ)\ \mathrm{mod}\ 360^\circ\right)"
            r"-180^\circ\;\in[-180^\circ,180^\circ)", 15))
        self.s_now = labelled_slider(c, "current angle θ", 0, 359, 350, deg, self._draw)
        self.s_goal = labelled_slider(c, "target angle θ_d", 0, 359, 10, deg, self._draw)
        self.st_naive = Stat("naive error", "--", theme.BAD)
        self.st_wrap = Stat("wrapped error", "--", theme.GOOD)
        self.st_waste = Stat("wasted rotation", "--", theme.WARN)
        self.st_mean = Stat("average: naive / on circle", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_naive, self.st_wrap, self.st_waste, self.st_mean))
        self.cv = MplCanvas(width=8.6, height=3.5, ncols=2)
        c.add(self.cv)
        c.add(plain(
            "<b>Is the torus 'already wrapped'? Yes — that is the point.</b> "
            "The torus is not a tool you apply; it is a fact about the robot: "
            "a free joint really does come back to where it started. Your "
            "numbers do not know that. θ lives in [0°, 360°) and ordinary "
            "subtraction treats 359° and 0° as far apart. Knowing the C-space "
            "is a circle tells you <b>which arithmetic is correct</b>: wrap "
            "differences. Knowing it is a torus S¹ × S¹ tells you more: wrap "
            "each joint <b>separately</b> (product rule). For a 2R arm at "
            "(170°, −170°) going to (−170°, 170°), the naive move is "
            "(−340°, +340°): both joints swing nearly a full turn. Wrapped, it "
            "is (+20°, −20°): on the flat square picture the short path leaves "
            "through one corner and comes back in at the opposite corner, "
            "because the edges are glued. A planner that draws the square "
            "without the glue never finds that path.<br>"
            "At θ = 350° going to 10°, the joint only needs to turn "
            "+20°. The naive error says −340°, so the controller swings the "
            "arm almost all the way round the other way: slower, and through "
            "whatever is in the way. Averaging fails the same way: two "
            "sensor readings of 350° and 10° average to 180° on the number "
            "line, which points the opposite way, while the true average on "
            "the circle is 0°. <b>Try:</b> keep the two angles far from the "
            "seam (say 100° and 140°): both errors agree and the topology "
            "does not matter. Then put them on either side of 0°: the red "
            "path goes the long way. Nothing about the joint changed; only "
            "whether the code knew it was on a circle. A joint <i>with "
            "limits</i> is an interval, not a circle, and there the long way "
            "round is the only way, so you must not wrap."))
        self._draw()

    def _draw(self, *_):
        th, td = self.s_now.value(), self.s_goal.value()
        naive = td - th
        wrap = (td - th + 180) % 360 - 180
        r = math.radians
        sx, cx = math.sin(r(th)) + math.sin(r(td)), math.cos(r(th)) + math.cos(r(td))
        circ = None if math.hypot(sx, cx) < 1e-9 else math.degrees(math.atan2(sx, cx)) % 360
        mean = (th + td) / 2
        self.st_naive.set(f"{naive:+d}°")
        self.st_wrap.set(f"{wrap:+d}°")
        self.st_waste.set(f"{abs(naive) - abs(wrap)}°")
        self.st_mean.set(f"{mean:.0f}° / " + ("undefined" if circ is None else f"{circ:.0f}°"))
        self.cv.clear()
        a1, a2 = self.cv.axes
        e = np.linspace(0, TAU, 200)
        a1.plot(np.cos(e), np.sin(e), color=theme.BORDER, lw=1)
        a1.plot([0, math.cos(r(th))], [0, math.sin(r(th))], color=theme.CYAN, lw=4,
                label="joint now")
        a1.plot([0, math.cos(r(td))], [0, math.sin(r(td))], "--", color=theme.WARN,
                lw=2, label="target")
        for err, rad, col in ((naive, 0.8, theme.BAD), (wrap, 0.6, theme.GOOD)):
            s = np.radians(np.linspace(th, th + err, 120))
            a1.plot(rad * np.cos(s), rad * np.sin(s), color=col, lw=2.2)
            a1.plot(rad * math.cos(s[-1]), rad * math.sin(s[-1]), "o", color=col, ms=5)
        a1.plot(1.15 * math.cos(r(mean)), 1.15 * math.sin(r(mean)), "x", color=theme.BAD,
                ms=10, mew=2.5, label="naive average")
        if circ is not None:
            a1.plot(1.15 * math.cos(r(circ)), 1.15 * math.sin(r(circ)), "o",
                    color=theme.GOOD, ms=9, label="average on the circle")
        a1.text(1.02, -0.16, "0°", color=theme.TEXT_DIM, fontsize=8)
        square(a1, 1.45)
        a1.set_title("red: naive path   green: wrapped path")
        self.cv.legend(a1, loc="lower left")
        t = np.linspace(0, 3, 200)
        for err, col, lab in ((naive, theme.BAD, "naive error"),
                              (wrap, theme.GOOD, "wrapped error")):
            a2.plot(t, th + err * (1 - np.exp(-2 * t)), color=col, lw=2, label=lab)
        for k in (-1, 0, 1):
            a2.axhline(td + 360 * k, color=theme.WARN, lw=0.8, ls=":")
        a2.set_ylim(min(th, th + naive, th + wrap) - 30, max(th, th + naive, th + wrap) + 30)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("angle turned through (deg)")
        a2.set_title("same P gain, same joint (dotted: target, every 360°)")
        self.cv.legend(a2, loc="best")
        self.cv.refresh()


# ==========================================================================
# 2.3.2  representation: explicit vs implicit
# ==========================================================================

class RepresentationCard:
    """Walk around a latitude circle at constant speed; watch longitude's rate."""

    def __init__(self):
        c = self.card = Card("representation: explicit parametrization vs implicit")
        c.add(body(
            "To write a configuration as numbers we must make arbitrary "
            "choices. In a <b>flat</b> space (a line, a plane, Eⁿ) we pick an "
            "origin and orthogonal axes, then any point is a list of "
            "coordinates and its velocity is the time derivative of that "
            "list. This changes nothing about the space itself. For a "
            "<b>curved</b> space like the sphere there are two options:"))
        c.add(body(_grid_table(
            ("", "explicit parametrization", "implicit representation"),
            [("idea", "use the minimum number of coordinates, n = dimension",
              "embed the n-D space in a bigger flat space and use more "
              "coordinates, tied by constraints"),
             ("sphere", "latitude φ, longitude λ (2 numbers)",
              "(x, y, z) with x² + y² + z² = 1 (3 numbers − 1 constraint = 2 DOF)"),
             ("orientation SO(3)", "3 Euler angles, roll–pitch–yaw",
              "rotation matrix R, 9 numbers, RᵀR = I and det R = +1 "
              "(6 constraints → 3 DOF)"),
             ("four-bar", "one crank angle (hard to derive, subtle "
                          "singularities)",
              "four joint angles θ with three loop-closure equations g(θ) = 0"),
             ("advantage", "smallest possible list; nothing to enforce",
              "no singularities, no jumps, smooth everywhere"),
             ("disadvantage", "bad behaviour somewhere: coordinates race "
                              "or jump at singularities",
              "more numbers to store, and constraints to keep satisfied "
              "(numerical drift must be corrected)")])))
        c.add(body(
            "<b>The experiment.</b> This is the textbook's own example "
            "(Modern Robotics §2.3.2): the sphere is the simplest curved "
            "C-space, a stand-in for the orientation of a wrist or a camera. "
            "Walk east at a constant v = 1 m/s around a circle of constant "
            "latitude φ on a sphere of radius R = 1 m, and ask how fast each "
            "description of your position changes.", dim=True))
        c.add(body(
            "<b>Where λ̇ = v / (R cos φ) comes from.</b> Latitude φ is the "
            "angle up from the equator. The circle you walk on has radius "
            "r = R cos φ (the horizontal distance from the sphere's axis): "
            "r = R at the equator, r = 0 at the pole. Longitude λ is the angle "
            "you have turned round that axis. Walking at speed v round a "
            "circle of radius r turns you at v / r radians per second — like a "
            "wheel: same rim speed, smaller wheel, faster spin. So "
            "λ̇ = v / r = v / (R cos φ). At φ = 0°, λ̇ = 1 rad/s ≈ 57°/s. At "
            "φ = 89°, cos φ ≈ 0.017, so λ̇ ≈ 3300°/s for the same gentle walk. "
            "At 90° it divides by zero.<br>"
            "<b>Why (x, y, z) stays calm.</b> Write the point implicitly, "
            "p = (R cos φ cos λ, R cos φ sin λ, R sin φ), and differentiate "
            "with φ fixed. The speed is R cos φ · λ̇ = v: the large λ̇ is "
            "cancelled exactly by the small radius. (x, y, z) change only as "
            "fast as you physically move, everywhere, pole included.",
            dim=True))
        c.add(math_label(
            r"r=R\cos\varphi,\qquad \dot\lambda=\frac{v}{r}=\frac{v}{R\cos\varphi}"
            r"\;\to\;\infty\ \mathrm{as}\ \varphi\to 90^\circ", 15))
        c.add(math_label(
            r"\dot p=R\cos\varphi\,\dot\lambda\,(-\sin\lambda,\ \cos\lambda,\ 0),\qquad "
            r"\Vert\dot p\Vert=R\cos\varphi\,\dot\lambda=v", 15))
        self.s, name, self.read = _row(c, 0, 899, 450, self._draw)
        name.setText("latitude φ")
        self.st_lr = Stat("longitude rate λ̇", "--", theme.BAD)
        self.st_lap = Stat("time for one lap", "--", theme.ACCENT)
        self.st_xyz = Stat("‖ṗ‖ implicit", "1.00 m/s", theme.GOOD)
        c.add_layout(stat_row(self.st_lr, self.st_lap, self.st_xyz))
        self.cv = MplCanvas(width=8.6, height=3.5, ncols=2)
        _layout(self.cv, ["3d", "2d"])
        c.add(self.cv)
        c.add(body(
            "<b>Singularity of the representation.</b> The North Pole is a "
            "singularity of latitude–longitude: longitude is undefined there "
            "and races near it; stepping over it makes longitude jump by "
            "180°. None of this is a property of the sphere — it looks the "
            "same at the pole as at the equator. The implicit (x, y, z) has "
            "no such point. <b>The book's convention:</b> configurations are "
            "usually stored implicitly (rotation matrices R, homogeneous "
            "transforms T), and velocities are <b>not</b> the time derivatives "
            "of coordinates: angular velocity is a 3-vector ω with Ṙ = [ω]R, "
            "not the 9 numbers of Ṙ and not Euler-angle rates.", dim=True))
        c.add(body(_grid_table(
            ("orientation representation", "numbers", "constraints", "trouble spot"),
            [("ZYX Euler angles (roll, pitch, yaw)", "3", "0",
              "pitch = ±90°: gimbal lock, roll and yaw merge"),
             ("exponential coordinates ω̂θ", "3", "0",
              "θ = π: two answers; θ = 0: axis undefined"),
             ("unit quaternion", "4", "1 (‖q‖ = 1)",
              "none, but q and −q are the same rotation (double cover)"),
             ("rotation matrix R ∈ SO(3)", "9", "6 (RᵀR = I) + det = +1",
              "none — the book's choice")])))
        c.add(plain(
            "Explicit = a map with the fewest numbers, like latitude and "
            "longitude on a globe. Implicit = 'here is the point in 3-D space, "
            "and it has to lie on the sphere', which needs an extra number "
            "and a rule but never misbehaves. The penalty of the explicit "
            "map: near the pole, walking slowly round a tiny circle spins "
            "your longitude very fast, and at the pole longitude means "
            "nothing. Robots hit exactly this with Euler angles: a wrist near "
            "pitch 90° asks for huge joint speeds to make a small turn. "
            "<b>Try:</b> slide φ toward 90° and watch λ̇ explode on the log "
            "plot while ‖ṗ‖ stays 1. A degree of freedom count is always "
            "<i>numbers − independent constraints</i>: 3 − 1 = 2 for the "
            "sphere, 9 − 6 = 3 for a rotation matrix."))
        self._draw()

    def _draw(self, *_):
        phi = math.radians(self.s.value() / 10)
        self.read.setText(f"{self.s.value()/10:.1f}°")
        v, R = 1.0, 1.0
        lr = v / (R * math.cos(phi))
        self.st_lr.set(f"{math.degrees(lr):.0f} °/s")
        self.st_lap.set(f"{TAU * R * math.cos(phi):.2f} s")
        _clear(self.cv)
        a1, a2 = self.cv.axes
        u, w = np.mgrid[0:TAU:30j, 0:math.pi:16j]
        a1.plot_surface(np.cos(u) * np.sin(w), np.sin(u) * np.sin(w), np.cos(w),
                        color=theme.ACCENT_DIM, alpha=0.2, lw=0)
        for lon in np.radians(np.arange(0, 360, 30)):
            t = np.linspace(-math.pi / 2, math.pi / 2, 40)
            a1.plot(np.cos(t) * math.cos(lon), np.cos(t) * math.sin(lon), np.sin(t),
                    color=theme.BORDER, lw=0.6)
        e = np.linspace(0, TAU, 120)
        a1.plot(math.cos(phi) * np.cos(e), math.cos(phi) * np.sin(e),
                math.sin(phi) + 0 * e, color=theme.WARN, lw=2)
        a1.scatter([0], [0], [1], color=theme.PINK, s=30)
        a1.set_box_aspect((1, 1, 1))
        a1.set_title("walk round latitude φ at 1 m/s")
        lat = np.radians(np.linspace(0, 89.9, 300))
        a2.semilogy(np.degrees(lat), np.degrees(v / np.cos(lat)), color=theme.BAD,
                    lw=1.8, label="longitude rate λ̇ (°/s)")
        a2.semilogy(np.degrees(lat), np.degrees(np.ones_like(lat)), color=theme.GOOD,
                    lw=1.8, label="‖ṗ‖ in °/s of arc (implicit)")
        a2.plot(math.degrees(phi), math.degrees(lr), "o", color=theme.WARN, ms=9)
        a2.set_xlabel("latitude φ (deg)")
        a2.set_ylabel("rate (log scale)")
        a2.set_title("explicit coordinates blow up at the pole")
        self.cv.legend(a2, loc="upper left")
        self.cv.refresh()


def choose_rep_card() -> Card:
    """The take-away of page 115: shape vs numbers, the two failure kinds,
    and the one-sentence rule the rest of the block uses."""
    c = Card("so which do I use? explicit, implicit, and when wrapping is enough")
    c.add(body(
        "<b>The message of this card in one line:</b> use plain angles "
        "(explicit) for every joint and wrap their differences; store "
        "anything that can point in any 3-D direction (a hand's orientation, "
        "a drone's attitude) as a rotation matrix or quaternion (implicit). "
        "The rest of the card is why, and how to tell which case you are in."))
    c.add(body(
        "<b>1. Two different questions; do not mix them.</b> <b>Topology</b> "
        "is the shape of the C-space. The robot decides it; you cannot "
        "choose it. <b>Representation</b> is which numbers you store for a "
        "point on that shape. You choose it. 'Explicit or implicit' is a "
        "choice of representation; 'circle, torus, sphere' is a fact of "
        "topology. The fact decides which choice is safe."))
    c.add(body(
        "<b>2. Explicit numbers fail in one of two ways, and only one is "
        "fixable by wrapping.</b>"))
    c.add(body(_grid_table(
        ("", "a jump (seam)", "a blow-up (singularity)"),
        [("happens on", "a circle: any joint angle", "a sphere or SO(3): "
                                                    "latitude–longitude, Euler angles"),
         ("example", "joint moves 359° → 1°: a 2° turn, but θ reads −358°",
          "wrist near pitch 89° turns slowly at 10°/s; yaw and roll must "
          "change at ≈ 10/cos 89° ≈ 570°/s to describe it"),
         ("is the number wrong?", "no, it is just written in the wrong "
                                  "place on the line",
          "yes: the rate really is huge, and at 90° the angles are undefined"),
         ("fix", "one line of code: wrap the difference to (−180°, 180°]",
          "none in those coordinates; switch to R or a quaternion")])))
    c.add(body(
        "So for your question — <i>'explicit has jumps, but if we wrap it is "
        "okay?'</i> — <b>yes, on a circle or torus</b>: a joint angle never "
        "blows up, because 1° of motion is always 1° of θ. Wrapping repairs "
        "every jump, so joint angles q are safe to use as they are. "
        "<b>No, on a sphere or SO(3)</b>: there the trouble is a blow-up, "
        "not a seam, and wrapping does nothing. That is the only reason "
        "implicit exists."))
    c.add(body(
        "<b>3. What implicit does and does not buy.</b> It removes "
        "singularities <i>of the numbers</i> (gimbal lock, the pole). It does "
        "<b>not</b> make every controller safe: singularities <i>of the "
        "robot</i> — an arm stretched straight, where no joint speed moves "
        "the hand outward — exist whatever numbers you use (Jacobian, page "
        "120). And it has costs: 9 numbers instead of 3, plus rules "
        "(RᵀR = I, ‖q‖ = 1) that rounding error slowly breaks, so you "
        "re-normalise R or the quaternion every so often."))
    c.add(body(_grid_table(
        ("your robot has…", "C-space piece", "store as", "in code"),
        [("a revolute joint", "circle S¹", "<b>explicit</b> angle θ",
          "wrap every difference: e = (θ_d − θ + 180) % 360 − 180"),
         ("a joint with stops, or a slider", "interval / line", "<b>explicit</b> θ or d",
          "plain subtraction; never wrap (the long way is the only way)"),
         ("a hand, camera, drone or IMU orientation", "SO(3) (or S² for a "
                                                      "pointing direction)",
          "<b>implicit</b> R or quaternion",
          "error from R_dᵀR, not from Euler angles; Euler only for display"),
         ("a closed loop (four-bar, Delta)", "a curve or surface inside Tⁿ",
          "<b>implicit</b>: all joint angles + g(θ) = 0",
          "solve g(θ) = 0 numerically (next page)")])))
    c.add(plain(
        "A worked example to carry forward. A 6-joint arm holding a cup. "
        "Its joints: six circles, so C-space T⁶ and q is six plain angles "
        "— the q in τ = M(q)q̈ + c + g. Its controller computes "
        "q<sub>d</sub> − q joint by joint, wrapped. The cup's orientation "
        "is a 3-D orientation, so the hand pose is stored as a rotation "
        "matrix R, and 'how far is the cup from upright?' is computed from "
        "R, never by subtracting roll–pitch–yaw. Two representations in "
        "the same program, each chosen by the shape of its piece. That is "
        "the whole lesson, and it is why page 117 is about rotation "
        "matrices while every dynamics page uses plain joint angles."))
    return c


# ==========================================================================
# 2.4  what a constraint and its derivative mean: the bead on a hoop
# ==========================================================================

class HoopConstraintCard:
    """g(q) = 0, A = ∂g/∂q, A q̇ and the null space, for a bead on a circle."""

    def __init__(self):
        c = self.card = Card("what g(q) = 0 and A(q)q̇ = 0 mean: one constraint you can see")
        c.add(body(
            "Before the four-bar's twelve-entry matrix, take the smallest "
            "example that has every piece. A bead threaded on a circular hoop "
            "of radius 1. Describe it with n = 2 numbers q = (x, y), and add "
            "k = 1 rule: stay on the hoop. Then C-space dimension = n − k = 1."))
        c.add(math_label(
            r"g(q)=x^2+y^2-1=0,\qquad "
            r"A(q)=\frac{\partial g}{\partial q}=\begin{bmatrix}2x&2y\end{bmatrix},\qquad "
            r"A(q)\,\dot q=2x\dot x+2y\dot y=0", 15))
        c.add(body(
            "<b>1. g(q) is a gap meter.</b> It measures how badly the rule is "
            "broken: g &gt; 0 means outside the hoop, g &lt; 0 inside, and "
            "g = 0 exactly on it. 'g(q) = 0' is just 'the gap is zero'. For "
            "the four-bar, g has three entries: the x-gap, the y-gap and the "
            "angle-gap between the end of the loop and its start.<br>"
            "<b>2. Why differentiate.</b> If the gap is zero at every instant, "
            "it cannot be changing, so dg/dt = 0. By the chain rule "
            "dg/dt = (∂g/∂x)ẋ + (∂g/∂y)ẏ. That is all A(q)q̇ = 0 is: the "
            "rate of change of the gap, set to zero.<br>"
            "<b>3. What ∂g/∂q means.</b> Entry j of row i is 'how fast gap i "
            "opens per unit speed of coordinate j, if only j moves'. Here "
            "row = (2x, 2y): moving straight outward opens the gap fastest. "
            "So the row of A, drawn as an arrow, points <i>across</i> the "
            "hoop: it is the forbidden direction.<br>"
            "<b>4. What A q̇ = 0 means.</b> q̇ has no component along any "
            "forbidden direction. The velocities that pass are the <b>null "
            "space</b> of A: all q̇ with A q̇ = 0. Here it is the tangent line "
            "to the hoop. Its dimension, n − rank A = 2 − 1 = 1, is the DOF."))
        self.s_pos = labelled_slider(c, "bead position α", -180, 180, 40, deg, self._draw)
        self.s_dir = labelled_slider(c, "proposed velocity direction β", -180, 180, 160,
                                     deg, self._draw)
        self.st_A = Stat("A(q) = [2x  2y]", "--", theme.BAD)
        self.st_Aq = Stat("A(q) q̇ (gap rate)", "--", theme.WARN)
        self.st_ok = Stat("allowed?", "--", theme.GOOD)
        self.st_split = Stat("along / across hoop", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_A, self.st_Aq, self.st_ok, self.st_split))
        self.cv = MplCanvas(width=8.6, height=3.5, ncols=2)
        c.add(self.cv)
        c.add(plain(
            "<b>Left:</b> the red arrow is the row of A at the bead: the "
            "direction that breaks the rule. The green line is the null space "
            "of A: every velocity that keeps the rule. The gold arrow is a "
            "velocity you propose. A q̇ is just 'how much of the gold arrow "
            "points along the red one' (times |A|).<br><b>Right:</b> move in "
            "a straight line along the gold arrow and track the gap g. Its "
            "slope at the start is exactly A q̇: that is what the derivative "
            "means. <b>Try:</b> turn β until the stat reads 'yes' (gold on "
            "the green line). The slope at the start becomes zero, but the "
            "dashed straight path still drifts off the hoop and g still grows "
            "like s². That is the point: A q̇ = 0 is a rule for <i>this "
            "instant</i>. The bead must re-choose a tangent velocity at every "
            "instant, which is how it ends up following the curve.<br>"
            "<b>Physically</b>, the red direction is also the direction in "
            "which the hoop pushes on the bead. A push along the red arrow "
            "can never speed up or slow down a motion along the green line, "
            "so the hoop does no work. Page 131 uses exactly this: the "
            "constraint force is Aᵀλ, and its power q̇ᵀAᵀλ = (A q̇)ᵀλ = 0."))
        self._draw()

    def _draw(self, *_):
        a = math.radians(self.s_pos.value())
        b = math.radians(self.s_dir.value())
        q = np.array([math.cos(a), math.sin(a)])
        qd = np.array([math.cos(b), math.sin(b)])
        A = 2 * q
        Aq = float(A @ qd)
        n_hat = q
        t_hat = np.array([-q[1], q[0]])
        along, across = float(qd @ t_hat), float(qd @ n_hat)
        self.st_A.set(f"[{A[0]:+.2f}  {A[1]:+.2f}]")
        self.st_Aq.set(f"{Aq:+.3f}")
        self.st_ok.set("yes" if abs(Aq) < 0.02 else "no — breaks the rule")
        self.st_split.set(f"{along:+.2f} / {across:+.2f}")
        self.cv.clear()
        a1, a2 = self.cv.axes
        e = np.linspace(0, TAU, 200)
        a1.plot(np.cos(e), np.sin(e), color=theme.TEXT_FAINT, lw=3, label="hoop: g = 0")
        tl = np.array([q - 0.9 * t_hat, q + 0.9 * t_hat])
        a1.plot(tl[:, 0], tl[:, 1], color=theme.GOOD, lw=2.5,
                label="null space of A (allowed q̇)")
        a1.annotate("", xy=q + 0.55 * n_hat, xytext=q,
                    arrowprops=dict(arrowstyle="-|>", color=theme.BAD, lw=2.5))
        a1.plot([], [], color=theme.BAD, lw=2.5, label="row of A (forbidden)")
        a1.annotate("", xy=q + 0.7 * qd, xytext=q,
                    arrowprops=dict(arrowstyle="-|>", color=theme.WARN, lw=2.5))
        s = np.linspace(0, 1, 50)
        path = q + np.outer(s, qd)
        a1.plot(path[:, 0], path[:, 1], "--", color=theme.WARN, lw=1, label="straight move along q̇")
        a1.plot(*q, "o", color=theme.TEXT, ms=9)
        square(a1, 1.9)
        a1.set_title("bead on a hoop")
        self.cv.legend(a1, loc="lower left")
        g = 2 * s * float(q @ qd) + s ** 2
        a2.plot(s, g, color=theme.WARN, lw=2, label="gap g along the straight move")
        a2.plot(s, Aq * s, "--", color=theme.BAD, lw=1.4, label="slope at start = A(q) q̇")
        a2.axhline(0, color=theme.GOOD, lw=1)
        a2.set_xlim(0, 1)
        a2.set_ylim(-1.2, 3.1)
        a2.set_xlabel("distance moved s")
        a2.set_ylabel("g = x² + y² − 1")
        a2.set_title("the derivative of the gap is A q̇")
        self.cv.legend(a2, loc="upper left")
        self.cv.refresh()


def constraint_uses_card() -> Card:
    """Why turn a position rule into a velocity rule, and where each piece is used."""
    c = Card("so what? why the velocity form, and where each piece is used later")
    c.add(body(
        "<b>Why turn g(q) = 0 into A(q)q̇ = 0 at all?</b> Three reasons.<br>"
        "<b>1. It is linear.</b> g is full of sines and cosines of q; "
        "A(q)q̇ = 0 is a plain matrix times a vector. Linear means you can use "
        "linear algebra: rank, null space, solve, least squares. Every later "
        "page (Jacobian, dynamics, control) works with velocities and is "
        "linear in them, so this is the form they can consume.<br>"
        "<b>2. One form covers both kinds.</b> The car's rule exists "
        "<i>only</i> as A(q)q̇ = 0; there is no g behind it. Writing the "
        "four-bar's rule the same way lets one toolkit handle both. "
        "'Pfaffian' is just the name for that shape: something × q̇ = 0.<br>"
        "<b>3. Dynamics needs it.</b> A constrained robot obeys "
        "M(q)q̈ + c + g = τ + A(q)ᵀλ. The rows of A are the directions the "
        "constraint pushes, λ is how hard, and the push does no work because "
        "(A q̇)ᵀλ = 0."))
    c.add(body(_grid_table(
        ("what you have", "what it tells you", "where you use it"),
        [("g(q) = 0", "which poses exist at all; n − k numbers are free",
          "closed-chain inverse kinematics and assembly modes (124); a hand "
          "held against a wall (131)"),
         ("A(q) = ∂g/∂q", "row i: how fast gap i opens per unit speed of "
                          "each joint; also the direction the constraint pushes",
          "constraint and contact forces Aᵀλ (131)"),
         ("null space of A", "every velocity the mechanism can actually make; "
                             "its size is the DOF at this pose",
          "the speeds of passive joints when the motors turn (124); same idea "
          "as the Jacobian null space of a redundant arm (123)"),
         ("rank of A drops", "a singular pose: the mechanism gains a freedom, "
                             "locks, or can flip to the other assembly mode",
          "actuator singularities of parallel robots (124)"),
         ("A(q)q̇ = 0 with no g behind it", "nonholonomic: directions are "
                                           "forbidden, places are not",
          "car and differential-drive planning and control (134, 139)")])))
    c.add(plain(
        "The puzzle so far, in order. Page 115: q is the list of joint numbers, "
        "and you know what shape the space of q is. This page: some q's are "
        "not allowed (g(q) = 0 throws them out), and at each allowed q some "
        "velocities are not allowed (A q̇ = 0 throws them out). The null space "
        "of A is what is left: the motions the robot can really make. Later, "
        "the Jacobian (120) maps the allowed q̇ to hand velocity, and the "
        "dynamics (125–131) say what torques produce a given q̈, plus the "
        "constraint force Aᵀλ that keeps the rule true."))
    return c


# ==========================================================================
# 2.4  configuration constraints: the four-bar as an implicit C-space
# ==========================================================================

_FOURBAR = {
    # crank a, coupler b, rocker c, ground g
    "crank-rocker (Grashof)": ((1.0, 2.4, 2.0, 2.6),
        "Shortest link (1.0) is the crank and s + l = 3.6 ≤ p + q = 4.4 "
        "(Grashof's condition), so the crank turns all the way round. The "
        "C-space is two separate closed loops, one per assembly mode "
        "(elbow up / elbow down). No motion of the mechanism takes you from "
        "one to the other without disassembling it."),
    "double-rocker (non-Grashof)": ((2.0, 1.5, 2.0, 2.8),
        "s + l = 4.3 > p + q = 4.0, so no link turns fully. The crank swings "
        "between two limits where coupler and rocker line up. At each limit "
        "the two assembly modes meet, so the C-space is one closed loop, and "
        "the limit points are singularities of the 'crank angle' "
        "parametrization: θ₁ stops but the other angles keep moving."),
    "parallelogram (change points)": ((1.0, 2.5, 1.0, 2.5),
        "Opposite links equal. At θ₁ = 0° and 180° all four links are "
        "collinear: the two branches cross, A(θ) loses rank, and the "
        "mechanism can switch from parallelogram to anti-parallelogram. The "
        "C-space is two loops touching at those points — not even a smooth "
        "curve there."),
}


def _fourbar_solve(L, t1, branch):
    """Joint angles (θ1..θ4) of the four-bar for crank angle t1, or None.
    Ground joint A at the origin, ground joint D at (-g, 0); joint angles are
    the turn between successive links walking A->B->C->D->A, so
    θ1 + θ2 + θ3 + θ4 = 2π·k, the third loop-closure equation."""
    a, b, c, g = L
    A = np.zeros(2)
    D = np.array([-g, 0.0])
    B = a * np.array([math.cos(t1), math.sin(t1)])
    d = np.linalg.norm(D - B)
    if d > b + c or d < abs(b - c) or d < 1e-12:
        return None
    x = (d * d + b * b - c * c) / (2 * d)
    h = math.sqrt(max(0.0, b * b - x * x))
    ex = (D - B) / d
    ey = np.array([-ex[1], ex[0]])
    C = B + x * ex + branch * h * ey
    ang = [t1,
           math.atan2(*(C - B)[::-1]),
           math.atan2(*(D - C)[::-1]),
           math.atan2(*(A - D)[::-1])]
    th = [ang[0]]
    for i in range(1, 4):
        th.append((ang[i] - ang[i - 1] + math.pi) % TAU - math.pi)
    return np.array(th), np.array([A, B, C, D, A])


def _fourbar_g(L, th):
    a, b, c, g = L
    Ls = [a, b, c, g]
    Phi = np.cumsum(th)
    g1 = sum(l * math.cos(p) for l, p in zip(Ls, Phi))
    g2 = sum(l * math.sin(p) for l, p in zip(Ls, Phi))
    s = Phi[-1]
    g3 = s - TAU * round(s / TAU)
    return np.array([g1, g2, g3])


def _fourbar_A(L, th):
    Ls = [L[0], L[1], L[2], L[3]]
    Phi = np.cumsum(th)
    A = np.zeros((3, 4))
    for j in range(4):
        A[0, j] = -sum(Ls[i] * math.sin(Phi[i]) for i in range(j, 4))
        A[1, j] = sum(Ls[i] * math.cos(Phi[i]) for i in range(j, 4))
        A[2, j] = 1.0
    return A


class FourBarCard:
    def __init__(self):
        c = self.card = Card("the four-bar: a 1-D C-space living in 4-D joint space")
        c.add(body(
            "For closed chains an <b>implicit</b> representation is usually "
            "easier than an explicit one. Grübler says the four-bar has one "
            "DOF, so a single number should do — but writing the other three "
            "angles as functions of it is messy and has subtle singularities. "
            "Instead keep all four joint angles θ = (θ₁, θ₂, θ₃, θ₄) and "
            "impose the <b>loop-closure equations</b>: walking round the loop "
            "must bring you back to the same position and orientation."))
        c.add(math_label(
            r"g(\theta)=\begin{bmatrix}"
            r"L_1c_1+L_2c_{12}+L_3c_{123}+L_4c_{1234}\\"
            r"L_1s_1+L_2s_{12}+L_3s_{123}+L_4s_{1234}\\"
            r"\theta_1+\theta_2+\theta_3+\theta_4-2\pi\end{bmatrix}=0", 14))
        c.add(body(
            "c₁₂ means cos(θ₁ + θ₂), and so on. n = 4 coordinates, k = 3 "
            "independent <b>holonomic</b> constraints ⇒ dim C-space = "
            "n − k = 1. Differentiating g(θ(t)) = 0 in time gives the "
            "velocity form, a <b>Pfaffian constraint</b> with a 3 × 4 matrix:",
            dim=True))
        c.add(math_label(
            r"\frac{d}{dt}g(\theta)=\frac{\partial g}{\partial\theta}\dot\theta"
            r"=A(\theta)\,\dot\theta=0,\qquad A(\theta)\in\mathbb{R}^{k\times n}"
            r"=\mathbb{R}^{3\times 4}", 15))
        self.combo = QComboBox()
        for k in _FOURBAR:
            self.combo.addItem(k)
        c.add(self.combo)
        self.branch = QComboBox()
        self.branch.addItems(["assembly mode +1 (elbow one way)",
                              "assembly mode −1 (elbow the other way)"])
        c.add(self.branch)
        self.s, name, self.read = _row(c, -180, 180, 70, self._draw)
        name.setText("crank angle θ₁")
        self.st_ok = Stat("valid pose?", "--", theme.GOOD)
        self.st_res = Stat("‖g(θ)‖", "--", theme.ACCENT)
        self.st_sv = Stat("smallest σ of A", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_ok, self.st_res, self.st_sv))
        self.cv = MplCanvas(width=8.6, height=3.5, ncols=2)
        c.add(self.cv)
        self.mats = body("")
        c.add(self.mats)
        self.note = body("", dim=True)
        c.add(self.note)
        c.add(plain(
            "Four hinges, but bolting the last link to the ground forces "
            "them to cooperate: pick the crank angle and (for a given "
            "assembly mode) the other three are decided. That is what the "
            "three equations say — two for 'the loop ends where it started' "
            "and one for 'and facing the same way'. 4 numbers − 3 rules = 1 "
            "freedom. The right panel draws the C-space: it is a curve, a 1-D "
            "thing, sitting inside the 4-D space of joint angles (we show "
            "two of the four). The matrix A turns the rules into a rule on "
            "speeds: the joint speeds θ̇ must satisfy Aθ̇ = 0, so θ̇ points "
            "along the curve. <b>Try:</b> crank-rocker, flip the assembly "
            "mode: the dot jumps to the other loop — you cannot get there by "
            "turning the crank. Double-rocker: drag θ₁ toward its limit and "
            "watch the smallest singular value of A head to zero and the "
            "speeds θ̇₂..θ̇₄ (for θ̇₁ = 1) blow up."))
        c.add(body(
            "<b>What a designer reads off this lab.</b><br>"
            "<b>The Grashof type decides whether a motor can drive it.</b> A "
            "crank-rocker turns a motor spinning round and round into a "
            "back-and-forth swing: windscreen wipers, oil pumpjacks. A "
            "double-rocker cannot be driven by a spinning motor at joint 1, "
            "because the crank hits its limits.<br>"
            "<b>The assembly mode is fixed when you build it.</b> The other "
            "loop of the C-space is a different machine made of the same "
            "parts; turning the crank never reaches it.<br>"
            "<b>θ̇ with θ̇₁ = 1 is the gear ratio.</b> It is the one vector "
            "that spans the null space of A, so every allowed motion is a "
            "multiple of it. θ̇₄ is (up to sign) how fast the output rocker "
            "swings relative to the ground, per 1 rad/s of crank. Power in equals "
            "power out (τ₁θ̇₁ = τ₄θ̇₄), so the torque ratio is the inverse: "
            "that is how you size the motor.<br>"
            "<b>The smallest σ of A is a warning light.</b> As it falls to "
            "zero the ratio blows up: the crank alone stops deciding the "
            "motion (a dead point), or the mechanism can flip branch. "
            "Designers keep the working range away from these poses; page "
            "124 calls them actuator singularities.", dim=True))
        self._curves = {}
        self.combo.currentIndexChanged.connect(self._draw)
        self.branch.currentIndexChanged.connect(self._draw)
        self._draw()

    def _draw(self, *_):
        k = self.combo.currentText()
        L, note = _FOURBAR[k]
        br = 1 if self.branch.currentIndex() == 0 else -1
        t1 = math.radians(self.s.value())
        self.read.setText(f"{self.s.value()}°")
        self.note.setText(f"<b>{k}:</b> links crank {L[0]}, coupler {L[1]}, "
                          f"rocker {L[2]}, ground {L[3]}. {note}")
        sol = _fourbar_solve(L, t1, br)
        self.cv.clear()
        a1, a2 = self.cv.axes
        # C-space curve, both branches (depends only on the link set)
        if k not in self._curves:
            ts = np.radians(np.linspace(-180, 180, 721))
            self._curves[k] = []
            for b_ in (1, -1):
                pts = []
                for t in ts:
                    s = _fourbar_solve(L, t, b_)
                    pts.append(np.degrees(s[0][:2]) if s else (np.nan, np.nan))
                self._curves[k].append(np.array(pts))
        for pts, b_, col in zip(self._curves[k], (1, -1), (theme.CYAN, theme.PINK)):
            a2.plot(pts[:, 0], pts[:, 1], ".", ms=1.6, color=col,
                    label=f"mode {b_:+d}")
        a2.set_xlim(-180, 180)
        a2.set_ylim(-180, 180)
        a2.set_xlabel("θ₁ (deg)")
        a2.set_ylabel("θ₂ (deg)")
        a2.set_title("C-space projected on (θ₁, θ₂)")
        reach = sum(L) / 2 + 0.3
        if sol is None:
            self.st_ok.set("no — cannot close")
            self.st_res.set("—")
            self.st_sv.set("—")
            self.mats.setText(
                "At this crank angle the coupler and rocker cannot reach each "
                "other: no θ₂, θ₃, θ₄ satisfy g(θ) = 0. This θ₁ is not in the "
                "C-space at all.")
            B = L[0] * np.array([math.cos(t1), math.sin(t1)])
            a1.plot([0, B[0]], [0, B[1]], color=theme.BAD, lw=4)
            a1.plot([0, -L[3]], [0, 0], color=theme.TEXT_FAINT, lw=5)
        else:
            th, P = sol
            g = _fourbar_g(L, th)
            A = _fourbar_A(L, th)
            sv = np.linalg.svd(A, compute_uv=False)
            # theta_dot with theta1_dot = 1: solve A[:,1:] x = -A[:,0]
            try:
                rest = np.linalg.solve(A[:, 1:], -A[:, 0])
                td = np.concatenate([[1.0], rest])
                td_txt = mat_html(td.reshape(1, -1), 2)
            except np.linalg.LinAlgError:
                td = None
                td_txt = "singular — θ₁ cannot be the driving joint here"
            self.st_ok.set("yes")
            self.st_res.set(f"{np.linalg.norm(g):.1e}")
            self.st_sv.set(f"{sv[-1]:.3f}")
            self.mats.setText(
                f"θ = ({', '.join(f'{math.degrees(x):+.1f}°' for x in th)}), "
                f"Σθ = {math.degrees(th.sum()):+.1f}°<br>"
                f"<b>A(θ)</b> (3 × 4):{mat_html(A, 2)}"
                f"<b>θ̇ with θ̇₁ = 1 rad/s</b> (the null space of A):{td_txt}"
                + (f"check A θ̇ = {np.linalg.norm(A @ td):.1e}" if td is not None
                   else ""))
            a1.plot(P[[0, 3], 0], P[[0, 3], 1], color=theme.TEXT_FAINT, lw=5)
            a1.plot(P[:2, 0], P[:2, 1], color=theme.WARN, lw=4)
            a1.plot(P[1:3, 0], P[1:3, 1], color=theme.CYAN if br > 0 else theme.PINK,
                    lw=4)
            a1.plot(P[2:4, 0], P[2:4, 1], color=theme.VIOLET, lw=4)
            a1.plot(P[:4, 0], P[:4, 1], "o", color=theme.TEXT, ms=6)
            for i, name in enumerate("ABCD"):
                a1.text(P[i, 0] + 0.08, P[i, 1] + 0.08, name, color=theme.TEXT_DIM,
                        fontsize=8)
            a2.plot(*np.degrees(th[:2]), "o", color=theme.WARN, ms=10)
        a1.set_xlim(-L[3] - 1.3, 1.6)
        a1.set_ylim(-reach, reach)
        a1.set_aspect("equal", adjustable="box")
        a1.set_title("mechanism (ground A–D)")
        self.cv.legend(a2, loc="lower left")
        self.cv.refresh()


# ==========================================================================
# 2.4  velocity constraints: the car, a nonholonomic Pfaffian constraint
# ==========================================================================

_MANEUVERS = {
    "drive straight": "Forward at 1 m/s, steering centred.",
    "drive an arc": "Forward with the wheel turned: a circle.",
    "parallel park (net sideways shift)":
        "Forward-left, forward-right, reverse-left, reverse-right, each for T "
        "seconds. Every instant obeys the no-slip rule, yet the net result is "
        "a pure sideways shift: Δx = 0, Δφ = 0, Δy ≠ 0.",
    "slide sideways (forbidden)":
        "Push the car straight sideways. This velocity violates the "
        "constraint: A(q)q̇ ≠ 0 the whole time. Real tyres would have to skid.",
}


class CarConstraintCard:
    def __init__(self):
        c = self.card = Card("the car: a velocity constraint that cannot be integrated")
        c.add(body(
            "Chassis on a plane, configuration <b>q = (φ, x, y)</b>: heading φ "
            "and the point midway between the rear wheels. With forward "
            "speed v the rear point moves along the heading:"))
        c.add(math_label(
            r"\dot x=v\cos\phi,\;\;\dot y=v\sin\phi\;\;\Rightarrow\;\;"
            r"\dot x\sin\phi-\dot y\cos\phi=0\;\;\Leftrightarrow\;\;"
            r"\underbrace{\left[0\;\;\sin\phi\;\;-\cos\phi\right]}_{A(q)}"
            r"\begin{bmatrix}\dot\phi\\ \dot x\\ \dot y\end{bmatrix}=0", 15))
        c.add(body(
            "(Eliminate v: v = ẏ / sin φ, substitute into ẋ.) This has the "
            "same Pfaffian form A(q)q̇ = 0 as the four-bar's, but here there "
            "is <b>no</b> g(q) whose derivative it is: it is "
            "<b>nonholonomic</b>. It removes one direction of <i>velocity</i> "
            "(no sliding sideways) without removing any dimension of "
            "<i>configuration</i>: the car can still reach every (φ, x, y). "
            "Holonomic constraints are called <i>integrable</i> because they "
            "are the integral of their velocity form; the car's is not. "
            "(How to test integrability in general — Lie brackets — is "
            "chapter 13.)", dim=True))
        self.combo = QComboBox()
        for k in _MANEUVERS:
            self.combo.addItem(k)
        self.combo.setCurrentIndex(2)
        c.add(self.combo)
        self.sT, nT, self.rT = _row(c, 10, 150, 60, self._draw)
        nT.setText("segment time T")
        self.sk, nk, self.rk = _row(c, 2, 20, 10, self._draw)
        nk.setText("steering curvature κ")
        self.st_dx = Stat("Δx", "--", theme.ACCENT)
        self.st_dy = Stat("Δy (sideways)", "--", theme.GOOD)
        self.st_dp = Stat("Δφ", "--", theme.VIOLET)
        self.st_res = Stat("max |A(q)q̇|", "--", theme.BAD)
        c.add_layout(stat_row(self.st_dx, self.st_dy, self.st_dp, self.st_res))
        self.cv = MplCanvas(width=8.6, height=3.5, ncols=2)
        c.add(self.cv)
        self.note = body("", dim=True)
        c.add(self.note)
        c.add(body(_grid_table(
            ("", "holonomic", "nonholonomic"),
            [("constrains", "configuration q: g(q) = 0",
              "velocity q̇ only: A(q)q̇ = 0, not integrable"),
             ("C-space dimension", "reduced: n − k", "unchanged: n"),
             ("velocity freedoms", "n − k", "n − k (fewer than the C-space dim)"),
             ("examples", "loop closure, a point kept on a surface, a "
                          "chassis kept on the floor",
              "rolling without slipping: car, unicycle, diff-drive, ball "
              "on a plate, ice skate"),
             ("consequence", "fewer variables to plan in",
              "every pose reachable, but only by indirect manoeuvres; no "
              "smooth static feedback can stabilise a point (Brockett)")])))
        c.add(body(
            "<b>Both at once.</b> Treat the chassis as a rigid body in space "
            "(6-D C-space). Three holonomic constraints keep it on the floor "
            "(z = 0, no roll, no pitch) → C-space is 3-D, (φ, x, y). One "
            "nonholonomic constraint then removes the sideways velocity → 2 "
            "velocity freedoms (drive and steer) in a 3-D C-space.", dim=True))
        c.add(plain(
            "Holonomic = a rule about <i>where</i> you can be (the four-bar's "
            "loop must close). Nonholonomic = a rule only about <i>which way "
            "you can move right now</i> (wheels roll forward, not sideways). "
            "The second kind does not shrink the map of places you can get "
            "to — it only forces detours. Parallel parking is the proof: no "
            "single motion slides the car sideways, but four legal arcs add "
            "up to exactly that. <b>Try:</b> 'parallel park' — the red "
            "residual stays at zero the whole time, yet Δy is nonzero and Δx, "
            "Δφ come back to zero. Increase T and κ: bigger arcs, bigger "
            "shift (for small arcs the shift grows like κT², the signature of "
            "a Lie bracket). Then pick 'slide sideways': the residual is −1 "
            "the whole time, which tyres cannot do."))
        self.combo.currentIndexChanged.connect(self._draw)
        self._draw()

    def _segments(self, k, T, kap):
        if k == "drive straight":
            return [(1.0, 0.0, 2 * T)]
        if k == "drive an arc":
            return [(1.0, kap, 3 * T)]
        if k.startswith("parallel"):
            return [(1, kap, T), (1, -kap, T), (-1, kap, T), (-1, -kap, T)]
        return None

    def _draw(self, *_):
        k = self.combo.currentText()
        T = self.sT.value() / 100
        kap = self.sk.value() / 10
        self.rT.setText(f"{T:.2f} s")
        self.rk.setText(f"{kap:.1f} 1/m")
        self.note.setText(_MANEUVERS[k])
        dt = 0.005
        q = np.zeros(3)
        Q, R, tt = [q.copy()], [0.0], [0.0]
        segs = self._segments(k, T, kap)
        if segs is None:
            for _ in range(int(round(2 * T / dt))):
                qd = np.array([0.0, 0.0, 0.5])
                R.append(qd[1] * math.sin(q[0]) - qd[2] * math.cos(q[0]))
                q = q + dt * qd
                Q.append(q.copy())
                tt.append(tt[-1] + dt)
        else:
            for v, kk, Ts in segs:
                for _ in range(int(round(Ts / dt))):
                    qd = np.array([v * kk, v * math.cos(q[0]), v * math.sin(q[0])])
                    R.append(qd[1] * math.sin(q[0]) - qd[2] * math.cos(q[0]))
                    q = q + dt * qd
                    Q.append(q.copy())
                    tt.append(tt[-1] + dt)
        Q, R, tt = np.array(Q), np.array(R), np.array(tt)
        R[0] = R[1] if len(R) > 1 else 0.0
        d = Q[-1] - Q[0]
        self.st_dx.set(f"{d[1]:+.3f} m")
        self.st_dy.set(f"{d[2]:+.3f} m")
        self.st_dp.set(f"{math.degrees(d[0]):+.1f}°")
        self.st_res.set(f"{np.abs(R).max():.2f}")
        self.cv.clear()
        a1, a2 = self.cv.axes
        a1.plot(Q[:, 1], Q[:, 2], color=theme.TEXT_FAINT, lw=1.2)
        idx = np.linspace(0, len(Q) - 1, 6).astype(int)
        for n, i in enumerate(idx):
            phi, x, y = Q[i]
            body_pts = np.array([[-0.15, -0.12], [0.45, -0.12], [0.45, 0.12],
                                 [-0.15, 0.12], [-0.15, -0.12]])
            Rm = np.array([[math.cos(phi), -math.sin(phi)],
                           [math.sin(phi), math.cos(phi)]])
            P = body_pts @ Rm.T + [x, y]
            col = theme.WARN if n == len(idx) - 1 else (
                theme.ACCENT if n == 0 else theme.BORDER)
            a1.plot(P[:, 0], P[:, 1], color=col, lw=1.6)
            a1.plot(x, y, "o", color=col, ms=3)
        a1.set_aspect("equal", adjustable="datalim")
        a1.set_xlabel("x (m)")
        a1.set_ylabel("y (m)")
        a1.set_title("chassis path (blue start, gold end)")
        a2.plot(tt, R, color=theme.BAD, lw=1.6, label="A(q)q̇ = ẋ sin φ − ẏ cos φ")
        a2.plot(tt, Q[:, 0], color=theme.VIOLET, lw=1.2, label="heading φ (rad)")
        a2.axhline(0, color=theme.BORDER, lw=1)
        a2.set_xlabel("time (s)")
        a2.set_title("constraint residual over time")
        self.cv.legend(a2, loc="lower left")
        self.cv.refresh()


# ==========================================================================
# 2.5  task space and workspace
# ==========================================================================

_TASKS = {
    "write with a marker on a whiteboard": (
        "ℝ² (the Euclidean plane of the board)", 2,
        "Only the (x, y) of the marker tip matters; pen pressure and "
        "the marker's tilt are not part of the task.",
        "a 2R planar arm is just enough; a 3R planar arm is redundant by 1; "
        "a 6R arm is redundant by 4."),
    "control position and orientation of a rigid body": (
        "SE(3) = ℝ³ × SO(3), the 6-D space of rigid-body configurations", 6,
        "Pick-and-place of an arbitrary part, machining, assembly: every one "
        "of the six numbers matters.",
        "a 6-DOF arm (UR5, PUMA) is exactly enough away from singularities; a "
        "7-DOF arm (Franka, iiwa) is redundant by 1."),
    "point a camera or a laser": (
        "S² (the 2-D sphere of directions)", 2,
        "The roll about the viewing axis does not matter for a laser, and "
        "where the device sits is fixed.",
        "a pan–tilt unit (2R) is exactly enough; it has its own "
        "lat–long style singularity when pointing straight up."),
    "planar pick and place (x, y, yaw)": (
        "ℝ² × S¹ (the plane of the table plus a heading)", 3,
        "Parts lie flat on a conveyor; only their in-plane position and "
        "rotation matter.",
        "a SCARA robot (RRP + R) gives these 3 plus a height: 4-DOF."),
    "weld along a seam with a torch": (
        "ℝ³ × S² (a point and a direction, 5-D)", 5,
        "The torch is symmetric about its own axis, so rotating it about "
        "that axis does not change the weld.",
        "a 6R arm has one redundant freedom for this task — commonly used to "
        "keep the cable away from the part."),
    "spray nozzle at a given height": (
        "ℝ¹ (a single real number)", 1,
        "Only the height above the floor; everything else is irrelevant.",
        "a single prismatic axis suffices."),
}


class TaskSpaceCard:
    def __init__(self):
        c = self.card = Card("three spaces people confuse: C-space, task space, workspace")
        c.add(body(_grid_table(
            ("space", "what it is", "depends on", "example"),
            [("C-space", "all configurations of the <b>robot</b> — every "
                         "joint value", "the robot only",
              "2R arm: torus T²"),
             ("task space", "a space in which the <b>task</b> is naturally "
                            "expressed", "the task only — you need not know "
                                         "the robot",
              "marker tip on a board: ℝ²"),
             ("workspace", "the end-effector configurations the robot <b>can "
                           "reach</b>", "the robot only — no task involved",
              "2R arm with limits: a crescent-shaped region")])))
        c.add(body(
            "Pick a task. Notice the task space is defined without saying "
            "what robot will do it; the robot comes in only when you ask "
            "whether it has enough freedoms (and whether the task lies inside "
            "its workspace).", dim=True))
        self.combo = QComboBox()
        for k in _TASKS:
            self.combo.addItem(k)
        self.combo.currentIndexChanged.connect(self._show)
        c.add(self.combo)
        self.st_dim = Stat("task-space dimension", "--", theme.ACCENT)
        self.st_6 = Stat("redundancy of a 6R arm", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_dim, self.st_6))
        self.info = body("")
        c.add(self.info)
        c.add(plain(
            "<b>Task space</b> answers 'what numbers describe the job?' — "
            "written down before anyone picks a robot. <b>Workspace</b> "
            "answers 'where can this robot's hand actually get to?' — "
            "a property of the robot, with no job in mind. <b>C-space</b> "
            "answers 'what are all the joint settings?'. If the robot has "
            "more joints than the task has numbers, it is <b>redundant</b> "
            "for that task: the spare freedoms can be used for something "
            "else (avoiding an obstacle, staying away from joint limits). "
            "Redundancy is task dependent: the same 6R arm is redundant for "
            "writing and exactly enough for full 6-D pose."))
        self._show()

    def _show(self, *_):
        k = self.combo.currentText()
        space, dim, why, robots = _TASKS[k]
        self.st_dim.set(str(dim))
        self.st_6.set(str(6 - dim))
        self.info.setText(_info_table([
            ("Task", k), ("Task space", space),
            ("Why that space", why), ("Robots for it", robots)]))


class JointLimitWorkspaceCard:
    """2R with the video's joint limits, and the dexterous workspace of a 3R."""

    def __init__(self):
        c = self.card = Card("workspace with joint limits, and the dexterous workspace")
        c.add(body(
            "The workspace is often drawn as the Cartesian points the "
            "end-effector can reach, and depends on joint limits as much as "
            "on link lengths. The video's example: a planar 2R arm whose "
            "joints range over <b>180°</b> and <b>150°</b>. Including "
            "orientation, the set of positions reachable <b>with every "
            "orientation</b> is the <b>dexterous workspace</b>. For a planar "
            "3R arm with full rotation it is an annulus:"))
        c.add(math_label(
            r"|L_1-L_2|+L_3\;\le\;\|p\|\;\le\;L_1+L_2-L_3"
            r"\quad(\text{empty if } |L_1-L_2|+L_3>L_1+L_2-L_3)", 15))
        self.s1, n1, self.r1 = _row(c, 10, 360, 180, self._draw)
        n1.setText("joint 1 range")
        self.s2, n2, self.r2 = _row(c, 10, 360, 150, self._draw)
        n2.setText("joint 2 range")
        self.s3, n3, self.r3 = _row(c, 0, 60, 30, self._draw)
        n3.setText("3R: wrist link L₃")
        self.s4, n4, self.r4 = _row(c, 0, 359, 45, self._draw)
        n4.setText("3R: required yaw ψ")
        self.st_area = Stat("2R workspace area", "--", theme.ACCENT)
        self.st_dex = Stat("3R dexterous annulus", "--", theme.GOOD)
        c.add_layout(stat_row(self.st_area, self.st_dex))
        self.cv = MplCanvas(width=8.6, height=3.7, ncols=2)
        c.add(self.cv)
        c.add(plain(
            "<b>Left:</b> every point the 2R hand can touch when joint 1 "
            "sweeps a range centred on straight ahead and joint 2 a range "
            "centred on straight. Shrink a range and the reachable region "
            "becomes a crescent — the video's 180° / 150° picture. "
            "<b>Right:</b> a 3R arm (L₁ = 1, L₂ = 0.8, plus a short wrist "
            "L₃) asked to hold the hand at a fixed yaw ψ: the wrist must sit "
            "L₃ behind the tip, so the reachable set for that yaw is the 2R "
            "annulus shifted by L₃ (the gold ring). Reachable at <i>every</i> "
            "yaw means inside every shifted ring at once: the green dexterous "
            "annulus. <b>Try:</b> raise L₃ above 0.4 — the dexterous "
            "workspace shrinks and vanishes even though the plain workspace "
            "grows. Rotate ψ and the gold ring slides around, always "
            "containing the green one."))
        self._draw()

    def _draw(self, *_):
        r1, r2 = self.s1.value(), self.s2.value()
        L3 = self.s3.value() / 100
        psi = math.radians(self.s4.value())
        self.r1.setText(f"{r1}°")
        self.r2.setText(f"{r2}°")
        self.r3.setText(f"{L3:.2f} m")
        self.r4.setText(f"{self.s4.value()}°")
        L = [1.0, 0.8]
        q1 = np.radians(np.linspace(-r1 / 2, r1 / 2, 120))
        q2 = np.radians(np.linspace(-r2 / 2, r2 / 2, 120))
        Q1, Q2 = np.meshgrid(q1, q2)
        X = L[0] * np.cos(Q1) + L[1] * np.cos(Q1 + Q2)
        Y = L[0] * np.sin(Q1) + L[1] * np.sin(Q1 + Q2)
        # area by occupancy grid
        H, _, _ = np.histogram2d(X.ravel(), Y.ravel(), bins=90,
                                 range=[[-1.9, 1.9], [-1.9, 1.9]])
        area = (H > 0).sum() * (3.8 / 90) ** 2
        self.st_area.set(f"≈ {area:.2f} m²")
        lo, hi = abs(L[0] - L[1]) + L3, L[0] + L[1] - L3
        self.st_dex.set(f"{lo:.2f} – {hi:.2f} m" if lo <= hi else "empty")
        self.cv.clear()
        a1, a2 = self.cv.axes
        a1.plot(X.ravel(), Y.ravel(), ".", color=theme.ACCENT, ms=1, alpha=0.4)
        e = np.linspace(0, TAU, 200)
        a1.plot(1.8 * np.cos(e), 1.8 * np.sin(e), color=theme.BORDER, lw=1, ls="--")
        draw_arm(a1, L, [math.radians(r1 / 4), math.radians(r2 / 3)])
        square(a1, 2.0)
        a1.set_title(f"2R workspace: {r1}° / {r2}°")
        # 3R, full rotation
        Rin, Rout = abs(L[0] - L[1]), L[0] + L[1]
        for rad in (Rin, Rout):
            a2.plot(rad * np.cos(e), rad * np.sin(e), color=theme.BORDER, lw=0.8)
        # reachable at yaw psi: the wrist w = p - sh must lie in the 2R
        # annulus, so p lies in that annulus shifted by sh
        sh = L3 * np.array([math.cos(psi), math.sin(psi)])
        for rad in (Rin, Rout):
            a2.plot(sh[0] + rad * np.cos(e), sh[1] + rad * np.sin(e),
                    color=theme.WARN, lw=1.4)
        if lo <= hi:
            ring = np.concatenate([hi * np.exp(1j * e), lo * np.exp(-1j * e)])
            a2.fill(ring.real, ring.imag, color=theme.GOOD, alpha=0.35, lw=0)
        Rall = Rout + L3
        a2.plot(Rall * np.cos(e), Rall * np.sin(e), color=theme.ACCENT, lw=1, ls="--")
        # an arm reaching a point in the dexterous set at yaw psi
        if lo <= hi:
            p = (lo + hi) / 2 * np.array([0.0, 1.0])
            w = p - sh
            d = np.linalg.norm(w)
            c2 = (d * d - L[0] ** 2 - L[1] ** 2) / (2 * L[0] * L[1])
            c2 = max(-1.0, min(1.0, c2))
            t2 = math.acos(c2)
            t1 = math.atan2(w[1], w[0]) - math.atan2(L[1] * math.sin(t2),
                                                     L[0] + L[1] * math.cos(t2))
            draw_arm(a2, [L[0], L[1], L3] if L3 > 0 else L,
                     [t1, t2, psi - t1 - t2][:3 if L3 > 0 else 2])
        square(a2, 2.0)
        a2.set_title("3R: gold = at yaw ψ, green = every yaw")
        self.cv.refresh()
