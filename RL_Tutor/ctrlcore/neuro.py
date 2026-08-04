"""
Neuromuscular machinery: the Hill muscle model and positive force feedback.

The one-sentence version, worth memorising before reading any code:

    Positive force feedback exists only if force changes activation.
    If force does not affect activation, it is not feedback.

Everything below is built to make that sentence testable. `hill_force` alone
is feedforward -- EMG in, force out, no loop. `PffLoop` closes the loop on
force and lets you watch it either amplify usefully or run away.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# ==========================================================================
# Hill-type muscle
# ==========================================================================

def force_length(l_norm: float, width: float = 0.45) -> float:
    r"""
    Force-length relation f_l(l), normalised so l = 1 is optimal fibre
    length. A Gaussian around the optimum: a muscle held too short or
    stretched too long simply cannot pull as hard, whatever the brain asks.
    """
    return math.exp(-(((l_norm - 1.0) / width) ** 2))


def force_velocity(v_norm: float) -> float:
    r"""
    Force-velocity relation f_v(dot l), with `v_norm` normalised to maximum
    shortening velocity. Sign convention: negative = shortening (concentric),
    positive = lengthening (eccentric).

        shortening   f_v = (1 + v) / (1 - v / 0.25)      v in [-1, 0]
        lengthening  f_v = 1.8 - 0.8 (1 - v) / (1 + 7.56 v)   capped at 1.8

    Both branches pass through f_v(0) = 1. Shortening fast costs you force
    (that is why you cannot lift heavy things quickly); being stretched
    while active gives you up to ~1.8x, which is what the calf exploits
    during the first half of stance.

    The eccentric expression drifts slightly above 1.8 once the lengthening
    velocity exceeds v_max, which is outside the range the approximation was
    fitted for, so it is clamped to the physiological plateau.
    """
    v = max(-1.0, v_norm)
    if v <= 0.0:
        return (1.0 + v) / (1.0 - v / 0.25)
    return min(1.8, 1.8 - 0.8 * (1.0 - v) / (1.0 + 7.56 * v))


def hill_force(activation: float, l_norm: float, v_norm: float,
               f_max: float = 3000.0) -> float:
    r"""
    Standard Hill-type contractile element:

        F_m = a * F_max * f_l(l) * f_v(dot l)

    Note what is NOT here: any dependence on F_m itself. This is pure
    feedforward. Drive it from EMG and you have a neuromuscular controller,
    a perfectly respectable thing -- but you must not call it positive force
    feedback, because nothing is fed back.
    """
    return activation * f_max * force_length(l_norm) * force_velocity(v_norm)


# ==========================================================================
# Positive force feedback
# ==========================================================================

@dataclass
class PffLoop:
    r"""
    Close the loop on force:

        a(t) = a_EMG(t) + k_f * F_m(t - tau)

    `k_f`   reflex gain           (how much force recruits more force)
    `delay` neural delay in s     (~30-50 ms in humans)
    `gate`  phase window (start, end) as a fraction of the cycle in which
            the loop is allowed to act at all. Biology does not run this
            loop continuously -- it is switched on during stance and
            push-off, when building force fast is the goal, and switched
            off otherwise.

    Whether this blows up is governed by the loop gain

        G = k_f * F_max * f_l * f_v

    G >= 1 with the gate wide open is genuine runaway. The biological
    system stays useful because the gate closes before the exponential has
    time to matter: it is phase-gated, time-limited, and embedded in a
    compliant musculoskeletal system that bleeds energy. "Positive
    feedback" here means functional amplification, not instability.
    """
    k_f: float = 0.0002
    delay: float = 0.04
    f_max: float = 3000.0
    gate: tuple = (0.10, 0.60)
    a_max: float = 1.0
    history: list = field(default_factory=list)

    def _delayed_force(self, dt: float) -> float:
        n = int(round(self.delay / dt))
        if n <= 0 or len(self.history) == 0:
            return self.history[-1] if self.history else 0.0
        if len(self.history) <= n:
            return 0.0
        return self.history[-1 - n]

    def step(self, a_emg: float, l_norm: float, v_norm: float,
             phase: float, dt: float, gated: bool = True) -> tuple[float, float]:
        """
        One control tick. Returns (force, activation).

        `gated=False` removes the phase window so you can see what an
        ungated positive loop actually does -- which is the point of the
        interactive page.
        """
        f_del = self._delayed_force(dt)
        in_window = (not gated) or (self.gate[0] <= phase <= self.gate[1])
        a = a_emg + (self.k_f * f_del if in_window else 0.0)
        a = max(0.0, min(self.a_max, a))
        f = hill_force(a, l_norm, v_norm, self.f_max)
        self.history.append(f)
        return f, a

    def reset(self):
        self.history = []


def loop_gain(k_f: float, f_max: float, l_norm: float = 1.0,
              v_norm: float = 0.0) -> float:
    """
    G = k_f * F_max * f_l * f_v. G < 1 decays, G = 1 sustains, G > 1 grows.
    """
    return k_f * f_max * force_length(l_norm) * force_velocity(v_norm)


def run_pff(k_f, delay=0.04, gated=True, a_emg=0.15, duration=1.1, dt=0.001,
            f_max=3000.0, gate=(0.10, 0.60)):
    """
    One gait cycle of an ankle plantarflexor with positive force feedback.

    The fibre is stretched through early stance and shortens through
    push-off, so f_v hands the loop extra gain exactly when the gate is
    open -- which is how biology gets a large, load-scaled push-off out of a
    small descending command.

    Returns (t, force, activation, phase).
    """
    loop = PffLoop(k_f=k_f, delay=delay, f_max=f_max, gate=gate)
    n = int(duration / dt)
    ts, fs, acts, phs = [], [], [], []
    for i in range(n):
        t = i * dt
        p = t / duration
        # fibre lengthens through early stance, shortens hard at push-off
        l_norm = 1.0 + 0.12 * math.sin(2 * math.pi * (p - 0.05))
        v_norm = -0.55 * math.exp(-((p - 0.52) ** 2) / (2 * 0.09 ** 2))
        f, a = loop.step(a_emg, l_norm, v_norm, p, dt, gated)
        ts.append(t)
        fs.append(f)
        acts.append(a)
        phs.append(p)
    return ts, fs, acts, phs


# ==========================================================================
# Robot side: where "force" can come from
# ==========================================================================

FORCE_SOURCES = {
    "sensor": (
        "Direct force/torque sensor",
        "Load cell or strain gauge at the interface. Honest and direct, but "
        "noisy, fragile, lower bandwidth, and you cannot afford one in every "
        "joint, finger and tendon."),
    "current": (
        "Motor current",
        "tau = K_t * I. Free, kHz-rate, low latency -- but only truthful if "
        "the transmission is transparent. Behind a 100:1 harmonic drive the "
        "current tells you about the gearbox, not the world."),
    "estimate": (
        "Model-based estimate",
        "From dynamics, from motor plus kinematics, or from an impedance "
        "model. Cheap and everywhere, but only as good as the model."),
}


def motor_torque_from_current(current: float, k_t: float) -> float:
    r"""
    tau = K_t * I -- the equation that turns an ordinary motor into a force
    sensor, and the reason proprioception and backdriveability are the same
    engineering requirement wearing two hats.
    """
    return k_t * current


def joint_torque_from_motor(tau_motor: float, ratio: float,
                            efficiency: float = 1.0) -> float:
    r"""
    tau_joint ~= tau_motor * r, valid only when r is known and the losses
    are small and predictable: low friction, low backlash, transparency.

    Drop `efficiency` toward 0.5 and watch the estimate decouple from the
    truth -- that is a geared robot losing its sense of touch.
    """
    return tau_motor * ratio * efficiency
