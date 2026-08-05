"""
Real-time control: the part that decides whether any of the theory survives
contact with a microcontroller.

Everything on the control pages assumes the loop runs "every tick". This
module is about what happens when it does not, and about the three numbers
people routinely confuse:

    f_s          sampling rate            -- how often you look        (1 kHz)
    f_nyq        Nyquist frequency        -- f_s / 2                   (500 Hz)
    f_bw         closed-loop bandwidth    -- how fast you can ACT      (50 Hz)

They are not the same number and they are not close to each other. A 1 kHz
loop does not give you 1 kHz of control authority; it gives you roughly
f_s/10 to f_s/20 once sampling delay, computation delay and phase margin are
paid for.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


# ==========================================================================
# Sampling
# ==========================================================================

def nyquist(f_s: float) -> float:
    """Highest frequency a sampler at f_s can represent. Above this, content
    does not vanish -- it FOLDS back down and masquerades as a low frequency."""
    return f_s / 2.0


def alias_frequency(f_signal: float, f_s: float) -> float:
    r"""
    Where a signal at f_signal actually APPEARS after sampling at f_s.

        f_alias = | f_signal - f_s * round(f_signal / f_s) |

    A 950 Hz vibration sampled at 1 kHz shows up as a 50 Hz oscillation that
    is indistinguishable from a real 50 Hz disturbance. No digital filter can
    undo it -- the information was destroyed at the ADC. The only fix is an
    ANALOG anti-alias filter in front of the converter.
    """
    if f_s <= 0:
        return 0.0
    return abs(f_signal - f_s * round(f_signal / f_s))


def practical_bandwidth(f_s: float, ratio: float = 15.0) -> float:
    """
    Rule of thumb for the closed-loop bandwidth a digital loop can actually
    achieve: f_s / 10 to f_s / 20.

    Nyquist says f_s / 2, but Nyquist is a statement about *reconstructing a
    signal*, not about *closing a loop around it*. A loop also has to pay:

      - zero-order hold, which costs an average delay of T/2
      - computation delay, up to another T
      - phase margin, which you must keep to stay stable

    Each of those is phase you do not get back.
    """
    return f_s / ratio


def delay_limited_bandwidth(delay_s: float, phase_budget_deg: float = 60.0) -> float:
    r"""
    The bandwidth ceiling imposed by transport delay alone.

    A delay costs 360*f*T_d degrees of phase. Decide how much phase you are
    willing to spend on delay (60 degrees is a common budget, leaving the
    rest for the plant and for margin) and solve for f:

        f_max = phase_budget / (360 * T_d)

    With T_d = 2 ms and a 60 degree budget, f_max = 83 Hz -- and no amount of
    extra sampling rate raises it. This is why the honest bandwidth estimate
    is min(sampling limit, delay limit), and why the delay term usually wins
    on anything with a network or a slow sensor in the loop.
    """
    if delay_s <= 0:
        return float("inf")
    return phase_budget_deg / (360.0 * delay_s)


def delay_phase_lag_deg(delay_s: float, freq_hz: float) -> float:
    r"""
    Phase lost to a pure transport delay:  angle = -omega * T_d.

        e^{-s T_d}  ->  phase = -2 pi f T_d  radians

    This is the single most under-appreciated number in embedded control.
    Delay costs you phase margin and buys you nothing. At 50 Hz, a 2 ms loop
    delay has already eaten 36 degrees.
    """
    return -360.0 * freq_hz * delay_s


# ==========================================================================
# Real-time task model
# ==========================================================================

@dataclass
class TaskProfile:
    """
    One periodic control task.

        period      how often it is supposed to run
        wcet        worst-case execution time
        deadline    when it must be finished (usually == period)
    """
    period_ms: float = 1.0
    wcet_ms: float = 0.35
    deadline_ms: float | None = None

    @property
    def deadline(self) -> float:
        return self.deadline_ms if self.deadline_ms is not None else self.period_ms

    @property
    def utilisation(self) -> float:
        """Fraction of CPU this task consumes. Sum over tasks must stay below
        1.0, and well below it if you want any margin."""
        return self.wcet_ms / self.period_ms if self.period_ms else float("inf")

    @property
    def schedulable(self) -> bool:
        return self.wcet_ms <= self.deadline


def rate_monotonic_bound(n_tasks: int) -> float:
    r"""
    Liu & Layland utilisation bound for rate-monotonic scheduling:

        U <= n (2^{1/n} - 1)

    n=1 -> 1.00,  n=2 -> 0.828,  n=3 -> 0.780,  n->inf -> ln 2 = 0.693

    Below this bound, a fixed-priority preemptive scheduler (which is what
    FreeRTOS gives you) is GUARANTEED to meet every deadline. Above it you
    may still be fine, but you no longer have a proof -- you have a hope.
    """
    if n_tasks <= 0:
        return 0.0
    return n_tasks * (2.0 ** (1.0 / n_tasks) - 1.0)


def sample_jitter(period_s: float, jitter_frac: float, rng: random.Random) -> float:
    """One actual inter-sample interval, given fractional timing jitter."""
    if jitter_frac <= 0.0:
        return period_s
    return period_s * (1.0 + rng.uniform(-jitter_frac, jitter_frac))


# ==========================================================================
# A PID that survives the real world
# ==========================================================================

@dataclass
class PID:
    r"""
    Textbook PID is three lines. A PID that works on hardware is these lines
    plus four defences, and every one of them exists because of a specific
    failure that happens on a real machine.

        kp, ki, kd      the gains
        tau_d           derivative filter time constant (0 = raw derivative)
        anti_windup     "none" | "clamp" | "back_calc"
        d_on_measurement  differentiate -y instead of e, killing setpoint kick
        out_min/max     actuator saturation -- the reason windup exists at all
    """
    kp: float = 40.0
    ki: float = 0.0
    kd: float = 3.0
    tau_d: float = 0.0
    anti_windup: str = "clamp"
    d_on_measurement: bool = True
    out_min: float = -12.0
    out_max: float = 12.0
    kt: float = 1.0            # back-calculation tracking gain

    integral: float = 0.0
    _prev_e: float = 0.0
    _prev_y: float = 0.0
    _d_state: float = 0.0
    _first: bool = True

    def reset(self):
        self.integral = 0.0
        self._prev_e = 0.0
        self._prev_y = 0.0
        self._d_state = 0.0
        self._first = True

    def step(self, setpoint: float, measurement: float, dt: float):
        """
        One tick. Returns (output, parts) where parts is (P, I, D).

        `dt` is the ACTUAL elapsed time, not the nominal period. Passing the
        nominal period when the real interval jittered is precisely the bug
        that ruins the derivative term -- see `derivative_error_from_jitter`.
        """
        if dt <= 0:
            dt = 1e-9
        e = setpoint - measurement

        # ---- P ---------------------------------------------------------
        p = self.kp * e

        # ---- D ---------------------------------------------------------
        # Differentiating the measurement rather than the error means a step
        # in the setpoint does not produce an impulse in the output. The
        # setpoint contributes nothing to D, which is what you want: you
        # asked for a new target, the plant did not suddenly move.
        if self._first:
            raw_d = 0.0
            self._first = False
        elif self.d_on_measurement:
            raw_d = -(measurement - self._prev_y) / dt
        else:
            raw_d = (e - self._prev_e) / dt

        if self.tau_d > 0.0:
            # first-order low-pass on the derivative -- the "dirty derivative"
            # N*s/(s+N) with N = 1/tau_d. Pure differentiation has infinite
            # high-frequency gain, so it amplifies encoder quantisation into
            # audible motor buzz.
            alpha = dt / (self.tau_d + dt)
            self._d_state += alpha * (raw_d - self._d_state)
            d_term = self.kd * self._d_state
        else:
            d_term = self.kd * raw_d

        # ---- I, with anti-windup ---------------------------------------
        i_candidate = self.integral + self.ki * e * dt
        unsat = p + i_candidate + d_term
        out = max(self.out_min, min(self.out_max, unsat))

        if self.anti_windup == "none":
            self.integral = i_candidate
        elif self.anti_windup == "clamp":
            # conditional integration: stop accumulating while saturated and
            # the error would push further into the stop
            saturated = unsat != out
            if not (saturated and (e > 0) == (unsat > 0)):
                self.integral = i_candidate
        elif self.anti_windup == "back_calc":
            # bleed the integrator back toward the value that would have
            # produced the saturated output
            self.integral = i_candidate + self.kt * (out - unsat) * dt
        else:
            raise ValueError(f"unknown anti_windup {self.anti_windup!r}")

        # recompute output with the accepted integral
        unsat = p + self.integral + d_term
        out = max(self.out_min, min(self.out_max, unsat))

        self._prev_e = e
        self._prev_y = measurement
        return out, (p, self.integral, d_term)


def derivative_error_from_jitter(jitter_frac: float) -> float:
    r"""
    How wrong the derivative term is when the loop jitters but the code
    divides by the NOMINAL period.

        d_est / d_true = T_nominal / T_actual = 1 / (1 + j)

    so the fractional error is  |1/(1+j) - 1| = |j| / (1+j).

    10% jitter -> ~9% error in D, every tick, in a term whose whole job is to
    predict. P is unaffected (it does not involve time). I is barely affected
    (errors average out over many ticks). D takes essentially all the damage,
    which is why derivative is the first thing to misbehave on a loaded CPU.

    The fix is not to reduce jitter. The fix is to MEASURE dt and divide by
    the real number -- and to filter the result.
    """
    if jitter_frac <= -1.0:
        return float("inf")
    return abs(1.0 / (1.0 + jitter_frac) - 1.0)


# ==========================================================================
# Simulations the GUI animates
# ==========================================================================

@dataclass
class RTTrace:
    t: list = field(default_factory=list)
    y: list = field(default_factory=list)
    r: list = field(default_factory=list)
    u: list = field(default_factory=list)
    p: list = field(default_factory=list)
    i: list = field(default_factory=list)
    d: list = field(default_factory=list)


def run_pid(pid: PID, setpoint=0.35, duration=2.0, period=0.001,
            jitter_frac=0.0, use_nominal_dt=False, inertia=0.25,
            friction=0.4, load_torque=0.0, load_until=None, block_until=None,
            seed=0, noise=0.0) -> RTTrace:
    """
    Drive a 1-DOF joint with a PID at a fixed nominal rate, optionally with
    timing jitter, optionally lying to the controller about dt.

    `use_nominal_dt=True` reproduces the common bug: the interval jittered,
    but the code divided by the constant it was written with.

    `block_until` HOLDS the joint immovable until that time -- a hard stop, or
    a hand gripping it. This is the scenario that produces windup: the error
    cannot shrink, so the integrator accumulates area it can never deliver,
    and the instant the obstruction disappears the joint must overshoot far
    enough to integrate all of it back out.

    Note this is different from merely applying a large `load_torque`, which
    does not block the joint -- it just drives it the other way.
    """
    from .impedance import Joint

    rng = random.Random(seed)
    j = Joint(inertia=inertia, friction=friction)
    pid.reset()
    tr = RTTrace()
    t = 0.0
    while t < duration:
        dt_actual = sample_jitter(period, jitter_frac, rng)
        meas = j.theta + (rng.gauss(0.0, noise) if noise > 0 else 0.0)
        dt_used = period if use_nominal_dt else dt_actual
        u, (p, i, d) = pid.step(setpoint, meas, dt_used)
        load = load_torque if (load_until is None or t < load_until) else 0.0
        if block_until is not None and t < block_until:
            # immovable: a hard stop absorbs whatever the motor produces
            j.reset(theta=j.theta, omega=0.0)
        else:
            j.step(u, load, dt_actual)
        tr.t.append(t)
        tr.y.append(j.theta)
        tr.r.append(setpoint)
        tr.u.append(u)
        tr.p.append(p)
        tr.i.append(i)
        tr.d.append(d)
        t += dt_actual
    return tr


def run_aliasing(f_signal=950.0, f_s=1000.0, duration=0.05, dense=8000):
    """
    Sample a fast sine slowly and return both the true waveform and what the
    sampler saw, plus the alias frequency it will be mistaken for.

    Returns (t_dense, y_dense, t_samp, y_samp, f_alias).
    """
    t_dense = [i * duration / dense for i in range(dense + 1)]
    y_dense = [math.sin(2 * math.pi * f_signal * t) for t in t_dense]
    n = int(duration * f_s)
    t_samp = [k / f_s for k in range(n + 1)]
    y_samp = [math.sin(2 * math.pi * f_signal * t) for t in t_samp]
    return t_dense, y_dense, t_samp, y_samp, alias_frequency(f_signal, f_s)
