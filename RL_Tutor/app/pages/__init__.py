"""
Page registry. The order below IS the sidebar order, and page numbers are
assigned from it automatically -- so reordering this list renumbers everything
and no TITLE string ever has to be edited.

The tutor is in two halves. The first half is the physical machine: what the
world feels when it touches the robot, and how a controller can shape that.
The second half is reinforcement learning: how a policy is found for a machine
whose dynamics you now understand.

CONTROL & DYNAMICS
     1     real-time control -- why your loop rate is not your bandwidth
     2     the control problem: what we are doing, and what "order" is for
     3-4   where a plant's numbers come from, and how software moves them
     5-9   first order, slowly: what it is, tau and the pole, the integrator,
           frequency, the s-plane
    10     free vibration -- the homogeneous solution from (x0, v0), and why
           the peak is a hypotenuse rather than x0
    11-14  second order, stability, Bode margins, Nyquist
    15     zeros -- the other dot on the map, and the destination poles head for
    16-20  controller design: stabilising, lead/lag, state feedback, LQR,
           observers
    21-22  CAPSTONE -- the biped and the arm, in the language of poles,
           margins and gains
    23-24  nonlinear systems, and the six things people do about them
    25-29  actuator mechanics -- effective inertia, SEA, PEA, gearing
    30-31  CAPSTONE -- an actuator for every joint of both machines
    32-39  the four control paradigms, ending in the one spectrum they share
    40-41  CAPSTONE -- which controller, which joint, which phase
    42-44  choosing a drivetrain for a real robot, and one case study
    45-47  proprioception: transparency, internal force sensing, active compliance
    48-49  positive force feedback, and the honesty test for claiming it
    50-51  translating human biomechanics into robot design

Page 10 comes before second order because the four pages after it all quote
the same function of time. Solving  m x'' + c x' + k x = 0  once, properly,
from initial conditions, turns the step response into "1 minus that", the
swept sine into "a sine at the drive frequency plus that", and the overshoot
formula into a line of calculus rather than a thing to memorise.

The three CAPSTONE pairs are the point of the whole structure. A block of
theory that is never spent on a specific machine does not stick, so each
block ends by spending itself twice -- once on a trunkless biped with six
actuators, once on a three-joint manipulator. The two robots are fixed
throughout so that the answers can be compared, and they disagree often
enough to be worth the space.

REINFORCEMENT LEARNING
    52-58  the environment felt by hand, then the vocabulary and the MDP
    59-62  how to measure how good a square is
    63-66  the four Bellman equations, one page each, in full arithmetic
    67-71  compute the perfect policy, given that we know the ice
    72-74  learn it WITHOUT knowing the ice -- what a real robot must do
    75-80  the surrounding ideas

NEURAL NETWORKS
    81-86  a neuron, the activations and their slopes, forward propagation,
           backpropagation (multiply along a path, SUM across paths), what a
           loss is actually for, and the housekeeping -- L2, dropout, batch
           versus layer norm, initialisation, clipping

DEEP RL & CONTINUOUS CONTROL
    87     tables run out: continuous states kill the table, continuous
           actions kill the argmax
    88     actor-critic, and deterministic mu(s) versus stochastic pi(a|s)
    89     DDPG: four networks, three equations
    90     the gradient handoff: dQ/da is the SEED of the actor's backward
           pass, not a target for its output
    91     inside the critic: two inputs of different kinds, and what the
           merge point does to dQ/da
    92     it is still an MDP; and what separates DDPG from TD3, SAC, PPO
    93     one rulebook -- Experience, StepResult, Env, ReplayBuffer, act():
           what every agent shares, and the two places PPO refuses to fit
    94     case study -- learning the impedance of a knee prosthesis, where
           one gait cycle is one timestep
    95     shipping it: a 1 kHz controller and a 20 Hz learner sharing memory

ROBOT MECHANICS
   114-118 configuration space, constraints, SO(3), SE(3), twists, wrenches
   119-124 forward kinematics (PoE), Jacobian, statics, IK, null space,
           closed chains
   125-131 dynamics: Lagrange, M(q), Newton-Euler, inverse and forward
           dynamics, task-space dynamics, constrained dynamics
   132-134 time scaling, time-optimal scaling, motion planning
   135-137 computed torque, operational space + null space, force control
   138-140 grasping, wheeled mobile robots, interview drill

The mechanics block is appended rather than inserted so that every earlier
page keeps its number. It derives the plant the control half assumed: where
M(q), c, g and J come from, following the twelve Modern Robotics playlists.

The last block closes the loop the tutor opened. Pages 1-51 built a compliant
joint and said what its impedance parameters mean; 52-80 built the machinery
for learning from experience; 81-86 use the second to choose the first, and
then put the result in two real-time tasks without missing a deadline.

Real-time comes first on purpose. Every later page makes a claim about how
fast something can respond, and every one of those claims is bounded by the
sampling, delay and scheduling facts established on page 1.

Page 2 is an orientation page and derives nothing. It exists because "is it
first order or second order?" is a useless question until you know what the
answer will be used for, and because the same hardware having different orders
for different outputs needs saying out loud before it is relied on.

The linear-systems and controller-design blocks follow immediately, because
"bandwidth", "damping" and "phase margin" are used as load-bearing terms from
the actuator pages onwards, and none of them means anything until you can see
a pole move. The nonlinear pages then say out loud what those two blocks were
assuming -- which is exactly the assumption a real robot breaks.
"""

from .capstone import (
    ArmActuatorsPage,
    ArmControlPage,
    ArmSystemsPage,
    BipedActuatorsPage,
    BipedControlPage,
    BipedSystemsPage,
)
from .ctrldesign import (
    LeadLagPage,
    ObserverPage,
    StabilisingPage,
)
from .statefb import LQRPage, StateFeedbackPage
from .orient import ControlProblemPage
from .plant import MeasuringPage, SoftwarePhysicsPage
from .firstorder import (
    FirstOrderFreqPage,
    FirstOrderPage,
    IntegratorPage,
    SPlanePage,
    TimeConstantPage,
)
from .linsys import (
    BodePage,
    FreeVibrationPage,
    NyquistPage,
    SecondOrderPage,
    StabilityPage,
)
from .zeros import ZerosPage
from .nonlin import NonlinearControlPage, NonlinearSystemsPage
from .beambalance import (
    BeamAdmittancePage,
    BeamControllerPage,
    BeamEstimationPage,
    BeamFrequencyPage,
    BeamMeasuringPage,
    BeamPlantPage,
    BeamRealTimePage,
    BeamResultsPage,
    BeamStabilityPage,
)
from .faulttol import (
    FaultCompensationPage,
    FaultDetectionPage,
    FaultEstimationPage,
    FaultFSMPage,
    FaultLatencyPage,
    FaultPlantPage,
    FaultRealTimePage,
    FaultResultsPage,
    FaultStabilityPage,
)
from .robo_space import (
    ConstraintsPage,
    CSpacePage,
    RoboRoadmapPage,
    RotationsPage,
    TwistsPage,
)
from .robo_kin import (
    ClosedChainPage,
    IKPage,
    JacobianPage,
    NullSpacePage,
    PoEPage,
    StaticsPage,
)
from .robo_dyn import (
    ConstrainedDynamicsPage,
    ForwardDynamicsPage,
    InverseDynamicsPage,
    LagrangePage,
    MassMatrixPage,
    NewtonEulerPage,
    TaskDynamicsPage,
)
from .robo_ctrl import (
    ForceControlPage,
    GraspingPage,
    InterviewDrillPage,
    MobileRobotPage,
    MotionControlPage,
    MotionPlanningPage,
    OperationalSpacePage,
    TimeOptimalPage,
    TimeScalingPage,
)
from .bellman import (
    BellmanExpQPage,
    BellmanExpVPage,
    BellmanOptQPage,
    BellmanOptVPage,
)
from .biodesign import BioActuationPage, BioStructurePage
from .design import ActuatorChoicePage, NeoPage, ScalingPage
from .dp_pages import (
    CompareDPPage,
    PolicyEvalPage,
    PolicyImprovePage,
    PolicyIterationPage,
    ValueIterationPage,
)
from .deeprl import (
    ActorCriticPage,
    DDPGPage,
    DeployRLPage,
    FunctionApproxPage,
    KneeRLPage,
    MDPandFamilyPage,
)
from .extras import BanditPage, ConvergencePage, HyperPage, ModelPage
from .forcefb import PFFIntroPage, PFFMathPage
from .foundations import MDPPage, PolicyPage
from .frozenlake import FrozenLakePage, TransitionsPage
from .intro import ReturnPage, RewardPage, WhatIsRLPage
from .lab import AdamPage, CodeLabPage
from .nn import (
    ActivationPage,
    BackpropPage,
    ForwardPropPage,
    LossPage,
    NeuronPage,
    RegularisationPage,
)
from .ddpgnn import AgentSkeletonPage, CriticArchPage, GradientHandoffPage
from .mc_pages import MCControlPage, MCIntroPage, MCPredictionPage
from .motors import (
    ActuatorCompare,
    EffectiveInertiaPage,
    GearingPage,
    PEAPage,
    SEAPage,
)
from .paradigms import (
    AdmittanceControlPage,
    GoalOfControlPage,
    ImpedanceControlPage,
    ImpVsAdmPage,
    PositionControlPage,
    SpectrumPage,
    TorqueControlPage,
)
from .pid import PIDPracticePage
from .realtime import RealTimePage
from .proprio import ActiveCompliancePage, BioProprioPage, RobotProprioPage
from .values import ActionValuePage, BellmanPage, StateValuePage, VvsQPage

PAGE_CLASSES = [
    # ======================================================================
    # CONTROL & DYNAMICS
    # ======================================================================
    # ---- Real-time: the constraint every later claim is bounded by --------
    RealTimePage,          # 1   sampling, Nyquist, jitter, scheduling
    # ---- Linear systems: what "pole", "damping" and "margin" mean ---------
    ControlProblemPage,    # 2   what we are doing, and what "order" is for
    MeasuringPage,         # 3   where J, b and k actually come from
    SoftwarePhysicsPage,   # 4   how a gain changes an equation of motion
    FirstOrderPage,        # 5   one store, one drain -- and what that buys you
    TimeConstantPage,      # 6   tau, 0.63, and the pole as a decay rate
    IntegratorPage,        # 7   the pole at s = 0: a store with no drain
    FirstOrderFreqPage,    # 8   the corner, -3 dB, and the 90 deg ceiling
    SPlanePage,            # 9   what j is; the second store that lifts a pole
    FreeVibrationPage,     # 10  x0 cos + (v0/wn) sin, and A as a hypotenuse
    SecondOrderPage,       # 11  wn and zeta, and every joint you will tune
    StabilityPage,         # 12  LHP, marginal, Routh-Hurwitz
    BodePage,              # 13  gain and phase margin, and PM = damping
    NyquistPage,           # 14  the -1 point, encirclements, vector margin
    ZerosPage,             # 15  what a zero is: blocked inputs, wrong-way steps
    # ---- Controller design: moving the poles on purpose -------------------
    StabilisingPage,       # 16  root locus, and why D is the term that saves you
    LeadLagPage,           # 17  lead, lag, notch -- and why notches betray you
    StateFeedbackPage,     # 18  what a state is; u = -Kx; place all n poles
    LQRPage,               # 19  name a price instead; Q, R, and P = V(s)
    ObserverPage,          # 20  estimate what you cannot measure; disturbance obs
    # ---- Capstone: everything above, spent on two real machines -----------
    BipedSystemsPage,      # 21  six joints, three unstable eigenvalues
    ArmSystemsPage,        # 22  coupling, configuration, gravity's sign
    # ---- Nonlinear: what all of the above was assuming --------------------
    NonlinearSystemsPage,  # 19  superposition dies; limit cycles, basins
    NonlinearControlPage,  # 20  computed torque, sliding mode, passivity
    # ---- Actuators: what the world actually feels -------------------------
    EffectiveInertiaPage,  # 21  J_eff, and direct drive from first principles
    SEAPage,               # 22  spring between motor and load
    PEAPage,               # 23  spring alongside; what negative J_eff means
    ActuatorCompare,       # 24  torque, speed, inertia, bandwidth head to head
    GearingPage,           # 25  the N^2 square law kills transparency
    # ---- Capstone: an actuator for every joint of both machines -----------
    BipedActuatorsPage,    # 29  ankle vs knee vs hip; impact decides
    ArmActuatorsPage,      # 30  the inertia ordering is upside down
    # ---- Control paradigms: four answers to one question ------------------
    GoalOfControlPage,     # 26  what is a controller even for?
    PositionControlPage,   # 27  command where
    PIDPracticePage,       # 28  anti-windup, D filtering, what jitter breaks
    TorqueControlPage,     # 29  command how hard
    ImpedanceControlPage,  # 30  command the relationship (motion in, force out)
    AdmittanceControlPage, # 31  command the relationship the other way round
    ImpVsAdmPage,          # 32  the decision, and the hardware that forces it
    SpectrumPage,          # 33  they were all one controller all along
    # ---- Capstone: which controller, which joint, which phase -------------
    BipedControlPage,      # 39  scheduled stiffness across a gait cycle
    ArmControlPage,        # 40  contact is the bit that decides
    # ---- Robot design ------------------------------------------------------
    ActuatorChoicePage,    # 34  humanoid vs biped vs quadruped
    ScalingPage,           # 35  the square-cube law and hybrid actuation
    NeoPage,               # 36  case study: 1X Neo
    # ---- Proprioception -----------------------------------------------------
    BioProprioPage,        # 37  spindles, GTOs, and the timescales
    RobotProprioPage,      # 38  transparency is the prerequisite
    ActiveCompliancePage,  # 39  software-defined compliance, three layers
    # ---- Force feedback -----------------------------------------------------
    PFFIntroPage,          # 40  what positive force feedback actually is
    PFFMathPage,           # 41  closing the loop, and the honesty test
    # ---- Bio -> robot -------------------------------------------------------
    BioActuationPage,      # 42  actuation and sensing
    BioStructurePage,      # 43  skin and bone
    # ======================================================================
    # REINFORCEMENT LEARNING
    # ======================================================================
    # ---- Start Here: the environment, then the vocabulary ----------------
    WhatIsRLPage,          # 44  play it yourself
    FrozenLakePage,        # 45  the board
    TransitionsPage,       # 46  the slippery ice, with real probabilities
    RewardPage,            # 47  what the lake pays you
    ReturnPage,            # 48  a list of rewards -> one number, via gamma
    PolicyPage,            # 49  the thing we are searching for
    MDPPage,               # 50  all five pieces, formally named
    # ---- Value Functions: how good is a square? ---------------------------
    StateValuePage,        # 51
    ActionValuePage,       # 52
    VvsQPage,              # 53
    BellmanPage,           # 54  all four at once -- the summary
    # ---- one page per Bellman equation, in full arithmetic ----------------
    BellmanExpVPage,       # 55  V^pi  expectation
    BellmanExpQPage,       # 56  Q^pi  expectation
    BellmanOptVPage,       # 57  V*    optimality
    BellmanOptQPage,       # 58  Q*    optimality
    # ---- Dynamic Programming: solve it, knowing the ice -------------------
    PolicyEvalPage,        # 59
    PolicyImprovePage,     # 60
    PolicyIterationPage,   # 61
    ValueIterationPage,    # 62
    CompareDPPage,         # 63
    # ---- Monte Carlo: learn it, NOT knowing the ice -----------------------
    MCIntroPage,           # 64
    MCPredictionPage,      # 65
    MCControlPage,         # 66
    # ---- Beyond -----------------------------------------------------------
    BanditPage,            # 67
    ModelPage,             # 68
    HyperPage,             # 69
    ConvergencePage,       # 70
    CodeLabPage,           # 71
    AdamPage,              # 72
    # ---- Neural networks: the machinery the whole deep half is made of ----
    NeuronPage,            # 80  weight = gain, bias = offset, squash between
    ActivationPage,        # 81  every activation, and its DERIVATIVE
    ForwardPropPage,       # 82  the signal crossing the weights, animated
    BackpropPage,          # 83  multiply along a path, sum across paths
    LossPage,              # 84  the loss is a seed; softmax vs argmax
    RegularisationPage,    # 85  L2, dropout, batch vs layer norm, init
    # ---- Deep RL: continuous actions, and one deployed system -------------
    FunctionApproxPage,    # 86  tables die twice: continuous states, then
                           #     continuous actions
    ActorCriticPage,       # 87  critic evaluates, actor acts; mu(s) vs pi(a|s)
    DDPGPage,              # 88  four networks, three equations
    GradientHandoffPage,   # 89  dQ/da is a seed, not a target
    CriticArchPage,        # 90  two inputs, one number, and where they merge
    MDPandFamilyPage,      # 91  still an MDP; DDPG vs TD3 vs SAC vs PPO
    AgentSkeletonPage,     # 92  the shared rulebook, and where PPO breaks it
    KneeRLPage,            # 93  case study: one gait cycle is one timestep
    DeployRLPage,          # 94  1 kHz controller, 20 Hz learner, shared memory
    # ======================================================================
    # APPLIED · BEAM BALANCE -- the mediolateral hip exoskeleton
    # ======================================================================
    BeamRealTimePage,      # 96  1 kHz admittance, 4 kHz drive, 5 Hz bandwidth
    BeamPlantPage,         # 97  three links, frontal plane, H about the foot
    BeamMeasuringPage,     # 98  anthropometry, gearbox, bench identification
    BeamStabilityPage,     # 99  an unstable pole and a 120 ms human
    BeamFrequencyPage,     # 100 the sine sweep and the rendered impedance
    BeamControllerPage,    # 101 the momentum law, term by term
    BeamEstimationPage,    # 102 three IMUs, a reference generator, drift
    BeamAdmittancePage,    # 103 why a 100:1 harmonic drive forces admittance
    BeamResultsPage,       # 104 what the beam said, and what it did not
    # ======================================================================
    # APPLIED · FAULT TOLERANCE -- the robotic knee prosthesis FTM
    # ======================================================================
    FaultRealTimePage,     # 105 a 200 ms fault and a 10 ms persistence test
    FaultPlantPage,        # 106 the sensitive signal and the robust one
    FaultFSMPage,          # 107 FSM impedance, and a wrong parameter set
    FaultDetectionPage,    # 108 residual, threshold, persistence
    FaultStabilityPage,    # 109 a supervisory layer on a working loop
    FaultCompensationPage, # 110 momentum error to additive torque
    FaultEstimationPage,   # 111 Gaussian processes as observers of normal
    FaultLatencyPage,      # 112 43 ms or 103 ms
    FaultResultsPage,      # 113 eight participants, four channels
    # ======================================================================
    # ROBOT MECHANICS -- configuration space, kinematics, dynamics, robot
    # control. One block per Modern Robotics playlist (chapters 2-13).
    # ======================================================================
    # ---- C-space & rigid motion (playlists 1-2) ---------------------------
    RoboRoadmapPage,       # 114 the twelve playlists, and what to master
    CSpacePage,            # 115 dof, Gruebler, the torus
    ConstraintsPage,       # 116 holonomic vs nonholonomic; task vs workspace
    RotationsPage,         # 117 SO(3), Rodrigues, the matrix log
    TwistsPage,            # 118 SE(3), screws, adjoint, wrenches
    # ---- Kinematics (playlists 3-6) ---------------------------------------
    PoEPage,               # 119 product of exponentials
    JacobianPage,          # 120 columns are screw axes; the velocity ellipse
    StaticsPage,           # 121 tau = J^T F, singularities, force ellipse
    IKPage,                # 122 analytic branches, Newton-Raphson, DLS
    NullSpacePage,         # 123 J^+, I - J^+ J, self-motion
    ClosedChainPage,       # 124 four-bar, Stewart, actuator singularities
    # ---- Dynamics (playlist 7) --------------------------------------------
    LagrangePage,          # 125 L = K - P, the 2R equations
    MassMatrixPage,        # 126 M SPD, Christoffel, Mdot - 2C skew
    NewtonEulerPage,       # 127 the O(n) recursion, traced
    InverseDynamicsPage,   # 128 torque from a trajectory, term by term
    ForwardDynamicsPage,   # 129 qdd = M^-1 (tau - h); integrators
    TaskDynamicsPage,      # 130 Lambda, mu, p; the mass the hand feels
    ConstrainedDynamicsPage,  # 131 Lagrange multipliers, contact forces
    # ---- Trajectories & planning (playlists 8-9) --------------------------
    TimeScalingPage,       # 132 cubic, quintic, trapezoid
    TimeOptimalPage,       # 133 the (s, sdot) phase plane
    MotionPlanningPage,    # 134 C-space obstacles, A*, RRT
    # ---- Robot control (playlist 10) --------------------------------------
    MotionControlPage,     # 135 PD + gravity vs computed torque
    OperationalSpacePage,  # 136 OSC and null-space torques
    ForceControlPage,      # 137 hybrid motion/force, task-space impedance
    # ---- Manipulation & mobility (playlists 11-12) ------------------------
    GraspingPage,          # 138 friction cones, force closure
    MobileRobotPage,       # 139 nonholonomic unicycle tracking
    InterviewDrillPage,    # 140 the questions, answered
]

# Stamp each class with its 1-based position. Page headers and the sidebar read
# this, so the numbers can never drift out of sync with the order above.
for _i, _cls in enumerate(PAGE_CLASSES, start=1):
    _cls.NUM = _i

LESSON_CLASSES = tuple(PAGE_CLASSES)
from ..lesson_connections import resolve_connections
CONNECTIONS = resolve_connections(LESSON_CLASSES)
from .section_summaries import with_summaries
PAGE_CLASSES = with_summaries(LESSON_CLASSES)
