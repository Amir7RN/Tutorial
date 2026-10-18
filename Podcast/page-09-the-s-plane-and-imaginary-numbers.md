# Page 9 — The s-Plane & Imaginary Numbers

*Listening script. Roughly twenty minutes. Includes the six-mode table, all six presets, and both interactives.*

---

This is page nine, and it is the one that explains the vertical axis.

The opening claim: **the s-plane has two axes because a motion can do two things at once — die away, and wiggle while doing it.** Horizontal is how fast it dies. Vertical is how fast it wiggles. A pole is one point saying "this system contains a motion that decays at *this* rate while turning at *that* one."

Everything on the page is earning those two sentences.

---

## What the imaginary part physically is — ninety seconds

Forget the word "imaginary", which is a bad name for a real thing. Ask instead what *multiplying* does to a number on a line.

Multiplying by **two** *stretches* it.

Multiplying by **minus one** *turns it a hundred and eighty degrees* — it points the other way.

So what turns it **ninety degrees**? Something you can apply *twice* to get a hundred-and-eighty-degree flip. Call it j. Then j times j equals minus one — which is the definition you were given in school, arrived at from the geometry instead of the other way round.

**So j is a quarter turn.** Real numbers scale; j rotates. A complex number is therefore "scale *and* turn". And e to the j omega t means "keep turning, at omega radians per second" — a point going round a circle. Its shadow on the real axis, as it goes round, traces a cosine.

That is the connection you need: **a rotation and an oscillation are the same object seen from two directions.** A sine is not fundamentally wavy. It is a circle viewed from the side.

And the physical punchline: **rotation is what two things trading back and forth looks like.** As the phasor turns, its horizontal component shrinks while its vertical one grows, then back. Two quantities, out of step by a quarter cycle, endlessly handing to each other while their sum stays put.

That is exactly what a spring and a mass do with energy — which is why **a system needs two stores before its pole can have an imaginary part.** One store has nobody to trade with, so there is nothing to rotate, so the pole lies flat on the real axis. It can only decay.

---

## "Rotating about what axis?" — the question everyone asks

Here is the answer nobody says out loud.

**Nothing in the machine is spinning. The rotation does not happen in physical space at all. It happens in *state space*.**

The mass on a spring slides back and forth along a straight line. There is no axis, no shaft, nothing turning. But plot the system's two stored quantities against each other — **position on one axis, velocity on the other** — and the point representing "the state of the system right now" goes round and round that plane. *That* is the rotation, and it is the only rotation there is.

Follow one cycle of a mass on a spring and watch the pair of numbers.

**Fully compressed:** position maximal, velocity zero. All the energy is in the spring.

**Passing through the middle:** position zero, velocity maximal. All the energy is in the mass.

**Fully stretched:** position maximal the other way, velocity zero again.

Two numbers, each maximal when the other is zero, taking turns. Which is precisely what the x and y coordinates of a point going round a circle do. **The quarter-cycle offset between position and velocity is the ninety degrees that j supplies.**

Energy sloshing between two stores *is* a rotation in the plane those two stores span. Engineers call that plane the **phase plane**, and the picture a **phase portrait** — both standard terms, and you will meet the phase portrait again on the nonlinear pages.

**So why can one store never rotate?** Because a rotation needs two coordinates. With a single store the state is a single number, and a single number lives on a line. A point on a line can move towards zero, away from zero, or sit still — it cannot go round anything, because there is nowhere to go round.

**Omega equals zero is not a special case of oscillation. It is the statement that the state space is one-dimensional.**

---

## Every motion a linear system can make — the complete list, and there are six

You might ask whether motions can only either continue forever or die while ringing. Close — there are exactly **six** possibilities, and they are just the three things the real part can be, crossed with the two things the imaginary part can be.

Each pole contributes one of these. The field's word for it is a **mode**, and any response is a sum of its modes.

**Sigma less than zero — left half plane — with omega equal to zero:** decays smoothly to nothing. The first-order response. Stable, no overshoot ever.

**Sigma less than zero, with omega non-zero:** rings, each swing smaller. A decaying oscillation — underdamped. Stable, but it overshoots.

**Sigma equals zero — on the axis — with omega equal to zero:** held, forever, at whatever value it has. An integrator. Never grows, never decays.

**Sigma equals zero, with omega non-zero:** rings forever at constant amplitude. A lossless resonator — a bell with no damping.

**Sigma greater than zero — right half plane — with omega equal to zero:** runs away smoothly. Unstable, no oscillation. An inverted pendulum falling over.

**Sigma greater than zero, with omega non-zero:** rings, each swing bigger. Unstable oscillation — the howl of a loop with too much gain.

**That table is the whole vocabulary of linear motion.** Nothing a linear system does falls outside it. The horizontal axis picks the row, the vertical axis picks the column, and a pole is just the coordinates of one cell.

---

## Interactive one — one pole, drawn three ways at once

Three panels, all showing the same number.

**Left:** where the pole is, on the s-plane.

**Middle:** the actual motion, e to the s t, in the complex plane — a point at radius e to the sigma t, and angle omega t. You watch it spiral.

**Right:** the real part of that motion, which is the signal you would measure, with the envelope drawn dashed above and below.

There are two sliders — sigma, the real part, and omega, the imaginary part — plus play, pause and restart. The readouts give you the decay rate, tau, the ring rate in radians per second, how long one wobble takes, and how many wobbles happen before it dies.

And there are **six preset buttons**, one for each cell of that table. Press them in order and you will have seen everything linear systems can do.

**Decays, no ring.** Nothing rotates, the spiral collapses onto a line, and the signal is a plain exponential decay. **That is a first-order system**, and seeing the spiral flatten into a line is the clearest way to understand why.

**Held forever.** Sigma and omega both zero. The integrator.

**Grows, no ring.** The spiral winds outward along a line and the signal grows. Unstable, and now you can see why the right half plane is shaded red.

**Rings and decays.** Both parts non-zero. It wobbles while its envelope shrinks. Two stores trading energy while friction eats it. Every underdamped joint you have ever tuned is this picture.

**Rings forever.** Sigma zero, omega non-zero. The radius never shrinks, so the circle closes on itself and the ringing never stops. The pole is on the imaginary axis, exactly on the boundary.

**Rings and grows.** The spiral winds outward while turning. Every wobble bigger than the last.

---

## So the two axes are two physical rates, and that is all

**Horizontal — the real part sigma: the decay rate**, in one over seconds. How fast the motion dies. Left means it dies, which is stable. Right means it grows, which is unstable. Further left means it decays faster. This is the pole you already met on page six.

**Vertical — the imaginary part omega: the ring rate**, in radians per second. How fast it wobbles on the way. A first-order system has nothing to wobble with, so omega is zero and its pole sits flat on the horizontal axis.

And one clarification that resolves an apparent contradiction: **"we don't want the response to die, we want it to settle" — these are the same thing.** What decays is not the output, it is the *transient*: the difference between where you are and where you were told to be. Killing that difference fast *is* settling fast. The output does not die; the error does.

---

## Interactive two — the second store, and where overshoot physically comes from

Two systems get the same step command at time zero.

**The left one has a single store** — the moving mass — and the thing you are watching, its speed, *is* that store.

**The right one has two:** the mass holds speed, and the spring holds position.

Watch the energy. On the left there is one bar and it fills monotonically. On the right, energy **sloshes** between two bars.

And the moment that matters is marked: **the output reaches its target while the mass is still moving.** At that instant the spring force is exactly right, the net force is zero — and yet the system is not at rest, because there is energy parked somewhere that is not the output variable. That parked kinetic energy is *momentum*, and it carries the output straight past the target. Then the spring reverses and shoves it back. That is ringing.

There is a **damping slider** for the right-hand system, a **time scrubber** so you can park the cursor anywhere in the run, a **run both** button, and a button marked **jump to the moment it hits target** — which takes you straight to the instant that makes the point. At a damping ratio of nought point two five, that moment shows about thirty-nine percent of the peak energy still in the mass, and one hundred percent of the *remaining* energy in the mass, because the spring is exactly at its rest value.

There are four panels: the two outputs against time, the energy against time showing spring and mass trading out of phase with the total decaying, the instantaneous energy bars at the cursor, and — the important one — **the phase portrait**.

**The phase portrait is position across and velocity up, and it is the rotation the imaginary axis is talking about.** The state spirals inward: turning because energy is being handed between the two stores, shrinking because the damper is eating it.

Set the damping above one and the spiral stops being a spiral: the state slides straight in without ever going round, which is exactly what "the poles left the imaginary axis" looks like in the machine.

And **the one-store system cannot be drawn there at all**, because its state is a single number. It would be a point moving along a line, with no second direction to turn into.

One more thing to try: turn the damping ratio up past one. The poles collide on the real axis and split apart along it. The imaginary parts vanish, the sloshing stops, and the overshoot goes to zero. The system still has two stores, but the damper is now eating the surplus faster than the spring can hand it back. **That is what "critically damped" means, and it is what most joint tuning is trying to buy.**

---

## The argument, stated once, now that you have seen it

**To overshoot, a system must arrive at its destination still carrying something that pushes it past.** Ask what that something could be in a first-order system.

The joint reaches its final speed at the exact moment friction b omega has grown to equal the applied torque tau. At that instant the net torque is **precisely zero** — nothing is left pushing. And the only quantity the system stores *is* the one you are watching. There is no second reservoir holding a surplus.

One store means the output **is** the state. Reaching the target means the state is at its final value. Nothing is left over. So it arrives and stops — for any input, at any gain.

And **"energy in a form that is not the output variable" — that is the whole trick, and now it is concrete.** You are measuring position; the surplus is hiding in velocity. Position is on target and the system is not at rest. Give the system somewhere to hide energy and it can overshoot; take that hiding place away and it cannot.

---

## And this is what a controller is actually for

You now have a map on which every behaviour you care about is a **location**.

**Too slow to respond?** The pole is too close to the origin. **Move it left.**

**Rings and wobbles?** The poles have too much imaginary part relative to real. **Push them down towards the real axis.**

**Never quite reaches the target?** You need a pole **at** the origin, one whose state never decays. **Add an integrator.**

**Unstable?** A pole is in the right half plane. **Drag it back across.**

**Feedback does not change the plant. It moves the plant's poles.** That single sentence is what the controller-design half of this tutor is about, and it is only meaningful because you can now read a pole's position as a pair of physical rates. Root locus, lead compensators, pole placement and LQR are four different ways of answering the question "where do I want these dots, and what gain puts them there?"

---

## Carrying forward

Real part is the decay rate. Imaginary part is the ring rate.

One store means no imaginary part, which means no overshoot, no ringing, at most ninety degrees of lag, and infinite gain margin.

Add the second store and every one of those five statements breaks — which is the next page, and it is where every robot joint you will ever tune lives.
