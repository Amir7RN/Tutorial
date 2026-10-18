# Page 11 — Stability & How to Check It

*Listening script. Roughly eighteen minutes. The full pole taxonomy, all four methods, and the worked Routh example.*

---

This is page eleven. What "stable" is a statement about, why marginal is its own category, and three ways to decide without guessing.

---

## The definition, and it is narrower than the word suggests

The formal definition is **BIBO stability**: every *bounded* input produces a *bounded* output. Bounded in, bounded out.

For a linear time-invariant system, that is equivalent to one geometric statement, and it is worth saying slowly:

**Every pole has a strictly negative real part.**

"Strictly" is load-bearing. A pole exactly on the imaginary axis is **not** a mild case of stable. It is a different category, with different failure behaviour — and it is extremely common in robotics.

Here is the full taxonomy, with where you meet each one.

**A pole at minus a, where a is positive.** Time response: e to the minus a t. It decays. Verdict: **stable**. Where you meet it: any damped mode.

**A complex pair at minus sigma plus or minus j omega.** Time response: e to the minus sigma t, times cosine omega t. It rings down. Verdict: **stable**. Where you meet it: a joint under PD control.

**A pole at exactly zero.** Time response: a constant. It never returns. Verdict: **marginal**. Where you meet it: a free joint — torque in, and the position drifts.

**A pair at plus and minus j omega, on the axis.** Time response: cosine omega t. It rings forever. Verdict: **marginal**. Where you meet it: an undamped SEA spring, or a frictionless pendulum.

**A pole at plus a.** Time response: e to the plus a t. It grows. Verdict: **unstable**. Where you meet it: an inverted pendulum — which is to say, every biped.

**A repeated pole at zero.** Time response: t. It ramps away. Verdict: **unstable**. Where you meet it: a double integrator — J theta double dot equals tau, with no friction at all.

---

## Marginal is not "almost stable" — it is "nothing decides"

This deserves its own moment.

A marginal system neither recovers from a disturbance nor diverges from it. It **keeps whatever you gave it, forever**.

And in practice that means the tiniest unmodelled term picks the outcome. A whisker of extra friction and it decays. A whisker of negative friction and it grows. **You have handed the decision to noise.**

It is also the normal state of robot hardware. A joint with negligible friction *is* a double integrator. A good SEA spring *is* nearly undamped.

Which reframes the whole enterprise: **feedback is not there to improve an already-stable machine. It is there to move those poles off the axis.** That is the entire job.

---

## Interactive one — place the poles yourself and watch the taxonomy

One complex pair, with two sliders: the real part and the imaginary part.

Slide the real part through zero and you have walked the whole table above in a single gesture — decaying, then ringing forever, then growing.

The readouts give you the verdict, the damping ratio zeta, the natural frequency omega n, and — the useful one — the **halving or doubling time**. That last one turns an abstract pole location into a number you can feel: how many milliseconds until the disturbance is half gone, or in the unstable case, twice as big.

---

## Four ways to check, in the order you would reach for them

**One. Compute the roots.**

If you have the closed-loop polynomial, factor it. Exact, trivial on a computer — and **useless for design**, because it tells you the answer for *one* set of gains and nothing about the neighbouring ones. You learn that this gain works. You learn nothing about how much room you have.

**Two. Routh–Hurwitz.**

Decide the same question *without* computing a single root, using only the coefficients.

Its real value today is not speed — computers factor polynomials instantly. Its value is that the entries stay **symbolic in your gain**, so you can solve for the exact gain at which stability is lost, instead of hunting for it by sweeping.

**Three. Frequency margins — Bode and Nyquist.**

The only method that works on a plant you **measured** rather than modelled. And the only one that tells you **how much room you have left**. That is the next two pages.

**Four. Lyapunov.**

Works when the system is nonlinear and has no poles at all. You find an energy-like function that can only decrease. Covered on the nonlinear pages.

---

## Routh–Hurwitz, worked

The mechanics: write the closed-loop characteristic polynomial, list the coefficients in two alternating rows, then cross-multiply downwards.

**The number of sign changes in the first column is the number of poles in the right half plane.** Zero sign changes means stable — and you knew it without factoring anything.

Now the classic worked example, which is also the standard cautionary tale about proportional gain.

Take a loop L of s equals K over s times s plus one times s plus two. The closed-loop characteristic polynomial is s cubed, plus three s squared, plus two s, plus K.

The first column of the Routh array comes out as: one, three, six minus K over three, and K.

For every entry to stay positive you need **K between zero and six**.

And at exactly K equals six, a whole row goes to zero — which is the signature of a pole pair sitting *on* the imaginary axis. The loop oscillates at the square root of two radians per second, forever.

That number, six, is a design fact you obtained **algebraically**. No simulation. No sweep.

And notice the *shape* of the result: **a third-order loop has a maximum usable gain.** The first- and second-order plants of the last few pages did not. This is the first time in the tutor that turning the knob up can actually hurt you — and it took three poles to get there.

---

## Interactive two — build a cubic and let Routh judge it

Three sliders for the coefficients of s cubed plus a-two s squared plus a-one s plus a-zero.

The Routh column and the actual roots are computed **independently**, and displayed side by side — right-half-plane poles according to Routh, and right-half-plane poles according to factoring. They always agree, which is the point of showing both.

There is also a classification readout, and the Routh array itself is printed underneath so you can watch the first column change sign as you drag.

---

## Necessary, not sufficient — and this is where beginners stop too early

This is the closing warning, and it is the reason the next two pages exist.

"Stable" only promises the response is **bounded**. It says nothing about whether the robot settles in fifty milliseconds or fifty seconds. Nothing about whether it overshoots into the person standing next to it. Nothing about whether it is still stable when the payload changes.

**A controller sitting one decimal place from the stability boundary is stable and worthless.**

That is why the rest of this section is about **margins** — not "is it stable" but **"how much would have to be wrong before it is not".**
