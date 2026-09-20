"""A fixed-example movie for each SEA explanation panel, plus a port-by-port guide."""
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QLabel, QPushButton, QGridLayout, QScrollArea

from .common import Card, body, math_label, title
from .lesson_animation import LessonAnimation
from .lesson_stories import movie, S


def motion(heading, *scenes):
    return movie(heading, 'sea_motion', *(S(t,c,mode=m) for t,c,m in scenes), seconds=9)


SEA_MOVIES = {
'ports': motion('Choose the experiment before choosing the frequency',
    ('Motor torque → motor angle', 'Torque is applied to the motor; external load torque is zero. At ω_n = √(k/J_L), the motor angle cancels while the load moves. This is the motor driving-point anti-resonance.', 'motor_anti'),
    ('Load torque → load angle', 'Now the world applies torque to the load; motor torque is zero. At ω_a = √(k/J_m), load motion cancels while the motor moves. This is the load driving-point anti-resonance.', 'load_anti'),
    ('Free two-body mode', 'With both bodies free, they exchange spring energy at ω_r = √(k/J_m + k/J_L). Both move in opposite directions. This is a mode of the full plant, not either anti-resonance.', 'resonance')),
'units': movie('Three frequencies, expressed in the same units', 'sea_frequency',
    S('ω_n and f_n are one frequency', 'For J_m = 0.04, J_L = 0.06 and k = 300: ω_n = 70.71 rad/s and f_n = 11.25 Hz. Divide by 2π; do not compare 11.25 Hz directly with 86.60 rad/s.', active=0),
    S('ω_a and f_a are another frequency', 'ω_a = 86.60 rad/s = 13.78 Hz. It is the zero of load angle / load torque when the motor receives no applied torque. The subscript identifies a transfer-function role, not a universal hardware rating.', active=1),
    S('ω_r is above both in this free model', 'ω_r = 111.80 rad/s = 17.79 Hz. Its square is ω_n² + ω_a². None of these numbers specifies how often the controller updates.', active=2), seconds=9),
'motor_zero': motion('Why the motor encoder can go quiet while the load moves',
    ('Low-frequency motor torque', 'Below the elastic frequencies, motor and load mostly move together. The motor encoder is then a useful approximation to load motion, subject to the spring deflection.', 'motor_slow'),
    ('At the motor anti-resonance', 'At ω_n, spring reaction cancels the torque applied to the motor. Motor acceleration and periodic motor motion are zero, but the load oscillates. Quiet at one measured output does not mean nothing moves.', 'motor_anti'),
    ('Why control and identification care', 'The motor-angle transfer has a zero here; the motor-torque-to-load-angle transfer does not. Do not mistake the encoder dip for a stopped load, and do not use the same transfer function for both measurements.', 'motor_anti')),
'load_zero': motion('Why the pushed load can stop moving while the motor oscillates',
    ('A slow load-side push', 'With motor torque set to zero, the load drags the rotor through the spring. Both inertias contribute to the low-frequency response.', 'load_slow'),
    ('At the load anti-resonance', 'At ω_a, the motor oscillation makes spring torque cancel the applied load torque. The load angle is zero in the ideal harmonic solution; the motor is not locked.', 'load_anti'),
    ('Why apparent inertia becomes infinite', 'J_eff is applied load torque divided by load acceleration. Here the numerator is nonzero while load acceleration is zero: its magnitude diverges. This is an input/output zero, not infinite physical mass.', 'load_anti')),
'balance': movie('Read the two torque balances as two moving bodies', 'sea_motion',
    S('The spring carries equal-and-opposite torques', 'J_m θ̈_m = τ_m − k(θ_m−θ_L); J_L θ̈_L = τ_L + k(θ_m−θ_L). The difference of the angles creates spring torque.', mode='load_slow'),
    S('The measured side can cancel', 'Set τ_m = 0 and drive τ_L at ω_a. Opposite arrows show applied and spring torques on the stationary load. The motor’s motion supplies that spring torque.', scene='sea_balance', drive='load'),
    S('The other input gives a different cancellation', 'Drive τ_m with τ_L = 0 at ω_n. Applied and spring torques now cancel on the motor, while the load moves. Swapping input and measurement swaps the numerator.', scene='sea_balance', drive='motor'), seconds=9),
'limits': motion('Slow and fast are limits, not a sudden disconnect',
    ('Slow compared with both elastic scales', 'For this load-driven experiment J_eff tends to J_L + J_m. The spring still deflects enough to accelerate the motor.', 'load_slow'),
    ('Cross the elastic mode carefully', 'Near the full relative-mode resonance, internal motion can be large. The frequency response between the two limits is not a monotone safety improvement.', 'resonance'),
    ('Far above the elastic scales', 'The motor angle is small relative to load angle and J_eff tends to J_L. The spring is still connected and transmits torque; the rotor contribution becomes small in this limit.', 'load_fast')),
'slow': motion('A small spring deflection can still carry torque',
    ('Both angles move together', 'Under slow harmonic load excitation, θ_m is close to θ_L. Their difference is small relative to either angle.', 'load_slow'),
    ('Small does not mean zero', 'The small difference produces k(θ_m−θ_L), which accelerates the rotor. This is why the load still feels motor inertia at low frequency.', 'load_slow'),
    ('Keep the experiment fixed', 'Increasing drive frequency changes the relative motion. The low-frequency approximation must not be used at the load anti-resonance, where θ_L vanishes.', 'load_anti')),
'fast': motion('The high-frequency limit still has a spring',
    ('Observe the two angles', 'The world drives the load quickly. Motor motion is small, load motion is larger, and most of the relative angle appears across the spring.', 'load_fast'),
    ('Compare torque scales', 'At sufficiently high ω, inertial torque J_L ω²θ_L dominates spring torque kθ_L. This gives the asymptote J_eff ≈ J_L.', 'load_fast'),
    ('What this does and does not protect', 'Reduced reflected rotor participation can soften impacts. Peak force still depends on load inertia, contact compliance, energy, damping and travel limits.', 'load_fast')),
'deflection': motion('Follow the difference between the two angles',
    ('Below anti-resonance', '|θ_m−θ_L|/|θ_L| ≈ J_mω²/k at low frequency. The rotor is being moved, not held fixed.', 'load_slow'),
    ('At anti-resonance the ratio diverges', 'θ_L goes to zero while θ_m need not. Dividing by the small load angle makes the deflection ratio large; that does not mean the spring has infinite physical travel.', 'load_anti'),
    ('Far above anti-resonance', 'The ratio approaches 1 from above, rather than growing forever. The rotor scarcely moves and spring deflection approaches the negative of load motion.', 'load_fast')),
'imposed': motion('Imposed motor motion is a different boundary condition',
    ('A stiff servo prescribes θ_m', 'Now motor angle is the input, not motor torque. The servo supplies whatever torque the ideal experiment requires. Far below ω_n, θ_L/θ_m is near 1.', 'imposed_slow'),
    ('Approach ω_n from below', 'θ_L/θ_m = k/(k−J_Lω²) has a pole at ω_n in the undamped model. Near it the load motion is amplified. At the exact undamped resonance there is no bounded forced solution.', 'imposed_near'),
    ('Above ω_n', 'The load moves out of phase and its amplitude eventually falls as 1/ω². This is a transmissibility resonance, not the −3 dB tracking bandwidth of a designed closed loop.', 'imposed_fast')),
'sensor': movie('Measuring spring torque and changing spring torque are different', 'flow',
    S('Measure the deflection', 'Two angle measurements determine δ = θ_m−θ_L. With known linear k, spring torque is kδ; real calibration, resolution and damping matter.', active=0, equation='Measurement: δ → estimated spring torque'),
    S('Compute a correction', 'A controller can know the torque before it has changed it. Sampling rate, sensor bandwidth and loop delay describe different parts of this path.', active=1, equation='A 1 ms computation is not a 1 ms mechanical response'),
    S('Move to change the force', 'Motor torque must accelerate the rotor and change δ. The result depends on both inertias, spring dynamics and load boundary conditions.', active=2, equation='Changing torque requires changing the physical state'),
    nodes=('Measure δ', 'Compute command', 'Move rotor / change δ'), seconds=9),
'margin': movie('A resonance can consume a loop’s stability margin', 'flow',
    S('Name L and the measured output', 'Motor torque to load angle is the plant used by the position-loop demonstration. Multiply it by the chosen controller to form L.', active=0, equation='P = θ_L / τ_m; L = C P'),
    S('Check every relevant crossing', 'A lightly damped mode can boost magnitude while adding phase lag. Crossover is where |L| = 1; the resonance frequency is a different marker.', active=1, equation='Gain crossover ≠ resonance ≠ closed-loop bandwidth'),
    S('Verify the closed loop', 'A changed gain, derivative filter or damping term changes the full loop. Check stability and the response rather than treating ω_n as a universal ceiling.', active=2, equation='T = L / (1 + L); stable first, then measure tracking bandwidth'),
    nodes=('Plant + controller', 'Loop gain & margins', 'Closed-loop response'), seconds=9),
'damping': motion('Real damping rounds the ideal zero and peak',
    ('An exact zero is an ideal limit', 'With no damping, load motion is exactly zero at ω_a in the harmonic particular solution. Real transients need not have disappeared.', 'load_anti'),
    ('Add spring damping', 'A spring damper adds torque proportional to relative velocity. The exact imaginary-axis zero becomes a finite dip; the load now moves a little.', 'load_damped'),
    ('Damping also affects resonance', 'The free relative mode exchanges energy between the inertias. Physical damping removes that energy; derivative feedback is not automatically the same damping in a non-collocated loop.', 'resonance')),
'numbers': movie('What a 10 Hz response number actually says', 'tracking',
    S('A slow command', 'This illustrative first-order closed loop has a 10 Hz bandwidth. At 1 Hz it follows closely. It does not wait 100 ms between movements.', f=1, bands=(10,), labels=('10 Hz response example',)),
    S('At its bandwidth', 'At 10 Hz the amplitude is 70.7% of DC response and lag is 45° for this first-order example. Its time constant is 15.9 ms; its 2% settling time is about 62 ms.', f=10, bands=(10,), labels=('10 Hz response example',)),
    S('Keep the model qualification', 'An SEA can resonate and is not generally first order. These timing conversions apply to the displayed first-order response, not automatically to an elastic joint.', f=30, bands=(10,), labels=('10 Hz response example',)), seconds=9),
'energy': motion('A series spring stores energy and transmits torque',
    ('Load the spring', 'A relative angle δ stores E = ½kδ². The spring transmits torque kδ; measuring δ can estimate it.', 'load_slow'),
    ('Energy can return later', 'The free relative mode repeatedly trades elastic and kinetic energy. Without damping this energy persists; an ideal spring does not dissipate it.', 'resonance'),
    ('Do not confuse peak and static torque', 'Dynamic spring torque can differ from instantaneous motor torque because the rotor accelerates and stored energy can be released. Steady torque transmission, motor limits and output peak torque are separate questions.', 'motor_anti')),
'stiffness': movie('Change k while keeping both inertias fixed', 'sea_frequency',
    S('Original spring', 'With k = 300 all three frequencies come from the same two inertias. At a fixed torque, deflection is τ/k.', k=300,active=0),
    S('Four times the stiffness', 'k = 1200 doubles every undamped frequency scale. Static deflection at the same torque becomes one quarter; stored energy at that torque also becomes one quarter.', k=1200,active=1),
    S('One quarter of the stiffness', 'k = 75 halves every frequency scale and permits more deflection. Choose using torque, travel, sensing, impact and verified closed-loop requirements, not frequency alone.', k=75,active=2), seconds=9),
'selection': movie('Choose against a specific task, not a topology slogan', 'flow',
    S('State the task', 'Write down static load, peak motion, collision energy and required torque-estimation accuracy. “Safe” or “fast” alone is not a design requirement.', active=0, equation='Holding torque · acceleration · impact energy'),
    S('Choose and check the mechanics', 'Spring stiffness and travel must carry the load and tolerate stored energy. Motor and load inertias determine the relevant modal frequencies.', active=1, equation='τ_s = kδ; E_s = ½kδ²'),
    S('Close the intended loop', 'Specify the sensor/output and controller. Verify margins, saturation and tracking bandwidth for that loop; repeat when the payload changes.', active=2, equation='Hardware + boundary condition + controller → achieved response'),
    nodes=('Task requirements', 'Mechanics & sensors', 'Verified controller'), seconds=9),
}


def add_sea_guide(page):
    """Add the missing motor-driving-point experiment before existing derivations."""
    guide = Card('Start here: three experiments, not three names for bandwidth')
    guide.add(body('<b>Convention:</b> motor inertia and angle are referred to the spring/output side; no gearbox ratio is hidden. The first derivations neglect damping, ground friction and active feedback. The free model also has a rigid-body mode at zero frequency.'))
    guide.add(body('<table cellpadding="6"><tr><th>Apply / prescribe</th><th>Measure</th><th>What appears</th></tr>'
                   '<tr><td>Motor torque τ_m; τ_L = 0</td><td>Motor angle θ_m</td><td>Anti-resonance at ω_n = √(k/J_L)</td></tr>'
                   '<tr><td>Load torque τ_L; τ_m = 0</td><td>Load angle θ_L</td><td>Anti-resonance at ω_a = √(k/J_m)</td></tr>'
                   '<tr><td>Motor torque τ_m; τ_L = 0</td><td>Load angle θ_L</td><td>No finite undamped anti-resonance; pole at ω_r</td></tr>'
                   '<tr><td>Motor angle θ_m prescribed</td><td>Load angle θ_L</td><td>Resonance at ω_n, a different boundary condition</td></tr></table>'))
    guide.add(LessonAnimation(SEA_MOVIES['ports']))
    page.content.insertWidget(3,guide)
    motor = Card('Motor-side anti-resonance: motor torque in, motor angle out')
    motor.add(math_label(r'\frac{\theta_m}{\tau_m}=\frac{J_Ls^2+k}{s^2[J_mJ_Ls^2+k(J_m+J_L)]}',16))
    motor.add(body('The numerator vanishes at ω_n = √(k/J_L), while the load still moves. The motor encoder’s dip is therefore <b>not</b> evidence that the whole actuator stopped. The cross response θ_L/τ_m has numerator k and no finite zero in this undamped model. This is the zero-versus-pole distinction from the earlier lesson, now tied to a sensor location.'))
    motor.add(LessonAnimation(SEA_MOVIES['motor_zero']))
    page.content.insertWidget(4,motor)
    units=Card('Keep f_n, ω_n, ω_a and ω_r in one unit system')
    units.add(body('Use ω for rad/s and f = ω/(2π) for Hz. This page keeps the legacy name f_n for the imposed-motor-motion resonance; equivalently ω_n is the motor driving-point anti-resonance. ω_a means the load driving-point anti-resonance. ω_r is the free two-inertia relative-mode frequency. With damping the modal frequency and exact response-peak frequency can differ.'))
    units.add(LessonAnimation(SEA_MOVIES['units']))
    page.content.insertWidget(5,units)
    return guide,motor,units


def attach_sea_walkthroughs(page):
    """Each pre-existing Card and callout gets a topic-matched movie; labs remain."""
    from .lesson_connection import LessonConnection
    cards = list(page.findChildren(Card))
    from PySide6.QtWidgets import QFrame
    callouts = [w for w in page.findChildren(QFrame) if w.objectName().startswith('Callout')]
    matches = [
        ('derivation','balance'), ('the two limits','limits'), ('slow push','slow'),
        ('high-speed impact','fast'), ('watch the transition','stiffness'),
        ('below the antiresonance','deflection'), ('after the antiresonance','fast'),
        ('transmissibility','imposed'), ('ceiling and not','margin'),
        ('ceiling actually','damping'), ('close a pd','margin'), ('50–100','numbers'),
        ('protective','energy'), ('higher stiffness','stiffness'), ('where seas','selection'),
        ('pros and cons','selection'),
    ]
    page.sea_panel_movies=[]
    for card in cards:
        if isinstance(card,(LessonAnimation,LessonConnection)):
            continue
        heading=next((w.text().lower() for w in card.findChildren(QLabel) if w.objectName()=='CardTitle'),'')
        key=next((key for needle,key in matches if needle in heading),None)
        if key is None:
            raise ValueError('Unreviewed SEA panel: '+heading)
        animation=LessonAnimation(SEA_MOVIES[key])
        card.add(animation)
        page.sea_panel_movies.append((card,animation))
    for panel in callouts:
        text=' '.join(w.text() for w in panel.findChildren(QLabel))
        if 'three different frequencies' in text or 'three experiments' in text:
            key='ports'
        elif 'sensor' in text.lower() or 'feel the world' in text:
            key='sensor'
        elif 'ceiling' in text.lower() or 'bound' in text.lower() or 'coincidence' in text.lower() or 'last column' in text.lower():
            key='margin'
        else:
            key='limits'
        animation=LessonAnimation(SEA_MOVIES[key])
        panel.layout().addWidget(animation)
        page.sea_panel_movies.append((panel,animation))
    guide,motor,units=add_sea_guide(page)
    nav=Card('Read in this order, or jump to a question')
    grid=QGridLayout()
    targets=[('1 · Which input and output?',guide),('2 · Motor anti-resonance',motor),('3 · Decode the symbols',units)]
    targets += [(a.story.title,p) for p,a in page.sea_panel_movies if isinstance(p,Card) and not any(p.isAncestorOf(q) for q,_ in page.sea_panel_movies if q is not p)]
    scroll=page.findChild(QScrollArea)
    for i,(label,target) in enumerate(targets):
        button=QPushButton(label)
        button.clicked.connect(lambda checked=False,t=target: scroll.verticalScrollBar().setValue(t.mapTo(scroll.widget(),QPoint(0,0)).y()-12))
        grid.addWidget(button,i//2,i%2)
    nav.add_layout(grid)
    page.content.insertWidget(2,nav)
