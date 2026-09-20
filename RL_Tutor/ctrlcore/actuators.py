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

    Between those two limits sit a resonance PAIR, and this is where the
    plot gets interesting:

        omega_a = sqrt(k / J_m)                    ANTIRESONANCE, J_eff -> inf
                  The motor-on-spring rings and acts as a tuned mass damper,
                  pinning the load. `math.inf` is returned exactly there;
                  real damping keeps it finite but large.

        omega_r = sqrt(k (J_m + J_L) / (J_m J_L))  RESONANCE, J_eff = 0
                  The two masses swing against each other. The load moves
                  for almost no applied torque.

    Between omega_a and omega_r, J_eff computes NEGATIVE. That is not a
    magic material. Dividing torque by s^2 theta expresses every impedance
    as an "equivalent inertia", and a negative answer simply means the
    driving-point impedance in that band is dominated by STIFFNESS rather
    than by mass -- the force leads the displacement instead of lagging it.
    It is a bookkeeping artifact of the units, not negative mass.
    """
    denom = k - j_m * omega * omega
    if abs(denom) < 1e-12:
        return math.inf
    return j_l + k * j_m / denom


def sea_antiresonance_rad_s(k: float, j_m: float) -> float:
    r"""
    LOAD-SIDE ANTIRESONANCE:  omega_a = sqrt(k / J_m)

    The motor-on-its-spring is a mass-spring oscillator in its own right, and
    this is its natural frequency. At exactly this frequency it acts as a
    tuned mass damper on the load: push the load here and the motor-spring
    pair absorbs the motion and pins it. J_eff -> infinity.

    This is a LOAD-SIDE phenomenon. It answers "what happens if the WORLD
    shakes the joint?", not "how fast can I command the motor?".
    """
    if j_m <= 0 or k <= 0:
        return 0.0
    return math.sqrt(k / j_m)


def sea_resonance_rad_s(k: float, j_m: float, j_l: float) -> float:
    r"""
    SYSTEM RESONANCE:  omega_r = sqrt( k (J_m + J_L) / (J_m J_L) ) = sqrt(k/mu)

    where mu = J_m J_L / (J_m + J_L) is the reduced inertia. This is the two
    masses swinging against each other through the spring. Here J_eff = 0:
    the load can be moved with almost no effort, because the spring and the
    inertia cancel.

    Always ABOVE the antiresonance. Between the two, the load-side J_eff is
    negative -- see `j_eff_sea` for what that actually means.
    """
    if j_m <= 0 or j_l <= 0 or k <= 0:
        return 0.0
    return math.sqrt(k * (j_m + j_l) / (j_m * j_l))


def sea_transmissibility(k: float, j_l: float, omega: float) -> float:
    r"""
    MOTOR-SIDE BANDWIDTH, as a magnitude:

        theta_L / theta_m = k / (k - J_L omega^2)

    Hold the motor under stiff position control and wiggle it. How much of
    that motion reaches the load? Below sqrt(k/J_L), all of it. Above, the
    spring absorbs the motion and the load stops following: the response
    rolls off as 1/omega^2.

    THIS is the number that limits trajectory tracking and force control.
    It is a different question, with a different answer, from the load-side
    antiresonance above -- which is the single most common confusion about
    series elastic actuators.
    """
    denom = k - j_l * omega * omega
    if abs(denom) < 1e-12:
        return math.inf
    return abs(k / denom)


def sea_deflection_ratio(j_m: float, k: float, omega: float) -> float:
    r"""
    How much the spring is actually bending, per radian of load motion:

        (theta_m - theta_L) / theta_L = -J_m omega^2 / (k + J_m s^2)
        magnitude = J_m omega^2 / |k - J_m omega^2|

    The answer to "at low frequency, is the spring deflecting at all?"

    It is -- but only by omega^2, so at low frequency the deflection is
    nearly zero. The spring bends by exactly the amount needed to generate
    the force that accelerates the rotor, and no more. The motor really is
    rotating down there, which is precisely why you feel J_m + J_L.

    At high frequency the rotor cannot be accelerated, the ratio grows past
    1, and the spring takes essentially all of the relative motion.
    """
    denom = abs(k - j_m * omega * omega)
    if denom < 1e-12:
        return math.inf
    return j_m * omega * omega / denom


def sea_bandwidth_hz(k: float, j_l: float) -> float:
    r"""
    Natural frequency of the spring-load pair, in Hz.

        f_n = (1 / 2pi) * sqrt(k / J_l)

    Historical API name retained for compatibility. This computes the
    imposed-motor-angle resonance, NOT a closed-loop -3 dB bandwidth.
    Controller, damping, sensing and boundary conditions determine the latter.
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
                       Shake it fast and the spring's k*theta torque is
                       negligible beside the inertial J*omega^2*theta term.
                       You feel the FULL machine, rotor included.

                       A PEA therefore gives NO impact protection. This is
                       the single biggest difference from an SEA, which
                       drops to J_l up here. The spring is rigid-in-effect
                       during an impact not because it is stiff, but because
                       there is no time for it to matter.

        omega = sqrt(k / (J_m + J_l))    J_eff = 0
                       Resonance. Spring and inertia torques cancel exactly
                       and the joint can be moved with almost no effort.

        omega -> 0     J_eff -> large and NEGATIVE
                       Read this one carefully, because the arithmetic
                       invites a wrong story. It does NOT mean the joint has
                       negative mass or spontaneously accelerates.

                       Dividing everything by s^2 theta forces a spring into
                       inertia units, and a spring's impedance carries the
                       opposite sign to a mass's. So "J_eff < 0" says only:
                       BELOW RESONANCE THIS JOINT FEELS LIKE A SPRING, NOT
                       LIKE A MASS. Push it slowly and what pushes back is
                       stiffness. If that spring was sized against gravity,
                       the stiffness is holding the limb up so the motor
                       does not have to.

                       The honest engineering statement is about torque, not
                       inertia -- see `motor_torque_pea`.
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
        force     F ~ L^2     (fixed allowable stress, similar geometry)
        torque  tau ~ L^3     (force capacity times moment arm)
        gravity tau ~ L^4     (weight times moment arm)
        inertia   J ~ L^5     (mass * length^2  =  L^3 * L^2)

    Torque capacity grows slower than gravity torque demand, and inertia grows
    faster than anything. A big robot is relatively weaker AND relatively
    lazier than a small one. That is why a quadruped can run on quasi-direct
    drive while a human-sized humanoid is pushed toward high gear ratios --
    and therefore toward all the reflected-inertia problems above.
    """
    L = length_ratio
    return {
        "length": L,
        "mass": L ** 3,
        "force": L ** 2,
        "torque": L ** 3,
        "gravity_torque": L ** 4,
        "capacity_to_gravity": 1 / L if L else 0.0,
        "inertia": L ** 5,
        # torque available per unit of weight to be carried
        "torque_per_mass": 1.0 if L else 0.0,
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
