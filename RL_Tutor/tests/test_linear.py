"""
Correctness checks for ctrlcore.linear and ctrlcore.nonlinear.
Run with:   python tests/test_linear.py

Same spirit as test_ctrl.py: every check here encodes a number that one of the
Systems & Stability, Controller Design or Nonlinear pages prints on screen. If
one of these flips, a page is lying to the reader.

Where a closed-form answer exists it is checked against the numerics, not
against itself -- the analytic second-order step against the RK4 integrator,
Routh-Hurwitz against actual root finding, the Nyquist encirclement count
against the closed-loop poles.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from ctrlcore.linear import (  # noqa: E402
    TF,
    bandwidth_second_order,
    damped_frequency,
    quality_factor,
    resonant_frequency,
    classify_stability,
    critical_gain,
    encirclements,
    first_order,
    is_controllable,
    is_observable,
    joint_wn_zeta,
    lead,
    lead_phase_deg,
    alpha_for_phase,
    lqr,
    margins,
    margins_with_delay,
    observer_gain,
    overshoot_fraction,
    peak_time,
    phase_margin_of_zeta,
    pid_tf,
    place_poles,
    poly_roots,
    resonant_peak_db,
    root_locus,
    routh_rhp_count,
    run_velocity_observer,
    second_order,
    second_order_step,
    settling_time,
    step_metrics,
    step_response,
    vector_margin,
    zeta_from_overshoot,
)
from ctrlcore.nonlinear import (  # noqa: E402
    Pendulum,
    backlash,
    computed_torque,
    coulomb_friction,
    deadzone,
    describing_function_saturation,
    energy_swingup,
    gain_scheduled_pd,
    gravity_comp_pd,
    large_angle_period,
    lyapunov_pd_pendulum,
    lyapunov_rate,
    pd_controller,
    run_stick_slip,
    saturation,
    separatrix,
    sliding_mode,
    trajectory,
)

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}   {detail}")
        FAILS.append(name)


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


# ==========================================================================
print("\n[1] First order -- one pole, and it cannot misbehave")

t, y = step_response(first_order(2.0, 0.1), 1.0, 1e-4)
i_tau = min(range(len(t)), key=lambda k: abs(t[k] - 0.1))
check("reaches 63.2% of K at t = tau", approx(y[i_tau] / 2.0, 0.632, 2e-3),
      y[i_tau] / 2.0)
check("never overshoots", max(y) <= 2.0 + 1e-9, max(y))
check("no proportional gain can destabilise it",
      math.isinf(critical_gain(first_order(1.0, 0.1))))
check("closed-loop pole only moves further left",
      (first_order(1.0, 0.1) * 50.0).feedback().poles()[0].real
      < (first_order(1.0, 0.1) * 1.0).feedback().poles()[0].real)


# ==========================================================================
print("\n[2] Second order -- the numerics must match the closed forms")

WN, Z = 8.0, 0.35
t, y = step_response(second_order(WN, Z), 3.0, 2e-4)
err = max(abs(yi - second_order_step(WN, Z, ti)) for ti, yi in zip(t, y))
check("RK4 step response matches the analytic solution", err < 1e-4, err)

m = step_metrics(t, y)
check("measured overshoot = exp(-pi z / sqrt(1-z^2))",
      approx(m.overshoot, overshoot_fraction(Z), 5e-3),
      (m.overshoot, overshoot_fraction(Z)))
check("measured peak time = pi / w_d",
      approx(m.peak_time, peak_time(Z, WN), 2e-3))
check("measured settling ~ 4 / (z wn)",
      approx(m.settling_time, settling_time(Z, WN), 0.15))
check("overshoot depends on zeta ALONE, not on wn",
      approx(step_metrics(*step_response(second_order(80.0, Z), 0.4,
                                         2e-5)).overshoot,
             m.overshoot, 5e-3))
check("zeta_from_overshoot inverts overshoot_fraction",
      approx(zeta_from_overshoot(overshoot_fraction(0.42)), 0.42, 1e-9))
check("zeta = 0.707 is exactly where the resonant peak vanishes",
      resonant_peak_db(0.708) == 0.0 and resonant_peak_db(0.70) > 0.0)
check("critically damped does not overshoot",
      step_metrics(*step_response(second_order(10.0, 1.0), 2.0,
                                  2e-4)).overshoot < 1e-3)
check("a pure second-order plant also has no critical gain",
      math.isinf(critical_gain(second_order(10.0, 0.5))))
check("J,K,B -> wn,zeta  (K=100, B=4, J=0.25 -> 20, 0.4)",
      np.allclose(joint_wn_zeta(100.0, 4.0, 0.25), (20.0, 0.4)))

# -- the frequency-domain face of zeta --------------------------------------
check("Q = 1/(2 zeta), and it IS the gain at wn",
      approx(quality_factor(0.05), 10.0)
      and approx(abs(second_order(1.0, 0.05).response(1.0)), 10.0, 1e-9))
check("the resonant peak sits at wn sqrt(1 - 2 z^2)",
      approx(resonant_frequency(0.3, 1.0), math.sqrt(1 - 2 * 0.09), 1e-12))
check("...and there is NO peak at or above zeta = 1/sqrt(2) exactly",
      resonant_frequency(1 / math.sqrt(2), 1.0) == 0.0
      and resonant_frequency(0.9, 1.0) == 0.0
      and resonant_frequency(0.7, 1.0) > 0.0)
check("the peak does not vanish abruptly -- it slides down to DC and "
      "flattens: w_r -> 0 and M_r -> 0 dB as zeta -> 1/sqrt(2)",
      resonant_frequency(0.7070, 1.0) < 0.02
      and resonant_peak_db(0.7070) < 0.001
      and resonant_frequency(0.70, 1.0) > 0.1)
check("the peak found numerically matches the formula",
      (lambda z: approx(
          max(((abs(second_order(1.0, z).response(0.2 + 0.002 * i)), 0.2 + 0.002 * i)
               for i in range(900)))[1],
          resonant_frequency(z, 1.0), 3e-3))(0.35))
check("M_r formula matches the numerically found peak height",
      (lambda z: approx(
          20 * math.log10(max(abs(second_order(1.0, z).response(0.2 + 0.002 * i))
                              for i in range(900))),
          resonant_peak_db(z), 1e-3))(0.35))
check("the three frequencies are ordered w_r < w_d < w_n, strictly",
      all(resonant_frequency(z, 1.0) < damped_frequency(z, 1.0) < 1.0
          for z in (0.1, 0.3, 0.5, 0.7)))
check("phase is exactly -90 deg at wn, for EVERY zeta",
      all(approx(math.degrees(np.angle(second_order(1.0, z).response(1.0))),
                 -90.0, 1e-9)
          for z in (0.05, 0.2, 0.5, 0.707, 1.0, 3.0)))
check("bandwidth ~ wn at zeta = 0.707 (why that value is the default)",
      approx(bandwidth_second_order(0.7071, 1.0), 1.0, 2e-3),
      bandwidth_second_order(0.7071, 1.0))
check("bandwidth is the -3 dB point it claims to be",
      all(approx(20 * math.log10(abs(second_order(1.0, z).response(
          bandwidth_second_order(z, 1.0)))), -3.0103, 1e-3)
          for z in (0.2, 0.5, 0.707, 1.5)))
check("doubling K alone LOWERS zeta by sqrt(2)",
      approx(joint_wn_zeta(200.0, 4.0, 0.25)[1],
             joint_wn_zeta(100.0, 4.0, 0.25)[1] / math.sqrt(2), 1e-9))


# ==========================================================================
print("\n[3] Stability -- Routh must agree with the roots, always")

check("integrator is marginal", classify_stability([1, 0]) == "marginal")
check("undamped oscillator is marginal", classify_stability([1, 0, 4])
      == "marginal")
check("a RHP root is unstable", classify_stability([1, -2]) == "unstable")
check("routh: s^3+3s^2+2s+1 is stable", routh_rhp_count([1, 3, 2, 1]) == 0)
check("routh: s^3+3s^2+2s+12 has 2 RHP poles",
      routh_rhp_count([1, 3, 2, 12]) == 2)
check("routh agrees with root finding on 40 random polynomials",
      all(routh_rhp_count(list(c))
          == sum(1 for r in poly_roots(list(c)) if r.real > 1e-9)
          for c in [np.random.RandomState(k).rand(4) + 0.1 for k in range(40)]))
check("the textbook result: K/(s(s+1)(s+2)) goes unstable at K = 6",
      approx(critical_gain(TF([1.0], [1.0, 3.0, 2.0, 0.0])), 6.0, 1e-3))
check("...and 1/(s+1)^3 at K = 8",
      approx(critical_gain(TF([1.0], [1.0, 3.0, 3.0, 1.0])), 8.0, 1e-2))


# ==========================================================================
print("\n[4] Bode margins -- checked against hand-computable cases")

mg = margins(TF([1.0], [1.0, 1.0, 0.0]))          # 1/(s(s+1))
check("PM of 1/(s(s+1)) = 51.83 deg",
      approx(mg.phase_margin_deg, 51.827, 0.05), mg.phase_margin_deg)
check("...at w_gc = 0.7862 rad/s", approx(mg.wgc, 0.78615, 1e-3), mg.wgc)
check("...with infinite gain margin (phase never reaches -180)",
      mg.gain_margin_db > 100)

mg2 = margins(TF([6.0], [1.0, 3.0, 2.0, 0.0]))    # exactly critical
check("GM = 0 dB at the critical gain", abs(mg2.gain_margin_db) < 0.02,
      mg2.gain_margin_db)
check("...at w_pc = sqrt(2)", approx(mg2.wpc, math.sqrt(2), 1e-3), mg2.wpc)

check("PM(zeta) formula matches the ~100*zeta rule of thumb",
      abs(phase_margin_of_zeta(0.45) - 45.0) < 4.0,
      phase_margin_of_zeta(0.45))
check("PM(0.707) = 65 deg", abs(phase_margin_of_zeta(0.707) - 65.0) < 1.0,
      phase_margin_of_zeta(0.707))

L = TF([20.0], [1.0, 1.0, 0.0])
base = margins(L)
DELAY = 0.02
delayed = margins_with_delay(L, DELAY)
check("delay leaves the gain crossover where it was",
      approx(delayed.wgc, base.wgc, 1e-6))
check("delay removes exactly w_gc * T_d of phase margin",
      approx(delayed.phase_margin_deg,
             base.phase_margin_deg - math.degrees(base.wgc * DELAY), 1e-6),
      (base.phase_margin_deg, delayed.phase_margin_deg))


# ==========================================================================
print("\n[5] Nyquist -- encirclement count vs the actual closed-loop poles")


def z_from_poles(loop):
    return sum(1 for r in loop.feedback().poles() if r.real > 1e-9)


for name, loop, p_rhp in (
        ("stable 3-pole", TF([1.0], [1.0, 3.0, 3.0, 1.0]), 0),
        ("K=20 on 1/(s+1)^3", TF([20.0], [1.0, 3.0, 3.0, 1.0]), 0),
        ("1/(s(s+1)) -- has an integrator", TF([1.0], [1.0, 1.0, 0.0]), 0),
        ("12/(s(s+1)(s+2))", TF([12.0], [1.0, 3.0, 2.0, 0.0]), 0),
        ("3/(s(s+1)(s+2))", TF([3.0], [1.0, 3.0, 2.0, 0.0]), 0)):
    n = encirclements(loop)
    check(f"Z = N + P holds for {name}",
          n + p_rhp == z_from_poles(loop), (n, p_rhp, z_from_poles(loop)))

check("vector margin is small when the curve passes close to -1",
      vector_margin(TF([5.5], [1.0, 3.0, 3.0, 1.0])) < 0.4,
      vector_margin(TF([5.5], [1.0, 3.0, 3.0, 1.0])))
check("...and healthy for a gentle loop",
      vector_margin(TF([0.5], [1.0, 3.0, 3.0, 1.0])) > 0.5)


# ==========================================================================
print("\n[6] Compensators")

check("lead phi_max(alpha=10) = 54.9 deg",
      abs(lead_phase_deg(10.0) - 54.9) < 0.1, lead_phase_deg(10.0))
check("lead phase peaks exactly at w_max",
      abs(math.degrees(np.angle(lead(10.0, 10.0).response(10.0)))
          - lead_phase_deg(10.0)) < 0.2)
check("alpha_for_phase inverts lead_phase_deg",
      approx(lead_phase_deg(alpha_for_phase(45.0)), 45.0, 1e-6))
check("a lead raises the phase margin of a joint loop",
      margins(TF([80.0], [0.25, 0.4, 0.0]) * lead(20.0, 6.0)
              ).phase_margin_deg
      > margins(TF([80.0], [0.25, 0.4, 0.0])).phase_margin_deg)
check("the realistic PID is proper; the ideal one is not",
      len(pid_tf(10, 5, 2, 0.01).num) <= len(pid_tf(10, 5, 2, 0.01).den)
      and len(pid_tf(10, 5, 2).num) > len(pid_tf(10, 5, 2).den))
check("ideal PID at s=j: Kp + j(Kd - Ki)",
      abs(pid_tf(10, 5, 2).response(1.0) - (10 + 1j * 2 - 1j * 5)) < 1e-9)

locus = root_locus(TF([1.0], [1.0, 3.0, 2.0]), [1e-9])
check("the root locus starts at the open-loop poles",
      all(min(abs(r - p) for p in (-1.0, -2.0)) < 1e-6 for r in locus[0]))


# ==========================================================================
print("\n[7] State feedback and observers")

A = np.array([[0.0, 1.0], [0.0, 0.0]])
B = np.array([[0.0], [1.0]])
C = np.array([[1.0, 0.0]])

K = place_poles(A, B, [-2, -2])
check("Ackermann on the double integrator gives K = [4, 4]",
      np.allclose(K, [[4.0, 4.0]]), K)
check("the placed poles are where they were asked for",
      np.allclose(sorted(np.linalg.eigvals(A - B @ K).real), [-2.0, -2.0]))
check("LQR on the double integrator with Q=I, R=1 gives [1, sqrt(3)]",
      np.allclose(lqr(A, B, np.eye(2), np.array([[1.0]])),
                  [[1.0, math.sqrt(3)]], atol=1e-6))
check("a bigger R (dearer torque) always gives a smaller gain",
      lqr(A, B, np.eye(2), np.array([[100.0]]))[0, 0]
      < lqr(A, B, np.eye(2), np.array([[1.0]]))[0, 0])
check("the double integrator is controllable", is_controllable(A, B))
check("...and observable from position alone", is_observable(A, C))
check("a mode the actuator cannot reach is uncontrollable",
      not is_controllable(np.array([[-1.0, 0.0], [0.0, -2.0]]),
                          np.array([[1.0], [0.0]])))
L = observer_gain(A, C, [-10, -10])
check("duality places the observer error poles correctly",
      np.allclose(sorted(np.linalg.eigvals(A - L @ C).real), [-10.0, -10.0]))

tr = run_velocity_observer(duration=1.0, noise=3e-4, obs_bw=50.0)
n = len(tr.omega)
sk = int(n * 0.2)


def _mae(a, b):
    return sum(abs(x - y) for x, y in zip(a[sk:], b[sk:])) / (n - sk)


check("the observer beats finite differencing under encoder noise",
      _mae(tr.omega_hat, tr.omega) < _mae(tr.omega_fd, tr.omega) / 5,
      (_mae(tr.omega_fd, tr.omega), _mae(tr.omega_hat, tr.omega)))
trd = run_velocity_observer(duration=3.0, noise=1e-4, obs_bw=25.0,
                            tau_ext=2.0, estimate_disturbance=True)
check("the disturbance observer recovers an unmeasured 2 N*m load",
      abs(trd.tau_hat[-1] - 2.0) < 0.15, trd.tau_hat[-1])


# ==========================================================================
print("\n[8] Nonlinear -- the pendulum's three faces")

P = Pendulum(m=1.0, l=0.5, b=0.15)
MGL = P.m * P.g * P.l

check("hanging linearises to a stable pair",
      all(v.real < 0 for v in P.linear_poles(0.0)))
check("inverted linearises to a RIGHT half plane pole",
      any(v.real > 0 for v in P.linear_poles(math.pi)))
check("horizontal linearises to a double integrator (pole at 0)",
      any(abs(v.real) < 1e-9 for v in P.linear_poles(math.pi / 2)))
check("the inverted pole is sqrt(g/l)",
      approx(P.unstable_pole_inverted(), math.sqrt(9.81 / 0.5), 1e-12))
check("a free pendulum loses energy and settles hanging",
      (lambda r: P.energy(r[1][-1], r[2][-1]) < 0.02 * P.energy(2.0, 0.0)
       and abs(r[1][-1]) < 0.05)(trajectory(P, 2.0, 0.0, duration=20.0)))
check("the period grows with amplitude (superposition is gone)",
      large_angle_period(P, math.radians(90))
      > 1.15 * large_angle_period(P, math.radians(5)))
check("the separatrix closes exactly at the inverted equilibrium",
      min(abs(u) for t_, u in zip(*separatrix(P)[:2])
          if abs(abs(t_) - math.pi) < 0.02) < 1e-6)


# ==========================================================================
print("\n[9] Nonlinear control -- who survives a wrong model")

TGT = math.pi / 2          # horizontal: gravity torque is at its maximum


def final_error(law, dur=5.0):
    _, th, _, _ = trajectory(P, TGT, 0.0, duration=dur, dt=1e-3, tau_fn=law)
    return abs(th[-1] - TGT)


e_pd = final_error(pd_controller(30.0, 4.0, theta_d=TGT))
check("plain PD holds a standing gravity error",
      approx(e_pd, MGL * math.sin(TGT - e_pd) / 30.0, 0.01), e_pd)
check("gravity compensation removes it",
      final_error(gravity_comp_pd(P, 30.0, 4.0, theta_d=TGT)) < 1e-3)
check("computed torque with an exact model is exact",
      final_error(computed_torque(P, 100.0, 20.0,
                                  traj_fn=lambda t: (TGT, 0.0, 0.0))) < 1e-6)

e_ct = final_error(computed_torque(P, 100.0, 20.0, model_error=-0.30,
                                   traj_fn=lambda t: (TGT, 0.0, 0.0)))
e_sm = final_error(sliding_mode(P, lam=10.0, eta=12.0, boundary=0.01,
                                theta_d=TGT, model_error=-0.30))
check("computed torque degrades in proportion to model error", e_ct > 5e-3,
      e_ct)
check("sliding mode is far more robust to the same error", e_sm < e_ct / 5,
      (e_ct, e_sm))
check("gain-scheduled PD reaches the inverted equilibrium",
      (lambda r: abs(r[1][-1] - math.pi) < 0.05)(
          trajectory(P, 0.5 * math.pi, 0.0, duration=4.0,
                     tau_fn=gain_scheduled_pd(P, wn=8.0, zeta=0.8))))

SU = Pendulum(m=1.0, l=0.5, b=0.06)
ts, th, w, tau = trajectory(
    SU, 0.05, 0.0, duration=18.0, dt=3e-3, tau_limit=60.0,
    tau_fn=energy_swingup(SU, k_e=1.5, tau_limit=0.35 * MGL, catch=0.5,
                          kp=45.0, kd=9.0))
fin = math.atan2(math.sin(th[-1]), math.cos(th[-1]))
check("energy shaping inverts the pendulum with 35% of the torque needed to "
      "lift it", abs(abs(fin) - math.pi) < 0.15, fin)
swing = [abs(x) for x, t_ in zip(tau, th)
         if abs(t_ - (math.pi + 2 * math.pi
                      * round((t_ - math.pi) / (2 * math.pi)))) >= 0.5]
check("...and never exceeded the pump limit while swinging",
      max(swing) <= 0.35 * MGL + 1e-9, max(swing))


# ==========================================================================
print("\n[10] Limit cycles and nonlinear elements")

lc = run_stick_slip(duration=12.0)
half = slice(int(len(lc.theta) * 0.5), None)
slips = sum(1 for a, b in zip(lc.stuck[half], lc.stuck[half][1:]) if a != b)
check("stiction + integral action gives a sustained limit cycle", slips >= 4,
      slips)
check("...with a visible amplitude",
      (max(lc.theta[half]) - min(lc.theta[half])) > 0.05)
dz = run_stick_slip(ki=0.0, duration=12.0)
tail = dz.theta[int(len(dz.theta) * 0.5):]
check("without integral action it sticks off-target for good, inside the "
      "f_s/Kp dead zone",
      (max(tail) - min(tail)) < 1e-6 and 1e-3 < abs(tail[-1] - 0.5)
      <= 6.0 / 20.0 + 1e-6, (max(tail) - min(tail), tail[-1]))

check("saturation clips", saturation(9.0, 2.0) == 2.0)
check("deadzone kills small inputs and shifts large ones",
      deadzone(0.05, 0.1) == 0.0 and approx(deadzone(0.3, 0.1), 0.2))
check("coulomb friction opposes the motion",
      coulomb_friction(2.0, 1.5) == -1.5 and coulomb_friction(-2.0, 1.5) == 1.5)
check("backlash holds inside the gap",
      backlash(0.02, 0.0, 0.1) == 0.0 and approx(backlash(0.5, 0.0, 0.1), 0.45))
check("describing function is 1 below the limit and falls above it",
      describing_function_saturation(0.5, 1.0) == 1.0
      and describing_function_saturation(5.0, 1.0) < 0.3)
check("Lyapunov V > 0 and Vdot <= 0",
      lyapunov_pd_pendulum(P, 30.0, math.pi, 2.0, 1.0) > 0
      and lyapunov_rate(P, 5.0, 1.3) < 0)


# ==========================================================================
print("\n" + "=" * 62)
if FAILS:
    print(f"  {len(FAILS)} FAILED: " + ", ".join(FAILS))
    sys.exit(1)
print("  all linear/nonlinear checks passed")
sys.exit(0)
