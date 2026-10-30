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
    c = Card("building M: move, push, feel — M = Σ J_kᵀ G_k J_k")
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
