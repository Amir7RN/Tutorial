# Page 15 — Lead, Lag & Notch

*Listening script. Roughly eighteen minutes. The lead design procedure with the alpha table, lag versus integral action, and why the notch is the most dangerous compensator on the page.*

---

This is page fifteen. Buying phase where you need it, gain where you need it, and killing one resonance you wish you did not have.

---

## Same job as PID, stated in the language that makes it designable

Here is the framing, and it is the reason this page exists at all.

**A PID controller is tuned. A lead-lag compensator is *designed*.** You write down the phase margin and the crossover frequency you want, and you solve for the parameters. No twiddling.

And they are close relatives — closer than the different names suggest:

**PD is approximately a lead** — a zero, plus a pole to keep it realisable.

**PI is approximately a lag** — a lag whose pole went all the way to the origin.

**PID is approximately a lead-lag.**

The differences are real but small, and they run in the compensator's favour. A lead has **finite** high-frequency gain — it is a filtered derivative by construction, rather than by afterthought. And a lag **cannot wind up**, because it has no pure integrator in it.

---

## Lead — buys phase, costs high-frequency gain

The form is: C of s equals K c, times s plus z, over s plus p — where p equals alpha times z, and alpha is greater than one.

The **zero comes first**. So between z and p the phase is positive: the output *leads* the input. That is where the name comes from.

And two things about that lead are exact, not approximate.

The **peak lead** is the arcsine of alpha minus one, over alpha plus one.

And it sits at **omega max equals the square root of z times p** — the geometric mean of the zero and the pole.

### The alpha table, and the row that matters

At alpha equals two, you get nineteen degrees of lead, and a high-frequency gain of two.

At alpha equals four: thirty-seven degrees, gain of four.

At alpha equals ten: fifty-five degrees, gain of ten.

At alpha equals twenty: sixty-five degrees, gain of twenty.

At alpha equals one hundred: seventy-nine degrees, gain of one hundred.

**Read the third row.** The high-frequency gain is **exactly alpha** — and that gain lands squarely on your sensor noise.

Now look at the trade. Going from alpha of ten to alpha of one hundred buys you twenty-four extra degrees of phase, and costs you a **factor of ten** in noise amplification. Past alpha of about ten, the phase returns collapse while the noise cost keeps climbing linearly.

Which is why **two cascaded moderate leads beat one aggressive lead** when you need more than about fifty-five degrees.

### The design procedure, and it is genuinely mechanical

**Step one.** Measure the phase margin you have, and the one you want. The difference — plus about five to ten degrees, to allow for the fact that adding the lead shifts crossover — is your required phi max.

**Step two.** Alpha equals one plus sine phi, over one minus sine phi.

**Step three.** Put omega max **at the crossover frequency**. That is the only frequency where phase actually matters, so that is where you spend your lead.

**Step four.** z equals omega max over the square root of alpha. And p equals omega max times the square root of alpha.

Four steps, closed form, no iteration. That is what "designed rather than tuned" means.

---

## Lag — buys low-frequency gain, costs a little phase

Same algebraic form: C of s equals K c times s plus z, over s plus p — but now **z equals beta times p**, with beta greater than one.

**The pole comes first now**, so the phase dips *negative* in between. Which is exactly why you keep a lag well away from crossover.

What you are buying is the **beta-times extra DC gain**. And DC gain is precisely what kills steady-state error.

**Place the zero about a decade below crossover.** By the time the loop reaches the crossover frequency, the lag's phase penalty has recovered to a few degrees — but the low-frequency gain is permanently beta times higher.

### Lag versus integral action

This comparison is worth having straight.

A **pure integrator** gives you *infinite* DC gain, and therefore exactly zero steady-state error. But it also gives you a permanent minus ninety degrees, and a windup problem.

A **lag** gives you a large but finite gain, a small phase cost, and no windup at all.

So when "nearly zero error" is good enough, **the lag is the better trade.** You are giving up perfection you did not need, in exchange for phase margin and robustness you did.

---

## Interactive one — design a lead for a real joint

The plant is one over nought point two five s squared plus nought point four s, with proportional gain — the rigid joint again.

The procedure to follow: note the phase margin **without** the lead first. Then switch the lead on, place omega max at the crossover, and raise alpha.

Watch the phase curve **lift exactly where the magnitude crosses zero decibels** — that is the whole point of step three of the design procedure, made visible. And watch the overshoot readout fall as it does.

The readouts are: lead available, phase margin, crossover, and overshoot. Three plots: magnitude, phase, and the closed-loop step.

---

## Notch — and the reason it is the most dangerous compensator here

The form is a ratio of two quadratics with the **same** natural frequency omega zero, where the numerator damping zeta z is much smaller than the denominator damping zeta p.

What that gives you is **unity gain everywhere, except a deep narrow hole at omega zero.**

You place the hole on the SEA spring, or the belt, or the flexible forearm — whichever mode is stopping you raising the gain — and the loop stops seeing it.

It works. And here is why it is dangerous.

**A notch cancels a pole with a zero, and cancellation is a promise about a number you do not control.**

The resonance **moves**. The payload changes. The arm extends and its inertia changes. The structure warms up. The belt ages.

When omega zero drifts even ten or twenty percent, the zero is no longer sitting on the pole. And what is left is a **very lightly damped mode with your now-higher loop gain wrapped around it.**

**Notches fail suddenly, and in service — not gradually, on the bench.** That is the worst possible failure profile: the thing that looked best during commissioning is the thing that bites you in the field.

### The preference order, and it is worth memorising

**First: fix it mechanically.** Stiffen it, damp it, shorten it. A resonance that is not there cannot drift.

**Second: a plain low-pass below the resonance.** It costs you bandwidth, but it **cannot be detuned** — there is no sharp feature to fall off.

**Third: a *wide* notch**, which tolerates drift.

**And only then: a sharp one.**

---

## Interactive two — notch a resonance, then move the resonance

This widget is built to make the failure happen to you rather than be described to you.

The plant has a lightly damped mode at eighteen hertz. Tune the notch onto it, and watch the gain margin recover — it works, exactly as advertised.

Then use the **resonance drift** slider to simulate a payload change.

**The notch stays where you put it. The resonance moves. And the margin you thought you had disappears.**

The sliders are: notch centre frequency, notch width — that is the zero damping zeta z, where smaller means sharper — and resonance drift as a percentage. The readouts are gain margin, phase margin, and the actual resonance frequency, so you can watch the gap open up between where the notch is and where the problem is.

The experiment worth doing: tune a **sharp** notch perfectly, note the gain margin, then drift the resonance by fifteen percent. Then do the same with a **wide** notch. The wide one gives you less margin to begin with, and keeps most of it. That comparison is the entire argument for preferring wide notches, run rather than asserted.
