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
     3-7   first order, slowly: what it is, tau and the pole, the integrator,
           frequency, the s-plane
     8-11  second order, stability, Bode margins, Nyquist
    12-15  controller design: stabilising, lead/lag, state feedback, observers
    16-17  nonlinear systems, and the six things people do about them
    18-22  actuator mechanics -- effective inertia, SEA, PEA, gearing
    23-30  the four control paradigms, ending in the one spectrum they share
    31-33  choosing a drivetrain for a real robot, and one case study
    34-36  proprioception: transparency, internal force sensing, active compliance
    37-38  positive force feedback, and the honesty test for claiming it
    39-40  translating human biomechanics into robot design

REINFORCEMENT LEARNING
    41-47  the environment felt by hand, then the vocabulary and the MDP
    48-51  how to measure how good a square is
    52-55  the four Bellman equations, one page each, in full arithmetic
    56-60  compute the perfect policy, given that we know the ice
    61-63  learn it WITHOUT knowing the ice -- what a real robot must do
    64-69  the surrounding ideas

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
    FirstOrderPage,        # 3   one store, one drain -- and what that buys you
    TimeConstantPage,      # 4   tau, 0.63, and the pole as a decay rate
    IntegratorPage,        # 5   the pole at s = 0: a store with no drain
    FirstOrderFreqPage,    # 6   the corner, -3 dB, and the 90 deg ceiling
    SPlanePage,            # 7   what j is; the second store that lifts a pole
    SecondOrderPage,       # 8   wn and zeta, and every joint you will tune
    StabilityPage,         # 9   LHP, marginal, Routh-Hurwitz
    BodePage,              # 10  gain and phase margin, and PM = damping
    NyquistPage,           # 11  the -1 point, encirclements, vector margin
    # ---- Controller design: moving the poles on purpose -------------------
    StabilisingPage,       # 12  root locus, and why D is the term that saves you
    LeadLagPage,           # 13  lead, lag, notch -- and why notches betray you
    StateFeedbackPage,     # 14  place every pole at once; LQR
    ObserverPage,          # 15  estimate what you cannot measure; disturbance obs
    # ---- Nonlinear: what all of the above was assuming --------------------
    NonlinearSystemsPage,  # 16  superposition dies; limit cycles, basins
    NonlinearControlPage,  # 17  computed torque, sliding mode, passivity
    # ---- Actuators: what the world actually feels -------------------------
    EffectiveInertiaPage,  # 18  J_eff, and direct drive from first principles
    SEAPage,               # 19  spring between motor and load
    PEAPage,               # 20  spring alongside; what negative J_eff means
    ActuatorCompare,       # 21  torque, speed, inertia, bandwidth head to head
    GearingPage,           # 22  the N^2 square law kills transparency
    # ---- Control paradigms: four answers to one question ------------------
    GoalOfControlPage,     # 23  what is a controller even for?
    PositionControlPage,   # 24  command where
    PIDPracticePage,       # 25  anti-windup, D filtering, what jitter breaks
    TorqueControlPage,     # 26  command how hard
    ImpedanceControlPage,  # 27  command the relationship (motion in, force out)
    AdmittanceControlPage, # 28  command the relationship the other way round
    ImpVsAdmPage,          # 29  the decision, and the hardware that forces it
    SpectrumPage,          # 30  they were all one controller all along
    # ---- Robot design ------------------------------------------------------
    ActuatorChoicePage,    # 31  humanoid vs biped vs quadruped
    ScalingPage,           # 32  the square-cube law and hybrid actuation
    NeoPage,               # 33  case study: 1X Neo
    # ---- Proprioception -----------------------------------------------------
    BioProprioPage,        # 34  spindles, GTOs, and the timescales
    RobotProprioPage,      # 35  transparency is the prerequisite
    ActiveCompliancePage,  # 36  software-defined compliance, three layers
    # ---- Force feedback -----------------------------------------------------
    PFFIntroPage,          # 37  what positive force feedback actually is
    PFFMathPage,           # 38  closing the loop, and the honesty test
    # ---- Bio -> robot -------------------------------------------------------
    BioActuationPage,      # 39  actuation and sensing
    BioStructurePage,      # 40  skin and bone
    # ======================================================================
    # REINFORCEMENT LEARNING
    # ======================================================================
    # ---- Start Here: the environment, then the vocabulary ----------------
    WhatIsRLPage,          # 41  play it yourself
    FrozenLakePage,        # 42  the board
    TransitionsPage,       # 43  the slippery ice, with real probabilities
    RewardPage,            # 44  what the lake pays you
    ReturnPage,            # 45  a list of rewards -> one number, via gamma
    PolicyPage,            # 46  the thing we are searching for
    MDPPage,               # 47  all five pieces, formally named
    # ---- Value Functions: how good is a square? ---------------------------
    StateValuePage,        # 48
    ActionValuePage,       # 49
    VvsQPage,              # 50
    BellmanPage,           # 51  all four at once -- the summary
    # ---- one page per Bellman equation, in full arithmetic ----------------
    BellmanExpVPage,       # 52  V^pi  expectation
    BellmanExpQPage,       # 53  Q^pi  expectation
    BellmanOptVPage,       # 54  V*    optimality
    BellmanOptQPage,       # 55  Q*    optimality
    # ---- Dynamic Programming: solve it, knowing the ice -------------------
    PolicyEvalPage,        # 56
    PolicyImprovePage,     # 57
    PolicyIterationPage,   # 58
    ValueIterationPage,    # 59
    CompareDPPage,         # 60
    # ---- Monte Carlo: learn it, NOT knowing the ice -----------------------
    MCIntroPage,           # 61
    MCPredictionPage,      # 62
    MCControlPage,         # 63
    # ---- Beyond -----------------------------------------------------------
    BanditPage,            # 64
    ModelPage,             # 65
    HyperPage,             # 66
    ConvergencePage,       # 67
    CodeLabPage,           # 68
    AdamPage,              # 69
]

# Stamp each class with its 1-based position. Page headers and the sidebar read
# this, so the numbers can never drift out of sync with the order above.
for _i, _cls in enumerate(PAGE_CLASSES, start=1):
    _cls.NUM = _i
