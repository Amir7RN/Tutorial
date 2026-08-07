"""
Nonlinear systems, and the five things people actually do about them.

Everything in `linear.py` rests on one property: SUPERPOSITION. Double the
input, double the output; add two inputs, add the two outputs. A transfer
function, a pole, a Bode plot and a phase margin all exist only because of it.

A real robot violates superposition in at least six places before you have
even written a controller:

    gravity        g(q) ~ sin(q)          torque depends on posture
    Coriolis       C(q, q') q'            quadratic in velocity
    inertia        M(q)                   the mass matrix MOVES as it folds
    friction       Coulomb + stiction     discontinuous at zero velocity
    actuator       saturation             the plant changes when you ask too much
    transmission   backlash, hysteresis   the output depends on the past

So the honest position is not "the robot is linear" but "the robot is linear
ENOUGH, near this operating point, at this amplitude" -- and the job of this
module is to make the boundary of that statement visible.

The pendulum is used throughout as the smallest system that shows every
nonlinear phenomenon at once:

    J th'' + b th' + m g l sin(th) = tau

Two equilibria (hanging and inverted), one stable and one not, an amplitude-
dependent period, and no transfer function anywhere.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


# ==========================================================================
# The nonlinear elements a real drivetrain is full of
# ==========================================================================

def saturation(u: float, limit: float) -> float:
    """
    The nonlinearity you cannot design away: every actuator has a current
    limit and therefore a torque limit.

    Its effect on a loop is exact and worth stating: above the limit the
    EFFECTIVE gain of your controller falls, because the extra command is
    thrown away. A loop tuned at small amplitude can be sluggish or unstable
    at large amplitude with no parameter having changed. That amplitude
    dependence is the signature of a nonlinearity.
    """
    return max(-limit, min(limit, u))


def deadzone(u: float, width: float) -> float:
    """Nothing happens until |u| exceeds width -- valve overlap, PWM deadtime,
    the gap in a gear mesh. Kills small corrections, so it shows up as a
    limit cycle: the loop hunts around the setpoint but never reaches it."""
    if abs(u) <= width:
        return 0.0
    return u - math.copysign(width, u)


def coulomb_friction(omega: float, f_c: float, v_eps: float = 1e-3) -> float:
    r"""
    Coulomb (sliding) friction torque, always OPPOSING the motion:

        |w| > v_eps :   -f_c * sign(w)
        |w| ~ 0     :   0 here -- sticking is a separate regime, because the
                        held torque depends on what is being applied, not on
                        the velocity. `run_stick_slip` implements it properly.

    Discontinuous at w = 0, which is exactly why it is hard: the derivative
    does not exist there, so linearisation is not merely inaccurate, it is
    undefined. Stick-slip, hunting and the dead band around a setpoint all
    come from this one term.
    """
    if abs(omega) < v_eps:
        return 0.0
    return -f_c * math.copysign(1.0, omega)


def backlash(u: float, state: float, width: float) -> float:
    """
    Gear backlash as a play element: the output follows the input only after
    the free gap of `width` has been taken up, and holds otherwise.

    Backlash has MEMORY -- the output depends on which way you were last
    moving -- so it is not just nonlinear, it is not even a function of the
    current input. No transfer function can represent it.
    """
    if u > state + width / 2:
        return u - width / 2
    if u < state - width / 2:
        return u + width / 2
    return state


# ==========================================================================
# The pendulum
# ==========================================================================

@dataclass
class Pendulum:
    """
    J th'' + b th' + m g l sin(th) = tau

    theta = 0 is HANGING DOWN. theta = pi is inverted.

    Chosen because it is the honest minimum: a robot arm against gravity is a
    pendulum, a biped is an inverted pendulum, and an ankle holding you
    upright is an inverted pendulum with a spring. Everything demonstrated on
    it transfers directly.
    """
    m: float = 1.0
    l: float = 0.5
    b: float = 0.15
    g: float = 9.81

    @property
    def J(self) -> float:
        return self.m * self.l * self.l

    def gravity_torque(self, theta: float) -> float:
        """m g l sin(theta) -- the term that makes it nonlinear. Note it is
        LARGEST horizontal and ZERO at both equilibria, which is why a robot
        arm needs most torque halfway through a lift, not at the ends."""
        return self.m * self.g * self.l * math.sin(theta)

    def accel(self, theta: float, omega: float, tau: float) -> float:
        return (tau - self.b * omega - self.gravity_torque(theta)) / self.J

    def energy(self, theta: float, omega: float) -> float:
        """
        E = kinetic + potential, measured from hanging.

        Energy is the Lyapunov function that makes the pendulum's stability
        provable without solving anything: with tau = 0, dE/dt = -b w^2 <= 0,
        so energy can only fall, so the motion can only settle. That single
        line is Lyapunov's direct method in miniature.
        """
        return 0.5 * self.J * omega ** 2 + \
            self.m * self.g * self.l * (1.0 - math.cos(theta))

    # -- linearisation ------------------------------------------------
    def linearise(self, theta0: float) -> tuple[np.ndarray, np.ndarray]:
        r"""
        Jacobian linearisation about theta0, as (A, B) for x = [th - th0, w]:

            A = [[0, 1], [-(m g l cos th0)/J, -b/J]],   B = [[0], [1/J]]

        The whole nonlinearity collapses into ONE number: the cos(theta0) in
        the corner. And its SIGN decides everything.

            theta0 = 0   (hanging):   -m g l / J  < 0   ->  stable, oscillatory
            theta0 = pi  (inverted):  +m g l / J  > 0   ->  a REAL POLE IN THE
                                                            RIGHT HALF PLANE
            theta0 = pi/2 (horizontal):        0        ->  double integrator

        Same pendulum, same equations, three completely different linear
        systems. That is what "linearisation is only local" means in practice.
        """
        a21 = -self.m * self.g * self.l * math.cos(theta0) / self.J
        A = np.array([[0.0, 1.0], [a21, -self.b / self.J]])
        B = np.array([[0.0], [1.0 / self.J]])
        return A, B

    def linear_poles(self, theta0: float) -> list[complex]:
        A, _ = self.linearise(theta0)
        return [complex(v) for v in np.linalg.eigvals(A)]

    def unstable_pole_inverted(self) -> float:
        """
        For the undamped inverted pendulum the RHP pole sits at

            s = + sqrt(g / l)

        A 1 m pendulum gives 3.1 rad/s, so its natural doubling time is about
        220 ms. That number is why balance loops must run fast and why a
        200 ms perception stall is a fall: you have to close the loop
        comfortably faster than the instability grows.
        """
        return math.sqrt(self.g / self.l)


# ==========================================================================
# Phase portraits -- the right picture for a nonlinear system
# ==========================================================================

def phase_field(pend: Pendulum, th_range=(-math.pi, 3 * math.pi),
                w_range=(-10.0, 10.0), n_th: int = 21, n_w: int = 15,
                tau_fn=None):
    """
    A grid of (theta, omega, dtheta, domega) arrows.

    Why a phase portrait rather than a step response: a nonlinear system has
    no single response to characterise it -- the answer depends on where you
    start and how hard you push. The phase plane shows ALL initial conditions
    at once, and the features that matter (equilibria, separatrices, limit
    cycles, basins of attraction) are visible as shapes rather than numbers.
    """
    tau_fn = tau_fn or (lambda th, w: 0.0)
    out = []
    for i in range(n_th):
        th = th_range[0] + (th_range[1] - th_range[0]) * i / (n_th - 1)
        for j in range(n_w):
            w = w_range[0] + (w_range[1] - w_range[0]) * j / (n_w - 1)
            out.append((th, w, w, pend.accel(th, w, tau_fn(th, w))))
    return out


def trajectory(pend: Pendulum, theta0: float, omega0: float,
               duration: float = 6.0, dt: float = 2e-3, tau_fn=None,
               tau_limit: float = math.inf, max_steps: int = 12000):
    """
    One trajectory through the phase plane, RK4.

    Plain floats rather than numpy arrays: the state is two numbers, and at
    that size numpy's per-call overhead is several times the arithmetic. These
    run behind live sliders.
    """
    tau_fn = tau_fn or (lambda th, w, t: 0.0)
    n_steps = int(duration / dt)
    if n_steps > max_steps:
        n_steps = max_steps
        dt = duration / n_steps
    h2, h6 = dt / 2.0, dt / 6.0

    def f(t, th, w):
        tau = saturation(tau_fn(th, w, t), tau_limit)
        return w, pend.accel(th, w, tau)

    th, w = float(theta0), float(omega0)
    ts, ths, ws, taus = [], [], [], []
    for i in range(n_steps):
        t = i * dt
        tau = saturation(tau_fn(th, w, t), tau_limit)
        ts.append(t)
        ths.append(th)
        ws.append(w)
        taus.append(tau)
        k1a, k1b = f(t, th, w)
        k2a, k2b = f(t + h2, th + h2 * k1a, w + h2 * k1b)
        k3a, k3b = f(t + h2, th + h2 * k2a, w + h2 * k2b)
        k4a, k4b = f(t + dt, th + dt * k3a, w + dt * k3b)
        th += h6 * (k1a + 2 * k2a + 2 * k3a + k4a)
        w += h6 * (k1b + 2 * k2b + 2 * k3b + k4b)
    return ts, ths, ws, taus


def separatrix(pend: Pendulum, n: int = 400):
    """
    The energy contour through the inverted equilibrium of the UNDAMPED
    pendulum: E = 2 m g l.

    It is the boundary of the basin of attraction -- start inside it and the
    pendulum swings back and forth forever, start outside and it goes over the
    top and rotates. A linear system has no such thing: its basin is always
    the entire state space. The existence of a boundary at all is a purely
    nonlinear fact, and it is what "our controller is stable" fails to say.
    """
    e_sep = 2.0 * pend.m * pend.g * pend.l
    ths, w_up, w_dn = [], [], []
    for i in range(n):
        th = -math.pi + 4 * math.pi * i / (n - 1)
        val = 2.0 * (e_sep - pend.m * pend.g * pend.l * (1 - math.cos(th))) / pend.J
        w = math.sqrt(max(0.0, val))
        ths.append(th)
        w_up.append(w)
        w_dn.append(-w)
    return ths, w_up, w_dn


def large_angle_period(pend: Pendulum, amplitude: float) -> float:
    r"""
    Period of the undamped pendulum at a given swing amplitude, from the
    exact elliptic-integral series:

        T = T0 * (1 + (1/16)A^2 + (11/3072)A^4 + ...)

    The amplitude-dependent period is the cleanest possible demonstration
    that superposition is gone. A linear oscillator has ONE frequency,
    forever, whatever you do to it. This one slows down as it swings wider --
    5 degrees and 90 degrees differ by 18%.
    """
    t0 = 2 * math.pi * math.sqrt(pend.l / pend.g)
    a = amplitude
    return t0 * (1.0 + a ** 2 / 16.0 + 11.0 * a ** 4 / 3072.0
                 + 173.0 * a ** 6 / 737280.0)


# ==========================================================================
# The five approaches
# ==========================================================================

def pd_controller(kp: float, kd: float, theta_d: float = math.pi):
    """
    Approach 0 -- ignore the nonlinearity and hope.

    Works near the setpoint if the gains are high enough to dominate gravity,
    and fails in a very specific way: a standing error of exactly
    m g l sin(theta)/Kp, because the spring must be stretched to hold the
    weight. Same standoff argument as the impedance pages.
    """
    def law(th, w, t):
        return -kp * (th - theta_d) - kd * w
    return law


def gravity_comp_pd(pend: Pendulum, kp: float, kd: float,
                    theta_d: float = math.pi, model_error: float = 0.0):
    r"""
    Approach 1 -- FEEDFORWARD the term you understand.

        tau = m g l sin(theta) + Kp(th_d - th) - Kd w

    The gravity term is cancelled exactly, and what is left for the PD to do
    is a linear double integrator. Steady-state error vanishes without an
    integrator, because feedback is no longer being asked to hold the load.

    `model_error` scales the compensation, because the honest question is not
    "does it work with a perfect model" but "how fast does it degrade with a
    wrong one". 20% error leaves 20% of gravity uncancelled -- which is still
    five times better than not trying.
    """
    def law(th, w, t):
        comp = (1.0 + model_error) * pend.m * pend.g * pend.l * math.sin(th)
        return comp - kp * (th - theta_d) - kd * w
    return law


def computed_torque(pend: Pendulum, kp: float, kd: float, traj_fn=None,
                    model_error: float = 0.0):
    r"""
    Approach 2 -- FEEDBACK LINEARISATION (in robotics: computed torque).

        tau = J ( th_d'' + Kd e' + Kp e ) + b w + m g l sin(th)

    Substitute it into the plant and every nonlinear term cancels, leaving

        e'' + Kd e' + Kp e = 0

    which is a linear second-order error system with poles you chose. This is
    the workhorse of manipulator control, and the multi-DOF version
    tau = M(q)(q_d'' + Kd e' + Kp e) + C(q,q')q' + g(q) is the same idea with
    matrices.

    The price, and it is not small: you have cancelled the nonlinearity using
    a MODEL. Every term you get wrong reappears as a disturbance, and unlike a
    PD controller there is no inherent robustness margin -- the method's
    strength is exactness, so its weakness is exactness. Hence `model_error`,
    and hence sliding mode below.
    """
    traj_fn = traj_fn or (lambda t: (math.pi, 0.0, 0.0))
    scale = 1.0 + model_error

    def law(th, w, t):
        th_d, w_d, a_d = traj_fn(t)
        e, ed = th_d - th, w_d - w
        v = a_d + kd * ed + kp * e
        return scale * (pend.J * v + pend.b * w + pend.gravity_torque(th))
    return law


def sliding_mode(pend: Pendulum, lam: float = 6.0, eta: float = 8.0,
                 boundary: float = 0.0, theta_d: float = math.pi,
                 model_error: float = 0.0):
    r"""
    Approach 3 -- SLIDING MODE. Robustness bought with discontinuity.

    Define a sliding surface that IS the error dynamics you want:

        s = e' + lambda e          s = 0  =>  e(t) = e(0) e^{-lambda t}

    then drive s to zero with a term big enough to overwhelm any bounded
    model error:

        tau = model terms + J ( lambda e' ) + eta * sign(s)

    Once on the surface, the response is exactly first-order with time
    constant 1/lambda REGARDLESS of the model being wrong -- that is the
    remarkable part, and it is why sliding mode survives payload changes that
    break computed torque.

    The cost is CHATTERING: sign(s) switches at every sample, exciting
    unmodelled resonances and heating the motor. The standard fix is a
    boundary layer -- replace sign(s) with saturation(s/phi) -- which trades a
    little tracking accuracy for a continuous command. Set `boundary` > 0 to
    see the trade directly.
    """
    scale = 1.0 + model_error

    def law(th, w, t):
        e = theta_d - th
        ed = -w
        s = ed + lam * e
        switch = (math.copysign(1.0, s) if boundary <= 0
                  else max(-1.0, min(1.0, s / boundary)))
        feedforward = scale * (pend.b * w + pend.gravity_torque(th))
        return feedforward + pend.J * lam * ed + eta * switch
    return law


def gain_scheduled_pd(pend: Pendulum, wn: float, zeta: float,
                      theta_d: float = math.pi):
    r"""
    Approach 4 -- GAIN SCHEDULING. Linearise everywhere, interpolate between.

    The linearisation of the pendulum has stiffness -m g l cos(theta), which
    changes sign across the workspace. A single fixed PD is therefore
    over-damped in one posture and under-damped in another. Scheduling
    chooses Kp(theta) so the CLOSED-LOOP poles stay put:

        Kp(th) = J wn^2 + m g l cos(th)
        Kd     = 2 zeta wn J

    This is what most industrial robots actually run, and its limitation is
    the classic one: it is only valid if the parameter varies SLOWLY compared
    with the loop. Schedule on something that changes fast and the
    interpolation itself becomes a dynamic you did not model.
    """
    kd = 2.0 * zeta * wn * pend.J

    def law(th, w, t):
        kp = pend.J * wn * wn + pend.m * pend.g * pend.l * math.cos(th)
        return -kp * (th - theta_d) - kd * w
    return law


def energy_swingup(pend: Pendulum, k_e: float = 1.2, tau_limit: float = 1.2,
                   catch: float = 0.5, kp: float = 40.0, kd: float = 8.0):
    r"""
    Approach 5 -- ENERGY SHAPING, the passivity-based idea in its simplest form.

    Differentiate the pendulum's energy along its own trajectory:

        E   = 1/2 J w^2 + m g l (1 - cos th)
        E'  = w (tau - b w)   ~   tau * w

    so the input can only change the energy through the product tau*w. Choose

        tau = k_e ( E_top - E ) sign(w)

    and E' is positive whenever the pendulum has too little energy, negative
    when it has too much, whatever the state. Pump until the energy EQUALS
    that of the inverted equilibrium, then hand over to a local PD to catch it.

    This inverts a pendulum whose motor CANNOT lift it directly -- the torque
    limit here is a fraction of m g l -- because it never fights the dynamics,
    it feeds them at the rate they will accept.

    It is also the honest miniature of why impedance control is safe: a
    controller that adds no more energy than the environment can absorb is
    PASSIVE, and a passive controller cannot destabilise a passive
    environment, whatever that environment turns out to be. That is a far
    stronger guarantee than any gain or phase margin, because it holds without
    knowing what you are about to touch.
    """
    e_top = 2.0 * pend.m * pend.g * pend.l

    def law(th, w, t):
        # nearest upright angle, in the SAME unwrapped frame as th -- after a
        # few rotations th may be 3*pi, and pulling it back to +pi would mean
        # commanding a whole extra turn
        n = round((th - math.pi) / (2.0 * math.pi))
        target = math.pi + 2.0 * math.pi * n
        if abs(th - target) < catch:
            return -kp * (th - target) - kd * w
        e = pend.energy(th, w)
        u = k_e * (e_top - e) * (1.0 if w >= 0 else -1.0)
        return saturation(u, tau_limit)
    return law


# ==========================================================================
# Limit cycles: the phenomenon linear systems cannot have
# ==========================================================================

@dataclass
class StickSlipTrace:
    t: list = field(default_factory=list)
    theta: list = field(default_factory=list)
    omega: list = field(default_factory=list)
    tau: list = field(default_factory=list)
    stuck: list = field(default_factory=list)


def run_stick_slip(kp: float = 20.0, kd: float = 1.0, ki: float = 60.0,
                   f_static: float = 6.0, f_coulomb: float = 2.5,
                   inertia: float = 0.25, viscous: float = 0.05,
                   theta_d: float = 0.5, duration: float = 8.0,
                   dt: float = 5e-4) -> StickSlipTrace:
    r"""
    A position loop against stiction -- and the two distinct failures it gives
    you, depending on whether there is integral action.

    WITHOUT an integrator (ki = 0): the joint sticks wherever the proportional
    torque first falls below breakaway and STAYS there, permanently off
    target. A dead zone of width f_static/Kp around the setpoint that no
    amount of patience removes. This is not a limit cycle; it is worse, because
    nothing about it looks like a fault.

    WITH an integrator (ki > 0): the error can no longer be tolerated, so:

        1. the joint is stuck; error persists; the INTEGRATOR climbs
        2. the command finally exceeds the breakaway torque f_static
        3. friction instantly drops to the lower sliding value f_coulomb, so
           there is a torque SURPLUS and the joint lurches
        4. it overshoots, velocity crosses zero, it sticks on the other side
        5. the integrator now unwinds the other way -- go to 1

    The result is a self-sustaining oscillation whose amplitude is set by the
    friction drop f_static - f_coulomb, not by the initial condition, and which
    tuning does not remove: lower the gain and it hunts more slowly, raise it
    and it hunts harder.

    A linear system cannot do this. Linear oscillations decay, grow, or sit
    exactly on the stability boundary; none of those is amplitude-locked. A
    LIMIT CYCLE -- isolated, self-sustaining, independent of where you started
    -- is available only to a nonlinear system, and stiction is the most
    common source of one in a robot.

    The real fixes are mechanical (better bearings, preload, lower ratio) or
    feedforward (a friction model, a dither signal), not a different gain.
    """
    tr = StickSlipTrace()
    th, w, integ = 0.0, 0.0, 0.0
    stuck = True
    for i in range(int(duration / dt)):
        t = i * dt
        e = theta_d - th
        integ += ki * e * dt
        tau = kp * e + integ - kd * w
        net = tau - viscous * w
        if stuck:
            if abs(net) > f_static:
                stuck = False
                fric = -math.copysign(f_coulomb, net)
            else:
                fric = -net                    # static friction holds it
        else:
            fric = (-math.copysign(f_coulomb, w) if abs(w) > 1e-6
                    else -math.copysign(f_coulomb, net))
        alpha = (net + fric) / inertia
        w += alpha * dt
        th += w * dt
        if not stuck and abs(w) < 1e-3 and abs(net) < f_static:
            stuck = True
            w = 0.0
        tr.t.append(t)
        tr.theta.append(th)
        tr.omega.append(w)
        tr.tau.append(tau)
        tr.stuck.append(1.0 if stuck else 0.0)
    return tr


def describing_function_saturation(amplitude: float, limit: float) -> float:
    r"""
    Equivalent gain of a saturation element to a sine of the given amplitude:

        N(A) = 1                                        A <= limit
        N(A) = (2/pi)( asin(k) + k sqrt(1 - k^2) ),  k = limit/A

    The describing-function method: pretend the nonlinearity is a gain that
    depends on AMPLITUDE, then reuse all the linear machinery. It predicts
    limit cycles as the intersection of the Nyquist curve with -1/N(A), and it
    is an approximation (it assumes the loop filters out harmonics) -- but it
    is the standard way to get a number out of a saturating loop, and it
    explains why a loop that is stable when it barely moves can hunt when
    driven hard.
    """
    if amplitude <= limit:
        return 1.0
    k = limit / amplitude
    return (2.0 / math.pi) * (math.asin(k) + k * math.sqrt(1.0 - k * k))


# ==========================================================================
# Lyapunov
# ==========================================================================

def lyapunov_pd_pendulum(pend: Pendulum, kp: float, theta_d: float,
                         theta: float, omega: float) -> float:
    r"""
    A Lyapunov candidate for gravity-compensated PD regulation:

        V = 1/2 J w^2 + 1/2 Kp (th - th_d)^2         >= 0, zero only at rest

    Differentiate along the closed-loop trajectories with
    tau = g(th) + Kp(th_d - th) - Kd w:

        V' = -(Kd + b) w^2   <= 0

    So V can only fall, and by LaSalle's theorem the motion must end where
    V' = 0 and stays there -- which is exactly th = th_d, w = 0.

    Read what that just achieved: a stability PROOF for a nonlinear system,
    with no linearisation, no poles, and without solving the differential
    equation. That is the whole appeal of Lyapunov's direct method, and its
    whole difficulty is that nothing tells you how to find V. For mechanical
    systems the answer is nearly always the same: try the energy.
    """
    return 0.5 * pend.J * omega ** 2 + 0.5 * kp * (theta - theta_d) ** 2


def lyapunov_rate(pend: Pendulum, kd: float, omega: float) -> float:
    """V' = -(Kd + b) w^2 -- negative semi-definite, which is enough."""
    return -(kd + pend.b) * omega ** 2
