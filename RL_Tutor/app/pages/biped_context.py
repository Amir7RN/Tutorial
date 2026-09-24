"""Read-in-order derivations and fixed comparison plots for pages 21 and 30."""
import numpy as np
from ctrlcore.biped_lesson import capture_delay_limit, motion_response
from .. import theme
from ..widgets import Card, MplCanvas, body, math_label


def poles_context():
    c = Card('1 · The same poles as before: what an eigenvalue tells you')
    c.add(body('Recall the first-order response: a pole at <b>s = −1/τ</b> gives an exponential '
        '<b>e<sup>−t/τ</sup></b> that decays. A pole at <b>s = +p</b> gives '
        '<b>e<sup>pt</sup></b> that grows. Right half-plane means Re(s) &gt; 0. '
        '<b>Yes: a right-half-plane eigenvalue of A is an unstable state-space pole.</b> '
        'A particular input-to-output transfer function can hide a mode if it is uncontrollable or unobservable; '
        'that does not remove the internal instability.'))
    c.add(body('From the state-feedback page, write the state vector as X and set the input to zero: '
        '<b>Ẋ = AX</b>. If Av = λv, then X(t) = v a₀e<sup>λt</sup> solves that equation. '
        '<b>v tells you the pattern of motion</b> (which angles and rates move together); '
        '<b>λ tells you how that pattern changes with time</b>. “Eigenvalue” is the matrix way of finding the poles, not a new kind of speed.'))
    c.add(math_label(r'a(t)=a_0e^{pt},\qquad t_{\rm double}=\frac{\ln 2}{p},\qquad t_{\rm limit}=\frac{\ln(a_{\rm limit}/a_0)}{p}', 16))
    c.add(body('For p = 8 s⁻¹, the growing-mode amplitude doubles every <b>86.6 ms</b>. '
        'Starting at 1°, it reaches 5° in <b>201 ms</b>. Starting closer to the limit leaves less time. '
        'This is the meaning intended by “deadline”: <b>time before a specified error limit is crossed</b>, '
        'not a fixed time at which the robot must fall, and not the software execution deadline from page 1. '
        'These curves isolate one mode; a released pendulum generally contains both growing and decaying modes.'))
    plot = MplCanvas(width=8, height=2.8, ncols=2)
    a,b=plot.axes; t=np.linspace(0,.35,250)
    a.plot(t,np.exp(-8*t),label='pole −8: decay',color=theme.GOOD)
    a.plot(t,np.exp(8*t),label='pole +8: growth',color=theme.BAD)
    a.axhline(5,color=theme.WARN,ls='--',label='chosen limit: 5°')
    a.set(xlabel='time (s)',ylabel='mode amplitude (°)',ylim=(0,10),title='Same exponential, opposite sign')
    plot.legend(a)
    for p,color in [(4,theme.CYAN),(8,theme.BAD)]:
        b.plot(t,np.exp(p*t),label=f'p = {p} s⁻¹',color=color)
    b.axvline(np.log(2)/8,color=theme.BAD,ls=':'); b.axhline(2,color=theme.TEXT_DIM,ls=':')
    b.set(xlabel='time (s)',ylabel='amplitude / initial amplitude',ylim=(0,8),title='Larger positive pole → less time')
    plot.legend(b);plot.refresh();c.add(plot)
    return c


def leg_derivation():
    c=Card('2 · From one upright joint to the six-state teaching model')
    c.add(body('<b>Start with one link, not a 6×6 matrix.</b> Let q be its small angle from upright, '
        'J its inertia about the pivot, d its viscous damping, m its lumped mass and ℓ the pivot-to-CoM distance. '
        'Gravity produces +mgℓ sin(q): it increases a small lean. Linearising means replacing sin(q) by q near zero. '
        'Define k_g = mgℓ &gt; 0, a destabilising gravity coefficient in N·m/rad.'))
    c.add(math_label(r'J\ddot q+d\dot q-k_gq=u,\qquad '
        r'\frac{d}{dt}\begin{bmatrix}q\\\dot q\end{bmatrix}='
        r'\begin{bmatrix}0&1\\k_g/J&-d/J\end{bmatrix}\begin{bmatrix}q\\\dot q\end{bmatrix}+'
        r'\begin{bmatrix}0\\1/J\end{bmatrix}u',16))
    c.add(body('The earlier mass–spring–damper equation had <b>+kq</b> on the left. '
        'Here it is <b>−k_g q</b>: gravity acts like negative stiffness. Try q = ce<sup>st</sup>, '
        'just as when finding the second-order poles:'))
    c.add(math_label(r'Js^2+ds-k_g=0,\quad s_\pm=\frac{-d\pm\sqrt{d^2+4Jk_g}}{2J};'
        r'\quad d=0\Rightarrow s_\pm=\pm p,\ p=\sqrt{k_g/J}',16))
    c.add(body('<b>The ± pair assumes zero damping.</b> With d &gt; 0, there is still one positive and one negative root, '
        'but they are not exact opposites. The live model below includes d = 0.8 N·m·s/rad. '
        'The symbols p₁, p₂, p₃ mean three different positive roots; they are not assumed equal.'))
    c.add(body('Now stack <b>X = [q_ankle, q_knee, q_hip, q̇_ankle, q̇_knee, q̇_hip]ᵀ</b>. '
        'The upper three equations say “angle derivative = angular rate”; the lower three are torque balances. '
        'This makes A a 6×6 matrix and B a 6×3 matrix. For this deliberately simplified example: '
        '<b>J = diag(3.2, 1.1, 0.45) kg·m²</b> and '
        '<b>K_g = mgz·diag(1, 0.45, 0.18)</b>. Those factors are assumed lumped gravity coefficients, '
        'not a multibody derivation of a particular manufactured leg.'))
    c.add(math_label(r'A=\begin{bmatrix}0&I\\J^{-1}K_g&-J^{-1}D\end{bmatrix},\qquad '
        r'B=\begin{bmatrix}0\\J^{-1}\end{bmatrix}',17))
    c.add(body('Because these matrices are diagonal in joint coordinates, this example has one growing mode per joint. '
        '<b>A real coupled leg generally has modes involving several joints</b>; contact, posture, damping and constraints change its poles. '
        'There is no universal rule that every biped has exactly three unstable poles or that the ankle is fastest. '
        'Here the nominal positive roots are approximately <b>8.18, 9.15 and 8.55 s⁻¹</b>: the knee mode is fastest. '
        'Increasing m with J artificially held fixed speeds growth; if J = mℓ² changes too, the undamped p = √(g/ℓ) is independent of mass.'))
    return c


def sampling_context():
    c=Card('3 · Growth rate, crossover and sample rate are three different quantities')
    c.add(body('<b>p [s⁻¹]</b> describes the uncontrolled growth. <b>ω_gc [rad/s]</b> is the frequency '
        'where the designed open-loop gain magnitude crosses 1. <b>f_s [samples/s]</b> is how often software updates. '
        'Crossover is related to closed-loop response bandwidth, but the two are not identical. '
        'Convert units before comparing: <b>f_gc = ω_gc/(2π)</b>.'))
    c.add(body('The Stabilising page’s 2p and 5–10p comparisons are <b>design heuristics, not necessary-and-sufficient stability tests</b>. '
        'Likewise f_gc ≲ f_s/15 is a sampling guideline, not a physical cap. '
        'For an illustrative p = 8 s⁻¹, choose ω_gc = 5p = 40 rad/s = 6.37 Hz. '
        'The guideline then suggests f_s ≳ 15×6.37 = <b>95.5 Hz</b>. '
        'It does <b>not</b> prove that balance inherently requires 1 kHz. Higher rates may be chosen for torque loops, '
        'contact changes, estimation and delay margins; planner and servo rates depend on the architecture.'))
    plot=MplCanvas(width=8,height=2.6,ncols=2);a,b=plot.axes
    a.bar(['growth p','example ω_gc'],[8,40],color=[theme.BAD,theme.ACCENT]);a.set(ylabel='inverse seconds / rad/s',title='Choose control speed relative to growth')
    rates=np.array([50,100,500,1000]);b.bar([str(v) for v in rates],rates/15,color=theme.CYAN)
    b.axhline(40/(2*np.pi),color=theme.WARN,ls='--',label='example crossover: 6.37 Hz')
    b.set(xlabel='sample rate f_s (Hz)',ylabel='guideline f_s/15 (Hz)',title='Sampling gives headroom, not bandwidth');plot.legend(b)
    plot.refresh();c.add(plot)
    c.add(body('For a shared sample rate, check the <b>most demanding controlled mode and loop</b>, not an average of the joints. '
        'Then verify actual closed-loop poles, delays, torque limits and contact constraints. '
        'In the lab below, f_s really changes the sample-and-hold simulation. The green poles describe ideal continuous LQR; '
        'the sampled stability stat checks eigenvalues of A_d − B_dK against the unit circle.'))
    return c


def lipm_context():
    c=Card('4 · A second model: centre of mass and the usable part of the foot')
    c.add(body('The six-state model asks how joint angles recover. For a different question—'
        '<b>can this foot stop the moving body?</b>—we introduce a reduced model, the linear inverted pendulum (LIPM). '
        'It assumes constant CoM height z, flat stationary support, adequate friction, maintained contact, '
        'and negligible change of angular momentum about the CoM. Vertical acceleration is zero, so F_z = mg. '
        'Moment balance gives F_x/F_z = (x − p_CoP)/z; dividing F_x by m gives the next equation. '
        '<b>This is a useful approximation, not the model every biped controller must use.</b> '
        'Jumping, changing height, hip/limb momentum and complex contacts require richer models.'))
    c.add(math_label(r'\ddot x=\omega_0^2(x-p_{\rm CoP}),\quad\omega_0=\sqrt{g/z},\quad '
        r's=\pm\omega_0',17))
    c.add(body('<b>x</b> is horizontal CoM position; <b>p_CoP</b> is a ground position in metres, '
        'not the pole p used above. <b>ω₀</b> is a growth-rate parameter, not the gait frequency or an actuator bandwidth. '
        'At z = 0.75 m, ω₀ = 3.62 s⁻¹ and the growing mode doubles in 192 ms. '
        'These poles belong to a different approximation from the joint model, so their values need not match. '
        'Under the stated assumptions, |p_CoP| ≤ half the foot length. With the ankle at the foot centre and negligible foot inertia, '
        '|τ_ankle| ≈ mg|p_CoP|; its sign depends on the torque convention. Motor limits can make the usable range smaller.'))
    c.add(math_label(r'\xi=x+\dot x/\omega_0,\quad \dot\xi=\omega_0(\xi-p_{\rm CoP});\qquad '
        r'p_{\rm CoP}=\xi(0)\Rightarrow x(t)=\xi(0)+(x(0)-\xi(0))e^{-\omega_0t}',15))
    c.add(body('Why this combination? Differentiate x + ẋ/ω₀ and substitute the acceleration equation: '
        'the result is the first-order growing equation above. Setting the CoP to ξ(0) cancels that growth; '
        'velocity decays and the CoM approaches that point. <b>ξ is the capture point</b>. '
        'If it is inside the foot, this ideal model admits a no-step stop. If outside, fixed-foot CoP control alone cannot stop it. '
        'A real robot may step, change height or use angular momentum. A delayed step must use the predicted future ξ, '
        'not blindly target its value at the instant of the shove.'))
    plot=MplCanvas(width=8,height=2.9,ncols=2);a,b=plot.axes
    w=np.sqrt(9.81/.75);t=np.linspace(0,.8,250);v=.3;xi=v/w
    a.plot([-.1,.1],[0,0],lw=6,color=theme.GOOD,label='20 cm foot')
    a.plot([xi,0],[0,.75],color=theme.TEXT_DIM);a.scatter([0,xi],[.75,0],color=[theme.ACCENT,theme.VIOLET],s=55)
    a.annotate('CoM (x, z)',(0,.75),xytext=(.02,.68),color=theme.TEXT);a.annotate('CoP', (xi,0),xytext=(.11,.12),color=theme.TEXT)
    a.set(xlim=(-.2,.25),ylim=(-.06,.85),xlabel='horizontal position (m)',ylabel='height (m)',title='Force acts from the CoP toward the CoM')
    b.plot(t,v/w*np.sinh(w*t)*100,label='CoP stays at 0',color=theme.BAD)
    b.plot(t,xi*(1-np.exp(-w*t))*100,label='CoP moved to ξ(0)',color=theme.GOOD)
    b.axhline(xi*100,color=theme.VIOLET,ls='--',label='ξ(0) = 8.3 cm')
    b.set(xlabel='time (s)',ylabel='CoM position (cm)',title='Same push: growing lean or a stop');plot.legend(b)
    plot.refresh();c.add(plot)
    return c


def learning_chain():
    c=Card('6 · Walk through one balance design using the earlier pages')
    for heading,text in [
        ('Start with poles (first and second order)', 'Find the equilibrium and linearise. A positive real pole means growing error; 1/p is an e-folding time. This diagnoses the uncontrolled problem.'),
        ('Choose the correction (PD, state feedback, LQR)', 'For one upright joint, u = −K_p q − K_d q̇ gives Jq̈ + (d+K_d)q̇ + (K_p−k_g)q = 0. Choose K_p > k_g and d+K_d > 0. Then ω_n = √((K_p−k_g)/J) and ζ = (d+K_d)/(2√(J(K_p−k_g))). These are the same natural frequency and damping ratio as before. State feedback extends the calculation to a matrix; LQR chooses gains from Q and R, not from a guaranteed torque bound.'),
        ('Check delivery (first-order actuators, Bode, phase margin)', 'The motor must deliver the requested torque quickly enough. A first-order torque response with time constant τ has bandwidth 1/(2πτ). At crossover, a pure delay T adds −ω_gc T radians of phase. Check margins on the actual loop; a lead network may recover phase but adds noise sensitivity. For an unstable plant, use the full Nyquist criterion or closed-loop poles rather than assuming a positive margin proves stability.'),
        ('Check the ground (capture point and saturation)', 'A stable unconstrained controller may ask for an impossible CoP or torque. Test the shove, foot geometry, motor limit and sample-and-hold response together. The simple CoP-to-CoM transfer −ω₀²/(s²−ω₀²) has unstable poles but no finite zeros: opposite initial acceleration alone does not prove a right-half-plane zero.'),
        ('Carry requirements to page 30', 'Specify the torque magnitude, tracking bandwidth and delay permitted for chosen pushes and loads. Then compare actuator designs against those requirements. “1 kHz software” by itself answers none of those mechanical questions.')]:
        c.add(body(f'<b>{heading}.</b> {text}'))
    c.add(body('References: <a style="color:#60a5fa" href="https://underactuated.mit.edu/pend.html">MIT: torque-limited pendulum</a>; '
        '<a style="color:#60a5fa" href="https://www.cs.cmu.edu/~cga/legs/Pratt_Goswami_Humanoids2006.pdf">Pratt et al.: capture point and model assumptions</a>.',dim=True))
    return c


def actuator_context():
    c=Card('From page 21 to actuator bandwidth: required speed versus achievable speed')
    c.add(body('<b>There is no single bandwidth of direct drive.</b> First name the input and output: '
        'current command → current, torque command → torque, or angle command → joint angle. '
        'Closed-loop bandwidth commonly means the −3 dB frequency of that tracking response. '
        'Direct drive means N = 1; it does not specify the controller, motor, load or bandwidth. '
        'The 10–30, 20–50 or 100 Hz examples elsewhere are operating examples, not definitions of actuator types.'))
    c.add(body('For the electrical loop, L di/dt + Ri = v − k_eω and τ_motor = k_t i. '
        'With speed fixed and no feedback, the electrical time constant is L/R. A current controller changes that response, '
        'subject to voltage, sampling and sensing limits. For motion, J_total = J_load + N²J_motor and '
        'J_total θ̈ = τ − external torque. <b>Yes, the load matters.</b> With ideal torque tracking and PD position control, '
        'derivative feedback on measured velocity, no gravity and negligible passive damping, the closed-loop transfer is:'))
    c.add(math_label(r'\frac{\theta}{\theta_d}=\frac{K_p}{J_{\rm total}s^2+K_ds+K_p},\qquad '
        r'\omega_n=\sqrt{K_p/J_{\rm total}},\quad\zeta=\frac{K_d}{2\sqrt{J_{\rm total}K_p}}',16))
    c.add(body('At fixed gains, more inertia lowers ω_n and changes damping, so the motion response changes. '
        'Holding the same ω_n and ζ requires proportionally larger K_p and K_d and more torque. '
        'Motor torque bandwidth need not fall by the same factor: the current loop may remain fast while the heavy load moves slowly. '
        'Speed-dependent back EMF, bus voltage, torque amplitude, heating, resonances, contact and delay limit the real result. '
        'Measure or model the frequency response under the intended load and amplitude.'))
    plot=MplCanvas(width=8,height=2.8,ncols=2);a,b=plot.axes
    f=np.logspace(-1,2,300)
    for j,color in [(1,theme.CYAN),(4,theme.WARN)]:
        h=motion_response(j,400,28,f);a.semilogx(f,20*np.log10(abs(h)),label=f'J = {j} kg·m²',color=color)
    a.axhline(-3,color=theme.TEXT_DIM,ls='--');a.set(xlabel='frequency (Hz)',ylabel='angle tracking gain (dB)',ylim=(-50,10),title='Same PD gains, different loads');plot.legend(a)
    w=np.sqrt(9.81/.75);t=np.linspace(0,.22,200)
    for xi,color in [(.05,theme.CYAN),(.08,theme.WARN)]:
        b.plot(t,xi*np.exp(w*t)*100,label=f'initial ξ = {xi*100:.0f} cm',color=color)
    b.axhline(10,color=theme.BAD,ls='--',label='toe at 10 cm');b.set(xlabel='uncorrected delay (s)',ylabel='capture point (cm)',title='More initial margin buys more time');plot.legend(b)
    plot.refresh();c.add(plot)
    delay=capture_delay_limit(.08,.1,w)
    c.add(body(f'<b>What “bandwidth set by capture point” should mean.</b> For the 20 cm foot, z = 0.75 m and ξ₀ = 8 cm, '
        f'holding CoP at zero gives ξ(t) = ξ₀e<sup>ω₀t</sup>; it reaches the toe in <b>{delay*1000:.1f} ms</b>. '
        'That is an example delay budget before this particular ideal no-step recovery becomes unavailable. '
        'It is not an equation that says “the ankle needs 12 Hz”. Other pushes have other budgets. '
        'For intuition only, a first-order torque loop settles to within 5% in about 3τ: '
        'at 10 Hz bandwidth that is 48 ms, at 30 Hz it is 16 ms. Sensing, computation, torque rise and whole-body motion '
        'all consume time, and CoP starts moving during the response. Verify the complete recovery; comparing settling time '
        'with 62 ms alone cannot certify balance.'))
    c.add(body('<b>SEA adds another set of dynamics.</b> The spring, motor-side inertia and load create resonances '
        'and anti-resonances (page 26). Their locations and your sensing/control arrangement affect torque tracking. '
        'A fraction of a resonance can be a conservative design target, not a universal bandwidth ceiling. '
        'The topology lab below uses illustrative screening numbers; it is not a measured motor specification or a capture-point calculation. '
        '<a style="color:#60a5fa" href="https://arxiv.org/abs/1902.05346">Lee et al.: torque amplitude, load and SEA bandwidth</a>.',dim=True))
    return c
