# Page 2 — The Control Problem

*Listening script. Roughly twenty minutes. Nothing on the page is skipped, including every dropdown option and every table row.*

---

Welcome to page two of the control tutor. This one is called The Control Problem, and it is deliberately different from every page that follows it. Nothing here is derived. There is no algebra you have to keep up with. This is the map you look at before you walk into the territory, and its whole job is to make sure that when the next eight pages start talking about poles and time constants and orders, you already know what all of that is *for*.

Let me start with the thing the page opens with, because it is a compliment and it is also the thesis.

You already worked out the shape of this yourself, and you were right. A plant has some behaviour of its own. You want different behaviour. So you characterise what it does, decide what you want instead, and add a controller that closes the gap. That is the entire discipline in one sentence, and everything else is detail.

Pages three and four are the two questions that have to be settled before any of it works. Page three is: how do you actually measure a real joint — where do the numbers come from. Page four is: how can a line of software possibly change what metal does. Pages five to ten are the *characterising* half, and pages fourteen to seventeen are the *closing the gap* half. This page is the map over all of it.

---

## Every control problem, in four steps

The page lays this out as a four-row table, and I want to read all four out properly, because the order matters.

**Step one. What does the thing do on its own?**

Push it and watch. This is the **plant** — the physical thing you are trying to control — and its unforced behaviour is called the **open-loop response**. Characterising it means answering a specific list of questions: how fast is it, how far does it go, does it overshoot, and can it be destabilised. Pages three to ten are entirely this. Eight pages on one step, which should tell you how much of control engineering is actually just understanding the thing in front of you before touching it.

**Step two. What do you want instead?**

This gets written down as **specifications**. Things like: settle within two hundred milliseconds. No more than five percent overshoot. Zero steady-state error against gravity. Recover from a kick in half a second. And stay that way when the payload doubles.

Notice something about that list. Every one of those is a statement about either the **transient** — the part of the response that dies away — or the **steady state** — where it ends up. Those are exactly the two things the next pages teach you to read off a curve. The specification language and the analysis language are the same language, which is not a coincidence.

**Step three. How far apart are those two?**

This is where order matters, and this is the step people skip.

Some gaps close with a single gain knob. You turn it up, the thing gets faster, you stop. Some gaps cannot be closed by any gain at all, no matter how far you turn it, and need a different *kind* of controller. And some gaps cannot be closed in software at all without changing the mechanics — the hardware simply will not do what you are asking.

Knowing which of those three cases you are in, *before* you start tuning, is most of the skill. People who are good at this are not people who tune faster. They are people who know in advance which knob is going to help.

**Step four. Add a controller and close the loop.**

P, PD, PI, PID, lead, lag, state feedback. Pages fourteen to seventeen.

And here is the sentence that makes the whole subject one subject: **a controller does not change the plant. It moves the plant's poles.** The metal is unchanged. What feedback does is rearrange where the roots of the closed-loop equation sit. If that sentence means nothing to you yet, that is fine — it is what pages five to ten exist to give meaning to. But hold onto the shape of it.

---

## The first interactive — the same joint, with and without a controller

The page then gives you something to play with, and since you are driving I will describe exactly what it does and what each setting shows.

The setup is one rigid joint. It has inertia J and bearing friction b. Torque goes in, and you are watching **position** come out. The mechanism is identical in every single case. The only thing that changes is what software sits in front of it.

There is a dropdown with five options, and three sliders underneath it for the gains K p, K d and K i. There are five readouts: overshoot, settling time, error against a load, closed-loop order, and whether it is stable.

Let me go through all five dropdown options, because that progression *is* the lesson.

**Option one — no controller. Open loop.**

You apply a constant torque and nothing is watching the angle. The joint accelerates until friction balances the torque, and then it keeps turning at that speed forever. The output runs away. The readout says the closed-loop order is two and the stability verdict is no. It never settles.

That is what "open loop" means, and it is why the pole at the origin matters — which is a whole page later on, page seven. For now, just notice: with nothing comparing the output to a target, there is no mechanism by which the joint could ever arrive anywhere.

**Option two — P. Proportional control.**

Now it aims. The controller supplies a restoring torque proportional to the error. Read that again, because it is the key: a torque proportional to displacement, opposing it. That is what a spring does. So the controller is *behaving like a spring*, which means there are now two energy-storage elements in the loop instead of one, and it can **ring**.

And it does. With the default gains, the overshoot readout says sixty-six percent. The joint sails past the target and swings back. It settles eventually, but ugly.

There is a second problem. Against a constant load — gravity, say — it settles short. Permanently short. And the reason is almost tautological: the controller's output is proportional to the error, so to produce the torque that holds the arm up, the error has to be non-zero. The joint must stay wrong in order to hold itself up. You can shrink that error by raising K p, but you can never remove it, and eventually raising K p costs you stability.

**Option three — PD.**

The D term reacts to how fast the error is changing. A torque proportional to velocity, opposing it — which is what a *damper* does. So now you have added a virtual damper on top of the virtual spring, and the poles get dragged away from the imaginary axis. The overshoot readout drops to about four percent and the settling time to about a sixth of a second.

The ringing is gone. But it still settles short against a load, because the D term does nothing when nothing is moving.

**Option four — PI.**

The I term adds a state that never decays — an accumulator. Because it never decays, the command can hold a bias while the error is zero, and the load error disappears entirely. The steady-state readout goes to zero.

But it added a pole. The closed-loop order goes up, and now the loop can be pushed unstable in a way it could not before. The default settings show around seventy percent overshoot, which is worse than P was — you fixed one thing and broke another.

**Option five — PID.**

D damps the ringing, I removes the load error. Three percent overshoot, a seventh of a second settling, zero steady-state error. Three knobs, three pole positions you are bargaining over.

And everything from that point onwards in the tutor is about doing that bargaining deliberately, instead of by trial and error.

The line the page repeats under every one of those five options is the important one: **the plant never changed.** J and b are the same number in every single case. Only the pole positions moved.

---

## So why is "what order is it?" the first thing anyone asks?

Because the answer decides what kind of problem you are in, before you touch a single gain. The page lists five specific consequences.

**One. Whether turning the gain up can ever hurt you.** A first-order plant under proportional feedback is stable at any gain. That is a theorem, not a rule of thumb, and it gets proved on page eight. A second-order plant is not. So "first order" means: tune until it is fast enough, and stop. And "second order or more" means: there is a limit, and you must go and find it.

**Two. Whether it can overshoot at all.** One storage element cannot overshoot. Ever. So if yours does, your model is wrong, and the overshoot is telling you where.

**Three. How fast a loop around it is worth running.** The slowest pole sets the ceiling. Everything faster than that is wasted computation and amplified noise.

**Four. How many numbers your model, observer or estimator needs.** Order equals the number of state variables equals the size of the vector you have to carry.

**Five. How much phase lag the plant will contribute** — which is what decides how much feedback you can apply before the loop turns on you. Roughly ninety degrees per storage element.

And the short version, which the page puts in a box: **order tells you how much trouble the plant is capable of causing.** One store, no trouble. Two, it can overshoot and it can be destabilised. Three or more, you stop tuning by feel and start designing.

---

## The standard vocabulary — including the words I should have been using

Now a confession, and it is worth hearing because vocabulary is what lets you read anyone else's work.

Throughout these pages the word "store" gets used a lot. The textbook word is **state variable**, and the physical part that creates one is an **energy-storage element**. Use those. They are what everyone else says.

Here is the vocabulary table, in full.

**Plant.** The physical thing you are trying to control, plus its actuator and its sensor. The joint, the motor, the arm.

**State.** And this is the real definition, so listen carefully: the *smallest set of numbers that, together with all future inputs, determines all future behaviour.* Read that twice. In plain words: if you told me these numbers right now, and then told me what torque I will apply from here on, I could predict everything the system will ever do.

**State variable.** One of those numbers. For a spinning rotor, it is omega, the speed. For a coil, it is the current. For a spring, it is its deflection.

**Energy-storage element.** The physical part that makes a state variable necessary. A mass, a spring, an inductor, a capacitor, a thermal mass. Each one holds energy, and the amount it holds cannot change instantly.

**Order.** The number of state variables, which equals the number of independent energy-storage elements. Equivalently, the highest derivative in the differential equation, or the degree of the denominator of the transfer function. Those are all the same number.

**Pole.** A root of that denominator. One per order. Each one describes one **mode** — one way the system's transient can behave.

And then a point that ties two ideas together. Why are "cannot change instantly" and "stores energy" the same test?

Because to change the energy in a component you have to move power through it, and power is finite. So the energy — and therefore the variable that carries it — has to move smoothly. That is why the test "can this quantity jump?" and the test "does this part store energy?" always give the same answer. Use whichever one is easier to see on the hardware in front of you.

---

## Which parts add a state, and which add none

This is the table to memorise, and it answers two questions people always ask.

The ones that **store**:

A **mass or inertia** stores kinetic energy, one half m v squared. Its state variable is velocity, or speed omega. Adds one to the order.

A **spring, or stiffness**, stores potential energy, one half k x squared. Its state variable is deflection, or position. Adds one to the order.

An **inductor or motor winding** stores magnetic energy, one half L i squared. Its state variable is current. Adds one.

A **capacitor** stores electric energy, one half C v squared. Its state variable is voltage. Adds one.

A **thermal mass** stores heat, C times T. Its state variable is temperature. Adds one.

And the ones that **do not store**:

A **damper or viscous friction** — no. It converts energy to heat and loses it. No state variable. Adds **zero** to the order.

A **resistor** — no. Adds zero.

**Thermal conduction** — no. Adds zero.

A plain **gain, lever or gear** — no. Adds zero.

Now, that table answers both of the questions that come up every time.

First question: *if the damper dissipates, what does stiffness do?* It **stores**. A spring is an energy-storage element exactly like a mass, just holding a different kind of energy. That is why a mass-spring-damper is second order: two storers and one dissipator.

Second question: *is a third-order system two storages and two dampings?* No. **Third order means three storage elements.** Dampers never count, no matter how many of them there are. A motor inertia, a series spring and a load inertia is third order whether it has one damper or six.

And there is one caveat so it does not bite you later: the storage elements have to be **independent**. Two springs bolted rigidly in parallel are one spring and one state, not two, because their deflections are not free to differ. Only count storage elements whose stored quantity can vary on its own.

---

## The second interactive — add parts and watch the order not change

Six machines, built up one element at a time. Each one lists its parts and marks each part either STORE or DISSIPATE, then shows the resulting order, the step response, and the pole map. Here are all six.

**Build one. A rotor spinning in free space. Torque in, speed out.** One part: rotor inertia J, which stores kinetic energy, and its state is speed omega. That is it — one storage element and no dissipation at all. Order one. And the single pole sits exactly at the origin, so it never settles: a constant torque just keeps accelerating it forever. This is the integrator, which gets a whole page on page seven.

**Build two. Rotor plus bearing friction. Torque in, speed out.** Two parts now: the rotor inertia, which stores, and bearing friction b, which dissipates — it turns energy into heat and loses it, so no state. And here is the point: adding the damper did **not** change the order. It moved the pole off the origin, so now the thing settles. But it is still order one, because a damper stores nothing.

**Build three. Rotor plus friction plus a second damper.** Three parts: rotor inertia storing, bearing friction b one dissipating, and windage or seal drag b two also dissipating. **Two dampers, and still order one.** This is the case worth staring at. You can bolt on as many dissipative elements as you like and the order never moves. All they do is push the existing pole further left. Order counts storage, and only storage.

**Build four. Mass plus spring plus damper. Force in, position out.** Three parts: the mass m, storing kinetic energy with state velocity. The spring k, storing potential energy with state deflection. And the damper c, dissipating, no state. Now there is a second *storage* element. Order two — and for the first time the response can overshoot, because energy can sit in the mass while the spring is already where it wants to be.

**Build five. A series-elastic actuator: motor, spring, load. Torque in, load speed out.** Four parts: motor inertia J m, storing, state is motor speed. The series spring k, storing, state is spring deflection. Load inertia J L, storing, state is load speed. And load damping b, dissipating, no state. **Three storage elements, order three.** This is the answer to "what does a third-order system look like" — not two dampers and two springs, but *three places to keep energy*. And notice that it rings: with three stores there are more ways for energy to slosh, and the response gets harder to predict by eye.

**Build six. An SEA driving a flexible link. Torque in, tip speed out.** Five parts: motor inertia storing, series spring k one storing, link inertia storing, link flexibility k two storing, and damping b dissipating. Four storage elements, order four. Two pairs of poles, two resonances, and a response nobody can tune by feel. This is why mechanical designers get asked to make things stiff: every flexibility you add is another state the controller now has to cope with.

---

## "The plant is the plant" — the thing that has been bothering you

Now the part that is genuinely subtle, and the objection is a good one.

The objection goes: a car's suspension is a car's suspension. It has the springs it has and the dampers it has. How can the same lump of metal be first order when I watch one thing and second order when I watch another?

And the answer is: **the physics does not change. The plant really is the plant.** What changes is which part of it your chosen output can see.

Take the rotor. Inertia J, friction b, torque in. Two equations:

Theta dot equals omega. And J omega dot equals tau minus b omega.

That is the plant, and it has **two state variables — theta and omega — always.** Two numbers you would need to be told before you could predict its future. Nothing you measure changes that. The rotor really is accumulating angle whether or not anyone is looking at it.

Now look at the first equation. Theta appears on the left. But theta appears **nowhere on the right** of either equation.

The angle is *fed by* the speed and *affects nothing*. It is a dead end — a state that the rest of the system does not care about. So if your output is **speed**, the theta state has no influence on anything you can measure, and the input-output behaviour you can see is governed by one equation, not two. **First order.**

If your output is **position**, that dead end is now exactly the thing you are watching, and both equations matter. **Second order.**

The standard name for this is **observability**, and it is a whole page later on, page seventeen. A state that produces no signature at your sensor is called **unobservable**, and a transfer function silently drops every unobservable mode. That is why the *transfer-function order* can be lower than the number of state variables. The full model is called a **realisation**; the reduced one that keeps only what is both drivable and visible is the **minimal realisation**, and that is what a transfer function always is.

So the honest statement, which is the one to carry:

The **plant** has a fixed number of state variables, set by its energy-storage elements. That is a property of the hardware, and nothing you do changes it.

A **transfer function** is not the plant. It is the answer to one specific question — if I push *here*, what happens *there*? — and different questions about the same hardware have different answers, and different orders.

When people say "the joint is first order" they always mean "torque in, speed out is first order". **The sloppiness is in the sentence, not in the physics.**

---

## And the part that is not just bookkeeping

The page then gives you a demonstration that this matters physically, not just on paper.

A velocity loop is holding the joint at zero speed, and it is doing it well. At some point something knocks the joint — a foot hits a rock, someone bumps the arm.

On the left panel, you watch the speed. It dips, and it comes straight back to zero. The controller did its job perfectly. As far as the controller is concerned, nothing happened and the error is gone.

On the right panel, you watch the angle. It moved. And it **never comes back**. With the default settings it ends up about nine tenths of a degree away from where it started, permanently, and no amount of velocity-loop gain will ever fix it — because the loop cannot see theta.

That unobservable state was not a mathematical technicality. It was a real physical quantity that quietly changed while a perfectly healthy controller reported no error.

And this is why real machines run a position loop wrapped around a velocity loop wrapped around a current loop. Each layer watches a state the layer inside it is blind to. **The cascade is not a convention — it is the direct consequence of the fact that different outputs see different parts of the same plant.**

---

## The five words used for what a response does

These get used loosely and it makes everything harder than it needs to be. Every response splits into exactly two parts, and four of the five words are about the first part.

The response equals the **steady state** plus the **transient**.

**Steady state** is where the output ends up and stays. The part that does *not* go away. If you commanded one point zero and it ends at zero point nine, the steady state is zero point nine and the zero point one gap is **steady-state error**.

**Transient** is everything else — the difference between where the output is right now and where it will end up. **This is the part that decays**, and it is the only thing poles describe.

**Decay** is what the transient does. It shrinks exponentially, at a rate given by the real part of the pole. Standard, precise, and the word to use.

**Settle** is the observable consequence of the transient having decayed far enough to ignore. Settling time is when the response enters and stays inside a plus-or-minus two percent band. **Settling and decaying are the same event** — one named from the outside, one from the inside.

**Die** is informal, and it is the source of the confusion. When someone says "the response dies" they mean **the transient** dies. The output does not go to zero — it goes to the steady state and stays there. **What dies is the error, not the motion.**

So "we want it to settle, not to die" was never a real conflict. You want the joint to hold thirty degrees — that is the steady state, and it persists. You want the wobbling and the leftover swing on the way there to vanish quickly — that is the transient, and it is what decays. Fast decay *is* fast settling. The output survives; the discrepancy is what dies.

---

## What the next eight pages do, and why in that order

**Page three. Measuring a real joint.** Where J, b and k actually come from. Four bench experiments, and the regression that gets all of them at once — because every number on every later page is one you had to go and measure.

**Page four. How software changes physics.** The one that has to be settled before poles mean anything: you cannot change J with a gain, so how does a gain change the behaviour? Answer: it adds a term to the equation of motion.

**Page five. What a first-order system is.** One storage element. How you identify order on real hardware, and what the answer buys you.

**Page six. The time constant and the pole.** How fast, expressed three equivalent ways. Where zero point six three comes from. Why the current loop runs at twenty kilohertz.

**Page seven. The pole at the origin.** A storage element with no dissipation. Why position is second order, and why the I term works.

**Page eight. First order in frequency.** Shake it with a sine instead of stepping it. Bandwidth, decibels, phase lag — the language every datasheet and every loop-shaping argument uses.

**Page nine. The s-plane.** The two axes, what the imaginary part physically is, and the second storage element that creates it.

**Page ten. Second-order systems.** Omega n and zeta — and the fact that the K and B of an impedance controller *are* omega n and zeta. This is where every robot joint you will ever tune actually lives.

And the closing thought: read them as one argument, not eight topics. Measure the plant. Count the storage elements. That gives the order. The order gives the number of poles. Each pole's position gives one rate. Those rates are the whole behaviour. And a controller is a device for moving them, by adding terms to the equation.

Every page is one link in that chain.

That is page two. Next up, page three: where the numbers actually come from.
