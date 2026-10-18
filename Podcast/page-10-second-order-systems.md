# Page 10 — Second-Order Systems

*Listening script. Roughly twenty-two minutes. Every regime, every formula, the pole geometry in full, and both interactives.*

---

This is page ten. Two poles, two energy stores, and the first system that can overshoot. Every robot joint you will ever tune is one of these.

The page opens by adding exactly one thing to the last page: **a second place to keep energy.**

The joint you have been studying had a mass, which stores speed, and friction, which only drains. Bolt a spring to it. Now there are **two** stores — the mass holds *kinetic* energy, the spring holds *potential* energy — and, crucially, **they can hand it to each other.**

That handover is what oscillation physically *is*. Not a mathematical property of a quadratic. A literal sloshing of energy between two containers.

---

## Watch the energy move — this is the whole page

Pull the joint twenty degrees away from rest and let go. Follow the energy, not the angle. Five steps.

**One.** At full deflection: the spring is stretched, so all the energy is **potential**. The joint is not moving — zero kinetic.

**Two.** The spring pulls it back. Potential drains, kinetic fills. The joint speeds up.

**Three.** It passes through the rest position. The spring is now relaxed — **zero potential** — so all the energy has become **kinetic**. Which means this is the moment it is moving **fastest**.

**Four.** And that is the answer. **It cannot stop at its destination, because it arrives there at maximum speed.** It sails through and starts compressing the spring on the far side.

**Five.** Kinetic drains back into potential until it stops — overshot — and the whole thing runs in reverse.

**Overshoot is momentum, and momentum is energy hiding in the other store.**

That is exactly what the previous page said was impossible with one store: reaching the target means the state is at its final value, with nothing left over. Here, reaching the target means the *spring* is at its final value while the *mass* is still carrying everything. Something is left over, and it is left over somewhere you were not looking.

Every overshoot you have ever seen on a robot is this. Every oscillation is energy that has nowhere to go and two places to be.

**Now add the damper back in.** It does not participate in the trade — it only takes. Each pass, some of the energy leaves as heat, so the amount being handed back and forth shrinks, and the swings get smaller. The three regimes everyone memorises are just three answers to one question: **how much does the damper steal per swing?**

---

## Interactive one — release it from twenty degrees and watch the two stores

On the left, the angle. On the right, where the energy actually is: blue is stored in the **spring**, orange is carried by the **mass**, and the pale line is the total — everything the damper has not yet turned into heat.

**Start at zeta equals zero.** The two curves swap perfectly and the total is a flat line: nothing is lost, so it rings forever. And here is the detail worth catching — every time the angle crosses zero, the spring's energy is zero and the mass holds all of it. **That peak in the orange curve *is* the overshoot, before it happens.** You can see the overshoot coming, in the energy, one quarter cycle early.

**Now raise zeta.** The total starts falling. At zeta equals one the trade barely completes once: the damper drains the spring before enough of it can become speed, so the mass never gets the momentum to carry past. **That is critical damping, and it is an energy statement, not a root-locus one.**

The readouts show you the energy left after one swing, the number of zero crossings, the peak kinetic share, and the regime name.

---

## The equation is those three sentences, written down

J theta double dot, plus B theta dot, plus K theta, equals tau.

Four terms, and each one is a sentence you already know.

**J theta double dot — the mass.** Stores kinetic energy; resists changes of speed. This is the store the previous pages had.

**K theta — the spring.** Stores potential energy; pulls harder the further you are from rest. **This term is the new one, and it is the entire difference between the two pages.**

**B theta dot — the damper.** Stores nothing; converts motion into heat, in proportion to speed.

**Tau** — what you push with.

Delete the K term and you are back to the first-order joint: one store, one leak, no overshoot. Delete the B term and nothing ever removes energy, so it rings forever. **The interesting behaviour lives entirely in the ratio between those two.**

Divide through by J and the three physical parameters collapse into two more useful ones. The transfer function becomes omega n squared, over s squared plus two zeta omega n s plus omega n squared — where **omega n equals the square root of K over J**, and **zeta equals B over two times the square root of K J**.

### Omega n — how fast the energy sloshes

Read the square root of K over J physically. A *stiffer* spring hands the energy back faster, so the trade happens quicker. A *heavier* mass takes longer to turn around, so it happens slower.

Omega n is literally the rate of that handover, in radians per second — and it is the frequency the joint would ring at with **no damper at all**.

### Zeta — what fraction of the sloshing the damper eats

This one is worth unpacking, because the phrase "damping ratio" hides a ratio of *what* to *what*.

The bottom of that fraction, two times the square root of K J, is not arbitrary. It is **exactly the amount of damping that would just barely stop the trade from happening at all.**

So zeta equals the damping you have, divided by the damping that would just kill the oscillation.

It is dimensionless because it compares damping with damping. Zeta equals nought point three means "I have thirty percent of the damping needed to suppress the sloshing entirely" — which is why zeta, and not B, predicts the overshoot.

### The same number read a second way: how much the damper steals per swing

Successive *peaks* shrink by a fixed factor every cycle. That is the **logarithmic decrement**.

The ratio of one peak to the next is e to the minus two pi zeta over the square root of one minus zeta squared. And the ratio of one *energy* to the next is e to the minus **four** pi zeta over the same square root.

Energy carries the **square** of the amplitude, so it falls twice as fast in the exponent. Which is why the widget reports twenty-eight percent of the *energy* surviving one swing at zeta equals nought point one, while the *amplitude* at that zeta is still fifty-three percent of what it was. Both numbers are correct. They are measuring different things, and confusing them is a standard way to misread a decay trace.

### The impedance-control connection, and it is exact

When you choose K and B on the impedance control page, you are not choosing "stiffness and damping". You are choosing **omega n and zeta**, and therefore the overshoot and the settling time, whether or not you meant to.

And note the trap sitting in the formulas: **double K alone**, and omega n rises by root two while zeta **falls** by root two.

**Stiffening a joint without raising B always makes it ring more.** That is the most common impedance-tuning mistake there is, and it is visible right there in the algebra.

---

## The five regimes, as energy accounting

Every one of these is the same question: **can the spring get enough energy into the mass, before the damper takes it, for the mass to carry past the target?**

**Zeta less than zero.** Something *adds* energy every swing instead of removing it — negative damping. The trade continues and grows. **Unstable.** And physically real: a controller feeding back with the wrong sign, or a delay that makes a correction arrive as a push.

**Zeta equals zero.** Nothing takes anything. The energy trades perfectly, forever. **Marginal.** An undamped SEA spring, or a frictionless joint.

**Zeta between zero and one.** The damper takes a slice each swing, but not enough to stop the trade. It rings, and each ring is smaller. **Underdamped** — and this is where nearly every real robot joint lives.

**Zeta equals one.** The damper takes it at exactly the rate the spring can hand it over. The mass never accumulates enough speed to overshoot — not even slightly — and it gets home as fast as that allows. **Critically damped: the fastest arrival with no overshoot.**

**Zeta greater than one.** The damper is greedier than the spring is generous. Most of the potential energy leaves as heat before it can become motion, so the joint *oozes* home. **Overdamped** — and slower than critical, which surprises people who assume more damping is safer.

And note what is *not* in that table: omega n. **The regime is decided entirely by zeta.** Omega n only sets how fast the whole story plays out.

---

## Where the poles are — and why the picture looks like that

The poles sit at s equals minus zeta omega n, plus and minus j omega n times the square root of one minus zeta squared.

The previous page said the two axes of the s-plane are two physical rates: horizontal is how fast it dies, vertical is how fast it wiggles. A first-order pole had nothing to wiggle with and sat on the axis. Now there are two stores trading, so the pole lifts off — and each part of that expression is one of those rates.

**Real part equals minus zeta omega n — the decay rate.** How fast the damper is draining the total. It is exactly the "pole equals leak over store" of the earlier pages, and **settling time depends on it and nothing else.**

**Imaginary part equals omega d, which is omega n times the square root of one minus zeta squared — the rate the energy is actually sloshing.** Note it is *slower* than omega n: the damper is stealing energy mid-trade, so each round trip takes longer. **This is the frequency you hear.**

**Distance from the origin equals omega n** — Pythagoras on the two above. The poles ride a circle of radius omega n, so changing zeta alone slides them *around* that circle without changing how energetic the system is, only how the energy is split between dying and wiggling.

**Angle from the negative real axis equals the arccosine of zeta** — therefore **the angle *is* the damping**. Straight left along the axis is zeta equals one: all decay, no wiggle. Straight up is zeta equals zero: all wiggle, no decay. Forty-five degrees is zeta equals nought point seven zero seven.

**So a pole plot is a picture of how a system spends its energy.** How far left is how fast it gives it up. How far up is how fast it passes it back and forth.

That is the whole reason experienced people read pole plots instead of step responses: the two things you care about are on two perpendicular axes, instead of tangled together in one curve.

And the summary table:

**Zeta less than zero** — poles in the right half plane — unstable, growing oscillation.

**Zeta equals zero** — poles exactly on the j omega axis — marginal, rings forever. An undamped SEA spring.

**Zeta between zero and one** — a complex pair in the left half — underdamped, overshoots then settles.

**Zeta equals one** — two equal real poles — critically damped, fastest with no overshoot.

**Zeta greater than one** — two distinct real poles — overdamped, the slow pole dominates, sluggish.

---

## The four formulas you will actually use

Peak overshoot M p equals e to the minus pi zeta over the square root of one minus zeta squared.

Settling time t s is approximately four divided by zeta omega n.

Peak time t p equals pi over omega d.

And omega d equals omega n times the square root of one minus zeta squared.

**Overshoot depends only on zeta.** Not on omega n, not on the plant, not on how big the step was. Zeta of nought point one gives seventy-three percent. Nought point three gives thirty-seven percent. Nought point five gives sixteen percent. **Nought point seven zero seven gives four point three percent.** One point zero gives zero.

**Settling time depends only on the real part.** Zeta omega n is the distance the poles sit to the left of the axis, and settling time is about four divided by it.

So "faster" and "less overshoot" are **separate** knobs — which is why "it overshoots, so slow it down" is bad advice. **Raise zeta, keep omega n, and you get both.**

**And why zeta equals nought point seven zero seven is everywhere.** It is the value at which the closed-loop magnitude response has *no peak at all* — maximally flat — while still being as fast as possible. Below it you get a resonant bump that amplifies disturbances at that frequency. Above it you are just being slow. So: nought point seven zero seven in analysis, and nought point eight to one point zero in a real robot, where you would rather not overshoot into a person.

---

## Interactive two — zeta and omega n, and the pole pair they place

Two sliders: zeta, which can go negative, and omega n. Watch the poles ride the circle as you change zeta, and the circle grow as you change omega n. Cross zeta equals zero and the poles cross into the red.

The readouts are overshoot, settling time to two percent, ring frequency, and resonant peak.

---

## Interactive three — J, K and B, and the omega n and zeta they secretly are

This is the same widget with the physical parameters on the front: sliders for inertia, stiffness and damping.

And there is one experiment to do deliberately. **Raise K alone** and watch zeta fall and the overshoot grow — that is the mistake described earlier, made visible. Then raise B to put it back.

The readouts show omega n, zeta, overshoot and settling time, so you can see three physical numbers turning into two behavioural ones in real time.

---

## Why second order is the universal model

It is not that the world happens to be second order. It is that **a mass with a spring and a damper is what a controlled joint becomes.**

Close a PD loop around a rigid inertia. You start with J theta double dot plus b theta dot equals minus K p theta minus K d theta dot. Move it all to one side and you get:

J theta double dot, plus the quantity b plus K d, times theta dot, plus K p theta, equals zero.

**Identical form.** Your **proportional gain became the spring** and your **derivative gain became the damper**. That is not an analogy — it is the same differential equation. So:

Omega n equals the square root of K p over J. And zeta equals b plus K d, over two times the square root of K p J.

Which is a complete PD tuning recipe. Want omega n of twenty radians per second and zeta of nought point eight, on an inertia of nought point two five kilogram metres squared with friction of nought point four?

Then K p equals J omega n squared, which is **one hundred**. And K d equals two zeta omega n J minus b, which is **seven point six**.

No trial and error. No twiddling.

---

## And here is the fact that surprises people

**A pure second-order plant *still* cannot be destabilised by proportional feedback.**

Two poles supply at most one hundred and eighty degrees of phase lag, and they only reach it asymptotically — so the loop magnitude has fallen far below one by the time the phase gets there.

You need a **third** pole, or a **delay**, or a **resonance** to make a loop oscillate.

Which is exactly why the real-time page mattered: **your loop delay is the thing that turns a well-behaved second-order joint into one that rings.**

Real instabilities are almost never the plant's fault. They are the implementation's.
