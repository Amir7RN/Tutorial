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
     2-6   actuator mechanics -- effective inertia, SEA, PEA, gearing
     7-14  the four control paradigms, ending in the one spectrum they share
    15-17  choosing a drivetrain for a real robot, and one case study
    18-20  proprioception: transparency, internal force sensing, active compliance
    21-22  positive force feedback, and the honesty test for claiming it
    23-24  translating human biomechanics into robot design

REINFORCEMENT LEARNING
    25-27  the environment, felt by hand before it is named
    28-29  what you get paid, and how a whole episode becomes one number
    30-31  the thing we search for (a policy), then the formal framework (MDP)
    32-35  how to measure how good a square is
    36-39  the four Bellman equations, one page each, in full arithmetic
    40-44  compute the perfect policy, given that we know the ice
    45-47  learn it WITHOUT knowing the ice -- what a real robot must do
    48-53  the surrounding ideas

Real-time comes first on purpose. Every later page makes a claim about how
fast something can respond, and every one of those claims is bounded by the
sampling, delay and scheduling facts established on page 1.
"""

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
    # ---- Actuators: what the world actually feels -------------------------
    EffectiveInertiaPage,  # 2   J_eff, and direct drive from first principles
    SEAPage,               # 3   spring between motor and load
    PEAPage,               # 4   spring alongside; what negative J_eff means
    ActuatorCompare,       # 5   torque, speed, inertia, bandwidth head to head
    GearingPage,           # 6   the N^2 square law kills transparency
    # ---- Control paradigms: four answers to one question ------------------
    GoalOfControlPage,     # 7   what is a controller even for?
    PositionControlPage,   # 8   command where
    PIDPracticePage,       # 9   anti-windup, D filtering, what jitter breaks
    TorqueControlPage,     # 10  command how hard
    ImpedanceControlPage,  # 11  command the relationship (motion in, force out)
    AdmittanceControlPage,  # 12  command the relationship the other way round
    ImpVsAdmPage,          # 13  the decision, and the hardware that forces it
    SpectrumPage,          # 14  they were all one controller all along
    # ---- Robot design ------------------------------------------------------
    ActuatorChoicePage,    # 15  humanoid vs biped vs quadruped
    ScalingPage,           # 16  the square-cube law and hybrid actuation
    NeoPage,               # 17  case study: 1X Neo
    # ---- Proprioception -----------------------------------------------------
    BioProprioPage,        # 18  spindles, GTOs, and the timescales
    RobotProprioPage,      # 19  transparency is the prerequisite
    ActiveCompliancePage,  # 20  software-defined compliance, three layers
    # ---- Force feedback -----------------------------------------------------
    PFFIntroPage,          # 21  what positive force feedback actually is
    PFFMathPage,           # 22  closing the loop, and the honesty test
    # ---- Bio -> robot -------------------------------------------------------
    BioActuationPage,      # 23  actuation and sensing
    BioStructurePage,      # 24  skin and bone
    # ======================================================================
    # REINFORCEMENT LEARNING
    # ======================================================================
    # ---- Start Here: the environment, then the vocabulary ----------------
    WhatIsRLPage,          # 25  play it yourself
    FrozenLakePage,        # 26  the board
    TransitionsPage,       # 27  the slippery ice, with real probabilities
    RewardPage,            # 28  what the lake pays you
    ReturnPage,            # 29  a list of rewards -> one number, via gamma
    PolicyPage,            # 30  the thing we are searching for
    MDPPage,               # 31  all five pieces, formally named
    # ---- Value Functions: how good is a square? ---------------------------
    StateValuePage,        # 32
    ActionValuePage,       # 33
    VvsQPage,              # 34
    BellmanPage,           # 35  all four at once -- the summary
    # ---- one page per Bellman equation, in full arithmetic ----------------
    BellmanExpVPage,       # 36  V^pi  expectation
    BellmanExpQPage,       # 37  Q^pi  expectation
    BellmanOptVPage,       # 38  V*    optimality
    BellmanOptQPage,       # 39  Q*    optimality
    # ---- Dynamic Programming: solve it, knowing the ice -------------------
    PolicyEvalPage,        # 40
    PolicyImprovePage,     # 41
    PolicyIterationPage,   # 42
    ValueIterationPage,    # 43
    CompareDPPage,         # 44
    # ---- Monte Carlo: learn it, NOT knowing the ice -----------------------
    MCIntroPage,           # 45
    MCPredictionPage,      # 46
    MCControlPage,         # 47
    # ---- Beyond -----------------------------------------------------------
    BanditPage,            # 48
    ModelPage,             # 49
    HyperPage,             # 50
    ConvergencePage,       # 51
    CodeLabPage,           # 52
    AdamPage,              # 53
]

# Stamp each class with its 1-based position. Page headers and the sidebar read
# this, so the numbers can never drift out of sync with the order above.
for _i, _cls in enumerate(PAGE_CLASSES, start=1):
    _cls.NUM = _i
