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
    10-13  second order, stability, Bode margins, Nyquist
    14     zeros -- the other dot on the map, and the destination poles head for
    15-18  controller design: stabilising, lead/lag, state feedback, observers
    19-20  nonlinear systems, and the six things people do about them
    21-25  actuator mechanics -- effective inertia, SEA, PEA, gearing
    26-33  the four control paradigms, ending in the one spectrum they share
    34-36  choosing a drivetrain for a real robot, and one case study
    37-39  proprioception: transparency, internal force sensing, active compliance
    40-41  positive force feedback, and the honesty test for claiming it
    42-43  translating human biomechanics into robot design

REINFORCEMENT LEARNING
    44-50  the environment felt by hand, then the vocabulary and the MDP
    51-54  how to measure how good a square is
    55-58  the four Bellman equations, one page each, in full arithmetic
    59-63  compute the perfect policy, given that we know the ice
    64-66  learn it WITHOUT knowing the ice -- what a real robot must do
    67-72  the surrounding ideas

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

from .ctrldesign import (
    LeadLagPage,
    ObserverPage,
    StabilisingPage,
    StateFeedbackPage,
)
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
    NyquistPage,
    SecondOrderPage,
    StabilityPage,
)
from .zeros import ZerosPage
from .nonlin import NonlinearControlPage, NonlinearSystemsPage
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
from .extras import BanditPage, ConvergencePage, HyperPage, ModelPage
from .forcefb import PFFIntroPage, PFFMathPage
from .foundations import MDPPage, PolicyPage
from .frozenlake import FrozenLakePage, TransitionsPage
from .intro import ReturnPage, RewardPage, WhatIsRLPage
from .lab import AdamPage, CodeLabPage
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
    SecondOrderPage,       # 10  wn and zeta, and every joint you will tune
    StabilityPage,         # 11  LHP, marginal, Routh-Hurwitz
    BodePage,              # 12  gain and phase margin, and PM = damping
    NyquistPage,           # 13  the -1 point, encirclements, vector margin
    ZerosPage,             # 14  what a zero is: blocked inputs, wrong-way steps
    # ---- Controller design: moving the poles on purpose -------------------
    StabilisingPage,       # 15  root locus, and why D is the term that saves you
    LeadLagPage,           # 16  lead, lag, notch -- and why notches betray you
    StateFeedbackPage,     # 17  place every pole at once; LQR
    ObserverPage,          # 18  estimate what you cannot measure; disturbance obs
    # ---- Nonlinear: what all of the above was assuming --------------------
    NonlinearSystemsPage,  # 19  superposition dies; limit cycles, basins
    NonlinearControlPage,  # 20  computed torque, sliding mode, passivity
    # ---- Actuators: what the world actually feels -------------------------
    EffectiveInertiaPage,  # 21  J_eff, and direct drive from first principles
    SEAPage,               # 22  spring between motor and load
    PEAPage,               # 23  spring alongside; what negative J_eff means
    ActuatorCompare,       # 24  torque, speed, inertia, bandwidth head to head
    GearingPage,           # 25  the N^2 square law kills transparency
    # ---- Control paradigms: four answers to one question ------------------
    GoalOfControlPage,     # 26  what is a controller even for?
    PositionControlPage,   # 27  command where
    PIDPracticePage,       # 28  anti-windup, D filtering, what jitter breaks
    TorqueControlPage,     # 29  command how hard
    ImpedanceControlPage,  # 30  command the relationship (motion in, force out)
    AdmittanceControlPage, # 31  command the relationship the other way round
    ImpVsAdmPage,          # 32  the decision, and the hardware that forces it
    SpectrumPage,          # 33  they were all one controller all along
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
]

# Stamp each class with its 1-based position. Page headers and the sidebar read
# this, so the numbers can never drift out of sync with the order above.
for _i, _cls in enumerate(PAGE_CLASSES, start=1):
    _cls.NUM = _i
