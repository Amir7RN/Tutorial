"""Kinematics summary extra: the null-space → pseudoinverse chain on one 3R arm.

Shown at the end of the Kinematics section summary. All numbers are for the
planar 3R arm with unit links at θ = (0°, 90°, −90°): joints at (0, 0), (1, 0),
(1, 1), tip at (2, 1), J = [−1 −1 0; 2 1 1].
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from .. import theme
from ..widgets import Card, body, math_label
from .robo_common import plain

PINV_HTML = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "pinv_steps.html")


def _ul(*items):
    return "<ul style='margin:0'>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def _ol(*items):
    return "<ol style='margin:0'>" + "".join(f"<li>{x}</li>" for x in items) + "</ol>"


def intro_card() -> Card:
    c = Card("the whole chain: null space → pseudoinverse as 'moment arm over moment arm squared'")
    c.add(plain(
        "One arm for every number: planar 3R, links of length 1, θ = (0°, 90°, −90°). "
        "Joints at (0, 0), (1, 0), (1, 1), tip at (2, 1), so J = [−1 −1 0; 2 1 1]."))
    return c


def pinv_steps_card() -> Card:
    """The interactive 'pseudo-inverse step by step' page, embedded."""
    c = Card("interactive: the pseudoinverse step by step on the arm (fat, tall, SVD, summary)")
    c.add(plain(
        "Tabs: fat (3 joints, 2 demands, θ̇ = Jᵀ(JJᵀ)⁻¹V), tall (fewer joints than "
        "demands, θ̇ = (JᵀJ)⁻¹JᵀV, the RRPR case), the same via SVD, and a summary. "
        "Step through with 'Next step', drag the blue arrow, open 'Show the math'."))
    url = QUrl.fromLocalFile(PINV_HTML)
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        QWebEngineView = None
    if QWebEngineView is not None:
        view = QWebEngineView()
        view.setMinimumHeight(1000)
        view.loadFinished.connect(
            lambda ok: view.page().runJavaScript("document.documentElement.dataset.theme='dark'"))
        view.load(url)
        c.add(view)
        c.view = view
    link = body(f"<a href='open' style='color:{theme.CYAN}'>Open it in the browser instead</a>")
    link.setTextInteractionFlags(Qt.TextBrowserInteraction)
    link.linkActivated.connect(lambda _: QDesktopServices.openUrl(url))
    c.add(link)
    return c


def spaces_card() -> Card:
    c = Card("1 · the two spaces and the two ways to read J")
    c.add(body(_ul(
        "<b>Joint space:</b> the joint speeds (θ̇₁, θ̇₂, θ̇₃). 3-D.",
        "<b>Hand space:</b> the tip velocity (v<sub>x</sub>, v<sub>y</sub>). 2-D.",
        "<b>Columns of J:</b> each joint's tip arrow, its moment-arm velocity "
        "ẑ × (tip − joint): (−1, 2), (−1, 1), (0, 1).",
        "<b>Rows of J:</b> each joint's leverage on one hand direction: "
        "row x = (−1, −1, 0), row y = (2, 1, 1).")))
    return c


def null_card() -> Card:
    c = Card("2 · the null space")
    c.add(body(
        "<b>What it is.</b> The joint motions perpendicular to <b>every</b> leverage "
        "row, so the tip feels nothing: v<sub>x</sub> = v<sub>y</sub> = 0. Same idea "
        "as the bead, whose velocity was perpendicular to the hoop's constraint row. "
        "3 joints, 2 task numbers → a <b>line</b> (3 − 2 = 1). The 4R arm had a plane.<br>"
        "<b>It depends only on the pose,</b> not on the desired velocity. V<sub>d</sub> "
        "just shifts the solution line, which always runs parallel to the null line."))
    c.add(body("<b>Four explicit ways to find it</b> (no trial and error):" + _ol(
        "<b>Cross product of the two rows</b> (3 joints, 2-D task): "
        "(−1, −1, 0) × (2, 1, 1) = (−1, 1, 1) ∝ <b>(1, −1, −1)</b>.",
        "<b>Solve Jn = 0</b> with one free unknown: n₁ = 1 forces n₂ = −1, n₃ = −1.",
        "<b>SVD / eigenvectors:</b> the vᵢ with σ = 0, i.e. the eigenvector of JᵀJ "
        "with eigenvalue 0.",
        "<b>The projector</b> N = I − J⁺J: take any joint motion and strip out the "
        "part the tip would feel. In control you never write the null line down.")))
    c.add(plain("The null line moves with the pose, so a controller recomputes it every tick."))
    return c


def eigen_card() -> Card:
    c = Card("3 · how eigenvalues and eigenvectors pair up")
    c.add(body(_ol(
        "The characteristic equation gives <b>only</b> the eigenvalues.",
        "Plug each λ back in: A − λI becomes singular. Solve (A − λI)v = 0. "
        "<b>That</b> v belongs to <b>that</b> λ, because you built it from that λ.",
        "Sort largest first; zeros go last.",
        "Check each pair: Av = λv.")))
    c.add(body("<b>Example: JᵀJ = [5 3 2; 3 2 1; 2 1 1]</b>" + _ul(
        "trace 8, sum of 2 × 2 minors 3, det 0, so λ(λ² − 8λ + 3) = 0",
        "λ = <b>7.606, 0.394, 0</b> → σ = 2.76 and 0.63",
        "v₁ = (0.81, 0.49, 0.32)",
        "v₂ = ±(0.10, −0.65, 0.75)",
        "v₃ = (1, −1, −1)/√3 (λ = 0: the null line)")))
    return c


def avoid_card() -> Card:
    c = Card("4 · using the null space to avoid singularities")
    c.add(math_label(r"\dot\theta=J^{+}V_d+k\,N\,\nabla w,\qquad w=\sigma_1\sigma_2=\sqrt{\det(JJ^T)}", 16))
    c.add(body(_ol(
        "<b>Health score:</b> w, the manipulability. It drops to 0 at a singularity.",
        "<b>Gradient:</b> the joint motion that raises w fastest.",
        "<b>Project with N:</b> keep only the part the tip can't feel.",
        "<b>Add it to the task.</b>")))
    c.add(body(
        "<b>Example:</b> nearly folded pose θ = (0°, 10°, 170°), σ₂ = 0.21. With "
        "V<sub>d</sub> = 0 and k = 2, after 1 s the arm opens into a triangle, "
        "σ₂ ≈ 1.22, and the <b>tip doesn't move</b>." + _ul(
            "It only fixes 'posture' singularities, not maximum reach.",
            "It never costs tip accuracy.")))
    return c


def jtj_card() -> Card:
    c = Card("5 · JᵀJ: the joint side (3 × 3)")
    c.add(body(_ul(
        "<b>Entry (i, j) = jᵢ · jⱼ</b> (column · column). Diagonal: the squared "
        "moment arm of each joint's arrow. Off-diagonal: overlap of two joints' "
        "arrows: positive reinforce, negative oppose, zero perpendicular.",
        "<b>It can't be diagonal per joint</b> for 3 joints in a plane: three "
        "nonzero arrows can't be mutually perpendicular in 2-D. So det = 0 and the "
        "null space exists.",
        "<b>In the eigen-basis</b> (the mixes v₁, v₂, v₃) the same matrix is "
        "diagonal: (σ₁², σ₂², 0). Each entry now belongs to a <b>mix</b>, a "
        "coordinated motion of all joints, not a single joint. Same object, "
        "different axes.",
        "<b>The mixes are independent channels:</b> v₁ → σ₁u₁, v₂ → σ₂u₂, v₃ → 0. "
        "That is how three perpendicular mixes fit into a 2-D hand space: one "
        "lands on nothing.")))
    return c


def jjt_card() -> Card:
    c = Card("6 · JJᵀ: the hand side (2 × 2)")
    c.add(body(_ul(
        "<b>Entry = row · row,</b> a sum over all joints: (x, x) = 2 total squared "
        "x-leverage; (y, y) = 6 total squared y-leverage; (x, y) = −3 x-y coupling "
        "(the joints that push up also push left).",
        "<b>The aim test:</b> move the joints in proportion to their leverage toward "
        "a direction d (that is Jᵀd). The tip actually goes along JJᵀd. Aim at x: "
        "the tip moves (2, −3), it <b>leaks</b> into y. Aim at u₁ = (−0.47, 0.88): "
        "the tip moves 7.6 × u₁, <b>straight</b>, no leak.",
        "<b>'Decoupled'</b> means u₁ and u₂ are the directions where aiming by "
        "leverage sends the tip straight where you aimed. The individual joint "
        "arrows still tilt, but their tilts cancel in the sum. These are the axes "
        "of the manipulability ellipse.",
        "Its eigenvalues are the same nonzero σ² as JᵀJ's, with no extra zero.")))
    return c


def inverse_card() -> Card:
    c = Card("7 · the inverse")
    c.add(body(
        "For JJᵀ = QΛQᵀ the inverse is QΛ⁻¹Qᵀ: the same axes, dividing by each "
        "stretch instead of multiplying."))
    return c


def pinv_card() -> Card:
    c = Card("8 · the pseudoinverse is 'moment arm ÷ moment arm squared'")
    c.add(body(
        "<b>One joint:</b> ω = v / r = (r · v) / r². That is Jᵀ(JJᵀ)⁻¹ = r / r².<br>"
        "<b>Why the roundabout form:</b> a moment arm is an <b>arrow</b>, and you "
        "can't divide by an arrow. Instead <b>dot with the arrow</b> (Jᵀ) and "
        "<b>divide by its squared length</b> ((JJᵀ)⁻¹).<br>"
        "<b>Several joints, one direction:</b> each joint gets speed <b>in proportion "
        "to its lever</b>, divided by the <b>total</b> squared leverage: "
        "ωᵢ = rᵢv / Σr². Levers (2, 1), v = 1 → (0.4, 0.2). The joint with more "
        "leverage does more of the work.<br>"
        "<b>Two directions:</b> the total squared leverage is the coupled 2 × 2 JJᵀ. "
        "Decouple it into u₁ and u₂; in each direction it is the one-direction "
        "division:" + _ul(
            "(JJᵀ)⁻¹ <b>divides by σ²</b>",
            "Jᵀ hands the result to the joints by leverage and <b>puts one σ back</b> "
            "(Jᵀuᵢ = σᵢvᵢ)",
            "<b>Net:</b> divide by σ, i.e. divide by the moment arm")))
    c.add(math_label(r"J^{+}V_d=J^T(JJ^T)^{-1}V_d=\sum_i\frac{u_i\cdot V_d}{\sigma_i}\,v_i=V\Sigma^{+}U^TV_d", 16))
    c.add(body(
        "<b>Example, V<sub>d</sub> = (0, 1):</b> w = (JJᵀ)⁻¹V<sub>d</sub> = (1, 0.667). "
        "Each joint's speed = its arrow · w → <b>θ̇ = (0.333, −0.333, 0.667)</b>." + _ul(
            "<b>Minimum norm</b> because Jᵀ only builds leverage-type motion, so there "
            "is never a null-space part.",
            "The <b>full family</b> of solutions is J⁺V<sub>d</sub> + (any amount) × "
            "the null line.")))
    return c


def chain_card() -> Card:
    c = Card("9 · the whole chain in one line")
    c.add(body(
        "J (moment arms) → rows give leverage, and the null space is what is "
        "perpendicular to all of them → JᵀJ compares joints, and its eigen-mixes "
        "are independent channels (one of them is null) → JJᵀ compares hand "
        "directions, and its eigen-axes are where aiming by leverage goes straight "
        "→ the pseudoinverse is 'multiply by the moment arm, divide by the moment "
        "arm squared', done separately in each decoupled direction → add null-space "
        "motion for extra goals, like avoiding singularities, without the tip "
        "feeling it."))
    return c


CARDS = (intro_card, pinv_steps_card, spaces_card, null_card, eigen_card, avoid_card,
         jtj_card, jjt_card, inverse_card, pinv_card, chain_card)
