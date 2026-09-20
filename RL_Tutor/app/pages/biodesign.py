"""
Pages 21-22: translating human biomechanics into robot design.

 21  Actuation & Sensing  -- muscles and receptors, as design requirements
 22  Skin & Bone          -- the structures that shape force before control runs

The discipline in both pages is the same one: do not copy the anatomy, copy
the *functional role*. A robot does not need a sarcomere; it needs whatever
the sarcomere was doing for the system.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from ..widgets import Card, body, callout, hline, title
from .base import Page

SECTION = "Bio → Robot"


def _translate_table(rows):
    """rows: (in humans, what matters, how I'd translate it)"""
    t = QTableWidget(len(rows), 3)
    t.setHorizontalHeaderLabels(
        ["In humans", "What matters biomechanically", "Translation to robot design"])
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    for c, w in enumerate((250, 250, 300)):
        t.setColumnWidth(c, w)
    t.setMinimumHeight(60 + 74 * len(rows))
    return t


# ==========================================================================
# PAGE 21 -- actuation and sensing
# ==========================================================================

class BioActuationPage(Page):
    TITLE = "Bio → Robot: Actuation & Sensing"
    SUBTITLE = ("Human actuation is not a set of stiff torque sources, and human "
                "sensing does not try to measure everything.")
    SECTION = SECTION
    NOTES = "material p.10"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(title("1 · Translating human actuation biomechanics"))

        h = Card("how it works in humans")
        h.add(title("Human actuation is not stiff torque sources.", 15))
        h.add(body(
            "Key properties:<br>"
            "&nbsp;&nbsp;• Muscles generate force through <b>compliant "
            "tendons</b><br>"
            "&nbsp;&nbsp;• Force depends on <b>length, velocity, and "
            "activation</b><br>"
            "&nbsp;&nbsp;• Reflexes provide fast, local correction<br>"
            "&nbsp;&nbsp;• Voluntary control operates at slower timescales<br><br>"
            "Humans combine <b>passive mechanics</b>, <b>reflexive responses</b>, "
            "and <b>volitional intent</b> — three layers running at three "
            "different rates."))
        self.add(h)

        w = Card("what matters biomechanically")
        w.add(body(
            (
                "&nbsp;&nbsp;• Compliance for shock absorption<br>&nbsp;&nbsp;• Energy storage and "
                "return<br>&nbsp;&nbsp;• <b>Timescale separation</b> (fast reflex, slow intent; response "
                "bandwidth and update rate are distinct)<br>&nbsp;&nbsp;• Stability through <b>interaction, not "
                "dominance</b>"
            )))
        w.add(body(
            "That last line is the thesis of this entire tutorial, stated "
            "biologically. A stiff position controller achieves stability by "
            "dominating the environment. A muscle achieves it by negotiating "
            "with it.", dim=True))
        self.add(w)

        t = Card("how I would translate this to robot design")
        t.add(body(
            "I would <b>not directly copy muscles</b>, but capture their "
            "<b>functional role</b>:"))
        t.add(body(
            "<b>1 · Compliant actuation</b><br>"
            "&nbsp;&nbsp;• SEA, PEA, tendon-driven systems<br>"
            "&nbsp;&nbsp;• Mechanical transparency<br><br>"
            "<b>2 · Impedance-based control</b><br>"
            "&nbsp;&nbsp;• Adjustable stiffness and damping<br>"
            "&nbsp;&nbsp;• Yield to external forces safely<br><br>"
            "<b>3 · Reflex-inspired control</b><br>"
            "&nbsp;&nbsp;• Fast local responses to deviations<br>"
            "&nbsp;&nbsp;• Supervisory safety layers (fault-tolerance "
            "monitoring)<br><br>"
            "<b>4 · Shared control</b><br>"
            "&nbsp;&nbsp;• Autonomous motion + human intent<br>"
            "&nbsp;&nbsp;• Similar to a CPG with voluntary override"))
        self.add(t)

        self.add(callout(
            "<i>\"I design actuation systems that cooperate with the human rather "
            "than overpower them.\"</i>", "good"))

        self.add(hline())
        self.add(title("2 · Translating human sensing biomechanics"))

        s = Card("how it works in humans")
        s.add(body(
            "Humans sense motion and interaction through:<br>"
            "&nbsp;&nbsp;• <b>Muscle spindles</b> → length &amp; velocity<br>"
            "&nbsp;&nbsp;• <b>Golgi tendon organs</b> → force<br>"
            "&nbsp;&nbsp;• <b>Cutaneous receptors</b> → pressure &amp; shear<br>"
            "&nbsp;&nbsp;• <b>Vestibular system</b> → acceleration &amp; "
            "orientation"))
        s.add(title("Humans do not measure everything precisely. They sense what "
                    "matters for stability and safety.", 15))
        s.add(body(
            "Sensing is <b>distributed</b>, <b>redundant</b>, and "
            "<b>context-dependent</b>."))
        self.add(s)

        sw = Card("what matters biomechanically")
        sw.add(body(
            "&nbsp;&nbsp;• Relative motion, not absolute precision<br>"
            "&nbsp;&nbsp;• Rate of change (velocity, acceleration)<br>"
            "&nbsp;&nbsp;• Threshold-based responses<br>"
            "&nbsp;&nbsp;• Integration across modalities"))
        self.add(sw)

        st = Card("how I would translate this to robot design")
        st.add(body(
            "I would focus on <b>proprioceptive and interaction-relevant "
            "sensing</b>:"))
        st.add(body(
            "<b>1 · Joint-level proprioception</b><br>"
            "&nbsp;&nbsp;• Motor current → torque<br>"
            "&nbsp;&nbsp;• Encoders → position &amp; velocity<br><br>"
            "<b>2 · Contact sensing</b><br>"
            "&nbsp;&nbsp;• Distributed pressure sensors<br>"
            "&nbsp;&nbsp;• Early detection of unexpected contact<br><br>"
            "<b>3 · State estimation</b><br>"
            "&nbsp;&nbsp;• Compare expected vs measured motion<br>"
            "&nbsp;&nbsp;• Detect abnormal interaction<br><br>"
            "<b>4 · Design sensing to serve control</b><br>"
            "&nbsp;&nbsp;• Not maximum resolution<br>"
            "&nbsp;&nbsp;• <b>Sufficient</b> resolution at the <b>correct "
            "bandwidth</b>"))
        self.add(st)

        self.add(callout(
            "<i>\"I design sensing to support stability and safety, not just "
            "measurement.\"</i><br><br>"
            "Connection to prosthesis and exoskeleton work: internal model vs "
            "measured motion, velocity-based error detection, and proprioceptive "
            "control without heavy external sensing.", "good"))

        self.finish()


# ==========================================================================
# PAGE 22 -- skin and bone
# ==========================================================================

class BioStructurePage(Page):
    TITLE = "Bio → Robot: Skin & Bone"
    SUBTITLE = ("The two structures that shape force <i>before</i> any controller "
                "gets a vote.")
    SECTION = SECTION
    NOTES = "material p.10"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(title("1 · Translating human skin biomechanics"))

        s = Card("how it works in humans")
        s.add(body(
            "Human skin is <b>layered</b> (epidermis, dermis, fat), "
            "<b>viscoelastic</b>, <b>highly deformable</b>, and a "
            "<b>mechanical + sensory interface</b>."))
        s.add(body(
            "Key functions:<br>"
            "&nbsp;&nbsp;• Distributes contact forces<br>"
            "&nbsp;&nbsp;• Absorbs impact energy<br>"
            "&nbsp;&nbsp;• Prevents sharp pressure peaks<br>"
            "&nbsp;&nbsp;• Houses dense tactile sensing<br>"
            "&nbsp;&nbsp;• Enables early detection of contact"))
        s.add(title("Skin does not stop force — it spreads it in time and space.",
                    15))
        self.add(s)

        sw = Card("what matters biomechanically")
        sw.add(body(
            "&nbsp;&nbsp;• Pressure distribution<br>"
            "&nbsp;&nbsp;• Rate-dependent response (fast vs slow contact)<br>"
            "&nbsp;&nbsp;• Contact area growth with load<br>"
            "&nbsp;&nbsp;• Coupling between deformation and sensing"))
        self.add(sw)

        t = Card("how I would translate this to robot design")
        t.add(body("For robot skin I would think in <b>layers</b>, just like "
                   "biology:"))
        t.add(body(
            "<b>1 · Outer compliant layer</b><br>"
            "&nbsp;&nbsp;• Soft elastomer or lattice<br>"
            "&nbsp;&nbsp;• First line of energy absorption<br>"
            "&nbsp;&nbsp;• Prevents high contact stress<br><br>"
            "<b>2 · Intermediate damping layer</b><br>"
            "&nbsp;&nbsp;• Viscoelastic foam or structured polymer<br>"
            "&nbsp;&nbsp;• Absorbs impact energy<br>"
            "&nbsp;&nbsp;• <b>Controls force rise rate</b><br><br>"
            "<b>3 · Inner sensing layer</b><br>"
            "&nbsp;&nbsp;• Pressure or force sensors<br>"
            "&nbsp;&nbsp;• Detect <b>distributed</b> contact, not just point "
            "force<br><br>"
            "<b>4 · Design targets derived from humans</b><br>"
            "&nbsp;&nbsp;• Maximum safe pressure<br>"
            "&nbsp;&nbsp;• Acceptable force rise time<br>"
            "&nbsp;&nbsp;• Deformation vs force curves"))
        self.add(t)

        self.add(callout(
            "<i>\"I would design robot skin as a mechanical signal conditioner "
            "that protects both the human and the robot before control "
            "reacts.\"</i><br><br>"
            "Note how this is the same argument as the SEA spring, one layer "
            "further out: the shell responds in microseconds, the control loop "
            "in milliseconds. Mechanics gets there first, always.", "good"))

        self.add(hline())
        self.add(title("2 · Translating human bone biomechanics"))

        b = Card("how it works in humans")
        b.add(title("Human bones are not rigid sticks.", 15))
        b.add(body(
            "They are <b>load-bearing structures with anisotropic stiffness</b>, "
            "optimised for <b>bending, torsion, and compression</b>, and designed "
            "to <b>redirect forces</b>, not just resist them."))
        b.add(body(
            "Key properties:<br>"
            "&nbsp;&nbsp;• Cortical bone: stiff, load-carrying<br>"
            "&nbsp;&nbsp;• Trabecular bone: compliant, energy-dissipating<br>"
            "&nbsp;&nbsp;• <b>Geometry</b> (cross-section, curvature) matters more "
            "than material strength alone<br>"
            "&nbsp;&nbsp;• Bones work with joints to <b>shape force paths</b> "
            "during walking, impacts, and falls"))
        b.add(body(
            "Bones are part of a <b>hierarchical system</b>: bone geometry → "
            "joint kinematics → muscle leverage → whole-body dynamics.", dim=True))
        self.add(b)

        bw = Card("what matters biomechanically")
        bw.add(body(
            "&nbsp;&nbsp;• <b>Directional stiffness</b> — strong where needed, "
            "compliant where safe<br>"
            "&nbsp;&nbsp;• Moment arms and leverage<br>"
            "&nbsp;&nbsp;• Load paths under dynamic motion<br>"
            "&nbsp;&nbsp;• Stress distribution over time (fatigue)"))
        self.add(bw)

        bt = Card("how I would translate this to robot design")
        bt.add(body(
            "In robots I would <b>not try to replicate bone anatomy</b>, but "
            "rather:"))
        bt.add(body(
            "<b>1 · Use geometry to control stiffness</b><br>"
            "&nbsp;&nbsp;• Vary cross-sections to tune bending vs torsional "
            "stiffness<br>"
            "&nbsp;&nbsp;• Use curved or tapered links to redirect loads "
            "safely<br><br>"
            "<b>2 · Design structural compliance intentionally</b><br>"
            "&nbsp;&nbsp;• Embed compliance in links or joints where humans "
            "tolerate motion<br>"
            "&nbsp;&nbsp;• Keep stiffness high where precision is required<br><br>"
            "<b>3 · Design for fatigue, not just peak load</b><br>"
            "&nbsp;&nbsp;• Bones survive millions of cycles → robots must too<br>"
            "&nbsp;&nbsp;• Use fatigue-informed design, not only static FEA<br><br>"
            "<b>4 · Exploit structure before control</b><br>"
            "&nbsp;&nbsp;• Let mechanical geometry do part of the "
            "stabilisation<br>"
            "&nbsp;&nbsp;• Reduce reliance on high-bandwidth control loops"))
        self.add(bt)

        self.add(callout(
            "<i>\"I think of robot 'bones' as load-guiding structures that shape "
            "forces before control even starts.\"</i>", "good"))

        self.add(hline())

        f = Card("the thread through all four translations")
        f.add(_translate_table([
            ("Muscle + tendon",
             "Compliance, energy return, bandwidth separation",
             "SEA / PEA / tendon drive + impedance control"),
            ("Spindles, GTOs, skin receptors",
             "Sense what matters for stability, not maximum resolution",
             "Proprioception from current + encoders; distributed contact "
             "sensing"),
            ("Skin",
             "Spread force in time and space; sense early",
             "Layered elastomer → damping foam → pressure array"),
            ("Bone",
             "Directional stiffness; shape load paths; survive fatigue",
             "Geometry-tuned links; intentional structural compliance"),
        ]))
        f.add(body(
            "Every row says the same thing: <b>mechanics acts first, control "
            "acts second.</b> The job of design is to make sure the part that "
            "acts first is already doing something sensible — because by the time "
            "the controller has an opinion, the collision is over.", dim=True))
        self.add(f)

        self.add(callout(
            "<b>Where this connects back to the RL section that follows.</b> "
            "Everything above shapes the <i>dynamics the policy is learning "
            "in</i>. A reinforcement-learning agent does not learn control laws "
            "in the abstract; it learns them for a specific plant, with a "
            "specific effective inertia, a specific bandwidth, and a specific "
            "safety envelope. Design the mechanics badly and no amount of "
            "training fixes it.", "key"))

        self.finish()
