"""
Page 128 extras -- manipulability, question by question.

One running example throughout: the 2R arm, L = (1, 0.8), at θ = (0°, 90°),
J = [[−0.8, −0.8], [1, 0]]. Every card answers one question a learner asks
on first meeting JJᵀ, its eigenvalues, the singular values, the "best mix"
of joint speeds and the force ellipse. MixLab shows the mixes directly.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QPushButton

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, math_label, stat_row
from .robo_common import deg, draw_arm, labelled_slider, plain, square
from .robo_space_rigid import in_words

L2R = (1.0, 0.8)


def _table(head, rows):
    cell = f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}'"
    h = "".join(f"<th {cell} align='left'>{x}</th>" for x in head)
    r = "".join("<tr>" + "".join(f"<td {cell}>{x}</td>" for x in row) + "</tr>"
                for row in rows)
    return f"<table style='border-collapse:collapse'><tr>{h}</tr>{r}</table>"


def qa_intro_card() -> Card:
    c = Card("questions first: the whole page in twelve answers")
    c.add(in_words(
        "Below, each card answers one question, in the order they come up. "
        "They all use one example so the numbers can be checked by hand: the "
        "2R arm with L = (1, 0.8) at θ = (0°, 90°), whose Jacobian is "
        "J = [−0.8 −0.8; 1 0]. Column 1 (−0.8, 1) is the hand velocity from "
        "joint 1 alone at 1 rad/s, column 2 (−0.8, 0) from joint 2 alone."))
    c.add(body(_table(
        ("#", "question", "one-line answer"),
        [("1", "Is my picture of J right?", "yes: columns = joint screws now; Jθ̇ = the hand's twist"),
         ("2", "J already gives v. Why build anything else?",
          "J answers one θ̇ at a time; we want the best and worst over all θ̇"),
         ("3", "Why JJᵀ? What kind of matrix is it?", "symmetric, positive semi-definite, hand-sized"),
         ("4", "Why (JJᵀ)⁻¹ for velocity and JJᵀ for force?", "each is the matrix of one ellipse's equation"),
         ("5", "Why the trace and the determinant?", "the 2 × 2 shortcut for the characteristic equation"),
         ("6", "Doesn't every matrix have eigenvectors?", "no; symmetric ones always do, and they are perpendicular"),
         ("7", "What are singular values, and why the square root?", "J's gains; JJᵀ squares them"),
         ("8", "Rotate-stretch-rotate for J too?", "yes, but the two turns live in two different spaces"),
         ("9", "How did you get the axis (0.766, −0.643)?", "(A − λI)u = 0, one row is enough"),
         ("10", "What is the best mix and the worst mix?", "the joint-speed directions v₁ and v₂"),
         ("11", "What does 2.44 times longer mean?", "the fast direction is 2.44× faster than the slow one"),
         ("12", "What is the force ellipse, and why not eig(J)?", "unit torque → hand force; eig(J) mixes two spaces")])))
    return c


def q1_card() -> Card:
    c = Card("Q1 · Is my picture right? Columns = screw axes, Jθ̇ = the hand's screw")
    c.add(body(
        "<b>Yes, with one detail.</b> Column i of the space Jacobian is joint i's "
        "screw axis Sᵢ = (ω̂ᵢ, vᵢ) <i>where the joint is now</i>, i.e. carried to "
        "the current pose by the joints before it (page 124). The top half ω̂ᵢ "
        "is the axis direction (unit spin rate), the bottom half vᵢ = −ω̂ᵢ × qᵢ "
        "is the velocity of the point at the {s} origin, which is how the "
        "point qᵢ on the axis enters. 'Screw axis' is the name for a twist "
        "normalised to unit speed: ‖ω‖ = 1, or ‖v‖ = 1 for a slider."))
    c.add(body(
        "Each joint turning at θ̇ᵢ contributes the twist Sᵢθ̇ᵢ. Twists at the same "
        "reference point add, so the hand's twist is V = S₁θ̇₁ + S₂θ̇₂ + … = Jθ̇. "
        "That sum is again a twist, so it is again one screw: the hand is "
        "instantaneously screwing about one axis with one pitch, exactly as you "
        "said. <b>So J is already all the physics.</b> The rest of this page "
        "does not add physics; it summarises what J can do over <i>all</i> θ̇."))
    c.add(body(
        "<b>Linear vs angular.</b> For a spatial arm, J is 6 × n: three rows "
        "of spin (rad/s), three rows of linear velocity (m/s). You cannot put "
        "rad/s and m/s in one length, so the page splits J into J<sub>ω</sub> "
        "(top rows) and J<sub>v</sub> (bottom rows) and draws one ellipsoid "
        "each. The planar examples use only the hand point's (ẋ, ẏ), so their "
        "J is 2 × 2 or 2 × 3 and there is one ellipse."))
    return c


def q2_card() -> Card:
    c = Card("Q2 · J already maps θ̇ to v. Why bother with anything else?")
    c.add(body(
        "Because J answers a <b>one-at-a-time</b> question: 'for <i>this</i> "
        "θ̇, what is v?'. Manipulability asks an <b>all-at-once</b> question: "
        "'with a fixed budget of joint speed, ‖θ̇‖ = 1, what is the fastest "
        "the hand can go, in which direction, and what is the slowest?' "
        "That is a maximum and a minimum over infinitely many inputs. You "
        "cannot read it off J's entries, just as you cannot see a car's top "
        "speed by looking at one gear."))
    c.add(body(
        "To find the max and min of ‖Jθ̇‖ you square it (lengths are easier "
        "squared, no square root):"))
    c.add(math_label(
        r"\|J\dot\theta\|^2=(J\dot\theta)^T(J\dot\theta)=\dot\theta^T(J^TJ)\,\dot\theta"
        r"\qquad\mathrm{max/min\ over}\ \|\dot\theta\|=1", 16))
    c.add(body(
        "There it is: the moment you square a length, a product of J with its "
        "own transpose appears. JᵀJ (n × n, joint side) and JJᵀ (m × m, hand "
        "side) are the two ways to write it; they have the same non-zero "
        "eigenvalues. That is the only reason these products show up: "
        "<b>they are what 'length squared' looks like for a matrix</b>."))
    return c


def q3_card() -> Card:
    c = Card("Q3 · Why JJᵀ, and what kind of matrix is it?")
    c.add(body(
        "<b>What it is for.</b> We want the shape of the set of hand velocities "
        "{Jθ̇ : ‖θ̇‖ = 1}. That set lives in hand space, so we want a matrix "
        "that also lives in hand space (m × m: 2 × 2 here, 3 × 3 for "
        "J<sub>v</sub>). JJᵀ is that matrix, whatever the number of joints. "
        "For a 3R arm J is 2 × 3, but JJᵀ is still 2 × 2."))
    c.add(body(_table(
        ("property", "why", "consequence"),
        [("square, m × m", "(m × n)(n × m)", "eigenvalues make sense: it maps hand space to hand space"),
         ("symmetric", "(JJᵀ)ᵀ = (Jᵀ)ᵀJᵀ = JJᵀ", "real eigenvalues, perpendicular eigenvectors (Q6)"),
         ("positive semi-definite", "xᵀJJᵀx = (Jᵀx)ᵀ(Jᵀx) = ‖Jᵀx‖² ≥ 0", "every eigenvalue λ ≥ 0"),
         ("positive definite iff J has full row rank", "‖Jᵀx‖ = 0 only if x = 0",
          "λ &gt; 0 away from singularities; some λ = 0 exactly at one")])))
    c.add(body(
        "Example: JJᵀ = [−0.8 −0.8; 1 0][−0.8 1; −0.8 0] = "
        "<b>[1.28 −0.8; −0.8 1]</b>. Mirror-symmetric across the diagonal "
        "(both off-diagonal entries −0.8), and both eigenvalues will be "
        "positive because the arm is not singular. Entry (1,1) = 1.28 is the "
        "sum of squares of row 1 of J: how much x-velocity all joints "
        "together can make."))
    return c


def q4_card() -> Card:
    c = Card("Q4 · Why (JJᵀ)⁻¹ for the velocity ellipse, and JJᵀ for the force ellipse?")
    c.add(body(
        "<b>Velocity.</b> The rule is 'joint speeds of length 1'. Write it in "
        "terms of the hand velocity v instead of θ̇. If J is invertible, "
        "θ̇ = J⁻¹v, so"))
    c.add(math_label(
        r"1=\dot\theta^T\dot\theta=v^TJ^{-T}J^{-1}v=v^T(JJ^T)^{-1}v", 16))
    c.add(body(
        "That is the equation of an ellipse in v, and its matrix happens to "
        "be (JJᵀ)⁻¹. (The same result holds for a non-square J of full row "
        "rank, with θ̇ taken as the smallest joint speed giving v.) So the "
        "inverse is not a separate step you choose to do: it falls out of "
        "rewriting ‖θ̇‖ = 1 in hand terms."))
    c.add(body(
        "<b>Force.</b> Now the rule is 'joint torques of length 1'. Torques "
        "come from hand forces by τ = JᵀF, so"))
    c.add(math_label(r"1=\tau^T\tau=F^TJJ^TF", 16))
    c.add(body(
        "Same kind of ellipse, but with JJᵀ itself, no inverse. <b>General "
        "rule</b> for an ellipse xᵀBx = 1 with B symmetric positive: its axes "
        "are B's eigenvectors and its half-lengths are 1/√(eigenvalue of B). "
        "With B = (JJᵀ)⁻¹ the half-lengths are √λ = σ; with B = JJᵀ they are "
        "1/√λ = 1/σ. Same axes, reciprocal lengths: that is the whole "
        "velocity–force duality in one line."))
    return c


def q5_card() -> Card:
    c = Card("Q5 · Why compute the trace and the determinant?")
    c.add(body(
        "You guessed right: only to get the eigenvalues quickly. For any 2 × 2 "
        "matrix A = [a b; c d], det(A − λI) = (a − λ)(d − λ) − bc expands to"))
    c.add(math_label(
        r"\lambda^2-(a+d)\,\lambda+(ad-bc)=\lambda^2-(\mathrm{trace})\,\lambda+\det=0", 16))
    c.add(body(
        "Example: trace = 1.28 + 1 = 2.28, det = 1.28·1 − (−0.8)(−0.8) = 0.64, "
        "so λ² − 2.28λ + 0.64 = 0 and λ = 1.952, 0.328. For a 3 × 3 the "
        "polynomial is cubic and in practice you call a solver "
        "(numpy.linalg.eigh)."))
    c.add(body(
        "<b>They also mean something on their own.</b> trace = λ₁ + λ₂ = "
        "σ₁² + σ₂²: the sum of squares of all entries of J, a rough 'total "
        "speed'. det = λ₁λ₂ = (σ₁σ₂)²: the squared area of the ellipse up to "
        "π. √det(JJᵀ) = σ₁σ₂ = 0.8 is the manipulability μ₃, and for a "
        "square J it equals |det J| = L₁L₂|sin θ₂|."))
    return c


def q6_card() -> Card:
    c = Card("Q6 · 'Every matrix has eigenvectors' — and what is special about symmetric ones?")
    c.add(body(
        "<b>Correction first:</b> not every matrix has real eigenvectors. A "
        "rotation by 90° turns every arrow, so no direction survives "
        "(λ = ±i). And a non-symmetric matrix that does have them can have "
        "slanted ones: [1 1; 0 2] has eigenvectors (1, 0) and (1, 1), 45° "
        "apart, not 90°."))
    c.add(body(
        "<b>Symmetric matrices are guaranteed three good things</b> (the "
        "spectral theorem): (1) all eigenvalues are real; (2) eigenvectors "
        "for different eigenvalues are perpendicular; (3) there is a full set "
        "of them, one per dimension. That is exactly what an ellipse's axes "
        "need: real lengths, at right angles, one per dimension. Your summary "
        "is right: a symmetric A turns its eigenvectors onto x, y (Qᵀ), "
        "stretches each by λ (Λ), and turns back (Q): A = QΛQᵀ."))
    c.add(body(
        "<b>Why that matters here.</b> J itself is not symmetric (and often "
        "not even square), so its eigenvectors, when they exist, are not the "
        "ellipse's axes. JJᵀ is always symmetric, so its eigenvectors always "
        "are. Forming JJᵀ is how you get a matrix that has the right kind of "
        "eigenvectors to describe the ellipse."))
    return c


def q7_card() -> Card:
    c = Card("Q7 · What are singular values, and why the square root?")
    c.add(body(
        "<b>Definition in words.</b> σ₁ is the largest hand speed you can get "
        "from a unit joint-speed vector; σ₂ the smallest (for a square or "
        "full-rank J). In general there is one σ per hand dimension, sorted "
        "σ₁ ≥ σ₂ ≥ … ≥ 0, and each one belongs to a pair of directions: an "
        "input direction vᵢ (joint space) and an output direction uᵢ (hand "
        "space), with"))
    c.add(math_label(r"J\,v_i=\sigma_i\,u_i\qquad(\|v_i\|=\|u_i\|=1)", 17))
    c.add(body(
        "<b>Why the square root.</b> Apply Jᵀ to both sides and use Jᵀuᵢ = "
        "σᵢvᵢ (the same relation read backwards): JJᵀuᵢ = J(σᵢvᵢ) = σᵢ²uᵢ. So "
        "uᵢ is an eigenvector of JJᵀ and its eigenvalue is σᵢ². JJᵀ goes "
        "through J twice (once forward, once back), so it multiplies the gain "
        "twice: λ = σ². The square root undoes that. Units say the same: σ "
        "is in (m/s) per (rad/s); λ is that squared."))
    c.add(body(_table(
        ("property of σ", "what you gain from it"),
        [("always real and ≥ 0, for a matrix of any shape", "works for 2 × 3, 6 × 7, … where eigenvalues do not"),
         ("σ₁ = max ‖Jθ̇‖, σ<sub>min</sub> = min ‖Jθ̇‖ over ‖θ̇‖ = 1", "best and worst hand speed per unit effort"),
         ("number of σ &gt; 0 = rank J", "σ<sub>min</sub> = 0 ⇔ singular pose"),
         ("σ₁σ₂⋯ = √det(JJᵀ) (= |det J| if square)", "ellipse size: μ₃"),
         ("σ₁/σ<sub>min</sub>", "lopsidedness: μ₁ (Q11)"),
         ("J⁻¹ (or J⁺) has gains 1/σᵢ", "how much inverse kinematics amplifies errors"),
         ("JᵀF ellipse has half-lengths 1/σᵢ", "force capacity (Q12)")])))
    return c


def q8_card() -> Card:
    c = Card("Q8 · Is J also 'rotate, stretch, rotate back'?")
    c.add(body(
        "Almost. Every matrix is <b>rotate, stretch, rotate</b>, but for J the "
        "two rotations are <i>different</i>, because the input and output "
        "spaces are different:"))
    c.add(math_label(
        r"J=U\,\Sigma\,V^T:\quad V^T\ \mathrm{turns\ joint\ space},\ \ "
        r"\Sigma\ \mathrm{stretches\ by}\ \sigma_i,\ \ U\ \mathrm{turns\ into\ hand\ space}", 15))
    c.add(body(
        "Vᵀ turns the best joint mix v₁ onto the first axis and the worst mix "
        "v₂ onto the second. Σ multiplies those two numbers by σ₁ and σ₂. U "
        "sends the first axis to the hand direction u₁ and the second to u₂. "
        "For a symmetric A the two turns are the same Q and the same space, "
        "which is why there it was 'turn back'."))
    c.add(body(
        "And the link: JJᵀ = UΣVᵀVΣUᵀ = UΣ²Uᵀ, because VᵀV = I. That is a "
        "symmetric 'turn, stretch, turn back' with Q = U and Λ = Σ². So "
        "the eigenvectors of JJᵀ are the hand directions uᵢ, and its "
        "eigenvalues are σᵢ². Likewise JᵀJ = VΣ²Vᵀ: its eigenvectors are the "
        "joint mixes vᵢ."))
    return c


def q9_card() -> Card:
    c = Card("Q9 · The formula for the axis: how (0.766, −0.643) came out")
    c.add(body(
        "It is just the eigenvector definition rearranged: Au = λu ⇔ "
        "(A − λI)u = 0. Put in A = [1.28 −0.8; −0.8 1] and λ₁ = 1.952:"))
    c.add(math_label(
        r"\left(1.28-1.952\right)u_1-0.8\,u_2=0\ \Rightarrow\ u_2=-0.84\,u_1"
        r"\ \Rightarrow\ u=\frac{(1,\,-0.84)}{\sqrt{1+0.84^2}}=(0.766,\,-0.643)", 15))
    c.add(body(
        "Only the first row is needed: because det(A − λI) = 0, the second row "
        "says the same thing. Divide by the length to make it a unit vector. "
        "The sign is free, (−0.766, 0.643) is the same axis. The short axis "
        "needs no work at all: for a symmetric matrix it is perpendicular, "
        "u₂ = (0.643, 0.766). So the long axis points 40° below the x-axis "
        "(or 140°), the short one 50° above it."))
    return c


def q10_card() -> Card:
    c = Card("Q10 · 'Best mix' and 'worst mix' of joint speeds")
    c.add(body(
        "A <b>mix</b> is a joint-speed vector θ̇ = (θ̇₁, θ̇₂) with total size "
        "‖θ̇‖ = √(θ̇₁² + θ̇₂²) = 1 rad/s: how you split one unit of joint speed "
        "between the two joints. (1, 0) is 'joint 1 only', (0.71, 0.71) is "
        "'both equally, same sign', (0.71, −0.71) is 'both equally, opposite'. "
        "Every mix is a point on the unit circle in joint-speed space."))
    c.add(body(
        "<b>Best mix = v₁</b>, the joint-speed direction that gives the "
        "longest hand velocity. <b>Worst mix = v₂</b>, the shortest. They come "
        "from the SVD (the eigenvectors of JᵀJ). For the example:"))
    c.add(body(_table(
        ("mix", "θ̇ = (θ̇₁, θ̇₂)", "hand velocity Jθ̇ = θ̇₁·col 1 + θ̇₂·col 2", "speed"),
        [("best, v₁", "(0.899, 0.438)", "0.899·(−0.8, 1) + 0.438·(−0.8, 0) = (−1.070, 0.899)",
          "<b>1.397 = σ₁</b>, along u₁"),
         ("worst, v₂", "(0.438, −0.899)", "0.438·(−0.8, 1) − 0.899·(−0.8, 0) = (0.368, 0.438)",
          "<b>0.573 = σ₂</b>, along u₂"),
         ("joint 1 only", "(1, 0)", "(−0.8, 1)", "1.281"),
         ("joint 2 only", "(0, 1)", "(−0.8, 0)", "0.800")])))
    c.add(body(
        "<b>Read it with moment arms.</b> In the best mix both joints turn the "
        "same way and their velocity contributions 0.899·(−0.8, 1) = (−0.72, 0.90) "
        "and 0.438·(−0.8, 0) = (−0.35, 0) both push the hand left: they add. "
        "In the worst mix joint 2 turns backwards: joint 1 gives "
        "(−0.35, 0.44), joint 2 gives −0.899·(−0.8, 0) = (+0.72, 0). The "
        "sideways parts fight each other and what is left is short. Any other "
        "mix lands between 0.573 and 1.397."))
    c.add(body(
        "<b>'Perpendicular' twice.</b> The two mixes are perpendicular in "
        "joint space (0.899·0.438 + 0.438·(−0.899) = 0), and the two resulting "
        "hand velocities are perpendicular in hand space (they are the "
        "ellipse's axes). The lab below lets you turn the mix round the "
        "circle and watch the hand speed rise to σ₁ and fall to σ₂."))
    return c


def q11_card() -> Card:
    c = Card("Q11 · What does '2.44 times longer' mean?")
    c.add(body(
        "σ₁/σ₂ = 1.397/0.573 = 2.44 is the ratio of the ellipse's long axis to "
        "its short axis, the measure μ₁ (also called the <b>condition "
        "number</b> of J). Three ways to read it:"))
    c.add(body(
        "<b>Speed:</b> with the same joint-speed budget, the hand moves 2.44× "
        "faster along u₁ than along u₂. A task that needs speed along u₂ is "
        "2.44× harder at this pose.<br>"
        "<b>Effort:</b> to move the hand at 1 m/s you need 1/1.397 = 0.72 rad/s "
        "of joint speed along u₁, but 1/0.573 = 1.75 rad/s along u₂.<br>"
        "<b>Closeness to singular:</b> 1 means a circle, equally good in every "
        "direction (isotropic). It grows as the arm straightens and is ∞ at the "
        "singularity, where σ₂ = 0. At 2.44 this pose is comfortably far from "
        "singular."))
    return c


def q12_card() -> Card:
    c = Card("Q12 · The force ellipse, and why we do not use J's own eigenvalues")
    c.add(body(
        "<b>Force ellipse</b> = every hand force F the motors can hold with a "
        "torque budget ‖τ‖ = 1 N·m (τ = JᵀF). Q4 showed it has the same axes "
        "uᵢ with half-lengths 1/σᵢ. In the example: <b>1/0.573 = 1.75 N</b> "
        "along u₂ (the slow direction) but only <b>1/1.397 = 0.72 N</b> along "
        "u₁ (the fast one). Check: F = 1.75·u₂ needs τ = JᵀF = (0.438, −0.899), "
        "length exactly 1."))
    c.add(body(
        "<b>Why slow = strong, with moment arms.</b> τᵢ = (column i)·F: each "
        "joint feels the part of the force along its own velocity column. A "
        "force along u₂ is nearly perpendicular to both columns, so each "
        "joint feels little of it and a big force costs little torque. A "
        "force along u₁ lines up with both columns and loads both joints "
        "fully. Power says the same: τᵀθ̇ = Fᵀv, so a direction with a big "
        "speed gain must have a small force gain, like a bicycle's gears."))
    c.add(body(
        "<b>Why not eig(J)?</b> Jv = λv asks for a v that is both a joint-speed "
        "vector (input) and a hand velocity (output) pointing the same way. "
        "Those are different spaces with different units (rad/s versus m/s), "
        "so the question has no physical meaning. In the example eig(J) = "
        "−0.4 ± 0.8i: complex numbers that tell you nothing about speed. JJᵀ "
        "maps hand space to hand space, so its eigenvalues are meaningful; "
        "that is why we bother with it. <b>Summary:</b> J for one θ̇; JJᵀ (or the "
        "SVD of J) for the best, the worst and the shape over all θ̇."))
    return c


class MixLab:
    """Turn one unit of joint speed round the circle; watch the hand speed."""

    def __init__(self):
        c = self.card = Card("lab: spend 1 rad/s of joint speed — find the best and the worst mix")
        c.add(in_words(
            "Left: joint-speed space. The cyan arrow is your mix θ̇ on the unit "
            "circle; green is the best mix v₁, orange the worst v₂. Middle: the "
            "arm. Your mix becomes θ̇₁·(column 1) + θ̇₂·(column 2), drawn tip to "
            "tail in red and violet; their sum is the cyan hand velocity, and "
            "it always ends on the green ellipse. Right: hand speed for every "
            "mix. The top of the curve is σ₁ (at v₁), the bottom σ₂ (at v₂)."))
        self.q2 = labelled_slider(c, "θ₂ (elbow), θ₁ = 0", -170, 170, 90, deg, self._draw)
        self.mix = labelled_slider(c, "mix angle α: θ̇ = (cos α, sin α)", 0, 359, 0, deg, self._draw)
        row = QHBoxLayout()
        for name, fn in (("go to best mix v₁", lambda: self._goto(0)),
                         ("go to worst mix v₂", lambda: self._goto(1)),
                         ("sweep the mix", self._sweep)):
            b = QPushButton(name)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        c.add_layout(row)
        self.st_m = Stat("mix θ̇", "--", theme.CYAN)
        self.st_v = Stat("hand speed ‖Jθ̇‖", "--", theme.ACCENT)
        self.st_s = Stat("σ₁ (best), σ₂ (worst)", "--", theme.GOOD)
        self.st_k = Stat("σ₁/σ₂", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_m, self.st_v, self.st_s, self.st_k))
        self.cv = MplCanvas(width=8.2, height=3.6, ncols=3)
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Press the two 'go to' buttons at θ₂ = 90°: you get "
            "(0.90, 0.44) → 1.40 m/s and (0.44, −0.90) → 0.57 m/s, the numbers "
            "of Q10. Watch the red and violet arrows: in the best mix they point "
            "the same way, in the worst they partly cancel. (2) Sweep: the cyan "
            "hand arrow runs round the ellipse while the mix runs round the "
            "circle. The circle maps onto the ellipse. (3) Bring θ₂ towards 0°. "
            "The curve on the right flattens to zero at its bottom: there is a "
            "mix that gives no hand speed at all, the null direction of a "
            "singular J. (4) The curve repeats every 180°: θ̇ and −θ̇ give the "
            "same speed in opposite directions, which is why an axis has no "
            "arrowhead."))
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.mix.setValue((self.mix.value() + 3) % 360))
        self._goto(0)

    def _svd(self):
        J = rk.planar_jacobian(L2R, [0.0, math.radians(self.q2.value())])
        U, s, Vt = np.linalg.svd(J)
        return J, U, s, Vt.T

    def _goto(self, i):
        self.timer.stop()
        _, _, _, V = self._svd()
        v = V[:, i]
        if v[0] < 0:
            v = -v
        self.mix.setValue(int(round(math.degrees(math.atan2(v[1], v[0])))) % 360)
        self._draw()

    def _sweep(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(50)

    def _draw(self, *_):
        J, U, s, V = self._svd()
        a = math.radians(self.mix.value())
        th = np.array([math.cos(a), math.sin(a)])
        v = J @ th
        self.st_m.set(f"({th[0]:+.2f}, {th[1]:+.2f})")
        self.st_v.set(f"{np.linalg.norm(v):.3f} m/s")
        self.st_s.set(f"{s[0]:.3f}, {s[1]:.3f}")
        self.st_k.set("∞" if s[1] < 1e-9 else f"{s[0] / s[1]:.2f}")
        c = self.cv
        c.clear()
        a1, a2, a3 = c.axes
        t = np.linspace(0, 2 * math.pi, 120)
        circ = np.vstack([np.cos(t), np.sin(t)])
        a1.plot(*circ, color=theme.TEXT_DIM, lw=1.2)
        for k, col, nm in ((0, theme.GOOD, "v₁ best"), (1, theme.WARN, "v₂ worst")):
            d = V[:, k] * (1 if V[0, k] >= 0 else -1)
            a1.plot(*np.vstack([-d, d]).T, "--", color=col, lw=1.2)
            a1.text(*(1.08 * d), nm, color=col, fontsize=8)
        a1.annotate("", xy=th, xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color=theme.CYAN, lw=2.4))
        square(a1, 1.4)
        a1.set_xlabel("θ̇₁ (rad/s)")
        a1.set_ylabel("θ̇₂ (rad/s)")
        a1.set_title("joint speeds: ‖θ̇‖ = 1")
        q = [0.0, math.radians(self.q2.value())]
        tip = draw_arm(a2, L2R, q)[-1]
        k = 0.8
        a2.plot(*(tip[:, None] + k * (U @ np.diag(s) @ circ)), color=theme.GOOD, lw=1.8)
        p1 = tip + k * th[0] * J[:, 0]
        for p0, p1_, col in ((tip, p1, theme.BAD), (p1, p1 + k * th[1] * J[:, 1], theme.VIOLET)):
            a2.annotate("", xy=p1_, xytext=p0,
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=1.8))
        a2.annotate("", xy=tip + k * v, xytext=tip,
                    arrowprops=dict(arrowstyle="-|>", color=theme.CYAN, lw=2.4))
        a2.set_xlim(tip[0] - 1.5, tip[0] + 1.5)
        a2.set_ylim(tip[1] - 1.5, tip[1] + 1.5)
        a2.set_aspect("equal", adjustable="box")
        a2.set_title("θ̇₁·col 1 + θ̇₂·col 2 = Jθ̇ (×0.8)")
        al = np.radians(np.arange(0, 360, 1.0))
        sp = np.linalg.norm(J @ np.vstack([np.cos(al), np.sin(al)]), axis=0)
        a3.plot(np.degrees(al), sp, color=theme.ACCENT, lw=1.8)
        a3.axhline(s[0], color=theme.GOOD, ls="--", lw=1)
        a3.axhline(s[1], color=theme.WARN, ls="--", lw=1)
        a3.text(4, s[0] + 0.03, "σ₁", color=theme.GOOD, fontsize=9)
        a3.text(4, s[1] + 0.03, "σ₂", color=theme.WARN, fontsize=9)
        a3.axvline(self.mix.value(), color=theme.CYAN, lw=1.2)
        a3.set_xlim(0, 360)
        a3.set_ylim(0, max(2.0, s[0] + 0.2))
        a3.set_xlabel("mix angle α (deg)")
        a3.set_title("hand speed per unit joint speed")
        c.refresh()
