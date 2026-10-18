# Page 12 — Bode Plots, Gain & Phase Margin

*Listening script. Roughly eighteen minutes. Both margins, the phase-margin-to-damping table, and all three experiments.*

---

This is page twelve. Not "is it stable", but **"how much would have to be wrong before it is not"**. The two numbers every real loop is signed off on.

---

## What a Bode plot is, and why the axes are the shape they are

Feed a linear system a sine at frequency omega and, once the transients die, the output is **the same sine** — different amplitude, shifted in time. Only two numbers change. So the entire behaviour at that frequency is one complex number: G of j omega, written as its magnitude times e to the j times its angle.

A Bode plot is those two numbers versus frequency. Both axes are logarithmic, and that is not cosmetic. Three reasons.

**Cascaded blocks multiply.** Controller times plant times sensor. Take the logarithm and multiplication becomes **addition** — so on a decibel plot you can literally add curves with a pencil.

**Phases add directly.** No logarithm needed; that is just how complex multiplication works.

**Log frequency, because a robot spans decades.** A twenty kilohertz current loop and a two hertz gait live on the same picture. On a linear axis one of them would be invisible.

### The three building blocks, which is all you need to sketch one

**A pole at omega p.** Flat, then minus twenty decibels per decade after omega p. Phase slides from zero to minus ninety degrees, passing minus forty-five *at* omega p.

**A zero at omega z.** The mirror image: plus twenty decibels per decade, and plus ninety degrees.

**An integrator — a pole at the origin.** Minus twenty decibels per decade everywhere, and a flat minus ninety degrees at every frequency.

That is genuinely all of it. Every Bode plot you will ever sketch is those three pieces added together.

---

## Where instability comes from, in one sentence

**Feedback subtracts.** If the loop delays a signal by exactly half a cycle — **minus one hundred and eighty degrees** — the subtraction turns into an *addition*. And if the loop gain is still greater than or equal to one at that frequency, the signal comes back bigger every trip.

That is oscillation. Everything else on this page is measuring how far you are from that condition.

---

## The two margins

**Gain margin.**

Find the frequency where the phase hits minus one hundred and eighty degrees. Call it omega p c, the phase crossover. The gain there is below one — and the gain margin is **how far below, in decibels**.

Formally: GM equals minus twenty log of the magnitude of L at omega p c, where the angle of L at omega p c is minus one hundred and eighty.

It answers the question: *how much stronger could my plant be than I think, before this oscillates?*

**Phase margin.**

Find the frequency where the gain passes through one, which is zero decibels. Call it omega g c, the gain crossover. The phase there is above minus one hundred and eighty — and the phase margin is **how far above**.

Formally: PM equals one hundred and eighty degrees plus the angle of L at omega g c, where the magnitude of L at omega g c equals one.

It answers: *how much more delay could there be before this oscillates?*

**Targets on real hardware: phase margin forty-five to sixty degrees, gain margin six to twelve decibels.**

Below thirty degrees of phase margin, a robot rings visibly and any payload change is a gamble. Above seventy degrees, you are almost certainly leaving bandwidth on the table.

---

## Phase margin *is* damping — the bridge back to second order

This is the part that makes phase margin stop being an abstract safety number.

For the standard second-order loop, phase margin maps **exactly** onto zeta, and therefore onto overshoot. Here is the table.

Thirty degrees of phase margin is a zeta of about nought point three zero, and thirty-seven percent overshoot.

Forty-five degrees is a zeta of nought point four three, and twenty-two percent overshoot.

Fifty-five degrees is nought point five five, and thirteen percent.

Sixty-five degrees is nought point seven one, and four point three percent.

Seventy-six degrees is a zeta of one point zero, and zero overshoot.

Hence the rule of thumb: **phase margin is approximately one hundred times zeta** — good to within a few degrees, up to a zeta of about nought point seven.

And hence the practical translation, which is the sentence to keep: **"my loop has forty-five degrees of phase margin" and "my robot overshoots about twenty percent" are the same sentence.** One is said in the frequency domain and one in the time domain, and they are the same fact.

---

## Interactive — build a loop and watch the margins move

The plant is a real joint: one over J s squared plus b s. Note the **pole at the origin**, which is why the phase starts at minus ninety degrees rather than zero — that is the integrator from page seven showing up in the frequency domain.

Four sliders: loop gain K p, derivative action K d, a mechanical resonance in hertz, and loop delay in milliseconds.

Four readouts: phase margin, gain margin, crossover frequency, and the overshoot those margins imply.

Three plots: Bode magnitude, Bode phase, and the closed-loop step response — so you can watch a frequency-domain number and a time-domain shape move together.

---

## Three experiments worth doing in that widget

**One. Raise K p with the resonance switched off.**

Crossover moves right. Phase margin barely suffers. Gain margin stays infinite.

That is the second-order result from two pages ago, seen from the frequency side: **you cannot destabilise it.** Two poles supply at most one hundred and eighty degrees and only asymptotically, so the magnitude has long since fallen below one by the time the phase gets there.

**Two. Turn the resonance on at fifteen hertz, then raise K p.**

The moment crossover approaches the resonance, **gain margin collapses**.

*This is the SEA bandwidth ceiling, derived rather than asserted.* The reason you cannot just turn the gain up on a series-elastic actuator is sitting right there as a peak in the magnitude plot poking above the zero decibel line.

**Three. Set the delay to five milliseconds and watch only the phase plot.**

The magnitude does not move **at all** — a delay has unit gain at every frequency, it attenuates nothing.

But the phase is dragged down by three hundred and sixty times f times T d degrees, and the phase margin drains away.

Page one said delay is pure loss. This is the picture of it: you pay in phase, you get nothing back, and there is no gain adjustment that recovers it.
