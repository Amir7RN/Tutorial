"""
Page registry. The order below IS the sidebar order, and page numbers are
assigned from it automatically -- so reordering this list renumbers everything
and no TITLE string ever has to be edited.

The sequence is deliberately concrete-before-abstract:

    1-3   the environment, felt by hand before it is named
    4-5   what you get paid, and how a whole episode becomes one number
    6-7   the thing we search for (a policy), then the formal framework (MDP)
    8-11  how to measure how good a square is
    12-15 the four Bellman equations, one page each, in full arithmetic
    16-20 compute the perfect policy, given that we know the ice
    21-23 learn it WITHOUT knowing the ice -- what a real robot must do
    24-29 the surrounding ideas
"""

from .bellman import (
    BellmanExpQPage,
    BellmanExpVPage,
    BellmanOptQPage,
    BellmanOptVPage,
)
from .dp_pages import (
    CompareDPPage,
    PolicyEvalPage,
    PolicyImprovePage,
    PolicyIterationPage,
    ValueIterationPage,
)
from .extras import BanditPage, ConvergencePage, HyperPage, ModelPage
from .foundations import MDPPage, PolicyPage
from .frozenlake import FrozenLakePage, TransitionsPage
from .intro import ReturnPage, RewardPage, WhatIsRLPage
from .lab import AdamPage, CodeLabPage
from .mc_pages import MCControlPage, MCIntroPage, MCPredictionPage
from .values import ActionValuePage, BellmanPage, StateValuePage, VvsQPage

PAGE_CLASSES = [
    # ---- Start Here: the environment, then the vocabulary ----------------
    WhatIsRLPage,          # 1   play it yourself
    FrozenLakePage,        # 2   the board
    TransitionsPage,       # 3   the slippery ice, with real probabilities
    RewardPage,            # 4   what the lake pays you
    ReturnPage,            # 5   a list of rewards -> one number, via gamma
    PolicyPage,            # 6   the thing we are searching for
    MDPPage,               # 7   all five pieces, formally named
    # ---- Value Functions: how good is a square? ---------------------------
    StateValuePage,        # 8
    ActionValuePage,       # 9
    VvsQPage,              # 10
    BellmanPage,           # 11  all four at once -- the summary
    # ---- one page per Bellman equation, in full arithmetic ----------------
    BellmanExpVPage,       # 12  V^pi  expectation
    BellmanExpQPage,       # 13  Q^pi  expectation
    BellmanOptVPage,       # 14  V*    optimality
    BellmanOptQPage,       # 15  Q*    optimality
    # ---- Dynamic Programming: solve it, knowing the ice -------------------
    PolicyEvalPage,        # 16
    PolicyImprovePage,     # 17
    PolicyIterationPage,   # 18
    ValueIterationPage,    # 19
    CompareDPPage,         # 20
    # ---- Monte Carlo: learn it, NOT knowing the ice -----------------------
    MCIntroPage,           # 21
    MCPredictionPage,      # 22
    MCControlPage,         # 23
    # ---- Beyond -----------------------------------------------------------
    BanditPage,            # 24
    ModelPage,             # 25
    HyperPage,             # 26
    ConvergencePage,       # 27
    CodeLabPage,           # 28
    AdamPage,              # 29
]

# Stamp each class with its 1-based position. Page headers and the sidebar read
# this, so the numbers can never drift out of sync with the order above.
for _i, _cls in enumerate(PAGE_CLASSES, start=1):
    _cls.NUM = _i
