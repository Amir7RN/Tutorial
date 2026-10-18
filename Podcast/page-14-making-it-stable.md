# Page 14 — Making It Stable

*Listening script. Roughly eighteen minutes. Root locus, what each PID term does to the poles, the inverted-pendulum derivation, and the two rules for unstable plants.*

---

This is page fourteen, and it starts the second half of the story.

The previous four pages were **diagnosis**: where are the poles, how close to the edge am I. This section is **treatment**. And the through-line for all four treatment pages is a single sentence:

**A controller cannot change the plant. It can only move the plant's poles, and it does that by adding poles and zeros of its own.**

Everything that follows — P, I, D, lead, lag, notch, state feedback — is a different way of choosing what to add.

---

## The one equation this page is about

Close a unity loop around L of s, which is some numerator over some denominator. The closed-loop poles are the roots of:

**den of s, plus K times num of s, equals zero.**

Read what that says. The open-loop poles were the roots of **den** alone. Turning K up **mixes num into den**, and the roots **move**.

Feedback is a pole-relocation machine. And the only question in controller design is where you want them to end up.

---

## The root locus, and its two endpoints

Sweep K from zero to infinity and trace the roots. That picture is the root locus.

Two facts fall straight out of the equation above, and they are worth more than all the sketching rules.

**As K goes to zero:** den dominates, so the closed-loop poles *are* the open-loop poles. **Every branch starts at a pole.**

**As K goes to infinity:** num dominates, so the roots go to the roots of num. **Every branch ends at a zero** — and if there are not enough zeros to go round, the leftover branches run off to infinity along asymptotes.

**And that is the whole reason a derivative term stabilises things.**

A PD controller, K p plus K d s, is a **zero** at s equals minus K p over K d.

A zero is a **destination**. It reaches out and pulls the locus toward itself. Put it in the left half plane and it drags the closed-loop poles left with it — and left is damping.

Move the zero closer to the origin — which means raising K d relative to K p — and it pulls harder.

That is the entire mechanism, and it is why "add some D" is the standard answer to "it's ringing."

---

## What each term adds, and what it costs

**P — the proportional term, K p.**

What it adds: nothing. It is pure gain.

Effect on the poles: it slides them *along* the existing locus — faster, and less damped.

The price: on a third-order plant it eventually crosses into the right half plane. And it puts noise straight through to the motor.

**D — the derivative term, K d s.**

What it adds: a **zero** at minus K p over K d.

Effect on the poles: it pulls the locus **left**, which is damping. And in the frequency domain it is plus ninety degrees of phase **lead**.

The price: it amplifies noise in proportion to frequency. So it must be filtered — and the filter adds a pole back.

**I — the integral term, K i over s.**

What it adds: a **pole at the origin**, plus a zero.

Effect on the poles: it drags the locus **right** — less damped, closer to the edge.

The price: minus ninety degrees of phase at low frequency, and windup.

So the familiar advice — *P for speed, D for damping, I only if you must* — is not folklore. It is a precise statement about **which direction each term drags the roots.**

---

## Interactive one — sweep the gain and watch the roots migrate

The grey trace is the whole locus. The crosses are where the poles sit at your current gain.

Four plants in the dropdown.

**Three poles:** one over the product of s plus one, s plus two, s plus three. This is the interesting one — take K past the critical value and watch a branch cross into the red half plane.

**Joint plus integrator:** one over s times s plus one times s plus two. The Routh example from page eleven, drawn as a locus.

**Rigid joint:** one over nought point two five s squared plus nought point four s. Two branches, and they never leave the left half plane no matter what you do.

**With a PD zero:** s plus eight, over s times s plus one times s plus two. Same plant as the second entry, but now with a zero at minus eight — and you can watch that zero reach out and drag the branches toward it.

The readouts are: the worst pole, the damping ratio, the verdict, and the critical gain.

---

## The genuinely unstable case: an inverted pendulum

Now the case that matters for a biped, and the algebra is short enough to follow by ear.

Linearise a pendulum about **upright**. The gravity term flips sign — it now pushes the pendulum *away* from equilibrium instead of back toward it. So the plant is:

J theta double dot, **minus** m g l theta, equals tau.

Which gives poles at s equals plus and minus the square root of m g l over J — which is plus and minus the square root of g over l.

**One of those is in the right half plane.** The plant is genuinely unstable, before any controller exists.

### Try pure proportional feedback

Set tau equals minus K p theta. The characteristic equation becomes:

J s squared, plus the quantity K p minus m g l, equals zero.

Which gives s equals plus and minus j times the square root of K p minus m g l, over J.

**Look at what happened.**

With K p **less than** m g l, the poles stay real and one is still in the right half plane. The pendulum falls — only slower.

With K p **greater than** m g l, the poles are **purely imaginary**. The pendulum no longer falls; it **oscillates about upright forever.**

Marginal. Never stable. For **any gain whatsoever.**

And the reason is visible in the equation: there is no damping term, so nothing removes energy. The pendulum swings past upright, comes back, swings past again.

### Add a damping term

J s squared, plus K d s, plus the quantity K p minus m g l, equals zero.

**Stable if and only if K d is greater than zero, *and* K p is greater than m g l.**

Two conditions, both necessary, and both physically obvious in hindsight: **you must push back harder than gravity pulls**, and **you must remove energy.**

This is the smallest complete example of why D is not optional. For a balancing robot it is not a tuning nicety — **without it the machine cannot stand up at any gain.**

---

## Interactive two — balance it yourself

A half-metre pendulum, released twenty degrees from upright. Two sliders: K p and K d.

The dashed line marks K p equals m g l. Below that line, no amount of damping helps — the readout will tell you it is still unstable however far you push K d.

And the experiment worth doing deliberately: set **K d to zero** with K p **above** the line, and watch the marginal oscillation that the algebra predicted. It does not fall over. It does not settle. It just swings, forever, exactly as the purely-imaginary poles said it would.

The readouts are: m g l, which is the number you must beat; the worst pole; the verdict; and the open-loop right-half-plane pole, so you can see what you are up against.

---

## Two rules that come with unstable plants

**Rule one. You must be faster than the instability.**

A right-half-plane pole at s equals plus p grows like e to the p t, doubling every natural-log-of-two over p seconds. Your loop crossover has to sit comfortably above p — a common rule is crossover greater than twice p — or **the divergence outruns the correction**.

Put numbers on it. For a one-metre inverted pendulum, p equals the square root of nine point eight one over one, which is three point one radians per second. The doubling time is **two hundred and twenty milliseconds.**

That single number is why a balance controller must run in the kilohertz, and why a two hundred millisecond perception stall is a fall.

It is the real-time page's argument arriving from the other direction — and notice it is not about computation being slow. It is about the physics being fast.

**Rule two. Never cancel an unstable pole with a zero.**

On paper, s minus p over s minus p equals one, and the problem disappears. It is very tempting.

In reality the cancellation is **never exact**. And what you have built is a system whose unstable mode is **invisible from the output** — it grows silently, producing no signature at your sensor, until something saturates and the machine comes apart.

**The pole must be moved by feedback, not hidden.**

---

## Carrying forward

P slides the poles along the locus. D adds a zero that pulls them left. I adds a pole at the origin that drags them right.

Marginal plants need D. Unstable plants need D *and* enough gain, and need the loop to be faster than the instability.

The next page does the same job in the frequency domain, where it is easier to be quantitative.
