# Page 5 — What a First-Order System Is

*Listening script. Roughly twenty minutes. All seven systems in the dropdown, all five input types, and every row of the "so what" table.*

---

This is page five, and it is where the machinery actually starts.

The page opens by telling you what to read it for, which is one question: **so what?**

Classifying a plant as first order is not trivia, and it is not something to memorise. It is a measurement you make on real hardware. It costs one experiment. And it tells you four specific things you would otherwise have to guess. The last card on the page lists those four things, and everything before it is what you need in order to believe them.

And if the word "order" itself still feels arbitrary, page two is the one to read first — that is where the word is defined, where the storage-versus-dissipation table lives, and where the fact that one piece of hardware can be first order in speed and second order in position gets its proper explanation.

---

## What a first-order system physically is — no equation needed

One vocabulary note before we start, because page two insisted on it. What gets called a *store* on this page is properly an **energy-storage element**, and the quantity it refuses to let jump is a **state variable**. Order equals the number of independent energy-storage elements, which equals the number of state variables. The word "store" survives here only because it is shorter, and because the plumbing picture on the next page needs it.

Now. Forget transfer functions. A system is first order when it has exactly **two** physical features.

**Feature one. One thing that stores.** And not "holds energy" — the sharper test is: **one quantity that cannot change instantly.** A spinning mass will not let *speed* jump. A coil will not let *current* jump. A hot motor will not let *temperature* jump. That refusal is what a store is.

**Feature two. One thing that drains, in proportion to how much is stored.** Friction drags harder the faster you spin. Resistance burns more the more current flows. A hot object loses heat faster the hotter it already is.

Now, the phrase that trips everybody: *a mass stores speed*. That sounds wrong until you read it as **a mass refuses to let speed jump.** Nothing is being kept in a jar. To change omega you need torque; torque is finite; therefore omega moves smoothly and the past leaks into the present.

Every store is a **low-pass filter on one variable**. Mass smooths velocity. Inductance smooths current. Capacitance smooths voltage. Heat capacity smooths temperature. Same object in four costumes.

And the whole behaviour follows from those two features. You pour in at a constant rate. The level rises. But the fuller it gets, the faster it leaks — so the rise slows. Eventually the leak exactly matches the pour, and the level stops. That is every first-order response you will ever see: **a constant fill racing a leak that grows with the level, ending in a draw.**

---

## Interactive one — how you tell the order of something on your bench

You do not read the order off a datasheet. You **count energy stores** — one per quantity that cannot jump — and then you confirm it with a step test, because the two answers disagreeing means you missed a store.

There are seven systems in the dropdown. The last three exist specifically to show you what "missing a store" looks like. Let me go through all seven.

**One. Flywheel plus bearing friction. Torque in, speed out.**

A spinning mass with viscous friction. Push it with a constant torque and ask what its speed does.

Stores: the spinning mass J, holding speed omega — because changing omega needs torque and torque is finite, so omega cannot jump. That is one store.

Drains: bearing friction b, removing b times omega — bigger the faster it spins.

Equation: J omega dot equals tau minus b omega. Order one. Cannot overshoot. Maximum phase lag ninety degrees.

**Two. Motor winding, R-L. Voltage in, current out.**

The innermost loop in every servo drive. Apply a voltage, ask what the current does.

Stores: the coil's inductance L, holding current i — changing i needs voltage, and voltage is finite, so i cannot jump. One store.

Drains: winding resistance R, burning R times i.

Equation: L d i by d t equals V minus R i. Order one.

**Three. An RC low-pass filter. Voltage in, voltage out.**

The filter on your encoder derivative, or on an analogue force sensor. Same object in different clothes.

Stores: the capacitor C, holding voltage v — changing v needs current, and current is finite, so v cannot jump. One store.

Drains: the resistor R, passing charge away at a rate set by the voltage across it.

Equation: R C v dot plus v equals v in. Order one.

**Four. Motor thermal mass. Watts in, temperature out.**

Why you can overload a motor for two seconds and not for two minutes. The slowest first-order system on the robot.

Stores: the copper and iron's heat capacity C, holding temperature T — heating needs power, power is finite, so T cannot jump. One store.

Drains: conduction to ambient, one over R, losing heat faster the hotter it already is.

Equation: C T dot plus T over R equals P. Order one — with a time constant measured in minutes.

**Five. Mass plus spring plus damper. Force in, position out.**

Add a spring to the flywheel and count again. This is the moment the page you are on stops applying.

Stores: the mass m, holding velocity v, same reason as the flywheel. **And** the spring k, holding deflection x — because compressing a spring stores energy that is *not* the velocity. A second, hidden reservoir.

Drains: the damper c, removing c times v.

Equation: m x double dot plus c x dot plus k x equals F. **Order two.** Can overshoot: yes. Maximum phase lag: one hundred and eighty degrees.

**Six. Rigid joint, torque in, position out.**

And here is the important one. This is the same joint as entry one — but you decided to watch position instead of speed. That decision changed the order.

Stores: the inertia J, holding speed omega, as before. **And** position itself, holding angle theta — because theta is the running total of omega and never leaks. A perfect, never-draining store. This is what an *integrator* is.

Drains: bearing friction b, removing b omega — and note it drains the *speed* store, and nothing at all drains theta.

Equation: J theta double dot plus b theta dot equals tau. **Order two.**

**Seven. Series-elastic actuator. Motor torque in, load speed out.**

Motor, spring, load. Count the reservoirs before you tune anything on one of these.

Stores: motor inertia J m holding motor speed. The series spring k holding spring deflection. Load inertia J L holding load speed. **Three stores.**

Drains: load-side friction b.

Order three, and it rings.

---

### The step-test signature

This is how you check your count without opening anything up.

**A curve that leaves the origin with its steepest slope, and only ever flattens, has one store.**

**A curve that starts flat, gathers pace, and then either overshoots or eases in, has two or more.**

That initial flatness is the tell. It is the second store having to be filled before the output can move at all. Look for it on a scope and you can classify a joint in one push.

---

## Now the equation — it is the picture, written down

Newton for that flywheel. Rate of change of the stored quantity equals what you put in, minus what leaks out:

J omega dot equals tau minus b omega.

Three terms. **J omega dot** is the store filling up. **Tau** is the fill rate, constant. **b omega** is the leak — and note that it is proportional to omega, the level itself. That proportionality is the whole mechanism.

Move the leak across and divide by b, purely to make the shape obvious:

J over b, times omega dot, plus omega, equals tau over b.

Or in standard form: **tau c times y dot, plus y, equals K u.**

And here is the point: **one derivative equals one store equals first order.** Anything you can write as "something times y dot, plus y, equals input" is this system with different words for the store and the leak. Two derivatives means two stores, and the next three pages are about what that costs you.

---

## The two numbers, and what each physically is

**K, the DC gain.** Made of one over b — one over the leak. What it physically is: **how far it eventually gets, per unit of input.** A leakier system settles lower for the same push. Nothing to do with speed — purely "where does it end up".

**Tau c, the time constant.** Made of J over b — store divided by leak. What it physically is: **how long it takes.** A bigger store takes longer to fill; a bigger leak drains it faster, so it reaches balance sooner. Measured in seconds. The whole of page six is about this number.

And crucially: **K and tau are independent.** K says where. Tau says when. You can have a fast joint that barely moves, and a sluggish one that eventually swings a long way. Those are different complaints with different fixes, and confusing them wastes a lot of tuning time.

---

## Interactive two — why anyone cares: two numbers are the entire plant

This is the payoff widget, and it makes the practical case.

You are shown grey dots: a **measured** step response from a joint you have never seen, noisy, like a real encoder. You drag two sliders, K and tau, until your model — the blue line — sits on the dots. That is a two-minute experiment on real hardware, and there is a mismatch readout that tells you when you have it: "identified", "close", or "keep dragging".

Then you change the input. And **your two numbers keep predicting.**

There are five input types in the dropdown: a **step**, a **ramp**, a **square wave**, a **sine**, and a **torque pulse**. In every one of them, the model that matched the step also matches the real joint, because a first-order plant has nothing else in it. There is a button to randomise the unknown joint and do it again.

*That* is what identifying the order buys you: a complete, permanent model of the machine from one push.

---

## So what? Four things the answer "first order" actually decides

This is the card the whole page was built to earn. Four rows.

**One. How fast you are allowed to run the loop around it.**

Tau sets the fastest thing the plant can physically do. A winding with tau of half a millisecond settles in about two milliseconds, so a twenty kilohertz current loop is doing useful work every cycle. A joint with tau of three hundred milliseconds cannot respond to anything you send it faster than a few hertz — so a twenty kilohertz position loop is nineteen thousand nine hundred wasted computations per second, and three extra sources of noise. Page six turns this into a calculator.

**Two. Whether you are allowed to turn the gain up.**

A first-order plant with proportional feedback **cannot be destabilised at any gain**. That is a theorem, not a rule of thumb, and it is proved on page eight. So when a loop is first order you tune it by turning the knob until it is fast enough, and then stopping. When it is second order you cannot — and the entire controller-design half of this tutor exists for that case.

**Three. How many states your model, observer or reinforcement-learning agent needs.**

One store equals one state. A velocity estimator for a first-order joint needs one number. A position controller for the same joint needs two, because you added an integrator. Guess low and your observer will never converge. Guess high and you are estimating noise. **The count of energy stores is the state dimension.**

**Four. What it means when the hardware disagrees with you.**

And this is the one that earns its keep. If you counted one store and the joint **rings**, your count is wrong. There is a shaft winding up, a belt stretching, a mount flexing, a filter you forgot, or a delay.

The ringing is not a nuisance to be tuned away. It is the machine telling you where a reservoir is that you did not know about. Tuning it out with a lower gain hides the information and leaves the reservoir sitting there.

---

## The vocabulary, since it gets used loosely

**Overshoot.** The output goes *past* the target before coming back. Needs a second store, always.

**Ringing**, also called wobbling. It overshoots, comes back too far, overshoots again, each swing smaller. Energy sloshing between two stores while friction eats it. It *does* die out.

**Hunting.** The same swinging, but it **does not die out**. The joint never settles; it patrols around the setpoint forever. Usually too much gain, a delay, or stiction. Ringing is a tuning imperfection. Hunting is a fault.

**Settled.** The fill and the leak have become equal, so the net flow is zero. Strictly this takes forever; in practice "settled" means inside a plus-or-minus two percent band, which is four time constants.

And the guarantee: a first-order joint under constant torque does none of the first three. It rises, it flattens, it stops. If yours wobbles, re-read row four above.

---

## The same two features, four different physical dresses

**Motor winding.** L d i by d t plus R i equals V. Tau equals L over R, typically nought point one to two milliseconds.

**Velocity of a joint.** J omega dot plus b omega equals tau. Tau equals J over b. Torque in, speed out — first order, always.

**Any low-pass filter.** Tau y dot plus y equals u. Including the derivative filter you were told to always add on the PID page.

**Thermal.** C T dot plus T over R equals P. Tau equals R C, in **minutes**. Motor thermal limits are a first-order system with a very slow pole.

---

## Carrying forward

One store, one drain, two numbers. And the count of stores is something you measure, not something you are told.

Next page: what tau actually *is*, where nought point six three comes from, and why that one number decides your loop rate.
