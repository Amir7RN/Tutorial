"""
The four control paradigms, as runnable simulations.

    position     command a position, let a stiff loop chase it
    torque       command a torque, do not look at where you end up
    impedance    motion in  -> force out    (measure theta, command tau)
    admittance   force in   -> motion out   (measure F,     command theta)

plus the decoupled impedance controller of Best, Rouse & Gregg, which shows
that the first three are all the same controller with different knobs.

Every simulation here is a plain explicit-Euler loop over a 1-DOF joint. Small
enough to read in one sitting, which is the point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# ==========================================================================
# A 1-DOF plant to control
# ==========================================================================

@dataclass
class Joint:
    """
    One rotational joint:  J*ddot(th) + b*dot(th) = tau_motor + tau_ext

    `b` is real physical friction in the bearing, not a control gain.
    """
    inertia: float = 0.25
    friction: float = 0.4
    theta: float = 0.0
    omega: float = 0.0

    def step(self, tau_motor: float, tau_ext: float, dt: float):
        alpha = (tau_motor + tau_ext - self.friction * self.omega) / self.inertia
        self.omega += alpha * dt
        self.theta += self.omega * dt
        return alpha

    def reset(self, theta=0.0, omega=0.0):
        self.theta, self.omega = theta, omega


# ==========================================================================
# Impedance control -- "motion in, force out"
# ==========================================================================

def impedance_torque(theta, omega, theta_d, omega_d, k, b, tau_ff=0.0) -> float:
    r"""
    The virtual spring-damper, in the decoupled form:

        tau = -K (theta - theta_d) - B (dot theta - dot theta_d) + tau_ff

    Read it as: "here is where I want to be; push me away from there and I
    push back in proportion." You are never commanding a position. You are
    commanding a *relationship* between displacement and force.

    Set tau_ff = 0 and this is exactly a PD position controller. That is not
    a coincidence -- see `equilibrium_angle` and Property 1 below.
    """
    return -k * (theta - theta_d) - b * (omega - omega_d) + tau_ff


def equilibrium_angle(theta_d, omega_d, k, b, tau_ff) -> float:
    r"""
    Convert the decoupled parameters back to the classic textbook form

        tau = -K (theta - theta_eq) - B dot theta

    via  theta_eq = theta_d + (tau_ff + B dot theta_d) / K.

    This is the number that confuses everybody: theta_eq is NOT where you
    want the joint to go. It is a control input chosen so that, once the
    ground and the user have pushed back, the joint ends up on theta_d.
    Two controllers with wildly different theta_eq can walk identically.
    """
    if abs(k) < 1e-12:
        return math.inf
    return theta_d + (tau_ff + b * omega_d) / k


def tau_ff_from_deviation(k, b, theta_hat, omega_d) -> float:
    r"""
    The reverse map, using the deviation angle  hat(theta) = theta_eq - theta_d:

        tau_ff = K hat(theta) - B dot(theta)_d
    """
    return k * theta_hat - b * omega_d


def impedance_magnitude(k: float, b: float) -> float:
    """
    ||Z|| = |K| + |B| -- where a controller sits on the spectrum.

        ||Z|| = 0      pure feedforward torque control
                       (prioritises nominal TORQUES; position drifts)
        ||Z|| small    soft, compliant, transparent
        ||Z|| large    stiff, high-gain position control
                       (prioritises nominal POSITIONS; torque does whatever
                        it must)

    Almost every published "impedance controller" lives in the middle. The
    useful insight is that this is a design knob, not a category.
    """
    return abs(k) + abs(b)


# ==========================================================================
# Admittance control -- "force in, motion out"
# ==========================================================================

@dataclass
class VirtualModel:
    """
    The ghost robot an admittance controller pretends to move.

        M_v ddot(x) + B_v dot(x) + K_v x = F_ext

    M_v  how heavy you want the robot to FEEL (not what it weighs)
    B_v  how viscous the air feels
    K_v  pull back toward the origin; usually 0 for transparent following
    """
    m_v: float = 2.0
    b_v: float = 6.0
    k_v: float = 0.0
    x: float = 0.0
    v: float = 0.0

    def step(self, f_ext: float, dt: float) -> tuple[float, float]:
        """
        One turn of the admittance loop, exactly as written in the notes:

            1. read force              F_ext
            2. virtual acceleration    ddot(x) = (F - B_v v - K_v x) / M_v
            3. integrate for velocity  v_new = v_old + ddot(x) dt
            4. integrate for position  x_new = x_old + v_new dt

        Step 4's output is then handed to the motor's own stiff inner
        position loop. Returns (x_new, v_new).
        """
        acc = (f_ext - self.b_v * self.v - self.k_v * self.x) / self.m_v
        self.v += acc * dt
        self.x += self.v * dt
        return self.x, self.v

    def reset(self, x=0.0, v=0.0):
        self.x, self.v = x, v


# ==========================================================================
# Simulations the GUI animates
# ==========================================================================

@dataclass
class SimTrace:
    """Time series produced by the runs below."""
    t: list = field(default_factory=list)
    theta: list = field(default_factory=list)
    theta_ref: list = field(default_factory=list)
    tau: list = field(default_factory=list)
    f_ext: list = field(default_factory=list)


def run_impedance(k, b, tau_ff=0.0, theta_d=0.0, push=(1.0, 1.6, 6.0),
                  duration=3.0, dt=0.002, inertia=0.25, friction=0.4) -> SimTrace:
    """
    Hold theta_d with a virtual spring-damper while a human leans on the
    joint with `push` = (start_s, end_s, torque_Nm).

    Watch two things as you raise K: the joint deviates less, and the torque
    it fights back with grows. Stiffness and compliance are the same dial
    read from opposite ends.
    """
    j = Joint(inertia=inertia, friction=friction, theta=theta_d)
    tr = SimTrace()
    t0, t1, mag = push
    n = int(duration / dt)
    for i in range(n):
        t = i * dt
        f = mag if t0 <= t < t1 else 0.0
        tau = impedance_torque(j.theta, j.omega, theta_d, 0.0, k, b, tau_ff)
        j.step(tau, f, dt)
        tr.t.append(t)
        tr.theta.append(j.theta)
        tr.theta_ref.append(theta_d)
        tr.tau.append(tau)
        tr.f_ext.append(f)
    return tr


def run_admittance(m_v, b_v, k_v=0.0, inner_kp=400.0, inner_kd=25.0,
                   push=(1.0, 1.6, 6.0), duration=3.0, dt=0.002,
                   inertia=0.25, friction=0.4, stiction=0.0) -> SimTrace:
    """
    The other direction: an F/T sensor reads the human's push, the virtual
    model decides where a frictionless ghost robot would have gone, and a
    high-gain inner position loop drags the real (stiff, geared) joint there.

    `stiction` models the breakaway friction of a high-ratio gearbox. Turn it
    up and notice what does NOT happen: the admittance loop keeps working,
    because the force sensor sits OUTSIDE the transmission and never had to
    fight the gears to notice you. That bypass is the entire reason to pick
    admittance over impedance on a 100:1 drive.
    """
    j = Joint(inertia=inertia, friction=friction)
    vm = VirtualModel(m_v=m_v, b_v=b_v, k_v=k_v)
    tr = SimTrace()
    t0, t1, mag = push
    n = int(duration / dt)
    for i in range(n):
        t = i * dt
        f = mag if t0 <= t < t1 else 0.0
        x_ref, v_ref = vm.step(f, dt)
        tau = inner_kp * (x_ref - j.theta) + inner_kd * (v_ref - j.omega)
        if stiction > 0.0 and abs(j.omega) < 1e-3 and abs(tau) < stiction:
            tau = 0.0                      # gearbox has not broken away yet
        j.step(tau, f, dt)
        tr.t.append(t)
        tr.theta.append(j.theta)
        tr.theta_ref.append(x_ref)
        tr.tau.append(tau)
        tr.f_ext.append(f)
    return tr


def run_position(kp, kd, theta_d=0.0, push=(1.0, 1.6, 6.0), duration=3.0,
                 dt=0.002, inertia=0.25, friction=0.4) -> SimTrace:
    """Plain PD position control -- the tau_ff = 0 corner of impedance."""
    return run_impedance(kp, kd, 0.0, theta_d, push, duration, dt,
                         inertia, friction)


def run_torque(tau_cmd, push=(1.0, 1.6, 6.0), duration=3.0, dt=0.002,
               inertia=0.25, friction=0.4) -> SimTrace:
    """
    Open-loop torque control: ||Z|| = 0. The commanded torque is delivered
    perfectly and the position goes wherever the world decides. Perfect
    transparency, zero position authority.
    """
    return run_impedance(0.0, 0.0, tau_cmd, 0.0, push, duration, dt,
                         inertia, friction)


# ==========================================================================
# The decoupled-parameterisation demonstration (Corollary 3.1)
# ==========================================================================

def nominal_ankle_torque(phase: float, mass: float = 75.0) -> float:
    """
    A smooth stand-in for the able-bodied ankle moment over one gait cycle,
    `phase` in [0, 1]. Dorsiflexion moment stays near zero through early
    stance, then a large plantarflexion push-off peak around 50%, then
    nothing through swing. Units: N*m.

    Shape only -- it exists so the two-controller demo has a realistic
    tau_ff to share, not to be used as clinical data.
    """
    if phase < 0.05 or phase > 0.65:
        return 0.0
    x = (phase - 0.05) / 0.60
    return -mass * 1.55 * math.exp(-((x - 0.78) ** 2) / (2 * 0.16 ** 2))


def nominal_ankle_angle(phase: float) -> float:
    """Matching nominal ankle angle in radians; plantarflexion negative."""
    return math.radians(
        -3.0
        + 7.0 * math.sin(2 * math.pi * (phase - 0.05))
        - 9.0 * math.exp(-((phase - 0.62) ** 2) / (2 * 0.06 ** 2))
    )


def two_controller_demo(k_a, b_a, k_b, b_b, perturb_deg=0.0, n=200,
                        mass: float = 75.0):
    r"""
    The headline result of the decoupled parameterisation.

    Build two impedance controllers, alpha and beta, that share the SAME
    nominal trajectory (theta_d, dot theta_d) and the SAME feedforward torque
    tau_ff, but have very different stiffness and damping.

    Property 3: when theta = theta_d and dot theta = dot theta_d, the feedback
    term vanishes and both reduce to tau = tau_ff. So with `perturb_deg = 0`
    the two torque curves lie exactly on top of each other -- K and B are
    invisible. Tuning them by looking at nominal walking tells you nothing.

    Turn `perturb_deg` up and they separate immediately, in proportion to
    their stiffness. Off-nominal behaviour is the ONLY place these parameters
    show themselves.

    Returns (phases, theta_d_deg, tau_alpha, tau_beta, theta_eq_a, theta_eq_b).
    """
    phases, th_d, ta, tb, eqa, eqb = [], [], [], [], [], []
    dp = 1.0 / n
    pert = math.radians(perturb_deg)
    for i in range(n):
        p = i * dp
        thd = nominal_ankle_angle(p)
        thd_next = nominal_ankle_angle(min(1.0, p + dp))
        omd = (thd_next - thd) / (dp * 1.1)          # 1.1 s gait cycle
        tff = nominal_ankle_torque(p, mass)

        th = thd + pert                              # measured, perturbed
        om = omd

        phases.append(p * 100.0)
        th_d.append(math.degrees(thd))
        ta.append(impedance_torque(th, om, thd, omd, k_a, b_a, tff))
        tb.append(impedance_torque(th, om, thd, omd, k_b, b_b, tff))
        eqa.append(math.degrees(equilibrium_angle(thd, omd, k_a, b_a, tff)))
        eqb.append(math.degrees(equilibrium_angle(thd, omd, k_b, b_b, tff)))
    return phases, th_d, ta, tb, eqa, eqb
