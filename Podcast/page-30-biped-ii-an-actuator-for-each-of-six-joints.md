# Page 30 — Biped II: An Actuator For Each Of Six Joints

*Listening script. Roughly twenty minutes. Direct drive, QDD, SEA, harmonic drive — and why the right answer at the ankle is the wrong answer at the hip.*

---

## The same machine, a different question

Same robot as Biped One. **Trunkless, two legs, six actuators, thirty kilograms, centre of mass 0.75 metres up, feet 0.20 metres long.** Ankle about ninety newton-metres peak, knee about a hundred and twenty, hip about eighty.

Biped One asked whether the *controller* could stabilise it. **This page asks what to physically bolt into each of those six joints** — and the answer is different at each one, which is the entire reason the page exists.

Start by refusing to collapse the requirement into one number. **A leg joint has three operating conditions, and they want different machines.**

**Stance sets sustained torque and thermal requirements.** Holding torque can require high current at **zero speed** — copper loss is I squared R even though the mechanical power, torque times speed, is zero. Your motor is heating up while doing no work at all. Gearing reduces the motor torque needed, at the cost of speed, losses, and reflected inertia. A sufficiently sized direct drive remains an option.

**Swing sets speed and acceleration requirements.** You accelerate a moving leg against its **configuration-dependent** inertia, then stop it accurately. It is not an unloaded joint — the inertia it fights changes as the knee bends.

**Contact sets impact and compliance requirements.** An impact's early force transient **can be faster than any feedback you can close.** A one-kilohertz update rate does not give you a one-millisecond force correction. Mechanical compliance shapes that initial transient; feedback matters as contact continues. Those are two different jobs, separated in time by about a millisecond.

---

## "What is the bandwidth of direct drive?" is not a well-posed question

Before comparing topologies, one piece of hygiene, because it is the most common way this comparison goes wrong.

**There is no single bandwidth of direct drive.** First name the input and the output. Current command to current? Torque command to torque? Angle command to joint angle? These are three different transfer functions with three different answers. Closed-loop bandwidth usually means the minus-three-decibel frequency of whichever tracking response you named.

**Direct drive means N equals one.** That is all it means. It does not specify the controller, the motor, the load, or a bandwidth. When you see "ten to thirty hertz" or "a hundred hertz" quoted for an actuator type, those are **operating examples, not definitions.**

And the load is genuinely part of the answer. For motion, **J-total equals J-load plus N squared J-motor**, and with ideal torque tracking and PD position control the closed loop is the familiar second order: **omega-n equals root K-p over J-total, zeta equals K-d over two root J-total K-p.**

So **at fixed gains, more inertia lowers omega-n and changes damping.** To hold the same omega-n and zeta you need proportionally larger K-p and K-d — and more torque to deliver them.

But notice the asymmetry: **motor torque bandwidth need not fall by the same factor.** The current loop can stay fast while the heavy load moves slowly. Those are different loops, and conflating them is how people convince themselves a gearbox is free.

---

## The five options, and what each one actually changes

**Direct drive, N equals one.** No gearbox, so rotor inertia is not multiplied. Still to verify: continuous torque, cooling, motor mass, bearing friction, load inertia, tracking response.

**QDD, low reduction.** Trades some output speed for torque. **Reflected rotor inertia grows as N squared.** Verify gear efficiency, friction, backlash, impact rating, and the motor's torque-speed curve. **N alone does not prove backdrivability.**

**SEA.** Spring deflection can measure output torque, and mechanically shapes contact transients. Verify the motor-spring-load modes, torque amplitude, load condition, spring travel and damping. **Compliance does not guarantee high tracking bandwidth** — the opposite, as the SEA page showed.

**High reduction.** High output torque from a smaller motor, with much greater reflected inertia. Verify whether friction, compliance and sensing permit the contact behaviour you need. **Not automatically forbidden on all bipeds** — plenty of walking machines use it.

**Hydraulic.** Pressure and flow give force and speed; accumulators can add compliance. Verify whole-system mass, supply, valve dynamics, efficiency and maintenance — the honest accounting is the system, not the robot mass alone.

---

## The N-squared term, with the ankle's numbers

Now make it concrete. The lab uses a rotor inertia of **sixty micro-kilogram-metres squared** — a small, light rotor — and for the ankle a load inertia of 3.2, with a local foot-and-shank inertia of **0.15 kilogram metres squared** that participates in an impact.

**Direct drive, N equals one.** Reflected rotor inertia is sixty micro-units — negligible. Effective inertia at impact: **0.150.**

**QDD at N equals eight.** N squared is sixty-four, so reflected rotor is 0.0038. Effective inertia: **0.154.** Barely changed.

**Harmonic drive at N equals one hundred.** N squared is **ten thousand.** That same sixty-microunit rotor now reflects as **0.6 kilogram metres squared** — four times the entire local limb inertia. Effective inertia at impact: **0.750.**

**Read that progression again.** Identical motor. The rotor contributed nothing at N equals one, nothing at N equals eight, and then **dominated everything** at N equals one hundred. The square law does not creep up on you gradually; it is invisible and then it is the whole problem.

---

## The impact argument, which is the heart of the page

Now the calculation that decides the ankle.

A collision is a **momentum change**. The torque through the transmission is *what it must accelerate*, times *the change in rate*, divided by *how long the collision lasts*. Only the local foot-and-shank inertia is involved — the body's momentum goes up the leg as a strut, not through the ankle actuator.

So for a **rigid** drive:

**tau equals, open bracket, reflected inertia plus local inertia, close bracket, times delta-omega, divided by contact time.**

**And note the one over contact time.** Harder ground, bigger spike, **without limit**, and nothing in software gets a vote.

Watch it move. Take the ankle at QDD N equals eight, with a foot arriving at 0.35 metres per second on a ten-centimetre lever — so delta-omega is 3.5 radians per second.

**Contact time ten milliseconds: fifty-four newton-metres.** Soft ground, fine. **Contact time 1.5 milliseconds: 359 newton-metres.** **Contact time 0.2 milliseconds — hard floor — 2,692 newton-metres.** Against a structural threshold of four hundred.

Now the harmonic drive at the same 1.5 milliseconds: **1,750 newton-metres**, because you are driving that 0.6 of reflected rotor into the ground. **More than four times over structure, on an ordinary step.**

**Now the series elastic version, and this is the argument.** The spring cannot deliver more than it can wind up in the time available, and energy settles it: half J delta-omega squared equals half k delta squared, which gives

**tau equals delta-omega, times root of k J.**

**There is no contact time in that expression at all.**

That independence is the entire case for series elasticity. The rigid number went from 54 to 2,692 newton-metres purely because the floor got harder. **The SEA number does not move**, because the spring — not the floor — sets how fast the force can rise. For the ankle at fifteen hundred newton-metres per radian, the estimate is **fifty-two newton-metres**, against 359 for the rigid QDD at the same impact. **Roughly a seven-fold reduction, from a passive part, with no controller involved and no sample rate required.**

---

## The lab, joint by joint

The widget scores each combination against three assumed thresholds: a bandwidth target, a four-hundred-newton-metre structural limit, and backdrivability.

**The ankle.** QDD at N equals eight: effective inertia 0.154, assumed bandwidth two hundred hertz, impact **359** — passes, but sitting close to the wall. SEA: same inertia, bandwidth drops to **thirty-three hertz**, impact falls to **fifty-two**, and it senses torque for free — passes. Harmonic drive at a hundred: inertia **0.750**, impact **1,750**, and **not backdrivable** — **fails**, on two counts at once.

**The knee.** Local inertia 0.10, so everything scales down slightly. QDD impact **242**, SEA **43**, harmonic **1,633** and still failing.

**The hip.** Local inertia 0.06, the lightest of the three. QDD impact **149** — comfortable. SEA **33**. Harmonic **1,540**, failing again.

**Two patterns fall out of that table.**

First, **the harmonic drive fails at every joint**, and for the same reason each time: the N-squared term. It is not that high reduction is a bad idea in general — it is that **this robot's problem is impacts**, and high reduction makes impacts worse in exactly the term that matters.

Second, and more interesting: **the impact numbers get easier as you move up the leg** — 359 at the ankle, 242 at the knee, 149 at the hip — while the **speed requirement moves the other way.** The ankle is modest in speed and brutal in impact. The hip is the fastest joint and barely sees the ground.

**That crossing is why the answer differs per joint.** It is not a preference or a style. The ankle's hardest problem and the hip's hardest problem are different problems.

---

## Where a bandwidth requirement actually comes from

This is the part most worth being able to argue, because "the ankle needs twelve hertz" is the kind of sentence that gets repeated until nobody remembers where it came from. Here is the honest derivation, and its limits.

**Start with the electrical layer, because it is the fast one.** The motor winding obeys **L d-i-d-t, plus R i, equals v minus k-e omega**, and motor torque is **k-t times i**. With speed fixed and no feedback, the electrical time constant is simply **L over R** — typically tens of microseconds. A current controller changes that response, subject to voltage, sampling and sensing limits.

**That is why the current loop is not your problem.** It runs at ten to forty kilohertz and it is essentially free. Everything hard on this page happens mechanically, below it.

**Now the balance side.** From Biped One: with the twenty-centimetre foot, a centre of mass at 0.75 metres, and an initial capture point of eight centimetres, holding the centre of pressure at zero gives xi growing as e to the omega-nought t. It reaches the toe at ten centimetres in **sixty-two milliseconds.**

**That is a delay budget.** It is the time available before this particular ideal no-step recovery stops being available at all.

For intuition only, a first-order torque loop settles to within five percent in about three time constants. **At ten hertz of bandwidth that is forty-eight milliseconds. At thirty hertz it is sixteen.** So a ten-hertz ankle spends three quarters of that sixty-two millisecond budget just getting its torque up.

**But do not turn that into a specification, and here is why.** Sensing, computation, torque rise and whole-body motion all consume time out of the same budget. **And the centre of pressure starts moving during the response** — the sixty-two milliseconds is not a frozen deadline, it is a moving one. Other pushes have entirely different budgets. So **comparing a settling time against sixty-two milliseconds cannot certify balance.** What it does is tell you which order of magnitude you are arguing about, and that is genuinely useful — it is the difference between "we need tens of hertz" and "we need hundreds."

**The lab's twelve, twenty and twenty-five hertz targets are illustrative for exactly this reason.** They are consistent with that kind of reasoning; they are not computed from it.

And a series elastic actuator adds one more layer to check. **The spring, the motor-side inertia and the load create resonances and anti-resonances** — the SEA page's whole subject. Where they sit, and how you have arranged your sensing and control, both affect torque tracking. Taking a fraction of the resonance as a design target is a **conservative screening choice, not a universal ceiling** — which is precisely what the one-third figure in this lab is.

---

## What to actually build — stated as candidates

The page is careful here, and so should you be in an interview.

**Ankle: investigate SEA, or QDD with a compliant foot.** It is the joint that meets the ground, so impact dominates. But check sustained torque, the usable centre-of-pressure range, and torque tracking under the push-recovery scenarios from Biped One. And note the honest link back: **capture-point margin motivates a response-time requirement; it does not hand you a universal ankle bandwidth.** The lab's twelve, twenty and twenty-five hertz targets are **illustrative, not computed from the capture point.**

**Knee: investigate QDD near N equals eight.** Check the hundred-and-twenty-newton-metre peak and the swing speed **together**, including thermal duty and configuration-dependent inertia — the two requirements pull opposite ways and must be satisfied by one machine.

**Hip: investigate QDD near N equals six.** Check swing-leg acceleration, achievable step placement, and landing time. Actual gearing has to follow the motor's torque-speed curve, the losses, the load, and impact tests.

**These are starting candidates, not calculated optima.** Direct drive is not ruled out by robot mass alone. And **an SEA is not automatically fast enough, or compliant enough, for every contact.**

---

## What the numbers on this page are, and are not

Worth being explicit, because the widget is a screen and not a datasheet.

For rigid drives it **assumes** two hundred hertz at N of twelve or below, and sixty hertz otherwise. It does not derive those from a motor. For the SEA it uses **one third of the undamped two-inertia resonance** as a screening estimate — a conservative design target, not a universal ceiling. The four-hundred-newton-metre structural threshold and the gear-ratio backdrive classification are **also assumptions.**

The rigid collision estimate scales as one over contact time for a fixed momentum change; **real contact compliance prevents an infinite spike.** The SEA estimate assumes the kinetic energy transfers into a spring with **sufficient travel** — and real contact duration, damping and hard stops all matter.

So what survives all those caveats? **The trends.** Reflected inertia really does go as N squared. Rigid impact torque really is inversely proportional to contact time. Series elastic impact torque really is independent of it. Those three facts are structural, and they are what you are meant to leave with.

---

## Carry forward

**One.** **Separate the demands before choosing hardware.** Stance is thermal, swing is inertial, contact is impulsive. A single "bandwidth" number answers none of them.

**Two.** **N squared is the term that decides.** It multiplies rotor inertia into the impact, and it is why the same motor is invisible at N equals eight and dominant at N equals one hundred.

**Three.** **Rigid impact torque carries a one-over-contact-time. Series elastic impact torque does not.** That single structural difference is the whole argument for a spring in the drivetrain — and the SEA page's inequality is what it costs you in bandwidth.

**Four.** **The right answer is per joint.** The ankle meets the ground and wants compliance; the hip swings a leg and wants speed. Any design that gives all six joints the same actuator has decided that one of those two problems does not matter.

And the thread continues: Biped Three asks which *controller* goes on each of these joints, in which gait phase — because having chosen the hardware, you still have to decide what it is being told to do when the foot is on the ground versus in the air.
