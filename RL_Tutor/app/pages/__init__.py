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
     2-6   linear systems: first order, second order, stability, Bode, Nyquist
     7-10  controller design: stabilising, lead/lag, state feedback, observers
    11-12  nonlinear systems, and the six things people do about them
    13-17  actuator mechanics -- effective inertia, SEA, PEA, gearing
    18-25  the four control paradigms, ending in the one spectrum they share
    26-28  choosing a drivetrain for a real robot, and one case study
    29-31  proprioception: transparency, internal force sensing, active compliance
    32-33  positive force feedback, and the honesty test for claiming it
    34-35  translating human biomechanics into robot design

REINFORCEMENT LEARNING
    36-42  the environment felt by hand, then the vocabulary and the MDP
    43-46  how to measure how good a square is
    47-50  the four Bellman equations, one page each, in full arithmetic
    51-55  compute the perfect policy, given that we know the ice
    56-58  learn it WITHOUT knowing the ice -- what a real robot must do
    59-64  the surrounding ideas

Real-time comes first on purpose. Every later page makes a claim about how
fast something can respond, and every one of those claims is bounded by the
sampling, delay and scheduling facts established on page 1.

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
from .linsys import (
    BodePage,
    FirstOrderPage,
    NyquistPage,
    SecondOrderPage,
    StabilityPage,
)
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
    FirstOrderPage,        # 2   one pole, one time constant, 90 deg ceiling
    SecondOrderPage,       # 3   wn and zeta, and every joint you will tune
    StabilityPage,         # 4   LHP, marginal, Routh-Hurwitz
    BodePage,              # 5   gain and phase margin, and PM = damping
    NyquistPage,           # 6   the -1 point, encirclements, vector margin
    # ---- Controller design: moving the poles on purpose -------------------
    StabilisingPage,       # 7   root locus, and why D is the term that saves you
    LeadLagPage,           # 8   lead, lag, notch -- and why notches betray you
    StateFeedbackPage,     # 9   place every pole at once; LQR
    ObserverPage,          # 10  estimate what you cannot measure; disturbance obs
    # ---- Nonlinear: what all of the above was assuming --------------------
    NonlinearSystemsPage,  # 11  superposition dies; limit cycles, basins
    NonlinearControlPage,  # 12  computed torque, sliding mode, passivity
    # ---- Actuators: what the world actually feels -------------------------
    EffectiveInertiaPage,  # 13  J_eff, and direct drive from first principles
    SEAPage,               # 14  spring between motor and load
    PEAPage,               # 15  spring alongside; what negative J_eff means
    ActuatorCompare,       # 16  torque, speed, inertia, bandwidth head to head
    GearingPage,           # 17  the N^2 square law kills transparency
    # ---- Control paradigms: four answers to one question ------------------
    GoalOfControlPage,     # 18  what is a controller even for?
    PositionControlPage,   # 19  command where
    PIDPracticePage,       # 20  anti-windup, D filtering, what jitter breaks
    TorqueControlPage,     # 21  command how hard
    ImpedanceControlPage,  # 22  command the relationship (motion in, force out)
    AdmittanceControlPage,  # 23 command the relationship the other way round
    ImpVsAdmPage,          # 24  the decision, and the hardware that forces it
    SpectrumPage,          # 25  they were all one controller all along
    # ---- Robot design ------------------------------------------------------
    ActuatorChoicePage,    # 26  humanoid vs biped vs quadruped
    ScalingPage,           # 27  the square-cube law and hybrid actuation
    NeoPage,               # 28  case study: 1X Neo
    # ---- Proprioception -----------------------------------------------------
    BioProprioPage,        # 29  spindles, GTOs, and the timescales
    RobotProprioPage,      # 30  transparency is the prerequisite
    ActiveCompliancePage,  # 31  software-defined compliance, three layers
    # ---- Force feedback -----------------------------------------------------
    PFFIntroPage,          # 32  what positive force feedback actually is
    PFFMathPage,           # 33  closing the loop, and the honesty test
    # ---- Bio -> robot -------------------------------------------------------
    BioActuationPage,      # 34  actuation and sensing
    BioStructurePage,      # 35  skin and bone
    # ======================================================================
    # REINFORCEMENT LEARNING
    # ======================================================================
    # ---- Start Here: the environment, then the vocabulary ----------------
    WhatIsRLPage,          # 36  play it yourself
    FrozenLakePage,        # 37  the board
    TransitionsPage,       # 38  the slippery ice, with real probabilities
    RewardPage,            # 39  what the lake pays you
    ReturnPage,            # 40  a list of rewards -> one number, via gamma
    PolicyPage,            # 41  the thing we are searching for
    MDPPage,               # 42  all five pieces, formally named
    # ---- Value Functions: how good is a square? ---------------------------
    StateValuePage,        # 43
    ActionValuePage,       # 44
    VvsQPage,              # 45
    BellmanPage,           # 46  all four at once -- the summary
    # ---- one page per Bellman equation, in full arithmetic ----------------
    BellmanExpVPage,       # 47  V^pi  expectation
    BellmanExpQPage,       # 48  Q^pi  expectation
    BellmanOptVPage,       # 49  V*    optimality
    BellmanOptQPage,       # 50  Q*    optimality
    # ---- Dynamic Programming: solve it, knowing the ice -------------------
    PolicyEvalPage,        # 51
    PolicyImprovePage,     # 52
    PolicyIterationPage,   # 53
    ValueIterationPage,    # 54
    CompareDPPage,         # 55
    # ---- Monte Carlo: learn it, NOT knowing the ice -----------------------
    MCIntroPage,           # 56
    MCPredictionPage,      # 57
    MCControlPage,         # 58
    # ---- Beyond -----------------------------------------------------------
    BanditPage,            # 59
    ModelPage,             # 60
    HyperPage,             # 61
    ConvergencePage,       # 62
    CodeLabPage,           # 63
    AdamPage,              # 64
]

# Stamp each class with its 1-based position. Page headers and the sidebar read
# this, so the numbers can never drift out of sync with the order above.
for _i, _cls in enumerate(PAGE_CLASSES, start=1):
    _cls.NUM = _i
