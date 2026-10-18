# Page 13 — The Nyquist Plot

*Listening script. Roughly eighteen minutes. Why minus one, the counting rule, all three margins read off the picture, and when Bode is not enough.*

---

This is page thirteen, and it closes the systems-and-stability block. One curve, one point, and a counting rule that survives the cases where Bode margins quietly lie.

---

## The same information, plotted differently

A Bode plot splits L of j omega into magnitude and phase, and draws them against frequency — two plots, frequency along the bottom of each.

A Nyquist plot keeps them together and draws **the complex number itself**. Each point on the curve is one frequency. Its distance from the origin is the magnitude of L. Its angle is the phase of L. **Frequency runs along the curve rather than along an axis.**

Nothing is added and nothing is lost. It is the same data.

What changes is that one specific point on the plane — **minus one** — becomes visible, and the whole of stability turns into a question about how the curve is arranged around it.

---

## Why minus one, and not some other number

The closed-loop transfer function of a unity feedback loop is T of s equals L of s, over one plus L of s.

So the closed-loop **poles** are the roots of **one plus L of s equals zero** — which is to say, the values of s where **L of s equals minus one**.

Now think about what that means physically. If that ever happens for s equals j omega — a real frequency, something you could actually excite — then at that frequency the loop returns **exactly the negative** of what went in. The feedback subtraction becomes reinforcement. And the loop sustains an oscillation **with no input at all**.

So minus one is not a convention someone chose. **It is the point where the denominator of the closed loop vanishes.** Everything on this page is about staying away from it.

---

## The criterion, and how to count

The Nyquist criterion is three letters:

**Z equals N plus P.**

**Z** is the number of closed-loop poles in the right half plane. You want **zero**.

**N** is the net number of **clockwise** encirclements of minus one by the Nyquist curve.

**P** is the number of *open-loop* poles in the right half plane. And you know this before you start — it is a property of the plant you already have.

**The common case:** the plant is open-loop stable, so P equals zero, and the rule collapses to: **the curve must not encircle minus one.** Simple enough to check by eye.

**The case that matters in robotics:** an inverted pendulum has P equals one — a genuinely unstable plant. Now you need **N equals minus one**: the curve must encircle minus one exactly once, **counter**-clockwise.

Read that again, because it inverts your instinct. **Not** encircling it is now the failure.

And a Bode plot cannot tell you this. Nyquist can. That is the main reason it is still taught.

---

## Reading the margins straight off the picture

All three margins are distances and angles on the same drawing.

**Gain margin.** Find where the curve crosses the negative real axis, at some distance d from the origin. The gain margin is one over d. Push the whole curve out by that factor and it lands on minus one.

**Phase margin.** Find where the curve crosses the **unit circle**. The phase margin is the angle from there back round to the negative real axis. Rotate the curve by that much and it lands on minus one.

**Vector margin.** The **shortest distance from the curve to minus one**, in any direction at all.

Formally: V m equals the minimum over omega of the magnitude of one plus L of j omega — which is also one over M s, the peak sensitivity.

---

## Vector margin is the honest one, and it is why this page exists

Here is the argument, and it is worth getting.

**Gain margin measures how far you are from minus one moving radially** — straight out from the origin.

**Phase margin measures how far you are moving tangentially** — around the circle.

A curve can be comfortable in *both* of those directions and still pass **within a hair of minus one diagonally**.

And diagonal is exactly what happens when a plant's gain and its phase are both a little wrong at once — which is exactly what real plants do. Nothing on a real robot is wrong in purely one direction.

**Aim for a vector margin of at least nought point five**, equivalently a peak sensitivity of two or less.

And the warning, stated plainly: **a loop with sixty degrees of phase margin, twelve decibels of gain margin, and a vector margin of nought point one five is a loop that will surprise you on the robot.** Both of the famous numbers look excellent. The loop is a hair from minus one.

---

## Interactive — sweep the gain, watch the curve approach minus one

There is a plant dropdown with three options, and a loop-gain slider. The readouts are: encirclements N, open-loop right-half-plane poles P, closed-loop right-half-plane poles Z, and the vector margin.

**Plant one — three real poles.** One over the product of s plus one, s plus two, s plus three. This is the simplest system that *can* be destabilised by gain alone. Turn K up and watch the curve inflate until it swallows minus one. P is zero, so the moment N becomes one, Z becomes one, and the loop is unstable.

**Plant two — joint plus integrator.** One over s times s plus one times s plus two. This is the Routh example from page eleven, now drawn geometrically — the one where the critical gain was exactly six. Watch the curve cross the negative real axis at minus one when K reaches that value.

**Plant three — an unstable plant.** One over s minus one times s plus three, with **P equals one**. This is the inverted-pendulum case. Here the curve must encircle minus one once counter-clockwise, and *low* gain is what fails. It is worth spending a minute on this one, because it is the case where every instinct built from the previous two plants is backwards.

The verdict is computed by **counting encirclements**, and then cross-checked against the closed-loop roots — the same trick as the Routh widget on page eleven. Two independent methods, always agreeing.

---

## When Bode is enough, and when it is not

Bode is fine for the overwhelmingly common case: an **open-loop stable plant whose magnitude crosses zero decibels exactly once**. That covers most joints most of the time, and it is easier to read.

Reach for Nyquist when any of these is true.

**The plant is open-loop unstable** — a balancing robot, a magnetic bearing. The counting rule is the only thing that works.

**The loop is conditionally stable** — stable at the design gain, but unstable if the gain is **reduced**. This happens when the magnitude crosses zero decibels more than once.

And that one is genuinely dangerous, so let me spell out why: **saturation reduces effective gain.** So a conditionally stable robot destabilises itself **by being pushed hard**. The harder you drive it, the more the actuator saturates, the lower the effective gain, and the closer it slides to the region where it oscillates. It is stable in gentle testing and unstable in the one situation you most needed it not to be.

**You care about the vector margin**, which has no natural reading on a Bode plot at all.

---

That is the end of the systems-and-stability block. You now have every tool for answering the question the whole section was built around: not "is it stable", but **how much would have to be wrong before it is not** — and the pages after this are about deliberately moving the poles to where you want them.
