# Page 4 — How Software Changes Physics

*Listening script. Roughly twenty minutes. Every line of the page, including all six rows of the synthesis table and all three failure modes.*

---

This is page four, and it is the one that answers the question that blocks everything else.

Let me state the question properly, the way it deserves to be stated. J and b are welded into the aluminium. A gain is a number in a loop. **How can the number change what the aluminium does?**

And the answer is: **it cannot, and it does not need to.**

The motion of the joint is not decided by J and b alone. It is decided by **Newton's law**, which says the acceleration comes from the *sum of the torques acting*. Software cannot touch J. But software decides the motor torque, and the motor torque is one of the terms in that sum. Change a term in the equation and you change the equation — and the equation is what the motion obeys.

That is the whole answer. Now let me do it in algebra, because seeing it happen is different from being told.

---

## The whole answer, in three lines of algebra

**Line one — the hardware.** This is fixed. Nothing you ever write changes it:

J theta double dot, plus b theta dot, equals tau motor plus tau external.

Inertia times acceleration, plus friction times velocity, equals the torque from the motor plus whatever the world is doing to you.

**Line two — the controller.** Here is the only thing software actually does. It reads the sensors and decides, right now, what number to send to the current loop. Take a plain PD aiming at a target angle theta d:

Tau motor equals minus K p times the quantity theta minus theta d, minus K d times theta dot.

That is it. Two multiplications and a subtraction. That is the entire controller.

**Line three — substitute the second into the first**, and move everything that depends on the motion over to the left-hand side:

J theta double dot, plus the quantity b plus K d, times theta dot, plus K p times theta, equals K p theta d plus tau external.

Now stop, and read that equation, because it *is* the answer to the question.

**It is a mass-spring-damper.**

The mass is still J. You were right — software cannot change it. But the damping coefficient is now **b plus K d**. And there is a **stiffness, K p**, in a joint that has no spring anywhere in it. Nowhere. There is no metal in that machine that has any elasticity you are relying on, and yet the equation of motion contains a stiffness term.

And nothing was faked to get there.

A steel spring produces a torque proportional to displacement and opposing it. Your controller reads displacement off the encoder and commands a torque proportional to it and opposing it. **The two torques are the same number, arriving at the same shaft, at the same moment.** The joint has no mechanism by which it could tell them apart. And neither does the person pushing on the arm.

So here is the honest one-liner, and it is worth memorising word for word: **software does not change the hardware's parameters. It adds terms to the hardware's equation of motion.**

And since behaviour is a property of the equation, and not of the hardware alone, that is enough. Everything else in control — pole placement, lead compensators, impedance control, LQR — is a more careful way of choosing which terms to add.

---

## A steel spring and a software spring, side by side

The page then gives you two rigs to compare, and I will describe what it shows.

**The left rig** is a bare joint with a real steel torsion spring bolted to it, stiffness k real, and a real oil damper, c real. No electronics at all. Pure mechanism.

**The right rig** is the same joint with *nothing* bolted to it, driven by a motor running tau equals minus K p theta minus K d theta dot.

Set K p equal to k real, and K d equal to c real, and press the button marked "match the hardware".

The two traces lie exactly on top of each other.

Not approximately. Not close enough for teaching purposes. The differential equations are the *same equation*, so the motions are the *same motion*. And on the pole map beside it, the software rig's poles land precisely on the steel rig's poles — the crosses sit inside the circles.

The line the page puts underneath is the one to take away: no measurement you can make at the shaft — position, velocity, reaction torque, energy — distinguishes them. **The physics does not care where the torque came from.**

One detail worth noticing, since it comes up when you try this for real: the joint's own friction b is present in *both* rigs and is already doing its share. So the software only has to supply what the bolted-on hardware would have added. You are topping up, not starting from nothing.

---

## What you can synthesise, what is hard, and what you cannot

Now the honest table. Six rows, and the pattern behind them is the useful bit.

**Stiffness — make one from nothing.** You do it with tau equals minus K p times the position error. And it is **easy**. The joint has no spring, so you can give it any stiffness you like — and, crucially, you can change it mid-motion, which no steel spring can do. This is the single biggest reason to use a motor rather than a mechanism.

**Damping — add some.** Tau equals minus K d times theta dot. **Easy**, and it is the most common thing a controller does.

**Damping — remove some.** Tau equals plus K d times theta dot. A negative gain. This is **possible but dangerous**. You are commanding the motor to help the motion along, which is exactly the negative-friction case that puts a pole in the right half plane. It is used deliberately, for friction compensation and for transparency, and it is always a knife-edge.

**Gravity — cancel it.** Tau plus equals m g l sine theta, as a feedforward term. This is **easy, and it feels like magic**. You add the torque that gravity is taking away, and the arm becomes weightless in your hand. Pure software, no hardware change. And it is exactly why you needed the m g l number from page three — this is what you were measuring it for.

**Inertia — increase it.** Tau equals minus K a times theta double dot. This **works**, if you can get a clean acceleration signal. Which you usually cannot, since differentiating an encoder twice is mostly noise.

**Inertia — reduce it.** Tau equals plus K a times theta double dot. And this is **the hard one, and the honest limit of the whole approach.**

To make the arm feel lighter than it is, the motor must supply torque the *instant* you push — before it has measured anything. But you are always one sample late. So the cancellation fails at exactly the frequencies where it matters most. **This is why a series-elastic actuator hides its rotor mechanically instead**, and it is the whole subject of the effective-inertia pages later on.

Now, the pattern behind that table, which is the part worth carrying:

**You can only synthesise a term in a variable you can measure, and you can only synthesise it as fast as your loop runs.**

Stiffness needs position — cheap, accurate, available. Damping needs velocity — one derivative, noisier, which is why there is a filter on the D term. Inertia needs acceleration — two derivatives, mostly noise, and needed instantly.

**The difficulty ranking is exactly the differentiation ranking.** That is not a coincidence. It is the whole reason.

---

## The three places the illusion breaks

This is the part that separates people who have read about impedance control from people who have shipped it.

### Break one — bandwidth

The first plot shows **what the world feels** when it pushes the joint at a given frequency. The proper name for this is the **rendered impedance**.

Push slowly, and you feel the virtual spring K p, exactly as designed. The curve is flat at the stiffness you asked for.

Push faster, and the controller starts falling behind. Past the loop bandwidth it has no useful influence at all, and what your hand feels is the **raw inertia J**, rising as J omega squared.

Which means: **tap a software-compliant joint sharply, and it is a lump of metal.**

A steel spring has no such limit. It is a spring at every frequency, because it does not have to compute anything. That is the fundamental difference, and it is not a matter of buying a faster processor — it is structural.

With the default settings the corner sits at about two hertz. Below two hertz, your hand feels the spring you designed. Above it, your hand feels the metal.

### Break two — the torque limit

A virtual spring with a stiffness of five hundred newton metres per radian demands five hundred times the deflection in newton metres. The motor may simply not have it.

The widget shows this as "travel before saturating" — how far you can push before the motor runs out of torque and the spring illusion collapses. Raise K p to push the bandwidth corner up, and watch that travel number shrink. You cannot have both.

### Break three — delay

And this is the one that bites hardest.

The K d term commands a torque opposing the velocity it measured. But that velocity is a few milliseconds old. At high frequency, the joint has *already reversed* by the time the torque arrives — so the torque pushes **with** the motion instead of against it, and adds energy on every cycle.

**The delay turned the virtual damper into a virtual anti-damper.**

A steel damper cannot do this. It responds to the velocity *now*, because it is not computing anything.

And notice how it fails, because this is worth knowing for real hardware: it does not fly apart. It settles into a steady buzz. That is the torque limit turning a divergence into a **limit cycle** — and it is exactly what an unstable joint sounds like on a real robot. A hum, at a fixed frequency and a fixed amplitude. Not an explosion.

The readout in the widget calls this "buzzing", and you can find it by raising K d and the delay together. Higher K d destabilises at *lower* delay, because raising K d raises the crossover frequency, and at higher frequency a given delay eats more phase.

---

## The deepest difference: where the energy comes from

This one is more fundamental than the other three.

A steel spring is **passive**. Every joule it gives back was a joule you put in. It is physically incapable of injecting energy into your arm — which is why no arrangement of springs and dampers has ever oscillated on its own.

A software spring is **active**. Its torque is supplied by the motor, out of the DC bus, and there is nothing in the arithmetic that forbids it from putting in more than it takes out. Get the phase slightly wrong — through delay, through a filter, or through a gain that is too high — and the "damper" starts pushing *with* the motion instead of against it.

**That is the real price of doing mechanics in software, and it is the one thing a mechanism never charges you.** A virtual spring can destabilise the machine it is attached to. A steel one cannot, ever.

The formal version of this is called **passivity**, and it is why series-elastic actuators exist. Putting a real spring in the transmission means the fast, high-force part of the interaction is handled by something that is passive by construction — leaving software to shape only the slow part it can actually keep up with. The SEA and passivity pages are that argument in full.

---

## So what is a pole or a zero "in the controller", physically?

You can now answer this concretely, which you could not before.

**A controller pole is a number the software remembers between samples.** The integrator's accumulator is one. A filter's previous output is one. It is a state variable made of memory instead of metal — and it behaves like one, including contributing phase lag.

**A controller zero is the controller reacting to a rate of change.** The D term is a zero. It contributes phase *lead*, which is why it damps.

**And the closed-loop poles are the roots of the combined equation** — the one derived at the top of this page. The plant contributes its terms. The controller contributes its terms. The roots depend on both. Neither side owns them.

Here is the picture to keep: **the controller is a machine built out of arithmetic, wired to the real machine through a sensor and a motor. The pair is one bigger machine**, with more state variables than the metal had on its own, and it is the bigger machine's equation that decides what happens.

So "placing the poles" is choosing the coefficients of that equation. And "designing a controller" is deciding what virtual mechanism to build out of software and bolt on. Root locus, lead compensators, LQR and pole placement are four different ways of doing that deliberately instead of by trial and error.

---

## And now the three control paradigms are one equation

Look at what was derived, and read off the special cases. These are not three different subjects. They are three choices of two numbers.

The equation again: J theta double dot, plus b plus K d, times theta dot, plus K p theta, equals K p theta d plus tau external.

**Torque control.** Choose K p equals K d equals zero, and command tau directly. Zero virtual stiffness. Push the joint and it moves — it does not argue. Maximum transparency, no position authority whatsoever.

**Impedance control.** Choose K p and K d to be the stiffness and damping you *want* the world to feel. What you get is exactly the mechanical impedance you designed — inside the bandwidth. And note this properly: **this whole page is the derivation of impedance control.** The later pages only add detail.

**Position control.** Choose K p and K d as large as stability allows. A very stiff virtual spring: be at theta d, whatever force that takes. The external torque term gets overwhelmed, which is the same thing as saying the joint stops noticing you.

**They were one controller all along, with a knob between them.** And that knob is the magnitude of Z — the impedance — which is the size of K p plus the size of K d. Turn it to zero and you have torque control. Turn it up and you slide continuously to position control. There is no boundary; it is one line.

If that now feels obvious rather than clever, this page did its job, and the impedance pages later on will read as detail rather than as a new subject.

---

## Carrying forward

Software cannot change J or b. It adds terms to the equation of motion, and the equation is what the motion obeys — so the joint genuinely behaves as though it had a spring and a damper it does not physically have.

The limits are real and worth respecting. Only inside the bandwidth. Only within the torque limit. And only while the phase is honest.

Everything from here is about choosing those added terms well.

Next up, page five: what a first-order system actually is.
