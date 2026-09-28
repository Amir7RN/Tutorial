"""
Active fault tolerance on a robotic knee prosthesis: FSM impedance control, a
residual detector, and a momentum-based compensator.

Follows the mechanism reported in

    "Active Fault-Tolerant Control of Robotic Knee Prostheses for Safe
     Locomotion" (IEEE T-RO submission)

Same separation of concerns as `ctrlcore.beamexo`:

  * `HARDWARE`, `DETECTOR`, `RESULTS` hold MEASURED / PUBLISHED numbers. Quoted.
  * The stance-phase knee simulation, the nominal-behaviour model and the
    detector/compensator implemented here are a TEACHING MODEL. They reproduce
    the architecture (robust input -> nominal prediction -> residual ->
    persistence test -> momentum-scaled additive torque) and the direction of
    every reported effect, on a single-joint plant. The published Gaussian
    Process models are replaced by an explicit nominal profile plus its
    variability band, which is what a GP trained on five minutes of undisturbed
    walking is doing here: predicting the nominal signal and how much it
    normally varies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# --------------------------------------------------------------------------
# Measured / published facts
# --------------------------------------------------------------------------

HARDWARE = {
    "joint": "powered knee, passive ankle",
    "angle_sensor": "potentiometer (ALPS RDC503013A)",
    "load_cell": "6-axis ATI Mini58 between foot and pylon",
    "imus": "2 x MicroStrain 3DM-CV7-AHRS (thigh/socket, shank)",
    "platform": "TwinCAT, 1 kHz, KEB C6 router, Simulink-authored control",
    "rate_hz": 1000.0,
    "fsm_states": ("SF (stance flexion)", "SE (stance extension)",
                   "SwF (swing flexion)", "SwE (swing extension)"),
    "walk_speed_ms": 0.6,
    "extra_speeds_ms": (0.4, 0.8),
    "ramp_deg": 4.6,
    "participants": "8 (5 non-disabled with bypass adapter, 3 transfemoral, K3-K4)",
    "load_filter_hz": 30.0,      # 4th-order Butterworth on load and IMU rates
    "band_of_interest_hz": (0.0, 8.0),
    "torque_filter_hz": 15.0,    # 2nd-order Butterworth on tau_FTM
    "torque_filter_delay_ms": 5.0,
}

DETECTOR = {
    "input": "axial load F_p and its derivative F_p_dot",
    "output": "nominal knee angular velocity",
    "threshold": "T_vel = |mu_omega| + k * sigma_omega",
    "k": 1.0,                    # deliberately sensitive
    "persistence_samples": 10,   # all 10 must exceed -> 10 ms at 1 kHz
    "fault_duration_ms": 200.0,  # injected fault, shorter than volition
    "volitional_window_ms": (200.0, 250.0),
}

RESULTS = {
    "sensitivity_pct": 100.0,
    "false_alarm_pct": 10.8,
    "false_alarm_sd": 10.0,
    "detect_ms": 54.4,
    "detect_sd": 28.7,
    "detect_effective_ms": 43.1,
    "detect_effective_sd": 11.5,
    "detect_delayed_ms": 103.5,
    "momentum_reduction_pct": 47.0,
    "momentum_reduction_other_pct": 27.6,
    "momentum_other": {"0.4 m/s": (30.6, 8.3), "0.8 m/s": (17.3, 2.1),
                       "4.6 deg ramp": (35.9, 1.1)},
    "impulse_true": 0.099,        # N.m.s/kg
    "impulse_false": 0.021,
    "impulse_p": 0.0034,
    "handrail_reduction": 15,     # touches, group mean
    "handrail_Z": 2.41,
    "handrail_p": 0.016,
    "handrail_d": 1.12,
    "critical_without_pct": (87.0, 9.0),
    "critical_with_pct": (15.0, 11.0),
    "phase_nrmse": {"normal": 0.14, "with FTM": 0.38, "without FTM": 1.61},
    "mos_reduction_pct": 46.0,
    "mos_with_vs_normal_p": 0.062,
    "mos_with_vs_normal_d": 0.74,
    "mos_with_vs_without_d": 1.84,
}

# FSM impedance parameter sets. Stance only -- that is where the faults were
# injected, and where the primary deviations were in equilibrium angle and
# stiffness.  (K in N.m/rad, B in N.m.s/rad, theta_eq in rad.)
PARAM_SETS = {
    "level ground (nominal)": {"SF": (180.0, 4.0, 0.12), "SE": (95.0, 3.0, 0.05)},
    "ramp ascent":            {"SF": (250.0, 5.0, 0.26), "SE": (150.0, 3.5, 0.16)},
    "ramp descent":           {"SF": (120.0, 6.5, 0.30), "SE": (70.0, 5.0, 0.22)},
    "stair ascent":           {"SF": (300.0, 5.5, 0.40), "SE": (190.0, 4.0, 0.30)},
    "stair descent":          {"SF": (90.0, 8.0, 0.45), "SE": (60.0, 6.0, 0.35)},
}


def blend(nominal: dict, other: dict, alpha: float) -> dict:
    """P_e(alpha) = P_n + alpha (P_o - P_n).  alpha=1 is a full misclassification."""
    out = {}
    for st in nominal:
        out[st] = tuple(pn + alpha * (po - pn)
                        for pn, po in zip(nominal[st], other[st]))
    return out


# --------------------------------------------------------------------------
# Stance-phase knee plant
# --------------------------------------------------------------------------

@dataclass
class Knee:
    """Shank + foot swinging about the knee, loaded by body weight in stance."""

    mass_kg: float = 75.0
    height_m: float = 1.75
    shank_mass_frac: float = 0.061      # shank + foot
    shank_len_frac: float = 0.285
    thigh_mass_frac: float = 0.100
    thigh_len_frac: float = 0.245

    @property
    def m_sh(self):
        return self.shank_mass_frac * self.mass_kg

    @property
    def l_sh(self):
        return self.shank_len_frac * self.height_m

    @property
    def m_th(self):
        return self.thigh_mass_frac * self.mass_kg

    @property
    def l_th(self):
        return self.thigh_len_frac * self.height_m

    @property
    def J(self):
        """Shank inertia about the knee."""
        return self.m_sh * self.l_sh ** 2 / 3.0

    def momentum(self, w_th, w_sh):
        """H_knee: thigh and shank angular momentum about the knee (Eq. 8)."""
        I_th = self.m_th * self.l_th ** 2 / 3.0
        return float(I_th * w_th + self.J * w_sh)


def axial_load_profile(t, stride_s=1.25, body_weight_n=735.0):
    """The robust signal: double-humped stance load, zero in swing."""
    ph = (t / stride_s) % 1.0
    stance = ph < 0.62
    x = np.clip(ph / 0.62, 0, 1)
    shape = (np.sin(np.pi * x) ** 0.6) * (1.0 + 0.18 * np.cos(2 * np.pi * x))
    return np.where(stance, body_weight_n * shape, 0.0)


def nominal_knee_velocity(t, stride_s=1.25):
    """What a GP trained on undisturbed walking predicts, and its spread.

    Returns (mu, sigma) in rad/s. Stance flexion first (knee yields, negative
    extension rate), then stance extension, then the swing sweep.
    """
    ph = (t / stride_s) % 1.0
    mu = (0.55 * np.sin(2 * np.pi * ph)
          + 1.9 * np.exp(-((ph - 0.72) / 0.06) ** 2)
          - 1.5 * np.exp(-((ph - 0.88) / 0.07) ** 2))
    sigma = 0.16 + 0.10 * np.exp(-((ph - 0.72) / 0.10) ** 2)
    return mu, sigma


def fsm_state(ph: float) -> str:
    if ph < 0.30:
        return "SF"
    if ph < 0.62:
        return "SE"
    if ph < 0.85:
        return "SwF"
    return "SwE"


# --------------------------------------------------------------------------
# The fault-tolerant mechanism
# --------------------------------------------------------------------------

class Detector:
    """Residual on knee angular velocity, with threshold and persistence.

    Two knobs, and both are published: k in T_vel = |mu| + k sigma (set to 1,
    trading false alarms for speed) and N_c consecutive samples (10, i.e. 10 ms
    at 1 kHz).
    """

    def __init__(self, k=DETECTOR["k"], n_consec=DETECTOR["persistence_samples"]):
        self.k = k
        self.n = int(n_consec)
        self.run = 0

    def threshold(self, mu, sigma):
        return abs(mu) + self.k * sigma

    def step(self, residual, mu, sigma) -> bool:
        if abs(residual) > self.threshold(mu, sigma):
            self.run += 1
        else:
            self.run = 0
        return self.run >= self.n


class TorqueFilter:
    """2nd-order Butterworth, 15 Hz, on the compensatory torque."""

    def __init__(self, f_hz=HARDWARE["torque_filter_hz"], dt=1e-3):
        wn = 2 * np.pi * f_hz
        self.a1, self.a0, self.dt = np.sqrt(2) * wn, wn * wn, dt
        self.y = self.yd = 0.0

    def step(self, u):
        ydd = self.a0 * (u - self.y) - self.a1 * self.yd
        self.yd += ydd * self.dt
        self.y += self.yd * self.dt
        return self.y


def fsm_torque(params, state, theta, omega):
    """Impedance law for one FSM state: tau = -K(theta - theta_eq) - B omega."""
    if state not in params:
        return 0.0
    K, B, th_eq = params[state]
    return -K * (theta - th_eq) - B * omega


@dataclass
class FaultTrial:
    """One stride with an injected impedance-parameter fault, FTM on or off."""

    knee: Knee = field(default_factory=Knee)
    dt: float = 1e-3
    stride_s: float = 1.25
    fault_mode: str = "ramp ascent"
    alpha: float = 1.0
    fault_state: str = "SE"
    fault_ms: float = DETECTOR["fault_duration_ms"]
    ftm: bool = True
    detector_k: float = DETECTOR["k"]
    n_consec: int = DETECTOR["persistence_samples"]
    false_alarm: bool = False        # inject a detection with no real fault
    seed: int = 3
    noise: float = 0.05              # rad/s of sensor noise on knee velocity

    def run(self) -> dict:
        rng = np.random.default_rng(self.seed)
        n = int(self.stride_s / self.dt)
        t = np.arange(n) * self.dt
        kn = self.knee
        nominal = PARAM_SETS["level ground (nominal)"]
        faulty = blend(nominal, PARAM_SETS[self.fault_mode], self.alpha)

        mu, sigma = nominal_knee_velocity(t, self.stride_s)
        load = axial_load_profile(t, self.stride_s, 9.81 * kn.mass_kg)

        th = np.zeros(n)
        w = np.zeros(n)
        tau_base = np.zeros(n)
        tau_ftm = np.zeros(n)
        resid = np.zeros(n)
        thr = np.zeros(n)
        flag = np.zeros(n, dtype=bool)
        H = np.zeros(n)
        H_nom = np.zeros(n)

        det = Detector(self.detector_k, self.n_consec)
        filt = TorqueFilter(dt=self.dt)
        active = False
        active_state = None
        detect_idx = None

        # fault window: inside the chosen FSM state
        ph_start = {"SF": 0.12, "SE": 0.40}.get(self.fault_state, 0.40)
        k0 = int(ph_start * n)
        k1 = k0 + int(self.fault_ms * 1e-3 / self.dt)
        fa0 = int(0.22 * n)
        fa1 = fa0 + int(0.04 / self.dt)

        # the plant is driven so that, with nominal parameters, it reproduces
        # the nominal velocity profile; a wrong parameter set then shows up as a
        # genuine deviation rather than as an arbitrary injected signal
        for k in range(1, n):
            ph = (t[k] / self.stride_s) % 1.0
            st = fsm_state(ph)
            in_fault = k0 <= k < k1
            params = faulty if in_fault else nominal

            tau_base[k] = fsm_torque(params, st, th[k - 1], w[k - 1])
            tau_nom = fsm_torque(nominal, st, th[k - 1], w[k - 1])

            # measured velocity: nominal profile plus what the torque error does
            drive = (tau_base[k] - tau_nom) / kn.J
            w[k] = mu[k] + drive * 0.045 + self.noise * rng.standard_normal()
            H[k] = kn.momentum(0.35 * w[k], w[k])
            H_nom[k] = kn.momentum(0.35 * mu[k], mu[k])

            # --- detection -------------------------------------------------
            resid[k] = w[k] - mu[k]
            thr[k] = det.threshold(mu[k], sigma[k])
            hit = det.step(resid[k], mu[k], sigma[k])
            if self.false_alarm and fa0 <= k < fa1:
                hit = True
            if hit and not active and st in ("SF", "SE"):
                active = True
                active_state = st
                if detect_idx is None and not (self.false_alarm and k < k0):
                    detect_idx = k
            # release at the end of the stance sub-state, if the residual is
            # back inside the band (published application logic)
            if active and st != active_state:
                if abs(resid[k]) < thr[k]:
                    active = False
                else:
                    active_state = st

            # --- compensation ---------------------------------------------
            if self.ftm and active:
                # tau_FTM = tau_FSM(nominal state) - tau_FSM(measured state);
                # the same map is evaluated twice, so model bias cancels
                raw = (fsm_torque(nominal, st, th[k - 1], mu[k] * 0.045)
                       - fsm_torque(nominal, st, th[k - 1], w[k] * 0.045))
                raw += 8.0 * (H_nom[k] - H[k])
                tau_ftm[k] = filt.step(raw)
            else:
                tau_ftm[k] = filt.step(0.0)

            tau_tot = tau_base[k] + (tau_ftm[k] if self.ftm else 0.0)
            acc = (tau_tot - tau_nom) / kn.J
            th[k] = th[k - 1] + w[k] * self.dt + 0.5 * acc * self.dt ** 2

        dev = np.abs(H - H_nom)
        rng_nom = float(H_nom.max() - H_nom.min()) or 1.0
        return {
            "t": t, "theta": th, "omega": w, "mu": mu, "sigma": sigma,
            "load": load, "residual": resid, "threshold": thr,
            "tau_base": tau_base, "tau_ftm": tau_ftm,
            "tau_final": tau_base + (tau_ftm if self.ftm else 0.0),
            "H": H, "H_nom": H_nom,
            "fault_window": (t[k0], t[min(k1, n - 1)]),
            "detect_ms": None if detect_idx is None
                         else (t[detect_idx] - t[k0]) * 1e3,
            "momentum_nrmse": float(np.sqrt(np.mean(dev ** 2)) / rng_nom),
            "impulse": float(np.sum(np.abs(tau_ftm)) * self.dt / kn.mass_kg),
        }


def detector_roc(k_values=None, n_strides=40, **kw):
    """Sensitivity and false-alarm rate against the threshold multiplier k.

    This is the trade the paper resolves by choosing k = 1: detect everything
    fast, accept some false alarms, because a false alarm costs a small torque
    impulse while a late detection costs balance.
    """
    if k_values is None:
        k_values = np.linspace(0.4, 3.0, 14)
    alpha = kw.pop("alpha", 1.0)
    sens, far, tdet = [], [], []
    for k in k_values:
        hits, times, fps = 0, [], 0
        for s in range(n_strides):
            faulty = FaultTrial(detector_k=k, ftm=False, alpha=alpha, seed=s,
                                **kw).run()
            if faulty["detect_ms"] is not None:
                hits += 1
                times.append(faulty["detect_ms"])
            clean = FaultTrial(detector_k=k, ftm=False, alpha=0.0, seed=100 + s,
                               **kw).run()
            if clean["detect_ms"] is not None:
                fps += 1
        sens.append(100.0 * hits / n_strides)
        far.append(100.0 * fps / n_strides)
        tdet.append(float(np.mean(times)) if times else np.nan)
    return {"k": np.asarray(k_values), "sensitivity": np.asarray(sens),
            "false_alarm": np.asarray(far), "detect_ms": np.asarray(tdet)}


# --------------------------------------------------------------------------
# Stability metric
# --------------------------------------------------------------------------

def margin_of_stability(com_pos, com_vel, toe_pos, com_height=0.95, g=9.81):
    """MoS = BoS - XCoM, with XCoM = CoM + v / sqrt(g/h).  (Eq. 16.)"""
    xcom = np.asarray(com_pos) + np.asarray(com_vel) / np.sqrt(g / com_height)
    return np.asarray(toe_pos) - xcom


def mos_trace(detect_ms=54.0, compensated=True, duration=1.0, dt=1e-3,
              fault_ms=DETECTOR["fault_duration_ms"], com_height=0.95):
    """How a stance fault moves the margin of stability, and what timing buys.

    The disturbance enters as a CoM acceleration pulse over the fault window;
    compensation removes the remaining part of the pulse once detection has
    fired, so the only thing that separates a good outcome from a bad one is how
    many milliseconds of the pulse were allowed through.
    """
    n = int(duration / dt)
    t = np.arange(n) * dt
    a = np.zeros(n)
    k0 = int(0.20 / dt)
    k1 = k0 + int(fault_ms * 1e-3 / dt)
    a[k0:k1] = 1.35
    if compensated:
        kd = k0 + int(detect_ms * 1e-3 / dt)
        a[min(kd, n - 1):k1] *= 0.15      # residual, not zero: transients pass
    v = np.cumsum(a) * dt
    x = np.cumsum(v) * dt
    toe = np.full(n, 0.11)
    return t, margin_of_stability(x, v, toe, com_height), (t[k0], t[min(k1, n - 1)])


def phase_variable(theta, omega, w=0.12, th0=0.0, w0=0.0):
    """phi_knee = atan2(w (omega - omega_0), theta - theta_0).  (Eq. 15.)"""
    return np.arctan2(w * (np.asarray(omega) - w0), np.asarray(theta) - th0)
