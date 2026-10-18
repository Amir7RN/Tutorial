# Page 6 — The Time Constant & the Pole

*Listening script. Roughly twenty minutes. Includes the full terminology table and both interactives.*

---

This is page six, and it has one thesis, stated at the top:

**Tau, the pole, and the bandwidth are the same number wearing three hats.**

Tau equals fifty milliseconds. Pole at minus twenty per second. Bandwidth three point two hertz. Those are three ways of saying one fact about one piece of hardware. This page earns that sentence, and then turns it into a calculator.

---

## The cup with a hole in it

Hold this picture, because everything follows from it.

A cup with a small hole in the bottom, and a tap above it. That is the entire object. Two things are worth noticing.

**The tap pours at a constant rate.** It does not care how full the cup is.

**The hole drains at a rate set by the level.** High water, more pressure, drains fast. Low water, drains slowly.

That second sentence is the whole of first-order dynamics. Because the leak grows with the level, the level does not rise in a straight line — it rises fast, then eases off, approaching the balance point more and more gently.

**That curve *is* the exponential.** e to the minus t over tau is not an abstract function that happens to fit. It is literally the shape of a thing changing at a rate proportional to how far it still has to go.

---

## Interactive one — pour, then stop pouring

The widget animates the cup, and there is one instruction: **watch the two rate bars on the left, not the level.**

There are three bars: the level, the fill rate, and the leak rate. The fill bar is constant. The leak bar grows as the level grows.

**Settled does not mean stopped. It means the two rate bars have become the same height.** Fill equals leak. Net flow zero. The tug-of-war balanced. That is the definition of steady state, and it is why nothing ever "arrives" — it just stops changing. When they match, a label appears saying SETTLED, net flow zero.

Then you press **stop pouring**. The fill bar goes to zero and the cup drains — fast at first, then slower, for exactly the same reason in reverse.

The right-hand plot shows the level against time, with dotted lines at sixty-three point two percent and thirty-six point eight percent, and vertical markers at one tau, two tau, three tau and so on. There is an elapsed readout that shows the time both in seconds and in multiples of tau.

---

## Where sixty-three point two percent comes from — computed, not asserted

Solve the equation with the tap turned on at time zero:

y of t equals K times the quantity one minus e to the minus t over tau c.

Now put t equals tau c into it:

One minus e to the minus one, equals one minus nought point three six seven nine, equals **nought point six three two**.

That is the entire origin of the number. It is e to the minus one and nothing else.

And note carefully: **tau is not "the time to settle."** An exponential never finishes. Tau is the time to get sixty-three point two percent of the way — which is a statement about *how fast the approach happens*, not about arriving.

Now the other way to read tau, which is the one worth carrying.

At the instant you turn the tap on, the cup is empty, so the leak is zero, so the level is rising at its fastest. **If it kept rising at that initial rate, it would reach the final value in exactly tau c seconds.**

It does not, because the leak grows as it climbs — so it only gets sixty-three point two percent of the way. The dashed tangent line in the plot is that "if the leak never grew" line, and it crosses the final value at t equals tau every single time, for any tau and any K.

The landmarks you will read off an oscilloscope for the rest of your life: one tau gives sixty-three point two percent. Two tau, eighty-six point five. Three tau, ninety-five point zero. Four tau, ninety-eight point two. Five tau, ninety-nine point three. "Settled" conventionally means four tau, the plus-or-minus two percent band.

---

## The pole — a duration, flipped into a rate

You have a duration: tau equals half a second. "This cup mostly-drains in half a second."

Flip it: one over tau equals two per second. "This cup mostly-drains twice a second."

That is the pole's size. It is the same information in the other unit — like saying a job takes half an hour versus you do two an hour.

Formally: **p equals minus one over tau c, which equals minus b over J**, in units of one over seconds.

Leak divided by store. Bigger number means faster draining means shorter tau. The minus sign says draining rather than growing.

**An e-fold, plainly.** One e-fold is one division by e, which is about two point seven one eight — a drop to thirty-six point eight percent. It is exactly the idea of a half-life, using e instead of two, because e is what falls out of the differential equation. If half-lives are more familiar to you: this system's half-life is nought point six nine three tau.

And the pole's magnitude is how many e-folds the transient loses per second.

A winding with tau of half a millisecond loses two thousand e-folds per second — after one millisecond a disturbance is down to fourteen percent of what it was. A joint with tau of half a second loses two per second, so half a second after a bump it is still thirty-seven percent wrong.

---

## What this is called in textbooks — and where my word "forgetting" came from

Now an honest interruption, because this matters for reading anyone else's work.

**Straight answer: "forgetting rate" is not standard control terminology. I coined it as a gloss, and if it is not helping, drop it.**

Here is the vocabulary the field actually uses for the identical quantity.

**Decay rate** — also called exponential decay rate, or rate of decay. Symbol: the magnitude of sigma, the magnitude of the real part of p, which equals one over tau. **This is the standard name for the number.** Units, one over seconds. You would say: "the transient decays at twenty per second."

**Time constant**, tau. Its reciprocal, in seconds. The most common way to quote it.

**Transient response** — also called the natural response, or the zero-input response. The part of the output that dies away and leaves nothing behind. What "is forgotten" is precisely this.

**Mode**. e to the p t. One pole's contribution. A system's response is a sum of its modes. "The slow mode dominates" is ordinary shop talk.

**Settling time**, T s, approximately four tau. How long until the transient is small enough to ignore, the plus-or-minus two percent band.

**Disturbance rejection**. The property of removing the effect of an uncommanded input. "Forgetting the rock" is this, in the proper words.

And three related terms that are real, so you do not confuse them:

**Memoryless** is a genuine, standard term for a component whose output depends only on the input *right now* — a resistor, ideal viscous friction, a gain. It has no state, so there is nothing for it to be late with. That term is used correctly on page eight, where friction is said to have no memory.

**Fading memory** is a real term in systems theory for exactly the property being described here: the influence of the distant past decays to nothing. Closest respectable relative of my coinage.

**Forgetting factor**, lambda, is a real and common term — but it belongs to *recursive least squares* and adaptive identification, where it weights old *data* less than new data. It is not a property of a plant's poles. Do not mix them up.

**So what should you actually say?** "The pole at minus twenty gives a fifty millisecond time constant." Or "the transient decays at twenty per second." Or "it settles in about two hundred milliseconds." Those are the three sentences people use, and they are all the same measurement.

Keep the metaphor only for the one thing it is good at: making it obvious **why a decaying transient is what you want.** Your foot hits a rock. The bump puts something into the joint's store that you never commanded. "The transient decays" and "the joint gets back to the speed you asked for" are the same event described twice. Fast decay equals fast recovery equals fast tracking. The price is that it also reacts to every twitch, including sensor noise — and that trade is the whole reason a controller has knobs.

---

## Interactive two — kick it, and watch the transient decay

Two systems, with different time constants, called A and B. You press **kick both**, which injects the same disturbance into each — one shove, then hands off. Nothing drives them after that, so what you are watching is the pure **zero-input response**: the transient, and nothing else.

The left plot is linear, with horizontal lines marked at each e-fold: thirty-seven percent is one e-fold, thirteen point five percent is two, five percent is three, one point eight percent is four.

The right plot is the same two traces on a **logarithmic** y-axis, and it is the point of the widget: **on a log axis, exponential decay is a straight line, and the pole is its slope.** A steeper line is a bigger pole, a shorter tau, a system whose transient dies faster. The pole is not an abstraction of the decay — it is the decay's gradient, in one over seconds.

There is a live readout under the sliders. For each system it gives you tau, the pole, how many e-folds it decays per second, how many e-folds have elapsed since the kick, and what percentage of the transient is still there.

And there is an experiment worth doing: set A to fifty milliseconds and B to three thousand milliseconds, then kick. A is back to baseline before B has visibly moved. Those are the same two systems as the current loop and the joint loop, and the gap you are looking at is the reason they cannot share a controller.

---

## One number, three hats

The next widget lets you drag tau and watch everything move together. The pole slides along the real axis, and the response changes speed. They are the same fact drawn twice. A pole at minus twenty per second and a fifty millisecond time constant are one sentence in two languages, and the bandwidth chip is the third translation — page eight earns that one.

The readouts are: the pole, the decay rate in e-folds per second, the sixty-three percent time, the settled time at four tau, and the bandwidth in hertz. All five move together, because they are all the same number.

---

## The sign, since it is the one thing people get backwards

The solution is y of t equals K times one minus e to the p t, where p equals minus one over tau c.

**p negative.** e to the p t decays. The leak wins, the disturbance drains away. **Stable.** This is what a real damper or resistor always does.

**p positive.** e to the p t grows. Something is *feeding* the store instead of draining it. **Unstable.** Physically that is negative friction, which sounds exotic until you meet an inverted pendulum, where gravity does exactly that.

**p equals zero.** No leak at all. Whatever goes in stays in, forever. **Marginal.** A frictionless joint: push it once and it coasts for the rest of time. This is an **integrator**.

**Further left equals decays faster.** The real part *is* the decay rate. Nothing is encoded or hidden.

And that third case is important enough to have the next page to itself. It is the exact opposite of the winding: a store with no drain at all, whose transient never decays. That sounds like a defect, and it is precisely the property that kills steady-state error, that makes position control second order even when the mechanism has one moving part, and that makes an integrator the one thing you cannot leave out of a real controller.

---

## Interactive three — why the current loop runs at twenty kilohertz and the joint loop cannot

This is the question that started the whole cascade.

Two columns. On the left, a winding with sliders for inductance L and resistance R, giving an electrical time constant of L over R. On the right, a joint with sliders for inertia J and damping b, giving a mechanical time constant of J over b.

Both are first-order systems. Both obey tau equals store divided by drain. They differ by three orders of magnitude, and that gap — not a convention, not a CPU limit — is what forces a fast inner loop inside a slow outer one.

Loop rate is taken as roughly **fifteen times the bandwidth**, which is the rule from page one: sampling, zero-order hold and computation each cost you phase, so you buy roughly your sample rate divided by fifteen of usable control authority.

The readouts give you the electrical tau, the mechanical tau, the achievable loop rate for each, and the separation factor between them. And the text underneath spells it out with your numbers: the winding's transient decays at some thousands of e-folds per second, the joint's at a couple per second. The winding is able to obey a new current command every fraction of a millisecond, so running its loop near twenty kilohertz means almost every cycle does useful work. The joint cannot respond to anything faster than a few hertz no matter what you send it — so a loop faster than roughly a hundred hertz spends its cycles re-deciding a command the mechanics have not begun to act on, while amplifying encoder noise.

**That gap is the whole reason for a cascade:** a fast inner loop that makes torque exact, wrapped in a slow outer loop that decides what the torque should be.

The left plot shows both step responses on a logarithmic time axis, so you can see three decades of separation in one picture. The right plot is a bar chart, on a log scale, comparing the joint bandwidth, the joint loop rate, the current bandwidth and the current loop rate, with a dashed line drawn at twenty kilohertz.

---

## What it means for the robot in front of you

**The current loop is first order**, L over R, which is why it can be closed at twenty kilohertz with a plain PI and never argued about. It is the well-behaved layer everything else stands on.

**A velocity loop on a rigid joint is first order**, J over b. Speed control is genuinely easy. Position control is not, because integrating velocity adds a pole at the origin — and that is a second-order system with a marginal pole in it.

**Your sensors and filters are first order too**, and each one hands the loop up to ninety degrees of lag it did not previously have. Three innocent filters can hand over two hundred and seventy degrees, which is more than enough to oscillate. Filters are not free.

**Rule of thumb:** a sensor filter should be five to ten times faster than the loop bandwidth, or its pole is now part of your control problem.

---

## Carrying forward

Tau equals store divided by drain, in seconds. The pole is minus one over tau, a decay rate in one over seconds, and it is the slope of the transient on a log axis. Both are the same measurement of the same hardware.

Next: what happens when the drain is missing altogether.
