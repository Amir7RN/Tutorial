"""
ctrlcore -- the control & dynamics half of the tutor.

Pure Python and maths, no Qt. Everything the control pages display is
computed here, so the GUI can be thrown away and the physics still runs
(and still has tests).

    actuators.py   effective inertia for DD / SEA / PEA, gearing, scaling
    impedance.py   position / torque / impedance / admittance control
    neuro.py       Hill muscle model and positive force feedback
"""

from .actuators import (  # noqa: F401
    TOPOLOGIES,
    TOPOLOGY_NAMES,
    gear_output,
    gravity_torque,
    j_eff,
    j_eff_direct,
    j_eff_pea,
    j_eff_sea,
    j_eff_sweep,
    motor_torque_pea,
    pea_resonance_rad_s,
    reflected_inertia,
    scale_factors,
    sea_bandwidth_hz,
    spring_torque,
)
from .impedance import (  # noqa: F401
    Joint,
    SimTrace,
    VirtualModel,
    equilibrium_angle,
    impedance_magnitude,
    impedance_torque,
    nominal_ankle_angle,
    nominal_ankle_torque,
    run_admittance,
    run_impedance,
    run_position,
    run_torque,
    tau_ff_from_deviation,
    two_controller_demo,
)
from .neuro import (  # noqa: F401
    FORCE_SOURCES,
    PffLoop,
    force_length,
    force_velocity,
    hill_force,
    joint_torque_from_motor,
    loop_gain,
    motor_torque_from_current,
    run_pff,
)
