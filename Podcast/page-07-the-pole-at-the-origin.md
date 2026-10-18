# Page 7 — The Pole at the Origin

*Listening script. Roughly twenty minutes. All three interactives and the full table of where integrators come from.*

---

This is page seven, and it is about one specific pole location: exactly zero.

Everything so far has had a drain. Friction bleeds speed. Resistance bleeds current. Conduction bleeds heat. And because the drain grows with the level, the level settles and the transient dies.

Now delete the drain and keep the store. That single change moves the pole to exactly s equals zero, and produces an object with properties unlike anything on the last three pages.

---

## What "no drain" does to the equation

Start from the flywheel and set the friction b to zero.

You had: J omega dot equals tau minus b omega.

You now have: J omega dot equals tau.

There is no longer any term containing omega on the right. **The rate of change no longer depends on the level at all** — only on what you are putting in.

Divide through, and the transfer function is G of s equals one over J s, with a pole at s equals zero.

And the output is literally the running total of the input:

Omega of t equals one over J, times the integral from zero to t of tau.

**That is why it is called an integrator: its output is the integral of its input.** It does not respond to the input, it *accumulates* it. And because nothing removes what has accumulated, the accumulation is permanent.

### Where integrators physically come from — always the same two cases

**Case one: a store with negligible loss.** A flywheel in good bearings, a frictionless joint, a superconducting coil, a perfectly insulated mass. Push it once and it keeps going.

**Case two: a quantity that is *defined* as the running total of another.** Position is the running total of velocity. Charge is the running total of current. Distance travelled is the running total of speed.

**These are integrators by definition, not by accident, and they are the ones that catch people out.** Nobody is surprised that a frictionless flywheel coasts. Plenty of people are surprised that watching position instead of speed added a state.

---

## Interactive one — remove the drain and watch what changes

There is one slider: the drain rate, a. Drag it down towards zero and watch two panels. The dashed grey trace is always the a-equals-zero case, shown for comparison.

**Left panel — kick it once, then let go.** This is the zero-input response.

With a drain, the transient decays and the system returns to where it started. The disturbance leaves no trace. With the default a of four per second, three seconds after the kick essentially nothing is left.

At a equals zero, the kick is **held forever**. One hundred percent of it, still there, three seconds later and three hours later. Nothing returns it, so the system is permanently offset by whatever happened to it.

**Right panel — hold a constant input.** This is the step response.

With a drain it settles, because the drain grows until it matches the input. The final level is one over a, and there the output stops.

At a equals zero there is nothing to grow, so nothing ever balances the input, and the output **ramps without limit**. Straight line, forever.

The readouts tell you the pole, the time constant, how much of the kick is left after three seconds, whether the step response settles or ramps, and the stability classification. At a equals zero the classification changes to **marginally stable**.

---

## Marginally stable — the third category, and why it needs one

A pole strictly in the left half plane is **stable**: transients decay. A pole in the right half plane is **unstable**: they grow without bound. A pole exactly *on* the boundary is neither, and it gets its own name — **marginally stable**.

That is not a technicality. A marginally stable system does not blow up, so it is not dangerous the way an unstable one is. But it never settles either, and every disturbance it has ever received is still in there, added up.

Two hours of a tiny sensor bias integrates into a large, confident, completely wrong number. Which is exactly what **drift** is — and why dead reckoning from an accelerometer fails, and why gyro bias has to be estimated rather than ignored.

The key sentence: **an integrator is the only linear system whose behaviour depends on your entire history rather than your recent history.** A pole at minus twenty has a transient that is effectively gone after about two hundred milliseconds, so only the recent past is still visible in the output. A pole at zero has no transient decay at all: every disturbance it has ever received is still in there, summed, and will still be in there in an hour.

---

## Why you deliberately put one in your controller

Take a joint holding a position against gravity. Gravity is a constant disturbance torque — it does not go away.

**With proportional control only**, the command is u equals K p times the error. To produce the torque that cancels gravity you need u to be non-zero. And since u is *proportional to the error*, you therefore need the **error to be non-zero**.

Read that again, because it is almost circular and that is the point: **the joint must stay permanently wrong in order to hold itself up.** Raising K p shrinks the error but never removes it, and eventually costs you stability.

**An integrator breaks that logic, and it is the only thing that can.**

Its output does not depend on the error *now*. It depends on the error's whole history. So it can sit at exactly the torque gravity demands **while the error is zero** — because the accumulated total stays put, since nothing drains it.

That is the whole argument for the **I** term, and it is a direct consequence of the pole being at the origin. A state that decayed would let the command sag back towards zero, and the error would reappear. **You need a state whose transient does not decay, precisely because you need a command that does not sag.**

---

## Interactive two — P alone versus PI, with the integrator's internal state shown

A first-order joint, commanded to one point zero. At a marked time, a constant load disturbance is applied — a hand pushing, or gravity after the arm extends.

The left panel shows the commanded value, the P-only response, and the PI response. Before the disturbance, P-only sits short of the target — about twenty percent short with the default gain. When the load lands, P-only gets *worse*, dropping to about forty percent error. PI dips briefly and comes back to zero.

But the **right panel** is the one to watch. It shows the integrator's stored value — the command it is holding.

Before the load arrives it sits at one point zero, the command needed to hold the target. When the load lands, it climbs by exactly the size of the load, and then **stops and stays there**, with the error back at zero. With a load of nought point five, it settles at one point five. With a load of one point zero, it settles at two point zero.

**That flat line at a new non-zero value is the entire point.** A state that decayed would sag back and let the error return. Turn K i to zero and watch the joint settle permanently short instead.

And then push K i up. The error dies sooner, and the response starts to overshoot and ring — because you have added a second energy store to the loop, and a loop with two stores can do that. At K i of forty you get four percent overshoot; at a hundred, sixteen percent; at two hundred, twenty-eight percent.

An integrator is not free. It costs you a pole, ninety degrees of phase lag at every frequency, and the risk of **integrator windup** when the actuator saturates and the accumulation keeps growing against a command that cannot be executed. The PID page deals with windup properly.

---

## Inertia and damping, position out — where the second store is hiding

This is the question worth being stubborn about, because the answer is the whole reason position control is harder than speed control.

The objection: the mechanism really does have one mass and one damper. How is that not first order?

The answer: **the order of a system is not the number of parts.** It is the number of quantities that cannot change instantly — the number of numbers you must be told before you can predict the future. Apply the test honestly.

**Can the speed omega jump?** No — that would need infinite torque. **One store.**

**Can the angle theta jump?** Also no — the joint cannot teleport. Theta is the running total of omega, and a running total of a finite quantity moves smoothly. **Two stores.**

And here is the resolution: **the second store is not a spring. It is the integrator you got for free the moment you decided to watch position instead of speed.**

Nothing physical was added. You changed which variable you call the output, and that changed the order. Friction drains omega; **nothing drains theta**. So the joint has one leaky store and one perfect one, and its two poles are exactly where you would now expect: one at minus b over J from the leaky store, and one at **zero** from the perfect one.

In symbols: J theta double dot plus b theta dot equals tau, which gives G of s equals one over s times the quantity J s plus b, which has poles at s equals zero and s equals minus b over J.

And now the overshoot question answers itself. Close a proportional position loop. The controller supplies a restoring torque proportional to the error, so it is *acting as the spring*. When the joint reaches the target the error is zero and the controller's torque is zero — but the mass is still moving, because its kinetic energy is a store that is not the output variable. It sails past.

**Position control of a plain damped inertia can ring, and speed control of the identical hardware cannot.** Same metal, different output, different order.

---

## Interactive three — the same joint, speed out versus position out

One piece of hardware, two choices of output, two different systems. Sliders for inertia, damping, and the position-loop gain.

The readouts show the order with speed out (one) and with position out (two), the open-loop poles (zero and minus b over J), and the closed-loop overshoot.

The left plot shows both open-loop step responses under constant torque: speed out settles, position out ramps away. The right plot shows the closed position loop, which **can** overshoot — raise the gain or lower the damping and watch it ring.

---

## Where integrators show up, and what each one costs you

Five rows.

**Position, from velocity.** Why it is there: definitional. Nothing you can remove. What it costs: every position loop is at least second order.

**The I in a PID.** Why: deliberate — it kills steady-state error against constant disturbances. What it costs: a pole, ninety degrees of lag, and windup on saturation.

**A frictionless or low-friction joint.** Why: accidental — good bearings, direct drive. What it costs: it coasts; it will not stop itself.

**Dead reckoning from a rate sensor.** Why: you integrated a gyro or an accelerometer. What it costs: **drift** — bias accumulates without bound, and no filter recovers it without an absolute reference.

**A charge-storing capacitor with no leakage path.** Why: circuit topology. What it costs: offsets never clear themselves.

And the one-line summary: **a pole in the left half plane has a transient that decays at a definite rate; a pole at the origin has a transient that never decays at all.** That is a liability when the physics hands it to you unasked — drift, coasting, position loops being second order. And it is exactly the tool you want when you add it on purpose — steady-state error elimination. The skill is knowing which of the two you are looking at.

---

## Carrying forward

Real part negative, the transient decays. Real part zero, it is held forever. Real part positive, it grows. Those are the only three things the horizontal axis can say.

The next page moves to frequency, and after that the vertical axis finally gets an explanation.
