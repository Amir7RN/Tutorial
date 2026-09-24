"""Explicit assumptions and small numerical examples for the biped lessons."""
import numpy as np
from .pole_lesson import matrix_exponential


def joint_growth_rates(leg):
    """Positive roots of J*s^2 + d*s - k_g = 0, in joint order."""
    j = leg.inertias()
    kg = -np.diag(leg.gravity_stiffness())
    return (-leg.d + np.sqrt(leg.d**2 + 4*j*kg))/(2*j)


def sampled_feedback(ss, K, x0, fs, limit, duration=1.5):
    """Exact zero-order-hold plant; feedback updates once per sample, no extra delay."""
    A, B = np.asarray(ss.A), np.asarray(ss.B)
    n, m = B.shape
    augmented = np.zeros((n+m, n+m))
    augmented[:n, :n], augmented[:n, n:] = A, B
    transition = matrix_exponential(augmented/fs)
    Ad, Bd = transition[:n, :n], transition[:n, n:]
    radius = float(np.max(np.abs(np.linalg.eigvals(Ad-Bd@K))))
    x = np.array(x0, dtype=float)
    ts, xs, us, hits = [], [], [], 0
    for i in range(int(duration*fs)+1):
        raw = -K@x
        u = np.clip(raw, -limit, limit)
        hits += bool(np.any(np.abs(raw)>limit))
        ts.append(i/fs); xs.append(x.copy()); us.append(u)
        x = Ad@x + Bd@u
        if not np.isfinite(x).all() or np.max(np.abs(x)) > 1e4:
            break
    return np.array(ts), np.array(xs), np.array(us), hits/len(ts), radius


def capture_delay_limit(xi0, half_foot, omega):
    """Time to the support edge if CoP remains at zero, positive forward push."""
    if xi0 <= 0:
        return float('inf')
    return max(0., float(np.log(half_foot/xi0)/omega))


def motion_response(j, kp, kd, frequencies):
    """Ideal torque source, rigid load, no gravity: theta/theta_ref under PD."""
    s = 2j*np.pi*np.asarray(frequencies)
    return kp/(j*s*s+kd*s+kp)
