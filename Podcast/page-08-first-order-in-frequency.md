# Page 8 — First Order in Frequency

*Listening script. Roughly twenty minutes. The jω substitution, the shaker, decibels, the roll-off, and the quarter-cycle stability theorem.*

---

This is page eight, and it changes the experiment. Up to now you have been *stepping* the plant — push it once and watch it settle. Now you are going to *shake* it.

The framing sentence: **a frequency response is one experiment repeated at many speeds.**

Wiggle the input back and forth at some rate. Measure how big the output wiggle is, and how far behind it arrives. Two numbers per frequency: **magnitude** and **phase**. Plot them against frequency and you have a Bode plot. Nothing more abstract than that is happening.

---

## Why s becomes j omega — nothing is being thrown away

This is the question that bothers people, so let me do it properly.

The variable s is not a number you pick. It is a placeholder for the *kind of signal* you are feeding in. Write it out:

e to the s t equals e to the quantity sigma plus j omega, times t. Which factorises into e to the sigma t, times the bracket cosine omega t plus j sine omega t.

Two factors, two meanings.

**e to the sigma t** — the first factor, set by the **real part sigma** — is an **envelope**. The signal growing or shrinking.

**The bracket** — cosine omega t plus j sine omega t, set by the **imaginary part omega** — is the **wiggle**. How fast it goes back and forth.

So setting sigma equal to zero is **not deleting anything. It is choosing the test signal.**

Sigma equals zero means an envelope of e to the zero, which is one: a sine that neither grows nor dies, going forever at constant amplitude. And that is exactly the signal you want for this experiment, because "frequency response" means *steady-state* response. You shake the thing until every transient has drained away and only the forced wiggle is left, and *then* you measure. A test sine that was itself dying would contaminate the measurement.

So **s equals j omega** is the sentence: "drive it with a pure, everlasting sine at omega radians per second." And G of j omega is the answer.

### One distinction worth nailing down, because it trips people

The **pole** is at s equals minus one over tau, on the real axis. That is where the system's *own, unforced* motion lives, and it describes how a disturbance drains away.

The **test point**, s equals j omega, is on the imaginary axis. That is where *you* are poking it.

They are different points on the same map. A first-order system has no pole off the real axis, but you can still shake it at any frequency you like.

And the formulas, for the record: G of j omega equals K over one plus j omega tau. The magnitude is K over the square root of one plus omega tau squared. And the phase is minus arctangent of omega tau.

---

## Interactive — the shaker

This is the widget the page is built around, and it has four panels.

**The top-left panel is the actual experiment**: your drive sine in grey, and the system's answer in blue, after transients have died. There is a marker showing how much later the output peak arrives, labelled in degrees.

Watch **two things shrink as you speed up**: the answer gets smaller, and it arrives later.

**The top-right panel** shows the pole in blue and the test point in amber, so you can see the distinction I just made, drawn.

**The bottom two panels** are the Bode magnitude and Bode phase, with a marker showing where you currently are. And this is the sentence to keep: **the Bode plot is not a new object; it is the logbook of this one experiment.**

The readouts give you: the amplitude ratio out over in, that ratio in decibels, the phase lag in degrees, the lag as a fraction of a cycle, and the lag in milliseconds.

Three regions to visit deliberately.

**Below the corner.** The store has plenty of time to keep up, so the output tracks the input nearly full size and nearly in step. This is the region where the plant does what you ask.

**At the corner.** Omega equals one over tau. The magnitude is K over root two, which is nought point seven zero seven, or minus three point zero one decibels. The phase is exactly minus forty-five degrees. Half the power through, half a quarter-cycle of lag. **This one frequency is the pole, the time constant and the bandwidth, all at once.**

**Above the corner.** You are asking the store to change faster than it can, so most of your drive never reaches the output, and what does arrive is late. Commands up here are wasted effort.

---

## Decibels, since it is only a unit

A decibel is a **logarithmic way of writing a ratio**, invented so that cascaded blocks add instead of multiply.

For an amplitude ratio: decibels equals twenty times the base-ten logarithm of the ratio of output to input.

The table worth knowing: a ratio of one is zero decibels. Nought point seven zero seven is **minus three**. Nought point five is minus six. Nought point one is minus twenty. Nought point zero one is minus forty.

**Why minus three decibels is the one that got a name.** Power goes as amplitude squared. So an amplitude ratio of one over root two — nought point seven zero seven — is a **power** ratio of exactly one half. And in power decibels, ten times log of nought point five is minus three point zero one.

"Half the power gets through" means: of the energy you are pumping into the input at this frequency, half is coming out the other end. The rest is not appearing at the output because the store will not move that fast.

It is a conventional line drawn on a smooth curve — but it is a sensible one, and everyone draws it in the same place.

**Does minus three decibels define bandwidth for every system, or just first order?** The *definition* — the frequency where the magnitude has fallen three decibels below its low-frequency value — is completely general, and is what a datasheet means by bandwidth for any plant, filter or closed loop.

What is *not* general is the formula. **Omega bandwidth equals one over tau holds only for a single pole.** A second-order system's minus-three-decibel point depends on both omega n and zeta, and a resonant one can rise *above* zero decibels before it falls — which is the next page's problem.

---

## Minus twenty decibels per decade, and minus ninety degrees, physically

**The roll-off.** Past the corner, a factor of ten in frequency costs a factor of ten in amplitude. That is what minus twenty decibels per decade means.

Physically: the store cannot keep up. Shake a coil's current twice as fast and the inductance opposes the change twice as hard, so half as much current gets through. The store is a "can't-change-that-fast" wall, and the harder you push, the more it blocks — in exact proportion.

Every single-store low-pass does this, at the same minus twenty decibels per decade, for the same reason: an RC filter, an RL winding, a mass with damping, a thermal mass. Same slope, every time.

**The phase.** Push the joint back and forth *slowly* with a sinusoidal torque, and the speed follows you almost exactly. At low speed the friction term b omega dominates — and friction has no memory, it depends only on the velocity right now, not on its history — so there is nothing to lag with, and the output is in step. Zero degrees.

Now push *fast*. The friction term never gets a chance to matter. The inertia J omega dot dominates, and speed becomes the **integral** of your push. And the integral of a sine peaks a **quarter cycle** after the sine does. That is ninety degrees, and it cannot get worse, because there is only one integration to do.

**One store equals one integration equals at most a quarter cycle of lag.**

And yes, that depends on what the controller is doing. What I just described is the bare plant, which is what you feel under torque control or with the drive disabled. Close a stiff position or impedance loop around it, and you are no longer feeling J and b — you are feeling the *rendered* impedance the controller is synthesising, with its own corner and its own phase. That is the entire point of the impedance-control pages: the controller gets to choose the dynamics the world touches.

---

## The quarter cycle you are short by

Now the stability theorem, and it follows directly from that ninety-degree ceiling.

To make something oscillate with feedback you have to push it in **exactly the wrong phase**. Your correction must arrive as the error is already heading back the other way, so that it *adds* to the error instead of opposing it.

That is a **half** cycle of lag: one hundred and eighty degrees. At that point the minus sign in negative feedback has been cancelled by the delay, and the loop is positively feeding itself.

**One energy store can only ever supply ninety degrees. You are a quarter cycle short of the half cycle that would flip the feedback, and no amount of gain manufactures phase** — gain scales the signal, it does not move it in time.

Therefore: a first-order plant with proportional feedback is stable at **every** gain. Infinite gain margin, provably. The closed-loop pole sits at minus one plus K times K p, over tau, and it only ever moves further left. Faster, with less steady-state error, and never unstable.

Enjoy it. It is the only plant in this tutor that behaves.

---

## Interactive — try to destabilise it, then cheat with delay

Turn the gain up as far as it goes. The phase curve never reaches minus one hundred and eighty degrees, so there is nothing to cross and no critical gain to find. The readout for "gain that destabilises" says **none**.

**Now add transport delay.**

Delay has unit magnitude and unbounded phase lag. It is pure phase loss, exactly as the real-time page said. So it will happily sell you the missing quarter cycle, and the guarantee evaporates.

The phase plot shows two curves once the delay is non-zero: the plant alone, which flattens at minus ninety, and the plant plus delay, which keeps falling and crosses minus one hundred and eighty. The phase margin readout drops accordingly.

And that is the honest statement of the theorem: *a first-order plant cannot be destabilised by proportional feedback* **assumes there is no delay and no second store.** On a real robot, both of those assumptions are things you have to earn.

---

## Carrying forward

Bandwidth equals one over tau equals the magnitude of the pole — the third hat on the same number.

Beyond it, minus twenty decibels per decade, and a phase heading for minus ninety degrees and stopping.

That stop is a stability guarantee, and it is bought by having exactly one place to put energy.

Next page: what the imaginary axis is, and what a second place to put energy does to all of this.
