"""
Pages 1-5: Motor selection, and the one question that decides it.

  1  Effective Inertia   -- the vocabulary, then direct drive from first principles
  2  Series Elastic      -- the spring between motor and load, derived in full
  3  Parallel Elastic    -- the spring alongside, and negative effective inertia
  4  DD vs SEA vs PEA    -- torque, speed, inertia, bandwidth, responsiveness
  5  Gearing             -- the N^2 square law and the death of transparency

The order is deliberate. You cannot argue about impedance control until you
know what the environment actually feels when it touches the robot, and that
number -- J_eff -- is set by mechanics long before any software runs.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
)

from ctrlcore.linear import (
    TF,
    bode,
    is_stable,
    log_freqs,
    margins,
    step_response,
)
from ctrlcore.realtime import practical_bandwidth
from ctrlcore.actuators import (
    TOPOLOGY_NAMES,
    gear_output,
    gravity_torque,
    j_eff,
    j_eff_direct,
    j_eff_pea,
    j_eff_sea,
    motor_torque_pea,
    pea_resonance_rad_s,
    reflected_inertia,
    sea_antiresonance_rad_s,
    sea_bandwidth_hz,
    sea_deflection_ratio,
    sea_resonance_rad_s,
    sea_transmissibility,
    spring_torque,
)
from .. import theme
from ..widgets import (
    Card,
    MplCanvas,
    Stat,
    body,
    callout,
    hline,
    math_label,
    stat_row,
    title,
)
from .base import Page

SECTION = "Actuators"


# --------------------------------------------------------------------------
# small shared helper
# --------------------------------------------------------------------------

def slider(lo, hi, val, step=1):
    s = QSlider(Qt.Horizontal)
    s.setRange(lo, hi)
    s.setValue(val)
    s.setSingleStep(step)
    return s


def _compare_table():
    """Direct drive vs geared, same output torque, real-ish numbers."""
    rows = [
        ("Rotor inertia  Jₘ", "0.0040 kg·m²  (big rotor)",
         "0.00004 kg·m²  (100× lighter)"),
        ("Gear ratio  N", "1 : 1", "50 : 1"),
        ("Reflected rotor  Jₘ·N²", "0.0040", "0.00004 × 2500 = 0.100"),
        ("Limb inertia  Jʟ", "0.025", "0.025"),
        ("J_eff at the joint", "0.029 kg·m²", "0.125 kg·m²   (4.3× worse)"),
        ("Backdriveable?", "yes — push it and the rotor turns",
         "no — stiction may need 20 N before anything moves"),
        ("Motor mass", "heavy", "light, but the gearbox is not"),
        ("Force sensing", "free, from motor current",
         "current tells you about the gearbox, not the world"),
    ]
    t = QTableWidget(len(rows), 3)
    t.setHorizontalHeaderLabels(["", "Direct drive, big motor",
                                 "Small motor + 50:1 gearbox"])
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    t.setColumnWidth(0, 170)
    t.setColumnWidth(1, 250)
    t.setColumnWidth(2, 300)
    t.setMinimumHeight(44 + 46 * len(rows))
    return t


def _verdict_table():
    """Which J_eff you want, band by band."""
    rows = [
        ("LOW ω\nslow lean, holding a\npose, human leading",
         "MODERATE — you want some",
         "Too low and the joint is floppy: it drifts under its own weight, "
         "wanders when bumped, and feels dead to a human trying to guide it. "
         "You want enough impedance here to hold a pose and reject slow "
         "disturbances. This is the one band where MORE is often right.",
         "PEA wins: it removes the gravity torque without needing the motor."),
        ("MID ω\nthe robot's own\nmotions, 1–30 Hz",
         "SMOOTH — flat is what you want",
         "This is your working band, so what matters is not the level but the "
         "SHAPE. Resonances and antiresonances here are poison: they make the "
         "plant gain swing wildly with frequency, which no fixed set of gains "
         "can handle. A flat curve is a plant you can tune once and trust.",
         "DD wins: flat everywhere by construction. SEA's resonance pair often "
         "lands exactly here, which is why SEAs are harder to tune."),
        ("HIGH ω\nimpacts, collisions,\nsomeone's hand",
         "AS LOW AS POSSIBLE",
         "Collision energy is ½·J_eff·ω². This is the number that decides "
         "whether a mistake is a bump or an injury, and no controller reaches up "
         "here to help — an impact is broadband, far above any loop bandwidth. "
         "Whatever mechanics presents is what lands.",
         "SEA wins outright: J_eff drops to J_L, the rotor is disconnected. "
         "PEA does nothing here. DD gives you the full machine."),
    ]
    t = QTableWidget(len(rows), 4)
    t.setHorizontalHeaderLabels(
        ["Band", "What you want", "Why", "Who wins"])
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    for c, w in enumerate((150, 175, 330, 270)):
        t.setColumnWidth(c, w)
    t.setMinimumHeight(360)
    return t


def _decision_table():
    """Machine type -> topology, with real examples."""
    rows = [
        ("Humanoid arm, works beside people",
         "SEA, or QDD + soft body",
         "Baxter/Sawyer (SEA); 1X Neo (QDD + polymer skin + proprioception)",
         "Impact energy is the binding constraint. Either filter it "
         "mechanically or keep J_eff tiny everywhere."),
        ("Humanoid / biped leg",
         "Hybrid: SEA ankle, PEA knee, QDD hip",
         "Agility Digit, Cassie, ANYmal",
         "Ankle takes the ground impacts; knee holds the body weight for hours; "
         "hip needs speed for swing."),
        ("Running quadruped",
         "QDD, low ratio (~6:1)",
         "MIT Cheetah, Mini Cheetah",
         "Leg repositioning speed beats everything. A 10 Hz mechanical filter "
         "would fight the gait. Compliance is done in software."),
        ("Industrial arm, caged",
         "High-ratio geared, position control",
         "Classic 6-axis welders and palletisers",
         "Nothing unexpected is in the workspace, so precision and stiffness "
         "dominate. Backdrivability is irrelevant."),
        ("Collaborative manipulator",
         "Geared + joint torque sensors",
         "KUKA LBR iiwa, Franka Emika",
         "The third path: keep the gearbox, and buy back torque control with a "
         "sensor on the OUTPUT side, past the friction."),
        ("Prosthesis / exoskeleton",
         "SEA, or geared + admittance",
         "Powered ankle prostheses; most exos",
         "Attached to a person, so compliance is safety. The spring doubles as "
         "the torque sensor and stores push-off energy."),
        ("Surgical / precision tool",
         "Stiff, geared, high-resolution",
         "da Vinci and similar",
         "Compliance is the enemy. Safety comes from scale, limits and the "
         "human in the loop, not from being soft."),
    ]
    t = QTableWidget(len(rows), 4)
    t.setHorizontalHeaderLabels(
        ["Machine", "Topology", "Real examples", "Why"])
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    for c, w in enumerate((200, 200, 230, 300)):
        t.setColumnWidth(c, w)
    t.setMinimumHeight(500)
    return t


def slider_row(label, sld, readout):
    lay = QHBoxLayout()
    lay.setSpacing(8)
    lb = QLabel(label)
    lb.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
    lb.setFixedWidth(150)
    lay.addWidget(lb)
    lay.addWidget(sld, 1)
    readout.setStyleSheet(
        f"color:{theme.ACCENT}; font-family:Consolas; font-weight:700;"
        f"background:transparent; min-width:78px;")
    lay.addWidget(readout)
    return lay


def preset_row(*pairs):
    """A row of preset buttons. `pairs` are (label, callable) tuples."""
    lay = QHBoxLayout()
    lay.setSpacing(8)
    for label, fn in pairs:
        b = QPushButton(label)
        b.clicked.connect(lambda _=False, f=fn: f())
        lay.addWidget(b)
    lay.addStretch(1)
    return lay


# ==========================================================================
# The elastic element as a plant -- shared by pages 1 to 4 of this block
#
# Every claim these four pages make about "the bandwidth of the spring" comes
# from one of the functions below, so they live in one place and each page
# plots the same objects rather than asserting numbers at each other.
# ==========================================================================

def elastic_corner_hz(k: float, j: float) -> float:
    r"""
    (1/2pi) sqrt(k / J) -- the ONLY frequency a spring-plus-inertia has.

    A spring on its own has no frequency; an inertia on its own has no
    frequency. Put them together and there is exactly one, and it is the
    frequency at which the spring's torque k*theta and the inertial torque
    J*w^2*theta are equal. Below it the spring dominates; above it the
    inertia does. Every "bandwidth" on these four pages is this expression
    with a different J substituted in.
    """
    if k <= 0 or j <= 0:
        return 0.0
    return math.sqrt(k / j) / (2.0 * math.pi)


def reduced_inertia(j_m: float, j_l: float) -> float:
    """Jm*JL/(Jm+JL) -- the inertia the SERIES mode actually swings."""
    if j_m <= 0 or j_l <= 0:
        return 0.0
    return j_m * j_l / (j_m + j_l)


def spring_damping(k: float, j_m: float, j_l: float, zeta_r: float) -> float:
    """
    The physical damping b_s (N m s/rad) across the series spring that gives
    its mode a damping ratio of zeta_r.

    The relative coordinate d = theta_m - theta_L obeys
        J_red * d'' + b_s * d' + k * d = 0,     J_red = Jm JL/(Jm+JL)
    so zeta_r = b_s / (2 sqrt(k J_red)), which inverts to the line below.
    This is the parameter the whole SEA ceiling turns on, and on real
    hardware it is small -- a steel flexure is 0.02 to 0.05.
    """
    jr = reduced_inertia(j_m, j_l)
    if jr <= 0 or k <= 0:
        return 0.0
    return 2.0 * zeta_r * math.sqrt(k * jr)


def dd_plant(j_m: float, j_l: float, b: float = 0.4) -> TF:
    """Rigid: motor torque in, load angle out. Two poles, one at the origin."""
    return TF([1.0], [j_m + j_l, b, 0.0])


def pea_plant(j_m: float, j_l: float, k: float, b: float = 0.4) -> TF:
    """
    Parallel spring: the SAME rigid body, with +k added to the denominator.

    Note what did NOT happen -- the order did not go up, and no pole left the
    real axis on its way anywhere new. A parallel spring adds stiffness to a
    plant you already had.
    """
    return TF([1.0], [j_m + j_l, b, k])


def sea_plant(j_m: float, j_l: float, k: float, b: float = 0.4,
              zeta_r: float = 0.05) -> TF:
    r"""
    Series spring: motor torque in, LOAD angle out. Fourth order.

    With D(s) = b_s s + k the two bodies give

        Jm s^2 theta_m = tau - D (theta_m - theta_L)
        JL s^2 theta_L + b s theta_L = D (theta_m - theta_L)

    Eliminating theta_m:

        theta_L     D(s)
        ------- = ----------------------------------------------------------
          tau     Jm JL s^4 + [Jm b + (Jm+JL) b_s] s^3
                             + [(Jm+JL) k + b b_s] s^2 + b k s

    Four poles: the origin, a load pole, and the lightly damped PAIR that is
    the entire subject of these pages.
    """
    bs = spring_damping(k, j_m, j_l, zeta_r)
    num = [bs, k]
    den = [j_m * j_l,
           j_m * b + (j_m + j_l) * bs,
           (j_m + j_l) * k + b * bs,
           b * k,
           0.0]
    return TF(num, den)


def sea_crossover_ceiling_hz(k: float, j_m: float, j_l: float,
                             zeta_r: float, gm_db: float = 6.0) -> float:
    r"""
    The ceiling derived on the Bode page:  w_gc <= 2 zeta_r w_res / g.

    At the resonance the spring hands the loop 180 degrees of lag AND
    multiplies its magnitude by Q = 1/(2 zeta_r). Demanding a gain margin of
    g = 10^(GM/20) and assuming the usual 20 dB/decade rolloff above
    crossover gives the bound. Returns hertz.

    Note what is in it and what is not: k, the inertias and the SPRING's
    damping. Not your gains, not your sample rate, not your control law.
    """
    if k <= 0 or zeta_r <= 0:
        return math.inf
    w_res = sea_resonance_rad_s(k, j_m, j_l)
    g = 10.0 ** (gm_db / 20.0)
    return (2.0 * zeta_r * w_res / g) / (2.0 * math.pi)


def pd_loop(plant: TF, kp: float, kd: float, tau_d: float = 1.0 / 400.0) -> TF:
    """Plant with a filtered-derivative PD wrapped round it, as shipped."""
    ctrl = TF([kd, kp], [tau_d, 1.0]) if kd > 0 else TF([kp], [1.0])
    return plant * ctrl


def closed_loop_bw_hz(t: TF, f_hi: float = 5.0e4) -> float:
    """
    Where |T| first falls 3 dB below its DC value -- the closed-loop
    bandwidth, same definition as any filter.

    This is the number to compare across topologies, because crossover is
    not comparable: a PEA's loop can cross over while the phase is still
    near zero, which makes its "phase margin" meaningless without also
    saying what the closed loop actually does.
    """
    try:
        dc = abs(t.response(1e-6))
    except Exception:
        return 0.0
    if dc <= 0:
        return 0.0
    target = dc / math.sqrt(2.0)
    lo, hi = 1e-4, f_hi * 2 * math.pi
    if abs(t.response(lo)) < target:
        return 0.0
    if abs(t.response(hi)) > target:
        return f_hi
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        if abs(t.response(mid)) > target:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi) / (2.0 * math.pi)


#: memo for max_sea_crossover_hz -- the search is the expensive part of the
#: SEA widgets and its answer does not depend on Kp, so dragging the gain
#: slider must not pay for it.
_xover_cache: dict[tuple, float] = {}


def max_sea_crossover_hz(j_m: float, j_l: float, k: float, zeta_r: float,
                         kd: float = 0.0, gm_min: float = 6.0) -> float:
    """
    The largest crossover this spring actually allows at `gm_min` dB of gain
    margin -- found by search rather than estimated.

    This is the honest counterpart to sea_crossover_ceiling_hz(): the formula
    assumes a 20 dB/decade rolloff between crossover and the resonance, and
    when the real rolloff is steeper the formula is conservative. Showing
    both is the point, so this has to be cheap enough to run on a slider.

    Gain margin falls monotonically with Kp, so bisect on Kp instead of
    sweeping it. Returns hertz, or 0.0 if no gain meets the margin.
    """
    key = (round(j_m, 6), round(j_l, 6), round(k, 3), round(zeta_r, 4),
           round(kd, 3), round(gm_min, 2))
    hit = _xover_cache.get(key)
    if hit is not None:
        return hit

    plant = sea_plant(j_m, j_l, k, 0.4, zeta_r)

    if kd <= 0.0:
        # Fast path, and it is exact rather than a shortcut. A pure gain adds
        # no phase, so w_pc does not move with Kp at all -- which means
        #     GM(Kp) dB = GM(1) dB - 20 log10(Kp)
        # and the largest admissible gain can be read off in one step instead
        # of bisected for. Two margins() calls instead of twenty-eight, which
        # is what makes the stiffness sweep on the comparison page draggable.
        base = margins(pd_loop(plant, 1.0, 0.0), 1e-2, 1e5, 800)
        gm1 = base.gain_margin_db
        if not math.isfinite(gm1):
            out = 0.0                            # no -180 crossing: see below
        else:
            kp_max = 10.0 ** ((gm1 - gm_min) / 20.0)
            if kp_max <= 0:
                out = 0.0
            else:
                mg = margins(pd_loop(plant, kp_max, 0.0), 1e-2, 1e5, 800)
                out = mg.wgc / (2.0 * math.pi) if mg.wgc else 0.0
        if not math.isfinite(gm1):
            # phase never reaches -180, so gain margin is not the binding
            # constraint; fall through to the general search below
            pass
        else:
            _xover_cache[key] = out
            return out

    def ok(kp: float) -> bool:
        # a coarse grid is plenty here: we only need the sign of a 6 dB test
        gm = margins(pd_loop(plant, kp, kd), 1e-2, 1e5, 400).gain_margin_db
        return (not math.isfinite(gm)) or gm >= gm_min

    lo, hi = 1e-3, 1e6
    if not ok(lo):
        _xover_cache[key] = 0.0
        return 0.0
    if ok(hi):
        lo = hi
    else:
        for _ in range(28):                      # 1e9 range down to ~2% in Kp
            mid = math.sqrt(lo * hi)
            if ok(mid):
                lo = mid
            else:
                hi = mid
    mg = margins(pd_loop(plant, lo, kd), 1e-2, 1e5, 400)
    out = mg.wgc / (2.0 * math.pi) if mg.wgc else 0.0
    if len(_xover_cache) > 4096:                 # bounded; these are cheap
        _xover_cache.clear()
    _xover_cache[key] = out
    return out


# ==========================================================================
# PAGE 1 -- Effective inertia and direct drive
# ==========================================================================

class EffectiveInertiaPage(Page):
    TITLE = "Effective Inertia"
    SUBTITLE = ("Before any controller exists, mechanics has already decided how "
                "heavy your robot feels to whoever touches it.")
    SECTION = SECTION
    NOTES = "material p.1-3"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            (
                "<b>The question this whole section answers.</b> You grab the output shaft of a robot joint and "
                "shake it. How much mass do you feel?<br><br>Not \"how much does the robot weigh\" — how much "
                "<i>inertia is presented at the point of contact</i>. That number is called the <b>effective "
                "inertia</b> J<sub>eff</sub>, and it influences acceleration and contact response. Safety, force"
                " estimation and tracking also depend on speed, damping, compliance, sensing and "
                "feedback.<br><br>Three mechanical layouts give three completely different answers. Same motor, "
                "same limb."
            ), "key"))

        v = Card("the four symbols, used everywhere below")
        v.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>J<sub>m</sub></b></td><td>motor (rotor) inertia — the "
            "spinning mass inside the motor itself</td></tr>"
            "<tr><td><b>J<sub>L</sub></b></td><td>limb / load inertia — the arm, "
            "leg or tool bolted to the output</td></tr>"
            "<tr><td><b>k</b></td><td>spring stiffness, if there is a spring "
            "anywhere in the drivetrain</td></tr>"
            "<tr><td><b>ω</b></td><td>frequency of the interaction — how fast the "
            "outside world is pushing on the joint</td></tr>"
            "</table>"))
        v.add(body(
            "That last one is the one people forget. <b>ω is not a property of "
            "the robot.</b> It is a property of what is happening to it. A slow "
            "lean and a sharp impact are the same joint at two different "
            "frequencies — and, as the next two pages show, they can feel like "
            "two completely different machines.", dim=True))
        self.add(v)

        self.add(hline())

        # ---- direct drive derivation -------------------------------------
        self.add(title((
                           "① Direct drive — the rigid single-inertia model"
                       )))
        self.add(body(
            (
                "In the ideal direct-drive model the motor is rigidly connected to the limb with ratio N = 1. "
                "Quasi-direct drive (QDD) uses a low-ratio transmission; its rotor inertia must first be "
                "reflected as N²J<sub>m</sub>. The two bodies are welded into one body, so they share one "
                "acceleration."
            )))

        d = Card("derivation")
        d.add(math_label(r"J_m\,\ddot\theta_m = \tau - J_L\,\ddot\theta"))
        d.add(body("Motor and limb move together, so θ<sub>m</sub> = θ. Collect "
                   "them:", dim=True))
        d.add(math_label(r"(J_m + J_L)\,\ddot\theta = \tau"))
        d.add(body("Divide by the acceleration and read off what the world feels:",
                   dim=True))
        d.add(math_label(r"\boxed{\;J_{eff} = J_m + J_L\;}", 18))
        d.add(body(
            "<b>No ω anywhere.</b> The answer is the same whether you lean on it "
            "for ten seconds or hit it in one millisecond. Hit a wall, move "
            "slowly — either way you feel the combined mass of motor <i>and</i> "
            "limb.", dim=True))
        self.add(d)

        self.add(callout(
            "<b>Why this is dangerous.</b> High-torque direct drive is risky "
            "around humans: there is nothing between the rotor and the person. "
            "A fast impact drives the full J<sub>m</sub> + J<sub>L</sub> into "
            "whatever it hit — and into the motor's own magnets and bearings on "
            "the way back.<br><br>"
            "<b>Unless</b> you pair it with external compliance. A soft skin, a "
            "compliant end-effector, a remote centre of compliance — put the give "
            "somewhere else and direct drive becomes acceptable again.", "warn"))

        # ---- interactive --------------------------------------------------
        i = Card("feel it: direct drive is flat in frequency")
        i.add(body(
            "Slide the two inertias. The curve is what an outside push feels "
            "across the whole frequency range — and for direct drive it is a "
            "flat line at J<sub>m</sub> + J<sub>L</sub>. Remember this shape; "
            "the next two pages break it.", dim=True))

        self.s_jm = slider(1, 200, 40)
        self.s_jl = slider(1, 200, 60)
        self.l_jm = QLabel()
        self.l_jl = QLabel()
        i.add_layout(slider_row("Motor  Jₘ", self.s_jm, self.l_jm))
        i.add_layout(slider_row("Limb  Jʟ", self.s_jl, self.l_jl))

        self.st_sum = Stat("J_eff  (kg·m²)", "--", theme.ACCENT)
        self.st_ratio = Stat("rotor share", "--", theme.WARN)
        i.add_layout(stat_row(self.st_sum, self.st_ratio))

        self.canvas = MplCanvas(width=7.4, height=2.9)
        i.add(self.canvas)
        self.add(i)

        self.s_jm.valueChanged.connect(self._redraw)
        self.s_jl.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            (
                "<b>The same inertia, three different questions.</b><br><br>• <b>Energy at a given speed:</b> E "
                "= ½J<sub>eff</sub>θ̇². Doubling J<sub>eff</sub> at the same joint speed doubles kinetic energy;"
                " how much reaches a contact also depends on compliance and dissipation. Here θ̇ is joint "
                "angular velocity, not the excitation frequency ω.<br><br>• <b>Torque and acceleration:</b> "
                "τ<sub>net</sub> = J<sub>eff</sub>α, with α = θ̈. At the same net torque, doubling inertia "
                "halves acceleration. To keep the same acceleration, it requires twice the net torque. Motor "
                "torque must also cover friction, gravity and other loads. A larger motor may add rotor inertia,"
                " so sizing is a coupled design problem.<br><br>• <b>Connect to first order:</b> for "
                "J<sub>eff</sub>ω̇ + bω = τ<sub>motor</sub>, with constant b and a torque step from rest, "
                "τ<sub>c</sub> = J<sub>eff</sub>/b. Doubling inertia doubles the time constant, the 10–90% rise "
                "time and the 2% settling time (about 4τ<sub>c</sub>). Initial acceleration halves, while final "
                "speed τ<sub>motor</sub>/b stays the same. This is a torque-to-speed model; final speed is not "
                "automatically a desired position.<br><br>• <b>Connect to second order:</b> for a position loop,"
                " J<sub>eff</sub>θ̈ + B<sub>total</sub>θ̇ + K<sub>total</sub>θ = input. Its natural frequency is"
                " ω<sub>n</sub> = √(K<sub>total</sub>/J<sub>eff</sub>) and damping ratio is ζ = "
                "B<sub>total</sub>/(2√(J<sub>eff</sub>K<sub>total</sub>)). Changing inertia at fixed gains "
                "changes both. Natural frequency, bandwidth and settling time are related but distinct; the "
                "first-order J/b rule is not a universal position-loop formula.<br><br>The rotor share says how "
                "much of this rigid model’s inertia comes from the motor. The elastic-actuator pages next show "
                "why a frequency-dependent apparent inertia needs a different interpretation."
            ), "key"))

        # ---- why it matters -------------------------------------------------
        self.add(hline())
        self.add(title("Why J_eff decides the design, the motor and the controller"))

        m = Card("1 · for mechanism design — watch out for DISTAL mass")
        m.add(body(
            "Inertia about a joint is <b>Σ m<sub>i</sub> d<sub>i</sub>²</b>. The "
            "distance is <b>squared</b>, so mass at the end of the linkage is "
            "punished quadratically. A 1 kg motor at the wrist costs a shoulder "
            "joint <i>sixteen times</i> more inertia than the same motor at "
            "0.25 of the reach."))
        m.add(body(
            "<b>This is why real robots look the way they do:</b><br>"
            "&nbsp;&nbsp;• <b>Proximal actuator placement</b> — put the motors in "
            "the torso or upper arm and transmit power outward. Tendons/cables "
            "(1X Neo, most dexterous hands), belts, or push-rods.<br>"
            "&nbsp;&nbsp;• <b>Parallel &amp; closed-chain mechanisms</b> — delta "
            "robots and five-bar linkages exist almost entirely to keep actuator "
            "mass at the base. Same reason for differential wrists.<br>"
            "&nbsp;&nbsp;• <b>Lightweight distal links</b> — carbon fibre "
            "forearms, hollow sections, and accepting the structural compliance "
            "that comes with them.<br>"
            "&nbsp;&nbsp;• <b>Biology did this first</b> — your calf muscles sit "
            "high on the shin and pull the foot through the Achilles tendon. "
            "Almost no muscle mass is in the foot."))
        self.add(m)

        s = Card("2 · for motor specification")
        s.add(body(
            (
                "The number a datasheet will not tell you directly is the <b>inertia match</b>, "
                "J<sub>L</sub>/J<sub>m</sub> (reflected through the gearing).<br><br>&nbsp;&nbsp;• <b>Ratio ≈ "
                "1–3</b> is the classic servo sweet spot: best acceleration per amp, well-damped, easy to "
                "tune.<br>&nbsp;&nbsp;• <b>Ratio ≫ 10</b> (load dominates) — the motor struggles to control the "
                "load; resonances show up; you need a gearbox or a bigger motor.<br>&nbsp;&nbsp;• <b>Ratio ≪ "
                "1</b> (rotor dominates) — you are mostly spending torque accelerating your own rotor. This is "
                "what over-gearing does, and it is the whole problem on page 29.<br><br>So J<sub>eff</sub> is "
                "not just an output of the design — it is the <b>input to motor sizing</b>. Pick the topology "
                "first, compute J<sub>eff</sub>, then choose the motor."
            )))
        self.add(s)

        c = Card("3 · for control — and what you can and cannot fix in software")
        c.add(body(
            "<b>What control CAN do:</b><br>"
            "&nbsp;&nbsp;• <b>Feedforward / computed torque.</b> If you know "
            "J(q), compute τ = J(q)q̈<sub>d</sub> + C(q,q̇)q̇ + g(q) and apply it "
            "directly. The feedback loop then only has to correct model error "
            "instead of fighting the full inertia. This is the single biggest "
            "win available and it costs nothing but a model.<br>"
            "&nbsp;&nbsp;• <b>Inertia shaping.</b> With force feedback you can "
            "make the joint <i>feel</i> lighter than it is — admittance control "
            "with M<sub>v</sub> &lt; J<sub>real</sub>.<br>"
            "&nbsp;&nbsp;• <b>Input shaping / notch filters</b> for the "
            "resonances that light distal links introduce."))
        c.add(body(
            "<b>What control CANNOT do — and this is the important half.</b> "
            "Every one of those tricks works <b>only inside the loop "
            "bandwidth</b>. Above it, the physical inertia is exactly what the "
            "world feels, because the controller has not noticed yet.<br><br>"
            "An impact is <b>broadband</b> — a 1 ms collision has energy out to "
            "hundreds of Hz, far above any joint loop. So during the event that "
            "actually matters for safety, your beautiful inertia-shaping law "
            "contributes <b>nothing</b>. Whatever J<sub>eff</sub> the mechanics "
            "presents up there is what hits the person.<br><br>"
            "How far can you push inertia shaping? Roughly: rendering "
            "M<sub>v</sub> much below J<sub>real</sub> demands loop gain, and "
            "loop gain plus delay is instability. A factor of 2–5 is realistic; "
            "a factor of 100 is not. <b>You cannot software your way out of a "
            "heavy rotor.</b>", dim=True))
        self.add(c)

        # ---- DD vs geared, with numbers --------------------------------------
        g = Card("\"big low-inertia motor\" vs \"small motor + gearbox\" — "
                 "the same joint, two ways")
        g.add(body(
            "Both deliver 40 N·m at the joint. They are not remotely the same "
            "machine."))
        g.add(_compare_table())
        g.add(body(
            "The geared version has a rotor <b>100× lighter</b> and still ends up "
            "presenting <b>4× more inertia</b> to the world, because N² = 2,500 "
            "beats the mass saving comfortably. And that inertia arrives with "
            "backlash and stiction attached.", dim=True))
        self.add(g)

        b = Card("so what bandwidth does each actually get?")
        b.add(body(
            "First, separate the three numbers from the Real-Time page — this is "
            "where people go wrong:<br><br>"
            "&nbsp;&nbsp;<b>Current loop:</b> 10–40 kHz on both. Electrical, and "
            "essentially free.<br>"
            "&nbsp;&nbsp;<b>Joint control loop:</b> 1–4 kHz on both. This is your "
            "<i>sample rate</i>, not your bandwidth.<br>"
            "&nbsp;&nbsp;<b>Usable force/impedance bandwidth:</b> this is where "
            "they diverge, and it is set by <b>mechanics</b>, not by the CPU."))
        b.add(body(
            (
                "<table cellpadding='6'><tr><td><b>Direct drive / QDD</b></td><td><b>50–100+ "
                "Hz</b></td><td>Limited by structural resonance of the link, encoder noise and loop delay. "
                "Nothing mechanical is filtering the force path.</td></tr><tr><td><b>High-ratio "
                "geared</b></td><td><b>~10–30 Hz</b></td><td>Limited by friction nonlinearity, backlash, and "
                "torsional windup of the flexspline. The gearbox is a low-pass filter you did not ask for — and "
                "worse, a <i>nonlinear</i> one.</td></tr><tr><td><b>SEA</b></td><td><b>10–20 "
                "Hz</b></td><td>Limited by the spring-load resonance. The Series Elastic Actuators lesson "
                "derives the relevant model.</td></tr></table>"
            )))
        b.add(body(
            "<b>Notice all three sit far below the 1 kHz loop rate.</b> That is "
            "the answer to \"we sample at 1 kHz, so why can't we react in 1 ms?\" "
            "— the sampling is not the constraint. The mechanics is.", dim=True))
        self.add(b)

        # ==================================================================
        # the primitive the next two pages are entirely built out of
        # ==================================================================
        self.add(hline())
        self.add(title("Before the spring pages: what \"the bandwidth of an "
                       "elastic element\" even means"))

        pr = Card("a spring has no frequency; an inertia has no frequency; "
                  "together they have exactly one")
        pr.add(body(
            "The next two pages both bolt a spring onto this actuator — one in "
            "series, one in parallel — and both immediately start quoting a "
            "frequency for it. It is worth being precise about where that "
            "frequency comes from, because <b>it is not a property of the "
            "spring.</b>"))
        pr.add(body(
            "Ask a spring on its own \"what is your bandwidth?\" and the "
            "question is meaningless — a spring produces torque kθ at any "
            "frequency you like, instantly, forever. Ask an inertia on its own "
            "and it is equally meaningless. <b>The frequency appears only when "
            "you ask which of the two wins</b>, and that has an exact answer:"))
        pr.add(math_label(r"\underbrace{k\,\theta}_{\text{spring torque}} "
                          r"\;=\; \underbrace{J\,\omega^2\theta}"
                          r"_{\text{inertial torque}} "
                          r"\qquad\Longrightarrow\qquad "
                          r"\omega = \sqrt{\frac{k}{J}}, \qquad "
                          r"f = \frac{1}{2\pi}\sqrt{\frac{k}{J}}", 17))
        pr.add(body(
            (
                "The θ cancels, which is why the answer does not depend on how far you push. <b>Below that "
                "frequency the spring's torque is the bigger of the two and the element behaves like a spring. "
                "Above it the inertial torque wins and the element behaves like a mass.</b> That crossing "
                "defines a spring–inertia natural frequency. A bandwidth additionally requires a specified "
                "input, output, damping and controller."
            )))
        pr.add(callout(
            "<b>And here is the thing that makes the next two pages "
            "different from each other: the formula has a J in it, and "
            "<i>which</i> J depends on where you bolt the spring.</b><br><br>"
            "&nbsp;&nbsp;• Bolt it <b>in parallel</b> and the spring works "
            "against the whole rigid machine, so J = J<sub>m</sub> + "
            "J<sub>L</sub>. One frequency, and it is the joint's new natural "
            "frequency.<br>"
            "&nbsp;&nbsp;• Bolt it <b>in series</b> and the spring has a "
            "different inertia on each end, so it produces <b>three</b> "
            "frequencies — √(k/J<sub>L</sub>) looking one way, "
            "√(k/J<sub>m</sub>) looking the other, and "
            "√(k/J<sub>red</sub>) for the two ends swinging against each other, "
            "with J<sub>red</sub> = J<sub>m</sub>J<sub>L</sub>/(J<sub>m</sub>+"
            "J<sub>L</sub>).<br><br>"
            "Same spring. Same stiffness. <b>One frequency or three, decided "
            "purely by which inertias the spring can see.</b> Every argument "
            "on the next three pages traces back to that sentence.", "key"))
        self.add(pr)

        el = Card("watch the two torques cross — this one crossing is what "
                  "every later plot is made of")
        el.add(body(
            "Left: the two torques against frequency, on log axes, for a "
            "one-radian motion. The <b>flat</b> line is the spring, kθ, which "
            "does not care about frequency at all. The <b>rising</b> line is "
            "the inertia, Jω²θ, climbing at 40 dB per decade. Where they cross "
            "is f<sub>n</sub>, and the shading says which one you are "
            "feeling.<br><br>"
            "Right: let it go from one radian and watch it ring at exactly "
            "that frequency — the same number, seen in the time domain.<br><br>"
            "<b>Two things to do.</b> Raise <b>k</b> and watch the flat line "
            "lift, pushing the crossing to the <i>right</i>: a stiffer spring "
            "stays in charge up to a higher frequency. Then raise <b>J</b> and "
            "watch the rising line move <i>left</i>, dragging the crossing "
            "down. Note that quadrupling either one only doubles "
            "f<sub>n</sub> — the square root is why stiffness is such an "
            "expensive way to buy bandwidth.", dim=True))
        self.s_ek = slider(10, 4000, 300)        # N m / rad
        self.s_ej = slider(2, 400, 100)          # x0.001 kg m^2
        self.l_ek, self.l_ej = QLabel(), QLabel()
        el.add_layout(slider_row("spring k (N·m/rad)", self.s_ek, self.l_ek))
        el.add_layout(slider_row("inertia J (×0.001)", self.s_ej, self.l_ej))
        self.st_efn = Stat("f_n = √(k/J)/2π", "--", theme.ACCENT)
        self.st_ewn = Stat("ω_n", "--", theme.VIOLET)
        self.st_eper = Stat("ring period", "--", theme.GOOD)
        self.st_ecmp = Stat("at 2·f_n the inertia wins by", "--", theme.WARN)
        el.add_layout(stat_row(self.st_efn, self.st_ewn, self.st_eper,
                               self.st_ecmp))
        self.c_el = MplCanvas(width=7.6, height=3.0, ncols=2)
        self._el_drawn = False
        el.add(self.c_el)
        self.t_el = body("", dim=True)
        el.add(self.t_el)
        self.add(el)
        for s in (self.s_ek, self.s_ej):
            s.valueChanged.connect(self._redraw_elastic)
        self._redraw_elastic()

        self.add(callout(
            (
                "<b>Real machines, so the numbers mean something.</b><br><br>&nbsp;&nbsp;• <b>MIT Cheetah 3 / "
                "Mini Cheetah</b> — QDD, ~6:1. Chose low reflected inertia over torque density so the legs could"
                " sense ground contact through the motors alone. No force sensors in the feet at "
                "all.<br>&nbsp;&nbsp;• <b>KUKA LBR iiwa / Franka</b> — high-ratio harmonic drives <i>plus a "
                "torque sensor on every joint output</i>. That third option recovers torque control without "
                "backdrivability, at considerable cost. The Control Paradigms section returns to "
                "it.<br>&nbsp;&nbsp;• <b>ANYmal</b> — SEA legs (ANYdrive). Accepted ~10 Hz joint bandwidth to "
                "get passive impact survival on rough terrain.<br>&nbsp;&nbsp;• <b>Universal Robots cobots</b> —"
                " geared and position-controlled, with collision detection from motor current. Safe by "
                "<i>stopping</i>, not by being compliant. A completely different safety philosophy, and a "
                "legitimate one."
            ), "good"))

        self.add(callout(
            "<b>The takeaway, in one line each.</b><br><br>"
            "<b>Mechanism design:</b> keep mass proximal, because d² is "
            "merciless.<br>"
            "<b>Motor spec:</b> aim for an inertia match near 1–3 <i>after</i> "
            "choosing the topology.<br>"
            "<b>Control:</b> feedforward what you know; and accept that above "
            "your bandwidth, mechanics is the only controller you have.<br><br>"
            "This is why this tutorial puts actuator mechanics before the "
            "control <i>paradigms</i>, and real-time behaviour before "
            "everything. The linear-systems pages came first only to give you "
            "the vocabulary — \"pole\", \"damping\", \"margin\" — that the "
            "sentence above is written in.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_elastic(self):
        """
        The one crossing the next three pages are built out of: spring torque
        (flat) against inertial torque (rising), for a fixed one-radian
        motion. They meet at sqrt(k/J), and that is the whole definition.
        """
        k = float(self.s_ek.value())
        j = self.s_ej.value() / 1000.0
        self.l_ek.setText(f"{k:.0f}")
        self.l_ej.setText(f"{j:.3f}")

        wn = math.sqrt(k / j)
        fn = wn / (2.0 * math.pi)
        self.st_efn.set(f"{fn:.2f} Hz")
        self.st_ewn.set(f"{wn:.1f} rad/s")
        self.st_eper.set(f"{1.0/fn*1000:.1f} ms")
        # at twice f_n the inertial torque is (2)^2 = 4x the spring torque,
        # always, for every k and J -- which is worth seeing stay fixed
        self.st_ecmp.set("4.0×")

        c = self.c_el
        c.clear()
        a1, a2 = c.axes

        ws = log_freqs(wn / 60.0, wn * 60.0, 300)
        spring = [k] * len(ws)
        inertial = [j * w * w for w in ws]
        a1.loglog(ws, spring, color=theme.ACCENT, lw=2.2,
                  label="spring  k·θ  (flat)")
        a1.loglog(ws, inertial, color=theme.WARN, lw=2.2,
                  label="inertia  J·ω²·θ  (+40 dB/dec)")
        a1.axvline(wn, color=theme.VIOLET, lw=1.4, ls="-.")
        a1.scatter([wn], [k], s=60, color=theme.VIOLET, zorder=6)
        lo, hi = ws[0], ws[-1]
        a1.axvspan(lo, wn, color=theme.ACCENT, alpha=0.07)
        a1.axvspan(wn, hi, color=theme.WARN, alpha=0.07)
        a1.set_xlim(lo, hi)
        a1.set_ylim(min(inertial[0], k) / 30.0, max(inertial[-1], k) * 3.0)
        a1.text(wn / 7.0, k * 12.0, "spring wins\n(feels like a SPRING)",
                color=theme.ACCENT, fontsize=7.5, ha="center")
        a1.text(wn * 7.0, k / 14.0, "inertia wins\n(feels like a MASS)",
                color=theme.WARN, fontsize=7.5, ha="center")
        a1.set_xlabel("frequency ω  (rad/s)")
        a1.set_ylabel("torque for θ = 1 rad  (N·m)")
        a1.set_title("they cross at ω = √(k/J) — that IS f_n", fontsize=8.5)
        c.legend(a1, loc="upper left")

        # the same number in the time domain: release from 1 rad, light damping
        zeta = 0.04
        wd = wn * math.sqrt(1 - zeta * zeta)
        dur = 6.0 * (2 * math.pi / wd)
        ts = [dur * i / 600 for i in range(601)]
        ys = [math.exp(-zeta * wn * t) * math.cos(wd * t) for t in ts]
        a2.plot(ts, ys, color=theme.ACCENT, lw=2.0)
        a2.plot(ts, [math.exp(-zeta * wn * t) for t in ts],
                color=theme.VIOLET, lw=1.0, ls=":")
        a2.plot(ts, [-math.exp(-zeta * wn * t) for t in ts],
                color=theme.VIOLET, lw=1.0, ls=":")
        a2.axhline(0, color=theme.BORDER, lw=1.0)
        for n in range(1, 7):
            tp = n / fn
            if tp < dur:
                a2.axvline(tp, color=theme.TEXT_FAINT, lw=0.7, ls=":")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("θ (rad)")
        a2.set_title(f"released from 1 rad — rings at {fn:.2f} Hz",
                     fontsize=8.5)
        c.refresh(layout=not self._el_drawn)
        self._el_drawn = True

        self.t_el.setText(
            f"<b>k = {k:.0f} N·m/rad against J = {j:.3f} kg·m² gives "
            f"f<sub>n</sub> = {fn:.2f} Hz.</b> Below that the joint pushes "
            f"back with stiffness; above it, with mass. To double "
            f"f<sub>n</sub> you must <b>quadruple k</b> — and on the next "
            f"page quadrupling k is exactly what stops the spring protecting "
            f"anybody, which is the whole trade in one sentence.")

    def _vals(self):
        return self.s_jm.value() / 1000.0, self.s_jl.value() / 1000.0

    def _redraw(self):
        jm, jl = self._vals()
        self.l_jm.setText(f"{jm:.3f}")
        self.l_jl.setText(f"{jl:.3f}")
        tot = j_eff_direct(jm, jl)
        self.st_sum.set(f"{tot:.3f}")
        self.st_ratio.set(f"{100.0 * jm / tot:.0f}%")

        c = self.canvas
        c.clear()
        ws = [10 ** (x / 40.0) for x in range(-40, 121)]
        c.ax.semilogx(ws, [tot] * len(ws), color=theme.ACCENT, lw=2.4,
                      label="direct drive")
        c.ax.semilogx(ws, [jl] * len(ws), color=theme.TEXT_FAINT, lw=1.2,
                      ls="--", label="limb alone (Jʟ)")
        c.ax.set_xlabel("interaction frequency ω  (rad/s)")
        c.ax.set_ylabel("J_eff  (kg·m²)")
        c.ax.set_ylim(0, max(tot * 1.35, 0.01))
        c.legend(loc="lower left")
        c.refresh()


# ==========================================================================
# PAGE 2 -- Series elastic actuator
# ==========================================================================

class SEAPage(Page):
    TITLE = "Series Elastic Actuators"
    SUBTITLE = ("Put a spring between motor and load and the effective inertia "
                "stops being a number — it becomes a function of frequency.")
    SECTION = SECTION
    NOTES = "material p.2"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The idea in one line.</b> If the robot hits something, let the "
            "spring compress <i>first</i> and absorb the energy before the motor "
            "can be damaged — or before the motor can do damage.<br><br>"
            "The spring is <b>passive</b>. It does not need electricity or a "
            "computer. A 1 kHz control loop takes 1.0 ms just to think; a spring "
            "compresses in 0.1 ms. The spring protects the human before the "
            "software even knows a collision happened.", "key"))

        # ---- derivation ---------------------------------------------------
        d = Card("derivation — two bodies now, not one")
        d.add(body(
            "The spring separates motor and load, so they are no longer the same "
            "body. Two equations, two angles:"))
        d.add(math_label(r"J_m\,\ddot\theta_m = -k\,(\theta_m - \theta_L)"))
        d.add(math_label(r"J_L\,\ddot\theta_L = k\,(\theta_m - \theta_L) + \tau_L"))
        d.add(body("Laplace the first and solve for the motor angle:", dim=True))
        d.add(math_label(r"(J_m s^2 + k)\,\theta_m = k\,\theta_L"
                         r"\quad\Rightarrow\quad "
                         r"\theta_m = \frac{k}{k + J_m s^2}\,\theta_L"))
        d.add(body("Substitute into the second and collect θ<sub>L</sub>:",
                   dim=True))
        d.add(math_label(r"\left[J_L s^2 + \frac{k\,J_m s^2}{k + J_m s^2}\right]"
                         r"\theta_L = \tau_L"))
        d.add(math_label(r"\boxed{\;J_{eff}(s) = J_L + "
                         r"\frac{k\,J_m}{k + J_m s^2}\;}", 18))
        d.add(body("On the imaginary axis s = jω, so s² = −ω²:", dim=True))
        d.add(math_label(r"J_{eff}(\omega) = J_L + \frac{k\,J_m}{k - J_m\omega^2}",
                         16))
        self.add(d)

        # ---- THE key clarification -------------------------------------------
        self.add(callout(
            (
                "<b>Before the plot: three experiments must be kept separate.</b><br><br>1 · <b>Prescribe motor "
                "angle, measure load angle:</b> f_n = √(k/J_L)/(2π) is the undamped resonance of θ_L/θ_m. It is "
                "not automatically a closed-loop bandwidth. The same angular frequency ω_n is the motor "
                "driving-point anti-resonance when torque, rather than angle, is the motor input.<br><br>2 · "
                "<b>Apply load torque with motor torque zero, measure load angle:</b> ω_a = √(k/J_m) is the load"
                " driving-point anti-resonance. Load angle vanishes in the ideal harmonic solution while the "
                "motor moves; J_eff diverges because it divides by load acceleration.<br><br>3 · <b>Both "
                "inertias free:</b> ω_r = √(k(1/J_m + 1/J_L)) is the relative-mode natural frequency. An "
                "undamped periodic forcing at this mode has no bounded steady solution; the formal load-side "
                "J_eff tends to zero.<br><br>Use f = ω/(2π) to compare in Hz. These are transfer-function "
                "features, not sampling rates or universal actuator bandwidth limits."
            ), "warn"))

        # ---- the two limits ----------------------------------------------
        lim = Card("the two limits — this is the whole argument for SEAs")
        g = QGridLayout()
        g.setSpacing(12)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)

        lo = Card("ω → 0   (slow push)")
        lo.add(math_label(r"J_{eff} \rightarrow J_L + J_m", 16))
        lo.add(body(
            "The spring is stiff enough to <b>move the motor</b>. Push slowly and "
            "you drag the whole machine along — you feel exactly what direct "
            "drive would give you. No benefit at all down here."))
        g.addWidget(lo, 0, 0, 1, 2)

        hi = Card("ω → ∞   (high-speed impact)")
        hi.add(math_label(r"J_{eff} \rightarrow J_L", 16))
        hi.add(body(
            "The motor's inertia cannot accelerate that fast, so the spring takes "
            "essentially all the relative motion and stores the disturbance "
            "energy. The spring <b>decouples motor from limb</b>, and the "
            "environment just feels the light limb.<br><br>"
            "<b>This is the safety mechanism.</b> The rotor is mechanically "
            "hidden during exactly the events that would hurt someone."))
        g.addWidget(hi, 1, 0, 1, 2)
        lim.add_layout(g)
        self.add(lim)

        # ---- interactive ---------------------------------------------------
        i = Card("watch the transition")
        i.add(body(
            "Drag the stiffness. Low k moves the whole transition to low "
            "frequency: safer, but the joint goes mushy and slow. High k pushes "
            "it right: crisper and faster, but the spring stops protecting "
            "anything until the impact is very fast indeed.", dim=True))

        self.s_jm = slider(1, 200, 40)
        self.s_jl = slider(1, 200, 60)
        self.s_k = slider(5, 4000, 300)
        self.l_jm, self.l_jl, self.l_k = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("Motor  Jₘ", self.s_jm, self.l_jm))
        i.add_layout(slider_row("Limb  Jʟ", self.s_jl, self.l_jl))
        i.add_layout(slider_row("Spring  k  (N·m/rad)", self.s_k, self.l_k))

        self.st_anti = Stat("ω_a antiresonance", "--", theme.BAD)
        self.st_res = Stat("ω_r resonance", "--", theme.VIOLET)
        self.st_hi = Stat("J_eff at impact", "--", theme.ACCENT)
        self.st_defl = Stat("spring deflection @1 rad/s", "--", theme.TEXT_DIM)
        i.add_layout(stat_row(self.st_anti, self.st_res, self.st_hi,
                              self.st_defl))

        self.canvas = MplCanvas(width=7.4, height=3.1)
        i.add(self.canvas)
        self.add(i)

        for s in (self.s_jm, self.s_jl, self.s_k):
            s.valueChanged.connect(self._redraw)
        # _redraw() also fills canvas_bw, which is built further down the page,
        # so the first call is deferred to the end of __init__.

        # ---- is the spring deflecting? ---------------------------------------
        d2 = Card("\"below the antiresonance, is the spring deflecting at all?\"")
        d2.add(body(
            "<b>Yes — but by an amount that vanishes as ω².</b> Solve the same "
            "equations for the deflection instead of the inertia:"))
        d2.add(math_label(r"\left|\frac{\theta_m - \theta_L}{\theta_L}\right| = "
                          r"\frac{J_m\,\omega^2}{\left|k - J_m\omega^2\right|}",
                          16))
        d2.add(body(
            "At low frequency this is ≈ J<sub>m</sub>ω²/k — near zero. The spring "
            "bends by <b>exactly</b> the amount needed to generate the force that "
            "accelerates the rotor, and no more.<br><br>"
            "So the answer to \"is it the motor rotating, or the spring "
            "deflecting?\" is: <b>overwhelmingly the motor rotating</b>, with a "
            "sliver of deflection. That is precisely <i>why</i> you feel "
            "J<sub>m</sub> + J<sub>L</sub> down there — the rotor really is being "
            "dragged along, so its mass really is in your hand."))
        d2.add(body(
            (
                "Immediately above ω<sub>a</sub> the ratio is large, then decreases toward 1 from above as "
                "frequency increases: now the spring is taking most of the relative motion and the rotor is "
                "barely moving. <b>The handover from \"motor moves\" to \"spring bends\" IS the transition on the "
                "plot.</b>"
            ), dim=True))
        self.add(d2)

        # ---- what happens after the antiresonance ----------------------------
        d3 = Card("\"and after the antiresonance it just converges to Jʟ — what "
                  "does that mean physically?\"")
        d3.add(body(
            "Above ω<sub>r</sub> the rotor is <b>inertially unreachable</b>. To "
            "move it that fast you would need a force the spring cannot transmit "
            "in the time available, so from the load's point of view the far end "
            "of the spring might as well be <b>bolted to the wall</b>."))
        d3.add(body(
            (
                "The load is then a mass on a spring anchored to ground. Push it fast enough and the spring "
                "force kθ becomes negligible next to the inertial force J<sub>L</sub>ω²θ — so what you feel is a"
                " <b>free mass J<sub>L</sub></b>, and nothing else.<br><br><b>That is the safety mechanism, "
                "stated properly:</b> the rotor is not \"absorbed\" or \"cushioned\". Its motion contributes "
                "progressively less in this high-frequency limit. The spring remains physically connected, and "
                "real collision response also depends on contact, damping and travel limits."
            ),
            dim=True))
        self.add(d3)

        # ---- motor-side bandwidth --------------------------------------------
        self.add(hline())
        self.add(title("Now the MOTOR side — a different question, a different "
                       "plot"))

        bw = Card("motor → load transmissibility")
        bw.add(body(
            "Everything above was the world pushing the load. Now hold the motor "
            "under stiff position control and wiggle <i>it</i>. How much of that "
            "motion reaches the arm?"))
        bw.add(math_label(r"\frac{\theta_L}{\theta_m} = \frac{k}{J_L s^2 + k} "
                          r"\quad\Rightarrow\quad "
                          r"\left|\frac{\theta_L}{\theta_m}\right| = "
                          r"\frac{k}{\left|k - J_L\omega^2\right|}", 16))
        bw.add(math_label(r"f_n = \frac{1}{2\pi}\sqrt{\frac{k}{J_L}}", 17))
        bw.add(body(
            (
                "Far below f_n, the load follows prescribed motor motion approximately 1:1. Near f_n, the "
                "undamped formula amplifies motion without bound at the pole. Above f_n, phase reverses and the "
                "amplitude eventually rolls off as 1/ω². A real damped response has a finite peak. This is a "
                "<b>motor-angle-to-load-angle transmissibility</b>, not the motor-torque-to-load-angle plant or "
                "a completed feedback design."
            )))
        self.canvas_bw = MplCanvas(width=7.4, height=2.8)
        bw.add(self.canvas_bw)
        self.add(bw)

        self.add(callout(
            (
                "<b>Spring torque sensing and spring torque control are different.</b><br><br>Measuring δ = "
                "θ_m−θ_L gives τ_s ≈ kδ for the elastic component. Sensor noise, quantisation, calibration and "
                "damping affect the estimate and its bandwidth.<br><br>To change that torque, the motor must "
                "change δ while interacting with the load. Current-loop dynamics, motor authority, both "
                "inertias, feedback and the load boundary condition all matter. A fast measurement does not "
                "guarantee a fast correction, and f_n alone is not a universal force-control limit."
            ),
            "key"))

        # ==================================================================
        # the ceiling, closed round a real loop and measured
        # ==================================================================
        self.add(hline())
        self.add(title("The ceiling, and a loop running into it"))

        why = Card("why the spring's frequency is a CEILING and not just "
                   "another pole")
        why.add(body(
            (
                "The imposed-motion resonance above is one boundary-condition example. The following position "
                "loop instead uses motor torque as input and load angle as output. Its lightly damped relative "
                "mode can constrain gain and crossover. How restrictive it is depends on the controller, "
                "damping, sensing and required margins."
            )))
        why.add(body(
            (
                "A lightly damped second-order mode changes phase from approximately 0° toward −180°, passing "
                "−90° at its natural frequency. Its magnitude there is approximately 1/(2ζ_r) relative to DC for"
                " the canonical low-pass factor. When this factor multiplies the rest of the loop, the "
                "<b>total</b> phase and gain may approach the instability condition together. Do not assign the "
                "total loop’s −180° crossing to the spring factor alone."
            )))
        why.add(callout(
            "<b>That coincidence is the whole problem.</b> An ordinary plant "
            "is safe because phase and magnitude are racing each other: by "
            "the time the phase crawls to −180°, the plant's own rolloff has "
            "crushed the gain far below 1, so there is nothing left to "
            "sustain an oscillation.<br><br>"
            "<b>A lightly damped series resonance breaks that race in the "
            "worst possible way — it supplies the phase AND boosts the gain, "
            "at the same frequency.</b> It is the same structural problem as "
            "a pure transport delay, except a delay merely refuses to "
            "attenuate, whereas a resonance actively amplifies.<br><br>"
            "So gain margin, which was infinite on the rigid actuator of the "
            "previous page, becomes finite the moment you fit the spring — "
            "and it can be <i>negative before you have tuned anything</i>.",
            "warn"))
        why.add(body(
            "Demanding a gain margin of a factor g at that resonance, and "
            "taking the loop's magnitude out there as roughly "
            "ω<sub>gc</sub>/ω<sub>res</sub>, gives the bound the Bode page "
            "derived:"))
        why.add(math_label(r"Q\,\frac{\omega_{gc}}{\omega_{res}} \leq "
                           r"\frac{1}{g} \qquad\Longrightarrow\qquad "
                           r"\boxed{\;\omega_{gc} \;\leq\; "
                           r"\frac{2\zeta_r}{g}\,\omega_{res}\;}", 17))
        why.add(body(
            (
                "This estimate assumes a particular high-frequency loop roll-off and a phase crossing near the "
                "mode. The mechanical quantities appear explicitly, but the controller and loop shape are "
                "assumptions of the derivation. It is a conditional crossover estimate, not an immutable "
                "hardware bandwidth law."
            ), dim=True))
        why.add(callout(
            "<b>Two honest caveats, because the widget below will show you "
            "both whether or not this card mentions them.</b><br><br>"
            "<b>1 · That bound assumes the −180° crossing happens AT the "
            "resonance.</b> On the Bode page's plant it did. On <i>this</i> "
            "plant it does not: θ<sub>L</sub>/τ has a pole at the origin and "
            "a real load pole, which between them drag the phase to −180° "
            "<b>below</b> the resonance — at about 0.7 ω<sub>res</sub> — so "
            "gain margin is measured before the resonance peak is even "
            "reached. The bound is therefore <b>conservative here, often by "
            "a factor of five or more.</b><br><br>"
            "<b>2 · Because of that, ζ<sub>r</sub> barely helps a pure-P "
            "loop.</b> Damping the spring lowers the resonance peak, but the "
            "peak is not what is binding; meanwhile the damper adds a zero at "
            "−k/b<sub>s</sub> that <i>lifts</i> the loop gain near the phase "
            "crossing. Measured on this plant, raising ζ<sub>r</sub> from "
            "0.02 to 0.4 moves the achievable crossover from 5.3 Hz to "
            "4.3 Hz — slightly <b>worse</b>.<br><br>"
            "<b>Neither caveat rescues the spring.</b> The ceiling is still "
            "there, it is still mechanical, and it still scales with √k. It "
            "is simply set by the phase crossing rather than by Q. Press "
            "presets 5 and 6 to see the case where ζ<sub>r</sub> becomes "
            "decisive after all.", "warn"))
        self.add(why)

        law = Card("what the ceiling actually is on this plant — measured, "
                   "not assumed")
        law.add(body(
            "The widget searches for the largest crossover that still holds "
            "6 dB of gain margin, at each stiffness. Run that search across "
            "four decades of k and the answer is strikingly regular:"))
        law.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>k (N·m/rad)</b></td><td><b>f<sub>res</sub></b></td>"
            "<td><b>√(k/J<sub>L</sub>)/2π</b></td>"
            "<td><b>max crossover</b></td>"
            "<td><b>÷ √(k/J<sub>L</sub>)</b></td></tr>"
            "<tr><td>50</td><td>7.3 Hz</td><td>4.6 Hz</td><td>2.76 Hz</td>"
            "<td>0.60</td></tr>"
            "<tr><td>180</td><td>13.8 Hz</td><td>8.7 Hz</td><td>5.27 Hz</td>"
            "<td>0.60</td></tr>"
            "<tr><td>600</td><td>25.2 Hz</td><td>15.9 Hz</td><td>9.52 Hz</td>"
            "<td>0.60</td></tr>"
            "<tr><td>2000</td><td>45.9 Hz</td><td>29.1 Hz</td><td>16.9 Hz</td>"
            "<td>0.58</td></tr>"
            "<tr><td>6000</td><td>79.6 Hz</td><td>50.3 Hz</td><td>27.8 Hz</td>"
            "<td>0.55</td></tr>"
            "</table>"))
        law.add(callout(
            (
                "<b>The last column is a crossover limit for this particular loop design.</b><br><br>Here "
                "f<sub>gc,max</sub> ≈ 0.6√(k/J<sub>L</sub>)/(2π) over the tabulated range. The ratio comes from "
                "this controller, damping and margin requirement. It is not an identity defining an SEA’s "
                "closed-loop −3 dB bandwidth.<br><br>Increasing spring stiffness raises the mechanical frequency"
                " scale as √k when the inertias stay fixed. In this design family that permits a higher "
                "crossover. Four times the stiffness gives twice the frequency scale; it also gives one quarter "
                "of the deflection at the same static torque. For impacts, peak deflection depends on the "
                "incident energy as well."
            ),
            "key"))
        self.add(law)

        ceil = Card("close a PD loop round the spring and watch the margin "
                    "die")
        ceil.add(body(
            "This is the SEA plant in full — motor torque in, <b>load</b> "
            "angle out, four poles — with a filtered-derivative PD wrapped "
            "round it. Left is the open-loop Bode of L, where the margins "
            "live; right is the closed-loop step, where you see what the "
            "margins meant.<br><br>"
            "The dotted vertical is the resonance. The solid green vertical "
            "is your crossover. <b>The entire game is keeping those two "
            "apart.</b>", dim=True))
        ceil.add(body(
            "<b>Press the presets in this order — it is a six-step "
            "argument, and the last two are the interesting ones:</b><br>"
            "&nbsp;&nbsp;<b>1 · rigid baseline</b> — k is 5500, so the "
            "resonance sits at 76 Hz, far above crossover. <b>24 dB of gain "
            "margin</b> and a clean step. This is the previous page's "
            "actuator, and note it is the <i>spring's</i> stiffness doing "
            "that, not your gains.<br>"
            "&nbsp;&nbsp;<b>2 · fit a real spring</b> — k drops to 180, a "
            "spring that would actually protect someone. The resonance falls "
            "to 14 Hz. To keep a healthy margin you must back K<sub>p</sub> "
            "right off, and crossover lands at <b>3.7 Hz</b>.<br>"
            "&nbsp;&nbsp;<b>3 · push the gain</b> — the instinct that works "
            "on every rigid plant. Crossover climbs to 5.5 Hz and gain "
            "margin falls to <b>5.5 dB</b>. You have bought 1.8 Hz and spent "
            "nearly all your margin for it.<br>"
            "&nbsp;&nbsp;<b>4 · over the edge</b> — K<sub>p</sub> doubled "
            "again. Gain margin goes <b>negative</b> and the step diverges, "
            "ringing at the spring's frequency rather than at anything you "
            "chose. Note there was no warning region: 5.5 dB to −0.5 dB in "
            "one doubling.<br>"
            "&nbsp;&nbsp;<b>5 · add a D term</b> — back to the stable gain, "
            "but with K<sub>d</sub> = 2. On a rigid joint a D term is free "
            "damping. Here it <b>destroys the loop</b> — gain margin −9.9 dB "
            "— because a derivative lifts loop gain at high frequency, which "
            "is precisely where the resonance peak is waiting.<br>"
            "&nbsp;&nbsp;<b>6 · damp the spring</b> — identical gains, "
            "ζ<sub>r</sub> raised from 0.02 to 0.25. <b>Margin returns to "
            "+4.2 dB and the step settles cleanly.</b> <i>This</i> is where "
            "spring damping earns its place: not for a P loop, but the "
            "moment your controller has any high-frequency gain at all.",
            dim=True))
        self.s_cjm = slider(2, 200, 40)          # x0.001 kg m^2
        self.s_cjl = slider(2, 400, 60)          # x0.001
        self.s_ck = slider(10, 6000, 300)        # N m / rad
        self.s_czr = slider(1, 50, 5)            # x0.01  spring damping
        self.s_ckp = slider(5, 6000, 300)
        self.s_ckd = slider(0, 200, 0)           # x0.1
        self.l_cjm, self.l_cjl, self.l_ck = QLabel(), QLabel(), QLabel()
        self.l_czr, self.l_ckp, self.l_ckd = QLabel(), QLabel(), QLabel()
        ceil.add_layout(slider_row("Motor Jₘ (×0.001)", self.s_cjm,
                                   self.l_cjm))
        ceil.add_layout(slider_row("Limb Jʟ (×0.001)", self.s_cjl, self.l_cjl))
        ceil.add_layout(slider_row("Spring k (N·m/rad)", self.s_ck, self.l_ck))
        ceil.add_layout(slider_row("Spring damping ζ_r (×0.01)", self.s_czr,
                                   self.l_czr))
        ceil.add_layout(slider_row("K_p", self.s_ckp, self.l_ckp))
        ceil.add_layout(slider_row("K_d (×0.1)", self.s_ckd, self.l_ckd))
        ceil.add_layout(preset_row(
            ("1 · rigid baseline",
             lambda: self._preset_ceil(jm=40, jl=60, k=5500, zr=2, kp=300,
                                       kd=0)),
            ("2 · fit a real spring",
             lambda: self._preset_ceil(jm=40, jl=60, k=180, zr=2, kp=50,
                                       kd=0)),
            ("3 · push the gain",
             lambda: self._preset_ceil(jm=40, jl=60, k=180, zr=2, kp=100,
                                       kd=0)),
            ("4 · over the edge",
             lambda: self._preset_ceil(jm=40, jl=60, k=180, zr=2, kp=200,
                                       kd=0)),
            ("5 · add a D term",
             lambda: self._preset_ceil(jm=40, jl=60, k=180, zr=2, kp=100,
                                       kd=20)),
            ("6 · damp the spring",
             lambda: self._preset_ceil(jm=40, jl=60, k=180, zr=25, kp=100,
                                       kd=20)),
            ("reset",
             lambda: self._preset_ceil(jm=40, jl=60, k=300, zr=5, kp=100,
                                       kd=0))))
        self.st_cres = Stat("resonance f_res", "--", theme.BAD)
        self.st_cgc = Stat("your crossover", "--", theme.GOOD)
        self.st_cgm = Stat("gain margin", "--", theme.WARN)
        self.st_cbound = Stat("Bode-page bound", "--", theme.VIOLET)
        self.st_cmax = Stat("measured ceiling", "--", theme.CYAN)
        ceil.add_layout(stat_row(self.st_cres, self.st_cgc, self.st_cgm,
                                 self.st_cbound, self.st_cmax))
        self.c_ceil = MplCanvas(width=7.6, height=4.4, nrows=2, ncols=2)
        self._ceil_drawn = False
        ceil.add(self.c_ceil)
        self.t_ceil = body("", dim=True)
        ceil.add(self.t_ceil)
        self.add(ceil)
        for s in (self.s_cjm, self.s_cjl, self.s_ck, self.s_czr, self.s_ckp,
                  self.s_ckd):
            s.valueChanged.connect(self._redraw_ceiling)

        num = Card("so what do 50–100 Hz and 10–20 Hz actually mean?")
        num.add(body(
            "They are <b>closed-loop force-control bandwidths</b>: the frequency "
            "at which commanded joint torque still tracks to −3 dB. They are "
            "<b>not</b> sample rates and they are <b>not</b> sensor bandwidths."))
        num.add(body(
            (
                "A 1 kHz update rate means a command update every 1 ms. Sampling 10–20 times a desired response "
                "bandwidth is a starting rule of thumb, followed by delay and margin checks. DD force loops "
                "sometimes target tens to hundreds of Hz, while SEA examples may target tens of Hz, but these "
                "are design-specific responses. Spring stiffness and inertia set frequency scales; controller, "
                "load condition and motor limits determine the achieved response."
            )))
        num.add(body(
            (
                "A 10 Hz −3 dB bandwidth does <b>not</b> mean one torque change every 100 ms. For a first-order "
                "closed loop only, it corresponds to τ_c = 1/(2π·10) = 15.9 ms, about 35 ms 10–90% rise time and"
                " 62 ms 2% settling time. An SEA is generally higher order, so compute those response times "
                "rather than using the first-order conversion blindly. Neural reflex latency in milliseconds is "
                "also not interchangeable with a bandwidth in Hz."
            ), dim=True))
        self.add(num)

        self.add(callout(
            (
                "Force information is useful because the controller can act on it. In an SEA, output sensing or "
                "spring-deflection sensing can reveal a disturbance even if rotor motion is small. Acting on "
                "that information still requires motor authority and a stable loop. Biological tendons are also "
                "compliant series elements; biological sensing and reflex delays should not be described as an "
                "instantaneous rigid connection."
            ), "key"))

        # ---- what the spring is and is not for --------------------------------
        purpose = Card("\"is the spring protective, or are we trying to get more "
                       "torque at the joint?\"")
        purpose.add(body(
            (
                "<b>A series spring transmits torque, stores energy and can support torque "
                "sensing.</b><br><br>In static balance without other loads, motor-side transmitted torque equals"
                " spring torque. During motion, rotor acceleration means instantaneous spring torque need not "
                "equal motor torque. Releasing stored energy can increase short-duration output power or torque;"
                " the spring is not an additional source of net energy.<br><br>Its compliant path can reduce "
                "rotor participation in fast load motion. Measuring spring deflection estimates elastic torque. "
                "The costs include deflection, travel limits and added dynamic modes that must be handled by "
                "control."
            )))
        purpose.add(body(
            "<b>If you want more torque, that is the PEA on the next page</b> — "
            "spring in <i>parallel</i>, so motor and spring add. Series buys "
            "safety; parallel buys torque and efficiency. Different position in "
            "the drivetrain, completely different function.", dim=True))
        self.add(purpose)

        # ---- the stiffness trade ---------------------------------------------
        kk = Card("\"so is higher stiffness better?\" — k is the safety ⇄ speed dial")
        kk.add(body(
            "Neither higher nor lower is better. k is the one knob that sets "
            "where you sit on the trade, and it moves <b>three things at "
            "once</b>:"))
        kk.add(body(
            (
                "<table cellpadding='6'><tr><th align='left'>Raising k</th><th "
                "align='left'>Effect</th></tr><tr><td>Natural frequency f<sub>n</sub> ∝ √k (fixed "
                "inertia)</td><td><b>Better.</b> Faster reflexes, better tracking.</td></tr><tr><td>Impact "
                "protection</td><td><b>Worse.</b> J<sub>eff</sub> stays at J<sub>m</sub>+J<sub>L</sub> up to a "
                "higher frequency, so less of the impact spectrum gets filtered.</td></tr><tr><td>Force "
                "resolution</td><td><b>Worse.</b> Deflection per N·m is 1/k, so a stiff spring makes a poor "
                "sensor — the deflection disappears into encoder quantisation.</td></tr><tr><td>Energy "
                "stored</td><td><b>Less</b> at a given torque (E = τ²/2k).</td></tr></table>"
            )))
        kk.add(body(
            "<b>How it is chosen in practice:</b> pick the softest spring whose "
            "f<sub>n</sub> still clears your fastest required motion, then check "
            "that the deflection at peak torque fits the mechanism and resolves "
            "well on your encoder. Typical result for a humanoid leg: f<sub>n</sub> "
            "around 10–20 Hz, deflection of a few degrees at rated torque.",
            dim=True))
        self.add(kk)

        rw = Card("where SEAs actually are, and where they are deliberately not")
        rw.add(body(
            "<b>Used:</b><br>"
            "&nbsp;&nbsp;• <b>Agility Digit / Cassie</b> — SEA in the legs. A "
            "walking robot in warehouses among people; passive impact survival is "
            "worth more than reflex speed.<br>"
            "&nbsp;&nbsp;• <b>ANYmal (ANYdrive)</b> — SEA legs for rough-terrain "
            "quadruped work. Rocks and steps are exactly the broadband impacts a "
            "spring is good at.<br>"
            "&nbsp;&nbsp;• <b>Baxter / Sawyer</b> — the original \"safe around "
            "untrained people\" arms. SEA in every joint.<br>"
            "&nbsp;&nbsp;• <b>Powered ankle prostheses</b> — the spring doubles as "
            "the torque sensor <i>and</i> stores push-off energy, mimicking the "
            "Achilles tendon.<br><br>"
            "<b>Deliberately avoided:</b><br>"
            "&nbsp;&nbsp;• <b>MIT Cheetah</b> — running needs fast leg "
            "repositioning; a 10 Hz filter fights you.<br>"
            "&nbsp;&nbsp;• <b>1X Neo</b> — rejected SEAs explicitly for bandwidth, "
            "and recovered safety through a soft body plus proprioceptive "
            "control instead. See the case-study page.<br>"
            "&nbsp;&nbsp;• <b>Surgical and machining robots</b> — compliance is "
            "the enemy of precision."))
        self.add(rw)

        pc = Card("pros and cons, plainly")
        pc.add(body(
            (
                "<b>Pros</b><br>• <b>Mechanical low-pass filter (safety).</b> At impact frequencies the spring "
                "absorbs energy before it reaches the motor: J<sub>eff</sub> ≈ J<sub>L</sub>. Protects robot and"
                " human.<br>• <b>Force sensing for free.</b> Measure the spring's deflection and you have a "
                "torque sensor. No strain gauges needed — you only need to know how much the spring bent.<br>• "
                "<b>Energy storage.</b> Like a tendon: store energy in one phase of the gait and release it in "
                "the next.<br><br><b>Cons</b><br>• <b>Tracking tradeoff.</b> Spring modes can constrain a chosen"
                " feedback bandwidth. Motion above a natural frequency is possible; its amplitude, phase, "
                "required torque and stability must be checked.<br>• <b>Stability is harder.</b> Motor and load "
                "are separated by a spring. Motor actuation with load-angle sensing is <b>non-collocated</b>; "
                "motor-angle sensing is a different, collocated measurement. High-frequency control gains can "
                "excite structural resonances and go unstable. Controlling an SEA at 1 kHz is harder than "
                "controlling a direct drive.<br><br><b>Consider for:</b> tasks that benefit from series "
                "compliance, spring-torque sensing or elastic energy storage. Select against measured "
                "requirements; a topology or a product name does not establish safety. You sacrifice high-speed "
                "precision to gain passive shock tolerance and high-fidelity force sensing."
            )))
        self.add(pc)

        self._redraw()
        self._redraw_ceiling()
        from ..widgets.sea_walkthroughs import attach_sea_walkthroughs
        attach_sea_walkthroughs(self)
        self.finish()

    # ------------------------------------------------------------------
    def _preset_ceil(self, **kw):
        for name, sld in (("jm", self.s_cjm), ("jl", self.s_cjl),
                          ("k", self.s_ck), ("zr", self.s_czr),
                          ("kp", self.s_ckp), ("kd", self.s_ckd)):
            if name in kw:
                sld.blockSignals(True)
                sld.setValue(int(kw[name]))
                sld.blockSignals(False)
        self._redraw_ceiling()

    def _ceil_params(self):
        return (self.s_cjm.value() / 1000.0,
                self.s_cjl.value() / 1000.0,
                float(self.s_ck.value()),
                self.s_czr.value() / 100.0,
                float(self.s_ckp.value()),
                self.s_ckd.value() / 10.0)

    def _redraw_ceiling(self):
        jm, jl, k, zr, kp, kd = self._ceil_params()
        self.l_cjm.setText(f"{jm:.3f}")
        self.l_cjl.setText(f"{jl:.3f}")
        self.l_ck.setText(f"{k:.0f}")
        self.l_czr.setText(f"{zr:.2f}")
        self.l_ckp.setText(f"{kp:.0f}")
        self.l_ckd.setText(f"{kd:.1f}")

        plant = sea_plant(jm, jl, k, 0.4, zr)
        loop = pd_loop(plant, kp, kd)
        mg = margins(loop)
        f_res = sea_resonance_rad_s(k, jm, jl) / (2.0 * math.pi)
        f_gc = mg.wgc / (2.0 * math.pi) if mg.wgc else 0.0
        bound = sea_crossover_ceiling_hz(k, jm, jl, zr, 6.0)
        fmax = max_sea_crossover_hz(jm, jl, k, zr, kd)

        self.st_cres.set(f"{f_res:.1f} Hz")
        self.st_cgc.set(f"{f_gc:.2f} Hz" if f_gc else "—")
        gm = mg.gain_margin_db
        self.st_cgm.set("∞" if not math.isfinite(gm) else f"{gm:.1f} dB")
        self.st_cgm.set_color(theme.GOOD if (not math.isfinite(gm) or gm >= 6)
                              else (theme.WARN if gm > 0 else theme.BAD))
        self.st_cbound.set(f"{bound:.2f} Hz" if math.isfinite(bound) else "∞")
        self.st_cmax.set(f"{fmax:.2f} Hz" if fmax else "none")

        c = self.c_ceil
        c.clear()
        a_m, a_p, a_s, a_b = c.axes

        ws = log_freqs(max(0.05, f_res * 0.003) * 2 * math.pi,
                       f_res * 40.0 * 2 * math.pi, 420)
        _, mag, ph = bode(loop, ws)
        fs_ = [w / (2 * math.pi) for w in ws]
        a_m.semilogx(fs_, mag, color=theme.ACCENT, lw=2.0)
        a_m.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a_m.axvline(f_res, color=theme.BAD, lw=1.3, ls=":")
        if f_gc:
            a_m.axvline(f_gc, color=theme.GOOD, lw=1.3)
        a_m.set_ylim(-80, max(40, max(mag) + 6))
        a_m.set_ylabel("|L| (dB)")
        a_m.set_title("loop gain — dotted red is the spring resonance",
                      fontsize=8)
        a_p.semilogx(fs_, ph, color=theme.ACCENT, lw=2.0)
        a_p.axhline(-180, color=theme.BAD, lw=1.1, ls=":")
        a_p.axvline(f_res, color=theme.BAD, lw=1.3, ls=":")
        if f_gc:
            a_p.axvline(f_gc, color=theme.GOOD, lw=1.3)
        a_p.set_ylim(max(-560, min(ph) - 20), 20)
        a_p.set_ylabel("∠L (deg)")
        a_p.set_xlabel("frequency (Hz)")
        a_p.set_title("180° of lag arrives in one octave", fontsize=8)

        cl = loop.feedback()
        dur = min(4.0, max(0.5, 18.0 / max(f_res, 1.0)))
        t, y = step_response(cl, dur, dur / 600.0)
        stable = max(abs(v) for v in y) < 12.0
        a_s.plot(t, y, color=theme.GOOD if stable else theme.BAD, lw=2.0)
        a_s.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a_s.set_ylim(-0.6, 2.6 if stable else 12.0)
        a_s.set_xlabel("time (s)")
        a_s.set_ylabel("load angle")
        a_s.set_title("closed-loop step", fontsize=8)

        # the ceiling picture: bound, true max, and where you actually are
        names = ["Bode-page\nbound", "measured\nceiling", "you", "resonance"]
        vals = [bound if math.isfinite(bound) else 0.0, fmax, f_gc, f_res]
        cols = [theme.VIOLET, theme.CYAN, theme.GOOD, theme.BAD]
        a_b.bar(names, vals, color=cols, alpha=0.85)
        a_b.set_ylabel("Hz")
        a_b.set_title("the ceiling, three ways", fontsize=8)
        a_b.tick_params(axis="x", labelsize=7)
        for i, v in enumerate(vals):
            if v > 0:
                a_b.text(i, v, f" {v:.1f}", ha="center", va="bottom",
                         color=theme.TEXT_DIM, fontsize=7)
        # tight_layout is ~70% of a four-pane redraw and the pane geometry
        # never changes after the first one, so pay for it once
        c.refresh(layout=not self._ceil_drawn)
        self._ceil_drawn = True

        f_load = elastic_corner_hz(k, jl)
        if not stable:
            verdict = (f"<b>Unstable.</b> Gain margin is {gm:.1f} dB, so the "
                       f"loop sustains its own oscillation — and look at the "
                       f"step: it is ringing near <b>{f_res:.1f} Hz</b>, the "
                       f"<i>spring's</i> frequency, not anything you chose. "
                       f"That is the signature worth recognising on "
                       f"hardware: when a compliant joint goes unstable it "
                       f"rings at the mechanism, which is why turning the "
                       f"gain down is the only thing that helps and retuning "
                       f"K<sub>d</sub> often makes it worse.")
        elif math.isfinite(gm) and gm < 6.0:
            verdict = (f"<b>Stable but thin.</b> {gm:.1f} dB of gain margin "
                       f"is a factor of only {10**(gm/20):.1f}× — and a "
                       f"spring's k moves with temperature and fatigue while "
                       f"J<sub>L</sub> moves with every payload. This is not "
                       f"enough room to ship.")
        else:
            verdict = (f"<b>Healthy.</b> Crossover {f_gc:.2f} Hz sits "
                       f"{f_res/max(f_gc,1e-6):.1f}× below the "
                       f"{f_res:.1f} Hz resonance, with "
                       + ("infinite" if not math.isfinite(gm)
                          else f"{gm:.1f} dB of") + " gain margin.")

        if fmax > 0 and f_load > 0:
            verdict += (
                f"<br><br><b>This loop family's tested crossover limit is {fmax:.2f} Hz</b> — "
                f"the largest crossover that still holds 6 dB, found by "
                f"search rather than formula. That is "
                f"<b>{fmax/f_load:.2f} × √(k/J<sub>L</sub>)/2π</b> and "
                f"{fmax/max(f_res,1e-6):.2f} × f<sub>res</sub>, and both "
                f"ratios describe this controller and margin search. They do not "
                f"make the spring frequency identical to closed-loop bandwidth.")
        if math.isfinite(bound) and bound > 0 and fmax > 0:
            verdict += (
                f" The Bode page's bound says {bound:.2f} Hz, a factor of "
                f"{fmax/bound:.1f} lower, because on this plant the −180° "
                f"crossing happens below the resonance rather than at it. "
                f"<b>Use it as a design-stage floor, not a prediction.</b>")
        self.t_ceil.setText(verdict)

    def _vals(self):
        return (self.s_jm.value() / 1000.0,
                self.s_jl.value() / 1000.0,
                float(self.s_k.value()))

    def _redraw(self):
        jm, jl, k = self._vals()
        self.l_jm.setText(f"{jm:.3f}")
        self.l_jl.setText(f"{jl:.3f}")
        self.l_k.setText(f"{k:.0f}")

        anti = sea_antiresonance_rad_s(k, jm)
        res = sea_resonance_rad_s(k, jm, jl)
        self.st_anti.set(f"{anti:.0f} rad/s")
        self.st_res.set(f"{res:.0f} rad/s")
        self.st_hi.set(f"{jl:.3f}")
        self.st_defl.set(f"{sea_deflection_ratio(jm, k, 1.0) * 100:.2f}%")

        # ---- load-side effective inertia ---------------------------------
        c = self.canvas
        c.clear()
        ws = [10 ** (x / 40.0) for x in range(-40, 141)]
        span = jm + jl

        below = [w for w in ws if w < anti * 0.98]
        mid = [w for w in ws if anti * 1.02 < w < res * 0.995]
        above = [w for w in ws if w > res * 1.005]
        for seg, lab in ((below, "SEA — load side"), (mid, None), (above, None)):
            if seg:
                c.ax.semilogx(seg, [j_eff_sea(jm, jl, k, w) for w in seg],
                              color=theme.GOOD, lw=2.4, label=lab)
        c.ax.axhline(span, color=theme.TEXT_FAINT, lw=1.1, ls="--",
                     label="Jₘ+Jʟ  (ω→0)")
        c.ax.axhline(jl, color=theme.ACCENT, lw=1.1, ls=":",
                     label="Jʟ  (ω→∞)  ← the safety number")
        c.ax.axhline(0, color=theme.BORDER, lw=1.0)
        c.ax.axvline(anti, color=theme.BAD, lw=1.1, alpha=0.8)
        c.ax.text(anti, span * 1.35, " ω_a\n antiresonance\n √(k/Jₘ)",
                  color=theme.BAD, fontsize=7.2, va="bottom")
        c.ax.axvline(res, color=theme.VIOLET, lw=1.1, alpha=0.8)
        c.ax.text(res, -span * 1.3, " ω_r\n resonance\n J_eff = 0",
                  color=theme.VIOLET, fontsize=7.2, va="top")
        c.ax.set_xlabel("frequency the WORLD pushes the load at,  ω (rad/s)")
        c.ax.set_ylabel("J_eff  (kg·m²)")
        c.ax.set_ylim(-span * 2.0, span * 2.4)
        c.legend(loc="upper left")
        c.refresh()

        # ---- motor-side transmissibility ----------------------------------
        cb = self.canvas_bw
        cb.clear()
        wn = math.sqrt(k / jl)
        lo = [w for w in ws if w < wn * 0.97]
        hi = [w for w in ws if w > wn * 1.03]
        for seg, lab in ((lo, "θʟ / θₘ"), (hi, None)):
            if seg:
                cb.ax.loglog(seg, [sea_transmissibility(k, jl, w) for w in seg],
                             color=theme.CYAN, lw=2.4, label=lab)
        cb.ax.axhline(1.0, color=theme.TEXT_FAINT, lw=1.1, ls="--",
                      label="load follows motor 1:1")
        cb.ax.axvline(wn, color=theme.GOOD, lw=1.3)
        cb.ax.text(wn, 0.02, f"  f_n = {sea_bandwidth_hz(k, jl):.1f} Hz\n"
                             f"  = {wn:.0f} rad/s",
                   color=theme.GOOD, fontsize=7.5)
        cb.ax.set_xlabel("frequency the MOTOR is commanded at,  ω (rad/s)")
        cb.ax.set_ylabel("|θʟ / θₘ|")
        cb.ax.set_ylim(1e-2, 1e2)
        cb.legend(loc="lower left")
        cb.refresh()


# ==========================================================================
# PAGE 3 -- Parallel elastic actuator
# ==========================================================================

class PEAPage(Page):
    TITLE = "Parallel Elastic Actuators"
    SUBTITLE = ("Spring alongside the motor instead of between. Buys energy, "
                "not safety — and can make the joint feel lighter than nothing.")
    SECTION = SECTION
    NOTES = "material p.3"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "In a PEA a passive spring is added <b>next to</b> the motor. Motor "
            "and spring work together to move the same load. Crucially, motor and "
            "load are still <b>rigidly connected</b> — so unlike an SEA, a hit to "
            "the arm still goes straight into the motor's gears.", "key"))

        d = Card("derivation — one body again, plus a spring torque")
        d.add(math_label(r"\tau_{ext} = J_L\ddot\theta + J_m\ddot\theta + k\theta"))
        d.add(math_label(r"= (J_m + J_L)s^2\theta + k\theta "
                         r"= \left[(J_m+J_L)s^2 + k\right]\theta"))
        d.add(body("Divide by s²θ to read off the inertia:", dim=True))
        d.add(math_label(r"\boxed{\;\frac{\tau_{ext}}{s^2\theta} = "
                         r"J_{eff} = (J_m + J_L) + \frac{k}{s^2}\;}", 18))
        d.add(body("With s = jω:", dim=True))
        d.add(math_label(r"J_{eff}(\omega) = (J_m + J_L) - \frac{k}{\omega^2}", 16))
        self.add(d)

        r = Card("three regimes — and one of them is a trap")
        r.add(body(
            "<b>ω → ∞ &nbsp;(fast).</b> The k/ω² term goes to zero and "
            "J<sub>eff</sub> → <b>J<sub>m</sub> + J<sub>L</sub></b>. You feel the "
            "full machine, rotor included. <b>A PEA gives no impact "
            "protection.</b>"))
        r.add(callout(
            "<b>\"But if I shake it fast the spring can't bend, so motor and "
            "spring are locked — shouldn't the link not move at all? And why "
            "isn't it J<sub>L</sub>?\"</b><br><br>"
            "Two things to separate here.<br><br>"
            "<b>First: it is NOT J<sub>L</sub>. It is J<sub>m</sub> + "
            "J<sub>L</sub>.</b> If you were expecting J<sub>L</sub>, you are "
            "thinking of the SEA. That drop to J<sub>L</sub> is the <i>one thing</i> "
            "a series spring does and a parallel spring cannot. In a PEA the "
            "motor is <b>rigidly bolted to the joint</b> — there is no compliance "
            "in the force path at all, so the rotor is always along for the "
            "ride.<br><br>"
            "<b>Second: the spring is not \"locked\" or acting as a stiff rod.</b> "
            "It is deflecting by exactly θ, the same as always — it is in "
            "parallel, so it stretches by whatever the joint moves. Its torque "
            "kθ is perfectly real. It is just <b>negligible in comparison</b>: "
            "the inertial torque grows as Jω²θ while the spring torque stays at "
            "kθ, so by ω = 10ω<sub>r</sub> the spring contributes 1% of the "
            "total. It is not overpowered — it is out-scaled.<br><br>"
            "Contrast with the SEA, where at high ω the spring is doing the "
            "<i>opposite</i>: taking essentially all the relative motion and "
            "thereby disconnecting the rotor. Series compliance decouples masses. "
            "Parallel compliance never can.", "warn"))
        r.add(body(
            "<b>ω = √(k/(J<sub>m</sub>+J<sub>L</sub>)) &nbsp;(resonance).</b> "
            "J<sub>eff</sub> = 0 exactly. The spring's restoring torque and the "
            "inertial torque cancel, so a tiny applied torque produces large "
            "motion. Bounce the joint at its natural frequency and it costs "
            "almost nothing — the same reason a child on a swing needs only small "
            "pushes."))
        r.add(body(
            "<b>ω → 0 &nbsp;(slow).</b> J<sub>eff</sub> goes large and "
            "<b>negative</b>. Read this one carefully."))
        r.add(callout(
            "<b>What \"negative effective inertia\" does and does not mean.</b><br><br>"
            "It does <b>not</b> mean the joint has negative mass, or that it "
            "spontaneously accelerates, or that you get energy for free. I "
            "over-stated this in an earlier version of this page and it is worth "
            "correcting plainly.<br><br>"
            "Dividing every torque by s²θ forces <i>everything</i> into inertia "
            "units — but a spring's impedance carries the opposite sign to a "
            "mass's, because a spring's force is in phase with displacement while "
            "a mass's is in phase with acceleration (180° apart). So a negative "
            "number here says exactly one thing:<br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>Below resonance, this joint feels like a "
            "SPRING, not like a MASS.</b><br><br>"
            "Push it slowly and what pushes back is stiffness. Which is useful "
            "and real — if that spring was sized against gravity, its stiffness "
            "is holding the limb up so the motor does not have to. But the honest "
            "statement is about <b>torque</b>, not inertia, which is why the "
            "gravity-compensation section below is the one that actually "
            "matters.", "bad"))
        self.add(r)

        # ---- interactive 1: frequency ---------------------------------------
        i = Card("effective inertia vs frequency")
        self.s_jm = slider(1, 200, 40)
        self.s_jl = slider(1, 200, 60)
        self.s_k = slider(5, 2000, 200)
        self.l_jm, self.l_jl, self.l_k = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("Motor  Jₘ", self.s_jm, self.l_jm))
        i.add_layout(slider_row("Limb  Jʟ", self.s_jl, self.l_jl))
        i.add_layout(slider_row("Spring  k  (N·m/rad)", self.s_k, self.l_k))

        self.st_res = Stat("J_eff = 0 at", "--", theme.VIOLET)
        self.st_hi = Stat("J_eff at impact", "--", theme.BAD)
        i.add_layout(stat_row(self.st_res, self.st_hi))

        self.canvas = MplCanvas(width=7.4, height=3.0)
        i.add(self.canvas)
        self.add(i)

        for s in (self.s_jm, self.s_jl, self.s_k):
            s.valueChanged.connect(self._redraw)

        # ==================================================================
        # the same spring, the other side of the motor
        # ==================================================================
        self.add(hline())
        self.add(title("The same spring, the other side of the motor — and "
                       "why its frequency is a FLOOR here, not a ceiling"))

        ask = Card("the question the previous page leaves you holding")
        ask.add(body(
            "The SEA page ended with a hard number: a series spring caps your "
            "crossover at about <b>0.6 × (1/2π)√(k/J<sub>L</sub>)</b>, and no "
            "controller moves it. The obvious next question is whether a "
            "parallel spring costs you the same thing — it is, after all, the "
            "same spring with the same stiffness and the same natural "
            "frequency.<br><br>"
            "<b>It does not. It does the opposite.</b> And the reason is one "
            "line of algebra."))
        ask.add(math_label(r"\text{SEA:}\;\; \frac{\theta_L}{\tau} = "
                           r"\frac{k}{J_mJ_Ls^4 + \dots} "
                           r"\qquad\qquad "
                           r"\text{PEA:}\;\; \frac{\theta}{\tau} = "
                           r"\frac{1}{(J_m{+}J_L)s^2 + bs + k}", 16))
        ask.add(body(
            "The series spring put a <b>fourth-order</b> plant in your loop, "
            "with a lightly damped pole pair sitting in the middle of it. The "
            "parallel spring left the order exactly where it was — <b>still "
            "two poles</b> — and simply added <b>+k</b> to the stiffness term "
            "that was already there."))
        ask.add(callout(
            "<b>Now close a proportional loop round each and read where the "
            "spring ends up.</b><br><br>"
            "For the PEA, the closed-loop denominator is "
            "(J<sub>m</sub>+J<sub>L</sub>)s² + (b+K<sub>d</sub>)s + "
            "<b>(k + K<sub>p</sub>)</b>. The spring's stiffness lands in the "
            "<i>same slot</i> as your proportional gain — they are added "
            "together, and the closed loop cannot tell them apart:", "key"))
        ask.add(math_label(r"\omega_n^{PEA} = \sqrt{\frac{k + K_p}"
                           r"{J_m + J_L}}", 18))
        ask.add(body(
            (
                "<b>A parallel spring adds physical stiffness to the same denominator term as K<sub>p</sub>.</b>"
                " At K<sub>p</sub> = 0 its passive natural frequency is √(k/(J<sub>m</sub>+J<sub>L</sub>)) in "
                "rad/s; divide by 2π for Hz. This is not a tracking bandwidth with the controller switched "
                "off.<br><br>At fixed damping, raising k also changes ζ. The actual closed-loop −3 dB bandwidth "
                "and settling time must be calculated from the full response. The spring stores energy and "
                "biases the equilibrium; it does not provide arbitrary commanded torque for free."
            ), dim=True))
        ask.add(callout(
            "<b>One sentence, and it is the one to remember out of both "
            "pages.</b><br><br>"
            "<b>A series spring is in the force path, so it filters what the "
            "motor can do — it is a lag. A parallel spring is beside the "
            "force path, so it adds to what the motor does — it is a "
            "gain.</b><br><br>"
            "Same component, same stiffness, same stored energy, opposite "
            "sign of consequence, decided entirely by which side of the load "
            "it is bolted to. Everything else on these two pages is "
            "bookkeeping on that sentence.", "good"))
        self.add(ask)

        cmp_ = Card("both loops, same spring, same gains — side by side")
        cmp_.add(body(
            (
                "Identical J<sub>m</sub>, J<sub>L</sub>, k and gains fed to both topologies. Top row is the loop"
                " gain of each; bottom left is the two closed-loop steps; bottom right compares the bandwidths "
                "that result.<br><br><b>The three things to watch as you drag k "
                "upward:</b><br>&nbsp;&nbsp;<b>1.</b> The <b>SEA</b> curve grows a resonant peak and its gain "
                "margin is finite and falling. The <b>PEA</b> curve has no peak and <b>no −180° crossing in this"
                " ideal delay-free model</b>, so its gain margin stays at ∞ for every gain you can "
                "type.<br>&nbsp;&nbsp;<b>2.</b> The PEA bandwidth <b>rises</b> with k, because k is adding to "
                "K<sub>p</sub>. The SEA bandwidth rises only as √k and stays pinned below its "
                "ceiling.<br>&nbsp;&nbsp;<b>3.</b> Set <b>K<sub>p</sub> = 5</b>, essentially no controller. The "
                "PEA joint is still <b>fast and stiff</b> — ω<sub>n</sub> = √(k/(J<sub>m</sub>+J<sub>L</sub>)) "
                "with the controller switched off — while the SEA goes limp. <b>That is the parallel spring "
                "holding the joint up for free.</b><br><br><b>And then read the steady-state error stat, because"
                " that is the bill.</b> A parallel spring pulls back against your command, so a proportional "
                "loop settles at K<sub>p</sub>/(k+K<sub>p</sub>) of where you asked — at K<sub>p</sub> = 5 "
                "against k = 3000 that is a <b>99.8% error</b>. The joint is stiff, fast and in the wrong place."
                " Fixing it needs an integrator, or a feedforward torque that cancels the spring — which is "
                "precisely the gravity-compensation section below.<br><br><b>So the steps are drawn scaled to "
                "their own final values</b>, because the honest comparison is of <i>shape</i> — how fast, how "
                "damped — with the offset reported separately rather than hidden inside a curve that never "
                "leaves zero. The SEA, by contrast, has a pole at the origin and therefore <b>no steady-state "
                "error at all</b>: slower, but it does arrive."
            ),
            dim=True))
        self.s_pjm = slider(2, 200, 40)
        self.s_pjl = slider(2, 400, 60)
        self.s_pk = slider(0, 6000, 600)
        self.s_pzr = slider(1, 50, 5)
        self.s_pkp = slider(0, 4000, 300)
        self.s_pkd = slider(0, 200, 0)
        self.l_pjm, self.l_pjl, self.l_pk = QLabel(), QLabel(), QLabel()
        self.l_pzr, self.l_pkp, self.l_pkd = QLabel(), QLabel(), QLabel()
        cmp_.add_layout(slider_row("Motor Jₘ (×0.001)", self.s_pjm,
                                   self.l_pjm))
        cmp_.add_layout(slider_row("Limb Jʟ (×0.001)", self.s_pjl, self.l_pjl))
        cmp_.add_layout(slider_row("Spring k (N·m/rad)", self.s_pk, self.l_pk))
        cmp_.add_layout(slider_row("Spring damping ζ_r (×0.01)", self.s_pzr,
                                   self.l_pzr))
        cmp_.add_layout(slider_row("K_p", self.s_pkp, self.l_pkp))
        cmp_.add_layout(slider_row("K_d (×0.1)", self.s_pkd, self.l_pkd))
        cmp_.add_layout(preset_row(
            ("no spring at all",
             lambda: self._preset_pea(k=0, kp=300, kd=0)),
            ("soft spring — SEA dies",
             lambda: self._preset_pea(k=120, kp=300, kd=0)),
            ("soft spring — SEA detuned",
             lambda: self._preset_pea(k=120, kp=40, kd=0)),
            ("stiff spring",
             lambda: self._preset_pea(k=3000, kp=300, kd=0)),
            ("switch the controller off",
             lambda: self._preset_pea(k=3000, kp=5, kd=0)),
            ("reset",
             lambda: self._preset_pea(jm=40, jl=60, k=600, zr=5, kp=300,
                                      kd=0))))
        self.st_pgmS = Stat("SEA gain margin", "--", theme.BAD)
        self.st_pgmP = Stat("PEA gain margin", "--", theme.GOOD)
        self.st_pbwS = Stat("SEA bandwidth", "--", theme.WARN)
        self.st_pbwP = Stat("PEA bandwidth", "--", theme.VIOLET)
        self.st_ppass = Stat("PEA with K_p = 0", "--", theme.CYAN)
        self.st_psse = Stat("PEA steady-state error", "--", theme.BAD)
        cmp_.add_layout(stat_row(self.st_pgmS, self.st_pgmP, self.st_pbwS,
                                 self.st_pbwP, self.st_ppass, self.st_psse))
        self.c_cmp = MplCanvas(width=7.6, height=4.4, nrows=2, ncols=2)
        self._cmp_drawn = False
        cmp_.add(self.c_cmp)
        self.t_cmp = body("", dim=True)
        cmp_.add(self.t_cmp)
        self.add(cmp_)
        for s in (self.s_pjm, self.s_pjl, self.s_pk, self.s_pzr, self.s_pkp,
                  self.s_pkd):
            s.valueChanged.connect(self._redraw_cmp)

        # ---- gravity compensation ------------------------------------------
        self.add(hline())
        self.add(title("Why a PEA exists: gravity compensation"))

        g = Card("the torque balance")
        g.add(body(
            "Picture a knee holding up a leg. Three torques act on the joint:"))
        g.add(body(
            "&nbsp;&nbsp;<b>τ<sub>g</sub></b> — gravity, pulling the leg down<br>"
            "&nbsp;&nbsp;<b>τ<sub>s</sub></b> — the spring, pushing it up<br>"
            "&nbsp;&nbsp;<b>τ<sub>m</sub></b> — the motor's effort to hold position"))
        g.add(math_label(r"\tau_m + \tau_s(\theta) = \tau_g(\theta)"))
        g.add(body("Gravity compensation means the motor does nothing "
                   "(τ<sub>m</sub> = 0), which happens when", dim=True))
        g.add(math_label(r"\tau_s(\theta) = \tau_g(\theta)"))
        g.add(body("Write both out — a straight line trying to match a sine:",
                   dim=True))
        g.add(math_label(r"\tau_g = m\,g\,L\sin\theta \qquad "
                         r"\tau_s = k\,(\theta_0 - \theta)"))
        g.add(math_label(r"k\,(\theta_0 - \theta) \approx m\,g\,L\,\sin\theta", 16))
        self.add(g)

        i2 = Card("tune the spring — what you are minimising, and why you cannot "
                  "win everywhere")
        i2.add(body(
            "<b>The objective:</b> <i>minimise |τ<sub>m</sub>| — the green curve — "
            "over the range of angles the robot actually spends its time in.</b> "
            "Nothing else. Not peak torque, not stiffness: <b>motor effort while "
            "holding a pose</b>, because that is what turns into heat and flat "
            "batteries."))
        i2.add(body(
            "<b>What you may change:</b> the spring stiffness k and its rest "
            "angle θ₀ — those are your design freedoms. The limb mass slider is "
            "there to show you that a spring tuned for one payload is "
            "<b>mistuned for another</b>; gravity is not yours to choose.<br><br>"
            "<b>Why you cannot zero it everywhere:</b> gravity torque goes as "
            "<b>sin θ</b> and a linear spring goes as <b>θ₀ − θ</b>. A straight "
            "line cannot match a sine. It can cross it at <b>two angles at most</b>, "
            "and that is your entire budget.<br><br>"
            "<b>So the real design question is: which pose do you want free?</b> "
            "Standing? Mid-stance? Arms-forward-holding-a-box? Put your two "
            "crossings there. Everywhere else the motor pays — and on the far "
            "side, it pays <i>double</i>, because it is now fighting the spring "
            "as well as gravity."))
        i2.add(body(
            "Try it: set θ₀ ≈ 55° and watch the green curve sit near zero across "
            "the mid-range. Then drag the limb mass and watch that carefully "
            "tuned cancellation fall apart. That is a robot picking up an "
            "unexpected payload.", dim=True))
        self.s_k2 = slider(1, 300, 90)
        self.s_th0 = slider(-90, 90, 55)
        self.s_mass = slider(1, 200, 60)
        self.l_k2, self.l_th0, self.l_mass = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("Spring  k", self.s_k2, self.l_k2))
        i2.add_layout(slider_row("Rest angle  θ₀  (°)", self.s_th0, self.l_th0))
        i2.add_layout(slider_row("Limb mass  (×0.5 kg)", self.s_mass, self.l_mass))
        self.canvas2 = MplCanvas(width=7.4, height=3.0)
        i2.add(self.canvas2)
        self.add(i2)

        for s in (self.s_k2, self.s_th0, self.s_mass):
            s.valueChanged.connect(self._redraw_grav)

        self._redraw()
        self._redraw_grav()

        pc = Card("pros and cons")
        pc.add(body(
            "<b>Pros</b><br>"
            "• <b>Gravity compensation.</b> Tune the spring to hold the robot's "
            "weight and the motor uses <b>zero power</b> to stand still.<br>"
            "• <b>High peak torque.</b> Motor and spring pulling together beat "
            "the motor alone.<br>"
            "• <b>Efficiency.</b> Excellent for cyclic tasks — the bounce of a "
            "bipedal run.<br><br>"
            "<b>Cons</b><br>"
            "• <b>No impact protection.</b> The motor is still rigidly connected "
            "to the joint. A hit goes straight to the gears.<br>"
            "• <b>Asymmetric effort.</b> A spring that helps you <i>stand up</i> "
            "actively <b>fights</b> you when you <i>squat down</i>. Standing: "
            "gravity pulls down, spring pulls up, they help each other, "
            "τ<sub>m</sub> is tiny. Squatting: gravity still pulls down, but now "
            "the spring <i>also</i> pulls up — the motor must push against the "
            "spring to bend the joint.<br><br>"
            "A PEA tunes the robot to be very efficient at <b>one specific "
            "task</b> at the cost of making other movements harder."))
        self.add(pc)

        self.add(callout(
            "<b>SEA vs PEA in one line each.</b><br><br>"
            "<b>SEA</b> — motor → spring → load. Primary benefit: <b>safety and "
            "impacts</b>. It <i>decouples</i> J<sub>m</sub> at high "
            "frequencies.<br>"
            "<b>PEA</b> — motor ∥ spring → load. Primary benefit: <b>energy "
            "efficiency</b>. It <i>subtracts</i> inertia at low frequencies "
            "(gravity comp).<br><br>"
            "They are not competitors — a real humanoid often wants SEA in the "
            "ankle for balance and impact, PEA in the knee to hold up the torso "
            "without draining the battery.", "good"))

        self._redraw_cmp()
        self.finish()

    # ------------------------------------------------------------------
    def _preset_pea(self, **kw):
        for name, sld in (("jm", self.s_pjm), ("jl", self.s_pjl),
                          ("k", self.s_pk), ("zr", self.s_pzr),
                          ("kp", self.s_pkp), ("kd", self.s_pkd)):
            if name in kw:
                sld.blockSignals(True)
                sld.setValue(int(kw[name]))
                sld.blockSignals(False)
        self._redraw_cmp()

    def _redraw_cmp(self):
        """
        The same spring in both topologies, with the same gains, so the only
        difference on screen is WHERE it is bolted.
        """
        jm = self.s_pjm.value() / 1000.0
        jl = self.s_pjl.value() / 1000.0
        k = float(self.s_pk.value())
        zr = self.s_pzr.value() / 100.0
        kp = float(self.s_pkp.value())
        kd = self.s_pkd.value() / 10.0
        self.l_pjm.setText(f"{jm:.3f}")
        self.l_pjl.setText(f"{jl:.3f}")
        self.l_pk.setText(f"{k:.0f}")
        self.l_pzr.setText(f"{zr:.2f}")
        self.l_pkp.setText(f"{kp:.0f}")
        self.l_pkd.setText(f"{kd:.1f}")

        l_pea = pd_loop(pea_plant(jm, jl, k), kp, kd)
        t_pea = l_pea.feedback()
        bw_pea = closed_loop_bw_hz(t_pea)
        mg_pea = margins(l_pea, 1e-2, 1e5, 600)

        sea_ok = True
        if k > 0:
            l_sea = pd_loop(sea_plant(jm, jl, k, 0.4, zr), kp, kd)
            t_sea = l_sea.feedback()
            # a -3 dB point on a diverging closed loop is a meaningless
            # number, so check before quoting one
            sea_ok = is_stable(t_sea.den)
            bw_sea = closed_loop_bw_hz(t_sea) if sea_ok else 0.0
            mg_sea = margins(l_sea, 1e-2, 1e5, 600)
        else:
            l_sea = t_sea = None
            bw_sea, mg_sea = 0.0, None

        # the whole point: a parallel spring alone, controller switched off
        passive = closed_loop_bw_hz(pd_loop(pea_plant(jm, jl, k), 0.0,
                                            0.0).feedback()) if k > 0 else 0.0
        if k > 0:
            passive = elastic_corner_hz(k, jm + jl)

        gm_s = mg_sea.gain_margin_db if mg_sea else float("nan")
        gm_p = mg_pea.gain_margin_db
        self.st_pgmS.set("—" if k <= 0 else
                         ("∞" if not math.isfinite(gm_s) else f"{gm_s:.1f} dB"))
        self.st_pgmS.set_color(theme.GOOD if (k <= 0 or not math.isfinite(gm_s)
                                              or gm_s >= 6) else theme.BAD)
        self.st_pgmP.set("∞" if not math.isfinite(gm_p) else f"{gm_p:.1f} dB")
        self.st_pgmP.set_color(theme.GOOD if (not math.isfinite(gm_p)
                                              or gm_p >= 6) else theme.BAD)
        self.st_pbwS.set("—" if k <= 0 else
                         ("UNSTABLE" if not sea_ok else f"{bw_sea:.2f} Hz"))
        self.st_pbwS.set_color(theme.BAD if (k > 0 and not sea_ok)
                               else theme.WARN)
        self.st_pbwP.set(f"{bw_pea:.2f} Hz")
        self.st_ppass.set("no spring" if k <= 0 else f"{passive:.2f} Hz")
        # the parallel spring's bill: it pulls back against the command, so
        # a P loop cannot hold a setpoint without an offset
        dc_pea = abs(t_pea.response(1e-6))
        sse = max(0.0, 1.0 - dc_pea)
        self.st_psse.set("no loop" if dc_pea <= 1e-9 else f"{sse*100:.1f}%")
        self.st_psse.set_color(theme.TEXT_DIM if dc_pea <= 1e-9 else
                               (theme.GOOD if sse < 0.1 else
                                (theme.WARN if sse < 0.5 else theme.BAD)))

        c = self.c_cmp
        c.clear()
        a_m, a_p, a_s, a_b = c.axes
        ref = max(bw_pea, bw_sea, passive, 1.0)
        ws = log_freqs(0.02 * ref * 2 * math.pi, 300.0 * ref * 2 * math.pi, 420)
        fs_ = [w / (2 * math.pi) for w in ws]

        _, mp_, pp_ = bode(l_pea, ws)
        a_m.semilogx(fs_, mp_, color=theme.VIOLET, lw=2.0, label="PEA")
        a_p.semilogx(fs_, pp_, color=theme.VIOLET, lw=2.0)
        if l_sea is not None:
            _, ms_, ps_ = bode(l_sea, ws)
            a_m.semilogx(fs_, ms_, color=theme.WARN, lw=2.0, label="SEA")
            a_p.semilogx(fs_, ps_, color=theme.WARN, lw=2.0)
        a_m.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a_m.set_ylim(-90, 70)
        a_m.set_ylabel("|L| (dB)")
        a_m.set_title("loop gain — same spring, same gains", fontsize=8)
        c.legend(a_m, loc="lower left")
        a_p.axhline(-180, color=theme.BAD, lw=1.1, ls=":")
        a_p.set_ylim(-560, 20)
        a_p.set_ylabel("∠L (deg)")
        a_p.set_xlabel("frequency (Hz)")
        a_p.set_title("PEA never reaches −180°; SEA sails past it",
                      fontsize=8)

        # Normalise each step by its own DC gain. Without this the PEA looks
        # broken rather than offset: a parallel spring pulls back against the
        # command, so its DC gain is Kp/(k+Kp) and the raw curve barely
        # leaves zero. The SHAPE is what is being compared here; the offset
        # is reported separately, because it is a real cost and not a
        # plotting artefact.
        dur = min(3.0, max(0.25, 12.0 / max(ref, 1.0)))
        dc_p = abs(t_pea.response(1e-6))
        t1, y1 = step_response(t_pea, dur, dur / 600.0)
        # Kp = 0 with no spring is a loop with no gain at all: there is no
        # final value to scale by, so plot it raw rather than dividing by it
        if dc_p <= 1e-9:
            pea_lbl, pea_y = "PEA (no loop gain)", list(y1)
        elif dc_p < 0.95:
            pea_lbl, pea_y = f"PEA (×{1/dc_p:.0f})", [v / dc_p for v in y1]
        else:
            pea_lbl, pea_y = "PEA", [v / dc_p for v in y1]
        a_s.plot(t1, pea_y, color=theme.VIOLET, lw=2.0, label=pea_lbl)
        ymax = 2.2
        if t_sea is not None and sea_ok:
            dc_s = abs(t_sea.response(1e-6))
            t2, y2 = step_response(t_sea, dur, dur / 600.0)
            ys = [v / dc_s if dc_s > 1e-9 else 0.0 for v in y2]
            a_s.plot(t2, ys, color=theme.WARN, lw=2.0, label="SEA")
            ymax = max(2.2, min(6.0, max(abs(v) for v in ys) * 1.1))
        a_s.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a_s.set_ylim(-0.4, ymax)
        a_s.set_xlabel("time (s)")
        a_s.set_ylabel("angle ÷ its own final value")
        a_s.set_title("step SHAPE (each scaled to its own DC gain)",
                      fontsize=8)
        c.legend(a_s, loc="lower right")

        names = ["SEA", "PEA", "PEA,\nK_p = 0"]
        vals = [bw_sea, bw_pea, passive]
        a_b.bar(names, vals, color=[theme.WARN, theme.VIOLET, theme.CYAN],
                alpha=0.85)
        for idx, v in enumerate(vals):
            if v > 0:
                a_b.text(idx, v, f" {v:.1f}", ha="center", va="bottom",
                         color=theme.TEXT_DIM, fontsize=7)
        a_b.set_ylabel("closed-loop −3 dB (Hz)")
        a_b.set_title("bandwidth that results", fontsize=8)
        a_b.tick_params(axis="x", labelsize=7)
        c.refresh(layout=not self._cmp_drawn)
        self._cmp_drawn = True

        if k <= 0:
            self.t_cmp.setText(
                "<b>k = 0 — there is no spring, so both topologies are the "
                "same rigid joint.</b> This is the baseline: everything "
                "below is what happens when you add the identical spring in "
                "the two possible places.")
        elif not sea_ok:
            self.t_cmp.setText(
                f"<b>At these gains the SEA loop is unstable and the PEA "
                f"loop is not — with the identical spring.</b> The SEA's "
                f"gain margin is {gm_s:.1f} dB; the PEA's is infinite, "
                f"because a parallel spring adds no order and no phase, so "
                f"its loop never reaches −180° to begin with.<br><br>"
                f"There is no SEA bandwidth to quote here: a −3 dB point on "
                f"a diverging response is not a number. Back K<sub>p</sub> "
                f"off until the SEA is stable again and compare then — you "
                f"will find you had to give up most of the gain that the PEA "
                f"is still happily using.")
        else:
            ratio = bw_pea / bw_sea if bw_sea > 0 else float("inf")
            self.t_cmp.setText(
                f"<b>Same spring, k = {k:.0f}. SEA bandwidth "
                f"{bw_sea:.2f} Hz, PEA bandwidth {bw_pea:.2f} Hz — a factor "
                f"of {ratio:.1f}.</b><br><br>"
                f"The PEA's gain margin is "
                + ("<b>infinite</b>, because its loop phase never reaches "
                   "−180° at all" if not math.isfinite(gm_p)
                   else f"{gm_p:.1f} dB")
                + (f", while the SEA's is {gm_s:.1f} dB"
                   if math.isfinite(gm_s) else ", while the SEA's is ∞")
                + f". And with the controller switched off entirely the PEA "
                f"still has a passive natural frequency of <b>{passive:.2f} Hz</b>. "
                f"That is a spring–inertia mode, not a commanded tracking bandwidth "
                f"with the controller off."
                f"<br><br><b>The parallel spring's bill: "
                f"{sse*100:.1f}% steady-state error.</b> It pulls back "
                f"against the command, so this P loop settles at "
                f"K<sub>p</sub>/(k+K<sub>p</sub>) of the setpoint. The SEA "
                f"has none — its plant contains an integrator. <b>Parallel "
                f"buys you speed and stiffness and charges you position "
                f"accuracy; series buys you protection and charges you "
                f"bandwidth.</b>")

    def _redraw(self):
        jm = self.s_jm.value() / 1000.0
        jl = self.s_jl.value() / 1000.0
        k = float(self.s_k.value())
        self.l_jm.setText(f"{jm:.3f}")
        self.l_jl.setText(f"{jl:.3f}")
        self.l_k.setText(f"{k:.0f}")

        wr = pea_resonance_rad_s(k, jm, jl)
        self.st_res.set(f"{wr:.0f} rad/s")
        self.st_hi.set(f"{jm + jl:.3f}")

        c = self.canvas
        c.clear()
        ws = [10 ** (x / 40.0) for x in range(-20, 141)]
        vals = [j_eff_pea(jm, jl, k, w) for w in ws]
        c.ax.semilogx(ws, vals, color=theme.VIOLET, lw=2.4, label="PEA")
        c.ax.axhline(jm + jl, color=theme.TEXT_FAINT, lw=1.1, ls="--",
                     label="Jₘ+Jʟ  (ω→∞)")
        c.ax.axhline(0, color=theme.BORDER, lw=1.0)
        c.ax.axvline(wr, color=theme.GOOD, lw=1.0, alpha=0.8)
        c.ax.text(wr, (jm + jl) * 0.55, "  J_eff = 0", color=theme.GOOD,
                  fontsize=8)
        c.ax.fill_between(ws, vals, 0, where=[v < 0 for v in vals],
                          color=theme.BAD, alpha=0.16)
        c.ax.text(ws[6], -(jm + jl) * 1.2, "negative effective inertia\n"
                  "the spring pushes for you",
                  color=theme.BAD, fontsize=7.5)
        c.ax.set_xlabel("interaction frequency ω  (rad/s)")
        c.ax.set_ylabel("J_eff  (kg·m²)")
        c.ax.set_ylim(-(jm + jl) * 2.2, (jm + jl) * 1.7)
        c.legend(loc="lower right")
        c.refresh()

    def _redraw_grav(self):
        k = float(self.s_k2.value())
        th0 = math.radians(self.s_th0.value())
        mass = self.s_mass.value() * 0.5
        length = 0.4
        self.l_k2.setText(f"{k:.0f}")
        self.l_th0.setText(f"{self.s_th0.value()}°")
        self.l_mass.setText(f"{mass:.1f} kg")

        c = self.canvas2
        c.clear()
        degs = list(range(0, 91))
        ths = [math.radians(d) for d in degs]
        tg = [gravity_torque(mass, length, t) for t in ths]
        ts = [spring_torque(k, t, th0) for t in ths]
        tm = [motor_torque_pea(mass, length, k, t, th0) for t in ths]
        c.ax.plot(degs, tg, color=theme.WARN, lw=2.0, label="τ_g  gravity")
        c.ax.plot(degs, ts, color=theme.ACCENT, lw=2.0, label="τ_s  spring")
        c.ax.plot(degs, tm, color=theme.GOOD, lw=2.6, label="τ_m  motor must supply")
        c.ax.axhline(0, color=theme.BORDER, lw=1.0)
        c.ax.set_xlabel("joint angle from vertical  (°)")
        c.ax.set_ylabel("torque  (N·m)")
        c.legend(loc="upper left")
        c.refresh()


# ==========================================================================
# PAGE 4 -- Head to head
# ==========================================================================

class ActuatorCompare(Page):
    TITLE = "DD vs SEA vs PEA"
    SUBTITLE = ("The three curves on one axis: output torque, speed, effective "
                "inertia, bandwidth and responsiveness.")
    SECTION = SECTION
    NOTES = "material p.2-3"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(body(
            "Everything so far, superimposed. Same J<sub>m</sub>, same "
            "J<sub>L</sub>, same k — three different places to put the spring."))

        i = Card("all three at once")
        self.s_jm = slider(1, 200, 40)
        self.s_jl = slider(1, 200, 60)
        self.s_k = slider(5, 2000, 300)
        self.l_jm, self.l_jl, self.l_k = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("Motor  Jₘ", self.s_jm, self.l_jm))
        i.add_layout(slider_row("Limb  Jʟ", self.s_jl, self.l_jl))
        i.add_layout(slider_row("Spring  k", self.s_k, self.l_k))

        self.chk = {}
        row = QHBoxLayout()
        row.setSpacing(16)
        for key, colour in (("direct", theme.ACCENT), ("sea", theme.GOOD),
                            ("pea", theme.VIOLET)):
            cb = QCheckBox(TOPOLOGY_NAMES[key])
            cb.setChecked(True)
            cb.setStyleSheet(f"color:{colour};")
            cb.stateChanged.connect(self._redraw)
            self.chk[key] = cb
            row.addWidget(cb)
        row.addStretch(1)
        i.add_layout(row)

        self.canvas = MplCanvas(width=7.6, height=3.4)
        i.add(self.canvas)
        i.add(body(
            "Read the plot as a story about <b>who you are protecting from "
            "what</b>. Right-hand side = impacts. The SEA curve drops to the bare "
            "limb there; the other two do not. Left-hand side = slow "
            "interaction. The PEA curve dives negative there; the other two do "
            "not.", dim=True))
        self.add(i)

        for s in (self.s_jm, self.s_jl, self.s_k):
            s.valueChanged.connect(self._redraw)
        self._redraw()

        # ---- the table ------------------------------------------------------
        t = Card("the comparison, column by column")
        tbl = QTableWidget(7, 4)
        tbl.setHorizontalHeaderLabels(
            ["", "Direct Drive / QDD", "Series Elastic", "Parallel Elastic"])
        rows = [
            ("Effective inertia",
             "Jₘ + Jʟ, at every frequency",
             "Jₘ+Jʟ slow → Jʟ at impact",
             "Jₘ+Jʟ fast → negative when slow"),
            ("Output torque",
             "Low density: needs a big heavy motor to get torque without gears",
             "Same as the motor can give; spring adds nothing to peak",
             "Motor + spring together → higher peak torque than motor alone"),
            ("Output velocity",
             "Fast, unfiltered; limited only by the motor",
             "Limited above fₙ — the spring absorbs the motion instead",
             "Fast; spring does not restrict motion, only biases it"),
            ("Bandwidth",
             "50–100 Hz and up. No spring slop, reacts instantly",
             "10–20 Hz. Physical limit τ ≥ 1/ωₙ, not a software one",
             "High — no series compliance in the force path"),
            ("Responsiveness",
             "Crisp. Push it and the motor spins immediately",
             "Lagged. Fast disturbance deflects the spring before the motor "
             "knows",
             "Crisp, but biased: the spring is always pulling one way"),
            ((
                 "Transparency /\nbackdrivability"
             ),
             "Excellent. No friction or spring hiding the external force",
             "Good at low ω; the spring masks fast events by design",
             "Good, but the spring torque must be modelled out"),
            ("Best for",
             "Small quadrupeds (MIT Cheetah): high-speed leg swinging beats "
             "carrying heavy loads",
             "Humanoids among people (1X Neo, Agility Digit): safety is "
             "requirement #1",
             "Heavy-duty bipeds and prosthetics: battery life and weight "
             "carrying"),
        ]
        for r, cells in enumerate(rows):
            for c, v in enumerate(cells):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemIsEnabled)
                tbl.setItem(r, c, it)
        tbl.verticalHeader().setVisible(False)
        tbl.setWordWrap(True)
        tbl.resizeRowsToContents()
        tbl.setColumnWidth(0, 150)
        for c in (1, 2, 3):
            tbl.setColumnWidth(c, 260)
        tbl.setMinimumHeight(430)
        t.add(tbl)
        self.add(t)

        # ==================================================================
        # where each topology's bandwidth actually comes from -- derived,
        # with the same PD loop closed around all three
        # ==================================================================
        self.add(hline())
        self.add(title("Where does each bandwidth number come from? — close "
                       "the same loop around all three and look"))

        bw = Card("the three plants, written out, so the ceilings are visible "
                  "before any gain is chosen")
        bw.add(body(
            "The table above asserts \"50–100 Hz, 10–20 Hz, high\". Those "
            "numbers are not conventions — each one falls out of the plant's "
            "own equation, and the widget below closes an identical PD position "
            "loop around all three so you can watch which ceiling stops "
            "you."))
        bw.add(math_label(r"P_{DD}(s) = \frac{1}{(J_m+J_L)s^2 + bs}"
                          r"\qquad\qquad "
                          r"P_{PEA}(s) = \frac{1}{(J_m+J_L)s^2 + bs + k}", 16))
        bw.add(math_label(r"P_{SEA}(s) = \frac{k}"
                          r"{J_mJ_L s^4 + J_m b\,s^3 + k(J_m{+}J_L)s^2 + kb\,s}",
                          16))
        bw.add(body(
            "&nbsp;&nbsp;• <b>Direct drive.</b> One rigid inertia. Nothing in "
            "the mechanism sets a ceiling at all — its bandwidth is bounded by "
            "the <i>implementation</i>: loop rate, current-loop lag, encoder "
            "noise, torque limits. That is why the answer is \"50–100 Hz and "
            "up\" rather than a formula.<br>"
            "&nbsp;&nbsp;• <b>SEA.</b> Four poles, and the spring puts a "
            "resonance at √(k(J<sub>m</sub>+J<sub>L</sub>)/(J<sub>m</sub>"
            "J<sub>L</sub>)) with an anti-resonance at √(k/J<sub>m</sub>) below "
            "it. Push crossover toward that pair and the loop rings. <b>The "
            "ceiling is mechanical</b> — roughly (1/2π)√(k/J<sub>L</sub>), and "
            "no controller moves it.<br>"
            "&nbsp;&nbsp;• <b>PEA.</b> Same two-pole shape as direct drive with "
            "<b>+k added to the stiffness</b>, so the pole pair moves out to "
            "√(k/(J<sub>m</sub>+J<sub>L</sub>)) — faster, not slower. There is "
            "no compliance <i>in the force path</i>, so the parallel spring "
            "costs no bandwidth; what it costs is a permanent bias torque and "
            "the range of motion the spring will allow."))
        bw.add(callout(
            "<b>The one sentence that separates SEA from PEA, and it is the "
            "sentence people get backwards.</b> A series spring sits "
            "<i>between</i> the motor and the load, so every newton the motor "
            "produces has to go through it — it filters the force path, which "
            "is exactly why it protects, and exactly why it costs bandwidth. A "
            "parallel spring sits <i>alongside</i>, so the motor's force path "
            "to the load is still rigid — it adds force without filtering "
            "anything. <b>Same spring, same stiffness, opposite consequence, "
            "purely because of where it is bolted.</b>", "key"))
        self.add(bw)

        ib = Card("three limits, three topologies — find out which one is "
                  "actually stopping you")
        ib.add(body(
            (
                "For each topology this simplified budget takes the <b>smallest of three estimated limits</b>. "
                "This is a design estimate, distinct from measuring the closed-loop −3 dB bandwidth. Every "
                "number traces to a formula, none is a rule of thumb dressed up as physics:<br><br>&nbsp;&nbsp;•"
                " <b>gain limit</b> — what your PD achieves on the inertia it can see: (1/2π)√(K<sub>p</sub>/J) "
                "for DD and SEA, and (1/2π)√((K<sub>p</sub>+k)/J) for PEA, because a parallel spring adds its "
                "stiffness to yours.<br>&nbsp;&nbsp;• <b>implementation limit</b> — f<sub>s</sub>/15, page 1's "
                "number, after sampling, hold and compute delay.<br>&nbsp;&nbsp;• <b>mechanical limit</b> — for "
                "the SEA, (1/2π)√(k/J<sub>L</sub>): above it the spring, not the motor, decides what the load "
                "does. DD and PEA have no series compliance in the force path and therefore no mechanical "
                "ceiling of this kind at all.<br><br>The bars are those ceilings; the diamond is what you "
                "actually get, and the caption under each says which one bound it.<br><br><b>The edge cases are "
                "buttons — press them in this order:</b><br>&nbsp;&nbsp;<b>1 · soft spring</b> — the SEA ceiling"
                " collapses to a few Hz while DD and PEA do not move at all. This is the safety/bandwidth trade "
                "in one press.<br>&nbsp;&nbsp;<b>2 · stiff spring</b> — SEA climbs back toward the others and "
                "PEA climbs above them, because k is now helping your K<sub>p</sub>. A series spring stiff "
                "enough to stop costing bandwidth is a spring that has stopped protecting "
                "anybody.<br>&nbsp;&nbsp;<b>3 · heavy load</b> — everything falls, but SEA falls fastest: "
                "J<sub>L</sub> is inside its ceiling directly.<br>&nbsp;&nbsp;<b>4 · crank the gain</b> — DD and"
                " PEA keep improving until the loop rate stops them; the SEA does not move at all past its "
                "spring. <b>That is the difference between a ceiling you can buy your way past and one you "
                "cannot.</b><br>&nbsp;&nbsp;<b>5 · slow loop (200 Hz)</b> — now everyone is capped by software "
                "instead, and the three converge. Page 1's argument, landing on hardware."
            ), dim=True))
        self.s_bjm = slider(1, 200, 40)          # x0.001 kg m^2
        self.s_bjl = slider(1, 400, 60)          # x0.001
        self.s_bk = slider(5, 4000, 300)         # N m / rad
        self.s_bkp = slider(10, 4000, 800)
        self.s_bkd = slider(0, 400, 60)          # x0.1
        self.s_bfs = slider(100, 4000, 1000)     # Hz
        self.l_bjm, self.l_bjl, self.l_bk = QLabel(), QLabel(), QLabel()
        self.l_bkp, self.l_bkd, self.l_bfs = QLabel(), QLabel(), QLabel()
        ib.add_layout(slider_row("Motor  Jₘ (×0.001)", self.s_bjm, self.l_bjm))
        ib.add_layout(slider_row("Limb  Jʟ (×0.001)", self.s_bjl, self.l_bjl))
        ib.add_layout(slider_row("Spring  k (N·m/rad)", self.s_bk, self.l_bk))
        ib.add_layout(slider_row("K_p", self.s_bkp, self.l_bkp))
        ib.add_layout(slider_row("K_d (×0.1)", self.s_bkd, self.l_bkd))
        ib.add_layout(slider_row("loop rate (Hz)", self.s_bfs, self.l_bfs))

        edge = QHBoxLayout()
        edge.setSpacing(8)
        for label, vals in (
                ("soft spring", dict(k=20)),
                ("stiff spring", dict(k=3000)),
                ("heavy load", dict(jl=350)),
                ("light rotor", dict(jm=3)),
                ("crank the gain", dict(kp=4000, kd=300)),
                ("slow loop (200 Hz)", dict(fs=200)),
                ("reset", dict(jm=40, jl=60, k=300, kp=800, kd=60, fs=1000))):
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, v=vals: self._preset_bw(v))
            edge.addWidget(b)
        edge.addStretch(1)
        ib.add_layout(edge)

        self.st_bdd = Stat("direct drive", "--", theme.ACCENT)
        self.st_bsea = Stat("SEA", "--", theme.GOOD)
        self.st_bpea = Stat("PEA", "--", theme.VIOLET)
        self.st_bceil = Stat("SEA ceiling √(k/Jʟ)", "--", theme.WARN)
        self.st_bimp = Stat("implementation f_s/15", "--", theme.CYAN)
        ib.add_layout(stat_row(self.st_bdd, self.st_bsea, self.st_bpea,
                               self.st_bceil, self.st_bimp))
        self.c_bw = MplCanvas(width=7.6, height=3.2)
        ib.add(self.c_bw)
        self.t_bw = body("", dim=True)
        ib.add(self.t_bw)
        self.add(ib)
        for s in (self.s_bjm, self.s_bjl, self.s_bk, self.s_bkp, self.s_bkd,
                  self.s_bfs):
            s.valueChanged.connect(self._redraw_bw)
        self._redraw_bw()

        # ==================================================================
        # the money plot: sweep the spring and watch the two ceilings diverge
        # ==================================================================
        self.add(hline())
        self.add(title("Sweep the spring itself — one plot with both ceilings "
                       "on it"))

        sw = Card("achievable bandwidth against stiffness, for all three "
                  "topologies at once")
        sw.add(body(
            "Everything on the last three pages has been at one stiffness at "
            "a time. This sweeps k across four decades and asks, at each "
            "value, <b>what bandwidth can this topology actually deliver</b> "
            "— by searching for the largest gain that still holds the margin "
            "you set, not by quoting a formula.<br><br>"
            "Three curves, and they have three different shapes for three "
            "different reasons:"))
        sw.add(body(
            "&nbsp;&nbsp;• <b>Direct drive is flat.</b> It has no spring, so "
            "k is not in its equations at all. Its ceiling is the "
            "implementation one — f<sub>s</sub>/15 — and it sits there "
            "regardless of anything on the x-axis.<br>"
            "&nbsp;&nbsp;• <b>PEA rises as √(k + K<sub>p</sub>).</b> The "
            "spring adds to the proportional gain, so stiffening the spring "
            "is indistinguishable from turning the gain up, and the curve "
            "climbs until it too hits the implementation ceiling.<br>"
            "&nbsp;&nbsp;• <b>SEA rises as √k but from far below</b>, pinned "
            "at roughly 0.6 × (1/2π)√(k/J<sub>L</sub>). It approaches the "
            "other two only where k has become so large that the spring "
            "deflects almost nothing — <b>which is exactly where it has "
            "stopped being a safety device.</b>"))
        sw.add(callout(
            "<b>Why the SEA number here is smaller than the one in the "
            "widget above, and why both are right.</b><br><br>"
            "The bar widget quotes the SEA's mechanical ceiling as "
            "<b>(1/2π)√(k/J<sub>L</sub>)</b>. That is the frequency at which "
            "the spring <i>stops transmitting</i> — above it the load simply "
            "does not follow the motor, whatever the controller wants. It is "
            "a property of the mechanism alone.<br><br>"
            "This sweep quotes about <b>0.6 ×</b> that, because it asks a "
            "stricter question: not \"where does transmission stop\" but "
            "<b>\"where can I still close a loop and keep 6 dB of gain "
            "margin\"</b>. You always have to cross over some way below the "
            "thing that is about to eat your margin, and 0.6 is the price of "
            "that particular margin — ask for 12 dB and it halves.<br><br>"
            "So: <b>√(k/J<sub>L</sub>)/2π is the wall; 0.6 of it is how "
            "close you may safely drive to the wall.</b> Both scale as √k, "
            "which is the only part that matters for the shape of this "
            "plot.", "key"))
        sw.add(callout(
            "<b>The crossing point is the whole design decision, and the "
            "plot puts a number on it.</b><br><br>"
            "Read where the SEA curve meets the direct-drive line. To the "
            "<b>left</b> of it you are paying bandwidth for impact "
            "protection — that is the trade, made deliberately. To the "
            "<b>right</b> of it you are paying for a spring that is too "
            "stiff to protect anyone and are getting no bandwidth advantage "
            "for it either. <b>A series spring stiff enough to stop costing "
            "you bandwidth is a spring that has stopped doing its job.</b>"
            "<br><br>"
            "The shaded band marks where the spring's deflection under the "
            "motor's peak torque falls below a degree — below which, for a "
            "typical encoder, the spring has also stopped working as a "
            "torque sensor. <b>Two of the three reasons to fit one are gone "
            "in that band.</b>", "key"))
        self.s_sjm = slider(2, 200, 40)
        self.s_sjl = slider(2, 400, 60)
        self.s_szr = slider(1, 50, 5)
        self.s_skp = slider(10, 4000, 500)
        self.s_sgm = slider(0, 200, 60)          # x0.1 dB
        self.s_sfs = slider(100, 4000, 1000)
        self.l_sjm, self.l_sjl, self.l_szr = QLabel(), QLabel(), QLabel()
        self.l_skp, self.l_sgm, self.l_sfs = QLabel(), QLabel(), QLabel()
        sw.add_layout(slider_row("Motor Jₘ (×0.001)", self.s_sjm, self.l_sjm))
        sw.add_layout(slider_row("Limb Jʟ (×0.001)", self.s_sjl, self.l_sjl))
        sw.add_layout(slider_row("Spring damping ζ_r (×0.01)", self.s_szr,
                                 self.l_szr))
        sw.add_layout(slider_row("PEA / DD  K_p", self.s_skp, self.l_skp))
        sw.add_layout(slider_row("margin demanded (×0.1 dB)", self.s_sgm,
                                 self.l_sgm))
        sw.add_layout(slider_row("loop rate (Hz)", self.s_sfs, self.l_sfs))
        self.st_scross = Stat("SEA catches DD at", "--", theme.WARN)
        self.st_sdefl = Stat("deflection there", "--", theme.BAD)
        self.st_sdd = Stat("DD ceiling", "--", theme.ACCENT)
        self.st_ssea100 = Stat("SEA at k = 100", "--", theme.GOOD)
        self.st_spea100 = Stat("PEA at k = 100", "--", theme.VIOLET)
        sw.add_layout(stat_row(self.st_scross, self.st_sdefl, self.st_sdd,
                               self.st_ssea100, self.st_spea100))
        self.c_sw = MplCanvas(width=7.6, height=3.4)
        self._sw_drawn = False
        sw.add(self.c_sw)
        self.t_sw = body("", dim=True)
        sw.add(self.t_sw)
        self.add(sw)
        for s in (self.s_sjm, self.s_sjl, self.s_szr, self.s_skp, self.s_sgm,
                  self.s_sfs):
            s.valueChanged.connect(self._redraw_sweep)
        self._redraw_sweep()

        self.add(callout(
            (
                "<b>What this budget estimates.</b> Its usable-frequency estimate is the smallest of three "
                "limits:<br><br>&nbsp;&nbsp;• <b>what the mechanism allows</b> — the SEA's √(k/J<sub>L</sub>), "
                "the first structural resonance of a link, the backlash in a gearbox<br>&nbsp;&nbsp;• <b>what "
                "the implementation allows</b> — f<sub>s</sub>/10 to f<sub>s</sub>/20 after delay, and less "
                "again if your current loop is slow<br>&nbsp;&nbsp;• <b>what you dare use</b> — noise into the "
                "motor, unmodelled modes above crossover, and the force this thing can apply to a "
                "person<br><br>Raising gain only helps while the first two are far away. In these SEA examples "
                "the elastic mode is restrictive. For all three topologies, achieved bandwidth depends on both "
                "hardware and control, with the input and output specified."
            ), "good"))

        # ---- answering "which is better" head on ------------------------------
        self.add(hline())
        self.add(title("\"So is higher J_eff better? Flat better? Negative "
                       "better?\" — answered directly"))

        ans = Card("there is no globally better curve. There is a better curve "
                   "AT EACH FREQUENCY.")
        ans.add(body(
            "That is the whole point of plotting against ω, and it is why the "
            "question has no single answer. Break it into the three bands that "
            "correspond to three different things that can go wrong:"))
        ans.add(_verdict_table())
        ans.add(body(
            "<b>Read the three rows as three different accidents.</b> Row 1 is a "
            "robot that is too floppy to be useful. Row 2 is a robot that rings "
            "when you push it. Row 3 is a robot that breaks someone's hand. They "
            "are not the same failure and they do not have the same fix.",
            dim=True))
        self.add(ans)

        w = Card("and \"is higher bandwidth always better?\" — no")
        w.add(body(
            "<b>What more bandwidth buys:</b> faster reflexes, better trajectory "
            "tracking, the ability to catch things and recover from shoves, and "
            "stiffer rendered impedance without instability.<br><br>"
            "<b>What it costs:</b><br>"
            "&nbsp;&nbsp;• <b>Noise.</b> Loop gain rises with bandwidth, and so "
            "does the amplification of encoder quantisation. Audible whine, motor "
            "heating, worn bearings.<br>"
            "&nbsp;&nbsp;• <b>Robustness.</b> A high-bandwidth loop reaches up "
            "into frequencies where your model is wrong — unmodelled structural "
            "resonances, cable dynamics, payload flex. It will find them and "
            "excite them.<br>"
            "&nbsp;&nbsp;• <b>Safety.</b> Bandwidth is the ability to apply force "
            "quickly, which is also the ability to <i>hurt</i> quickly.<br><br>"
            "<b>The right target is \"enough\", not \"maximum\":</b> comfortably "
            "above your fastest required motion, comfortably below your first "
            "unmodelled resonance. For a walking humanoid leg, 10–30 Hz. For a "
            "manipulator doing contact tasks, 50–100 Hz. For a surgical tool, "
            "higher still — and none of them wants \"as much as possible\"."))
        self.add(w)

        d = Card("the decision table — what to actually build")
        d.add(_decision_table())
        self.add(d)

        self.add(callout(
            "<b>Design rule of thumb.</b> Ask what frequency the danger arrives "
            "at.<br><br>"
            "• Danger is a <b>collision</b> (high ω) → you need the inertia "
            "hidden up there → <b>SEA</b>, or a soft body.<br>"
            "• Danger is a <b>flat battery</b> (holding a pose, ω ≈ 0) → you need "
            "the gravity torque taken off the motor → <b>PEA</b>.<br>"
            "• Danger is <b>being too slow</b> (catching, balancing) → you cannot "
            "afford any mechanical filter → <b>DD/QDD</b> plus software "
            "compliance.<br><br>"
            "And note these compose: a real humanoid leg can be <b>QDD hip, SEA "
            "ankle, PEA knee</b>, because the three joints face three different "
            "dangers.", "key"))

        self.finish()

    # ------------------------------------------------------------------
    def _preset_bw(self, vals):
        for key, sld in (("jm", self.s_bjm), ("jl", self.s_bjl),
                         ("k", self.s_bk), ("kp", self.s_bkp),
                         ("kd", self.s_bkd), ("fs", self.s_bfs)):
            if key in vals:
                sld.blockSignals(True)
                sld.setValue(vals[key])
                sld.blockSignals(False)
        self._redraw_bw()

    def _redraw_sweep(self):
        """
        The one plot that puts both ceilings on the same axes: achievable
        bandwidth against spring stiffness, searched rather than asserted.

        DD is flat because k is not in its equations. PEA climbs because k
        adds to Kp. SEA climbs as sqrt(k) from far below, and where it
        finally catches DD is where the spring has become too stiff to
        protect anything.
        """
        jm = self.s_sjm.value() / 1000.0
        jl = self.s_sjl.value() / 1000.0
        zr = self.s_szr.value() / 100.0
        kp = float(self.s_skp.value())
        gm_min = self.s_sgm.value() / 10.0
        fs = float(self.s_sfs.value())
        self.l_sjm.setText(f"{jm:.3f}")
        self.l_sjl.setText(f"{jl:.3f}")
        self.l_szr.setText(f"{zr:.2f}")
        self.l_skp.setText(f"{kp:.0f}")
        self.l_sgm.setText(f"{gm_min:.1f} dB")
        self.l_sfs.setText(f"{fs:.0f} Hz")

        impl = fs / 15.0                       # page 1's number
        ks = [10.0 ** (1.0 + 3.2 * i / 39.0) for i in range(40)]

        dd = closed_loop_bw_hz(pd_loop(dd_plant(jm, jl), kp, 0.0).feedback())
        dd = min(dd, impl)

        sea, pea = [], []
        for k in ks:
            s = max_sea_crossover_hz(jm, jl, k, zr, 0.0, gm_min)
            sea.append(min(s, impl) if s > 0 else 0.0)
            t = pd_loop(pea_plant(jm, jl, k), kp, 0.0).feedback()
            pea.append(min(closed_loop_bw_hz(t), impl))

        # where does the SEA finally catch direct drive?
        k_cross, defl = None, None
        for k, s in zip(ks, sea):
            if s >= dd * 0.98:
                k_cross = k
                # deflection under a representative 20 N m peak torque
                defl = math.degrees(20.0 / k)
                break
        self.st_sdd.set(f"{dd:.1f} Hz")
        self.st_scross.set("never" if k_cross is None else
                           f"k = {k_cross:.0f}")
        self.st_sdefl.set("—" if defl is None else f"{defl:.2f}°")
        self.st_sdefl.set_color(theme.BAD if (defl is not None and defl < 1.0)
                                else theme.WARN)
        s100 = max_sea_crossover_hz(jm, jl, 100.0, zr, 0.0, gm_min)
        p100 = closed_loop_bw_hz(
            pd_loop(pea_plant(jm, jl, 100.0), kp, 0.0).feedback())
        self.st_ssea100.set(f"{min(s100, impl):.2f} Hz")
        self.st_spea100.set(f"{min(p100, impl):.2f} Hz")

        c = self.c_sw
        c.clear()
        a = c.ax
        a.loglog(ks, [dd] * len(ks), color=theme.ACCENT, lw=2.2,
                 label="direct drive — no k in its equations")
        a.loglog(ks, pea, color=theme.VIOLET, lw=2.2,
                 label="PEA — k adds to K_p")
        a.loglog(ks, sea, color=theme.WARN, lw=2.4,
                 label="SEA — pinned near 0.6·√(k/Jʟ)/2π")
        a.axhline(impl, color=theme.CYAN, lw=1.2, ls="--",
                  label=f"implementation ceiling  f_s/15 = {impl:.0f} Hz")
        # the band where the spring has stopped being a spring: under a
        # representative 20 N m peak the deflection is below one degree
        k_stiff = 20.0 / math.radians(1.0)
        if k_stiff < ks[-1]:
            a.axvspan(max(k_stiff, ks[0]), ks[-1], color=theme.BAD,
                      alpha=0.09)
            a.text(max(k_stiff, ks[0]) * 1.15, min(sea[0] * 1.2, dd * 0.12)
                   if sea[0] > 0 else dd * 0.12,
                   "spring deflects <1°\nat peak torque:\nno longer protecting,\n"
                   "no longer a sensor",
                   color=theme.BAD, fontsize=6.6, va="bottom")
        if k_cross is not None:
            a.axvline(k_cross, color=theme.WARN, lw=1.1, ls=":")
        a.set_xlabel("spring stiffness k  (N·m/rad)")
        a.set_ylabel("achievable closed-loop bandwidth (Hz)")
        a.set_title("the two ceilings, on one pair of axes", fontsize=9)
        c.legend(loc="upper left")
        c.refresh(layout=not self._sw_drawn)
        self._sw_drawn = True

        msg = (f"<b>Direct drive sits flat at {dd:.1f} Hz</b> — it has no "
               f"spring, so nothing on the x-axis can move it; only the loop "
               f"rate can. ")
        if k_cross is None:
            msg += ("<b>The SEA never catches it</b> anywhere in this range: "
                    "at every stiffness you can build, the series spring is "
                    "costing you bandwidth. That is the honest picture for a "
                    "soft, protective spring.")
        else:
            msg += (f"<b>The SEA only catches it at k ≈ {k_cross:.0f} "
                    f"N·m/rad</b> — and at that stiffness the spring "
                    f"deflects just <b>{defl:.2f}°</b> under a 20 N·m peak. "
                    + ("That is inside the shaded band: too stiff to absorb "
                       "an impact, and too stiff to read as a torque sensor. "
                       "You have paid for a spring and kept none of its "
                       "benefits." if defl < 1.0 else
                       "Still just about usable as a sensor, but the impact "
                       "protection is already thin."))
        msg += (f"<br><br>At a genuinely protective k = 100, the SEA manages "
                f"<b>{min(s100, impl):.2f} Hz</b> against the PEA's "
                f"<b>{min(p100, impl):.2f} Hz</b> with the identical spring. "
                f"<b>That gap is not a controller problem and no controller "
                f"closes it.</b>")
        self.t_sw.setText(msg)

    def _redraw_bw(self):
        """
        Bandwidth as the smallest of three ceilings, computed per topology.

        Nothing here is simulated: each ceiling is a closed-form number, which
        is the point -- you can see WHICH constraint binds, and watch the
        binding one change as the hardware changes.
        """
        jm = self.s_bjm.value() / 1000.0
        jl = self.s_bjl.value() / 1000.0
        k = float(self.s_bk.value())
        kp = float(self.s_bkp.value())
        kd = self.s_bkd.value() / 10.0
        fs = float(self.s_bfs.value())
        self.l_bjm.setText(f"{jm:.3f}")
        self.l_bjl.setText(f"{jl:.3f}")
        self.l_bk.setText(f"{k:.0f}")
        self.l_bkp.setText(f"{kp:.0f}")
        self.l_bkd.setText(f"{kd:.1f}")
        self.l_bfs.setText(f"{fs:.0f} Hz")

        j_tot = jm + jl
        f_impl = practical_bandwidth(fs)                  # f_s / 15
        f_gain_rigid = math.sqrt(kp / j_tot) / (2 * math.pi)
        f_gain_pea = math.sqrt((kp + k) / j_tot) / (2 * math.pi)
        f_sea_mech = sea_bandwidth_hz(k, jl)              # (1/2pi) sqrt(k/JL)

        limits = {
            "direct": [("gain", f_gain_rigid), ("loop rate", f_impl),
                       ("mechanical", math.inf)],
            "sea": [("gain", f_gain_rigid), ("loop rate", f_impl),
                    ("mechanical", f_sea_mech)],
            "pea": [("gain", f_gain_pea), ("loop rate", f_impl),
                    ("mechanical", math.inf)],
        }
        got, binder = {}, {}
        for key, lims in limits.items():
            name, val = min(lims, key=lambda kv: kv[1])
            got[key], binder[key] = val, name

        colours = {"direct": theme.ACCENT, "sea": theme.GOOD,
                   "pea": theme.VIOLET}
        for stat, key in ((self.st_bdd, "direct"), (self.st_bsea, "sea"),
                          (self.st_bpea, "pea")):
            stat.set(f"{got[key]:.0f} Hz")
            stat.set_color(colours[key])
        self.st_bceil.set(f"{f_sea_mech:.0f} Hz")
        self.st_bimp.set(f"{f_impl:.0f} Hz")

        damping_note = ""
        if kd < 0.05:
            damping_note = (" With K<sub>d</sub> at zero none of these three "
                            "is usable in practice — the number below is what "
                            "the gain would buy if the ringing were "
                            "survivable, which it is not.")
        if binder["sea"] == "mechanical":
            msg = (f"<b>The SEA is spring-limited at {f_sea_mech:.0f} Hz</b>, "
                   f"while DD reaches {got['direct']:.0f} Hz and PEA "
                   f"{got['pea']:.0f} Hz on identical gains and an identical "
                   "loop rate. Turn K_p up: the other two move, the SEA does "
                   "not — its ceiling has no gain in it. The only way through "
                   "is a stiffer spring or a lighter limb, which are both "
                   "decisions about metal, not code." + damping_note)
        elif binder["sea"] == "loop rate":
            msg = (f"<b>Everything is software-limited now.</b> At {fs:.0f} Hz "
                   f"the loop caps all three at {f_impl:.0f} Hz, below even "
                   f"the SEA's mechanical {f_sea_mech:.0f} Hz. Buying a "
                   "stiffer spring here would change nothing at all — the "
                   "controller is the bottleneck, and that is a genuinely "
                   "common situation on cheap hardware." + damping_note)
        else:
            msg = (f"<b>Gain-limited across the board.</b> Nothing mechanical "
                   f"or temporal is in the way yet: raise K_p and all three "
                   f"numbers rise together, until DD and PEA hit "
                   f"{f_impl:.0f} Hz and the SEA hits {f_sea_mech:.0f} Hz. "
                   "This is the regime where tuning actually helps, and it is "
                   "the only one." + damping_note)
        self.t_bw.setText(msg)

        c = self.c_bw
        c.clear()
        cap = max([v for _, v in limits["direct"] + limits["sea"]
                   + limits["pea"] if math.isfinite(v)] + [f_impl]) * 1.35
        names = {"direct": "Direct drive", "sea": "SEA", "pea": "PEA"}
        width = 0.26
        for i, (label, _) in enumerate(limits["direct"]):
            xs, hs = [], []
            for j, key in enumerate(("direct", "sea", "pea")):
                val = dict(limits[key])[label]
                xs.append(j + (i - 1) * width)
                hs.append(cap if math.isinf(val) else val)
            c.ax.bar(xs, hs, width=width * 0.92, label=label,
                     color=(theme.CYAN, theme.WARN, theme.BAD)[i], alpha=0.55)
        for j, key in enumerate(("direct", "sea", "pea")):
            c.ax.scatter([j], [got[key]], marker="D", s=90,
                         color=colours[key], zorder=6)
            c.ax.text(j, got[key] * 1.08,
                      f"{got[key]:.0f} Hz\nbound by {binder[key]}",
                      ha="center", fontsize=8, color=colours[key])
        c.ax.set_xticks([0, 1, 2])
        c.ax.set_xticklabels([names[k] for k in ("direct", "sea", "pea")],
                             fontsize=9)
        c.ax.set_ylabel("bandwidth ceiling (Hz)")
        c.ax.set_ylim(0, cap)
        c.ax.set_title("bars are the three ceilings; the diamond is what you "
                       "get (a bar at the top means 'no limit of that kind')",
                       fontsize=8)
        c.legend(loc="upper right")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw(self):
        jm = self.s_jm.value() / 1000.0
        jl = self.s_jl.value() / 1000.0
        k = float(self.s_k.value())
        self.l_jm.setText(f"{jm:.3f}")
        self.l_jl.setText(f"{jl:.3f}")
        self.l_k.setText(f"{k:.0f}")

        c = self.canvas
        c.clear()
        ws = [10 ** (x / 40.0) for x in range(-20, 141)]
        colours = {"direct": theme.ACCENT, "sea": theme.GOOD, "pea": theme.VIOLET}
        anti = math.sqrt(k / jm)
        for key, colour in colours.items():
            if not self.chk[key].isChecked():
                continue
            if key == "sea":
                for seg in ([w for w in ws if w < anti * 0.985],
                            [w for w in ws if w > anti * 1.015]):
                    if seg:
                        c.ax.semilogx(seg, [j_eff(key, jm, jl, k, w) for w in seg],
                                      color=colour, lw=2.3,
                                      label=TOPOLOGY_NAMES[key] if seg[0] == ws[0]
                                      else None)
            else:
                c.ax.semilogx(ws, [j_eff(key, jm, jl, k, w) for w in ws],
                              color=colour, lw=2.3, label=TOPOLOGY_NAMES[key])
        c.ax.axhline(0, color=theme.BORDER, lw=1.0)
        c.ax.axhline(jl, color=theme.TEXT_FAINT, lw=0.9, ls=":")
        c.ax.set_xlabel("interaction frequency ω  (rad/s)   —   slow lean ← → sharp impact")
        c.ax.set_ylabel("J_eff  (kg·m²)")
        c.ax.set_ylim(-(jm + jl) * 1.6, (jm + jl) * 2.2)
        c.legend(loc="upper left")
        c.refresh()


# ==========================================================================
# PAGE 5 -- Gearing and the square law
# ==========================================================================

class GearingPage(Page):
    TITLE = "Gearing & Reflected Inertia"
    SUBTITLE = ((
                    "The N² square law: why a 100:1 gearbox makes your motor feel 10,000 times heavier — and limits "
                    "the impedance you can render."
                ))
    SECTION = SECTION
    NOTES = "material p.1"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The \"Square Law\" of reflected inertia.</b> This is the single "
            "most important technical reason behind most humanoid actuator "
            "choices. When you put a gear ratio N between motor and joint, the "
            "inertia of the motor's rotor is <i>reflected</i> to the output shaft "
            "by <b>N²</b>.", "key"))

        d = Card("the maths, and the number that follows from it")
        d.add(math_label(r"J_{reflected} = J_m \times N^2", 18))
        d.add(body(
            "For a 100:1 drive: 100² = <b>10,000</b>.<br><br>"
            "The human at the output shaft doesn't just feel the weight of the "
            "robot arm; they feel the motor's internal rotor inertia "
            "<b>10,000 times heavier</b> than it actually is."))
        self.add(d)

        i = Card("turn the ratio")
        self.s_n = slider(1, 200, 100)
        self.s_jm = slider(1, 200, 40)
        self.l_n, self.l_jm = QLabel(), QLabel()
        i.add_layout(slider_row("Gear ratio  N", self.s_n, self.l_n))
        i.add_layout(slider_row("Rotor  Jₘ", self.s_jm, self.l_jm))

        self.st_refl = Stat("reflected inertia", "--", theme.BAD)
        self.st_mult = Stat("multiplier", "--", theme.WARN)
        self.st_tq = Stat("output torque", "--", theme.GOOD)
        self.st_sp = Stat("output speed", "--", theme.ACCENT)
        i.add_layout(stat_row(self.st_refl, self.st_mult, self.st_tq, self.st_sp))

        self.canvas = MplCanvas(width=7.4, height=2.9)
        i.add(self.canvas)
        self.add(i)
        self.s_n.valueChanged.connect(self._redraw)
        self.s_jm.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(hline())
        self.add(title("Why this kills impedance control"))

        k = Card("loss of transparency")
        k.add(body(
            "Impedance control is an <b>open-loop force</b> strategy. You command "
            "a torque and <i>assume</i> the mechanics will let the arm move if "
            "someone pushes it. The encoder is your only witness."))
        k.add(body(
            "<b>With a direct drive:</b> I push the arm, the motor spins "
            "immediately, the encoder sees the change, and the software says "
            "\"he pushed it 1 degree, I should apply X of virtual spring "
            "force.\""))
        k.add(body(
            "<b>With a 100:1 harmonic drive:</b> I push the arm with 5 N and "
            "<b>it does not move at all</b> — the reflected inertia and the "
            "friction hold it. Since the arm doesn't move, the encoder sees "
            "<b>zero change</b>, and the software thinks <b>no one is touching "
            "it</b>."))
        k.add(body(
            (
                "<b>Stiction on top.</b> High-ratio gears have high static friction. You might have to push with"
                " 20 N of force just to get the gears to \"break away\" and start moving at all. The system is no "
                "longer <b>backdrivable</b>."
            ), dim=True))
        self.add(k)

        self.add(callout(
            "In impedance control the motor 'feels' the user through <b>motion</b> "
            "(encoders). Behind a gearbox, the gears mask that motion. This is "
            "the reason to choose <b>admittance control</b> instead: it uses an "
            "external force sensor to bypass the gear friction entirely, so the "
            "controller can 'see' the user's intent even when the gears are "
            "physically locked.", "warn"))

        b = Card("the bypass: how a force sensor physically skips the gears")
        b.add(body(
            "In a standard robot without a force sensor, the <b>only</b> way the "
            "controller knows you are pushing is if the motor's encoder sees the "
            "shaft move. With a 100:1 harmonic drive the gears are so stiff that "
            "a human push might not move the motor at all. The encoder sees 0 "
            "movement, so the controller does 0."))
        b.add(body(
            "<b>The bypass solution:</b> put a Force/Torque sensor at the "
            "interface where the human touches the robot — the end-effector, or "
            "the cuff of an exoskeleton.<br><br>"
            "&nbsp;&nbsp;<b>Input:</b> the sensor picks up your 5 N push "
            "instantly.<br>"
            "&nbsp;&nbsp;<b>The bypass:</b> that signal goes directly to the "
            "computer <b>before</b> the force has to fight the gears. The "
            "computer sees your intent even though the arm hasn't moved a single "
            "millimetre yet."))
        b.add(body(
            "Admittance control is essential here because it lets the robot use "
            "<b>its own power</b> to overcome <b>its own friction</b>. The robot "
            "feels your 1 N push and says: <i>\"I will start the motor for you so "
            "you don't have to fight my 10,000× inertia.\"</i>", dim=True))
        self.add(b)

        third = Card("the third option nobody mentions: sense AFTER the gearbox")
        third.add(body(
            "Impedance needs backdrivability. Admittance needs a sensor at the "
            "contact point. There is a middle path that is what most "
            "collaborative arms actually do:<br><br>"
            "<b>Put a torque sensor on the joint OUTPUT — downstream of the "
            "gearbox.</b>"))
        third.add(body(
            "Now the friction, backlash and reflected inertia of the transmission "
            "are all <i>inside</i> the loop, between the motor and the sensor. "
            "The controller closes on the torque that is <b>actually leaving the "
            "joint</b>, so the gearbox's sins become a disturbance to be "
            "rejected rather than a wall you cannot see through.<br><br>"
            "This is how <b>KUKA LBR iiwa</b> and <b>Franka Emika</b> do genuine "
            "impedance control through 100:1 harmonic drives. It is also how "
            "high-end SEAs work — the spring <i>is</i> an output-side torque "
            "sensor, just a mechanical one."))
        third.add(body(
            "<b>The costs:</b> a strain-gauge torque sensor per joint is "
            "expensive, adds compliance (it must deflect to measure), adds a "
            "failure mode, and its bandwidth and noise now cap your torque loop. "
            "You have also not fixed the <b>inertia</b> — during an impact faster "
            "than your loop, the reflected N²J<sub>m</sub> still arrives. Sensing "
            "after the gearbox buys you control authority, not passive safety.",
            dim=True))
        self.add(third)

        self.add(callout(
            (
                "<b>Three ways out of a gearbox, ranked by what they actually fix.</b><br><br><b>1 · Don't "
                "gear.</b> QDD. Fixes sensing <i>and</i> inertia. Costs torque density and motor mass.<br><b>2 ·"
                " Output-side torque sensor.</b> Fixes sensing. Does <b>not</b> fix inertia. Costs money and "
                "adds compliance.<br><b>3 · F/T sensor at the contact point + admittance.</b> Fixes sensing at "
                "one point only. Does <b>not</b> fix inertia. Goes unstable against stiff contact.<br><br>Note "
                "that none of them fixes reflected inertia except the first. Once N² inertia exists, only "
                "mechanics removes it — which is the same lesson as the Series Elastic Actuators page."
            ), "key"))

        self.add(callout(
            "<b>Interview-ready summary.</b> \"The bypass happens because we "
            "sense the user's force at the point of contact <b>before</b> it "
            "enters the transmission. In a 100:1 system, the reflected inertia "
            "and friction would otherwise lock the joint. By feeding that force "
            "into a virtual mass-damper model, we calculate the motion a "
            "'perfect' frictionless robot would have, and then command our actual "
            "motor to reach that position using a high-gain inner loop.\"", "good"))

        self.finish()

    def _redraw(self):
        n = float(self.s_n.value())
        jm = self.s_jm.value() / 1000.0
        self.l_n.setText(f"{n:.0f}:1")
        self.l_jm.setText(f"{jm:.3f}")

        refl = reflected_inertia(jm, n)
        tq, sp = gear_output(1.0, 100.0, n)
        self.st_refl.set(f"{refl:.1f}")
        self.st_mult.set(f"{n * n:,.0f}×")
        self.st_tq.set(f"{tq:.0f} N·m")
        self.st_sp.set(f"{sp:.1f} rad/s")

        c = self.canvas
        c.clear()
        ns = list(range(1, 201))
        c.ax.semilogy(ns, [reflected_inertia(jm, x) for x in ns],
                      color=theme.BAD, lw=2.4, label="reflected Jₘ · N²")
        c.ax.semilogy(ns, [jm * x for x in ns], color=theme.TEXT_FAINT, lw=1.3,
                      ls="--", label="if it were only linear in N")
        c.ax.axvline(n, color=theme.ACCENT, lw=1.2)
        c.ax.scatter([n], [refl], color=theme.ACCENT, zorder=5, s=34)
        c.ax.set_xlabel("gear ratio N")
        c.ax.set_ylabel("inertia felt at output  (kg·m²)")
        c.legend(loc="upper left")
        c.refresh()
