"""
Page registry. The order below IS the sidebar order, and page numbers are
assigned from it automatically -- so reordering this list renumbers everything
and no TITLE string ever has to be edited.

The tutor is in two halves. The first half is the physical machine: what the
world feels when it touches the robot, and how a controller can shape that.
The second half is reinforcement learning: how a policy is found for a machine
whose dynamics you now understand.

CONTROL & DYNAMICS
     1-5   actuator mechanics -- effective inertia, SEA, PEA, gearing
     6-12  the four control paradigms, ending in the one spectrum they share
    13-15  choosing a drivetrain for a real robot, and one case study
    16-18  proprioception: transparency, internal force sensing, active compliance
    19-20  positive force feedback, and the honesty test for claiming it
    21-22  translating human biomechanics into robot design

REINFORCEMENT LEARNING
    23-25  the environment, felt by hand before it is named
    26-27  what you get paid, and how a whole episode becomes one number
    28-29  the thing we search for (a policy), then the formal framework (MDP)
    30-33  how to measure how good a square is
    34-37  the four Bellman equations, one page each, in full arithmetic
    38-42  compute the perfect policy, given that we know the ice
    43-45  learn it WITHOUT knowing the ice -- what a real robot must do
    46-51  the surrounding ideas
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
from .proprio import ActiveCompliancePage, BioProprioPage, RobotProprioPage
from .values import ActionValuePage, BellmanPage, StateValuePage, VvsQPage

PAGE_CLASSES = [
    # ======================================================================
    # CONTROL & DYNAMICS
    # ======================================================================
    # ---- Actuators: what the world actually feels -------------------------
    EffectiveInertiaPage,  # 1   J_eff, and direct drive from first principles
    SEAPage,               # 2   spring between motor and load
    PEAPage,               # 3   spring alongside; negative effective inertia
    ActuatorCompare,       # 4   torque, speed, inertia, bandwidth head to head
    GearingPage,           # 5   the N^2 square law kills transparency
    # ---- Control paradigms: four answers to one question ------------------
    GoalOfControlPage,     # 6   what is a controller even for?
    PositionControlPage,   # 7   command where
    TorqueControlPage,     # 8   command how hard
    ImpedanceControlPage,  # 9   command the relationship (motion in, force out)
    AdmittanceControlPage,  # 10  command the relationship the other way round
    ImpVsAdmPage,          # 11  the decision, and the hardware that forces it
    SpectrumPage,          # 12  they were all one controller all along
    # ---- Robot design ------------------------------------------------------
    ActuatorChoicePage,    # 13  humanoid vs biped vs quadruped
    ScalingPage,           # 14  the square-cube law and hybrid actuation
    NeoPage,               # 15  case study: 1X Neo
    # ---- Proprioception -----------------------------------------------------
    BioProprioPage,        # 16  spindles, GTOs, and the timescales
    RobotProprioPage,      # 17  transparency is the prerequisite
    ActiveCompliancePage,  # 18  software-defined compliance, three layers
    # ---- Force feedback -----------------------------------------------------
    PFFIntroPage,          # 19  what positive force feedback actually is
    PFFMathPage,           # 20  closing the loop, and the honesty test
    # ---- Bio -> robot -------------------------------------------------------
    BioActuationPage,      # 21  actuation and sensing
    BioStructurePage,      # 22  skin and bone
    # ======================================================================
    # REINFORCEMENT LEARNING
    # ======================================================================
    # ---- Start Here: the environment, then the vocabulary ----------------
    WhatIsRLPage,          # 23  play it yourself
    FrozenLakePage,        # 24  the board
    TransitionsPage,       # 25  the slippery ice, with real probabilities
    RewardPage,            # 26  what the lake pays you
    ReturnPage,            # 27  a list of rewards -> one number, via gamma
    PolicyPage,            # 28  the thing we are searching for
    MDPPage,               # 29  all five pieces, formally named
    # ---- Value Functions: how good is a square? ---------------------------
    StateValuePage,        # 30
    ActionValuePage,       # 31
    VvsQPage,              # 32
    BellmanPage,           # 33  all four at once -- the summary
    # ---- one page per Bellman equation, in full arithmetic ----------------
    BellmanExpVPage,       # 34  V^pi  expectation
    BellmanExpQPage,       # 35  Q^pi  expectation
    BellmanOptVPage,       # 36  V*    optimality
    BellmanOptQPage,       # 37  Q*    optimality
    # ---- Dynamic Programming: solve it, knowing the ice -------------------
    PolicyEvalPage,        # 38
    PolicyImprovePage,     # 39
    PolicyIterationPage,   # 40
    ValueIterationPage,    # 41
    CompareDPPage,         # 42
    # ---- Monte Carlo: learn it, NOT knowing the ice -----------------------
    MCIntroPage,           # 43
    MCPredictionPage,      # 44
    MCControlPage,         # 45
    # ---- Beyond -----------------------------------------------------------
    BanditPage,            # 46
    ModelPage,             # 47
    HyperPage,             # 48
    ConvergencePage,       # 49
    CodeLabPage,           # 50
    AdamPage,              # 51
]

# Stamp each class with its 1-based position. Page headers and the sidebar read
# this, so the numbers can never drift out of sync with the order above.
for _i, _cls in enumerate(PAGE_CLASSES, start=1):
    _cls.NUM = _i
