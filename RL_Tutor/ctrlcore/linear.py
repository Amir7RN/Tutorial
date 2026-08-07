"""
Linear time-invariant systems: the machinery behind first-order, second-order,
stability, Bode, Nyquist, compensator design, pole placement and observers.

No control-systems library is used. Everything here is built from polynomial
arithmetic, a state-space integrator, and numpy's eigenvalue/root solvers, so
every number a page prints can be traced to a few lines you can read.

The organising idea of the whole module:

    A transfer function is a ratio of polynomials in s. Its DENOMINATOR ROOTS
    (the poles) are the exponents of the natural response. Everything else --
    stability, overshoot, bandwidth, margins -- is a way of asking where those
    roots are, or of moving them.

        pole at s = -a          ->  e^{-at}      decays      STABLE
        pole at s = +a          ->  e^{+at}      grows       UNSTABLE
        pole at s = 0           ->  constant     drifts      MARGINAL
        poles at -s +- j w      ->  e^{-st}cos   rings down  STABLE
        poles at   0 +- j w     ->  cos(wt)      rings for   MARGINAL
                                                 ever

Conventions used everywhere in this file:

    * polynomial coefficients are DESCENDING powers, so [1, 2, 3] is
      s^2 + 2 s + 3
    * frequencies passed to Bode/Nyquist helpers are in rad/s
    * `L` always means the OPEN-LOOP (loop) transfer function of a unity
      feedback system; the closed loop is then L / (1 + L)
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass

import numpy as np


# ==========================================================================
# Polynomial helpers
# ==========================================================================

def poly_mul(a: list[float], b: list[float]) -> list[float]:
    """Multiply two descending-power coefficient lists."""
    out = [0.0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        for j, bj in enumerate(b):
            out[i + j] += ai * bj
    return out


def poly_add(a: list[float], b: list[float]) -> list[float]:
    """Add two descending-power coefficient lists of any lengths."""
    n = max(len(a), len(b))
    a = [0.0] * (n - len(a)) + list(a)
    b = [0.0] * (n - len(b)) + list(b)
    return [x + y for x, y in zip(a, b)]


def poly_eval(coeffs: list[float], s: complex) -> complex:
    """Horner evaluation, valid for complex s -- which is the whole point."""
    out = 0.0 + 0.0j
    for c in coeffs:
        out = out * s + c
    return out


def poly_roots(coeffs: list[float]) -> list[complex]:
    """Roots of a descending-power polynomial, [] for a constant."""
    c = list(coeffs)
    while c and abs(c[0]) < 1e-15:
        c.pop(0)
    if len(c) <= 1:
        return []
    return [complex(r) for r in np.roots(c)]


# ==========================================================================
# Transfer function
# ==========================================================================

@dataclass
class TF:
    """
    num(s) / den(s), both descending-power coefficient lists.

        TF([1], [1, 2])         ->  1 / (s + 2)
        TF([4], [1, 0.8, 4])    ->  4 / (s^2 + 0.8 s + 4)

    A TF is PROPER when deg(num) <= deg(den) -- required for anything
    physically realisable, because a strictly improper transfer function is a
    perfect differentiator and would have infinite gain at infinite frequency.
    """
    num: list[float]
    den: list[float]

    # -- structure ----------------------------------------------------
    def poles(self) -> list[complex]:
        return poly_roots(self.den)

    def zeros(self) -> list[complex]:
        return poly_roots(self.num)

    def order(self) -> int:
        return max(0, len(_trim(self.den)) - 1)

    def dc_gain(self) -> float:
        """G(0). Infinite when there is a pole at the origin (an integrator)."""
        n, d = _trim(self.num), _trim(self.den)
        if abs(d[-1]) < 1e-15:
            return math.inf if abs(n[-1]) > 1e-15 else 0.0
        return n[-1] / d[-1]

    # -- frequency domain ---------------------------------------------
    def at(self, s: complex) -> complex:
        d = poly_eval(self.den, s)
        if abs(d) < 1e-300:
            return complex(math.inf, 0.0)
        return poly_eval(self.num, s) / d

    def response(self, w: float) -> complex:
        """G(jw) -- substitute s = jw. This single substitution is the entire
        reason Bode plots exist: it turns a differential equation into a
        complex number per frequency."""
        return self.at(1j * w)

    # -- algebra -------------------------------------------------------
    def __mul__(self, other: "TF | float") -> "TF":
        """Series connection. Cascading blocks MULTIPLIES transfer functions,
        which is why log magnitude (dB) adds and phase adds."""
        if isinstance(other, (int, float)):
            return TF([c * other for c in self.num], list(self.den))
        return TF(poly_mul(self.num, other.num), poly_mul(self.den, other.den))

    __rmul__ = __mul__

    def feedback(self, h: "TF | None" = None) -> "TF":
        """
        Close the loop.  L / (1 + L*H),  H = 1 by default.

        The closed-loop DENOMINATOR is 1 + L(s), so the closed-loop poles are
        the roots of  den_L + num_L = 0.  Feedback does not change the plant;
        it MOVES ITS POLES. That sentence is the whole of control design.
        """
        if h is None:
            return TF(list(self.num), poly_add(self.den, self.num))
        fwd_n, fwd_d = self.num, self.den
        op = poly_mul(fwd_n, h.num)
        return TF(poly_mul(fwd_n, h.den),
                  poly_add(poly_mul(fwd_d, h.den), op))


def _trim(c: list[float]) -> list[float]:
    out = list(c)
    while len(out) > 1 and abs(out[0]) < 1e-15:
        out.pop(0)
    return out or [0.0]


# ==========================================================================
# The two canonical plants
# ==========================================================================

def first_order(k: float = 1.0, tau: float = 0.1) -> TF:
    r"""
        G(s) = K / (tau s + 1)          single pole at s = -1/tau

    Where they come from, in a robot:

        motor winding      L di/dt + R i = V          tau = L/R  (~1 ms)
        velocity loop      J dw/dt + b w = tau        tau = J/b
        thermal            C dT/dt + T/R = P          tau = minutes
        any low-pass filter, including the derivative filter in your PID

    Two facts worth memorising, both of which come from having exactly ONE
    pole:

      1. It cannot overshoot and cannot oscillate. There is nothing to
         exchange energy with.
      2. Its phase lag can never exceed 90 degrees, so a proportional loop
         around a first-order plant is stable for ANY gain -- infinite gain
         margin. Every instability you have ever seen needed a second energy
         store, or a delay.
    """
    return TF([k], [tau, 1.0])


def second_order(wn: float = 10.0, zeta: float = 0.7, k: float = 1.0) -> TF:
    r"""
        G(s) = K wn^2 / (s^2 + 2 zeta wn s + wn^2)

    The canonical form every mechanical joint reduces to:

        J th'' + B th' + K th = tau
            wn   = sqrt(K/J)          natural frequency
            zeta = B / (2 sqrt(K J))  damping ratio

    Which means that when you pick the K and B of an impedance controller you
    are not picking "stiffness and damping" -- you are picking wn and zeta,
    and therefore the overshoot and settling time, whether you meant to or
    not.
    """
    return TF([k * wn * wn], [1.0, 2.0 * zeta * wn, wn * wn])


def joint_wn_zeta(k_gain: float, b_gain: float, inertia: float
                  ) -> tuple[float, float]:
    r"""
    Map a joint's (K, B, J) onto (wn, zeta).

        wn   = sqrt(K/J)
        zeta = B / (2 sqrt(K J))

    Note what happens when you double K alone: wn rises by sqrt(2) but zeta
    FALLS by sqrt(2). Stiffening a joint without also raising B always makes
    it ring more. This is the single most common impedance-tuning mistake.
    """
    if inertia <= 0 or k_gain <= 0:
        return 0.0, math.inf
    wn = math.sqrt(k_gain / inertia)
    zeta = b_gain / (2.0 * math.sqrt(k_gain * inertia))
    return wn, zeta


# -- closed-form second-order step metrics -------------------------------

def overshoot_fraction(zeta: float) -> float:
    r"""
        Mp = exp(-pi zeta / sqrt(1 - zeta^2))        (0 <= zeta < 1)

    zeta 0.1 -> 73%,  0.5 -> 16%,  0.707 -> 4.3%,  1.0 -> 0%.
    Depends ONLY on zeta -- not on wn. Speed and overshoot are separate
    knobs, which is why "it overshoots, so slow it down" is wrong advice.
    """
    if zeta >= 1.0:
        return 0.0
    if zeta <= 0.0:
        return 1.0
    return math.exp(-math.pi * zeta / math.sqrt(1.0 - zeta * zeta))


def zeta_from_overshoot(mp: float) -> float:
    """Invert the above -- what damping a measured overshoot implies."""
    if mp <= 0:
        return 1.0
    if mp >= 1:
        return 0.0
    l = math.log(mp)
    return -l / math.sqrt(math.pi ** 2 + l * l)


def settling_time(zeta: float, wn: float, band: float = 0.02) -> float:
    """
    Time to stay inside +-band of final value.  ts ~ -ln(band)/(zeta wn).

    For the usual 2% band that is the familiar  ts ~ 4 / (zeta wn)  -- and
    note the product zeta*wn is exactly the REAL PART of the pole. Settling
    time is set by how far left the poles are, nothing else.
    """
    if zeta <= 0 or wn <= 0:
        return math.inf
    return -math.log(band) / (zeta * wn)


def peak_time(zeta: float, wn: float) -> float:
    """tp = pi / wd, the time of the first overshoot peak."""
    if zeta >= 1.0 or wn <= 0:
        return math.inf
    return math.pi / (wn * math.sqrt(1.0 - zeta * zeta))


def damped_frequency(zeta: float, wn: float) -> float:
    """wd = wn sqrt(1 - zeta^2) -- the frequency it actually rings at."""
    if zeta >= 1.0:
        return 0.0
    return wn * math.sqrt(1.0 - zeta * zeta)


def resonant_peak_db(zeta: float) -> float:
    """
    Height of the closed-loop magnitude bump, 20 log10( 1/(2 zeta sqrt(1-z^2)) ).

    There is NO peak at all for zeta >= 0.707: that is what "maximally flat"
    means, and it is why 0.707 is the default damping target everywhere.
    """
    if zeta >= 1.0 / math.sqrt(2.0):
        return 0.0
    return 20.0 * math.log10(1.0 / (2.0 * zeta * math.sqrt(1.0 - zeta * zeta)))


def phase_margin_of_zeta(zeta: float) -> float:
    r"""
    Exact phase margin of the standard second-order loop wn^2/(s(s+2 zeta wn)):

        PM = atan( 2 zeta / sqrt( sqrt(1 + 4 zeta^4) - 2 zeta^2 ) )

    This is the theorem behind the famous rule of thumb PM ~ 100*zeta, which
    is accurate to a few degrees up to about zeta = 0.7 (PM = 65 deg).
    """
    if zeta <= 0:
        return 0.0
    inner = math.sqrt(1.0 + 4.0 * zeta ** 4) - 2.0 * zeta ** 2
    return math.degrees(math.atan(2.0 * zeta / math.sqrt(inner)))


def second_order_step(wn: float, zeta: float, t: float) -> float:
    """Analytic unit step response -- used to check the numerical integrator."""
    if wn <= 0:
        return 0.0
    if zeta < 1.0:
        wd = wn * math.sqrt(1.0 - zeta ** 2)
        phi = math.atan2(math.sqrt(1.0 - zeta ** 2), zeta)
        return 1.0 - math.exp(-zeta * wn * t) / math.sqrt(1 - zeta ** 2) \
            * math.sin(wd * t + phi)
    if abs(zeta - 1.0) < 1e-9:
        return 1.0 - math.exp(-wn * t) * (1.0 + wn * t)
    a = wn * (zeta - math.sqrt(zeta ** 2 - 1.0))
    b = wn * (zeta + math.sqrt(zeta ** 2 - 1.0))
    return 1.0 - (b * math.exp(-a * t) - a * math.exp(-b * t)) / (b - a)


# ==========================================================================
# State space, and the transfer-function bridge
# ==========================================================================

@dataclass
class StateSpace:
    """
        x' = A x + B u
        y  = C x + D u

    Why bother, when a transfer function says the same thing for SISO? Three
    reasons that matter in robotics: it handles MIMO without pain, it is what
    every nonlinear method linearises INTO, and it exposes the internal
    states -- which is what an observer estimates and what pole placement
    moves.
    """
    A: np.ndarray
    B: np.ndarray
    C: np.ndarray
    D: np.ndarray

    @property
    def n(self) -> int:
        return self.A.shape[0]

    def poles(self) -> list[complex]:
        """Poles of a state-space model ARE the eigenvalues of A. Same
        objects, different name, and the reason 'eigenvalue' and 'pole' are
        used interchangeably by control engineers."""
        return [complex(v) for v in np.linalg.eigvals(self.A)]


def tf_to_ss(tf: TF) -> StateSpace:
    """
    Controllable canonical form. Requires a proper transfer function.

    Given  (b0 s^n + ... + bn) / (s^n + a1 s^{n-1} + ... + an):

        D  = b0                        (0 unless the TF is biproper)
        b' = num - D*den               (strictly proper remainder)
        A  = companion matrix of den
        B  = [1, 0, ..., 0]^T
        C  = b'[1:]
    """
    den = _trim(list(tf.den))
    n = len(den) - 1
    if n < 1:
        raise ValueError("tf_to_ss needs at least one pole")
    a0 = den[0]
    den = [c / a0 for c in den]
    num = [c / a0 for c in tf.num]
    num = [0.0] * (len(den) - len(num)) + num
    if len(num) > len(den):
        raise ValueError("improper transfer function (deg num > deg den)")

    d = num[0]
    rem = [x - d * y for x, y in zip(num, den)]      # rem[0] == 0

    A = np.zeros((n, n))
    A[0, :] = [-c for c in den[1:]]
    if n > 1:
        A[1:, :-1] = np.eye(n - 1)
    B = np.zeros((n, 1))
    B[0, 0] = 1.0
    C = np.array([rem[1:]], dtype=float)
    D = np.array([[d]], dtype=float)
    return StateSpace(A, B, C, D)


def simulate_ss(ss: StateSpace, u_of_t, duration: float, dt: float = 1e-3,
                x0: np.ndarray | None = None, max_steps: int = 20000):
    """
    Fixed-step RK4. Returns (t, y, X) with X the full state history as lists.

    RK4 rather than Euler because these pages plot lightly damped systems,
    and Euler adds its own artificial negative damping -- which would make a
    page about stability lie about stability.

    Written with plain Python lists rather than numpy arrays on purpose: the
    state dimension here is 2-4, and at that size numpy's per-call overhead
    costs more than the arithmetic it saves. These run behind live sliders,
    so the difference is the difference between smooth and unusable.

    `max_steps` coarsens dt rather than letting a careless duration/dt pair
    freeze the UI.
    """
    n = ss.n
    A = [[float(v) for v in row] for row in np.asarray(ss.A)]
    B = [float(v) for v in np.asarray(ss.B).ravel()]
    C = [float(v) for v in np.asarray(ss.C).ravel()]
    D = float(np.asarray(ss.D).ravel()[0])

    n_steps = max(1, int(round(duration / dt)))
    if n_steps > max_steps:
        n_steps = max_steps
        dt = duration / n_steps
    h2, h6 = dt / 2.0, dt / 6.0

    x = [0.0] * n if x0 is None else [float(v) for v in
                                      np.asarray(x0, dtype=float).ravel()]
    ts, ys, xs = [], [], []

    def deriv(state, u):
        return [sum(A[i][j] * state[j] for j in range(n)) + B[i] * u
                for i in range(n)]

    for i in range(n_steps + 1):
        t = i * dt
        u = u_of_t(t)
        ts.append(t)
        ys.append(sum(C[j] * x[j] for j in range(n)) + D * u)
        xs.append(list(x))
        k1 = deriv(x, u)
        um = u_of_t(t + h2)
        k2 = deriv([x[j] + h2 * k1[j] for j in range(n)], um)
        k3 = deriv([x[j] + h2 * k2[j] for j in range(n)], um)
        k4 = deriv([x[j] + dt * k3[j] for j in range(n)], u_of_t(t + dt))
        x = [x[j] + h6 * (k1[j] + 2 * k2[j] + 2 * k3[j] + k4[j])
             for j in range(n)]
    return ts, ys, xs


def step_response(tf: TF, duration: float = 2.0, dt: float = 1e-3,
                  amplitude: float = 1.0):
    """Unit (or scaled) step response of any proper transfer function."""
    ss = tf_to_ss(tf)
    t, y, _ = simulate_ss(ss, lambda _t: amplitude, duration, dt)
    return t, y


def impulse_response(tf: TF, duration: float = 2.0, dt: float = 1e-3):
    """Impulse response, done honestly: release the system from the state a
    unit impulse would leave it in, rather than faking a tall thin pulse."""
    ss = tf_to_ss(tf)
    x0 = ss.B.copy()
    t, y, _ = simulate_ss(ss, lambda _t: 0.0, duration, dt, x0=x0)
    return t, y


@dataclass
class StepMetrics:
    """What a step response is actually judged on."""
    steady_state: float = 0.0
    overshoot: float = 0.0         # fraction of the final value
    peak_time: float = 0.0
    rise_time: float = 0.0         # 10% -> 90%
    settling_time: float = math.inf
    steady_state_error: float = 0.0


def step_metrics(t: list[float], y: list[float], target: float = 1.0,
                 band: float = 0.02) -> StepMetrics:
    """Measure a simulated step. Deliberately the same definitions the
    closed-form second-order formulas use, so the two can be compared."""
    if not y:
        return StepMetrics()
    yss = y[-1]
    m = StepMetrics(steady_state=yss, steady_state_error=target - yss)
    if abs(yss) > 1e-12:
        peak = max(y)
        m.overshoot = max(0.0, (peak - yss) / abs(yss))
        m.peak_time = t[y.index(peak)]
        lo, hi = 0.1 * yss, 0.9 * yss
        t_lo = t_hi = None
        for ti, yi in zip(t, y):
            if t_lo is None and yi >= lo:
                t_lo = ti
            if t_hi is None and yi >= hi:
                t_hi = ti
                break
        if t_lo is not None and t_hi is not None:
            m.rise_time = t_hi - t_lo
        tol = band * abs(yss)
        m.settling_time = 0.0
        for ti, yi in zip(t, y):
            if abs(yi - yss) > tol:
                m.settling_time = ti
    return m


# ==========================================================================
# Frequency response: Bode, margins, Nyquist
# ==========================================================================

def log_freqs(w_min: float = 1e-2, w_max: float = 1e4, n: int = 500
              ) -> list[float]:
    """Logarithmically spaced frequencies -- the only sensible x-axis for a
    system whose behaviour spans decades."""
    a, b = math.log10(w_min), math.log10(w_max)
    return [10 ** (a + (b - a) * i / (n - 1)) for i in range(n)]


def bode(tf: TF, w: list[float] | None = None):
    """
    Returns (w, magnitude_dB, phase_deg) with the phase UNWRAPPED.

    Unwrapping matters: atan2 returns (-180, 180], so an honest -190 degrees
    comes back as +170 and a naive plot shows a 360 degree jump that is not
    there. Phase margin computed from wrapped phase is simply wrong.
    """
    w = w or log_freqs()
    mag_db, phase = [], []
    prev = None
    offset = 0.0
    for wi in w:
        g = tf.response(wi)
        m = abs(g)
        mag_db.append(20.0 * math.log10(m) if m > 1e-300 else -600.0)
        p = math.degrees(cmath.phase(g))
        if prev is not None:
            d = p + offset - prev
            if d > 180.0:
                offset -= 360.0
            elif d < -180.0:
                offset += 360.0
        p += offset
        phase.append(p)
        prev = p
    return w, mag_db, phase


def _phase_deg_unwrapped(tf: TF, w: float, reference: float | None = None
                         ) -> float:
    """Phase at a single frequency, optionally pulled to the branch nearest a
    reference value so bisection does not jump across a 360 degree seam."""
    p = math.degrees(cmath.phase(tf.response(w)))
    if reference is not None:
        while p - reference > 180.0:
            p -= 360.0
        while reference - p > 180.0:
            p += 360.0
    return p


@dataclass
class Margins:
    """
    The two numbers that decide whether a loop survives reality.

        gain_margin_db   how much extra GAIN before instability
        phase_margin_deg how much extra LAG before instability

    Both are distances from the point L(jw) = -1, measured along the two
    directions you can actually be wrong in: your model's gain, and your
    loop's delay. Targets on real hardware: PM 45-60 deg, GM 6-12 dB.
    """
    gain_margin_db: float = math.inf
    phase_margin_deg: float = math.inf
    wgc: float = 0.0               # gain crossover, |L| = 1
    wpc: float = 0.0               # phase crossover, angle L = -180
    stable: bool = True


def margins(l: TF, w_min: float = 1e-3, w_max: float = 1e6, n: int = 1200
            ) -> Margins:
    """
    Gain and phase margin of a unity-feedback loop with open-loop L.

    Found by scanning a dense log grid for sign changes and then bisecting,
    which is robust for the plants these pages use and needs no root solving.

        PM = 180 + angle L( w_gc )     where |L(w_gc)| = 1
        GM = -20 log10 |L( w_pc )|     where angle L(w_pc) = -180

    `stable` is decided from the closed-loop poles, not from the margins,
    because margins alone are not a stability proof (a conditionally stable
    loop can have a healthy PM and still be unstable -- see the Nyquist page).
    """
    ws = log_freqs(w_min, w_max, n)
    mags, phs = [], []
    prev = None
    offset = 0.0
    for wi in ws:
        g = l.response(wi)                 # one evaluation per frequency
        mags.append(abs(g))
        p = math.degrees(cmath.phase(g))
        if prev is not None:
            d = p + offset - prev
            if d > 180.0:
                offset -= 360.0
            elif d < -180.0:
                offset += 360.0
        p += offset
        phs.append(p)
        prev = p

    out = Margins()
    cl_poles = TF(l.num, l.den).feedback().poles()
    out.stable = all(p.real < -1e-9 for p in cl_poles) if cl_poles else True

    # ---- gain crossover: |L| passes through 1 -------------------------
    for i in range(len(ws) - 1):
        if (mags[i] - 1.0) * (mags[i + 1] - 1.0) < 0:
            lo, hi = ws[i], ws[i + 1]
            for _ in range(40):
                mid = math.sqrt(lo * hi)
                if (abs(l.response(lo)) - 1.0) * (abs(l.response(mid)) - 1.0) <= 0:
                    hi = mid
                else:
                    lo = mid
            out.wgc = math.sqrt(lo * hi)
            ref = phs[i] + (phs[i + 1] - phs[i]) * 0.5
            out.phase_margin_deg = 180.0 + _phase_deg_unwrapped(l, out.wgc, ref)
            break

    # ---- phase crossover: angle L passes through -180 ------------------
    for i in range(len(ws) - 1):
        f0, f1 = phs[i] + 180.0, phs[i + 1] + 180.0
        if f0 * f1 < 0:
            lo, hi = ws[i], ws[i + 1]
            ref = phs[i]
            for _ in range(40):
                mid = math.sqrt(lo * hi)
                if (f0) * (_phase_deg_unwrapped(l, mid, ref) + 180.0) <= 0:
                    hi = mid
                else:
                    lo = mid
            out.wpc = math.sqrt(lo * hi)
            m = abs(l.response(out.wpc))
            out.gain_margin_db = (-20.0 * math.log10(m) if m > 1e-300
                                  else math.inf)
            break
    return out


def nyquist_points(l: TF, w_min: float = 1e-3, w_max: float = 1e5,
                   n: int = 2000):
    """
    L(jw) for w > 0, as (real, imag) lists.

    The negative-frequency half is the mirror image, so plotting it adds no
    information -- but it IS part of the contour when you count encirclements,
    which is why the Nyquist page draws both.
    """
    re, im = [], []
    for wi in log_freqs(w_min, w_max, n):
        g = l.response(wi)
        if math.isfinite(g.real) and math.isfinite(g.imag):
            re.append(g.real)
            im.append(g.imag)
    return re, im


def encirclements(l: TF, w_min: float = 1e-4, w_max: float = 1e6,
                  n: int = 6000) -> int:
    """
    Net CLOCKWISE encirclements N of the point -1 by the full Nyquist
    contour, counted by accumulating the angle of (L(jw) + 1).

    The Nyquist criterion is then

            Z = N + P

    Z = closed-loop poles in the right half plane, P = open-loop ones. So for
    an open-loop stable plant (P = 0) the loop is stable exactly when the
    curve does not encircle -1 at all.

    Poles of L at the origin are handled the standard way: the contour makes a
    small detour into the right half plane around s = 0, and for m poles there
    that detour sweeps L through -m*180 degrees on an arc of huge radius. That
    term is added explicitly below -- forget it and every integrator-containing
    loop is miscounted by one.
    """
    ws = log_freqs(w_min, w_max, n)
    total = 0.0
    prev = None
    for wi in ws:
        v = l.response(wi) + 1.0
        if abs(v) < 1e-12:
            continue
        a = cmath.phase(v)
        if prev is not None:
            d = a - prev
            while d > math.pi:
                d -= 2 * math.pi
            while d < -math.pi:
                d += 2 * math.pi
            total += d
        prev = a
    # the w<0 half contributes the mirror image, i.e. the same amount again
    total *= 2.0
    # ...plus the indentation around any poles at the origin
    total += -math.pi * _origin_pole_count(l)
    turns = total / (2.0 * math.pi)
    return int(round(-turns))          # negative angle change = clockwise


def _origin_pole_count(l: TF) -> int:
    """How many poles L has at s = 0 (i.e. how many pure integrators)."""
    d = _trim(list(l.den))
    m = 0
    while m < len(d) and abs(d[len(d) - 1 - m]) < 1e-14:
        m += 1
    return m


def vector_margin(l: TF, w_min: float = 1e-3, w_max: float = 1e5,
                  n: int = 1500) -> float:
    """
    Shortest distance from the Nyquist curve to the -1 point:

        Vm = min_w | 1 + L(jw) | = 1 / Ms

    The single most useful robustness number there is, because unlike gain
    and phase margin it cannot be fooled: a loop can have 60 degrees of phase
    margin and 12 dB of gain margin and still pass within 0.1 of -1 by moving
    diagonally. Aim for Vm >= 0.5 (Ms <= 2).
    """
    best = math.inf
    for wi in log_freqs(w_min, w_max, n):
        best = min(best, abs(1.0 + l.response(wi)))
    return best


def delay_tf_phase(delay_s: float, w: float) -> float:
    """
    Phase of a pure transport delay, in degrees:  -w * T_d.

    A delay is not a transfer function of finite order -- e^{-sT} has no
    polynomial form -- which is why it is applied as a phase correction
    rather than multiplied in. It has UNIT magnitude at every frequency and
    unbounded phase lag: pure loss, exactly as the Real-Time page said.
    """
    return -math.degrees(w * delay_s)


def margins_with_delay(l: TF, delay_s: float, w_min: float = 1e-3,
                       w_max: float = 1e6, n: int = 1200) -> Margins:
    """
    Margins of L(s) e^{-s T_d}. The magnitude is untouched, so the gain
    crossover frequency does not move -- but the phase there is dragged down
    by w_gc * T_d, and the phase margin falls by exactly that much.

    This is the quantitative version of "delay costs phase margin and buys
    nothing", and it is how the Real-Time page's bandwidth ceiling is
    actually derived.
    """
    base = margins(l, w_min, w_max, n)
    out = Margins(stable=base.stable, wgc=base.wgc, wpc=base.wpc)
    if base.wgc > 0 and math.isfinite(base.phase_margin_deg):
        out.phase_margin_deg = (base.phase_margin_deg
                                + delay_tf_phase(delay_s, base.wgc))
    else:
        out.phase_margin_deg = base.phase_margin_deg
    # phase crossover moves down in frequency; rescan including the delay
    ws = log_freqs(w_min, w_max, n)
    prev_f = None
    for wi in ws:
        ph = math.degrees(cmath.phase(l.response(wi))) + \
            delay_tf_phase(delay_s, wi)
        f = ph + 180.0
        if prev_f is not None and prev_f * f < 0:
            m = abs(l.response(wi))
            out.wpc = wi
            out.gain_margin_db = (-20.0 * math.log10(m) if m > 1e-300
                                  else math.inf)
            break
        prev_f = f
    out.stable = out.phase_margin_deg > 0 and out.gain_margin_db > 0
    return out


# ==========================================================================
# Stability tests
# ==========================================================================

def is_stable(den: list[float]) -> bool:
    """Strictly stable: every root has a strictly negative real part."""
    r = poly_roots(den)
    return bool(r) and all(p.real < -1e-12 for p in r)


def classify_stability(den: list[float]) -> str:
    """
    'stable' | 'marginal' | 'unstable', from the pole locations alone.

    Marginal is its own category and not a mild form of stable: an
    undamped SEA spring, a pure integrator, and a frictionless joint are all
    marginal, and all of them will oscillate forever or drift forever in
    response to the smallest disturbance.
    """
    r = poly_roots(den)
    if not r:
        return "stable"
    if any(p.real > 1e-9 for p in r):
        return "unstable"
    if any(abs(p.real) <= 1e-9 for p in r):
        return "marginal"
    return "stable"


def routh_table(coeffs: list[float]) -> list[list[float]]:
    r"""
    Build the Routh array of a descending-power polynomial.

    The point of Routh-Hurwitz is that it answers "are all roots in the left
    half plane?" WITHOUT computing a single root -- using only additions,
    multiplications and divisions of the coefficients. That mattered enormously
    before computers, and it still matters now for one reason: the entries are
    SYMBOLIC in your gains, so you can solve for the exact gain at which the
    system goes unstable instead of hunting for it numerically.

    The special cases (a leading zero, or an entire row of zeros) are handled
    the standard way: substitute a small epsilon, or differentiate the
    auxiliary polynomial. A full row of zeros always means a pair of roots
    symmetric about the origin -- usually a pair sitting exactly on the
    imaginary axis, i.e. the boundary of stability.
    """
    c = _trim(list(coeffs))
    n = len(c)
    if n < 2:
        return [c]
    rows: list[list[float]] = [c[0::2], c[1::2]]
    width = max(len(rows[0]), len(rows[1]))
    rows[0] = rows[0] + [0.0] * (width - len(rows[0]))
    rows[1] = rows[1] + [0.0] * (width - len(rows[1]))

    eps = 1e-9
    for i in range(2, n):
        prev, prev2 = rows[i - 1], rows[i - 2]
        if all(abs(v) < 1e-14 for v in prev):
            # row of zeros: differentiate the auxiliary polynomial from the
            # row above -- the classic sign of poles on the imaginary axis
            order = n - i
            aux = []
            for j, v in enumerate(prev2):
                p = order + 1 - 2 * j
                if p > 0:
                    aux.append(v * p)
            prev = aux + [0.0] * (width - len(aux))
            rows[i - 1] = prev
        if abs(prev[0]) < 1e-14:
            prev = [eps] + prev[1:]
            rows[i - 1] = prev
        row = []
        for j in range(width - 1):
            a, b = prev2[0], prev[0]
            cc = prev2[j + 1] if j + 1 < width else 0.0
            dd = prev[j + 1] if j + 1 < width else 0.0
            row.append((b * cc - a * dd) / b)
        rows.append(row + [0.0])
    return rows


def routh_rhp_count(coeffs: list[float]) -> int:
    """
    Number of closed-loop poles in the right half plane, read off the Routh
    array as the number of SIGN CHANGES down the first column.

    Zero sign changes = stable. Any sign change = that many unstable poles,
    and you know how many before you know where they are.
    """
    rows = routh_table(coeffs)
    col = [r[0] for r in rows if r]
    changes = 0
    prev = None
    for v in col:
        if abs(v) < 1e-14:
            continue
        if prev is not None and (v > 0) != (prev > 0):
            changes += 1
        prev = v
    return changes


def critical_gain(plant: TF, k_lo: float = 1e-4, k_hi: float = 1e9) -> float:
    """
    The proportional gain at which a unity-feedback loop first goes unstable,
    found by bisection on 'is the closed loop stable'.

    Returns inf when no such gain exists -- which is exactly the case for
    first-order and second-order plants, and is the reason those two pages
    insist that instability needs a THIRD pole, or a delay.
    """
    def stable(k):
        return is_stable((plant * k).feedback().den)

    if stable(k_hi):
        return math.inf
    if not stable(k_lo):
        return k_lo
    for _ in range(200):
        mid = math.sqrt(k_lo * k_hi)
        if stable(mid):
            k_lo = mid
        else:
            k_hi = mid
    return math.sqrt(k_lo * k_hi)


# ==========================================================================
# Root locus
# ==========================================================================

def root_locus(plant: TF, gains: list[float]) -> list[list[complex]]:
    """
    Closed-loop pole locations as the loop gain K is swept.

    The closed-loop denominator is  den(s) + K num(s), so:

        K -> 0     the closed-loop poles ARE the open-loop poles
        K -> inf   they migrate to the open-loop ZEROS, and any left over
                   run off to infinity along asymptotes

    Which is the whole reason a derivative term stabilises things: D adds a
    ZERO, and a zero is a destination that pulls the locus toward it. Put the
    zero in the left half plane and you have dragged the poles left with it.
    """
    out = []
    for k in gains:
        den = poly_add(plant.den, [c * k for c in plant.num])
        out.append(poly_roots(den))
    return out


# ==========================================================================
# Compensators
# ==========================================================================

def lead(w_max: float, alpha: float, gain: float = 1.0) -> TF:
    r"""
    Lead compensator, parameterised the way you actually design one:

        C(s) = gain * (s + z) / (s + p),    p = alpha z,  alpha > 1
        z = w_max / sqrt(alpha),   p = w_max * sqrt(alpha)

    so the maximum phase lead lands exactly on w_max, with

        phi_max = asin( (alpha - 1) / (alpha + 1) )

    alpha  4 -> 37 deg,  10 -> 55 deg,  20 -> 65 deg.  Above about 10 the
    returns collapse while the high-frequency gain (= alpha) keeps growing,
    which is why two cascaded modest leads beat one aggressive one.

    A lead compensator IS a filtered derivative. Compare it with the "dirty
    derivative" on the PID page: N s/(s+N) is the same object with the zero
    at the origin.
    """
    z = w_max / math.sqrt(alpha)
    p = w_max * math.sqrt(alpha)
    return TF([gain, gain * z], [1.0, p])


def lead_phase_deg(alpha: float) -> float:
    """phi_max = asin((alpha-1)/(alpha+1)) -- the most a single lead can give."""
    if alpha <= 1:
        return 0.0
    return math.degrees(math.asin((alpha - 1.0) / (alpha + 1.0)))


def alpha_for_phase(phi_deg: float) -> float:
    """Invert the above: how much separation you need for a required lead."""
    s = math.sin(math.radians(min(phi_deg, 88.0)))
    return (1.0 + s) / (1.0 - s)


def lag(w_zero: float, beta: float, gain: float = 1.0) -> TF:
    r"""
    Lag compensator:  C(s) = gain * (s + z) / (s + p),  z = beta p,  beta > 1

    The mirror image of lead. It raises LOW-frequency gain by a factor beta,
    which is what kills steady-state error, and it costs a little phase --
    so you place its zero a decade BELOW the crossover, where the damage does
    not reach.

    A lag is a PI controller that stopped short of putting its pole exactly at
    the origin. It gets you most of the disturbance rejection of integral
    action without the windup and without the phase penalty at crossover.
    """
    p = w_zero / beta
    return TF([gain, gain * w_zero], [1.0, p])


def notch(w0: float, zeta_zero: float = 0.02, zeta_pole: float = 0.5) -> TF:
    r"""
    Notch filter:

        (s^2 + 2 zeta_z w0 s + w0^2) / (s^2 + 2 zeta_p w0 s + w0^2)

    Built to cancel one specific resonance -- the SEA spring, a flexible
    link, a belt. Unity gain everywhere except a deep, narrow hole at w0.

    Use with care, and this is not a stylistic warning: a notch cancels a
    resonance by placing a ZERO on top of a POLE. If the resonance moves --
    the payload changes, the structure warms up, the arm extends -- the pole
    is no longer cancelled, and what is left is a very lightly damped mode
    with your loop gain wrapped around it.
    """
    return TF([1.0, 2 * zeta_zero * w0, w0 * w0],
              [1.0, 2 * zeta_pole * w0, w0 * w0])


def pid_tf(kp: float, ki: float = 0.0, kd: float = 0.0, tau_d: float = 0.0
           ) -> TF:
    r"""
    PID as a transfer function.

        ideal:     Kp + Ki/s + Kd s          =  (Kd s^2 + Kp s + Ki) / s
        realistic: Kp + Ki/s + Kd s/(tau_d s + 1)

    The ideal form is improper -- degree 2 over degree 1 -- meaning infinite
    gain at infinite frequency. It cannot be built and should not be
    simulated. tau_d makes it proper, and that filter is not a detail: it is
    the difference between a controller and a noise amplifier.

    Read against the compensators above: PD is a lead, PI is a lag whose pole
    sits exactly at the origin, PID is a lead-lag.
    """
    if tau_d > 0:
        # Kp + Ki/s + Kd s/(tau s + 1), over the common denominator s(tau s+1)
        num = poly_add(poly_mul([kp], [tau_d, 1.0, 0.0]),
                       poly_mul([ki], [tau_d, 1.0]))
        num = poly_add(num, [kd, 0.0, 0.0])
        return TF(num, [tau_d, 1.0, 0.0])
    return TF([kd, kp, ki], [1.0, 0.0])


# ==========================================================================
# State feedback and pole placement
# ==========================================================================

def ctrb(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Controllability matrix  [B, AB, A^2 B, ..., A^{n-1} B].

    Full rank means every state can be steered by the input. Rank deficient
    means some direction in state space is INVISIBLE TO YOUR ACTUATOR -- and
    no controller, however clever, can move it. That is a mechanical design
    fault, not a tuning problem.
    """
    n = A.shape[0]
    cols = [B]
    for _ in range(1, n):
        cols.append(A @ cols[-1])
    return np.hstack(cols)


def obsv(A: np.ndarray, C: np.ndarray) -> np.ndarray:
    """
    Observability matrix  [C; CA; CA^2; ...; CA^{n-1}].

    Full rank means the output history determines the state. Rank deficient
    means some internal motion produces NO signature at the sensor, so no
    observer and no filter can ever estimate it.
    """
    n = A.shape[0]
    rows = [C]
    for _ in range(1, n):
        rows.append(rows[-1] @ A)
    return np.vstack(rows)


def rank(M: np.ndarray, tol: float = 1e-9) -> int:
    s = np.linalg.svd(M, compute_uv=False)
    return int(np.sum(s > tol * max(1.0, s[0] if len(s) else 1.0)))


def is_controllable(A, B) -> bool:
    return rank(ctrb(A, B)) == A.shape[0]


def is_observable(A, C) -> bool:
    return rank(obsv(A, C)) == A.shape[0]


def place_poles(A: np.ndarray, B: np.ndarray, desired: list[complex]
                ) -> np.ndarray:
    r"""
    SISO pole placement by Ackermann's formula:

        K = [0 ... 0 1] * ctrb(A,B)^{-1} * phi_d(A)

    where phi_d is the DESIRED characteristic polynomial evaluated as a matrix
    polynomial. Returns K as a 1 x n row, for the control law u = -K x.

    What this buys you: with u = -Kx the closed-loop matrix is A - BK, and if
    the pair is controllable you can put its eigenvalues ANYWHERE you like.
    Complete authority over the dynamics.

    What it does not tell you: whether you can afford it. Poles placed far
    into the left half plane demand large gains, large gains demand torque you
    may not have, and the moment the actuator saturates the placement is
    fiction. This is why LQR exists.
    """
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float).reshape(-1, 1)
    n = A.shape[0]
    Wc = ctrb(A, B)
    if rank(Wc) < n:
        raise ValueError("uncontrollable: poles cannot be placed")
    coeffs = np.real(np.poly(np.array(desired, dtype=complex)))
    phi = np.zeros_like(A)
    for c in coeffs:
        phi = phi @ A + c * np.eye(n)
    e = np.zeros((1, n))
    e[0, -1] = 1.0
    return e @ np.linalg.inv(Wc) @ phi


def lqr(A: np.ndarray, B: np.ndarray, Q: np.ndarray, R: np.ndarray
        ) -> np.ndarray:
    r"""
    Continuous-time LQR gain, solved through the Hamiltonian matrix.

    Minimise  J = int( x^T Q x + u^T R u ) dt.  Form

        H = [[ A, -B R^-1 B^T ], [ -Q, -A^T ]]

    take the eigenvectors belonging to its STABLE eigenvalues, split them as
    [X1; X2], and P = X2 X1^{-1} solves the algebraic Riccati equation. Then
    K = R^{-1} B^T P.

    Why it matters more than pole placement in practice: you do not choose
    pole locations (which nobody has good intuition for beyond second order),
    you choose how much you care about error versus how much you care about
    effort. R is the price of torque. That is a question an engineer can
    actually answer.
    """
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    Q = np.asarray(Q, dtype=float)
    R = np.asarray(R, dtype=float)
    Ri = np.linalg.inv(R)
    n = A.shape[0]
    H = np.block([[A, -B @ Ri @ B.T], [-Q, -A.T]])
    vals, vecs = np.linalg.eig(H)
    idx = [i for i in range(2 * n) if vals[i].real < 0]
    V = vecs[:, idx]
    X1, X2 = V[:n, :], V[n:, :]
    P = np.real(X2 @ np.linalg.inv(X1))
    return Ri @ B.T @ P


# ==========================================================================
# Observers
# ==========================================================================

def observer_gain(A: np.ndarray, C: np.ndarray, desired: list[complex]
                  ) -> np.ndarray:
    r"""
    Luenberger observer gain L, placed by DUALITY:

        (A, B) controllable   <->   (A^T, C^T) controllable
                              <->   (A, C) observable

    so designing an observer is designing a controller for the transposed
    system and transposing the answer back:

        L = place_poles(A^T, C^T, desired)^T

    The estimator is  xhat' = A xhat + B u + L (y - C xhat),  and its error
    e = x - xhat obeys  e' = (A - L C) e.  Choose the eigenvalues of A - LC
    and you have chosen how fast the estimate catches up.
    """
    A = np.asarray(A, dtype=float)
    C = np.asarray(C, dtype=float).reshape(1, -1)
    return place_poles(A.T, C.T, desired).T


@dataclass
class ObserverTrace:
    t: list = None
    theta: list = None
    omega: list = None
    theta_meas: list = None
    omega_fd: list = None          # finite-difference estimate
    omega_hat: list = None         # observer estimate
    tau_ext: list = None
    tau_hat: list = None           # disturbance observer estimate


def run_velocity_observer(duration: float = 2.0, dt: float = 1e-3,
                          inertia: float = 0.25, friction: float = 0.4,
                          obs_bw: float = 60.0, noise: float = 2e-4,
                          quant: float = 0.0, tau_ext: float = 0.0,
                          seed: int = 0, estimate_disturbance: bool = False
                          ) -> ObserverTrace:
    r"""
    The comparison that justifies observers existing at all.

    A joint  J w' + b w = tau  is driven with a smooth torque and its angle is
    measured through a noisy, quantised encoder. Velocity is then obtained two
    ways:

        finite difference   (theta_k - theta_{k-1}) / dt
        Luenberger observer using the model plus the same measurement

    The finite difference multiplies the measurement noise by 1/dt -- at 1 kHz
    that is a gain of 1000 -- while the observer only trusts the measurement as
    fast as its own bandwidth allows, and fills the rest in from the model.

    With `estimate_disturbance=True` the state is augmented with an unknown
    constant load torque, giving a DISTURBANCE OBSERVER: the same machinery now
    estimates the external torque with no force sensor at all. That is how
    "sensorless" collision detection and friction compensation actually work.
    """
    import random as _random
    rng = _random.Random(seed)

    if estimate_disturbance:
        # x = [theta, omega, tau_d],  tau_d modelled as constant (x3' = 0)
        A = np.array([[0.0, 1.0, 0.0],
                      [0.0, -friction / inertia, 1.0 / inertia],
                      [0.0, 0.0, 0.0]])
        B = np.array([[0.0], [1.0 / inertia], [0.0]])
        C = np.array([[1.0, 0.0, 0.0]])
        poles = [-obs_bw, -obs_bw * 1.3, -obs_bw * 1.6]
    else:
        A = np.array([[0.0, 1.0], [0.0, -friction / inertia]])
        B = np.array([[0.0], [1.0 / inertia]])
        C = np.array([[1.0, 0.0]])
        poles = [-obs_bw, -obs_bw * 1.4]

    L = observer_gain(A, C, poles)
    n = A.shape[0]
    xhat = np.zeros((n, 1))

    theta = omega = 0.0
    prev_meas = 0.0
    tr = ObserverTrace([], [], [], [], [], [], [], [])
    steps = int(duration / dt)
    for i in range(steps):
        t = i * dt
        u = 3.0 * math.sin(2 * math.pi * 1.0 * t)

        # true plant
        alpha = (u + tau_ext - friction * omega) / inertia
        omega += alpha * dt
        theta += omega * dt

        meas = theta + (rng.gauss(0.0, noise) if noise > 0 else 0.0)
        if quant > 0:
            meas = round(meas / quant) * quant

        fd = (meas - prev_meas) / dt if i else 0.0
        prev_meas = meas

        y = np.array([[meas]])
        xdot = A @ xhat + B * u + L @ (y - C @ xhat)
        xhat = xhat + xdot * dt

        tr.t.append(t)
        tr.theta.append(theta)
        tr.omega.append(omega)
        tr.theta_meas.append(meas)
        tr.omega_fd.append(fd)
        tr.omega_hat.append(float(xhat[1, 0]))
        tr.tau_ext.append(tau_ext)
        tr.tau_hat.append(float(xhat[2, 0]) if n > 2 else 0.0)
    return tr


# ==========================================================================
# A plant with a real resonance, used by several pages
# ==========================================================================

def geared_joint_plant(inertia: float = 0.25, friction: float = 0.4,
                       resonance_hz: float = 0.0, zeta_r: float = 0.05) -> TF:
    r"""
    Torque-to-angle transfer function of a joint:

        1 / ( J s^2 + b s )        rigid: two poles, one of them at the origin

    optionally cascaded with a lightly damped resonance at `resonance_hz` --
    the SEA spring, the harmonic drive's torsion, the flexible link.

    The rigid version already has a pole AT THE ORIGIN, which is why a joint
    drifts under any constant torque and why position control needs feedback
    at all. Adding the resonance is what makes high gain dangerous: it hands
    the loop 180 more degrees of phase lag just above the resonant frequency.
    """
    base = TF([1.0], [inertia, friction, 0.0])
    if resonance_hz and resonance_hz > 0:
        wr = 2 * math.pi * resonance_hz
        base = base * TF([wr * wr], [1.0, 2 * zeta_r * wr, wr * wr])
    return base
