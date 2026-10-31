"""
Chapter 8 lecture videos (Podcast/captions/chapter8), as cards for pages 133-135.

    8.1 part 1   forward vs inverse dynamics; Lagrange on the point-mass 2R
    8.1 part 2   centripetal and Coriolis terms, physically; Christoffel form
    8.1.3        understanding the mass matrix; the end-effector mass Lambda
    8.2 part 1   one rigid body from point masses; inertia matrix, principal axes
    8.2 part 2   spatial inertia G_b, the Lie bracket, F_b = G_b Vdot - ad^T G V
"""

from __future__ import annotations

from ..widgets import Card, body, math_label
from .robo_common import plain
from .robo_space_rigid import in_words, video_tag


def _table(head, rows):
    from .. import theme
    cell = f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}'"
    h = "".join(f"<th {cell} align='left'>{x}</th>" for x in head)
    r = "".join("<tr>" + "".join(f"<td {cell}>{x}</td>" for x in row) + "</tr>" for row in rows)
    return f"<table style='border-collapse:collapse'>{'<tr>' + h + '</tr>'}{r}</table>"


# ---------------------------------------------------------------- page 133
def fwd_inv_card() -> Card:
    c = Card("video 8.1, part 1 — forward and inverse dynamics, and two ways to get them")
    c.add(video_tag(
        "8.1", "lagrangian formulation of dynamics (part 1 of 2)",
        "Chapter 8 is the dynamics of open chains. Forward dynamics: θ̈ from (θ, θ̇, τ), for "
        "simulation. Inverse dynamics: τ from (θ, θ̇, θ̈), for control. Two routes: Lagrange "
        "(energy, derivatives) and Newton–Euler (f = ma per link, recursive)."))
    c.add(body(_table(
        ("", "inverse dynamics", "forward dynamics"),
        [("given", "θ, θ̇, θ̈", "θ, θ̇, τ"),
         ("find", "τ", "θ̈"),
         ("used for", "control (feedforward, computed torque)", "simulation; analysis of planners and controllers"),
         ("page", "136", "137")])))
    c.add(body(_table(
        ("", "Lagrangian", "Newton–Euler"),
        [("starts from", "kinetic and potential energy of the whole robot", "f = ma for each link"),
         ("tool", "derivatives of L = K − P", "twists, wrenches, adjoints (chapters 3–5)"),
         ("best for", "seeing the structure; small arms by hand", "an efficient recursive algorithm (page 135)")])))
    c.add(math_label(r"\mathcal{L}(\theta,\dot\theta)=\mathcal{K}(\theta,\dot\theta)-\mathcal{P}(\theta),\qquad "
                     r"\tau_i=\frac{d}{dt}\frac{\partial\mathcal{L}}{\partial\dot\theta_i}-\frac{\partial\mathcal{L}}{\partial\theta_i}", 16))
    c.add(plain(
        "τ and θ̇ are <b>dual</b>: τ·θ̇ is the power the joints consume or produce, the same "
        "pairing as twist and wrench. The equations are stated, not derived; any mechanics "
        "book has the derivation."))
    return c


def point_mass_2r_card() -> Card:
    c = Card("the video's 2R arm: all the mass in two points, worked through")
    c.add(in_words(
        "Links L₁ and L₂, gravity down, mass m₁ at the elbow and m₂ at the tip. Write each "
        "mass's position, differentiate to get its velocity, then K = ½mv² and P = mg·height. "
        "The step lab at the top of this page does every line with live numbers."))
    c.add(body(
        "<b>Positions</b>: x₁ = L₁c₁, y₁ = L₁s₁; x₂ = L₁c₁ + L₂c₁₂, y₂ = L₁s₁ + L₂s₁₂.<br>"
        "<b>Kinetic energy</b>: K₁ = ½m₁L₁²θ̇₁²; "
        "K₂ = ½m₂[(L₁² + 2L₁L₂c₂ + L₂²)θ̇₁² + 2(L₂² + L₁L₂c₂)θ̇₁θ̇₂ + L₂²θ̇₂²].<br>"
        "<b>Potential energy</b>: P₁ = m₁gL₁s₁, P₂ = m₂g(L₁s₁ + L₂s₁₂)."))
    c.add(body(
        "<b>One component, by hand.</b> Take L_comp = m₂L₁L₂θ̇₁θ̇₂ cos θ₂ (part of K₂). Then "
        "∂L_comp/∂θ̇₂ = m₂L₁L₂θ̇₁ cos θ₂; its time derivative is "
        "m₂L₁L₂(θ̈₁ cos θ₂ − θ̇₁θ̇₂ sin θ₂); subtract ∂L_comp/∂θ₂ = −m₂L₁L₂θ̇₁θ̇₂ sin θ₂. "
        "The last two terms cancel: τ₂,comp = m₂L₁L₂ θ̈₁ cos θ₂."))
    c.add(math_label(r"M=\left[\ m_1L_1^2+m_2(L_1^2+2L_1L_2c_2+L_2^2)\ \ ,\ \ m_2(L_1L_2c_2+L_2^2)\ ;"
                     r"\ \ m_2(L_1L_2c_2+L_2^2)\ \ ,\ \ m_2L_2^2\ \right]", 13))
    c.add(math_label(r"c=\left(-m_2L_1L_2s_2(2\dot\theta_1\dot\theta_2+\dot\theta_2^2),\ \ m_2L_1L_2s_2\dot\theta_1^2\right),\quad "
                     r"g=\left((m_1+m_2)L_1gc_1+m_2gL_2c_{12},\ \ m_2gL_2c_{12}\right)", 13))
    c.add(body(
        "<b>Three kinds of term.</b> Linear in θ̈ → M(θ)θ̈ (n × n mass matrix). Products of "
        "joint speeds (θ̇₁θ̇₂, θ̇₂²) → c(θ, θ̇), the velocity-product term. No speed or "
        "acceleration → g(θ), the gravity term. Springs at the joints would add to the "
        "potential energy and so to g. A wrench F_tip that the hand applies to the world adds "
        "<b>Jᵀ(θ)F_tip</b> (chapter 5):"))
    c.add(math_label(r"\tau=M(\theta)\ddot\theta+c(\theta,\dot\theta)+g(\theta)+J^T(\theta)\mathcal{F}_{tip}", 16))
    c.add(plain(
        "It looks like f = ma plus gravity, except that the accelerations of the masses also "
        "depend on products of joint speeds. That happens because joint angles are not "
        "inertial coordinates: a mass going round a circle at constant θ̇ still accelerates."))
    return c


def velocity_products_card() -> Card:
    c = Card("video 8.1, part 2 — what the velocity-product terms are, physically")
    c.add(video_tag(
        "8.1", "lagrangian formulation of dynamics (part 2 of 2)",
        "A term with one joint speed squared is centripetal; a product of two different joint "
        "speeds is Coriolis. Set gravity and θ̈ to zero and look at what mass 2 does at "
        "θ = (0, π/2)."))
    c.add(body(
        "Force on mass 1 = m₁ × its Cartesian acceleration, and that acceleration contains "
        "θ̇₁² even when θ̈₁ = 0. <b>Zero joint acceleration does not mean zero acceleration of "
        "the mass.</b> At θ₁ = 0, θ₂ = π/2:"))
    c.add(body(_table(
        ("joint speeds", "mass 2 moves on", "its acceleration", "torque needed"),
        [("θ̇₁ &gt; 0, θ̇₂ = 0", "a circle about joint 1", "centripetal ∝ θ̇₁², toward joint 1",
          "joint 1: none (the force line passes through joint 1); joint 2: positive"),
         ("θ̇₁ = 0, θ̇₂ &gt; 0", "a circle about joint 2", "centripetal ∝ θ̇₂², toward joint 2", "—"),
         ("both &gt; 0", "both circles at once", "plus a Coriolis part toward joint 2",
          "joint 1: <b>negative</b>, or joint 1 speeds up")])))
    c.add(plain(
        "The last row is the skater: pulling the arms in lowers the inertia and the spin "
        "speeds up. To hold both joint speeds constant, joint 1 must brake."))
    c.add(body(
        "<b>Compact forms</b>, all equal to c(θ, θ̇):"))
    c.add(math_label(r"c=\dot\theta^T\Gamma(\theta)\dot\theta,\quad "
                     r"\Gamma_{ijk}=\frac{1}{2}\left(\frac{\partial m_{ij}}{\partial\theta_k}+"
                     r"\frac{\partial m_{ik}}{\partial\theta_j}-\frac{\partial m_{jk}}{\partial\theta_i}\right),"
                     r"\quad c=C(\theta,\dot\theta)\dot\theta,\ C_{ij}=\sum_k\Gamma_{ijk}\dot\theta_k", 14))
    c.add(body(
        "Γ is an n × n × n array of <b>Christoffel symbols</b> of M: it depends on θ only, and "
        "it makes plain that c is <b>quadratic</b> in θ̇. Scalar picture: momentum p = m(x)ẋ, "
        "so f = dp/dt = mẍ + (dm/dx)ẋ². dm/dx plays the role of the Christoffel symbols. "
        "Everything without θ̈ is often lumped into h(θ, θ̇) = c + g, giving "
        "τ = M(θ)θ̈ + h(θ, θ̇) (+ JᵀF_tip)."))
    return c


def velocity_product_card() -> Card:
    c = Card("the velocity-product term c(θ, θ̇), plainly: pulls and levers")
    c.add(in_words(
        "If every joint spins at a steady speed with no acceleration, why do the motors still "
        "need torque? Because the masses move on curves, and anything on a curve needs a pull "
        "toward the centre even at constant speed. The motors supply that pull. That is c."))
    c.add(body(_table(
        ("step", "mass matrix (M θ̈)", "velocity product (c)"),
        [("1. move", "each mass accelerates because joints speed up: J θ̈",
          "each mass accelerates because it curves: every spinning link pulls it inward"),
         ("2. push", "force = mass × that acceleration", "force = mass × that curving acceleration"),
         ("3. feel", "each joint feels it through its moment arm (Jᵀ)", "the same: through the moment arm (Jᵀ)")])))
    c.add(body(
        "<b>Where the curving comes from.</b> Each link spins at its absolute rate, the sum of "
        "the joint speeds before it: link 2 spins at θ̇₁ + θ̇₂. Each spinning link pulls "
        "everything beyond it inward by (rate)² × length. Squaring a sum of speeds gives two "
        "kinds of term: θ̇ⱼ² terms are <b>centripetal</b> (one joint's speed, squared); "
        "θ̇ⱼθ̇ₖ terms are <b>Coriolis</b> (the cross pieces of the square)."))
    c.add(math_label(r"c_i=\dot\theta^T\,\Gamma_i\,\dot\theta,\qquad "
                     r"p_2=a_1+a_2,\quad \ddot p_2=-\dot\theta_1^2\,a_1-(\dot\theta_1+\dot\theta_2)^2\,a_2", 15))
    c.add(body(
        "<b>Γᵢ</b> collects, for joint i, the torque per speed product: entry (j, j) per θ̇ⱼ² "
        "(centripetal); entry (j, k) per θ̇ⱼθ̇ₖ (Coriolis, counted twice since (j, k) and "
        "(k, j) both appear). The Christoffel formula computes the same numbers from how M "
        "changes with pose; it is bookkeeping, and the 3R explorer below checks they match."))
    c.add(body(
        "<b>Constant speed is not constant angle.</b> If θ̇₂ = 0 the elbow holds, the arm is "
        "one rigid body, and m₂ rides a big circle about joint 1 with its pull aimed at joint "
        "1. If θ̇₂ ≠ 0 the elbow keeps folding, and m₂ traces a looping path around no fixed "
        "point: two epicycles, a₁ spinning at θ̇₁ and a₂ at θ̇₁ + θ̇₂, each with its own inward "
        "pull (moon around planet around sun). “Circling joint 2” is true only in link 1's "
        "rotating frame, and describing motion in a rotating frame costs the 2ω × v_rel term."))
    c.add(body(
        "<b>Coriolis, two ways.</b> (1) <b>Geometric</b>: v_rel is how fast the elbow alone "
        "carries m₂ (perpendicular to link 2). Turn it 90° the way link 1 spins and scale by "
        "2θ̇₁: that is the Coriolis pull, 2ω × v_rel, which lands back along link 2. "
        "(2) <b>Ice skater</b>: as the elbow opens, m₂'s reach from joint 1 changes, so M₁₁ "
        "changes while joint 1 spins. Holding θ̇₁ steady through a changing inertia costs"))
    c.add(math_label(r"\tau_{1,\mathrm{Coriolis}}=\dot\theta_1\,\frac{dM_{11}}{dt}", 16))
    c.add(plain(
        "Coriolis is not a new force: it is the price of spinning while your inertia changes "
        "shape. For the 2R arm, with h = m₂L₁L₂: θ̇₁'s own spin loads only joint 2 "
        "(+h sin θ₂ θ̇₁²), θ̇₂'s own spin loads only joint 1 (−h sin θ₂ θ̇₂²), and Coriolis "
        "loads only joint 1 (−2h sin θ₂ θ̇₁θ̇₂). At θ₂ = 0° or 180° all of it vanishes: every "
        "pull lines up with both joints, and the reach is momentarily not changing."))
    return c


# ---------------------------------------------------------------- page 134
def mass_matrix_video_card() -> Card:
    c = Card("video 8.1.3 — understanding the mass matrix")
    c.add(video_tag(
        "8.1.3", "understanding the mass matrix",
        "K = ½θ̇ᵀM(θ)θ̇, just like ½vᵀmv for a point mass. M is symmetric, positive definite "
        "and depends on θ. Its ellipses say which directions are heavy; at the hand it becomes "
        "the end-effector mass Λ(θ)."))
    c.add(body(
        "<b>Positive definite</b>: K &gt; 0 for every θ̇ ≠ 0, the matrix version of “mass is "
        "positive”. <b>Symmetric</b>. <b>Configuration dependent</b>: the inertia about each "
        "joint changes with how stretched the arm is."))
    c.add(body(
        "<b>Joint-space ellipses</b> (2R, link lengths and masses 1, at rest). A circle of "
        "joint accelerations maps through M to an ellipse of joint torques: some acceleration "
        "directions need more torque. Principal axes = eigenvectors of M, semi-axes = "
        "eigenvalues. M is invertible, so a circle of torques maps through M⁻¹ to an ellipse "
        "of accelerations. Both change with the configuration, but neither is easy to feel."))
    c.add(body(
        "<b>Grab the hand instead.</b> With endpoint velocity V = Jθ̇, equate the kinetic "
        "energies ½VᵀΛV = ½θ̇ᵀMθ̇ and substitute θ̇ = J⁻¹V:"))
    c.add(math_label(r"\Lambda(\theta)=J^{-T}(\theta)\,M(\theta)\,J^{-1}(\theta)", 16))
    c.add(body(
        "A circle of endpoint accelerations maps through Λ to an ellipse of endpoint forces. "
        "Two lessons: (1) the apparent mass depends on the direction of acceleration; (2) force "
        "and acceleration are parallel <b>only</b> along a principal axis. Push the hand "
        "purely along x and it accelerates with both x and y components. A robot hand does "
        "not feel like a point mass, and the feeling changes with the configuration."))
    c.add(plain(
        "Summary of the video: the equations of motion are f = ma, where the 'ma' depends on "
        "joint accelerations <b>and</b> velocities, plus forces to balance gravity, plus forces "
        "to create the wrench at the hand. Next, the same equations from f = ma for one rigid "
        "body: the Newton–Euler formulation (page 135). Page 138 builds the full task-space "
        "equation F = Λẍ + μ + p on Λ."))
    return c


def mass_matrix_build_card() -> Card:
    c = Card("building M: move, push, feel — M = Σ JₖᵀGₖJₖ")
    c.add(in_words(
        "M_ij is the inertia joint i feels when joint j accelerates. M₁₁: accelerate joint 1 "
        "at 1 rad/s² with joints 2 and 3 locked, so the whole arm swings about joint 1 as one "
        "rigid piece; how much torque does joint 1 need? Every link's mass gets pushed through "
        "its moment arm to joint 1, and joint 1 feels each push back through that same arm."))
    c.add(math_label(r"M(\theta)=\sum_{k=1}^{n}J_k^T(\theta)\,\mathcal{G}_k\,J_k(\theta),\qquad "
                     r"\mathcal{G}_k=\left[\ \mathcal{I}_k\ \ 0\ ;\ \ 0\ \ m_kI_3\ \right]", 16))
    c.add(body(
        "<b>J_k</b> is the body Jacobian (6 × n) of link k's centre-of-mass frame, as if that "
        "frame were the end effector. Joints after link k cannot move it, so their columns are "
        "<b>zero</b>. For a 3R arm: J₁ = [B₁ 0 0], J₂ = [Ad·B₁ B₂ 0], J₃ = [Ad·B₁ Ad·B₂ B₃], "
        "with the usual adjoints of the exponentials. Read JᵀGJ right to left, one link at a "
        "time:"))
    c.add(body(_table(
        ("step", "matrix", "meaning"),
        [("1. move", "J_k", "accelerate joint j alone at 1 rad/s²: link k accelerates by column j of J_k "
                            "(joint j's arm to the mass, turned 90°)"),
         ("2. push", "G_k J_k", "the force (and moment) the link needs: mass × that acceleration"),
         ("3. feel", "J_kᵀ G_k J_k", "each joint i feels that push through its own arm, the statics rule τ = JᵀF"),
         ("sum", "Σ_k", "each link's torques simply add, so one product per link gives all n² entries")])))
    c.add(body(
        "<b>G_k</b> is the 6 × 6 spatial inertia, block-diagonal in the twist order (ω, v): "
        "top-left 𝓘_k, the rotational inertia about the link's own centre of mass in its own "
        "frame; bottom-right m_k·I₃; off-diagonal blocks zero. Fully diagonal only when the frame "
        "is on the principal axes: G = diag(I_xx, I_yy, I_zz, m, m, m). Point mass: 𝓘 = 0, "
        "G = diag(0, 0, 0, m, m, m). Thin rod of length ℓ along x, frame at its centre: "
        "G = diag(0, mℓ²/12, mℓ²/12, m, m, m). That is why K = ½ωᵀ𝓘ω + ½m|v|²."))
    c.add(body(
        "<b>One entry.</b> For point masses, (i, j) = Σ_k m_k (arm_i · arm_j): column i dotted "
        "with m × column j. On the diagonal that is Σ (m_k r_k² + 𝓘_k), the "
        "<b>parallel-axis theorem</b> appearing on its own: each link counts as spin about its "
        "own centre plus mass × distance². Off the diagonal, the two arms' dot product says how "
        "much the two joints swing that mass the same way."))
    c.add(body(
        "<b>Check</b> (m₃ = 1 kg, joint 2 accelerating). Move: m₃'s column for joint 2 is "
        "ẑ × (1, 1) = (−1, 1). Push: 1 kg × (−1, 1) = (−1, 1) N. Feel: joint 1, arm (−1, 2): "
        "(−1, 2)·(−1, 1) = 3, m₃'s share of M₁₂. Joint 3, arm (0, 1): (0, 1)·(−1, 1) = 1, all "
        "of M₃₂."))
    c.add(plain(
        "<b>“Accelerate joint 2 alone”</b> means joints 1 and 3 are held at zero acceleration: "
        "locked, not loose. Joint 3 still works to keep link 3 from bending as it is swung, "
        "which is why M₃₂ = 1, not 0. Every joint reports the torque it needs to hold its own "
        "angle while joint 2 speeds up. <b>Why the compact form:</b> by hand you would sum the "
        "torque at joint 1 from every link separately; JᵀGJ gives the diagonal and coupling "
        "terms of all joints at once. <b>Notation</b>: τ = M(θ)θ̈ + c(θ, θ̇) + g(θ), where "
        "c = C(θ, θ̇)θ̇ is the velocity-product vector, not “c·θ̇”."))
    return c


def link_vs_task_inertia_card() -> Card:
    c = Card("Gₖ vs Λ: two inertias on opposite sides of M")
    c.add(in_words(
        "The JᵀGJ build of M and the lecturer's Λ = J⁻ᵀMJ⁻¹ are not the same formula "
        "inverted: they are two different matrices. G_k goes <b>into</b> M; Λ comes <b>out "
        "of</b> M. Kinetic energy is one number written in three sets of coordinates:"))
    c.add(math_label(r"\mathcal{K}=\frac{1}{2}\sum_k\mathcal{V}_k^T\mathcal{G}_k\mathcal{V}_k"
                     r"=\frac{1}{2}\dot\theta^TM\dot\theta=\frac{1}{2}\mathcal{V}_{hand}^T\Lambda\,\mathcal{V}_{hand}", 16))
    c.add(body(_table(
        ("", "G_k (link inertia)", "Λ(θ) (task-space inertia)"),
        [("describes", "one link's own mass and inertia about its centre of mass",
          "the whole arm's apparent inertia at the hand"),
         ("size", "6 × 6, one per link", "6 × 6 (or m × m), one for the arm"),
         ("depends on θ?", "no, constant in the link's frame", "yes, changes with pose"),
         ("role", "an input you build M from", "an output you derive from M")])))
    c.add(body(
        "Substitute V_k = J_kθ̇ and you get M = Σ J_kᵀG_kJ_k (links → joints). Substitute "
        "V_hand = Jθ̇ and you get M = JᵀΛJ (hand → joints). Same rule both times: "
        "<b>Jᵀ (inertia) J pulls an inertia back into the input coordinates</b>. Going the "
        "other way, from joints out to the hand, you invert, which is where J⁻ᵀ and J⁻¹ come "
        "from:"))
    c.add(math_label(r"\Lambda=J^{-T}MJ^{-1}\qquad\text{general form (redundant arms too):}\quad "
                     r"\Lambda=\left(JM^{-1}J^T\right)^{-1}", 16))
    c.add(body(
        "<b>Check</b> (2R, L = 1, 0.8; m = 1, 1.5; θ = 0.3, 1.1): M = [4.549 1.504; 1.504 "
        "0.960], Λ = J⁻ᵀMJ⁻¹ = [1.536 0.211; 0.211 2.723], JᵀΛJ = M ✓, and (JM⁻¹Jᵀ)⁻¹ gives "
        "the same Λ. <b>Meaning</b>: the mass the hand feels when you push it. At this pose a "
        "push along x meets 1.52 kg, along y 2.69 kg: same arm, different heft per direction. "
        "That is why Λ is the centrepiece of operational-space control (Khatib): command the "
        "hand as a free-floating object with direction-dependent mass (page 138)."))
    c.add(plain(
        "G_k is per <b>link</b>, about that link's centre of mass, not per joint. J⁻¹ exists "
        "only for a square, non-singular J; use (JM⁻¹Jᵀ)⁻¹ otherwise."))
    return c


# ---------------------------------------------------------------- page 135
def rigid_body_card() -> Card:
    c = Card("video 8.2, part 1 — the dynamics of one rigid body, from point masses")
    c.add(video_tag(
        "8.2", "dynamics of a single rigid body (part 1 of 2)",
        "Newton–Euler starts from f = ma for each body. A rigid body is a set of point masses "
        "rigidly attached; put frame {b} at the centre of mass and add up f = ma over the "
        "points."))
    c.add(body(
        "<b>Centre of mass</b>: Σ mᵢpᵢ = 0 in {b}. With body twist V_b = (ω_b, v_b), point i "
        "moves at ṗᵢ = v_b + ω_b × pᵢ. Differentiate once more (V̇_b is the body acceleration):"))
    c.add(math_label(r"\ddot p_i=\dot v_b+\dot\omega_b\times p_i+\omega_b\times v_b+\omega_b\times(\omega_b\times p_i)", 15))
    c.add(body(
        "The last two terms are velocity products again. Force on point i: fᵢ = mᵢp̈ᵢ, moment "
        "pᵢ × fᵢ. Sum over all points, using Σmᵢpᵢ = 0:"))
    c.add(math_label(r"f_b=m(\dot v_b+[\omega_b]v_b),\qquad m_b=\mathcal{I}_b\dot\omega_b+[\omega_b]\mathcal{I}_b\omega_b,\qquad "
                     r"\mathcal{I}_b=-\sum_i m_i[p_i]^2", 15))
    c.add(body(_table(
        ("entry", "formula", "meaning"),
        [("I_xx", "Σ mᵢ(yᵢ² + zᵢ²)", "moment of inertia about x: big if mass is far from the x-axis"),
         ("I_yy, I_zz", "Σ mᵢ(xᵢ² + zᵢ²), Σ mᵢ(xᵢ² + yᵢ²)", "same about y and z"),
         ("I_xy, I_xz, I_yz", "−Σ mᵢxᵢyᵢ, −Σ mᵢxᵢzᵢ, −Σ mᵢyᵢzᵢ", "products of inertia"),
         ("continuous body", "volume integrals with density ρ", "same idea; tables for common shapes")])))
    c.add(body(
        "Like M for a robot, I_b is symmetric and positive definite, and the rotational kinetic "
        "energy is ½ω_bᵀI_bω_b. <b>Principal axes</b>: eigenvectors of I_b; <b>principal "
        "moments</b>: its eigenvalues (page 127). R_bp has the eigenvectors as columns, and "
        "equal kinetic energies give I_p = R_bpᵀI_bR_bp, which is diagonal. In principal axes "
        "Euler's equation needs far fewer operations:"))
    c.add(math_label(r"m_b=\left(I_1\dot\omega_1+(I_3-I_2)\omega_2\omega_3,\ \ I_2\dot\omega_2+(I_1-I_3)\omega_1\omega_3,\ \ "
                     r"I_3\dot\omega_3+(I_2-I_1)\omega_1\omega_2\right)", 14))
    return c


def spatial_inertia_card() -> Card:
    c = Card("video 8.2, part 2 — spatial inertia, the Lie bracket, and one 6-D equation")
    c.add(video_tag(
        "8.2", "dynamics of a single rigid body (part 2 of 2)",
        "Pack rotation and translation together, so the rigid-body equation looks like the "
        "rotation-only one: inertia × acceleration minus a velocity-product term."))
    c.add(math_label(r"\mathcal{G}_b=\left[\ \mathcal{I}_b\ \ 0\ ;\ \ 0\ \ mI\ \right],\qquad "
                     r"\mathcal{K}=\frac{1}{2}\omega_b^T\mathcal{I}_b\omega_b+\frac{1}{2}m\,v_b^Tv_b=\frac{1}{2}\mathcal{V}_b^T\mathcal{G}_b\mathcal{V}_b", 15))
    c.add(body(
        "G_b is the 6 × 6 <b>spatial inertia</b>: symmetric and positive definite, like M and "
        "I_b. The 6-D cousin of the cross product is the <b>Lie bracket</b>: "
        "[V₁][V₂] − [V₂][V₁] in matrix form, or [ad_V₁]V₂ in vector form, with"))
    c.add(math_label(r"[\mathrm{ad}_\mathcal{V}]=\left[\ [\omega]\ \ 0\ ;\ \ [v]\ \ [\omega]\ \right]\in\mathbb{R}^{6\times6}", 15))
    c.add(body(
        "[ad_V₁]V₂ is an acceleration: how motion along V₂ would change if the body follows V₁. "
        "With it the rigid-body equation is one line:"))
    c.add(math_label(r"\mathcal{F}_b=\mathcal{G}_b\dot{\mathcal{V}}_b-[\mathrm{ad}_{\mathcal{V}_b}]^T\mathcal{G}_b\mathcal{V}_b", 17))
    c.add(body(_table(
        ("rotation only", "rigid body"),
        [("I_b", "G_b"), ("ω_b", "V_b"), ("ω_b × (·)", "[ad_Vb](·)"),
         ("m_b = I_bω̇_b − [ω_b]ᵀI_bω_b", "F_b = G_bV̇_b − [ad_Vb]ᵀG_bV_b")])))
    c.add(body(
        "<b>Another frame {a}</b>: equal kinetic energies give G_a = [Ad_T_ba]ᵀ G_b [Ad_T_ba], "
        "and the equation keeps the same form with F_a, G_a, V_a. A centre-of-mass frame is "
        "usually preferred. Inverse dynamics of one body: (V_b, V̇_b) → F_b. Forward: "
        "V̇_b = G_b⁻¹(F_b + [ad_Vb]ᵀG_bV_b). The next video chains these link by link: the "
        "recursive Newton–Euler algorithm below."))
    return c


# ---------------------------------------------------------------- page 135
def rnea_video_card() -> Card:
    c = Card("video 8.3 — Newton–Euler inverse dynamics for an open chain")
    c.add(video_tag(
        "8.3", "newton–euler inverse dynamics",
        "Chain the one-body equation F = GV̇ − ad_Vᵀ GV link by link. Forward iterations "
        "carry twists and accelerations out from the base; backward iterations carry wrenches "
        "back from the tip; each joint torque is the wrench projected on its own axis."))
    c.add(body(
        "<b>Frames.</b> {0} fixed in the world, {1} … {n} at the centres of mass of the links, "
        "{n+1} at the end-effector. V_i is the twist of link i written in {i}. "
        "<b>Given</b> θ, θ̇, θ̈ and the tip wrench F_tip; <b>find</b> τ."))
    c.add(body(_table(
        ("symbol", "meaning"),
        [("M_{i,i−1}", "pose of {i−1} in {i} when joint i is at zero"),
         ("A_i", "screw axis of joint i, written in {i}"),
         ("G_i", "6 × 6 spatial inertia of link i (page 134)"),
         ("F_{n+1} = F_tip", "wrench the end-effector applies to the environment"),
         ("V₀ = 0, V̇₀ = (0, −g)", "gravity as an upward base acceleration: indistinguishable from it")])))
    c.add(body("<b>Forward iterations</b>, i = 1 … n:"))
    c.add(math_label(r"T_{i,i-1}=e^{-[\mathcal{A}_i]\theta_i}M_{i,i-1},\quad "
                     r"\mathcal{V}_i=[\mathrm{Ad}_{T_{i,i-1}}]\mathcal{V}_{i-1}+\mathcal{A}_i\dot\theta_i,\quad "
                     r"\dot{\mathcal{V}}_i=[\mathrm{Ad}_{T_{i,i-1}}]\dot{\mathcal{V}}_{i-1}"
                     r"+[\mathrm{ad}_{\mathcal{V}_i}]\mathcal{A}_i\dot\theta_i+\mathcal{A}_i\ddot\theta_i", 14))
    c.add(body("<b>Backward iterations</b>, i = n … 1:"))
    c.add(math_label(r"\mathcal{F}_i=[\mathrm{Ad}_{T_{i+1,i}}]^T\mathcal{F}_{i+1}+\mathcal{G}_i\dot{\mathcal{V}}_i"
                     r"-[\mathrm{ad}_{\mathcal{V}_i}]^T\mathcal{G}_i\mathcal{V}_i,\qquad "
                     r"\tau_i=\mathcal{F}_i^T\mathcal{A}_i", 15))
    c.add(body(_table(
        ("term", "in words"),
        [("[Ad]V_{i−1}", "the parent's twist, moved into this link's frame"),
         ("A_iθ̇_i", "what joint i adds"),
         ("[ad_V_i]A_iθ̇_i", "velocity product: joint i spins inside a frame that already moves"),
         ("[Ad]ᵀF_{i+1}", "the wrench the child needs, moved back into this frame"),
         ("G_iV̇_i − ad ᵀG_iV_i", "this link's own rigid-body needs (video 8.2)"),
         ("F_iᵀA_i", "only the part along the joint axis is the motor's job; bearings carry the rest")])))
    c.add(plain(
        "Two passes: out from the base (each link's speed and acceleration builds on its "
        "parent's), back from the tip (each link's wrench builds on its child's). "
        "<b>No differentiation</b> anywhere, and the work grows linearly with the number of "
        "links, so it runs at 1 kHz in real controllers. For simulation you need the forward "
        "dynamics instead (page 137). The step lab below runs every line with live numbers on "
        "a 3R arm, one link per step, and checks the result against the planar formulas."))
    return c


# ---------------------------------------------------------------- page 137
def forward_dyn_video_card() -> Card:
    c = Card("video 8.5 — forward dynamics of open chains")
    c.add(video_tag(
        "8.5", "forward dynamics of open chains",
        "Solve for θ̈ given τ, θ, θ̇ (and F_tip), using nothing but the inverse dynamics "
        "algorithm: n + 1 calls give M and h, then solve M θ̈ = τ − h and integrate."))
    c.add(body(_table(
        ("call", "inputs to RNEA", "output"),
        [("0", "real θ, θ̇, g, F_tip; θ̈ = 0", "h = c(θ, θ̇) + g(θ) + JᵀF_tip"),
         ("i = 1 … n", "g = 0, F_tip = 0, θ̇ = 0, θ̈ = e_i (joint i at 1, the rest 0)", "column i of M(θ)"),
         ("then", "solve M θ̈ = τ − h with any efficient solver", "θ̈")])))
    c.add(math_label(r"\theta[k+1]=\theta[k]+\dot\theta[k]\,\Delta t,\qquad "
                     r"\dot\theta[k+1]=\dot\theta[k]+\ddot\theta[k]\,\Delta t", 15))
    c.add(body(
        "<b>Simulation</b>: at each timestep compute θ̈ by forward dynamics, then update θ and "
        "θ̇ by numerical integration. The video drops a 6R arm in gravity with τ = 0. It looks "
        "a little unreal because joint friction is not modelled; add your favourite friction "
        "model as a torque that depends on θ̇."))
    c.add(plain(
        "<b>Energy test.</b> With zero friction and zero torque nothing dissipates energy, so "
        "K + P must stay constant: the arm swings back to about the same height every time. "
        "Integration drift changes the total slowly; a smaller Δt or a better integrator (RK4) "
        "reduces it. The step lab below runs all n + 1 calls with their inner recursions, the "
        "solve, one step, and then a full simulation with the energy plotted live."))
    return c


# ---------------------------------------------------------------- page 138
def task_space_video_card() -> Card:
    c = Card("video 8.6 — dynamics in the task space")
    c.add(video_tag(
        "8.6", "dynamics in the task space",
        "The same dynamics written in end-effector motions and wrenches instead of joint "
        "motions and torques."))
    c.add(body(
        "With V = Jθ̇ (space or body frame) and J invertible: V̇ = Jθ̈ + J̇θ̇. Solve for θ̇ "
        "and θ̈, substitute into τ = Mθ̈ + h and τ = JᵀF:"))
    c.add(math_label(r"\mathcal{F}=\Lambda(\theta)\dot{\mathcal{V}}+\eta(\theta,\mathcal{V}),\qquad "
                     r"\Lambda=J^{-T}MJ^{-1},\quad \eta=J^{-T}h-\Lambda\dot JJ^{-1}\mathcal{V}", 15))
    c.add(plain(
        "Λ is the mass matrix seen at the end-effector (page 134); η collects velocity "
        "products and gravity as an end-effector wrench. Both are written in θ, not in the "
        "end-effector pose X, because one pose can have several robot configurations. A tip "
        "wrench F_tip simply adds to the total wrench."))
    return c


# ---------------------------------------------------------------- page 139
def constrained_video_card() -> Card:
    c = Card("video 8.7 — constrained dynamics")
    c.add(video_tag(
        "8.7", "constrained dynamics",
        "Loop closures, wheels, feet on the ground, a hand erasing a whiteboard: constraints "
        "need forces to enforce them. Add those forces with Lagrange multipliers, then project "
        "them away."))
    c.add(body(
        "Configuration constraints b(θ) = 0 hold at all times, so their derivative is zero "
        "too: (∂b/∂θ)θ̇ = A(θ)θ̇ = 0, with A k × n (k velocity constraints). These "
        "<b>Pfaffian</b> constraints can also be nonholonomic (chapter 2). Assume they are "
        "<b>workless</b> (for the eraser: no friction on the board). Then τ_con · θ̇ = 0 for "
        "every allowed θ̇, so τ_con is a combination of the rows of A:"))
    c.add(math_label(r"\tau=M\ddot\theta+h+A^T\lambda,\qquad A\ddot\theta+\dot A\dot\theta=0", 15))
    c.add(body(
        "n + k equations in n + k unknowns: the k multipliers λ and either θ̈ (forward) or "
        "τ (inverse). Eliminate λ with the n × n projection of rank n − k:"))
    c.add(math_label(r"P(\theta)=I-A^T\left(AM^{-1}A^T\right)^{-1}AM^{-1},\qquad "
                     r"P\tau=P\left(M\ddot\theta+h\right)", 15))
    c.add(plain(
        "P is not invertible, so you cannot cancel it. It projects joint torques onto the ones "
        "that move the robot and removes the ones that only push against the constraints. "
        "Inverse dynamics: plug θ, θ̇, θ̈ into the right side; then add <b>any</b> Aᵀλ, which "
        "pushes on the constraint without changing the motion. Chapter 11 uses exactly this "
        "freedom for hybrid motion–force control: motion along free directions, force along "
        "constrained ones."))
    return c


def qp_vs_newton_euler_card() -> Card:
    c = Card("Newton–Euler vs a QP: computing a torque vs choosing one")
    c.add(in_words(
        "Newton–Euler answers a question that has exactly one answer: this motion, which "
        "torques? A QP is for questions with many answers, or with answers that must stay "
        "inside limits: a wall that only pushes, a foot that must not slip, a motor that "
        "saturates. Then you pick the best allowed answer. The QP does not replace "
        "Newton–Euler; it is built from it."))
    c.add(body(_table(
        ("", "Newton–Euler (RNEA)", "QP (whole-body / contact control)"),
        [("kind of problem", "evaluate a function", "optimise: minimise a cost under constraints"),
         ("input", "θ, θ̇, θ̈ (and F_tip if known)", "θ, θ̇, a goal (task acceleration, momentum)"),
         ("unknowns", "τ (n)", "x = (θ̈, τ, λ): accelerations, torques, contact forces"),
         ("count", "n equations, n unknowns", "fewer equations than unknowns"),
         ("inequalities", "none", "λₙ ≥ 0, friction cone, τ limits, joint limits"),
         ("answers", "exactly one", "a whole set; the cost picks one, or none if infeasible"),
         ("cost per call", "O(n), two sweeps, no iterations", "iterative solver, ~0.1–1 ms per tick"),
         ("dynamics enter as", "the algorithm itself", "an equality constraint, with M and h as data")])))
    c.add(body(
        "<b>When the answer stops being unique.</b> Fixed base, no contact, every joint "
        "driven: θ̈ fixes τ, done. Add a contact and τ = Mθ̈ + h − Aᵀλ: any λ gives the same "
        "motion (video 8.7). Make the base float (legs, humanoid) and the six base rows have "
        "no motor: only λ can move the body, so θ̈ and λ must be chosen together. Add a wall "
        "that cannot pull or a foot that cannot slip and you have inequalities, which no "
        "recursion can handle. A typical whole-body controller solves, every 1–2 ms:"))
    c.add(math_label(
        r"\min_{\ddot q,\tau,\lambda}\ \|J\ddot q+\dot J\dot q-\ddot x_{des}\|_W^2+\epsilon\|\tau\|^2"
        r"\quad\text{s.t.}\quad M\ddot q+h=S^T\tau+J_c^T\lambda,\ \ "
        r"J_c\ddot q+\dot J_c\dot q=0,\ \ \lambda\in\mathcal{K}_\mu,\ \ \tau_{min}\le\tau\le\tau_{max}", 13))
    c.add(plain(
        "Quadratic cost, linear constraints (friction cone 𝒦_μ linearised to a pyramid): a "
        "convex QP, one global minimum, solved fast. The first constraint is the equation of "
        "motion; M and h come from Newton–Euler (n + 1 calls, page 137, or CRBA). So the "
        "chain is: RNEA builds the model, the QP chooses the motion and forces, and the τ "
        "it returns is what the motors get."))
    c.add(body(
        "<b>Worked example — the hand on the wall above.</b> 2R arm, hand at (1.1, 0.6) on "
        "the wall, at rest, asked to slide up at 2 m/s². Two joint equations, three unknowns "
        "(τ₁, τ₂, λ), so one degree of freedom is left to choose. The wall pushes with −λ."))
    c.add(body(_table(
        ("method / extra rule", "wall push −λ (N)", "τ (N·m)", "‖τ‖"),
        [("RNEA, λ = 0 (hand grazes the wall)", "0", "(29.33, 0.97)", "29.35"),
         ("QP: min ‖τ‖²", "18.63", "(18.15, −13.77)", "22.78"),
         ("QP + push ≥ 20 N (firm contact)", "20.00 (active)", "(17.33, −14.85)", "22.82"),
         ("QP + |τ₂| ≤ 10 N·m (weak motor 2)", "13.87", "(21.01, −10.00) (active)", "23.27"),
         ("QP + both rules", "—", "infeasible", "—")])))
    c.add(plain(
        "Same θ̈ in every row: the hand moves identically. RNEA gives one torque and has no "
        "idea the wall could help; the QP leans on the wall to cut torque by 22%, moves along "
        "the line τ = Mθ̈ + h − Aᵀλ until a limit becomes active, and with both rules it "
        "reports that no torque does the job. RNEA cannot say \"impossible\"; a QP can."))
    c.add(body(
        "<b>The link back to this page.</b> With no inequalities the QP collapses to "
        "linear algebra: fixed base and cost ‖θ̈ − θ̈_des‖² give θ̈ = θ̈_des and τ = RNEA. "
        "And constrained forward dynamics is itself a QP (Gauss's principle of least "
        "constraint): the true θ̈ is the one closest to the free motion M⁻¹(τ − h), measured "
        "with the mass matrix, that obeys the constraint:"))
    c.add(math_label(
        r"\ddot\theta=\arg\min\ \tfrac12(\ddot\theta-\ddot\theta_{free})^TM(\ddot\theta-\ddot\theta_{free})"
        r"\quad\text{s.t.}\quad A\ddot\theta=-\dot A\dot\theta", 14))
    c.add(plain(
        "Its optimality (KKT) conditions are exactly the block system [M −Aᵀ; A 0] on this "
        "page, and λ is the multiplier. Require λ to push only (λₙ ≥ 0, contact may open) "
        "and it turns into an inequality QP / complementarity problem: that is what physics "
        "engines (MuJoCo, Bullet, Drake) solve at every contact step."))
    return c
