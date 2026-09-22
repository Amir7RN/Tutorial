"""Small SISO teaching helpers for the pole-placement lesson."""
import cmath
import numpy as np


def second_order_poles(wn, zeta):
    root = cmath.sqrt(zeta*zeta - 1)
    return [-wn*zeta + wn*root, -wn*zeta - wn*root]


def regulator_response(ss, K, x0, dur, dt, u_max=None):
    """Same forward-Euler model as simulate_feedback, without per-tick allocation.

    The page uses a constant SISO plant and no external disturbance. Keep the
    existing integration step and saturation semantics for a comparable plot.
    """
    A, B = np.asarray(ss.A), np.asarray(ss.B)[:, 0]
    gain = np.asarray(K).reshape(-1)
    x = np.asarray(x0, dtype=float).copy()
    count = int(dur / dt)
    ts = np.arange(count)*dt
    xs = np.empty((count, len(x)))
    us = np.empty((count, 1))
    transition = np.eye(len(x)) + dt*A
    drive = dt*B
    closed = transition - np.outer(drive, gain)
    hits = 0
    for i in range(count):
        requested = -float(gain @ x)
        u = requested if u_max is None else max(-u_max, min(u_max, requested))
        hits += u_max is not None and abs(u-requested) > 1e-8+1e-5*abs(requested)
        xs[i], us[i, 0] = x, u
        x = closed @ x if u_max is None else transition @ x + drive*u
        if not np.isfinite(x).all() or np.max(np.abs(x)) > 1e6:
            return ts[:i+1], xs[:i+1], us[:i+1], hits/(i+1)
    return ts, xs, us, hits/max(1, count)
