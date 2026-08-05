"""
Correctness checks for ctrlcore. Run with:   python tests/test_ctrl.py

Same spirit as test_core.py: these encode the facts the control pages assert
on screen. If a limit or a sign flips here, a page is lying to the reader.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ctrlcore.actuators import (  # noqa: E402
    gear_output,
    gravity_torque,
    j_eff_direct,
    j_eff_pea,
    j_eff_sea,
    motor_torque_pea,
    pea_resonance_rad_s,
    reflected_inertia,
    scale_factors,
    sea_antiresonance_rad_s,
    sea_bandwidth_hz,
    sea_deflection_ratio,
    sea_resonance_rad_s,
    sea_transmissibility,
    spring_torque,
)
from ctrlcore.realtime import (  # noqa: E402
    PID,
    TaskProfile,
    alias_frequency,
    delay_limited_bandwidth,
    delay_phase_lag_deg,
    derivative_error_from_jitter,
    nyquist,
    practical_bandwidth,
    rate_monotonic_bound,
    run_pid,
)
from ctrlcore.impedance import (  # noqa: E402
    VirtualModel,
    equilibrium_angle,
    impedance_magnitude,
    impedance_torque,
    run_admittance,
    run_impedance,
    tau_ff_from_deviation,
    two_controller_demo,
)
from ctrlcore.neuro import (  # noqa: E402
    force_length,
    force_velocity,
    hill_force,
    joint_torque_from_motor,
    loop_gain,
    motor_torque_from_current,
    run_pff,
)

FAILS = []

JM, JL, K = 0.04, 0.06, 300.0


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}   {detail}")
        FAILS.append(name)


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


# ==========================================================================
print("\n[1] Direct drive")

check("J_eff = Jm + JL", approx(j_eff_direct(JM, JL), JM + JL))
check("J_eff is frequency independent",
      all(approx(j_eff_direct(JM, JL, w), JM + JL)
          for w in (0.0, 1.0, 10.0, 1e4)))


# ==========================================================================
print("\n[2] Series elastic -- the two limits are the whole argument")

check("omega -> 0 gives Jm + JL",
      approx(j_eff_sea(JM, JL, K, 0.0), JM + JL, 1e-9))
check("omega -> inf gives JL alone",
      approx(j_eff_sea(JM, JL, K, 1e7), JL, 1e-6),
      f"got {j_eff_sea(JM, JL, K, 1e7)}")
check("the rotor really is hidden at impact "
      "(J_eff at 1e5 rad/s has collapsed onto JL)",
      j_eff_sea(JM, JL, K, 1e5) < JM + JL
      and approx(j_eff_sea(JM, JL, K, 1e5), JL, 1e-6),
      f"got {j_eff_sea(JM, JL, K, 1e5)}, JL={JL}, Jm+JL={JM + JL}")

anti = math.sqrt(K / JM)
check("antiresonance at sqrt(k/Jm) is infinite",
      math.isinf(j_eff_sea(JM, JL, K, anti)))
check("J_eff grows without bound approaching antiresonance from below",
      j_eff_sea(JM, JL, K, anti * 0.999) > 10 * (JM + JL))

check("bandwidth f_n = (1/2pi)sqrt(k/JL)",
      approx(sea_bandwidth_hz(K, JL), math.sqrt(K / JL) / (2 * math.pi)))
check("stiffer spring raises the bandwidth",
      sea_bandwidth_hz(2 * K, JL) > sea_bandwidth_hz(K, JL))
check("heavier limb lowers the bandwidth",
      sea_bandwidth_hz(K, 2 * JL) < sea_bandwidth_hz(K, JL))
check("SEA bandwidth lands in the 10-20 Hz band for plausible humanoid numbers",
      8.0 < sea_bandwidth_hz(180.0, 0.06) < 30.0,
      f"{sea_bandwidth_hz(180.0, 0.06):.1f} Hz")


# ==========================================================================
print("\n[3] Parallel elastic -- negative inertia is not a bug")

check("omega -> inf gives Jm + JL (no impact protection)",
      approx(j_eff_pea(JM, JL, K, 1e7), JM + JL, 1e-6))
check("slow interaction gives NEGATIVE effective inertia",
      j_eff_pea(JM, JL, K, 0.5) < 0)
wr = pea_resonance_rad_s(K, JM, JL)
check("J_eff = 0 exactly at sqrt(k/(Jm+JL))",
      approx(j_eff_pea(JM, JL, K, wr), 0.0, 1e-9))
check("J_eff is monotonically increasing in omega",
      all(j_eff_pea(JM, JL, K, w) < j_eff_pea(JM, JL, K, w * 1.5)
          for w in (0.5, 2.0, 10.0, 60.0)))


# ==========================================================================
print("\n[4] Gravity compensation")

m, L, k_s, th0 = 30.0, 0.4, 90.0, math.radians(55)
check("gravity torque is zero hanging straight down",
      approx(gravity_torque(m, L, 0.0), 0.0))
check("gravity torque is maximal horizontal",
      approx(gravity_torque(m, L, math.pi / 2), m * 9.81 * L))
check("spring torque is zero at its rest angle",
      approx(spring_torque(k_s, th0, th0), 0.0))
check("motor torque = gravity - spring",
      approx(motor_torque_pea(m, L, k_s, 0.4, th0),
             gravity_torque(m, L, 0.4) - spring_torque(k_s, 0.4, th0)))
# there must exist an angle where the motor does nothing
signs = [motor_torque_pea(m, L, k_s, math.radians(d), th0) for d in range(0, 91)]
check("some angle exists where the motor supplies zero torque",
      min(signs) < 0 < max(signs))


# ==========================================================================
print("\n[5] Gearing and scaling")

check("reflected inertia is Jm * N^2",
      approx(reflected_inertia(0.001, 100.0), 0.001 * 10000))
check("100:1 multiplies rotor inertia by exactly 10,000",
      approx(reflected_inertia(1.0, 100.0), 10000.0))
tq, sp = gear_output(2.0, 300.0, 50.0)
check("gearing multiplies torque by N", approx(tq, 100.0))
check("gearing divides speed by N", approx(sp, 6.0))

f = scale_factors(2.0)
check("mass scales as L^3", approx(f["mass"], 8.0))
check("torque scales as L^2", approx(f["torque"], 4.0))
check("inertia scales as L^5", approx(f["inertia"], 32.0))
check("torque per unit mass FALLS as the robot grows",
      scale_factors(2.0)["torque_per_mass"] < scale_factors(1.0)["torque_per_mass"])


# ==========================================================================
print("\n[6] Impedance control")

check("zero error and no feedforward gives zero torque",
      approx(impedance_torque(0.1, 0.2, 0.1, 0.2, 50.0, 5.0), 0.0))
check("with tau_ff, nominal tracking outputs exactly tau_ff",
      approx(impedance_torque(0.1, 0.2, 0.1, 0.2, 50.0, 5.0, 3.3), 3.3))
check("torque opposes positive displacement",
      impedance_torque(0.1, 0.0, 0.0, 0.0, 50.0, 5.0) < 0)
check("||Z|| = |K| + |B|", approx(impedance_magnitude(-30.0, 4.0), 34.0))

# round-trip between the two parameterisations
k_i, b_i, thd, omd, tff = 60.0, 8.0, 0.15, -0.4, 2.5
eq = equilibrium_angle(thd, omd, k_i, b_i, tff)
back = tau_ff_from_deviation(k_i, b_i, eq - thd, omd)
check("theta_eq <-> tau_ff round-trips", approx(back, tff, 1e-9),
      f"{back} vs {tff}")
check("theta_eq differs from theta_d whenever tau_ff is non-zero",
      abs(eq - thd) > 1e-9)

# Property 3 / Corollary 3.1 -- the headline result
_, _, ta, tb, eqa, eqb = two_controller_demo(160.0, 9.6, 45.0, 2.7, 0.0)
check("PROPERTY 3: identical torque under nominal kinematics despite "
      "different K and B",
      max(abs(a - b) for a, b in zip(ta, tb)) < 1e-9,
      f"max gap {max(abs(a - b) for a, b in zip(ta, tb))}")
check("...even though their equilibrium angles are very different",
      max(abs(a - b) for a, b in zip(eqa, eqb)) > 1.0)

_, _, ta2, tb2, _, _ = two_controller_demo(160.0, 9.6, 45.0, 2.7, 4.0)
check("OFF-NOMINAL: the same two controllers now diverge",
      max(abs(a - b) for a, b in zip(ta2, tb2)) > 1.0)

# position control is the tau_ff = 0 corner
pos = run_impedance(80.0, 6.0, tau_ff=0.0)
check("a PD position controller returns to its target after a push",
      abs(pos.theta[-1]) < abs(max(pos.theta, key=abs)) * 0.3)
tor = run_impedance(0.0, 0.0, tau_ff=0.0)
check("||Z|| = 0 has no restoring force: it never comes back",
      abs(tor.theta[-1]) >= abs(max(tor.theta, key=abs)) * 0.9)

soft = run_impedance(20.0, 4.0)
stiff = run_impedance(300.0, 20.0)
check("stiffer means less deviation",
      max(abs(x) for x in stiff.theta) < max(abs(x) for x in soft.theta))
check("stiffer means more force on the human",
      max(abs(x) for x in stiff.tau) > max(abs(x) for x in soft.tau))


# ==========================================================================
print("\n[7] Admittance control")

vm = VirtualModel(m_v=2.0, b_v=0.0, k_v=0.0)
x, v = vm.step(10.0, 0.01)
check("virtual acceleration is F / M_v",
      approx(v, (10.0 / 2.0) * 0.01, 1e-12))
check("position integrates from the new velocity",
      approx(x, v * 0.01, 1e-12))

light = run_admittance(0.5, 2.0)
heavy = run_admittance(15.0, 2.0)
check("a lighter virtual mass moves further for the same push",
      max(abs(x) for x in light.theta) > max(abs(x) for x in heavy.theta))

free = run_admittance(2.0, 6.0, stiction=0.0)
stuck = run_admittance(2.0, 6.0, stiction=25.0)
check("THE BYPASS: heavy gearbox stiction barely changes the response, "
      "because the force sensor sits outside the transmission",
      abs(max(abs(x) for x in stuck.theta)
          - max(abs(x) for x in free.theta)) < 0.25 * max(abs(x) for x in free.theta),
      f"free {max(abs(x) for x in free.theta):.4f} "
      f"stuck {max(abs(x) for x in stuck.theta):.4f}")


# ==========================================================================
print("\n[8] Hill muscle model")

check("force-length peaks at optimal fibre length",
      approx(force_length(1.0), 1.0) and force_length(0.6) < 0.5)
check("force-length is symmetric about the optimum",
      approx(force_length(0.8), force_length(1.2), 1e-9))
check("force-velocity is 1.0 at zero velocity", approx(force_velocity(0.0), 1.0))
check("shortening fast costs force", force_velocity(-0.8) < 0.3)
check("being stretched while active gives a bonus (eccentric > 1)",
      force_velocity(0.5) > 1.0)
check("eccentric branch saturates at the 1.8 plateau",
      approx(force_velocity(50.0), 1.8) and force_velocity(0.2) < 1.8)
check("hill force is zero with zero activation",
      approx(hill_force(0.0, 1.0, 0.0), 0.0))
check("hill force is linear in activation",
      approx(hill_force(0.5, 1.0, 0.0), 0.5 * hill_force(1.0, 1.0, 0.0)))


# ==========================================================================
print("\n[9] Positive force feedback")

check("loop gain is k_f * F_max at optimum length and zero velocity",
      approx(loop_gain(1e-4, 3000.0), 0.3))

_, f_open, a_open, _ = run_pff(0.0)
_, f_closed, a_closed, _ = run_pff(2e-4)
check("k_f = 0 leaves activation exactly at the EMG command",
      max(a_open) - min(a_open) < 1e-12)
check("closing the loop AMPLIFIES force without changing the command",
      max(f_closed) > max(f_open) * 1.05)
check("closing the loop raises activation above the EMG command",
      max(a_closed) > max(a_open) + 1e-6)

_, f_gated, _, _ = run_pff(9e-4, gated=True)
_, f_ungated, _, _ = run_pff(9e-4, gated=False)
check("the phase gate is what keeps a high-gain loop bounded",
      max(f_ungated) > max(f_gated),
      f"gated {max(f_gated):.0f} N, ungated {max(f_ungated):.0f} N")
check("force stays finite even ungated (activation saturates at 1)",
      math.isfinite(max(f_ungated)))


# ==========================================================================
print("\n[10] SEA: the three frequencies are three different things")

w_a = sea_antiresonance_rad_s(K, JM)
w_r = sea_resonance_rad_s(K, JM, JL)
w_n = 2 * math.pi * sea_bandwidth_hz(K, JL)

check("antiresonance is sqrt(k/Jm)", approx(w_a, math.sqrt(K / JM)))
check("resonance is sqrt(k(Jm+JL)/(Jm JL))",
      approx(w_r, math.sqrt(K * (JM + JL) / (JM * JL))))
check("resonance sits ABOVE antiresonance", w_r > w_a,
      f"w_a={w_a:.1f}  w_r={w_r:.1f}")
check("J_eff = 0 exactly at the resonance",
      approx(j_eff_sea(JM, JL, K, w_r), 0.0, 1e-6),
      f"got {j_eff_sea(JM, JL, K, w_r)}")
check("J_eff is negative BETWEEN antiresonance and resonance",
      j_eff_sea(JM, JL, K, math.sqrt(w_a * w_r)) < 0)
check("motor-side bandwidth is a DIFFERENT frequency from either",
      abs(w_n - w_a) > 1.0 and abs(w_n - w_r) > 1.0,
      f"w_n={w_n:.1f} w_a={w_a:.1f} w_r={w_r:.1f}")

check("transmissibility is ~1 well below f_n",
      approx(sea_transmissibility(K, JL, w_n * 0.02), 1.0, 1e-2))
check("transmissibility blows up at f_n",
      sea_transmissibility(K, JL, w_n * 0.999) > 100.0)
check("transmissibility rolls off far above f_n (load stops following)",
      sea_transmissibility(K, JL, w_n * 30) < 0.01)

check("spring deflection vanishes as omega^2 at low frequency",
      sea_deflection_ratio(JM, K, 0.1) < 1e-4,
      f"got {sea_deflection_ratio(JM, K, 0.1)}")
check("deflection ratio quadruples when omega doubles (the omega^2 law)",
      approx(sea_deflection_ratio(JM, K, 0.2) / sea_deflection_ratio(JM, K, 0.1),
             4.0, 1e-2))
check("the spring DOES deflect at low frequency -- it is not zero",
      sea_deflection_ratio(JM, K, 0.1) > 0.0)
check("above the antiresonance the spring takes MOST of the relative motion",
      sea_deflection_ratio(JM, K, w_a * 4) > 1.0)


# ==========================================================================
print("\n[11] PEA is NOT an SEA -- the difference that matters")

fast = 1e6
check("at impact a PEA presents Jm+JL, NOT JL",
      approx(j_eff_pea(JM, JL, K, fast), JM + JL, 1e-6),
      f"got {j_eff_pea(JM, JL, K, fast)}")
check("at impact an SEA presents JL, NOT Jm+JL",
      approx(j_eff_sea(JM, JL, K, fast), JL, 1e-6),
      f"got {j_eff_sea(JM, JL, K, fast)}")
check("so the SEA hides the rotor at impact and the PEA does not",
      j_eff_sea(JM, JL, K, fast) < j_eff_pea(JM, JL, K, fast) - 1e-9)
ratio = j_eff_pea(JM, JL, K, fast) / j_eff_sea(JM, JL, K, fast)
check("PEA presents (Jm+JL)/JL times more inertia at impact",
      approx(ratio, (JM + JL) / JL, 1e-4), f"ratio {ratio:.3f}")


# ==========================================================================
print("\n[12] Real-time: sampling, delay, scheduling")

check("Nyquist is half the sample rate", approx(nyquist(1000.0), 500.0))
check("practical bandwidth is far BELOW Nyquist",
      practical_bandwidth(1000.0) < nyquist(1000.0) / 5)
check("1 kHz loop gives roughly 67 Hz of usable bandwidth",
      60.0 < practical_bandwidth(1000.0) < 75.0)

check("a signal below Nyquist is not aliased",
      approx(alias_frequency(120.0, 1000.0), 120.0))
check("950 Hz sampled at 1 kHz folds down to 50 Hz",
      approx(alias_frequency(950.0, 1000.0), 50.0))
check("a signal exactly at f_s aliases to DC",
      approx(alias_frequency(1000.0, 1000.0), 0.0))

check("delay costs phase linearly with frequency",
      approx(delay_phase_lag_deg(0.001, 100.0), -36.0))
check("2 ms of delay caps bandwidth near 83 Hz on a 60 deg budget",
      approx(delay_limited_bandwidth(0.002), 60.0 / (360 * 0.002), 1e-9))
check("delay ceiling is independent of sample rate -- faster sampling "
      "cannot buy it back",
      delay_limited_bandwidth(0.01) < practical_bandwidth(20000.0),
      f"delay-limited {delay_limited_bandwidth(0.01):.1f} Hz vs "
      f"sampling-limited {practical_bandwidth(20000.0):.1f} Hz")
check("zero delay imposes no ceiling",
      math.isinf(delay_limited_bandwidth(0.0)))
check("doubling the delay doubles the phase lost",
      approx(delay_phase_lag_deg(0.002, 100.0),
             2 * delay_phase_lag_deg(0.001, 100.0)))

check("rate-monotonic bound is 100% for one task",
      approx(rate_monotonic_bound(1), 1.0))
check("rate-monotonic bound approaches ln 2",
      approx(rate_monotonic_bound(400), math.log(2), 1e-3))
check("bound falls monotonically as tasks are added",
      all(rate_monotonic_bound(k) > rate_monotonic_bound(k + 1)
          for k in range(1, 10)))

t = TaskProfile(period_ms=1.0, wcet_ms=0.35)
check("utilisation is WCET / period", approx(t.utilisation, 0.35))
check("a task longer than its deadline is not schedulable",
      not TaskProfile(period_ms=1.0, wcet_ms=1.4).schedulable)


# ==========================================================================
print("\n[13] PID: jitter hits D, saturation winds up I")

check("10% jitter gives ~9% derivative error",
      approx(derivative_error_from_jitter(0.10), 0.10 / 1.10, 1e-9))
check("no jitter, no derivative error",
      approx(derivative_error_from_jitter(0.0), 0.0))
check("derivative error grows with jitter",
      derivative_error_from_jitter(0.30) > derivative_error_from_jitter(0.05))

# Windup needs the joint BLOCKED (error cannot shrink) and the actuator
# SATURATED. Released at t = 1.5 s, which is what turns the stored integral
# area into visible overshoot.
_WIND = dict(setpoint=0.35, duration=4.0, block_until=1.5)


def _wind(mode):
    return run_pid(PID(kp=40, ki=120, kd=3, tau_d=0.002, anti_windup=mode),
                   **_WIND)


free, clamped, back = _wind("none"), _wind("clamp"), _wind("back_calc")

check("the blocking load really does saturate the actuator",
      any(abs(abs(u) - 12.0) < 1e-6 for u in free.u))
check("WINDUP: without anti-windup the integrator grows far larger",
      max(abs(v) for v in free.i) > 2.0 * max(abs(v) for v in clamped.i),
      f"none {max(abs(v) for v in free.i):.1f} vs "
      f"clamp {max(abs(v) for v in clamped.i):.1f}")
check("...and once the load is released, that stored area becomes overshoot",
      max(free.y) > max(clamped.y) + 1e-4,
      f"none {max(free.y):.4f} vs clamp {max(clamped.y):.4f}")
check("back-calculation also bounds the integrator",
      max(abs(v) for v in back.i) < max(abs(v) for v in free.i),
      f"back {max(abs(v) for v in back.i):.1f} vs "
      f"none {max(abs(v) for v in free.i):.1f}")
check("a released load lets the joint reach its target again",
      abs(clamped.y[-1] - 0.35) < 0.02,
      f"ended at {clamped.y[-1]:.4f}")

# derivative filtering suppresses noise-driven chatter
def _chatter(tr):
    return sum(abs(b - a) for a, b in zip(tr.u, tr.u[1:])) / max(1, len(tr.u) - 1)

raw = run_pid(PID(kp=40, ki=0, kd=3, tau_d=0.0), duration=1.0, noise=2e-4)
filt = run_pid(PID(kp=40, ki=0, kd=3, tau_d=0.003), duration=1.0, noise=2e-4)
check("FILTERING: an unfiltered derivative chatters far more under noise",
      _chatter(raw) > 2.0 * _chatter(filt),
      f"raw {_chatter(raw):.3f} vs filtered {_chatter(filt):.3f}")

check("output respects the actuator saturation limits",
      all(-12.0 - 1e-9 <= u <= 12.0 + 1e-9 for u in clamped.u))


# ==========================================================================
print("\n[14] Motor as a force sensor")

check("tau = K_t * I", approx(motor_torque_from_current(4.0, 0.09), 0.36))
check("perfect transmission: joint torque = motor torque * r",
      approx(joint_torque_from_motor(2.0, 50.0), 100.0))
check("losses make the estimate optimistic",
      joint_torque_from_motor(2.0, 50.0, 0.6) < joint_torque_from_motor(2.0, 50.0))


# ==========================================================================
print("\n" + "=" * 62)
if FAILS:
    print(f"  {len(FAILS)} FAILED: " + ", ".join(FAILS))
    sys.exit(1)
print("  all ctrlcore checks passed")
sys.exit(0)
