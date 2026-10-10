"""Worked, animated recap pages appended to each sidebar section.

Original lesson numbers are retained. Recaps are labeled Summary, so existing
references (and a reader's page number) do not change when a recap is inserted.
"""
from html import escape
from PySide6.QtCore import Qt
from .base import Page
from ..widgets import Card, body
from ..widgets.lesson_animation import LessonAnimation
from ..widgets.lesson_stories import STORIES, PAGE_ONE_EXTRAS, movie, S
from .. import theme


RECAP_MOVIES = {
    'inertia_time': movie('Double inertia: the same final speed takes longer', 'tank',
        S('Original inertia', 'The tank level represents speed as a percentage of its final value. J = 0.04, b = 0.4: τ_c = 0.10 s and 2% settling is 0.391 s. One 1 N·m step starts at 25 rad/s².', tau=.1,duration=.6,equation='Speed model: Jω̇ + bω = τ_motor; final speed = 2.5 rad/s'),
        S('Double J, keep b and torque fixed', 'J = 0.08 gives τ_c = 0.20 s and 2% settling is 0.782 s. Initial acceleration is now 12.5 rad/s². The final speed is still 2.5 rad/s; compare the same 0.6 s time window.',tau=.2,duration=.6,equation='Same final value; twice the time constant and settling time'),
        S('Double damping as well: a different comparison', 'With J = 0.08 and b = 0.8, J/b returns to 0.10 s. But for the same 1 N·m torque the final speed is now 1.25 rad/s. Holding b fixed was an essential part of the earlier conclusion.',tau=.1,duration=.6,equation='Changing another parameter changes which conclusions survive'), seconds=9),
    'inertia_position': movie('More inertia changes natural frequency AND damping ratio', 'mass',
        S('Original position model', 'J = 0.04, K = 100, B = 2 gives ω_n = 50 rad/s and ζ = 0.5. The moving block represents a normalized angular step response, shown in a slowed 0.5 s window.', mode='step',wn=50,zeta=.5,duration=.5,body_label='J',equation='Jθ̈ + Bθ̇ + Kθ = Kθ_d; normalized final angle = 1'),
        S('Double J at the same gains', 'J = 0.08 with K = 100 and B = 2 gives ω_n = 35.36 rad/s and ζ = 0.354. The slower, less damped response is not described by changing only a first-order time constant.',mode='step',wn=35.3553390593,zeta=.353553390593,duration=.5,body_label='2J',equation='Both ω_n = √(K/J) and ζ = B/(2√(JK)) change'),
        S('Retune to restore the ideal shape', 'For J = 0.08, choose K = 200 and B = 4. This restores ω_n = 50 and ζ = 0.5, but requires more commanded torque. Check saturation, sensing and delay before assuming hardware can deliver it.',mode='step',wn=50,zeta=.5,duration=.5,body_label='2J',equation='Same normalized response is possible only if the increased control effort is available'), seconds=9),
}


# Each checkpoint has a concrete statement/calculation, an animation and a
# prerequisite target. Movie IDs can also address the detailed opening/SEA set.
RECAPS = {
'Real-Time': [
    ('Count updates inside a motion cycle', 'At 1 kHz, T_s = 1 ms. A 20 Hz oscillation lasts 50 ms, so it contains 50 updates; a 100 Hz oscillation contains 10. Neither count says how closely the actuator follows.', 1, 'opening:cycles'),
    ('Recognise an ambiguous measurement', 'At f_s = 1000 Hz, cos(2π·950n/1000) equals cos(2π·50n/1000). A digital filter cannot distinguish those already-identical samples. Restrict unwanted content before sampling or before downsampling.', 1, 'opening:alias_data'),
    ('Budget delay and computation separately', 'A 2 ms delay costs 360·50·0.002 = 36° at 50 Hz. A 1 ms deadline also requires each control job to finish on time. Raising f_s can help timing, but does not directly change physical inertia or spring stiffness.', 1, 'opening:deadline'),
],
'Systems & Stability': [
    ('The inertia example, calculated', 'For J = 0.04 and b = 0.4, τ_c = J/b = 0.10 s; 2% settling takes about 0.391 s. Double J at fixed b and the settling time doubles. A 1 N·m torque step has initial acceleration 25 → 12.5 rad/s², while final speed remains 2.5 rad/s.', 6, 'recap:inertia_time'),
    ('A position model needs two response parameters', 'For J = 0.04, K = 100, B = 2: ω_n = 50 rad/s and ζ = 0.5. Double J at fixed K and B: ω_n = 35.36 and ζ = 0.354. The natural frequency and damping both change; bandwidth and settling time must be read from that response.', 11, 'recap:inertia_position'),
    ('Read the correct curve and the correct units', 'Plant P, loop gain L and closed-loop T answer different questions. Find |L| = 1 for gain crossover and read phase margin there. Find T’s −3 dB point for tracking bandwidth. Zeros can change overshoot even when the poles are unchanged.', 15, 'ZerosPage'),
],
'Controller Design': [
    ('Move closed-loop poles, then check limits', 'For Jθ̈ = τ with τ = −K_pθ − K_dθ̇, the characteristic equation is Js² + K_ds + K_p = 0. Positive K_p and K_d give a damped ideal rigid joint; saturation and delay require a separate check.', 16, 'StabilisingPage'),
    ('Pay for phase and low-frequency accuracy', 'Lead supplies phase near crossover but can increase high-frequency gain. Lag raises DC gain with a slower tail. A notch assumes a mode location; if the load changes, recheck the notch and the full loop.', 17, 'LeadLagPage'),
    ('State, cost and estimate are three objects', 'State feedback uses u = −Kx. LQR chooses K by minimising ∫(xᵀQx + uᵀRu)dt; xᵀPx is cost-to-go. An observer supplies x̂ when x is not measured. Good estimation cannot remove actuator limits.', 20, 'ObserverPage'),
],
'Capstone · Systems': [
    ('Balance starts with unstable modes', 'A linearised inverted pendulum has a growing mode. Its growth rate sets how quickly correction must act; the digital update rate and delay budget constrain that correction. Fast sampling alone does not make the mode stable.', 21, 'BipedSystemsPage'),
    ('Arm dynamics change with configuration', 'M(q) couples joint accelerations. Moving a payload changes both inertia and gravity, so the same gain can produce different poles at another pose. A fixed base does not imply every joint equilibrium is stable.', 22, 'ArmSystemsPage'),
    ('Connect a design to measured behavior', 'Identify the operating point, choose a controller, then verify torque limits, estimation and margins. Distinguish command tracking from disturbance rejection and from contact-force behavior; one successful test does not establish all three.', 20, 'ObserverPage'),
],
'Nonlinear': [
    ('Find the broken linear assumption', 'Saturation, friction and contact violate superposition. If doubling input does not double the deviation response, the linear approximation may be outside its useful region. A local stable linearisation does not prove global recovery.', 23, 'NonlinearSystemsPage'),
    ('Use a model without pretending it is exact', 'Computed torque uses τ = M(q)v + C(q,q̇)q̇ + g(q). With a matching model the remaining acceleration follows v; parameter errors become residual dynamics that feedback must handle.', 24, 'NonlinearControlPage'),
    ('Check stored energy and dissipation', 'A spring exchanges stored energy with motion; damping removes it. An active controller can add energy. A passivity or Lyapunov argument must include the relevant storage, dissipation and implementation assumptions.', 10, 'FreeVibrationPage'),
],
'Actuators': [
    ('Reflect inertia before using Jα', 'With J_m = 0.001 kg·m², N = 10 reflects 0.1 kg·m² to the output; N = 20 reflects 0.4. At a fixed net torque, acceleration decreases as total inertia increases. Gearing trades torque and speed as well as inertia.', 29, 'GearingPage'),
    ('SEA: name the port before the feature', 'Motor torque → motor angle has anti-resonance at √(k/J_L). Load torque → load angle has anti-resonance at √(k/J_m). The free relative mode is √(k/J_m+k/J_L). Prescribed motor motion changes the boundary condition; none is automatically a bandwidth.', 26, 'sea:ports'),
    ('Parallel stiffness does not erase mass', 'PEA adds k to rigid-joint stiffness. Its apparent J_eff(ω) = J_m+J_L−k/ω² can be negative, although both physical inertias are positive. The spring can share torque and return energy; it does not isolate rotor motion like an SEA.', 27, 'PEAPage'),
],
'Capstone · Actuators': [
    ('At the foot, separate support and impact', 'Standing requires sustained torque; heel strike involves momentum and energy over a short contact time. Select motor capacity and compliance against those separate demands, then verify balance bandwidth.', 30, 'BipedActuatorsPage'),
    ('At the wrist, mass is expensive upstream', 'For added point mass m at distance r, the inertia contribution is mr². Moving 1 kg from 0.2 m to 0.4 m changes that contribution from 0.04 to 0.16 kg·m². Proximal motor placement and rotor reflection must both be considered.', 31, 'ArmActuatorsPage'),
    ('Specify before comparing', 'Compare motor-to-load tracking, load-side response, torque sensing and thermal holding capacity separately. “SEA is slow” and “DD is fast” omit the load, controller and measured response that make a comparison meaningful.', 28, 'ActuatorCompare'),
],
'Control Paradigms': [
    ('One signed torque balance explains sag', 'At rest, θ_ss−θ_d = (τ_ff+τ_ext)/K. With K = 100, τ_ext = −10 and τ_ff = 0, the offset is −0.1 rad. With τ_ff = +10 it is zero. B shapes the transient but does not enter this static balance.', 36, 'ImpedanceControlPage'),
    ('Reverse the signal direction for admittance', 'Impedance computes torque from motion deviation. Admittance computes a motion reference from measured force. With K_v = 0, M_v = 2 kg and B_v = 10 N·s/m, a 5 N push gives final velocity 0.5 m/s and time constant 0.2 s.', 37, 'AdmittanceControlPage'),
    ('Name the inner loop and its failure modes', 'A torque command may leave position open loop while current remains closed loop. Integral windup comes from accumulating error when output cannot be delivered. D amplifies high-frequency noise; both I and D depend on elapsed time.', 34, 'PIDPracticePage'),
],
'Capstone · Control': [
    ('Schedule before contact, not after it', 'The biped can use higher stiffness for swing tracking and lower stiffness near touchdown, with damping and support feedforward chosen separately. Gait phase is progress through a step, not phase lag in a Bode plot.', 40, 'BipedControlPage'),
    ('Choose contact behavior on the arm', 'A stiff position target beyond a wall creates force. A compliant torque law sets a different force–motion relationship; a sensor-based admittance creates a motion reference. Both implementations still need delay, saturation and contact-stability checks.', 41, 'ArmControlPage'),
    ('Separate software clocks from response', 'A 1 kHz joint loop, slower planner and slower learning task are update schedules. Their rates do not specify joint bandwidth or collision response. Each layer must have a defined input, output and fallback behavior.', 1, 'opening:timing'),
],
'Robot Design': [
    ('Scaling includes the lever arm', 'Under geometric similarity and fixed density: mass ∝ L³ and inertia ∝ L⁵. At fixed allowable stress, force capacity ∝ L² and torque capacity includes another L. Gravity torque demand ∝ L⁴. State assumptions rather than calling area a torque.', 43, 'ScalingPage'),
    ('Topology is one design decision', 'Series elasticity adds relative motion and sensing opportunities; parallel elasticity shares spring torque; low-ratio gearing reduces reflection compared with large N. Select by required motion, sustained load and interaction response.', 42, 'ActuatorChoicePage'),
    ('Translate hardware descriptions into quantities', 'For tendon drives, ask for ratio, friction, elastic deflection and motor location. Current estimates motor torque; transmission and dynamics determine joint torque. Product names are not substitutes for those quantities.', 44, 'NeoPage'),
],
'Proprioception': [
    ('Observation is not the entire state', 'An encoder measures position; a model or additional sensor can estimate velocity and force-related quantities. Biological length, velocity and tendon-force sensing similarly report different aspects of motion.', 45, 'BioProprioPage'),
    ('Current is a motor-torque clue', 'τ_motor ≈ K_t i. To infer external joint torque, account for ratio, efficiency, rotor acceleration, friction and gravity. An output torque sensor changes the measurement path, not automatically the controller paradigm.', 46, 'RobotProprioPage'),
    ('Acting requires more than detecting', 'Detect a signal, interpret it, then modify impedance. Active compliance requires delay and motor authority; passive compliance responds mechanically. A fast sensor alone cannot produce fast corrective motion.', 47, 'ActiveCompliancePage'),
],
'Force Feedback': [
    ('Write the closed path', 'If activation produces force and measured or estimated force changes activation with a plus sign, positive force feedback is present. EMG or another command alone does not close that force path.', 48, 'PFFIntroPage'),
    ('Keep units and gains explicit', 'If feedback uses force, convert a torque estimate using the appropriate moment arm before multiplying by the force gain. A dimensionless loop-gain comparison comes after the physical conversions.', 49, 'PFFMathPage'),
    ('A gate is not a proof of stability', 'A gait-phase gate limits when positive feedback acts. Gain, duration, saturation, delay and mechanics determine amplification. The toy local growth example must not be treated as a universal model of biological reflex safety.', 12, 'StabilityPage'),
],
'Bio → Robot': [
    ('Separate command, sensation and mechanics', 'Activation is a command; muscle/tendon force is a mechanical signal; joint motion is an outcome. The analogous robot quantities are current/torque command, sensed or estimated torque, and encoder motion.', 50, 'BioActuationPage'),
    ('A spring stores; a damper dissipates', 'At a given deflection δ, elastic energy is ½kδ². A damping term proportional to velocity dissipates power b·velocity². A soft layer can spread contact but does not make every event safe.', 51, 'BioStructurePage'),
    ('Design the dynamics the policy will inherit', 'Geometry, inertia, compliance and sensing shape the plant. A later policy learns actions for that plant; it cannot repeal torque limits, insufficient sensing or an execution deadline.', 25, 'EffectiveInertiaPage'),
],
'Start Here': [
    ('Two different sources of randomness', 'π(a|s) describes the chosen action; P(s′|s,a) describes the resulting state. A deterministic command can still slip. The fully observed lake has observation = state; a robot often does not.', 54, 'TransitionsPage'),
    ('Turn rewards into return', 'For rewards −0.04, −0.04, +1 and γ = 0.9, return is −0.04 − 0.036 + 0.81 = 0.734. The first reward is not discounted. Expected return, not the next reward alone, is the optimisation objective.', 56, 'ReturnPage'),
    ('The rulebook is not the player', 'An MDP specifies states, actions, transitions, rewards and discount. A policy chooses actions within it. The state must preserve the information needed for the next outcome distribution; changing the policy does not redefine the dynamics.', 58, 'MDPPage'),
],
'Value Functions': [
    ('V averages Q under the policy', 'If π chooses two actions with probabilities 0.25 and 0.75, with Q values 0.2 and 0.8, then V = 0.25·0.2 + 0.75·0.8 = 0.65. Q fixes the first action and follows π afterward.', 61, 'VvsQPage'),
    ('Keep addition inside each branch', 'A branch with p = 0.5, r = −0.04, γ = 0.9 and successor value 0.8 contributes 0.5·(−0.04+0.72) = 0.34. Add branch contributions; do not multiply reward by value.', 63, 'BellmanExpVPage'),
    ('Max over actions, average over outcomes', 'V* optimises the current action; Q* fixes it and optimises the successor action. Neither lets the agent choose the ice outcome. A terminal successor contributes its arrival reward and zero continuation.', 66, 'BellmanOptQPage'),
],
'Dynamic Prog.': [
    ('Evaluation holds π fixed', 'Apply the expectation backup repeatedly to score a policy. In a synchronous sweep, every update reads the previous table. That is computation, not another action taken in the lake.', 67, 'PolicyEvalPage'),
    ('Improvement changes the action rule', 'Compare model-based one-step action scores from V^π. Exact greedy improvement is not worse under the standard finite discounted assumptions. Preserve or consistently resolve ties so identical values do not cause needless switching.', 68, 'PolicyImprovePage'),
    ('Choose the schedule deliberately', 'Policy iteration evaluates then improves. Value iteration applies optimality backups without a full evaluation phase. For γ < 1 the tabular Bellman operator contracts; use a residual tolerance, not a claim that a finite sweep is exact.', 71, 'CompareDPPage'),
],
'Monte Carlo': [
    ('The target is a completed sampled return', 'With returns 0.4, 0.8 and 0.3, the sample-mean estimate is 0.5. Monte Carlo needs no transition table and does not bootstrap from a successor value. First-visit and every-visit select different occurrences to average.', 73, 'MCPredictionPage'),
    ('Prediction and control remain different', 'Prediction estimates V^π for a fixed policy. Control updates action values and improves the policy. Exploration supplies experience that a purely greedy initial table might never collect.', 74, 'MCControlPage'),
    ('Check what the episode ending means', 'A true terminal state has zero continuation. A time limit imposed only for data collection can truncate a return that would have continued. Declare the modeled task and distinguish truncation from termination.', 72, 'MCIntroPage'),
],
'Beyond': [
    ('Know which knob changes the objective', 'γ weights future rewards; α scales learning updates; ε sets exploration; θ stops an iterative solve. A change in γ changes the task objective even if the board does not change.', 77, 'HyperPage'),
    ('Model use is independent of representation', 'A known or learned dynamics model can support planning. A neural Q function is a value model, not a transition model. Model-free does not mean every method must learn Q; policy gradients may use returns and a V baseline.', 76, 'ModelPage'),
    ('Plateau, optimum and stability differ', 'Adam updates weights using first and second raw gradient moments. A flat loss can signal a poor solution as well as convergence. Measure evaluated return and task constraints separately from optimisation statistics and physical stability.', 80, 'AdamPage'),
],
'Neural Networks': [
    ('Forward predicts, backward differentiates', 'A neuron computes z = xW+b and then φ(z). Backpropagation multiplies local derivatives along paths and adds contributions at merges. The optimiser changes weights only after those gradients are computed.', 84, 'BackpropPage'),
    ('Loss selects what the gradient means', 'For half-squared error ½(y−target)², the output derivative is y−target. A DDPG actor has no supervised target action: minimising −Q sends the negative action sensitivity backward through its output.', 85, 'LossPage'),
    ('Keep preprocessing and limits distinct', 'Input scaling changes feature units; normalisation uses statistics; regularisation penalises parameters; gradient clipping limits a derivative vector. A bounded actor output and actuator safety limits act on commands, not on that gradient.', 86, 'RegularisationPage'),
],
'Beam Balance': [
    ('Bandwidth is measured, not declared', 'The hip exoskeleton targets 5 Hz because the volitional balance response takes 200-250 ms; 5 Hz is a 32 ms time constant, so assistance is essentially delivered within 130 ms. The number was then confirmed by a 1-100 Hz sine sweep on the loaded device, not inferred from J and b.', 1, 'opening:timing'),
    ('The controller regulates momentum, not a pose', 'Setting lateral CoM position and velocity to zero solves for a desired torso angle and rate; the momentum error against that reference drives the torque. There is no correct torso angle to hold on a beam, which is why an admittance-to-velocity law is used rather than a position target.', 37, 'AdmittanceControlPage'),
    ('A 100:1 gearbox chooses the control mode', 'Rotor inertia is reflected to the hip by N squared, so a 1e-4 kg m^2 rotor contributes 1.0 kg m^2 at N = 100. The joint is not backdrivable and motor current is not a torque estimate, so interaction torque is measured with a load cell and motion is commanded: admittance, not impedance.', 29, 'GearingPage'),
],
'Fault Tolerance': [
    ('Latency, not accuracy, decided the outcome', 'Compensation worked at 43.1 +/- 11.5 ms of detection time; the perturbations still rated Medium or Large had an average detection delay of 103.5 ms. A false alarm cost 0.021 N m s/kg of impulse against 0.099 for a real fault, which is why the detector was tuned for sensitivity.', 1, 'opening:deadline'),
    ('Pick a robust input and a sensitive output', 'Axial load is relatively robust to control faults and knee angular velocity is highly sensitive to them, so load and its derivative predict nominal velocity and the residual detects the fault. Load alone is ambiguous because each level occurs twice per stance; the derivative separates loading from unloading.', 20, 'ObserverPage'),
    ('An additive layer that vanishes when nothing is wrong', 'tau_Final = tau_base + tau_FTM, with tau_FTM the difference between the same learned map evaluated at the nominal and the measured state, so model bias cancels. The baseline impedance controller stays engaged throughout, keeping its compliance and its passive stability properties.', 36, 'ImpedanceControlPage'),
],
'C-Space & Rigid Motion': [
    ('Count before you control', 'A planar 3R arm has dof = 3(4 − 1 − 3) + 3 = 3; a four-bar has 3(4 − 1 − 4) + 4 = 1; a Stewart platform 6(14 − 1 − 18) + 36 = 6. Its two-joint C-space is a torus, so angles wrap and a planner must know it.', 115, 'CSpacePage'),
    ('Rotations are matrices, not angle triples', 'A turn of 90° about ẑ gives R = [[0,−1,0],[1,0,0],[0,0,1]], RᵀR = I and det R = 1. log R returns (0, 0, π/2). Euler angles lose a freedom at pitch ±90°; R and quaternions do not.', 118, 'RotationsPage'),
    ('Angular velocity is a null space', 'RᵀR = I is 6 rules on 9 numbers; differentiating gives a 6×9 matrix A(R) whose null space is every Ṙ = [ω]R: 3 numbers. With R = Rot(ẑ, 90°) and ω_s = (1, 0, 0), ω_b = Rᵀω_s = (0, −1, 0). Euler-angle rates divide by cos(pitch); ω never blows up.', 119, 'AngularVelocityPage'),
    ('Store ω, not Ṙ or Euler rates', 'With R = Rot(ẑ, 90°) and ω_s = (1, 0, 0), Ṙ = [ω_s]R has 9 entries; hold it constant for 1 s and column 1 becomes (0, 1, 1), length 1.41. At pitch 89° a gyro reading of 0.1 rad/s needs yaw and roll rates of 5.7 rad/s. Integrate with R e^[ω_b]Δt instead.', 120, 'ExpCoordsPage'),
    ('Power does not care about frames', 'A revolute axis through q = (1, 0, 0) along ẑ has S = (0,0,1, 0,−1,0). Twists transform by Ad_T, wrenches by Ad_Tᵀ, so VᵀF is the same number in every frame — the seed of τ = JᵀF.', 121, 'TwistsPage'),
],
'Kinematics': [
    ('Velocity and force use the same matrix', 'For a 2R arm with L₁ = 1, L₂ = 0.8 at q = (30°, 60°), det J = L₁L₂ sin q₂ = 0.69. A 20 N downward hand force needs τ = JᵀF; straighten the elbow and det J → 0 while a radial force needs no torque at all.', 124, 'StaticsPage'),
    ('Two branches, then iterate', 'The 2R target (0.9, 0.8) with L = (1, 0.7) has an elbow-up and an elbow-down solution. Newton–Raphson from a nearby guess doubles the correct digits each step; from a bad guess it can land on the other branch.', 125, 'IKPage'),
    ('Use the null space on purpose', 'A planar 3R arm on a 2-D task has a 1-D null space. q̇ = J⁺ẋ + (I − J⁺J)q̇₀ keeps the hand error at numerical zero while the elbow follows q̇₀; adding q̇₀ without the projector drags the hand.', 126, 'NullSpacePage'),
],
'Dynamics': [
    ('Know the 2R equations by structure', 'M = [[a + 2b cos q₂, d + b cos q₂], [d + b cos q₂, d]] with b = m₂L₁r₂; c carries b sin q₂ times velocity products; g is the gradient of potential energy. Recursive Newton–Euler reproduces the same τ to machine precision.', 128, 'LagrangePage'),
    ('M is positive definite and Ṁ − 2C is skew', 'Kinetic energy ½q̇ᵀMq̇ > 0 makes M invertible at every posture. With Christoffel C, q̇ᵀ(Ṁ − 2C)q̇ = 0, so dE/dt = q̇ᵀτ: the arm returns only the energy it was given.', 129, 'MassMatrixPage'),
    ('Inverse for control, forward for simulation', 'RNEA gives τ from (q, q̇, q̈) in O(n). Forward dynamics builds M from n RNEA calls and solves M q̈ = τ − h. Explicit Euler pumps energy into a passive pendulum; semi-implicit Euler does not drift.', 132, 'ForwardDynamicsPage'),
],
'Trajectories & Planning': [
    ('Time scaling sets the torque', 'For a move of duration T, a cubic peaks at ṡ = 1.5/T and s̈ = 6/T²; the quintic at 1.875/T and 5.77/T². Halving T quadruples the inertial torque while gravity torque is unchanged.', 135, 'TimeScalingPage'),
    ('Let the limits choose the speed', 'Along a fixed path τ = m(s)s̈ + c(s)ṡ² + g(s). Torque limits bound s̈; the optimal profile accelerates on the upper bound, brakes on the lower bound and switches where they meet, under the velocity limit curve.', 136, 'TimeOptimalPage'),
    ('Plan in C-space, then time it', 'Two circular obstacles become irregular forbidden regions in (θ₁, θ₂) on a torus. A* on a 72 × 72 grid or an RRT returns a path; a time scaling then makes it a trajectory.', 137, 'MotionPlanningPage'),
],
'Robot Control': [
    ('Computed torque needs the model', 'τ = M̂(q̈_d + K_dė + K_pe) + ĥ gives ë + K_dė + K_pe = 0 when M̂ = M and ĥ = h. A 30% mass error leaves a disturbance; PD + gravity uses only ĝ and is globally stable for set-points.', 138, 'MotionControlPage'),
    ('Project posture torques dynamically', 'With J̄ = M⁻¹JᵀΛ, J M⁻¹(I − JᵀJ̄ᵀ) = 0: posture torques cause no hand acceleration. With the kinematic J⁺ the identity fails and the hand error grows while the posture task runs.', 139, 'OperationalSpacePage'),
    ('Force along the blocked direction', 'Against a wall, control force along the normal and motion along the tangent. Impedance instead renders K and B at the hand; the contact force becomes K times penetration, which stays stable on a stiff passive surface.', 140, 'ForceControlPage'),
],
'Manipulation & Mobility': [
    ('Antipodal within the cone', 'Two fingers on opposite sides of a disc are in force closure when the grasp line makes an angle with each normal below atan μ; with μ = 0.3 that is 16.7°. Frictionless contacts never resist the moment about the centre.', 141, 'GraspingPage'),
    ('Two inputs, three coordinates', 'A differential drive obeys −sin φ ẋ + cos φ ẏ = 0. It reaches every pose but no smooth static feedback stabilises one; a look-ahead point d ahead of the axle is fully actuated and can track a path.', 142, 'MobileRobotPage'),
    ('Answer one level lower', 'Spaces first, then kinematics and the Jacobian, then M q̈ + c + g = τ + JᵀF, then the control law. Every controller in the tutor is a statement about that equation.', 143, 'InterviewDrillPage'),
],
'Deep RL & Continuous Control': [
    ('Build the DDPG target carefully', 'y = r + γ(1−terminated)Q_target(s′, μ_target(s′)). The critic fits y. The actor follows the critic’s action derivative, while target networks move slowly. τ here is a mixing fraction, not a mechanical time constant.', 89, 'DDPGPage'),
    ('Do not merge independent algorithm choices', 'DDPG is deterministic/off-policy; SAC is stochastic/off-policy; PPO commonly uses stochastic/current-policy rollouts. Policy randomness does not decide whether replay is valid. A critic may be V or Q depending on the update rule.', 92, 'MDPandFamilyPage'),
    ('The knee closes the course’s timing loop', 'A knee action changes profile weights once per stride; the impedance controller can still run at 1 kHz and the trainer at another rate. Clamp and validate updates, retain a known-good policy, and never make the fast task wait for a training batch.', 95, 'DeployRLPage'),
],
}


def get_movie(key):
    if key.startswith('recap:'):
        return RECAP_MOVIES[key.split(':',1)[1]]
    if key.startswith('opening:'):
        return PAGE_ONE_EXTRAS[key.split(':',1)[1]]
    if key.startswith('sea:'):
        from ..widgets.sea_walkthroughs import SEA_MOVIES
        return SEA_MOVIES[key.split(':',1)[1]]
    return STORIES[key]


class SectionSummary(Page):
    IS_SUMMARY = True
    SUBTITLE = 'Worked checkpoints: recall the relationship, watch it happen, and check the assumptions.'

    def __init__(self,parent=None):
        super().__init__(parent)
        from . import LESSON_CLASSES
        lookup={c.NUM:c for c in LESSON_CLASSES}
        self.summary_movies=[]
        for heading,text,num,key in RECAPS[self.SECTION]:
            card=Card(heading)
            card.add(body(text))
            animation=LessonAnimation(get_movie(key))
            card.add(animation)
            self.summary_movies.append(animation)
            cls=lookup[num]
            link=body(f'<a style="color:{theme.CYAN}" href="{cls.__name__}">Revisit {num} · {escape(cls.TITLE)}</a>')
            link.setTextInteractionFlags(Qt.TextBrowserInteraction)
            link.setOpenExternalLinks(False)
            link.linkActivated.connect(self.navigate_requested.emit)
            card.add(link)
            self.add(card)
        self.finish()


def with_summaries(classes):
    result=[]
    for i,cls in enumerate(classes):
        result.append(cls)
        if i==len(classes)-1 or classes[i+1].SECTION != cls.SECTION:
            if cls.SECTION not in RECAPS:
                raise ValueError('Missing section recap: '+cls.SECTION)
            result.append(type(cls.__name__+'SectionSummary',(SectionSummary,),
                               {'TITLE':'Summary — '+cls.SECTION,'SECTION':cls.SECTION,'NUM':0}))
    return result
