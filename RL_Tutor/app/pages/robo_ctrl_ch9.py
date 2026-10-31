"""
Chapter 9 lecture videos (Podcast/captions/Chapter9), as cards for pages 140-141.

    9.1-9.2 part 1   trajectory, path, time scaling; straight lines in joint space,
                     task space and SE(3)
    9.1-9.2 part 2   cubic, quintic, trapezoidal and S-curve time scalings
    9.3              polynomial via-point trajectories; B-splines
    9.4 part 1       dynamics along a path; torque limits become L <= s'' <= U
    9.4 part 2       the (s, s') phase plane, motion cones, bang-bang
    9.4 part 3       the velocity limit curve and the tangent-point algorithm

Every card carries one worked example with numbers; the step labs embedded on
the pages compute the same quantities live.
"""

from __future__ import annotations

from ..widgets import Card, body, math_label
from .robo_common import plain
from .robo_space_rigid import in_words, video_tag
from .robo_dyn_ch8 import _table


# ---------------------------------------------------------------- page 140
def path_video_card() -> Card:
    c = Card("video 9.1–9.2, part 1 — trajectory = path + time scaling")
    c.add(video_tag(
        "9.1", "point-to-point trajectories (part 1 of 2)",
        "A controller streams desired configurations thousands of times a second; θ(t), "
        "t ∈ [0, T], is a trajectory. Split it into a path θ(s), s ∈ [0, 1] (geometry) and a "
        "time scaling s(t) (speed). Then straight-line paths in joint space, task space and "
        "SE(3)."))
    c.add(math_label(r"\dot\theta=\frac{d\theta}{ds}\dot s,\qquad "
                     r"\ddot\theta=\frac{d\theta}{ds}\ddot s+\frac{d^2\theta}{ds^2}\dot s^2", 16))
    c.add(body(
        "<b>Worked numbers.</b> The video's 2R move: 180° on joint 1, 150° on joint 2, so on a "
        "straight joint line θ′ = (3.142, 2.618) rad and θ″ = 0. With a quintic, T = 2 s, at "
        "t = 0.8 s: s = 0.317, ṡ = 0.864 /s, s̈ = 0.720 /s². Then θ̇ = θ′ṡ = (2.71, 2.26) rad/s "
        "and θ̈ = θ′s̈ = (2.26, 1.88) rad/s². On a Cartesian line θ″ ≠ 0, so θ̈ picks up "
        "θ″ṡ² even while ṡ is constant."))
    c.add(body(_table(
        ("path", "formula", "property"),
        [("joint-space line", "θ(s) = θ_start + s(θ_end − θ_start)",
          "stays in the joint-limit box (convex); the hand curves"),
         ("task-space line", "X(s) = X_start + s(X_end − X_start), θ = IK(X)",
          "hand straight; can leave the (non-convex) workspace"),
         ("screw path in SE(3)", "X(s) = X_start exp(log(X_start⁻¹X_end) s)",
          "constant twist, written in {start}: exponential on the right"),
         ("decoupled", "p(s) on a line, R(s) = R_start exp(log(R_startᵀR_end) s)",
          "origin straight, rotation about an axis fixed in the frame")])))
    c.add(plain(
        "Both θ(s) and s(t) must be twice differentiable, because the dynamics need θ̈. "
        "SE(3) elements cannot be subtracted — that is why the frame paths use exp and log."))
    return c


def scaling_video_card() -> Card:
    c = Card("video 9.1–9.2, part 2 — the four standard time scalings")
    c.add(video_tag(
        "9.2", "point-to-point trajectories (part 2 of 2)",
        "Cubic (4 coefficients, 4 terminal constraints), quintic (6 and 6), trapezoidal "
        "(accelerate, coast, decelerate) and the 7-segment S-curve with bounded jerk."))
    c.add(math_label(r"\begin{bmatrix}1&0&0&0\\1&T&T^2&T^3\\0&1&0&0\\0&1&2T&3T^2\end{bmatrix}"
                     r"\begin{bmatrix}a_0\\a_1\\a_2\\a_3\end{bmatrix}=\begin{bmatrix}0\\1\\0\\0\end{bmatrix}"
                     r"\ \Rightarrow\ a=\left(0,\,0,\,\frac{3}{T^2},\,-\frac{2}{T^3}\right)", 14))
    c.add(body(
        "<b>Worked numbers, T = 2 s.</b> Cubic: a = (0, 0, 0.75, −0.25); ṡ_max = 3/(2T) = 0.75 /s; "
        "s̈ jumps from 0 to 6/T² = 1.5 /s² at t = 0. Quintic: a₃ = 10/T³ = 1.25, a₄ = −15/T⁴ = "
        "−0.9375, a₅ = 6/T⁵ = 0.1875; ṡ_max = 15/(8T) = 0.9375 /s, s̈_max = 10/(√3T²) = 1.443 /s², "
        "and s̈(0) = s̈(T) = 0. Trapezoid with v = 0.8 /s, a = 1.2 /s²: v²/a = 0.533 ≤ 1, so it "
        "cruises; T = (a + v²)/(va) = 1.917 s, accelerating for v/a = 0.667 s."))
    c.add(plain(
        "Cubic and trapezoid have acceleration jumps (infinite jerk); quintic and S-curve do not. "
        "The real joint speed is (θ_end − θ_start)·ṡ, so it depends on the distance and on T, "
        "not only on the shape of s(t)."))
    return c


def via_video_card() -> Card:
    c = Card("video 9.3 — polynomial via-point trajectories")
    c.add(video_tag(
        "9.3", "polynomial via point trajectories",
        "Choose configurations and times to pass through (and, optionally, velocities there), "
        "and solve directly for the trajectory: one cubic per joint per segment."))
    c.add(math_label(r"a_{j0}=\beta_j,\ a_{j1}=\dot\beta_j,\ "
                     r"a_{j2}=\frac{3\beta_{j+1}-3\beta_j-2\dot\beta_j\Delta T-\dot\beta_{j+1}\Delta T}{\Delta T^2},\ "
                     r"a_{j3}=\frac{2\beta_j+(\dot\beta_j+\dot\beta_{j+1})\Delta T-2\beta_{j+1}}{\Delta T^3}", 13))
    c.add(body(
        "<b>Worked numbers.</b> Joint 1 from β = 0 at T = 0 (at rest) to β = 1.2 rad at T = 1 s "
        "with β̇ = 1.2 rad/s there: ΔT = 1, a₀ = 0, a₁ = 0, a₂ = 3(1.2) − 1.2 = 2.4, "
        "a₃ = −2(1.2) + 1.2 = −1.2. Check: 2.4 − 1.2 = 1.2 ✓, slope 4.8 − 3.6 = 1.2 ✓. "
        "Acceleration at the end of this segment is 2(2.4) + 6(−1.2) = −2.4 rad/s²; the next "
        "segment starts with its own 2a₂, generally different — the jump the video points out."))
    c.add(body(_table(
        ("method", "you give", "continuous", "note"),
        [("cubic, specified via velocities", "times, positions, velocities", "θ, θ̇",
          "θ̈ jumps at vias; velocities steer the shape"),
         ("cubic, times only", "times, positions", "θ, θ̇, θ̈",
          "via velocities come out of a small linear system"),
         ("B-spline", "control points", "smooth",
          "does not pass through them; stays in their convex hull → respects joint limits")])))
    return c


# ---------------------------------------------------------------- page 141
def topt_dyn_video_card() -> Card:
    c = Card("video 9.4, part 1 — dynamics along the path, and bounds on s̈")
    c.add(video_tag(
        "9.4", "time-optimal time scaling (part 1 of 3)",
        "Fix θ(s); find the fastest s(t) that respects the torque limits. On the path the "
        "dynamics collapse to one scalar unknown: τ = m(s)s̈ + c(s)ṡ² + g(s)."))
    c.add(math_label(r"m(s)=M\theta',\quad c(s)=M\theta''+\theta'^T\Gamma\theta',\quad g(s)=g(\theta(s))", 15))
    c.add(math_label(r"m_i>0:\ L_i=\frac{\tau_i^{min}-c_i\dot s^2-g_i}{m_i},\ U_i=\frac{\tau_i^{max}-c_i\dot s^2-g_i}{m_i};"
                     r"\quad m_i<0:\ \text{swap}\qquad L=\max_iL_i,\ U=\min_iU_i", 14))
    c.add(body(
        "<b>Worked numbers</b> (page 141's arm, straight path θ = (−1.4, 1.8) → (1.0, 0.2), "
        "|τ₁| ≤ 40, |τ₂| ≤ 15 N·m) at s = 0.4, ṡ = 2 /s: θ = (−0.44, 1.16), m = (6.231, 0.831), "
        "c = (2.816, 3.168), g = (26.614, 4.425). Joint 1: L₁ = (−40 − 11.27 − 26.61)/6.231 = −12.50, "
        "U₁ = (40 − 37.88)/6.231 = 0.34. Joint 2: L₂ = (−15 − 12.67 − 4.43)/0.831 = −38.62, "
        "U₂ = (15 − 17.10)/0.831 = −2.53. So L = −12.50, U = −2.53: at this speed the elbow "
        "already forces braking."))
    c.add(in_words(
        "If at some (s, ṡ) the largest lower bound exceeds the smallest upper bound, no torque "
        "keeps the arm on the path — it is moving too fast for its motors. The step lab at the "
        "top of the card below prints m, c, g, every L_i and U_i at the state you pick."))
    return c


def topt_phase_video_card() -> Card:
    c = Card("video 9.4, part 2 — the phase plane, motion cones and bang-bang")
    c.add(video_tag(
        "9.4", "time-optimal time scaling (part 2 of 3)",
        "Draw ṡ against s. At each state the time scaling's tangent (ṡ, s̈) must lie in the "
        "feasible motion cone s̈ ∈ [L, U]. Integrate U forward from (0, 0) and L backward from "
        "(1, 0); switch where they cross."))
    c.add(body(
        "<b>Worked numbers</b> for the same move: the forward-U and backward-L curves cross at "
        "s* = 0.812, ṡ* ≈ 1.79 /s, and T = ∫ ds/ṡ = 0.88 s. Along the profile every point has "
        "some |τ_i| at its limit (the lab's torque plot touches ±40 or ±15 N·m throughout)."))
    c.add(plain(
        "Velocity limit curve: raising ṡ at fixed s narrows the cone until L = U (a single "
        "allowed acceleration); above it, none. If forward U and backward L run into that curve "
        "instead of each other, bang-bang is impossible — part 3."))
    return c


def topt_algo_video_card() -> Card:
    c = Card("video 9.4, part 3 — when the velocity limit curve gets in the way")
    c.add(video_tag(
        "9.4", "time-optimal time scaling (part 3 of 3)",
        "Integrate L back from the end; integrate U forward from the start. If U hits the "
        "velocity limit curve at s_lim, search for the tangent point, integrate L back from it "
        "to the U curve (switch s₁), mark the tangent point as s₂, and continue with U."))
    c.add(body(_table(
        ("step", "what is computed", "numbers (bulged path, b = 0.9)"),
        [("2", "L backward from (1, 0)", "stops at the VLC near s = 0.93"),
         ("3", "U forward from (0, 0)", "hits the VLC at s_lim ≈ 0.72"),
         ("4", "lower ṡ at s_lim, integrate L forward; binary search", "tangent at s_tan ≈ 0.892"),
         ("5", "L backward from the tangent point to the U curve", "switch s₁ ≈ 0.479 (U → L)"),
         ("6", "tangent point = s₂, then U forward again", "meets the final L curve: s₃ ≈ 0.946"),
         ("—", "result", "U, L, U, L: three switches, T ≈ 0.98 s")])))
    c.add(plain(
        "Every actuator margin is used up, and the model is never exact, so the algorithm is "
        "rarely run directly on hardware; it tells you the robot's maximum capability along a "
        "path."))
    return c
