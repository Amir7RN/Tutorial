r"""
Actuator mechanics: how much inertia the *outside world* feels.

Everything here answers one question in three different ways: if I grab the
output shaft and shake it at frequency omega, how heavy does it feel?

The three topologies, in the notation of the notes:

    J_m   motor (rotor) inertia
    J_l   limb / load inertia
    k     spring stiffness
    omega frequency of interaction

    (1) Direct Drive        motor --------------- load
    (2) Series Elastic      motor --/\/\/\------- load        (spring between)
    (3) Parallel Elastic    motor --------------- load
                              \____/\/\/\____/            (spring alongside)

The derivations live in the docstrings of each function, because the whole
point of the tutor is that the algebra is visible, not hidden.
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------
# (1) Direct drive
# --------------------------------------------------------------------------


def j_eff_direct(j_m: float, j_l: float, omega: float = 0.0) -> float:
    r"""
    Effective inertia of a direct-drive joint.

        J_m * ddot(theta)_m = tau - J_l * ddot(theta)
        (J_m + J_l) * ddot(theta) = tau
        =>  J_eff = J_m + J_l

    There is no spring, so nothing filters anything: the answer does not
    depend on omega at all. Whatever hits the limb hits the rotor too. That
    single fact is both the appeal of direct drive (perfect transparency, the
    motor feels the world) and its danger (a wall collision at speed slams the
    full rotor mass into the wall).

    `omega` is accepted and ignored so all three topologies share a signature.
    """
    return j_m + j_l


# --------------------------------------------------------------------------
# (2) Series elastic actuator
# --------------------------------------------------------------------------


def j_eff_sea(j_m: float, j_l: float, k: float, omega: float) -> float:
    r"""
    Effective inertia seen at the load of a series elastic actuator.

    Spring k sits BETWEEN motor and load, so they are two separate bodies:

        J_m * ddot(theta)_m = -k (theta_m - theta_l)
        J_l * ddot(theta)_l =  k (theta_m - theta_l) + tau_l

    Laplace the first line and solve for the motor angle:

        (J_m s^2 + k) theta_m = k theta_l
        theta_m = k / (k + J_m s^2) * theta_l

    Substitute into the second line and collect:

        [J_l s^2 + k J_m s^2 / (k + J_m s^2)] theta_l = tau_l

        J_eff(s) = J_l + k J_m / (k + J_m s^2)

    On the imaginary axis s = j*omega, so s^2 = -omega^2:

        J_eff(omega) = J_l + k J_m / (k - J_m omega^2)

    The two limits are the entire engineering argument for SEAs:

        omega -> 0    J_eff -> J_l + J_m
                      Slow push. The spring is stiff enough to drag the motor
                      along, so you feel the whole machine.

        omega -> inf  J_eff -> J_l
                      Fast impact. The motor cannot accelerate in time, the
                      spring takes all the relative motion and stores the
                      energy. The environment feels only the light limb --
                      the rotor is mechanically hidden.

    Between them sits omega = sqrt(k / J_m), where the denominator crosses
    zero: the motor-on-spring antiresonance. `math.inf` is returned there;
    physically real damping keeps it finite but large, and it is exactly the
    frequency at which an SEA control loop wants to ring.
    """
    denom = k - j_m * omega * omega
    if abs(denom) < 1e-12:
        return math.inf
    return j_l + k * j_m / denom


def sea_bandwidth_hz(k: float, j_l: float) -> float:
    r"""
    Natural frequency of the spring-load pair, in Hz.

        f_n = (1 / 2pi) * sqrt(k / J_l)

    This is the mechanical low-pass corner. Command the joint faster than
    f_n and the spring simply absorbs the motion instead of passing it to
    the arm. Typical numbers from the notes:

        direct drive   50-100 Hz and up
        SEA            10-20 Hz

    10 Hz is plenty for walking and far too slow for a cat-like reflex or
    for catching a falling object -- which is the trade every humanoid
    designer has to sign.
    """
    if j_l <= 0 or k <= 0:
        return 0.0
    return math.sqrt(k / j_l) / (2.0 * math.pi)


# --------------------------------------------------------------------------
# (3) Parallel elastic actuator
# --------------------------------------------------------------------------


def j_eff_pea(j_m: float, j_l: float, k: float, omega: float) -> float:
    r"""
    Effective inertia of a parallel elastic actuator.

    Here the spring is alongside the motor, so motor and load are still
    rigidly one body and the spring just adds a restoring torque:

        tau_ext = J_l ddot(theta) + J_m ddot(theta) + k theta
                = (J_m + J_l) s^2 theta + k theta

    Divide through by s^2 theta to read off the inertia:

        J_eff(s) = (J_m + J_l) + k / s^2
        J_eff(omega) = (J_m + J_l) - k / omega^2

    Three regimes, and this is the whole PEA story:

        omega -> inf   J_eff -> J_m + J_l
                       Shake it fast and the spring has no time to help.
                       You feel the full machine -- a PEA gives NO impact
                       protection, unlike an SEA.

        omega -> 0     J_eff -> large and NEGATIVE
                       Move slowly and the stored spring torque pushes the
                       load for you. This is gravity compensation: the joint
                       behaves as if it had negative mass, wanting to
                       accelerate on its own.

        omega = sqrt(k / (J_m + J_l))    J_eff = 0
                       Resonance. Spring and inertia cancel exactly and the
                       joint can be moved with almost no effort.
    """
    if omega == 0.0:
        return -math.inf
    return (j_m + j_l) - k / (omega * omega)


def pea_resonance_rad_s(k: float, j_m: float, j_l: float) -> float:
    """Frequency where a PEA's effective inertia passes through zero."""
    tot = j_m + j_l
    if tot <= 0 or k <= 0:
        return 0.0
    return math.sqrt(k / tot)


# --------------------------------------------------------------------------
# Gravity compensation (the reason PEAs exist)
# --------------------------------------------------------------------------


def gravity_torque(mass: float, length: float, theta: float, g: float = 9.81) -> float:
    """
    Gravitational torque on a limb of mass `mass` with its centre of mass at
    `length`, held at angle `theta` from vertical:

        tau_g = m * g * L * sin(theta)

    Zero when the limb hangs straight down, maximum when horizontal.
    """
    return mass * g * length * math.sin(theta)


def spring_torque(k: float, theta: float, theta_0: float) -> float:
    """
    Torque from a linear torsional spring with rest angle `theta_0`:

        tau_s = k * (theta_0 - theta)
    """
    return k * (theta_0 - theta)


def motor_torque_pea(mass, length, k, theta, theta_0, g=9.81) -> float:
    """
    What the motor still has to supply in a PEA:

        tau_m = tau_g(theta) - tau_s(theta)

    Perfect gravity compensation means tau_m = 0, i.e. the spring alone
    holds the pose and the motor draws no current. That only happens at the
    angles where k(theta_0 - theta) = m g L sin(theta) -- a straight line
    trying to match a sine, so it can be exact at a couple of angles and
    only approximate elsewhere. Tune for the pose you hold the longest.
    """
    return gravity_torque(mass, length, theta, g) - spring_torque(k, theta, theta_0)


# --------------------------------------------------------------------------
# Gearing: the square law
# --------------------------------------------------------------------------


def reflected_inertia(j_m: float, ratio: float) -> float:
    r"""
    Rotor inertia as felt at the output shaft through a gear ratio N:

        J_reflected = J_m * N^2

    The square is what kills compliance. At N = 100 the user does not feel a
    slightly heavier arm, they feel the rotor 10,000 times heavier than it
    is. Push on it and nothing moves; the encoder reads zero change; an
    impedance controller concludes nobody is touching the robot.
    """
    return j_m * ratio * ratio


def gear_output(torque: float, speed: float, ratio: float) -> tuple[float, float]:
    """
    Ideal gearbox trade: torque multiplies by N, speed divides by N.
    Returns (output_torque, output_speed).
    """
    return torque * ratio, (speed / ratio if ratio else 0.0)


# --------------------------------------------------------------------------
# Scaling: the square-cube law
# --------------------------------------------------------------------------


def scale_factors(length_ratio: float) -> dict[str, float]:
    r"""
    How the numbers move when you scale a robot up by `length_ratio` in
    every linear dimension.

        mass      m ~ L^3     (volume)
        torque  tau ~ L^2     (cross-sectional area of motor and gear teeth)
        inertia   J ~ L^5     (mass * length^2  =  L^3 * L^2)

    Torque grows slower than the weight it has to lift, and inertia grows
    faster than anything. A big robot is relatively weaker AND relatively
    lazier than a small one. That is why a quadruped can run on quasi-direct
    drive while a human-sized humanoid is pushed toward high gear ratios --
    and therefore toward all the reflected-inertia problems above.
    """
    L = length_ratio
    return {
        "length": L,
        "mass": L ** 3,
        "torque": L ** 2,
        "inertia": L ** 5,
        # torque available per unit of weight to be carried
        "torque_per_mass": L ** 2 / L ** 3 if L else 0.0,
    }


# --------------------------------------------------------------------------
# Topology comparison table used by the GUI
# --------------------------------------------------------------------------

TOPOLOGIES = ("direct", "sea", "pea")

TOPOLOGY_NAMES = {
    "direct": "Direct Drive (DD / QDD)",
    "sea":    "Series Elastic (SEA)",
    "pea":    "Parallel Elastic (PEA)",
}


def j_eff(topology: str, j_m: float, j_l: float, k: float, omega: float) -> float:
    """Dispatch to the right effective-inertia formula."""
    if topology == "direct":
        return j_eff_direct(j_m, j_l, omega)
    if topology == "sea":
        return j_eff_sea(j_m, j_l, k, omega)
    if topology == "pea":
        return j_eff_pea(j_m, j_l, k, omega)
    raise ValueError(f"unknown topology {topology!r}")


def j_eff_sweep(topology, j_m, j_l, k, omegas):
    """Effective inertia over a list of frequencies, for plotting."""
    return [j_eff(topology, j_m, j_l, k, w) for w in omegas]
