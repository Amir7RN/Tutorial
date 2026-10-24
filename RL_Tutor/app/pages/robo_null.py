"""
Page 130 extras -- the pseudoinverse and the null space, from scratch, on ONE
example: the planar 3R arm with joints at (0, 0), (1, 0), (1, 1) and the tip
at (2, 1), i.e. L = (1, 1, 1), θ = (0°, 90°, −90°):

    J = [−1 −1 0; 2 1 1]      columns = tip velocities (−1, 2), (−1, 1), (0, 1)

Ten short steps, every number checkable by hand, then a 3-D lab of the four
fundamental subspaces in which the whole story can be watched at once.
"""

from __future__ import annotations

import math

import numpy as np

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, math_label, stat_row
from .robo_common import deg, draw_arm, labelled_slider, mat_html, plain, square
from .robo_space_rigid import in_words
from .robo_space_topo import _clear, _layout

L3 = (1.0, 1.0, 1.0)
Q_EX = np.radians([0.0, 90.0, -90.0])


def _table(head, rows):
    cell = f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}'"
    h = "".join(f"<th {cell} align='left'>{x}</th>" for x in head)
    r = "".join("<tr>" + "".join(f"<td {cell}>{x}</td>" for x in row) + "</tr>"
                for row in rows)
    return f"<table style='border-collapse:collapse'><tr>{h}</tr>{r}</table>"


def _m(rows):
    """A small matrix written with brackets, rows separated by line breaks."""
    return "<span style='font-family:Consolas'>" + "<br>".join(
        "[ " + "  ".join(f"{x:>5}" for x in r).replace(" ", "&nbsp;") + " ]" for r in rows) + "</span>"


def roadmap_card() -> Card:
    c = Card("the pseudoinverse and the null space, step by step, on one arm")
    c.add(in_words(
        "Everything on this page answers one question: <b>given the hand "
        "velocity V you want, which joint speeds θ̇ should you use?</b> With "
        "Jθ̇ = V and a square, healthy J the answer is θ̇ = J⁻¹V and the story "
        "ends. This page is about what to do when J is not square (more joints "
        "than needed, or fewer) or is singular. The ten steps below use one "
        "arm, so every number can be checked with a pencil."))
    c.add(body(
        "<b>The example.</b> A planar 3R arm with all links 1 m long, at "
        "θ = (0°, 90°, −90°): joint 1 at (0, 0), joint 2 at (1, 0), joint 3 at "
        "(1, 1), tip at (2, 1). Task: the tip's (ẋ, ẏ), two numbers. Three "
        "joints for two task numbers: one joint too many, the redundant case."))
    c.add(body(_table(
        ("step", "question it answers"),
        [("1", "what does J look like here, read by columns and by rows?"),
         ("2", "why is there no unique answer, and what do all the answers look like?"),
         ("3", "what are JᵀJ and JJᵀ, and how do they connect?"),
         ("4", "four pieces, two in joint space and two in hand space: the map of the whole problem"),
         ("5", "how to find U, Σ, V for any matrix (the SVD recipe)"),
         ("6", "applying J through its SVD: project, stretch, build"),
         ("7", "the pseudoinverse = the SVD run backwards"),
         ("8", "the same answer the leverage way: Jᵀ(JJᵀ)⁻¹"),
         ("9", "why J⁺ gives the shortest θ̇, and what N = I − J⁺J does"),
         ("10", "the other cases: too few joints, singular, weighted")])))
    return c


def s1_card() -> Card:
    c = Card("step 1 · J read two ways: columns are joints, rows are hand directions")
    c.add(body(
        "Each column is one joint's tip velocity at 1 rad/s, ẑ × (tip − jointᵢ) "
        "(the moment arm turned 90°, page 124):"))
    c.add(body(_table(
        ("joint", "at", "tip − joint", "column = ẑ × (tip − joint)"),
        [("1", "(0, 0)", "(2, 1)", "(−1, 2)"),
         ("2", "(1, 0)", "(1, 1)", "(−1, 1)"),
         ("3", "(1, 1)", "(1, 0)", "(0, 1)")])))
    c.add(body(
        "J = <b>[ −1 −1 0 ; 2 1 1 ]</b>, 2 rows (hand x, hand y) by 3 columns "
        "(joints 1, 2, 3).<br>"
        "<b>Columns</b> answer 'what does joint i do to the tip?'. "
        "<b>Rows</b> answer 'how much does each joint push the tip in direction "
        "x (or y)?'. Row y = (2, 1, 1) is each joint's horizontal distance to "
        "the tip; row x = (−1, −1, 0) is minus each joint's height below the "
        "tip. Call a row a <b>leverage pattern</b>: it lists every joint's "
        "leverage on one hand direction."))
    c.add(body(
        "Jθ̇ = θ̇₁·(column 1) + θ̇₂·(column 2) + θ̇₃·(column 3) is the column "
        "reading. Entry k of Jθ̇ = (row k) · θ̇ is the row reading. Same numbers, "
        "two pictures. You need both below."))
    return c


def s2_card() -> Card:
    c = Card("step 2 · two equations, three unknowns: a whole line of answers")
    c.add(body(
        "Ask for V<sub>d</sub> = (0, 1): tip straight up at 1 m/s. Jθ̇ = V<sub>d</sub> is"))
    c.add(math_label(r"-\dot\theta_1-\dot\theta_2=0,\qquad 2\dot\theta_1+\dot\theta_2+\dot\theta_3=1", 17))
    c.add(body(
        "Two equations, three unknowns: one degree of freedom is left over. "
        "θ̇ = (1/3, −1/3, 2/3) works (check: −1/3 + 1/3 = 0, 2/3 − 1/3 + 2/3 = 1). "
        "So does (1/3, −1/3, 2/3) + t·(1, −1, −1) for <b>any</b> t, because "
        "J(1, −1, −1) = (−1 + 1 + 0, 2 − 1 − 1) = (0, 0): that joint motion does "
        "nothing to the tip. It is the <b>null space</b> of J, the elbow "
        "swinging while the tip stays still."))
    c.add(body(
        "<b>Picture in joint-speed space (3-D):</b> each equation is a plane; "
        "two planes meet in a line; every point of that line is an exact "
        "answer. J⁻¹ does not exist (J is not square), so 'the' answer has to "
        "be chosen. The pseudoinverse picks the point of the line closest to "
        "the origin: the least joint motion. The lab at the end draws this line."))
    return c


def s3_card() -> Card:
    c = Card("step 3 · JᵀJ and JJᵀ: the same arrows, compared two ways")
    c.add(body(_table(
        ("", "JᵀJ (3 × 3, joint side)", "JJᵀ (2 × 2, hand side)"),
        [("entry (i, j)", "column i · column j", "row i · row j"),
         ("meaning", "how much joints i and j push the tip the same way; "
          "diagonal = squared moment arm of each joint",
          "how much the x-pattern and y-pattern of leverage overlap; "
          "diagonal = total squared leverage on x, on y"),
         ("here", _m([[5, 3, 2], [3, 2, 1], [2, 1, 1]]), _m([[2, -3], [-3, 6]])),
         ("eigenvectors", "the joint mixes v₁, v₂, v₃", "the hand directions u₁, u₂"),
         ("eigenvalues", "σ₁² = 7.606, σ₂² = 0.394, and 0", "σ₁² = 7.606, σ₂² = 0.394")])))
    c.add(body(
        "<b>The link to your screw-axis columns.</b> JJᵀ is also the sum of "
        "each column times itself, the 'spread' of the three arrows over the "
        "hand plane:"))
    c.add(body(
        "JJᵀ = (−1, 2)(−1, 2)ᵀ + (−1, 1)(−1, 1)ᵀ + (0, 1)(0, 1)ᵀ = "
        "[1 −2; −2 4] + [1 −1; −1 1] + [0 0; 0 1] = <b>[2 −3; −3 6]</b>. "
        "So 'rows · rows' and 'sum of column outer products' are the same matrix."))
    c.add(plain(
        "Both matrices are symmetric (so their eigenvectors are perpendicular) "
        "and both have the <b>same non-zero eigenvalues σ²</b>: they describe "
        "the same three arrows. JᵀJ compares the arrows with each other (one "
        "row and column per joint); JJᵀ measures how the arrows spread over the "
        "hand plane. The eigenvalues are the stretch <i>squared</i>; σ itself "
        "is the square root (√7.606 = 2.758, √0.394 = 0.628). JᵀJ has one extra "
        "eigenvalue 0, for the null direction: three joint directions, only "
        "two can reach the hand."))
    return c


def s4_card() -> Card:
    c = Card("step 4 · the four fundamental subspaces: the map of the whole problem")
    c.add(in_words(
        "Every matrix splits its input space into two perpendicular pieces and "
        "its output space into two perpendicular pieces. Once you know the "
        "four pieces, J, Jᵀ, J⁺ and the null-space projector are all just "
        "'which piece goes where'. Two pieces live in joint space, two in "
        "hand space, and this page names them that way."))
    c.add(body(_table(
        ("piece", "lives in", "SVD vectors", "robot meaning", "here"),
        [("<b>joint working space</b>", "joint speeds (ℝ³)", "vᵢ with σᵢ &gt; 0",
          "joint mixes that move the tip", "the plane spanned by the rows (−1, −1, 0) and (2, 1, 1)"),
         ("<b>joint null space</b>", "joint speeds", "vᵢ with σᵢ = 0 (and extra vᵢ)",
          "self-motion: the tip does not feel it", "the line through (1, −1, −1)"),
         ("<b>hand reachable space</b>", "hand velocities (ℝ²)", "uᵢ with σᵢ &gt; 0",
          "tip velocities you can make", "the whole plane (rank 2)"),
         ("<b>hand unreachable space</b>", "hand velocities", "uᵢ with σᵢ = 0",
          "tip directions you cannot make", "nothing here; appears at a singularity")])))
    c.add(plain(
        "Textbook names, only for reading Strang or the book: joint working "
        "space = <i>row space</i>, joint null space = <i>null space</i>, hand "
        "reachable space = <i>column space</i>, hand unreachable space = "
        "<i>left null space</i>."))
    c.add(body(
        "<b>Perpendicular pairs.</b> Joint null space ⟂ joint working space: (1, −1, −1) · (−1, −1, 0) "
        "= 0 and (1, −1, −1) · (2, 1, 1) = 0. That is no accident: Jn = 0 says "
        "exactly 'every row dotted with n is 0'. Same on the hand side: hand "
        "reachable space ⟂ hand unreachable space."))
    c.add(body(
        "<b>What J does:</b> it maps the joint working space onto the hand "
        "reachable space (one to one, stretching by σᵢ) and sends the joint "
        "null space to zero.<br>"
        "<b>What J⁺ does:</b> the exact reverse: maps the hand reachable space "
        "back onto the joint working space (dividing by σᵢ) and sends the hand "
        "unreachable space to zero."))
    return c


def s5_card() -> Card:
    c = Card("step 5 · finding U, Σ and V for any matrix")
    c.add(body(
        "<b>The one pair of equations to remember</b> (careful with which is "
        "which):"))
    c.add(math_label(r"J\,v_i=\sigma_i\,u_i\qquad\qquad J^T u_i=\sigma_i\,v_i", 18))
    c.add(body(
        "J takes a joint mix vᵢ to a hand direction uᵢ, stretched by σᵢ. Jᵀ "
        "takes uᵢ back to vᵢ, stretched by the same σᵢ. (Jᵀv = σu is wrong: "
        "v lives in joint space and Jᵀ needs a hand-space input.)<br>"
        "<b>Recipe, hand side first</b> (the smaller matrix here):"))
    c.add(body(_table(
        ("", "do", "here"),
        [("1", "eigen of JJᵀ → the uᵢ and σᵢ²",
          "JJᵀ = [2 −3; −3 6]: λ = 7.606, 0.394 → σ = 2.758, 0.628; "
          "u₁ = (−0.472, 0.882), u₂ = (0.882, 0.472)"),
         ("2", "vᵢ = Jᵀuᵢ / σᵢ (from the second equation)",
          "v₁ = Jᵀu₁ / 2.758 = (0.811, 0.491, 0.320); v₂ = (0.099, −0.653, 0.751)"),
         ("3", "complete V with unit vectors ⟂ to all vᵢ found so far: the null space",
          "v₃ = (1, −1, −1)/√3 = (0.577, −0.577, −0.577)")])))
    c.add(body(
        "<b>Or joint side first:</b> eigen of JᵀJ gives the vᵢ and σᵢ², then "
        "uᵢ = Jvᵢ / σᵢ. Same SVD (up to the sign of each pair). Use whichever "
        "matrix is smaller."))
    return c


def s6_card() -> Card:
    c = Card("step 6 · applying J through its SVD: project, stretch, build")
    c.add(body(
        "J = UΣVᵀ, read right to left, applied to a joint-speed vector θ̇:"))
    c.add(body(_table(
        ("", "operation", "meaning", "θ̇ = (1, 0, 0), joint 1 alone"),
        [("Vᵀθ̇", "three dot products vᵢ · θ̇",
          "how much of θ̇ lies along each special joint mix (projection; equivalently, "
          "turn the vᵢ onto the axes and read the coordinates)",
          "(0.811, 0.099, 0.577)"),
         ("Σ(…)", "multiply coordinate i by σᵢ; σ₃ = 0 drops coordinate 3",
          "the null part is thrown away here, which is why it never reaches the tip",
          "(2.235, 0.062)"),
         ("U(…)", "2.235·u₁ + 0.062·u₂",
          "build the hand velocity out of the hand directions",
          "(−1, 2) = column 1 ✓")])))
    c.add(plain(
        "Doing Jθ̇ directly gives the same (−1, 2), of course. The SVD route is "
        "not for computing; it is for <b>seeing</b>: which part of θ̇ matters "
        "(the joint working part), how much each part is amplified (σᵢ), and which "
        "part is lost entirely (the null part, 0.577 of this θ̇)."))
    return c


def s7_card() -> Card:
    c = Card("step 7 · the pseudoinverse is the SVD run backwards")
    c.add(math_label(r"J=U\,\Sigma\,V^T\qquad\Rightarrow\qquad J^{+}=V\,\Sigma^{+}U^T,\qquad"
                     r"\Sigma^{+}:\ \sigma_i\to1/\sigma_i\ (\sigma_i>0),\ \ 0\to0", 16))
    c.add(body(_table(
        ("", "operation", "meaning", "V<sub>d</sub> = (0, 1)"),
        [("UᵀV<sub>d</sub>", "dot products uᵢ · V<sub>d</sub>",
          "the request, measured along the two hand directions", "(0.882, 0.472)"),
         ("Σ⁺(…)", "divide coordinate i by σᵢ",
          "weak direction (small σ) needs more joint speed; σ = 0 directions are skipped",
          "(0.882/2.758, 0.472/0.628) = (0.320, 0.751)"),
         ("V(…)", "0.320·v₁ + 0.751·v₂",
          "build the joint speeds out of the joint mixes; <b>nothing on v₃</b>",
          "(0.333, −0.333, 0.667)")])))
    c.add(body(
        "That is the whole definition. J⁺V<sub>d</sub> = (1/3, −1/3, 2/3), the "
        "answer of step 2. 'Inverse' only where an inverse makes sense: on "
        "the reachable hand directions, back into the joint mixes that make "
        "them. Directions that J kills (joint null space) or cannot reach (hand "
        "unreachable space) are simply left out."))
    return c


def s8_card() -> Card:
    c = Card("step 8 · the same answer the leverage way: J⁺ = Jᵀ(JJᵀ)⁻¹")
    c.add(body(
        "When J can reach every hand direction (here: yes, rank 2) there is a formula without "
        "the SVD. It means the same thing, in x and y instead of u₁ and u₂."))
    c.add(body(
        "<b>One task number first.</b> Want only ẏ = 1: 2θ̇₁ + θ̇₂ + θ̇₃ = 1, a "
        "plane in joint space. Its closest point to the origin lies along the "
        "plane's normal, the coefficient vector (2, 1, 1), which is row y, the "
        "leverage pattern. So θ̇ = c(2, 1, 1) with (4 + 1 + 1)c = 1, c = 1/6. "
        "<b>Jᵀ gives the direction</b> (move each joint in proportion to its "
        "leverage), <b>(JJᵀ)⁻¹ gives the amount</b> (6 = row y · row y)."))
    c.add(body(
        "<b>Two task numbers: cross-talk.</b> (1/6)(2, 1, 1) gives Jθ̇ = (−0.5, 1): "
        "y is right but x leaks, because the joints you moved for y also lever "
        "x. JJᵀ = [2 −3; −3 6] is the cross-talk table: the −3 says the x- and "
        "y-patterns overlap. (JJᵀ)⁻¹(0, 1) = (1, 0.667) blends the patterns so "
        "the leaks cancel: θ̇ = 1·(−1, −1, 0) + 0.667·(2, 1, 1) = (1/3, −1/3, 2/3). "
        "Same answer as step 7."))
    c.add(body(
        "<b>Why they agree.</b> In the u-directions there is no cross-talk "
        "(JJᵀ is diagonal there, σ₁², σ₂²), so 'untangling' is plain division, "
        "and Jᵀuᵢ = σᵢvᵢ turns each leverage pattern into a joint mix:"))
    c.add(math_label(r"J^T(JJ^T)^{-1}V_d=\sum_i\frac{u_i\cdot V_d}{\sigma_i^2}\,J^Tu_i="
                     r"\sum_i\frac{u_i\cdot V_d}{\sigma_i}\,v_i=V\Sigma^{+}U^TV_d", 16))
    c.add(plain(
        "Use the SVD form as the definition (it always exists, any shape, any "
        "rank) and Jᵀ(JJᵀ)⁻¹ as the quick formula when JJᵀ is invertible. At a "
        "singularity JJᵀ has no inverse and the formula breaks, but VΣ⁺Uᵀ just "
        "skips the σ = 0 direction."))
    return c


def s9_card() -> Card:
    c = Card("step 9 · why J⁺ is the shortest answer, and what N = I − J⁺J does")
    c.add(body(
        "<b>Shortest.</b> Every exact answer is θ̇* + t·n with θ̇* = J⁺V<sub>d</sub> "
        "and n = (1, −1, −1) in the null space. θ̇* is built from v₁ and v₂ only "
        "(joint working space), n is along v₃, and joint working space ⟂ "
        "joint null space, so by "
        "Pythagoras ‖θ̇* + tn‖² = ‖θ̇*‖² + t²‖n‖². Any t ≠ 0 makes it longer. "
        "Numbers: ‖(1/3, −1/3, 2/3)‖ = 0.816; add one unit of v₃ and it is 1.291."))
    c.add(body(
        "<b>J⁺J and I − J⁺J.</b> J⁺J first maps θ̇ to the hand and then back: "
        "the null part is lost on the way, the working part comes back "
        "unchanged. So J⁺J = projector onto the joint working space, and"))
    c.add(math_label(r"N=I-J^{+}J=v_3v_3^T=\frac{1}{3}\left[\ \ 1\ -1\ -1;\ \ -1\ \ 1\ \ 1;\ \ -1\ \ 1\ \ 1\ \right]", 15))
    c.add(body(
        "is the projector onto the joint null space: it keeps only the part of a "
        "joint motion along v₃. Example: θ̇₀ = (1, 0, 0) ('turn joint 1') becomes "
        "Nθ̇₀ = (1/3)(1, −1, −1): turn joint 1 a bit, joints 2 and 3 back, and "
        "the tip stays put. Check: J·(1, −1, −1) = 0.<br>"
        "<b>The redundancy formula</b> now reads itself:"))
    c.add(math_label(r"\dot\theta=\underbrace{J^{+}V_d}_{\mathrm{joint\ working\ part:\ does\ the\ task}}"
                     r"+\underbrace{(I-J^{+}J)\,\dot\theta_0}_{\mathrm{joint\ null\ part:\ invisible\ to\ the\ tip}}", 16))
    c.add(plain(
        "The two pieces live in perpendicular parts of joint space, so they cannot "
        "interfere: whatever θ̇₀ you choose (away from joint limits, towards "
        "high manipulability, away from an obstacle), N strips its working "
        "part and the task is untouched. Forgetting N is the classic bug: θ̇₀'s "
        "working part leaks into the hand (the self-motion lab below has a "
        "'WRONG' option that shows exactly that)."))
    return c


def s10_card() -> Card:
    c = Card("step 10 · the other cases: too few joints, singular, weighted")
    c.add(body(_table(
        ("case", "what the four pieces look like", "what J⁺V<sub>d</sub> gives"),
        [("fat, rank = rows (our arm)", "joint null space ≠ {0}, hand unreachable space = {0}",
          "exact, shortest θ̇; = Jᵀ(JJᵀ)⁻¹V<sub>d</sub>"),
         ("tall, rank = columns (e.g. the 6 × 4 RRPR J)", "joint null space = {0}, hand unreachable space ≠ {0}",
          "the θ̇ whose twist is closest to V<sub>d</sub> (least squares); = (JᵀJ)⁻¹JᵀV<sub>d</sub>; "
          "the unreachable part of V<sub>d</sub> is simply impossible"),
         ("singular (our arm straightened: θ = 0)", "a σ hits 0: both null pieces grow",
          "closest twist, and among those the shortest θ̇; only VΣ⁺Uᵀ works"),
         ("nearly singular", "a σ is tiny: 1/σ is huge",
          "violent joint speeds; damp: σ/(σ² + λ²) instead of 1/σ")])))
    c.add(body(
        "<b>Weighted.</b> 'Shortest' measured as θ̇ᵀWθ̇ instead of Σθ̇ᵢ² makes "
        "some joints expensive: J<sub>W</sub>⁺ = W⁻¹Jᵀ(JW⁻¹Jᵀ)⁻¹. With W = M(θ) "
        "the 'cost' is kinetic energy, which is the dynamically consistent "
        "inverse of the task-space dynamics page (138). Same idea every time: "
        "among all θ̇ that do the job, pick the cheapest by your measure."))
    c.add(plain(
        "<b>If you want to read more:</b> Gilbert Strang's MIT 18.06 lectures "
        "on the four fundamental subspaces and on the SVD (free on MIT "
        "OpenCourseWare), and 3Blue1Brown's 'Essence of Linear Algebra' series "
        "for the geometric feel. Once the joint/hand four-piece picture clicks, J, Jᵀ, "
        "J⁺ and N are all 'which piece goes where'."))
    return c


class FourSubspacesLab:
    """Joint-speed space in 3-D: working plane, null line, the line of exact answers."""

    def __init__(self):
        c = self.card = Card("lab (3-D): joint and hand spaces, the line of answers and J⁺")
        c.add(in_words(
            "Left, joint-speed space (θ̇₁, θ̇₂, θ̇₃). The translucent plane is the "
            "joint working space (spanned by v₁, v₂), the red line is the joint "
            "null space (v₃). "
            "The orange line is every θ̇ with Jθ̇ = V<sub>d</sub>; it runs "
            "parallel to the null line. The cyan dot is J⁺V<sub>d</sub>: where the "
            "orange line pierces the working plane, its closest point to the "
            "origin. The yellow dot is J⁺V<sub>d</sub> + t·v₃ (null slider). Right: "
            "the arm, its three column arrows, and the tip velocity produced by "
            "the yellow θ̇, which never changes when you move t."))
        self.q = [labelled_slider(c, f"arm θ{i+1}", -180, 180, v, deg, self._draw)
                  for i, v in enumerate((0, 90, -90))]
        self.ang = labelled_slider(c, "V_d direction", -180, 180, 90, deg, self._draw)
        self.mag = labelled_slider(c, "V_d size", 0, 20, 10, lambda v: f"{v/10:.1f} m/s", self._draw)
        self.t = labelled_slider(c, "null motion t (along v₃)", -15, 15, 0,
                                 lambda v: f"{v/10:+.1f}", self._draw)
        self.st_s = Stat("σ₁, σ₂", "--", theme.GOOD)
        self.st_p = Stat("J⁺V_d (‖·‖)", "--", theme.CYAN)
        self.st_y = Stat("yellow θ̇ (‖·‖)", "--", theme.WARN)
        self.st_v = Stat("J · yellow θ̇", "--", theme.ACCENT)
        c.add_layout(stat_row(self.st_s, self.st_p, self.st_y, self.st_v))
        self.txt = body("")
        c.add(self.txt)
        self.cv = MplCanvas(width=8.2, height=4.6)
        _layout(self.cv, ["3d", "2d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Defaults are the example: V<sub>d</sub> = (0, 1), "
            "J⁺V<sub>d</sub> = (0.33, −0.33, 0.67), ‖·‖ = 0.816. (2) Move t: the "
            "yellow dot slides along the orange line, its length grows, and J·θ̇ "
            "on the right stays exactly V<sub>d</sub>: that is null motion. "
            "(3) Turn V<sub>d</sub>: the orange line moves but always stays "
            "parallel to the red null line, and the cyan dot always stays in the "
            "plane. (4) Change the arm pose: the plane and the null line tilt; J "
            "is a different matrix, same four-piece picture. (5) Set θ₂ = θ₃ "
            "= 0 (arm straight): σ₂ → 0, the working space collapses to a line, the "
            "joint null space becomes a plane, and most V<sub>d</sub> can no longer be "
            "made exactly. The step-by-step numbers of step 7 are printed above "
            "the plot for whatever you choose."))
        self._draw()

    def _draw(self, *_):
        q = np.radians([s.value() for s in self.q])
        J = rk.planar_jacobian(L3, q)
        U, s, Vt = np.linalg.svd(J)
        V = Vt.T
        a = math.radians(self.ang.value())
        Vd = self.mag.value() / 10 * np.array([math.cos(a), math.sin(a)])
        r = int(np.sum(s > 1e-6))
        sp = np.array([1 / x if x > 1e-6 else 0.0 for x in s])
        c1 = U.T @ Vd
        c2 = sp * c1
        p = V[:, :2] @ c2
        n = V[:, 2] * (1 if V[0, 2] >= 0 else -1)
        y = p + self.t.value() / 10 * n
        self.st_s.set(f"{s[0]:.3f}, {s[1]:.3f}")
        self.st_p.set("(" + ", ".join(f"{x:+.2f}" for x in p) + f") ({np.linalg.norm(p):.3f})")
        self.st_y.set("(" + ", ".join(f"{x:+.2f}" for x in y) + f") ({np.linalg.norm(y):.3f})")
        Jy = J @ y
        self.st_v.set(f"({Jy[0]:+.2f}, {Jy[1]:+.2f})")
        self.txt.setText(
            f"J = {mat_html(J, 2)} UᵀV<sub>d</sub> = ({c1[0]:+.3f}, {c1[1]:+.3f}) → ÷σ → "
            f"({c2[0]:+.3f}, {c2[1]:+.3f}) → build on v₁, v₂ → J⁺V<sub>d</sub> = "
            f"({p[0]:+.3f}, {p[1]:+.3f}, {p[2]:+.3f}). "
            f"<span style='color:{theme.TEXT_DIM}'>rank J = {r}; null direction v₃ = "
            f"({n[0]:+.3f}, {n[1]:+.3f}, {n[2]:+.3f})</span>")
        _clear(self.cv)
        ax, bx = self.cv.axes
        R = 1.6
        g = np.linspace(-R, R, 2)
        if r == 2:
            A, B = np.meshgrid(g, g)
            P = V[:, 0][:, None, None] * A + V[:, 1][:, None, None] * B
            ax.plot_surface(P[0], P[1], P[2], color=theme.ACCENT, alpha=0.15, linewidth=0)
        else:
            ax.plot(*np.vstack([-R * V[:, 0], R * V[:, 0]]).T, color=theme.ACCENT, lw=2)
        ax.plot(*np.vstack([-R * n, R * n]).T, color=theme.BAD, lw=2, label="joint null space (v₃)")
        ax.plot(*np.vstack([p - R * n, p + R * n]).T, color=theme.ORANGE, lw=2,
                label="all θ̇ with Jθ̇ = V_d")
        ax.plot([0, p[0]], [0, p[1]], [0, p[2]], color=theme.CYAN, lw=2.2)
        ax.scatter(*p, color=theme.CYAN, s=40, depthshade=False)
        ax.scatter(*y, color=theme.WARN, s=50, depthshade=False)
        for k, col in ((0, theme.GOOD), (1, theme.VIOLET)):
            ax.quiver(0, 0, 0, *V[:, k], color=col, lw=1.6, arrow_length_ratio=0.15)
            ax.text(*(1.1 * V[:, k]), f"v{k+1}", color=col, fontsize=8)
        for k, nm in enumerate(("θ̇₁", "θ̇₂", "θ̇₃")):
            e = np.zeros(3)
            e[k] = R
            ax.plot(*np.vstack([-e, e]).T, color="#55606f", lw=0.6)
            ax.text(*(1.05 * e), nm, color=theme.TEXT_DIM, fontsize=8)
        for nm in ("x", "y", "z"):
            getattr(ax, f"set_{nm}lim")(-R, R)
        ax.set_box_aspect((1, 1, 1), zoom=1.15)
        ax.view_init(elev=28, azim=-8)
        ax.set_title("joint-speed space: plane = working space", color=theme.TEXT, fontsize=9)
        self.cv.legend(ax, loc="upper left")
        pts = draw_arm(bx, L3, q)
        tip = pts[-1]
        k = 0.6
        for i, col in enumerate((theme.BAD, theme.VIOLET, theme.PINK)):
            bx.annotate("", xy=tip + k * J[:, i], xytext=tip,
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=1.4))
            bx.text(*(tip + k * 1.1 * J[:, i]), f"col {i+1}", color=col, fontsize=7)
        bx.annotate("", xy=tip + k * Jy, xytext=tip,
                    arrowprops=dict(arrowstyle="-|>", color=theme.WARN, lw=2.6))
        bx.plot(*(tip + k * Vd), "o", ms=10, mfc="none", mec=theme.CYAN, mew=1.5)
        bx.set_xlim(tip[0] - 2.0, tip[0] + 1.6)
        bx.set_ylim(tip[1] - 2.0, tip[1] + 1.6)
        bx.set_aspect("equal", adjustable="box")
        bx.set_title("tip: J·(yellow θ̇) (×0.6); circle = V_d")
        self.cv.fig.subplots_adjust(left=0.0, right=0.98, bottom=0.08, top=0.92, wspace=0.1)
        self.cv.refresh(layout=False)
