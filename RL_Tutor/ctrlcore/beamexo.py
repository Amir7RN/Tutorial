"""
Mediolateral hip exoskeleton -- the plant, the momentum controller, and the
beam-walking task, in the same language as the linear-systems pages.

Everything here follows the device and the control law reported in

    Naseri, Nalam, Tacca, Huang -- "A Robotic Approach to Assist Mediolateral
    Walking Stability in Humans: Evidence from Narrow Beam Walking"
    Nalam et al. -- "Development of a Hip Abduction-Adduction Exoskeleton for
    Mediolateral Assistance"

Two things are kept strictly apart, because mixing them would be dishonest:

  * MEASURED NUMBERS from those papers live in `HARDWARE` and `TRIAL_RESULTS`.
    They are quoted, never simulated.
  * The frontal-plane simulations below are a THREE-LINK / INVERTED-PENDULUM
    TEACHING MODEL with the published control law bolted on. They reproduce the
    mechanism (momentum error -> dead zone -> distribution -> filter ->
    admittance -> actuator lag -> torque) and the qualitative direction of every
    published effect. They are not a validated model of a human on a beam, and
    no number produced here should be read as an experimental result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# --------------------------------------------------------------------------
# Measured hardware facts (quoted, not simulated)
# --------------------------------------------------------------------------

HARDWARE = {
    "motor": "Maxon EC-60 brushless, one per hip",
    "gear": "100:1 harmonic drive (CSD-20-100-2A-GR-SP674)",
    "drive": "Elmo Gold Solo Twitter, 24 V, up to 40 A, PID velocity mode",
    "high_level": "admittance law on TwinCAT, 1 kHz",
    "low_level_rate_hz": 4000.0,
    "high_level_rate_hz": 1000.0,
    "sensing": "3 x MicroStrain 3DM-CV7-AHRS (torso, left leg, right leg), "
               "cantilevered load cell in parallel with each actuator",
    "bus": "EtherCAT, KEB C6 router",
    "mass_kg": 6.0,
    "rom_deg": 30.0,                 # +/- 30 deg abduction/adduction
    "peak_torque_nm": 72.0,          # 0.8 N.m/kg x 90 kg design user
    "torque_spec_nm_per_kg": 0.8,
    "design_user_kg": 90.0,
    "velocity_bandwidth_hz": 5.0,    # measured, loaded by an 85 kg user
    "volitional_response_ms": 200.0, # the reason 5 Hz was the target
    "max_rendered_stiffness": 95.0,  # N.m/rad, R^2 > 99 %
    "static_r2_min": 99.4,           # %
    "stiffnesses_tested": (12.0, 48.0, 95.04),
    "damping_ratios_tested": (0.6, 0.8, 1.0, 1.2),
    "sweep_range_hz": (1.0, 100.0),
}

# Control law constants, exactly as published
CONTROL = {
    "dead_zone_rad": 0.08,      # ~4.6 deg of torso sway before anything happens
    "stance_share": 0.20,       # 20 % of the corrective torque to the stance hip
    "swing_share": 0.05,        # 5 % to the swing hip
    "gain_levels": (0.75, 1.0),  # 15 % and 20 % of the computed correction
    "filter_hz": 2.0,           # 2nd-order Butterworth on the raw torque
    "filter_zeta": 0.707,
    "admittance_M": 1e-3,
    "admittance_B": 1e-2,
    "admittance_K": 5e-2,
}

# Beam geometry used in the study
BEAM = {
    "total_len_m": 5.6,
    "lead_len_m": 0.6,
    "lead_width_m": 0.084,
    "test_len_m": 5.0,
    "test_width_m": 0.04,
    "trials_per_condition": 18,
    "max_distance_m": 90.0,      # 18 trials x 5 m
}

# Group results (paired t-tests, n = 10). Quoted.
TRIAL_RESULTS = {
    "baseline_pct": 80.9,
    "no_assist_pct": 70.1,
    "active_pct": 79.5,
    "active_vs_no_assist_p": 0.049,
    "active_vs_no_assist_d": 0.89,
    "no_assist_vs_baseline_p": 0.048,
    "active_vs_baseline_p": 0.965,
    "speed_p": 0.0386,
    "speed_d": 0.76,
    "com_dev_p": 0.019,
    "com_dev_d": -0.90,
    "wbam_dev_p": 0.0169,
    "wbam_dev_d": -1.395,
    "helpfulness_mean": 1.57,
    "helpfulness_sd": 0.58,
    "detection_mean": 4.2,
    "detection_sd": 0.8,
    "gain_pct_improvement": 9.4,
    "gain_ci": (1.83, 17.16),
    "extra_metres_per_condition": 8.5,
}


# --------------------------------------------------------------------------
# The plant: a three-link frontal-plane chain
# --------------------------------------------------------------------------

@dataclass
class Subject:
    """Segment properties scaled from height and mass, Winter-style fractions.

    Only the three segments the controller knows about exist here: torso
    (head-arms-trunk lumped) and the two legs.
    """

    height_m: float = 1.75
    mass_kg: float = 75.0

    # fractions of body mass / height
    torso_mass_frac: float = 0.578      # HAT
    leg_mass_frac: float = 0.161        # one whole leg
    leg_len_frac: float = 0.530         # greater trochanter to floor
    torso_len_frac: float = 0.288       # hip to shoulder
    torso_com_frac: float = 0.626       # of torso length, from the hip
    leg_com_frac: float = 0.447         # of leg length, from the floor

    @property
    def m_torso(self) -> float:
        return self.torso_mass_frac * self.mass_kg

    @property
    def m_leg(self) -> float:
        return self.leg_mass_frac * self.mass_kg

    @property
    def l_leg(self) -> float:
        return self.leg_len_frac * self.height_m

    @property
    def l_torso(self) -> float:
        return self.torso_len_frac * self.height_m

    @property
    def d_torso(self) -> float:
        """Hip to torso centre of mass."""
        return self.torso_com_frac * self.l_torso

    @property
    def d_leg(self) -> float:
        """Stance foot to leg centre of mass."""
        return self.leg_com_frac * self.l_leg

    @property
    def I_torso(self) -> float:
        """Torso inertia about its own CoM, slender-rod approximation."""
        return self.m_torso * self.l_torso ** 2 / 12.0

    @property
    def I_leg(self) -> float:
        return self.m_leg * self.l_leg ** 2 / 12.0

    def torso_inertia_about_foot(self, theta_t: float = 0.0) -> float:
        """Parallel-axis torso inertia about the stance-foot contact."""
        r = self.moment_arm(theta_t)
        return self.I_torso + self.m_torso * r ** 2

    def moment_arm(self, theta_t: float = 0.0) -> float:
        """d_ST: stance foot to torso CoM, from the leg/torso triangle."""
        ll, dt = self.l_leg, self.d_torso
        return float(np.sqrt(ll ** 2 + dt ** 2 - 2 * ll * dt * np.cos(np.pi - theta_t)))

    def whole_body_inertia(self, theta_t: float = 0.0) -> float:
        """Everything above the stance foot, for the inverted-pendulum view."""
        legs = 2 * (self.I_leg + self.m_leg * self.d_leg ** 2)
        return self.torso_inertia_about_foot(theta_t) + legs

    # ---- the four published quantities -------------------------------
    def com_x(self, th_t, th_l, th_r) -> float:
        """Eq. 4 -- mass-weighted lateral projection, zeroed in quiet stance."""
        return (self.m_torso * self.d_torso * np.sin(th_t)
                + self.m_leg * self.d_leg * np.sin(th_l)
                + self.m_leg * self.d_leg * np.sin(th_r)) / self.mass_kg

    def com_v(self, th_t, th_l, th_r, w_t, w_l, w_r) -> float:
        """Eq. 5 -- its time derivative."""
        return (self.m_torso * self.d_torso * w_t * np.cos(th_t)
                + self.m_leg * self.d_leg * w_l * np.cos(th_l)
                + self.m_leg * self.d_leg * w_r * np.cos(th_r)) / self.mass_kg

    def wbam(self, th_t, th_l, th_r, w_t, w_l, w_r) -> float:
        """Eq. 3 -- H_wb about the stance foot for the three-link chain."""
        h = (self.I_torso + self.m_torso * self.moment_arm(th_t) ** 2) * w_t
        h += (self.I_leg + self.m_leg * self.d_leg ** 2) * w_l
        h += (self.I_leg + self.m_leg * self.d_leg ** 2) * w_r
        return float(h)

    def torso_momentum(self, th_t, w_t) -> float:
        """Eq. 7 -- the torso's own share of H_wb."""
        return float((self.I_torso
                      + self.m_torso * self.moment_arm(th_t)
                      * self.d_torso) * w_t)

    def desired_torso_state(self, th_l, th_r, w_l, w_r):
        """Eq. 6 -- the torso angle and rate that put CoM and CoM-dot at zero.

        This is the whole control target: solve x_CoM = 0 for theta_T, then
        solve x_CoM_dot = 0 for theta_T_dot at that angle.
        """
        legs_pos = self.m_leg * self.d_leg * (np.sin(th_l) + np.sin(th_r))
        s = -legs_pos / (self.m_torso * self.d_torso)
        s = float(np.clip(s, -0.999, 0.999))
        th_d = float(np.arcsin(s))
        legs_vel = self.m_leg * self.d_leg * (w_l * np.cos(th_l)
                                              + w_r * np.cos(th_r))
        w_d = float(-legs_vel / (self.m_torso * self.d_torso * np.cos(th_d)))
        return th_d, w_d


# --------------------------------------------------------------------------
# The published control law, term by term
# --------------------------------------------------------------------------

def distribution(theta_t: float) -> tuple[float, float]:
    """D(theta_T): (stance share, swing share) with the +/-0.08 rad dead zone.

    Returns (0, 0) inside the dead zone -- the controller is transparent there,
    which is the clause that leaves balance authority with the user.
    """
    dz = CONTROL["dead_zone_rad"]
    if abs(theta_t) <= dz:
        return 0.0, 0.0
    return CONTROL["stance_share"], CONTROL["swing_share"]


class Butter2:
    """Discrete 2nd-order low-pass, matched to the published 2 Hz / 0.707."""

    def __init__(self, f_hz=CONTROL["filter_hz"], zeta=CONTROL["filter_zeta"],
                 dt=1e-3):
        wn = 2 * np.pi * f_hz
        self.a1 = 2 * zeta * wn
        self.a0 = wn * wn
        self.dt = dt
        self.y = 0.0
        self.yd = 0.0

    def step(self, u: float) -> float:
        ydd = self.a0 * (u - self.y) - self.a1 * self.yd
        self.yd += ydd * self.dt
        self.y += self.yd * self.dt
        return self.y


class Admittance:
    """omega_cmd = 1/(M s^2 + B s + K) * tau, with the published constants.

    With M = 1e-3, B = 1e-2, K = 5e-2 the rendered mechanism is so light and so
    soft that the block is effectively a torque-to-velocity pass-through: the
    device behaves as a torque source while keeping an admittance structure, and
    therefore keeps its passivity argument.
    """

    def __init__(self, M=CONTROL["admittance_M"], B=CONTROL["admittance_B"],
                 K=CONTROL["admittance_K"], dt=1e-3):
        self.M, self.B, self.K, self.dt = M, B, K, dt
        self.x = 0.0     # rendered "position" state
        self.v = 0.0     # rendered velocity = commanded joint velocity

    @property
    def wn(self) -> float:
        return float(np.sqrt(self.K / self.M))

    @property
    def zeta(self) -> float:
        return float(self.B / (2 * np.sqrt(self.K * self.M)))

    def step(self, tau: float) -> float:
        a = (tau - self.B * self.v - self.K * self.x) / self.M
        self.v += a * self.dt
        self.x += self.v * self.dt
        return self.v


def actuator_lag_pole(bandwidth_hz=HARDWARE["velocity_bandwidth_hz"]) -> float:
    """The measured 5 Hz closed-loop velocity bandwidth, as a first-order pole."""
    return -2 * np.pi * bandwidth_hz


def rendered_stiffness_check(K_cmd: float) -> dict:
    """What the benchtop admittance identification reported for a given K."""
    wn = float(np.sqrt(K_cmd / CONTROL["admittance_M"]))
    return {
        "K_cmd": K_cmd,
        "within_spec": K_cmd <= HARDWARE["max_rendered_stiffness"],
        "omega_n": wn,
        "omega_n_hz": wn / (2 * np.pi),
    }


# --------------------------------------------------------------------------
# Frontal-plane beam-walking simulation (teaching model)
# --------------------------------------------------------------------------

@dataclass
class BeamSim:
    """One trial of narrow-beam walking, frontal plane only.

    The body above the stance foot is one inverted pendulum in theta_T. Each
    step, the swing leg's angular momentum about the stance foot is injected as
    a disturbance -- this is the physical story the paper starts from: kicking
    the leg out to place the next foot generates angular momentum that moves the
    CoM off the beam line, and the torso has to counter-rotate.

    The human's own balance response is a delayed PD acting on torso sway, with
    a torque ceiling: that ceiling is why assistance can matter at all.
    """

    subject: Subject = field(default_factory=Subject)
    dt: float = 1e-3
    duration: float = 12.0
    step_hz: float = 1.15               # steps per second on a beam: slow
    swing_momentum: float = 3.2         # kg.m^2/s injected per step
    human_kp: float = 210.0             # N.m/rad, delayed
    human_kd: float = 34.0              # N.m.s/rad
    human_delay_s: float = 0.120        # sensorimotor delay
    human_tau_max: float = 46.0         # N.m ceiling on the trunk response
    assist: bool = True
    gain: float = 1.0                   # the published personalisation gain
    extra_mass_kg: float = 0.0          # worn device that is not assisting
    comp_delay_s: float = 0.002         # sample + compute + bus
    seed: int = 0

    def run(self) -> dict:
        rng = np.random.default_rng(self.seed)
        n = int(self.duration / self.dt)
        t = np.arange(n) * self.dt
        s = self.subject

        I = s.whole_body_inertia() + self.extra_mass_kg * (0.55 * s.height_m) ** 2
        m_eff = s.mass_kg + self.extra_mass_kg
        l_com = 0.55 * s.height_m
        g = 9.81

        th = np.zeros(n)
        w = np.zeros(n)
        tau_h = np.zeros(n)
        tau_a = np.zeros(n)
        com = np.zeros(n)
        H = np.zeros(n)
        dH = np.zeros(n)
        fired = np.zeros(n, dtype=bool)

        filt = Butter2(dt=self.dt)
        adm = Admittance(dt=self.dt)
        p_act = actuator_lag_pole()
        tau_act = 0.0                   # actuator-side first-order lag state
        nd_h = int(self.human_delay_s / self.dt)
        nd_c = int(self.comp_delay_s / self.dt)

        step_period = 1.0 / self.step_hz
        next_step = 0.35
        leg_sign = 1.0
        th_l = np.zeros(n)
        th_r = np.zeros(n)
        w_l = np.zeros(n)
        w_r = np.zeros(n)

        fail_idx = n - 1
        half_beam = BEAM["test_width_m"] / 2 + 0.055   # beam plus foot margin
        H_prev = 0.0

        for k in range(1, n):
            # --- swing-leg disturbance, once per step ---------------------
            if t[k] >= next_step:
                next_step += step_period * (1 + 0.06 * rng.standard_normal())
                leg_sign = -leg_sign
                kick = self.swing_momentum * (1 + 0.22 * rng.standard_normal())
                w[k - 1] += -leg_sign * kick / I
                fired[k] = True

            # a smooth stand-in for the two leg angles the IMUs would report
            ph = 2 * np.pi * self.step_hz * t[k]
            th_l[k] = 0.10 * np.sin(ph)
            th_r[k] = -0.10 * np.sin(ph)
            w_l[k] = 0.10 * 2 * np.pi * self.step_hz * np.cos(ph)
            w_r[k] = -w_l[k]

            # --- what the controller can measure -------------------------
            H[k] = s.torso_momentum(th[k - 1], w[k - 1])
            dH[k] = (H[k] - H_prev) / self.dt
            H_prev = H[k]

            th_d, w_d = s.desired_torso_state(th_l[k], th_r[k], w_l[k], w_r[k])
            H_d = s.torso_momentum(th_d, w_d)
            dH_err = dH[k]

            # --- the human's own delayed response ------------------------
            j = max(0, k - 1 - nd_h)
            u_h = -(self.human_kp * th[j] + self.human_kd * w[j])
            tau_h[k] = float(np.clip(u_h, -self.human_tau_max,
                                     self.human_tau_max))

            # --- the exoskeleton -----------------------------------------
            if self.assist:
                jj = max(0, k - 1 - nd_c)
                stance_share, swing_share = distribution(th[jj])
                raw = 0.0
                if stance_share:
                    dHt = H[k] - H_d
                    mag = abs(dHt) + 0.02 * abs(dH_err)
                    raw = -np.sign(th[jj]) * self.gain * (
                        stance_share + swing_share) * 9.0 * mag
                tau_cmd = filt.step(raw)
                v_cmd = adm.step(tau_cmd)
                # the velocity loop tracks v_cmd with the measured 5 Hz
                # bandwidth; its torque is what the user actually feels
                tau_act += self.dt * (-p_act) * (tau_cmd - tau_act)
                tau_a[k] = float(np.clip(tau_act, -HARDWARE["peak_torque_nm"],
                                         HARDWARE["peak_torque_nm"]))
                _ = v_cmd

            # --- inverted-pendulum dynamics -------------------------------
            grav = m_eff * g * l_com * np.sin(th[k - 1])
            acc = (grav + tau_h[k] + tau_a[k]) / I
            w[k] = w[k - 1] + acc * self.dt
            th[k] = th[k - 1] + w[k] * self.dt

            com[k] = l_com * np.sin(th[k])
            if abs(com[k]) > half_beam:
                fail_idx = k
                break

        sl = slice(0, fail_idx + 1)
        speed = 0.62                             # m/s along the beam
        distance = min(BEAM["test_len_m"], t[fail_idx] * speed)
        dist_norm = max(distance, 1e-3)
        return {
            "t": t[sl], "theta": th[sl], "omega": w[sl],
            "tau_human": tau_h[sl], "tau_exo": tau_a[sl],
            "com": com[sl], "H": H[sl], "steps": fired[sl],
            "fell": fail_idx < n - 1,
            "distance_m": distance,
            "com_dev": float(np.sum(np.abs(com[sl])) * self.dt / dist_norm
                             / self.subject.height_m),
            "wbam_dev": float(np.sum(np.abs(H[sl])) * self.dt / dist_norm
                              / (self.subject.mass_kg
                                 * self.subject.height_m * speed)),
            "peak_torque": float(np.max(np.abs(tau_a[sl])) if self.assist else 0.0),
            "duty": float(np.mean(np.abs(tau_a[sl]) > 0.5)) if self.assist else 0.0,
        }


def survival_curves(n_trials=18, **kw) -> dict:
    """Distance-to-step-off across repeated trials, assist vs no assist.

    Same seeds for both conditions, so the two curves see the same sequence of
    swing-leg disturbances -- the paired design of the experiment.
    """
    out = {}
    for label, assist, extra in (("no assist", False, HARDWARE["mass_kg"]),
                                 ("active assist", True, HARDWARE["mass_kg"]),
                                 ("baseline", False, 0.0)):
        d = []
        for i in range(n_trials):
            sim = BeamSim(assist=assist, extra_mass_kg=extra, seed=i, **kw)
            d.append(sim.run()["distance_m"])
        d = np.array(d)
        xs = np.linspace(0, BEAM["test_len_m"], 120)
        surv = np.array([(d >= x).mean() for x in xs])
        out[label] = {"distances": d, "x": xs, "survival": surv,
                      "pct": 100 * d.sum() / (n_trials * BEAM["test_len_m"])}
    return out


# --------------------------------------------------------------------------
# Frequency-domain views used by the pages
# --------------------------------------------------------------------------

def velocity_loop_bode(f, bandwidth_hz=HARDWARE["velocity_bandwidth_hz"],
                       delay_ms=2.0, filter_hz=None):
    """Magnitude (dB) and phase (deg) of the assistance path.

    Three blocks, all measured or published: the closed-loop velocity response
    (first order at the identified bandwidth), the transport delay, and -- if
    asked for -- the 2nd-order Butterworth the raw torque command goes through.
    """
    f = np.asarray(f, dtype=float)
    jw = 1j * 2 * np.pi * f
    H = 1.0 / (1.0 + jw / (2 * np.pi * bandwidth_hz))
    H = H * np.exp(-jw * delay_ms * 1e-3)
    if filter_hz:
        wn = 2 * np.pi * filter_hz
        z = CONTROL["filter_zeta"]
        H = H * wn ** 2 / (jw ** 2 + 2 * z * wn * jw + wn ** 2)
    return 20 * np.log10(np.abs(H)), np.degrees(np.angle(H))


def phase_budget(f_hz, bandwidth_hz=HARDWARE["velocity_bandwidth_hz"],
                 delay_ms=2.0, filter_hz=CONTROL["filter_hz"]):
    """Where the phase at one frequency is spent. Degrees, all negative."""
    w = 2 * np.pi * f_hz
    lag_plant = np.degrees(np.arctan(f_hz / bandwidth_hz))
    lag_delay = np.degrees(w * delay_ms * 1e-3)
    wn = 2 * np.pi * filter_hz
    z = CONTROL["filter_zeta"]
    H = wn ** 2 / ((1j * w) ** 2 + 2 * z * wn * (1j * w) + wn ** 2)
    lag_filter = -np.degrees(np.angle(H))
    return {"velocity loop": -lag_plant, "transport delay": -lag_delay,
            "torque filter": -lag_filter,
            "total": -(lag_plant + lag_delay + lag_filter)}


def reflected_inertia(rotor_inertia=1.0e-4, N=100.0, link_inertia=0.9):
    """Why this device is admittance-controlled and not torque-controlled."""
    reflected = rotor_inertia * N ** 2
    return {"rotor": rotor_inertia, "N": N, "reflected": reflected,
            "link": link_inertia, "total": reflected + link_inertia,
            "ratio": reflected / link_inertia}
