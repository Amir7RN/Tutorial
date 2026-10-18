# Page 21 — Biped I: Poles, Growth Time and the Foot

*Listening script. Roughly twenty minutes. The first capstone: everything from the linear-systems and controller-design blocks, spent on one specific machine — and the two constraints that do not negotiate.*

---

## The machine

Fixed for the whole tutor, so the answers can be compared. **A trunkless biped. Two legs, no trunk, six actuators** — ankle, knee and hip on each side, all in the sagittal plane for these pages. **Thirty kilograms. Centre of mass 0.75 metres up when standing. Feet 0.20 metres long.** No arms — though leg motion can still change angular momentum, and the simple balance example deliberately omits that strategy.

The three joints, with what each one carries. **The ankle** carries the entire body above it, peak torque about ninety newton-metres, modest speed. **The knee** carries a configuration-dependent leg load, about a hundred and twenty newton-metres, high speed in swing. **The hip** carries the leg it is swinging, about eighty newton-metres, and it is the fastest of the three.

Nothing on this page is new theory. It is the theory you already have, pointed at one machine, with an interactive that lets the decision be wrong so you can see what wrong looks like.

---

## What an eigenvalue actually tells you

Start from something already familiar. A pole at **s equals minus one over tau** gives an exponential **e to the minus t over tau** — it decays. A pole at **s equals plus p** gives **e to the p t** — it grows. Right half plane means the real part is positive.

And yes: **a right-half-plane eigenvalue of A is an unstable state-space pole.** A particular input-to-output transfer function can *hide* a mode if that mode happens to be uncontrollable or unobservable — but hiding it does not remove the internal instability. The robot still falls over; you just cannot see it in that one transfer function.

From the state-feedback page: write the state vector as X, set the input to zero, and you have **X dot equals A X**. If A v equals lambda v, then X of t equals v, times a-nought, times e to the lambda t, solves that equation exactly.

So the two halves of an eigenpair do two different jobs. **The eigenvector v tells you the pattern of motion** — which angles and rates move together. **The eigenvalue lambda tells you how that pattern changes with time.** "Eigenvalue" is the matrix way of finding the poles. It is not a new kind of speed.

Now the number that matters for a falling robot. For amplitude growing as a-nought e to the p t, the **doubling time is log two over p**, and the time to reach some stated limit is **log of the ratio, over p**.

Put numbers on it. **For p of eight per second, the growing mode doubles every 86.6 milliseconds.** Starting at one degree, it reaches five degrees in **201 milliseconds**. Starting closer to the limit leaves you less time.

Be careful with the word "deadline" here, because the tutor is careful with it. **This means the time before a specified error limit is crossed.** It is not a fixed instant at which the robot must fall, and it is emphatically not the software execution deadline from the real-time page. Two different deadlines, same word.

One more honesty note: these curves isolate a single mode. **A released pendulum generally contains both growing and decaying modes at once**, and what you see is their sum.

---

## From one upright joint to six states

Do not start with a six-by-six matrix. Start with one link.

Let q be its small angle from upright, J its inertia about the pivot, d its viscous damping, m its lumped mass, and l the pivot-to-centre-of-mass distance. Gravity produces **plus m g l sine q** — note the sign: it *increases* a small lean. Linearise by replacing sine q with q near zero, and define **k-g equals m g l**, a positive, **destabilising** gravity coefficient in newton-metres per radian.

The equation of motion is **J q double dot, plus d q dot, minus k-g q, equals u.**

**Compare that with the mass-spring-damper from earlier.** That one had **plus k q** on the left. This one has **minus k-g q.** **Gravity acts like negative stiffness.** That single sign flip is the entire difference between a system that returns to rest and one that runs away from it.

Try q equals c e to the s t, exactly as when finding the second-order poles, and you get **J s squared, plus d s, minus k-g, equals zero**, with roots **minus d, plus or minus root of d squared plus four J k-g, all over two J.**

With **zero damping** those roots are a clean plus-or-minus p, with **p equal to root k-g over J** — one growing, one decaying, exact mirror images. With **d greater than zero** there is still one positive and one negative root, but **they are no longer exact opposites.** The live model uses d of 0.8 newton-metre-seconds per radian, so this matters.

Now stack six states: **the three joint angles, then the three joint rates.** The upper three equations say "angle derivative equals angular rate." The lower three are torque balances. That makes A a six-by-six and B a six-by-three, with the familiar block structure — zero and identity on top, J-inverse K-g and minus J-inverse D underneath.

For this deliberately simplified example, **J is diagonal — 3.2, 1.1 and 0.45 kilogram metres squared** — and the gravity matrix is m g z times diagonal one, 0.45, 0.18. Those factors are **assumed lumped coefficients**, not a multibody derivation of a manufactured leg.

And because those matrices are diagonal in joint coordinates, this example has **exactly one growing mode per joint.** Which brings the caveat the page insists on: **a real coupled leg generally has modes involving several joints at once.** Contact, posture, damping and constraints all move its poles. **There is no universal rule that every biped has exactly three unstable poles, or that the ankle is the fastest one.**

In fact, in this model it is not. The three positive roots come out at **8.18, 9.15 and 8.55 per second** — and **the knee is fastest**, at 9.15, which is a doubling time of **75.8 milliseconds**.

---

## Three quantities that are not the same quantity

This is the confusion the page exists to kill, and it is worth stating slowly because all three get quoted in hertz-adjacent units.

**p, in inverse seconds**, describes the **uncontrolled growth** of the plant. It is a property of the robot falling over, with no controller present.

**Omega-g-c, in radians per second**, is the frequency where your designed open-loop gain magnitude crosses one. It is a property of **the loop you built**. Crossover is *related* to closed-loop bandwidth, but the two are not identical — and to compare it with anything in hertz you must divide by two pi.

**f-s, in samples per second**, is how often the software updates. That is a property of **your implementation**.

The stabilising page's comparisons — crossover at two p, or five to ten p — are **design heuristics, not necessary-and-sufficient stability tests.** Likewise crossover below f-s over fifteen is a **sampling guideline, not a physical cap.**

Worked through: for an illustrative p of eight per second, choose crossover at five p, which is forty radians per second, which is **6.37 hertz**. The guideline then suggests a sample rate of at least fifteen times that — **95.5 hertz**.

**Read that number, because it is the point.** It does **not** prove that balance inherently requires one kilohertz. Higher rates get chosen for torque loops, contact transitions, estimation and delay margin — all good reasons — but they are not this reason. And for a shared sample rate you check **the most demanding controlled mode and loop**, not an average across the joints.

---

## The sampling lab — what actually happens

Now the first interactive, and it is more honest than the guideline.

The question it asks: **can this simplified leg recover from a five-degree ankle lean, at the chosen torque limit and sample rate?**

The important detail is what the verdict stat measures. The green poles on the left are **ideal continuous LQR**. The verdict checks something different — **the eigenvalues of A-d minus B-d K, the genuinely sampled closed loop, against the unit circle.**

At the defaults — thirty kilograms, 0.75 metres, **five hundred hertz**, a hundred and fifty newton-metres — updates are two milliseconds apart, the largest sampled pole magnitude is **0.980**, comfortably inside the unit circle, and torque clips on **0.7 percent** of samples. Stable.

Now drop the sample rate. At **two hundred hertz** — five millisecond updates — still inside the circle. At **fifty hertz**, twenty millisecond updates: **unstable.** At **five hertz**: very unstable. The fastest mode doubles in 75.8 milliseconds, and you are now updating every two hundred milliseconds — the error has grown by a factor of about six between one look and the next.

Then the more interesting slider: **torque limit**. Take it down to ten newton-metres and the linear verdict still says "inside unit circle" — but the readout says **torque clips on one hundred percent of samples.**

**That is the lesson of the panel.** Stable linear poles do not guarantee recovery when the command clips. During clipping the system is **nonlinear**: it does not simply become open loop, but its trajectory is no longer predicted by the poles you designed. Two separate facts, and the widget reports them separately on purpose.

One more caveat the page makes and I will repeat: this diagonal model has **no joint coupling**, so an ankle-only lean leaves the other joints at zero. The torque slider also changes R through Bryson scaling, so LQR genuinely redesigns for that budget. And the f-s-over-fifteen stat is only sampling headroom — no motor dynamics, no extra delay, no foot contact limits.

---

## The foot — the constraint no controller negotiates with

The six-state model asks how joint *angles* recover. Now a completely different question: **can this foot stop the moving body?**

For that, a second and much smaller model: the **linear inverted pendulum**. It assumes constant centre-of-mass height, a flat stationary support, adequate friction, maintained contact, and negligible change of angular momentum about the centre of mass. Vertical acceleration is zero, so the vertical force is just m g. Moment balance gives horizontal over vertical force equals x minus the centre of pressure, over z. Divide by m and you have:

**x double dot equals omega-nought squared, times x minus p-c-o-p**, with **omega-nought equal to root g over z**, and poles at **plus and minus omega-nought.**

Watch the symbols, because they collide. **x** is horizontal centre-of-mass position. **p-c-o-p** is a ground *position*, in metres — not the pole p from earlier. And **omega-nought is a growth-rate parameter, not a gait frequency and not an actuator bandwidth.**

At z of 0.75 metres, **omega-nought is 3.62 per second**, and the growing mode doubles in **192 milliseconds**. Note that does not match the joint model's numbers, and it should not — **they are different approximations of different questions.**

Now the trick that makes the whole thing usable. Define the **capture point**:

**xi equals x, plus x dot over omega-nought.**

Differentiate it, substitute the acceleration equation, and you get **xi dot equals omega-nought times xi minus the centre of pressure** — a *first-order* growing equation. Which means: **set the centre of pressure to xi at time zero, and the growth cancels exactly.** The velocity decays, and the centre of mass coasts to rest at that point.

**So xi is the place you would have to put your foot pressure to stop, and the question becomes purely geometric: is xi inside the foot?**

Under the stated assumptions the centre of pressure cannot leave the support polygon — the ground cannot pull. So the constraint is **absolute value of p-c-o-p, at most half the foot length.** With the ankle at the foot centre and negligible foot inertia, **ankle torque is about m g times the centre-of-pressure offset**, which for this robot's ten-centimetre half-foot is a bound of about **twenty-nine newton-metres.**

---

## The capture-point lab

Twenty-centimetre foot, so the edge is at plus or minus ten centimetres. Centre of mass at 0.75 metres, so omega-nought is 3.62.

**Push at 0.10 metres per second: xi is 2.8 centimetres.** Well inside the foot. **Feasible.**

**Push at 0.30: xi is 8.3 centimetres.** Still inside ten — but only just, and the peak ankle torque the plotted controller asks for is inside the twenty-nine newton-metre geometry bound.

**Push at 0.50: xi is 13.8 centimetres. Outside the toe.** And now no amount of control authority helps, because the ground cannot push from a place your foot is not.

**Push at 0.80: xi is 22.1 centimetres**, more than twice the foot.

Then change the foot instead of the push. Hold the push at 0.30, so xi stays at 8.3 centimetres. **Shrink the foot to ten centimetres** — edge now at five — and the same push that was recoverable becomes **outside support**. **Grow the foot to forty centimetres** and the bound rises to fifty-nine newton-metres and the push is comfortable.

**That is the page's central claim made concrete: foot geometry is a control parameter, and it is set in CAD.** No gain schedule recovers a push whose capture point lies beyond the toe.

Two honest qualifications, both of which the page states. First, the stat tests **theoretical no-step feasibility** — the plotted controller is one chosen recovery strategy, not a proof that every feasible push recovers under those particular gains. Second, **the initial xi is not a commanded step distance.** If the robot does step, swing time, reach, and xi *at landing* all have to be accounted for — a delayed step must target the **predicted future** capture point, not the value at the instant of the shove.

---

## Carry forward

Four things, in the order the page builds them.

**One.** A right-half-plane eigenvalue is a growth rate, and **log two over p is the time you have** before the error doubles. That is what diagnoses the uncontrolled problem.

**Two.** **Gravity is negative stiffness.** The minus-k-g term is the whole reason balance is a stabilisation problem rather than a tracking problem.

**Three.** **Growth rate, crossover and sample rate are three different quantities** in three different units, and the heuristics connecting them are heuristics. What you actually verify is the sampled closed-loop poles, the delays, the torque limits and the contact constraints — together, not one at a time.

**Four.** **A stable controller can still ask for something impossible.** The centre of pressure it requests may lie outside the foot, or the torque it requests may exceed the motor. Both of those are input constraints, not stability properties, and the unconstrained linear design will never mention them.

Which sets up the actuator block, and then Biped Two — because every number on this page assumed a joint that could deliver the torque you asked for, at the moment you asked for it. **The next question is what to actually bolt into each of those six joints, and why the right answer at the ankle is the wrong answer at the hip.**
