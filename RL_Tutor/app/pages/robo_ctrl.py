"""
ROBOT MECHANICS, part 4 -- trajectories, planning, control, grasping, mobility.
Modern Robotics playlists 8-12 (chapters 9-13), and an interview drill.

    time scaling        cubic, quintic, trapezoid; path vs trajectory
    time-optimal        the (s, sdot) phase plane under torque limits
    motion planning     C-space obstacles, A* on a torus, RRT
    motion control      PD + gravity vs computed torque, with model error
    task-space control  operational space + null-space posture torque
    force control       hybrid motion/force and task-space impedance
    grasping            friction cones, form and force closure
    wheeled robots      nonholonomic unicycle, look-ahead tracking
    interview drill     the questions, answered in two sentences each
"""

from __future__ import annotations

import math

import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Circle
from PySide6.QtWidgets import QCheckBox, QComboBox

from ctrlcore import robodyn as rd
from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, callout, math_label, stat_row
from .base import Page
from .robo_common import (
    SEC_CTRL,
    SEC_MANIP,
    SEC_PLAN,
    deg,
    draw_arm,
    interview,
    labelled_slider,
    plain,
    playlist_badge,
    square,
    start_here,
    watch,
)

ARM = dict(L=[1.0, 0.8], m=[2.0, 1.5], r=[0.5, 0.4], I=[0.17, 0.08])


# ==========================================================================
# Playlist 8 -- trajectory generation
# ==========================================================================

class TimeScalingPage(Page):
    TITLE = "Trajectories: Path, Time Scaling, Via Points"
    SUBTITLE = ("A path is geometry, θ(s) for s ∈ [0, 1]. A time scaling s(t) "
                "says how fast to walk it. Their product is the trajectory, and "
                "the time scaling alone decides peak velocity, acceleration "
                "and jerk.")
    SECTION = SEC_PLAN
    NOTES = playlist_badge(8)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(8))
        self.add(start_here(
            "Planning a motion has two separate parts. The <b>path</b> is the "
            "route — the shape of the curve, pure geometry. The <b>time "
            "scaling</b> is how fast you travel along it at each moment. A "
            "road trip: the route on the map versus your speedometer. s runs "
            "from 0 (start) to 1 (end) along the path, and s(t) says how far "
            "along you are at time t."))

        t = Card("three standard time scalings")
        t.add(math_label(r"\mathrm{cubic:}\ s=3\left(\frac{t}{T}\right)^2-2\left(\frac{t}{T}\right)^3"
                         r",\quad \mathrm{quintic:}\ s=10\tau^3-15\tau^4+6\tau^5", 15))
        t.add(math_label(r"\mathrm{cubic:}\ \dot s_{max}=\frac{3}{2T},\ \ddot s_{max}=\frac{6}{T^2}"
                         r"\qquad \mathrm{quintic:}\ \dot s_{max}=\frac{15}{8T},\ "
                         r"\ddot s_{max}=\frac{10}{\sqrt{3}T^2}", 15))
        t.add(body(
            "Cubic: zero velocity at both ends, but acceleration jumps from 0 "
            "to 6/T² at t = 0 — infinite jerk, which excites flexible modes "
            "(the SEA and gearbox resonances of pages 26–29). Quintic adds "
            "zero end accelerations. <b>Trapezoidal</b> (bang-coast-bang) "
            "is time-optimal for a velocity limit and an acceleration limit "
            "and is what most industrial controllers ship; S-curves smooth "
            "its corners to bound jerk."))
        t.add(body(
            "Straight line in joint space is easy and stays in joint limits; "
            "straight line in task space (screw motion in SE(3), or "
            "decoupled p(s) and R(s) = R₀exp(log(R₀ᵀR₁)s)) looks right to a "
            "human but can pass through singularities.", dim=True))
        t.add(plain(
            "<b>Cubic</b>: speed starts and ends at zero, but acceleration "
            "jumps instantly at both ends — a jolt ('infinite jerk') that "
            "shakes springy parts and gearboxes. <b>Quintic</b>: acceleration "
            "also starts and ends at zero, so no jolt, at the price of a "
            "slightly higher top speed (15/8T against 3/2T). "
            "<b>Trapezoid</b>: full acceleration, cruise at top speed, full "
            "braking — the fastest possible under a speed limit and an "
            "acceleration limit, and what industrial controllers use. A "
            "straight line in joint space keeps joints in range but the hand "
            "traces a curve; a straight line for the hand looks right but can "
            "pass through a singularity."))
        self.add(t)

        lab = Card("compare the scalings for the same move")
        self.T = labelled_slider(lab, "duration T (cubic/quintic)", 5, 40, 20,
                                 lambda v: f"{v/10:.1f} s", self._draw)
        self.v = labelled_slider(lab, "trapezoid cruise ṡ", 6, 30, 8,
                                 lambda v: f"{v/10:.1f} /s", self._draw)
        self.a = labelled_slider(lab, "trapezoid accel s̈", 5, 50, 12,
                                 lambda v: f"{v/10:.1f} /s²", self._draw)
        self.st_tr = Stat("trapezoid duration", "--", theme.WARN)
        lab.add_layout(stat_row(self.st_tr))
        self.cv = MplCanvas(width=7.6, height=4.4, nrows=3)
        lab.add(self.cv)
        lab.add(plain(
            "Three stacked plots: position s, speed ṡ and acceleration s̈, "
            "for all three profiles. Look for: the cubic's acceleration "
            "starting and ending with a vertical jump; the quintic's smooth "
            "acceleration curve; the trapezoid's flat acceleration blocks and "
            "flat cruising speed. <b>Try:</b> lower the trapezoid's "
            "acceleration until the stat says 'triangle — never cruises': it "
            "runs out of path before reaching the cruise speed."))
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“Why quintic instead of cubic?”</b> A cubic matches position "
            "and velocity at the ends but not acceleration, so commanded "
            "acceleration (and therefore motor torque, via M q̈) steps "
            "instantly at start and stop. Infinite jerk excites structural "
            "modes and wears gearboxes. Quintic matches acceleration too; "
            "for multi-segment paths with via points, use cubic splines with "
            "continuous acceleration at the knots or B-splines."))
        self.finish()

    def _draw(self):
        T = self.T.value() / 10
        v, a = self.v.value() / 10, self.a.value() / 10
        ts = np.linspace(0, max(T, 3.0) * 1.05, 400)
        c = rd.cubic(ts, T)
        qn = rd.quintic(ts, T)
        tr = rd.trapezoid(ts, v, a)
        self.st_tr.set(f"{tr[3]:.2f} s" + ("  (triangle — never cruises)" if v * v / a > 1 else ""))
        cv = self.cv
        cv.clear()
        names = ["s", "ṡ", "s̈"]
        for k, ax in enumerate(cv.axes):
            ax.plot(ts, c[k], color=theme.ACCENT, label="cubic")
            ax.plot(ts, qn[k], color=theme.GOOD, label="quintic")
            ax.plot(ts, tr[k], color=theme.WARN, label="trapezoid")
            ax.set_ylabel(names[k])
        cv.axes[-1].set_xlabel("time (s)")
        cv.legend(cv.axes[0], loc="lower right")
        cv.refresh()


class TimeOptimalPage(Page):
    TITLE = "Time-Optimal Time Scaling Under Torque Limits"
    SUBTITLE = ("Fix the path and let the dynamics decide the speed. Along "
                "q(s), τ = m(s)s̈ + c(s)ṡ² + g(s), so torque limits become "
                "bounds on s̈ that depend on (s, ṡ). The fastest motion rides "
                "those bounds: full acceleration, then full braking.")
    SECTION = SEC_PLAN
    NOTES = playlist_badge(8)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(8))
        self.add(start_here(
            "You know the path and your motors' torque limits. What is the "
            "<b>fastest</b> way to travel it? Like a lap on a known race "
            "track: floor it, then brake as late as possible for the corner. "
            "Along a fixed path the whole robot collapses to one number s, "
            "and each motor's torque limit becomes a limit on how hard you "
            "may speed up or slow down at each point."))

        d = Card("dynamics restricted to a path")
        d.add(math_label(r"\tau=\underbrace{M(q)q'}_{m(s)}\ddot s+"
                         r"\underbrace{\left(Mq''+q'^T\Gamma q'\right)}_{c(s)}\dot s^2+"
                         r"\underbrace{g(q)}_{g(s)}", 16))
        d.add(math_label(r"\tau_i^{min}\leq m_i\ddot s+c_i\dot s^2+g_i\leq\tau_i^{max}"
                         r"\ \Rightarrow\ L(s,\dot s)\leq\ddot s\leq U(s,\dot s)", 16))
        d.add(body(
            "In the (s, ṡ) phase plane the feasible region lies below the "
            "<b>velocity limit curve</b> where L = U. Bobrow / Shin–McKay: "
            "integrate U forward from (0, 0), L backward from (1, 0), and "
            "switch where they meet. If the curves touch the VLC there are "
            "more switches; this page uses the single-switch case."))
        d.add(plain(
            "Plug the path q(s) into τ = Mq̈ + c + g; by the chain rule "
            "everything becomes a function of s, ṡ and s̈. Each motor's min "
            "and max torque then gives a lowest and highest allowed s̈ at "
            "each (s, ṡ): L and U. The <b>phase plane</b>: horizontal = how "
            "far along the path, vertical = how fast. The algorithm: from the "
            "start, accelerate as hard as allowed (follow U); from the end, "
            "run backwards braking as hard as allowed (follow L); where the "
            "two curves cross, switch from accelerating to braking. The "
            "<b>velocity limit curve</b> is the speed above which no torque "
            "can keep you on the path — like the maximum speed for a corner."))
        self.add(d)

        lab = Card("a straight joint-space move of the 2R arm")
        self.t1 = labelled_slider(lab, "shoulder torque limit", 5, 80, 40,
                                  lambda v: f"{v} N·m", self._draw, tracking=False)
        self.t2 = labelled_slider(lab, "elbow torque limit", 3, 40, 15,
                                  lambda v: f"{v} N·m", self._draw, tracking=False)
        self.st_T = Stat("minimum time", "--", theme.GOOD)
        self.st_sw = Stat("switch at s =", "--", theme.WARN)
        lab.add_layout(stat_row(self.st_T, self.st_sw))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        lab.add(plain(
            "Left: the phase plane — red velocity limit curve, green "
            "'accelerate from start', orange 'brake into end', and the cyan "
            "time-optimal profile that rides them, switching at the marked s. "
            "Right: joint torques along the path; at every point some joint "
            "sits at its limit ('bang-bang'). <b>Try:</b> change one torque "
            "limit at a time and watch the minimum time and the switch point "
            "move — usually not in proportion."))
        self.add(lab)
        self._draw()

        self.add(callout(
            "Halve the elbow limit and the minimum time does not double: "
            "different parts of the path are limited by different joints, and "
            "gravity helps on the way down. That non-intuitive coupling is "
            "the whole reason this algorithm exists rather than scaling a "
            "trapezoid by the weakest motor.", "key"))
        self.finish()

    def _draw(self):
        arm = rd.PlanarArm(**ARM)
        lim = [self.t1.value(), self.t2.value()]
        q0, q1 = [-1.4, 1.8], [1.0, 0.2]
        res = rd.time_optimal_line(arm, q0, q1, lim, ns=160)
        self.st_T.set(f"{res['T']:.2f} s")
        self.st_sw.set(f"{res['switch']:.2f}")
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        ax.plot(res["s"], res["vlc"], color=theme.BAD, lw=1.5, label="velocity limit curve")
        ax.plot(res["s"], res["accel"], color=theme.GOOD, ls="--", lw=1, label="max accel from start")
        ax.plot(res["s"], res["decel"], color=theme.WARN, ls="--", lw=1, label="max brake into end")
        ax.plot(res["s"], res["profile"], color=theme.CYAN, lw=2.5, label="time-optimal ṡ(s)")
        ax.set_xlabel("s (path parameter)")
        ax.set_ylabel("ṡ (1/s)")
        ax.set_ylim(0, max(res["profile"].max() * 1.8, 0.5))
        cv.legend(ax, loc="upper right")
        # torque along the optimal profile
        s, sd = res["s"], res["profile"]
        sdd = np.gradient(sd ** 2, s) / 2
        dq = np.array(q1) - np.array(q0)
        taus = []
        for si, sdi, sddi in zip(s, sd, sdd):
            q = np.array(q0) + si * dq
            taus.append(arm.rnea(q, dq * sdi, dq * sddi))
        taus = np.array(taus)
        bx.plot(s, taus[:, 0], color=theme.ACCENT, label="τ₁")
        bx.plot(s, taus[:, 1], color=theme.VIOLET, label="τ₂")
        for v, col in ((lim[0], theme.ACCENT), (lim[1], theme.VIOLET)):
            bx.axhline(v, color=col, ls=":")
            bx.axhline(-v, color=col, ls=":")
        bx.set_xlabel("s")
        bx.set_ylabel("N·m")
        bx.set_title("at every s, some joint is at its limit")
        cv.legend(bx, loc="best")
        cv.refresh()


# ==========================================================================
# Playlist 9 -- motion planning
# ==========================================================================

class MotionPlanningPage(Page):
    TITLE = "Motion Planning in Configuration Space"
    SUBTITLE = ("Obstacles live in the workspace; the planner lives in C-space. "
                "Map every collision to a forbidden (θ₁, θ₂), and planning "
                "an arm becomes finding a path for a point on a torus.")
    SECTION = SEC_PLAN
    NOTES = playlist_badge(9)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(9))
        self.add(start_here(
            "Get the arm from A to B without hitting anything. The trick: do "
            "not plan the arm's shape in the real world; plan a <b>single "
            "point in C-space</b> (page 115). Every arm pose that would "
            "collide becomes a forbidden region on the C-space map. Planning "
            "then becomes a maze: find a route for a dot around the forbidden "
            "blobs."))

        m = Card("the planner families")
        m.add(body(
            "<b>Complete / grid:</b> discretise C-space, run A* (optimal on the "
            "grid, exponential in dimension). Fine for 2–3 DOF.<br>"
            "<b>Sampling-based:</b> RRT grows a tree toward random samples "
            "(single query, probabilistically complete); PRM builds a roadmap "
            "once and answers many queries; RRT* and PRM* are asymptotically "
            "optimal. The workhorse for 6–7 DOF arms (MoveIt/OMPL).<br>"
            "<b>Potential fields:</b> attract to goal, repel from obstacles, "
            "follow −∇U. Fast and reactive, but local minima.<br>"
            "<b>Optimisation:</b> CHOMP, TrajOpt — start from a straight line "
            "and push it out of collision while smoothing it."))
        m.add(plain(
            "<b>Grid A*</b>: chop C-space into cells and search like a GPS — "
            "it finds the shortest route on the grid, but 100 cells per joint "
            "means 100⁶ cells for a 6-joint arm. <b>RRT</b>: throw random "
            "darts and grow a tree from the start toward each one; finds "
            "<i>a</i> route quickly even with many joints, not the shortest. "
            "<b>PRM</b>: build a road map of the free space once and reuse it "
            "for many trips. <b>Potential fields</b>: the goal attracts, "
            "obstacles repel, roll downhill — fast, but you can get stuck in "
            "a dip. <b>Optimisation</b>: start with a straight line and bend "
            "it out of the obstacles."))
        self.add(m)

        lab = Card("two circles in the workspace become blobs in C-space")
        self.ox = labelled_slider(lab, "obstacle 1 x", -15, 15, 9, lambda v: f"{v/10:.1f}", self._draw, tracking=False)
        self.oy = labelled_slider(lab, "obstacle 1 y", -15, 15, 8, lambda v: f"{v/10:.1f}", self._draw, tracking=False)
        self.orr = labelled_slider(lab, "obstacle radius", 1, 6, 3, lambda v: f"{v/10:.1f}", self._draw, tracking=False)
        self.alg = QComboBox()
        self.alg.addItems(["A* on the C-space grid (wraps around)", "RRT (seed 0)"])
        self.alg.currentIndexChanged.connect(self._draw)
        lab.add(self.alg)
        self.st = Stat("path", "--", theme.GOOD)
        self.st_free = Stat("free C-space", "--", theme.ACCENT)
        lab.add_layout(stat_row(self.st, self.st_free))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        lab.add(plain(
            "Left: the real world, with the arm at start (grey) and goal "
            "(green) and a round obstacle. Right: the same scene as a C-space "
            "map; red = every (θ₁, θ₂) where the arm hits the obstacle. A "
            "simple circle in the world becomes a strange blob on the map. "
            "The map's edges wrap (torus, page 115), so A* may leave one side "
            "and come back on the other. <b>Try:</b> drag the obstacle and "
            "watch the blob reshape; make it big enough to block every route. "
            "Switch to RRT: a jagged, non-shortest path from a random tree."))
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“RRT vs PRM vs A* — when each?”</b> A* on a grid: low "
            "dimension, need optimality, map known. PRM: static environment, "
            "many queries (precompute roadmap). RRT/RRT-Connect: one query in "
            "high dimension, fast to first solution; then shortcut/smooth. "
            "RRT* if you need cost convergence. Always: the collision checker "
            "dominates run time, and the output is a path — time scaling "
            "turns it into a trajectory."))
        self.finish()

    def _draw(self):
        L = [1.0, 0.8]
        r = self.orr.value() / 10
        obs = [(self.ox.value() / 10, self.oy.value() / 10, r), (-0.6, -1.0, 0.25)]
        n = 72
        G = rk.cspace_grid_2r(L, obs, n=n)
        qs = np.linspace(-math.pi, math.pi, n, endpoint=False)
        qA, qB = np.array([-2.6, 0.4]), np.array([1.4, -0.3])
        self.st_free.set(f"{100 * (1 - G.mean()):.0f}%")

        def idx(q):
            return tuple(int(round((v + math.pi) / (2 * math.pi) * n)) % n for v in q)

        path_q = None
        tree = None
        if self.alg.currentIndex() == 0:
            path = rk.astar(G, idx(qA), idx(qB))
            if path:
                path_q = np.array([[qs[i], qs[j]] for i, j in path])
        else:
            def free(q):
                return not rk.collides_2r(L, q, obs)
            if free(qA) and free(qB):
                path_q, nodes, parent = rk.rrt(free, qA, qB, [-math.pi] * 2, [math.pi] * 2,
                                               step=0.25, iters=1500, seed=0)
                tree = (nodes, parent)
        if path_q is None:
            self.st.set("none found")
            self.st.set_color(theme.BAD)
        else:
            self.st.set(f"{len(path_q)} waypoints")
            self.st.set_color(theme.GOOD)
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        for (cx, cy, rr) in obs:
            ax.add_patch(Circle((cx, cy), rr, color=theme.BAD, alpha=0.5))
        if path_q is not None:
            for qq in path_q[::max(1, len(path_q) // 10)]:
                draw_arm(ax, L, qq, ghost=True)
        draw_arm(ax, L, qA, color=theme.TEXT_DIM, lw=3)
        draw_arm(ax, L, qB, color=theme.GOOD, lw=3)
        square(ax, 2.0)
        ax.set_title("workspace: start grey, goal green")
        bx.imshow(G.T, origin="lower", extent=[-180, 180, -180, 180],
                  cmap=ListedColormap([theme.BG_INPUT, theme.BAD]), alpha=0.8,
                  aspect="auto", interpolation="nearest")
        if tree is not None:
            nodes, parent = tree
            for i, p in enumerate(parent):
                if p >= 0 and abs(nodes[i] - nodes[p]).max() < 1.0:
                    bx.plot(np.degrees([nodes[i][0], nodes[p][0]]),
                            np.degrees([nodes[i][1], nodes[p][1]]),
                            color=theme.TEXT_FAINT, lw=0.5)
        if path_q is not None:
            P = np.degrees(path_q)
            jumps = np.where(np.abs(np.diff(P, axis=0)).max(axis=1) > 90)[0]
            P = np.insert(P, jumps + 1, np.nan, axis=0)
            bx.plot(P[:, 0], P[:, 1], color=theme.CYAN, lw=2)
        bx.plot(*np.degrees(qA), "o", color=theme.TEXT, ms=8)
        bx.plot(*np.degrees(qB), "*", color=theme.GOOD, ms=12)
        bx.set_xlabel("θ₁ (deg)")
        bx.set_ylabel("θ₂ (deg)")
        bx.set_title("C-space: red = collision (torus — edges wrap)")
        cv.refresh()


# ==========================================================================
# Playlist 10 -- robot control
# ==========================================================================

class MotionControlPage(Page):
    TITLE = "Motion Control: PD + Gravity vs Computed Torque"
    SUBTITLE = ("Independent joint PD ignores the coupling. Adding gravity "
                "compensation makes it provably stable for set-points. "
                "Computed torque cancels M, c and g so the error obeys a "
                "linear ODE you design — as long as the model is right.")
    SECTION = SEC_CTRL
    NOTES = playlist_badge(10)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(10))
        self.add(start_here(
            "Now make the arm actually follow a desired motion. Two classic "
            "controllers. <b>PD + gravity compensation</b>: a spring and "
            "damper on each joint, plus exactly the torque that cancels the "
            "arm's weight — simple, and provably stable for reaching a fixed "
            "target. <b>Computed torque</b>: use the full model (M, c, g) to "
            "cancel all the dynamics, so every joint behaves like an ideal "
            "spring–damper you design — excellent tracking, but only as good "
            "as the model."))

        c = Card("the laws")
        c.add(math_label(r"\mathrm{PD+g:}\ \tau=K_pe+K_d\dot e+\hat g(q)\qquad"
                         r"\mathrm{CTC:}\ \tau=\hat M(q)\left(\ddot q_d+K_d\dot e+K_pe\right)+"
                         r"\hat c(q,\dot q)+\hat g(q)", 15))
        c.add(math_label(r"\hat M=M,\ \hat h=h\ \Rightarrow\ \ddot e+K_d\dot e+K_pe=0", 16))
        c.add(body(
            "Computed torque (inverse-dynamics control, feedback "
            "linearisation) is page 24's idea made exact with the RNEA. "
            "Choose K<sub>p</sub> = ω<sub>n</sub>², K<sub>d</sub> = 2ζω<sub>n</sub> "
            "per joint and every joint is the second-order system of page 11, "
            "decoupled, at every posture. With model error the residual "
            "(M − M̂)q̈ + (h − ĥ) acts as a disturbance the PD must reject."))
        c.add(plain(
            "e = desired angle − actual angle; ė is how fast that error "
            "changes. <b>PD+g</b>: τ = stiffness × e + damping × ė + weight. "
            "<b>Computed torque</b>: first decide the acceleration you want "
            "(the planned one plus corrections from the error), multiply by "
            "M̂ to turn it into torque, then add ĉ and ĝ. The hat ^ means 'my "
            "model of it'. With a perfect model the error obeys ë + "
            "K<sub>d</sub>ė + K<sub>p</sub>e = 0: a damped spring whose speed "
            "(ω<sub>n</sub>) and damping (ζ) you pick. With a wrong model the "
            "leftover terms act like a disturbance the PD has to fight."))
        self.add(c)

        lab = Card("track a fast sinusoid with a wrong model")
        self.err = labelled_slider(lab, "model mass error", -50, 50, 0,
                                   lambda v: f"{v:+d}%", self._sim, tracking=False)
        self.wn = labelled_slider(lab, "ω_n (both joints)", 2, 30, 10,
                                  lambda v: f"{v} rad/s", self._sim, tracking=False)
        self.pay = labelled_slider(lab, "unmodelled payload", 0, 30, 0,
                                   lambda v: f"{v/10:.1f} kg", self._sim, tracking=False)
        self.st_ctc = Stat("CTC RMS error", "--", theme.GOOD)
        self.st_pd = Stat("PD+g RMS error", "--", theme.WARN)
        self.st_pdx = Stat("PD only (no g) RMS", "--", theme.BAD)
        lab.add_layout(stat_row(self.st_ctc, self.st_pd, self.st_pdx))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        lab.add(plain(
            "Three controllers, same gains, track a fast sine on the elbow. "
            "Left: elbow angle against the reference. Right: total error over "
            "time. <b>Try:</b> (1) model error 0 → computed torque (CTC) is "
            "nearly perfect (about 0.03° against 2.6° for PD+g). (2) Model "
            "error ±50 % → CTC's error grows to several degrees, and at +50 % "
            "it is even worse than PD+g: a wrong model can be worse than none. "
            "(3) Raise ω<sub>n</sub> → all errors fall (real robots cap this "
            "because of noise and flexible parts). (4) Add payload → nobody "
            "modelled it. PD without gravity compensation always sags, "
            "because nothing holds the weight."))
        self.add(lab)
        self._sim()

        self.add(interview(
            "<b>“Prove PD + gravity compensation is stable.”</b> Take "
            "V = ½q̇ᵀMq̇ + ½eᵀK<sub>p</sub>e with e = q<sub>d</sub> − q constant "
            "target. dV/dt = q̇ᵀ(τ − c − g) + ½q̇ᵀṀq̇ − eᵀK<sub>p</sub>q̇; "
            "substitute τ and use q̇ᵀ(Ṁ − 2C)q̇ = 0 to get dV/dt = "
            "−q̇ᵀK<sub>d</sub>q̇ ≤ 0. LaSalle: q̇ ≡ 0 forces q̈ = 0, so "
            "K<sub>p</sub>e = 0 — global asymptotic stability. It needs only "
            "g(q), never M."))
        self.finish()

    def _sim(self):
        e = 1 + self.err.value() / 100
        pay = self.pay.value() / 10
        wn = self.wn.value()
        Kp, Kd = np.full(2, wn * wn), np.full(2, 2 * 0.9 * wn)
        m2 = ARM["m"][1] + pay
        r2 = (ARM["m"][1] * ARM["r"][1] + pay * ARM["L"][1]) / m2
        plant = rd.PlanarArm(L=ARM["L"], m=[ARM["m"][0], m2], r=[ARM["r"][0], r2],
                             I=[ARM["I"][0], ARM["I"][1] + pay * (ARM["L"][1] - r2) ** 2])
        model = rd.PlanarArm(L=ARM["L"], m=[x * e for x in ARM["m"]], r=ARM["r"],
                             I=[x * e for x in ARM["I"]])
        Mbar = np.diag(np.diag(model.mass_matrix([0, 1.0])))

        def ref(t):
            w = 2.5
            qd = np.array([0.6 * math.sin(w * t), 1.0 + 0.6 * math.cos(w * t)])
            v = np.array([0.6 * w * math.cos(w * t), -0.6 * w * math.sin(w * t)])
            a = np.array([-0.6 * w * w * math.sin(w * t), -0.6 * w * w * math.cos(w * t)])
            return qd, v, a

        results = {}
        laws = {
            "ctc": lambda t, q, qd: rd.ctc_tau(model, q, qd, *ref(t), Kp, Kd),
            "pdg": lambda t, q, qd: (Mbar @ (Kp * (ref(t)[0] - q) + Kd * (ref(t)[1] - qd))
                                     + model.gravity(q)),
            "pd": lambda t, q, qd: Mbar @ (Kp * (ref(t)[0] - q) + Kd * (ref(t)[1] - qd)),
        }
        for k, law in laws.items():
            ts, Q, _, _ = rd.simulate(plant, [0.0, 1.6], [1.5, 0.0], 4.0, 0.002, law,
                                     method="semi")
            R = np.array([ref(t)[0] for t in ts])
            results[k] = (ts, Q, R)
        rms = {k: math.degrees(math.sqrt(np.mean((Q - R)[len(ts) // 4:] ** 2)))
               for k, (ts, Q, R) in results.items()}
        self.st_ctc.set(f"{rms['ctc']:.2f}°")
        self.st_pd.set(f"{rms['pdg']:.2f}°")
        self.st_pdx.set(f"{rms['pd']:.2f}°")
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        ts, Q, R = results["ctc"]
        ax.plot(ts, np.degrees(R[:, 1]), color=theme.TEXT_DIM, lw=2, label="reference q₂")
        for k, col, nme in (("ctc", theme.GOOD, "CTC"), ("pdg", theme.WARN, "PD + g"),
                            ("pd", theme.BAD, "PD only")):
            ax.plot(results[k][0], np.degrees(results[k][1][:, 1]), color=col, lw=1.2, label=nme)
        ax.set_xlabel("time (s)")
        ax.set_ylabel("elbow angle (deg)")
        cv.legend(ax, loc="lower left")
        for k, col in (("ctc", theme.GOOD), ("pdg", theme.WARN), ("pd", theme.BAD)):
            ts, Q, R = results[k]
            bx.plot(ts, np.degrees(np.linalg.norm(Q - R, axis=1)), color=col)
        bx.set_yscale("log")
        bx.set_xlabel("time (s)")
        bx.set_ylabel("‖q − q_d‖ (deg)")
        bx.set_title("same gains; the model is the difference")
        cv.refresh()


class OperationalSpacePage(Page):
    TITLE = "Task-Space Control and Null-Space Torques"
    SUBTITLE = ("Control the hand directly: F = Λ(ẍ_d + K_d ė + K_p e) + μ + p, "
                "τ = JᵀF. With a redundant arm, add a posture torque through "
                "I − JᵀJ̄ᵀ and the elbow obeys without the hand noticing — "
                "but only if J̄ is the dynamically consistent inverse.")
    SECTION = SEC_CTRL
    NOTES = playlist_badge(10)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(10))
        self.add(start_here(
            "Control the <b>hand</b> directly in x and y instead of the joint "
            "angles. Decide what force the hand needs using the task-space "
            "dynamics of page 132, then turn it into joint torques with τ = "
            "JᵀF (page 123). With a spare joint, add a posture goal through "
            "the null space (page 125) — but for <i>torques</i> the filter "
            "must use the mass-weighted J̄, not the plain J⁺ of the velocity "
            "page."))

        o = Card("operational space control (Khatib)")
        o.add(math_label(r"\tau=J^T\left[\Lambda(\ddot x_d+K_d\dot e+K_pe)+\mu+p\right]+"
                         r"\left(I-J^T\bar J^T\right)\tau_0", 16))
        o.add(body(
            "With the exact model the hand obeys ë + K<sub>d</sub>ė + "
            "K<sub>p</sub>e = 0 in Cartesian coordinates — straight lines stay "
            "straight. The term (I − JᵀJ̄ᵀ)τ<sub>0</sub> is the <b>null-space "
            "torque</b>: J M⁻¹ (I − JᵀJ̄ᵀ) = 0, so it produces no hand "
            "acceleration. Use J⁺ instead of J̄ and the identity fails; the "
            "posture task then pushes the hand around."))
        o.add(body(
            "Cheaper cousins: <b>Jacobian-transpose control</b> τ = Jᵀ(K<sub>p</sub>e "
            "− K<sub>d</sub>ẋ) + g — no Λ, no inverse, stable for set-points by "
            "the same Lyapunov argument as PD+g, but the hand path is curved "
            "and posture-dependent. <b>Resolved-rate</b>: q̇<sub>d</sub> = "
            "J⁺ẋ<sub>d</sub> sent to stiff joint velocity loops — kinematic "
            "only, standard on position-controlled industrial arms.", dim=True))
        o.add(plain(
            "The bracket is the force the hand needs: Λ × the hand "
            "acceleration you want (plus spring–damper corrections from the "
            "hand error), plus the Coriolis and gravity effects felt at the "
            "hand. Jᵀ turns that force into joint torques. The second term is "
            "the posture torque τ₀ passed through the filter I − JᵀJ̄ᵀ, which "
            "guarantees it cannot accelerate the hand. Why J̄ and not J⁺: a "
            "torque turns into motion through M⁻¹, so the filter must know "
            "how the arm's mass spreads a push around. J⁺ is right for "
            "velocities, wrong for torques — it leaks. Cheaper options when "
            "you have no good model: Jᵀ control (a spring pulling the hand) "
            "or resolved-rate (send joint speeds)."))
        self.add(o)

        lab = Card("3R arm: hand traces a circle, elbow chases a posture")
        self.mode = QComboBox()
        self.mode.addItems(["dynamically consistent projector (I − JᵀJ̄ᵀ)",
                            "kinematic projector (I − JᵀJ⁺ᵀ) — leaks",
                            "no posture task"])
        self.mode.currentIndexChanged.connect(self._sim)
        lab.add(self.mode)
        self.kn = labelled_slider(lab, "posture stiffness", 0, 100, 40,
                                  lambda v: f"{v} N·m/rad", self._sim, tracking=False)
        self.post = labelled_slider(lab, "desired elbow angle", -150, 150, -90, deg, self._sim, tracking=False)
        self.st_e = Stat("hand RMS error", "--", theme.GOOD)
        self.st_p = Stat("posture error at end", "--", theme.ACCENT)
        lab.add_layout(stat_row(self.st_e, self.st_p))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        lab.add(plain(
            "The hand traces a circle while a posture task pulls the elbow "
            "toward the angle you set. Right plot (log scale): hand error and "
            "posture error over time. <b>Mode 1</b> (correct J̄ filter): hand "
            "error stays tiny while the elbow moves toward its goal. <b>Mode "
            "2</b> (J⁺ filter): the hand error jumps — the posture task leaks "
            "into the hand. <b>Mode 3</b>: no posture task, the elbow goes "
            "wherever. <b>Try:</b> raise posture stiffness in mode 2 to make "
            "the leak obvious, then switch to mode 1 at the same stiffness."))
        self.add(lab)
        self._sim()

        self.add(interview(
            "<b>“Your humanoid's arm task fights its posture task. How do "
            "you make the posture task strictly secondary?”</b> Project the "
            "posture torque through the dynamically consistent null space "
            "N = I − JᵀJ̄ᵀ with J̄ = M⁻¹JᵀΛ, so it generates zero task "
            "acceleration. For many tasks, nest the projectors (strict "
            "hierarchy) or solve a hierarchical QP (soft/strict priorities "
            "plus torque and contact constraints) — what modern whole-body "
            "controllers do."))
        self.finish()

    def _sim(self):
        arm = rd.PlanarArm(L=[1.0, 0.8, 0.5], m=[2.0, 1.5, 0.8])
        mode = self.mode.currentIndex()
        kn = self.kn.value()
        post = np.array([0.0, math.radians(self.post.value()), 0.6])
        c0, R, w = np.array([1.1, 0.5]), 0.35, 2.0
        Kp, Kd = np.full(2, 150.0), np.full(2, 2 * math.sqrt(150.0))

        def law(t, q, qd):
            xr = c0 + R * np.array([math.cos(w * t), math.sin(w * t)])
            vr = R * w * np.array([-math.sin(w * t), math.cos(w * t)])
            ar = -R * w * w * np.array([math.cos(w * t), math.sin(w * t)])
            if mode == 2:
                return rd.osc_tau(arm, q, qd, xr, vr, ar, Kp, Kd)
            return rd.osc_tau(arm, q, qd, xr, vr, ar, Kp, Kd, q_post=post,
                              Kp_null=kn, Kd_null=math.sqrt(max(kn, 1.0)),
                              consistent=(mode == 0))

        # start on the circle, already moving with it, so the error shown is
        # what the projector does and not a start-up transient
        q0, _, _ = rk.ik_newton(arm.L, c0 + np.array([R, 0.0]), [0.2, 1.2, -1.0])
        qd0 = rk.pinv_damped(arm.jacobian(q0)) @ np.array([0.0, R * w])
        ts, Q, QD, _ = rd.simulate(arm, q0, qd0, 2 * math.pi / w, 0.01, law)
        X = np.array([arm.tip(q) for q in Q])
        Xr = c0 + R * np.column_stack([np.cos(w * ts), np.sin(w * ts)])
        e = np.linalg.norm(X - Xr, axis=1)
        self.st_e.set(f"{1000 * math.sqrt(np.mean(e ** 2)):.2f} mm")
        self.st_e.set_color(theme.GOOD if e.max() < 0.005 else theme.BAD)
        self.st_p.set(f"{math.degrees(Q[-1, 1] - post[1]):+.1f}° (elbow)")
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        for k in range(0, len(ts), len(ts) // 8):
            draw_arm(ax, arm.L, Q[k], ghost=True)
        draw_arm(ax, arm.L, Q[-1])
        ax.plot(Xr[:, 0], Xr[:, 1], color=theme.TEXT_DIM, ls="--", lw=1)
        ax.plot(X[:, 0], X[:, 1], color=theme.CYAN, lw=1.5)
        square(ax, 2.4)
        ax.set_title("dashed: reference circle; cyan: hand")
        bx.semilogy(ts, np.maximum(e * 1000, 1e-6), color=theme.WARN, label="hand error (mm)")
        bx.plot(ts, np.abs(np.degrees(Q[:, 1] - post[1])) + 1e-6, color=theme.VIOLET,
                 label="|elbow − posture| (deg)")
        bx.set_xlabel("time (s)")
        cv.legend(bx, loc="best")
        cv.refresh()


class ForceControlPage(Page):
    TITLE = "Force, Hybrid and Task-Space Impedance Control"
    SUBTITLE = ("Touching the world turns half the task directions into force "
                "directions. Hybrid control splits them with a selection "
                "matrix; impedance control refuses to split and specifies the "
                "relationship between them instead.")
    SECTION = SEC_CTRL
    NOTES = playlist_badge(10)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(10))
        self.add(start_here(
            "When the hand touches something you cannot choose both position "
            "<i>and</i> force in the same direction: pressing on a wall, the "
            "wall decides where the hand is; you only decide how hard to "
            "push. <b>Hybrid control</b> picks per direction — force into the "
            "wall, motion along it. <b>Impedance control</b> refuses to pick: "
            "it makes the hand behave like a spring–damper, so the force "
            "follows from how far the hand is pushed off its target."))

        h = Card("natural and artificial constraints")
        h.add(body(
            "Wiping a table: the table forbids motion along z (natural "
            "constraint) and the robot cannot command force along x, y "
            "without moving (it is free there). So <b>command force along "
            "z, motion along x, y</b> — the artificial constraints are "
            "complementary to the natural ones. In k contact directions you "
            "control force, in 6 − k you control motion; you never control "
            "both along the same direction."))
        h.add(math_label(r"\tau=J^T\left[\Lambda\,P\,(\ddot x_d+K_d\dot e+K_pe)+"
                         r"(I-P)\,(F_d+K_{fi}\int e_F)+\mu+p\right]", 15))
        h.add(math_label(r"\mathrm{impedance:}\quad M_d\ddot{\tilde x}+B_d\dot{\tilde x}+"
                         r"K_d\tilde x=F_{ext}", 16))
        h.add(body(
            "P is the motion selection projector (built in the contact "
            "frame), I − P the force one. <b>Impedance</b> (Hogan) is the "
            "task-space version of pages 36–38: a virtual mass–spring–damper "
            "at the hand. Stable in contact with any passive environment "
            "when the rendered impedance is passive — which is why it, and "
            "not pure force control, is the default for contact-rich "
            "manipulation.", dim=True))
        h.add(plain(
            "<b>Natural constraints</b>: what the world dictates (cannot move "
            "into the table). <b>Artificial constraints</b>: what you command "
            "in the remaining directions (a force into the table, motion "
            "across it). In the hybrid law P is a selector that keeps the "
            "motion directions and I − P keeps the force directions; the "
            "force loop adds the integral of the force error so the push "
            "settles on F<sub>d</sub>. In the impedance law M<sub>d</sub>, "
            "B<sub>d</sub>, K<sub>d</sub> are a virtual mass, damper and "
            "spring that you choose, x̃ is how far the hand is from its "
            "target, and F<sub>ext</sub> is the push from outside. A soft "
            "K<sub>d</sub> makes contact gentle. 'Passive' = never creates "
            "energy by itself, so it stays stable touching anything that is "
            "passive too."))
        self.add(h)

        lab = Card("2R hand slides along a wall while pressing on it")
        lab.add(body(
            "Wall at x = 1.2 m, modelled as a stiff spring k<sub>w</sub>. "
            "Hybrid: force loop along x (target F<sub>d</sub>), motion loop "
            "along y (sinusoid). Impedance: one spring–damper toward a "
            "target placed slightly <i>inside</i> the wall; the contact "
            "force becomes K × penetration, not a commanded number.", dim=True))
        self.mode = QComboBox()
        self.mode.addItems(["hybrid motion/force", "task-space impedance"])
        self.mode.currentIndexChanged.connect(self._sim)
        lab.add(self.mode)
        self.fd = labelled_slider(lab, "desired force F_d", 0, 40, 15, lambda v: f"{v} N", self._sim, tracking=False)
        self.kw = labelled_slider(lab, "wall stiffness", 1, 50, 10,
                                  lambda v: f"{v} kN/m", self._sim, tracking=False)
        self.st_f = Stat("mean contact force", "--", theme.ACCENT)
        self.st_ey = Stat("y tracking RMS", "--", theme.GOOD)
        lab.add_layout(stat_row(self.st_f, self.st_ey))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        lab.add(plain(
            "Wall at x = 1.2 m. <b>Hybrid</b>: along x a force loop drives "
            "the push to F<sub>d</sub>; along y the hand follows a sine. "
            "<b>Impedance</b>: the hand's target sits 1 cm inside the wall "
            "and its spring is chosen to give F<sub>d</sub> against a rigid "
            "wall; the actual force = spring × how far the target is past the "
            "hand. <b>Try:</b> compare the mean force with F<sub>d</sub> in "
            "each mode, then lower the wall stiffness: with impedance the "
            "wall gives way, the spring stretches less and the force drops "
            "below F<sub>d</sub>, while the hybrid force loop keeps pushing "
            "until it gets F<sub>d</sub>."))
        self.add(lab)
        self._sim()

        self.add(interview(
            "<b>“Force control or impedance control for peg-in-hole?”</b> "
            "Impedance (or admittance on a stiff, geared arm): low stiffness "
            "laterally so misalignment produces small forces that guide the "
            "peg, higher stiffness along insertion. Pure force control is "
            "fragile at contact transitions (free space has no force to "
            "regulate) and against stiff surfaces; hybrid needs a correct "
            "contact-frame model. State whether the hardware is "
            "torque-controlled (impedance) or position-controlled "
            "(admittance) — page 38's decision."))
        self.finish()

    def _sim(self):
        arm = rd.PlanarArm(**ARM)
        xw = 1.2
        kw = self.kw.value() * 1000.0
        Fd = float(self.fd.value())
        hybrid = self.mode.currentIndex() == 0
        q = rk.ik_2r(*arm.L, xw - 0.01, 0.4, 1)
        qd = np.zeros(2)
        dt = 0.001
        ts, F, Y, YR = [], [], [], []
        eI = 0.0
        for k in range(int(2.5 / dt)):
            t = k * dt
            x = arm.tip(q)
            J = arm.jacobian(q)
            xd = J @ qd
            pen = max(0.0, x[0] - xw)
            f_wall = -kw * pen - (60.0 * xd[0] if pen > 0 else 0.0)   # on the tip, +x
            yr = 0.4 + 0.25 * math.sin(1.5 * t)
            vy = 0.25 * 1.5 * math.cos(1.5 * t)
            ay = -0.25 * 2.25 * math.sin(1.5 * t)
            Lam, Jbar, mu, p = arm.task_space(q, qd)
            if hybrid:
                fx_meas = -f_wall
                eF = Fd - fx_meas
                eI += eF * dt
                ay_cmd = ay + 40 * (vy - xd[1]) + 400 * (yr - x[1])
                F_task = np.array([Fd + 0.5 * eF + 20.0 * eI - 15.0 * xd[0],
                                   (Lam @ np.array([0.0, ay_cmd]))[1]])
                F_task = F_task + mu + p
            else:
                K, B = np.array([Fd / 0.01 if Fd > 0 else 100.0, 400.0]), np.array([40.0, 40.0])
                xt = np.array([xw + 0.01, yr])
                F_task = K * (xt - x) + B * (np.array([0.0, vy]) - xd) + p
            tau = J.T @ F_task
            qdd = np.linalg.solve(arm.mass_matrix(q), tau + J.T @ np.array([f_wall, 0.0])
                                  - arm.h(q, qd))
            qd = qd + dt * qdd
            q = q + dt * qd
            if k % 5 == 0:
                ts.append(t)
                F.append(-f_wall)
                Y.append(x[1])
                YR.append(yr)
        ts, F, Y, YR = map(np.array, (ts, F, Y, YR))
        half = len(ts) // 3
        self.st_f.set(f"{F[half:].mean():.1f} N (target {Fd:.0f})")
        self.st_ey.set(f"{1000 * math.sqrt(np.mean((Y - YR)[half:] ** 2)):.1f} mm")
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        ax.plot(ts, F, color=theme.ACCENT, label="contact force (N)")
        ax.axhline(Fd, color=theme.TEXT_DIM, ls="--", label="F_d")
        ax.set_xlabel("time (s)")
        ax.set_ylabel("N")
        cv.legend(ax, loc="best")
        bx.plot(ts, YR, color=theme.TEXT_DIM, ls="--", label="y reference")
        bx.plot(ts, Y, color=theme.GOOD, label="hand y")
        bx.set_xlabel("time (s)")
        bx.set_ylabel("m")
        cv.legend(bx, loc="best")
        cv.refresh()


# ==========================================================================
# Playlist 11 -- grasping
# ==========================================================================

class GraspingPage(Page):
    TITLE = "Grasping: Friction Cones and Force Closure"
    SUBTITLE = ("A grasp is a set of contacts whose wrenches can resist any "
                "external wrench. With friction each contact contributes a "
                "cone of forces; force closure means those cones positively "
                "span every force and moment.")
    SECTION = SEC_MANIP
    NOTES = playlist_badge(11)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(11))
        self.add(start_here(
            "When is an object held securely? Each fingertip can push into "
            "the surface and, thanks to friction, a little sideways. The set "
            "of forces a finger can apply without slipping is a <b>cone</b> — "
            "the friction cone. A grasp has <b>force closure</b> when the "
            "fingers together can resist any push or twist on the object just "
            "by squeezing harder."))

        c = Card("contacts, cones and closure")
        c.add(math_label(r"\|f_t\|\leq\mu f_n,\qquad \mathcal{F}_i=\begin{bmatrix}p_i\times f_i\\ "
                         r"f_i\end{bmatrix},\qquad \mathrm{pos\,span}\{\mathcal{F}_{i,j}\}="
                         r"\mathbb{R}^{3\ \mathrm{(planar)}\ \mathrm{or}\ 6}", 15))
        c.add(body(
            "<b>Form closure</b>: geometry alone (frictionless contacts) "
            "immobilises the body — needs at least 4 contacts in the plane, 7 "
            "in space. <b>Force closure</b>: with friction, the contact "
            "wrenches can balance any external wrench by squeezing — 2 "
            "contacts suffice in the plane if the line between them lies "
            "inside both friction cones (antipodal grasp), 3 in space. Test: "
            "the edge wrenches of all cones must positively span the wrench "
            "space; equivalently the origin is strictly inside their convex "
            "hull."))
        c.add(plain(
            "‖f<sub>t</sub>‖ ≤ μf<sub>n</sub>: the sideways force can be at "
            "most μ times the pressing force, otherwise the finger slips. The "
            "cone's half-angle is atan μ (μ = 0.3 → about 17°). Each contact "
            "force also makes a twist on the object, so it is written as a "
            "wrench (moment, force). Force closure = by adding positive "
            "amounts of the cone forces you can produce <i>any</i> wrench, so "
            "any disturbance can be cancelled. Form closure = held by shape "
            "alone, no friction, which needs more contacts. Two-finger rule: "
            "the line joining the fingertips must lie inside both cones."))
        self.add(c)

        lab = Card("two-finger grasp of a disc-shaped part")
        self.mu = labelled_slider(lab, "friction coefficient μ", 0, 100, 30,
                                  lambda v: f"{v/100:.2f}", self._draw)
        self.a2 = labelled_slider(lab, "finger 2 position on rim", 0, 360, 180, deg, self._draw)
        self.third = QCheckBox("add a third finger at 270°")
        self.third.stateChanged.connect(self._draw)
        lab.add(self.third)
        self.st = Stat("force closure?", "--", theme.GOOD)
        self.st_ang = Stat("angle between normal and grasp line", "--", theme.ACCENT)
        self.st_cone = Stat("cone half-angle atan μ", "--", theme.VIOLET)
        lab.add_layout(stat_row(self.st, self.st_ang, self.st_cone))
        self.cv = MplCanvas(width=7.4, height=3.8)
        lab.add(self.cv)
        lab.add(plain(
            "Finger 1 is fixed at 0° on the rim; you move finger 2. Orange "
            "wedges are the friction cones, the dashed line joins the fingers "
            "(green = closure, red = not). On a disc every surface normal "
            "points at the centre, so the angle between the grasp line and "
            "the normal is half of how far finger 2 is from directly "
            "opposite. <b>Try:</b> (1) at 180° the line runs along both "
            "normals — closure for any μ > 0. (2) Move finger 2 away until "
            "that angle passes the cone half-angle — closure is lost. (3) "
            "Raise μ: wider cones, more positions work. (4) μ = 0: a "
            "two-finger grasp can never resist a twist."))
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“How do you know a two-finger grasp is stable?”</b> Planar "
            "antipodal test: the segment joining the two contacts must lie "
            "inside both friction cones, i.e. its angle to each surface "
            "normal is below atan μ. Then squeezing harder resists any "
            "disturbance wrench (force closure). For spatial grasps check that "
            "the cone edges positively span ℝ⁶ (an LP), and use the grasp "
            "quality metric (largest ball of wrenches resisted per unit "
            "squeeze) to rank candidates."))
        self.finish()

    def _draw(self):
        mu = self.mu.value() / 100
        angs = [0.0, math.radians(self.a2.value())]
        if self.third.isChecked():
            angs.append(math.radians(270))
        pts = [(math.cos(a), math.sin(a)) for a in angs]
        nrm = [(-math.cos(a), -math.sin(a)) for a in angs]
        W = rk.contact_wrenches_planar(pts, nrm, mu)
        fc = rk.force_closure_planar(W)
        self.st.set("YES" if fc else "no")
        self.st.set_color(theme.GOOD if fc else theme.BAD)
        line = np.array(pts[1]) - np.array(pts[0])
        if np.linalg.norm(line) < 1e-9:
            self.st_ang.set("fingers coincide")
        else:
            ang = math.degrees(math.acos(max(-1, min(1, line @ np.array(nrm[0])
                                                   / np.linalg.norm(line)))))
            self.st_ang.set(f"{ang:.1f}°")
        self.st_cone.set(f"{math.degrees(math.atan(mu)):.1f}°")
        cv = self.cv
        cv.clear()
        ax = cv.ax
        t = np.linspace(0, 2 * math.pi, 200)
        ax.fill(np.cos(t), np.sin(t), color=theme.BG_RAISED, ec=theme.TEXT_DIM)
        for p, n in zip(pts, nrm):
            p, n = np.array(p), np.array(n)
            tng = np.array([-n[1], n[0]])
            for s in (1, -1):
                e = n + s * mu * tng
                e = e / np.linalg.norm(e)
                ax.plot([p[0], p[0] + 0.8 * e[0]], [p[1], p[1] + 0.8 * e[1]], color=theme.WARN, lw=1.5)
            ax.fill([p[0], p[0] + 0.8 * (n + mu * tng)[0] / np.linalg.norm(n + mu * tng),
                     p[0] + 0.8 * (n - mu * tng)[0] / np.linalg.norm(n - mu * tng)],
                    [p[1], p[1] + 0.8 * (n + mu * tng)[1] / np.linalg.norm(n + mu * tng),
                     p[1] + 0.8 * (n - mu * tng)[1] / np.linalg.norm(n - mu * tng)],
                    color=theme.WARN, alpha=0.2)
            ax.plot(*p, "o", color=theme.CYAN, ms=10)
        ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]], color=theme.GOOD if fc else theme.BAD,
                ls="--")
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-1.8, 1.8)
        ax.set_ylim(-1.5, 1.5)
        ax.set_title("orange: friction cones; dashed: grasp line")
        cv.refresh()


# ==========================================================================
# Playlist 12 -- wheeled mobile robots
# ==========================================================================

class MobileRobotPage(Page):
    TITLE = "Wheeled Mobile Robots: Nonholonomic Motion"
    SUBTITLE = ("Omni wheels can move any direction instantly. A differential "
                "drive or car cannot slide sideways — two velocity inputs for "
                "three coordinates — yet it reaches every pose. Control it by "
                "steering a point just ahead of the axle.")
    SECTION = SEC_MANIP
    NOTES = playlist_badge(12)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(12))
        self.add(start_here(
            "Wheeled robots. Omni and mecanum wheels can move in any "
            "direction instantly — easy. A normal two-wheeled robot (a robot "
            "vacuum) or a car <b>cannot slide sideways</b>: it has 2 controls "
            "(forward speed, turn rate) for 3 position numbers (x, y, "
            "heading). It can still reach any spot and heading (parallel "
            "parking), but steering it there needs more care than a simple "
            "feedback law."))

        k = Card("kinematics of the unicycle / differential drive")
        k.add(math_label(r"\begin{bmatrix}\dot x\\ \dot y\\ \dot\phi\end{bmatrix}="
                         r"\begin{bmatrix}\cos\phi&0\\ \sin\phi&0\\ 0&1\end{bmatrix}"
                         r"\begin{bmatrix}v\\ \omega\end{bmatrix},\quad "
                         r"v=r\frac{u_R+u_L}{2},\ \omega=r\frac{u_R-u_L}{2d}", 15))
        k.add(body(
            "The columns are the two allowed motions (drive, spin). Their "
            "Lie bracket is the sideways direction: wiggling forward/turn/"
            "back/turn makes net lateral progress, which is parallel parking "
            "and the reason the system is <b>controllable</b> though not "
            "smoothly <b>stabilisable</b> to a point (Brockett). Omni and "
            "mecanum bases have u = H(φ)q̇ with H full rank 3: holonomic, "
            "control is trivial."))
        k.add(body(
            "<b>Mobile manipulation</b>: stack the base's allowed twists "
            "(through H⁺ or the unicycle matrix) with the arm Jacobian, "
            "J<sub>e</sub> = [J<sub>base</sub> J<sub>arm</sub>]; the result "
            "is usually redundant, so the null-space page applies directly.",
            dim=True))
        k.add(plain(
            "The matrix says: forward speed v moves you along your heading "
            "(cos φ, sin φ); turn rate ω changes the heading. With wheel "
            "speeds u: the average of the two wheels drives forward, their "
            "difference turns (r = wheel radius, d = half the distance "
            "between the wheels). <b>Lie bracket</b> in plain words: small "
            "forward, turn, back, turn-back moves leave you shifted sideways "
            "— how you wiggle a car out of a tight spot. <b>Brockett</b>: "
            "because of this, no smooth fixed feedback law can park the robot "
            "exactly at a point. Mobile manipulation: put the base's allowed "
            "motions and the arm's Jacobian side by side in one bigger "
            "Jacobian."))
        self.add(k)

        lab = Card("track a figure-eight with the look-ahead point")
        self.off = labelled_slider(lab, "look-ahead distance", 2, 50, 15,
                                   lambda v: f"{v/100:.2f} m", self._draw)
        self.gain = labelled_slider(lab, "feedback gain k", 1, 100, 20,
                                    lambda v: f"{v/10:.1f}", self._draw)
        self.st_e = Stat("final tracking error", "--", theme.GOOD)
        self.st_lat = Stat("max sideways slip", "--", theme.ACCENT)
        lab.add_layout(stat_row(self.st_e, self.st_lat))
        self.cv = MplCanvas(width=7.4, height=3.8)
        lab.add(self.cv)
        lab.add(plain(
            "The trick: the axle centre cannot move sideways, but a point a "
            "short distance <i>ahead</i> of it can move in any direction "
            "(drive and turn together). So control that look-ahead point with "
            "ordinary feedback toward the moving reference. Dashed = "
            "reference figure-eight, cyan = axle path, arrows = heading. "
            "<b>Try:</b> small look-ahead → tight tracking but sharp "
            "steering; large → smooth but cuts the corners. Gain k = how hard "
            "it corrects. The sideways-slip stat stays near zero: the no-skid "
            "rule is never broken."))
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“Why can't you just use a PD on (x, y, φ) for a "
            "differential-drive robot?”</b> There are only two inputs and the "
            "lateral direction is not directly actuated, so the linearisation "
            "at a standstill is uncontrollable and no smooth static feedback "
            "stabilises a pose. Track a moving reference instead "
            "(look-ahead point, pure pursuit, Kanayama), use time-varying or "
            "discontinuous feedback for parking, or plan with Reeds–Shepp / "
            "Dubins curves."))
        self.finish()

    def _draw(self):
        off = self.off.value() / 100
        k = self.gain.value() / 10

        def path(t):
            w = 0.5
            p = np.array([1.2 * math.sin(w * t), 0.6 * math.sin(2 * w * t)])
            v = np.array([1.2 * w * math.cos(w * t), 1.2 * w * math.cos(2 * w * t)])
            return p, v

        ts, X, R = rk.unicycle_track(path, 14.0, 0.01, k, off)
        P = X[:, :2] + off * np.column_stack([np.cos(X[:, 2]), np.sin(X[:, 2])])
        e = np.linalg.norm(P - R, axis=1)
        d = np.diff(X[:, :2], axis=0)
        lat = np.abs(-np.sin(X[:-1, 2]) * d[:, 0] + np.cos(X[:-1, 2]) * d[:, 1]).max()
        self.st_e.set(f"{e[-1] * 1000:.1f} mm")
        self.st_lat.set(f"{lat:.1e} m/step")
        cv = self.cv
        cv.clear()
        ax = cv.ax
        ax.plot(R[:, 0], R[:, 1], color=theme.TEXT_DIM, ls="--", label="reference")
        ax.plot(X[:, 0], X[:, 1], color=theme.CYAN, lw=1.5, label="axle centre")
        for i in range(0, len(ts), 120):
            x, y, ph = X[i]
            ax.arrow(x, y, 0.12 * math.cos(ph), 0.12 * math.sin(ph), color=theme.WARN,
                     width=0.01, head_width=0.05)
        ax.set_aspect("equal", adjustable="datalim")
        cv.legend(ax, loc="lower left")
        cv.refresh()


# ==========================================================================
# Interview drill
# ==========================================================================

_DRILL = [
    ("Kinematics", [
        ("What is the Jacobian, and what does each column mean?",
         "J(q) maps joint velocities to end-effector twist, V = Jq̇. Column i is the twist produced by joint i alone at unit speed — for the space Jacobian, joint i's screw axis at its current pose."),
        ("Why does the same J map forces back as τ = JᵀF?",
         "Power balance: τᵀq̇ = Fᵀ(Jq̇) for every q̇, so τ = JᵀF. It is frame independent: J_bᵀF_b = J_sᵀF_s."),
        ("What is a singularity? Give two examples.",
         "rank J < m: some hand direction needs infinite joint speed and a matching force costs zero torque. 2R arm fully stretched (boundary); 6R wrist with axes 4 and 6 aligned (interior)."),
        ("What is the null space of J used for?",
         "Joint motions with zero hand velocity. q̇ = J⁺ẋ + (I − J⁺J)q̇₀ runs a secondary objective (joint limits, manipulability, obstacles) without disturbing the task."),
        ("Analytic vs numerical IK?",
         "Analytic: all branches, constant time, needs special geometry (spherical wrist). Numerical Newton–Raphson / DLS: general, handles redundancy and constraints, needs a seed, can converge to the wrong branch or stall at singularities."),
        ("What does damped least squares fix?",
         "J⁺ blows up as σ_min → 0. J^T(JJ^T + λ²I)⁻¹ caps the gain at 1/(2λ), trading tracking error for bounded joint rates near singularities."),
    ]),
    ("Dynamics", [
        ("Write the manipulator equation and name every term.",
         "M(q)q̈ + C(q,q̇)q̇ + g(q) = τ + JᵀF_ext. M inertia (SPD), Cq̇ Coriolis q̇ᵢq̇ⱼ and centripetal q̇ᵢ² terms, g gravity = ∂P/∂q, friction often added as Bq̇ + f_c sign(q̇)."),
        ("Why is M symmetric positive definite? Why does it matter?",
         "K = ½q̇ᵀMq̇ > 0 for any motion. M⁻¹ always exists, so forward dynamics is never singular, and M defines an energy metric used in every Lyapunov proof."),
        ("What is the skew-symmetry property?",
         "With Christoffel C, Ṁ − 2C is skew, so q̇ᵀ(Ṁ − 2C)q̇ = 0 and dE/dt = q̇ᵀτ: the arm is passive. Basis of PD+g stability and adaptive control."),
        ("Inverse vs forward dynamics — algorithms and cost?",
         "Inverse: τ from (q,q̇,q̈), recursive Newton–Euler O(n), used by controllers. Forward: q̈ from τ, ABA O(n) or CRBA O(n²) + Cholesky O(n³), used by simulators."),
        ("How does RNEA handle gravity?",
         "Set the base acceleration to −g (i.e., +g upward). Every link then 'feels' gravity through the acceleration recursion; no separate gravity terms are needed."),
        ("What is the operational-space inertia Λ?",
         "Λ = (JM⁻¹Jᵀ)⁻¹, the inertia felt at the hand. Direction and posture dependent, infinite at singularities along the lost direction; it sets collision forces and is what OSC cancels."),
        ("How do you identify the dynamic parameters of a real arm?",
         "τ = Y(q,q̇,q̈)π is linear in the base parameters π (masses, first moments, inertias, friction). Excite with optimised periodic trajectories, filter, least squares; enforce physical consistency (positive mass, valid inertia)."),
    ]),
    ("Control", [
        ("Computed torque vs PD + gravity?",
         "CTC cancels M, c, g so every joint becomes ë + K_dė + K_pe = 0 — great tracking, needs an accurate model. PD+g only needs g, is globally stable for set-points, but tracking degrades with speed."),
        ("How do you control the hand in Cartesian space?",
         "OSC: F = Λ(ẍ_d + K_dė + K_pe) + μ + p, τ = JᵀF. Simpler: Jacobian-transpose τ = JᵀK e + g (stable, no inversion), or resolved-rate q̇ = J⁺ẋ on a position-controlled arm."),
        ("Why the dynamically consistent null space?",
         "Only N = I − JᵀJ̄ᵀ with J̄ = M⁻¹JᵀΛ satisfies JM⁻¹N = 0, so posture torques create no hand acceleration. The kinematic J⁺ version leaks."),
        ("Impedance vs admittance vs hybrid force control?",
         "Impedance: motion in, force out — needs torque-controllable, backdrivable joints. Admittance: force in, motion out — for stiff geared position-controlled arms with a F/T sensor. Hybrid: force along constrained, motion along free directions via a selection matrix."),
        ("How would you detect a collision without a skin?",
         "Momentum observer: r = K(p(t) − ∫(τ + Cᵀq̇ − g + r)dt − p(0)), p = Mq̇. r ≈ τ_ext with first-order dynamics, no q̈ needed; threshold it per joint."),
    ]),
]


class InterviewDrillPage(Page):
    TITLE = "Interview Drill: Kinematics, Dynamics, Control"
    SUBTITLE = ("The questions a robotics interview asks, each answered in two "
                "sentences you should be able to say out loud and then derive "
                "on a whiteboard. Cover the answer, say yours, then reveal.")
    SECTION = SEC_MANIP
    NOTES = "drill · all playlists"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "How to use this page: take one card at a time. Read each "
            "question, say your answer out loud in two sentences, then tick "
            "<b>show answers</b> and compare. Any answer you could not give "
            "points to a page: go back to that page's START HERE and IN PLAIN "
            "WORDS boxes, rewatch its playlist, and try again tomorrow. "
            "Finish with the eight whiteboard derivations at the bottom."))
        self.chk = QCheckBox("show answers")
        self.chk.setChecked(False)
        self.chk.stateChanged.connect(self._toggle)
        self.add(self.chk)
        self.answers = []
        for topic, qa in _DRILL:
            c = Card(topic)
            for q, a in qa:
                c.add(body(f"<b>Q.</b> {q}"))
                lb = body(f"<span style='color:{theme.GOOD}'><b>A.</b></span> {a}", dim=True)
                lb.setVisible(False)
                self.answers.append(lb)
                c.add(lb)
            self.add(c)

        w = Card("whiteboard derivations to rehearse until automatic")
        w.add(body(
            "1. Forward kinematics and Jacobian of a 2R arm, then det J = "
            "L₁L₂ sin q₂.<br>"
            "2. τ = JᵀF from virtual work.<br>"
            "3. Lagrangian dynamics of a single link, then the 2R M(q).<br>"
            "4. One pass of RNEA for a 2R arm, gravity as base acceleration.<br>"
            "5. Λ = (JM⁻¹Jᵀ)⁻¹ from q̈ = M⁻¹(JᵀF − h).<br>"
            "6. Lyapunov proof of PD + gravity compensation using Ṁ − 2C skew.<br>"
            "7. q̇ = J⁺ẋ + (I − J⁺J)q̇₀ and why J N = 0.<br>"
            "8. Nonholonomic constraint of a unicycle and why it is not "
            "integrable."))
        self.add(w)

        self.add(callout(
            "The last interview went to the controller. The fix is not to "
            "forget the controller — it is to start one level lower: when "
            "asked about a robot, first say what the configuration and task "
            "spaces are, write the kinematics and the Jacobian, write "
            "M q̈ + c + g = τ + JᵀF, and only then choose the control law. "
            "Every controller on pages 16–41 is a statement about that "
            "equation.", "key"))
        self.finish()

    def _toggle(self):
        for lb in self.answers:
            lb.setVisible(self.chk.isChecked())
