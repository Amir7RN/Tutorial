# Interview Prep — Pages 2 to 15

*Listening script, about fifty minutes at the usual narration speed. Boston Dynamics, Staff Robotics Engineer, Spot Manipulation. Pages two through fifteen as one argument, with the questions an interviewer is likely to build out of it.*

*If you want it in two drives, stop after page eleven — that is roughly the halfway mark and the natural break. Pages two to eleven are "what a joint is and what your gains actually set"; twelve to fifteen are "how close to the edge are you, and what can you not design around". If you only have one drive, the highest-value twenty minutes are page eleven, page thirteen, and the two summary sections at the end.*

---

## The frame

The job asks for rigid-body dynamics, inverse kinematics, and classical control — **impedance and force control, operational space control** — plus years on real hardware.

Notice what that is really saying. **Impedance control is a second-order systems question wearing a robotics hat.** Setting a stiffness and a damping on an arm *is* placing a pole pair. Asking whether the arm stays stable against a wall *is* asking about margins. Asking why you cannot stiffen further *is* asking about a drivetrain resonance and a sampling rate.

So these are not textbook pages. **They are the vocabulary the interviewer will use to ask about arm control.** And at staff level they test whether you know what each formula is a statement *about*, and where it stops being true — so I will give derivations, because a derivation survives a follow-up you did not anticipate.

---

## Page two — order, states, and the words

**The order of a system is the number of independent energy storage elements.** Not the number of parts.

A **mass** stores kinetic energy, state is velocity. A **spring** stores potential energy, state is deflection. A **motor winding** stores magnetic energy, state is current. Each adds one. A **damper** converts energy to heat and loses it — **no state.** A resistor, a gear ratio, a lever — no state.

Two things people get wrong. **Dampers never count**, however many: motor inertia, series spring, load inertia is third order whether it has one damper or six. And the stores must be **independent** — two springs bolted rigidly in parallel are one state, because their deflections cannot differ.

Then vocabulary. **Every response is steady state plus transient, and the transient is the only thing poles describe.** When someone says the response "dies", they mean the *transient* dies — the output goes to the steady state and stays. **What dies is the error, not the motion.**

**Likely question: what order is a Spot arm joint?** Answer with a question — *from what input to what output, and how much drivetrain am I modelling?* Motor current to link angle with a rigid transmission is second order. Add the harmonic drive's torsion as a spring and it is motor inertia, spring, link inertia: **third order minimum, per joint.** Add the winding and you are at fourth. Land this: **you pick model order by deciding which stores matter inside your bandwidth, and the one you dropped is usually the one that bites.**

---

## Page three — measuring a real joint

Three numbers: **J**, inertia. **b**, viscous friction. **k**, stiffness.

Four experiments. **Coast-down** — the slope of log-omega against time *is* the pole, b over J. **Torque step** — torque over steady speed is b. **Pendulum swing** — let the link fall, time the swings, and gravity as the spring gives you **J directly**; the value is that **the motor is off**, so no torque constant or gearbox efficiency can bias it. **Tap test** — hit it, read the ring, and with J known, **k is J omega-n squared.**

Now the warning, and this is the hardware answer they are hiring for. **Real friction is not b times omega.** There is Coulomb friction — roughly constant, opposing motion regardless of speed — plus stiction at zero speed. The honest model is **b omega plus f-c times sign of omega.** Fit only b and you get a number wrong at every speed but the one you fitted at. And sign-of-omega is not linear, so a joint *modelled* first order still has a dead zone near zero.

How it is really done: **one trajectory, all parameters at once**, because the dynamics are **linear in the parameters** — a row of measured signals times a column of unknowns. Drive one rich trajectory, stack rows, least-squares it. And what matters more than the maths is the trajectory: **if you never accelerate, the omega-dot column is zeros and J is unidentifiable.** That is **persistent excitation**, worth naming out loud.

Then damping, from **the logarithmic decrement.** Two peaks exactly n cycles apart differ *only* by the envelope, because the cosine repeats. Take the log of the ratio, substitute the damped period, and **omega-n cancels**: delta is one over n times the log of the ratio, and **zeta is delta over two pi.** That cancellation is what makes it usable — **you need neither stiffness, nor inertia, nor even calibrated sensor units.** Two amplitudes and a cycle count.

The rule of thumb is **wait for at least a fifty percent amplitude drop**, and that is a noise argument: fractional error goes as noise over the log of the ratio, so peaks three percent apart divide your noise by zero point zero three and the answer is garbage. Half amplitude means **n is about zero point one one over zeta** — two cycles at zeta of zero point zero five, and **less than one by zeta of zero point three**, where the method runs out of data.

And the self-check: **repeat with a different pair of peaks**, because every pair should give the same delta. If zeta drifts as you pick later peaks, it is an offset you forgot to subtract, or **Coulomb friction, which removes a fixed amount per cycle rather than a fixed fraction**, so its peaks fall on a straight line instead of an exponential.

---

## Page four — how software changes physics

The page that matters most for an impedance job.

Rigid joint, close a PD loop, collect terms: **J theta-double-dot, plus b plus K-d, theta-dot, plus K-p theta, equals zero.**

**Your proportional gain became a spring. Your derivative gain became a damper.** Not an analogy — the same differential equation a steel spring would have produced, with no spring in the machine. So **omega-n is root K-p over J, and zeta is b plus K-d over two root K-p J.** A complete tuning recipe: for omega-n of twenty and zeta of zero point eight on a quarter-kilo-metre-squared joint with b of zero point four, K-p is one hundred and K-d is seven point six. No twiddling.

You can synthesise any stiffness, any damping, **negative** damping, stiffness that changes with configuration or contact state. **What you cannot escape is this: a steel spring is passive; a software spring is active.** Every joule a steel spring returns was one you put in — it physically cannot inject energy. A software spring's torque comes from the power supply through an amplifier, and **it can put in more than it took out**, which is what instability physically *is*. Strong line: *my impedance controller is only as safe as its passivity margin, and a discrete-time implementation with delay is not automatically passive even when the continuous design is.*

**Three places the illusion breaks**, and these are the debugging answers.

**Bandwidth.** A software spring is a spring only inside the loop bandwidth. Lean slowly and you feel K-p exactly. Strike it, and above the bandwidth the controller has not reacted, so **what you feel is the bare inertia and the raw drivetrain.** That is why an impedance-controlled arm feels compliant when pushed and like a brick when hit.

**Torque limit.** A virtual spring saturates at the motor limit; past that the stiffness you programmed is not there.

**Delay.** Every sample turns intended damping into phase lag, and enough of it turns damping *negative*. **A D term with too much delay does not damp — it drives.**

**Likely question: why not just set K-p very high?** Four reasons, give all four: torque limit; noise amplified through the D term; crossover pushed into a drivetrain resonance; sampling and delay.

---

## Pages five to eight — first order

**One energy store, one drain.** Bench signature: step it and it rises fastest at the start, decelerating the whole way, **never overshooting.** Any overshoot at all and it is not first order. **After one tau it has covered sixty-three point two percent**, because that is one minus e-to-the-minus-one, and **the pole is minus one over tau** — a duration flipped into a rate.

The robotics special case is **the pole at the origin — an integrator, a store with no drain.** A free joint: constant torque in, position ramps forever. **Marginally stable** — a third category, not a mild kind of stable. Every position-controlled joint has one, which is why position control needs feedback at all. And you deliberately add one in the controller — the I term — because **an integrator is the only thing that holds a nonzero output with zero input**, which is exactly what cancels a constant gravity load with zero steady-state error.

Then frequency. Ask where a first-order magnitude falls to one over root two — which is what **minus three dB** means, and which is really the **half-power point**, since power goes as amplitude squared — and you get **omega equals one over tau.** So **the pole, the corner and the bandwidth are the same number.** A ten-millisecond current loop is a hundred-radian-per-second pole is a **fifteen point nine hertz** bandwidth.

Two more: **settling to two percent is four tau; rise time ten to ninety is two point two tau.** Multiply rise time by bandwidth in hertz and you get **zero point three five**, exactly, because the taus cancel. Best sanity check in the area — **a datasheet claiming one kilohertz is claiming a zero point three five millisecond rise time.** If the scope shows three milliseconds, someone is wrong.

Above the corner: **minus twenty dB per decade**, phase sliding toward **minus ninety**, passing minus forty-five exactly at the corner. And the structural fact: **one pole approaches minus ninety but never reaches it**, so **you cannot destabilise a first-order plant with proportional feedback at any gain.**

**Likely question: why does the current loop run at twenty kilohertz and the joint loop at one?** Because L over R is tens of microseconds and the mechanical constant is tens of milliseconds — three orders apart. **That separation is what lets you treat the current loop as an ideal torque source**, and the moment joint bandwidth creeps toward it, the assumption quietly stops being true.

---

## Page nine — the s-plane

**The two axes are two physical rates. The real part is how fast it dies; the imaginary part is how fast it wiggles.** A pair at minus sigma plus or minus j omega gives e-to-the-minus-sigma-t times cosine omega t — **real part sets the envelope, imaginary part sets the ringing inside it.** Which is why experienced people read pole plots rather than step responses: **the two things you care about sit on perpendicular axes instead of tangled in one curve.**

---

## Page ten — free vibration, solved from initial conditions

No damper, no input, but an initial displacement and velocity. Guess x equals e-to-the-s-t — which works because differentiating an exponential just multiplies it by s. The equation collapses to **s equals plus or minus j root k over m**: purely imaginary, so nothing decays, because there is nothing to decay into. Euler turns those into a cosine and a sine, and the initial conditions pick the constants directly:

**x equals x-nought cosine omega-n t, plus v-nought over omega-n, sine omega-n t.**

The cosine is what you loaded **as position** — full height, zero slope. The sine is what you loaded **as speed** — zero height, full slope. Same oscillation, a quarter cycle apart. Collapse to one cosine: **x equals A cosine, omega-n t minus phi**, with **A the square root of x-nought squared plus v-nought over omega-n squared.**

Here is the practical content. **The peak is not x-nought — it is the hypotenuse of a right triangle whose legs are the two initial conditions, and it is strictly bigger whenever the velocity is nonzero.** And because v-nought enters squared, **the direction of the velocity does not matter** — a shove toward the target and a shove away give the *same* peak excursion, differing only in *when*.

Concrete: an impact leaving a link at two degrees and forty degrees per second, on a joint with omega-n of twenty, does not swing to two degrees. It swings to **two point eight three.** And that A is conservation of energy in disguise — **the two legs of the triangle are the square roots of the two energy stores, and the hypotenuse is the total.**

One more reading: **phi is a time shift wearing angular units** — the peak arrives at phi over omega-n. **An angle is a delay, and the conversion factor is the frequency.** Every phase lag on every later page is that sentence at a different frequency, which is why phase margin will turn out to mean something about time.

Add the damper and the quadratic gives **s equals minus zeta omega-n, plus or minus omega-n root zeta squared minus one.** **Everything that follows is decided by the sign under that root.** **Below one:** complex pair, **oscillates** inside a decaying envelope. **Exactly one:** the roots collide, and since one exponential cannot carry two initial conditions the second solution is **t times e-to-the-minus omega-n t** — no sine anywhere. **Above one:** two real roots, a sum of plain exponentials.

Take this from the last branch: as zeta rises past one, **the roots split and one moves back toward the origin.** At zeta of three they sit at minus zero point one seven omega-n and minus five point eight three. The slow one dominates, so a heavily overdamped joint behaves like a **first-order** system nearly six times slower than critical. **More damping is not safer past zeta of one — you are dragging a pole toward the imaginary axis.**

And a piece of judgement worth showing. Root of one minus zeta squared is zero point nine nine five at zeta of zero point one, so **drop it from magnitudes freely — but never from a phase.** Two reasons. **Amplitude errors multiply; phase errors add** — five point seven degrees across four blocks is twenty-three degrees, out of a margin that is only forty-five. And **a frequency error accumulates in time**: half a percent means that after fifty cycles you are a quarter cycle out, predicting "peak" where the hardware says "zero crossing."

---

## Page eleven — second-order systems

**Overshoot is momentum, and momentum is energy hiding in the other store.** The joint passes through its target at maximum speed, because that is the moment the spring is relaxed and everything has become kinetic. **It cannot stop at its destination because it arrives there at maximum speed.**

**Omega-n is root K over J** — how fast energy sloshes. **Zeta is B over two root K J** — and the thing to unpack is what that denominator *is*: **two root K J is exactly the damping that would just barely stop the trade happening at all.** So zeta is "the damping you have over the damping that would kill the oscillation." Dimensionless, because it compares damping with damping.

**The impedance connection — have this sentence ready.** When you choose K and B, **you are not choosing stiffness and damping, you are choosing omega-n and zeta, and therefore overshoot and settling time, whether you meant to or not.** And the trap in the algebra: **double K alone and omega-n rises by root two while zeta falls by root two.** Stiffening without raising B always makes it ring more. **The most common impedance-tuning mistake there is.**

Now the step response, solved rather than quoted. The **particular** solution for a constant command is the constant one. The **homogeneous** part is page ten unchanged. Starting from rest, the free part must begin at minus one to cancel the particular part, which gives **A equals one over root one minus zeta squared.** So:

**y equals one, minus e-to-the-minus zeta omega-n t over root one minus zeta squared, times sine omega-d t plus phi — where phi is arccosine zeta.**

And **phi is arccosine zeta, the same angle the poles make with the negative real axis.** Adjacent zeta, opposite root one minus zeta squared, hypotenuse one — **every phase angle in second-order theory is an acute angle of that one triangle.**

Differentiate once and the two terms collapse, because zeta and the root term are cosine phi and sine phi, so **phi disappears**: **y-dot equals omega-n e-to-the-minus zeta omega-n t over root one minus zeta squared, times sine omega-d t.** That line is worth more than the formulas below it: **the slope of a second-order step response is a decaying sine at omega-d with no phase offset**, so every turning point is where that sine is zero — **evenly spaced forever at multiples of pi over omega-d.**

From which: **peak time is pi over omega-d.** **Overshoot** is that time put back in — the sine becomes minus root one minus zeta squared, which **divides out against the amplitude**, leaving **e to the minus pi zeta over root one minus zeta squared.** Two cancellations, and that is the entire reason overshoot depends on zeta alone. **Settling time** comes from solving the envelope, not the function: minus log of your tolerance over zeta omega-n. Minus log of zero point zero two is three point nine one, hence **four over zeta omega-n** — use three for a five percent band. **The rule is not attached to the number four.**

Memorise: **zeta zero point one gives seventy-three percent overshoot; zero point three, thirty-seven; zero point five, sixteen; zero point seven zero seven, four point three; one, zero.**

**Why zeta of zero point seven zero seven is everywhere** — three reasons. It is the exact boundary below which the closed loop has a **resonant peak**. At that value the response is **maximally flat** — nothing amplified. And **the minus three dB bandwidth equals omega-n to four figures**, so the number you designed for is the number you measure.

**Three frequencies, and they are not the same number.** **Omega-n**, the pole radius, what it rings at undamped. **Omega-d**, omega-n root one minus zeta squared, what a **step response** rings at. **Omega-r**, omega-n root one minus **two** zeta squared, where a **swept sine peaks.** Always omega-r below omega-d below omega-n. At zeta of zero point one they are zero point nine nine, zero point nine nine five and one — indistinguishable, which is why nobody notices. At zeta of zero point six they are **zero point five three, zero point eight and one**, and confusing them is a forty-seven percent error.

Related: **Q is one over two zeta** — the gain at omega-n, and also energy stored over energy lost per radian. **A joint with zeta of zero point zero one has Q of fifty**: shake it at omega-n with a torque that would statically move it one degree and it swings **fifty**. That is how a trivial vibration destroys a lightly damped structure.

And the closing fact. **A pure second-order plant cannot be destabilised by proportional feedback** — two poles supply at most one hundred eighty degrees and only asymptotically, so the magnitude has collapsed by the time the phase arrives. **You need a third pole, a delay, or a resonance.** Real instabilities are almost never the plant's fault — **they are the implementation's.**

---

## Page twelve — stability

**BIBO**: bounded input, bounded output. For a linear time-invariant system that is one geometric statement — **every pole has a strictly negative real part.** "Strictly" is load-bearing.

A left-half pair rings down, **stable** — a joint under PD. A pole at exactly zero holds a constant forever, **marginal** — a free joint. A pair on the imaginary axis rings forever, **marginal** — an undamped spring. A right-half pole grows, **unstable** — an inverted pendulum, which is every biped, and also **an arm held against gravity past its balance point.**

**Marginal is not "almost stable", it is "nothing decides."** Its own category because the failure mode differs: it does not blow up, it **drifts**, and drift is harder to debug because it looks like a bias.

And keep this one: **all coefficients positive is necessary but not sufficient.** Practically every unstable third-order-and-up system has all-positive coefficients and still fails the Routh array.

---

## Page thirteen — Bode, margins, and the bandwidth ceiling

The most likely section to be interviewed on.

**Where instability comes from, in one sentence.** Feedback subtracts. If the loop delays a signal by exactly half a cycle — **minus one hundred eighty degrees** — the subtraction becomes an *addition*, and if the loop gain is still at or above one there, the signal returns bigger every trip.

**Gain margin.** Find where the phase hits minus one eighty; the gain there is below one, and GM is how far below. It answers *how much stronger could my plant be than I think.* Note the minus sign in the definition: at a healthy crossing the raw dB is negative and the minus flips it positive. So **positive gain margin is safe; negative means the nominal design already does not work.** A negative gain margin is not a small margin.

**Phase margin.** Find where the gain passes zero dB — the crossover. The phase there is above minus one eighty, and PM is how far above. It answers *how much more delay could there be.*

**Targets: phase margin forty-five to sixty degrees, gain margin six to twelve dB.** Below thirty degrees a robot rings visibly and any payload change is a gamble.

**Phase margin is damping**, and run it both ways. Thirty degrees is zeta zero point three, thirty-seven percent overshoot. Forty-five is zeta zero point four three, twenty-two percent. Sixty-five is zeta zero point seven one, four point three percent. **PM is roughly a hundred times zeta.**

Follow that chain, because it is why the frequency domain is worth learning. Measure forty-five degrees of phase margin on a swept sine. That is zeta of zero point four three, about twenty-two percent overshoot. **You now know the shape of the time response and you never ran a step.** Backwards is what you actually do on hardware: the arm overshoots about twenty percent, so zeta is about zero point four five, so you have about forty-five degrees, so **stop raising the gain.**

One distinction that separates people who have shipped. **The same dB axis answers two questions with opposite verdicts.** *Does the output follow the input* is asked of one block at **every** frequency, and positive dB there is fine. *Is the loop weak enough to avoid sustaining oscillation* is asked of the **whole loop** at exactly **one** frequency, and positive dB there is fatal. Every real loop is positive down low and negative up high — **that shape is not a fault, it is what a working design looks like.**

And the payoff: **the "bad" reading causes the "good" one.** A plant's rolloff is poor tracking at high frequency, and it is *also* exactly what crushed the loop gain before the phase crawled to minus one eighty. **Phase and magnitude are racing, and for a plain plant magnitude always wins.** Instability needs something that supplies phase **without** the attenuation — and **a pure delay is the purest example: unlimited phase lag at unity gain, forever.**

Also know which curve you are holding. **Margins live on L, the loop gain with feedback imagined cut, and only there. Overshoot, settling and bandwidth live on T, the closed loop. Hardware resonances and Q live on P, the raw plant.** You cannot read a margin off T: if the loop is unstable, T diverges and there is nothing to measure against.

Now **bandwidth**, because two definitions circulate.

**Open loop, bandwidth is the crossover** — and that is derived. The error transfer is one over one plus L. Below crossover the loop gain is large, the error is small, and **the loop is in charge.** Above crossover the loop gain is small, one over one plus L is about one, and **the loop is a spectator.** Crossover is where **authority runs out.**

**Closed loop, bandwidth is where T falls three dB below its DC value** — same definition as any filter, because T *is* a filter. And the bridge: **closed-loop bandwidth is between one point three and one point six times the crossover.** So **crossover, then bandwidth, then twice crossover**, with one and a half the working estimate.

Now **the SEA bandwidth ceiling, derived** — the highest-value item here.

A lightly damped resonance in the drivetrain — series elastic element, harmonic drive torsion, flexible link — multiplies the loop gain by one extra second-order factor with its own omega-res and its own very small zeta-r.

**Below the resonance that factor is one in magnitude and zero in phase.** The spring is invisible and your rigid design still holds. That is why this is a *ceiling*, not a general penalty.

**At the resonance it does two things at once.** It adds one hundred eighty degrees of lag, nearly all inside one octave, because zeta-r is small and the transition is sharp. And it **multiplies the magnitude by Q, one over two zeta-r** — a steel flexure at zeta-r of zero point zero five is a **ten-times amplifier**, precisely where the phase has just handed you minus one eighty.

**Both effects land at the same frequency, and that coincidence is the entire problem.** A plain plant is safe because rolloff crushes the gain before the phase arrives. **A lightly damped resonance supplies the phase and simultaneously boosts the gain.** Same structural problem as a delay — except a delay merely refuses to attenuate, whereas a resonance actively amplifies.

Put it together. Gain margin is measured at the phase crossover, which is now essentially the resonance, and the gain there is the rigid design's gain times Q. So **gain margin is about minus twenty log of Q times the rigid loop's magnitude at the resonance.** Above crossover a typical loop rolls off twenty dB per decade, so that magnitude is roughly crossover over resonance. Substitute, demand a gain margin of a factor g, and solve:

**Crossover must be at most two zeta-r, times omega-res, divided by g.**

Read it, because it is the SEA design rule and it is brutal. **Your achievable bandwidth is not the resonant frequency. It is the resonant frequency times twice the damping of a spring nobody designed to be damped, divided by your margin requirement.** A fifteen-hertz spring at zeta-r of zero point zero five with six dB of gain margin gives **zero point seven five hertz.** Not fifteen. Under one hertz, from a mechanism resonating at fifteen.

Three fixes, and they are the only three, because every term is a lever. **Raise zeta-r** — the bound is *linear* in it, so going from zero point zero five to zero point two five buys five times the bandwidth. Do it physically, or with an inner torque loop — **which is exactly why an SEA has a torque sensor and a cascade structure.** **Raise omega-res** — stiffer spring, but stiffness is what you fitted a spring to give up, so you trade away force fidelity, shock tolerance and backdriveability. **That is the SEA trade, stated as one inequality.** Or **notch it** — works, and fragile, because a notch is tuned to a frequency that moves with payload and temperature, and a mistuned notch is worse than none.

**Versus direct drive**, the point is not how much bandwidth the spring costs. It is that **the two architectures are limited by entirely different things.** Direct drive is limited by **implementation** — sampling, delay, the electrical pole, noise — and its gain margin under proportional control is **infinite**, with only phase margin eroding as gain rises. Series elastic is limited by **a mechanical property you deliberately bolted in**, its gain margin is finite and can start out negative before you tune anything, and **gain margin is the one that dies first.**

Honest summary: **an SEA trades bandwidth for force fidelity, and the exchange rate is two zeta-r.** That is the reason to choose it, not a criticism. A leg surviving heel strike wants the spring and does not need a hundred hertz to walk. An arm doing precise insertion wants the bandwidth and can avoid impacts. **What is not acceptable is choosing series elasticity and being surprised by the ceiling**, because the inequality is evaluable at the CAD stage.

One clean fact on delay: **a delay has unit gain at every frequency and contributes phase lag of minus omega T.** The magnitude does not move at all, so **delay is pure loss** — you pay margin and get nothing. At one kilohertz sampling, one sample costs about three point six degrees at a ten-hertz crossover and **thirty-six degrees at a hundred-hertz crossover.**

---

## Page fourteen — Nyquist

Same information as Bode, plotted as **one curve in the complex plane.**

**Why minus one?** The closed-loop poles are the roots of one plus L equals zero, so "is there a root on the imaginary axis" is exactly "does L pass through minus one". And minus one is **magnitude one at minus one hundred eighty degrees** — gain of one, half a cycle of lag. The same oscillation condition, stated as a point.

The criterion counts **encirclements**: closed-loop right-half poles equal clockwise encirclements of minus one plus open-loop right-half poles, and that must be zero.

**Vector margin — the shortest distance from the curve to minus one — is the honest one, because it is a single number that cannot be gamed.** A loop can have a comfortable gain margin *and* a comfortable phase margin and still pass very close to minus one on a diagonal, which both Bode numbers miss entirely.

**Bode quietly lies** when the open loop is already unstable — an arm past its balance point — when there are multiple crossings so "the" margin is ambiguous, or when the plant is non-minimum phase. Then you count encirclements.

---

## Page fifteen — zeros

Poles are what a system does on its own. **Zeros are what it refuses to pass.** Physically, **a zero is always two paths cancelling** — a frequency at which two routes arrive equal and opposite, so the output is zero no matter how hard you drive.

In the time domain, **a zero adds a scaled copy of the derivative of the zero-free response**: **y equals y-nought minus one over z, times y-nought-dot.**

For a **left-half-plane zero**, minus one over z is positive, so early on — when the response is rising steeply — that slug of slope *adds*. **Faster rise, more overshoot, and plus twenty dB per decade with up to plus ninety degrees of phase.** A zero is the exact mirror of a pole, which is why **a zero is the standard cure for a phase-margin problem — you are buying back phase the poles spent. A D term is a zero.** That is all a D term is.

For a **right-half-plane zero**, the slug arrives with a **minus** sign, so at the very start, when the slope is biggest and the output near nothing, the derivative term wins and **drags the output backwards.** The system moves the wrong way first. Formally, **non-minimum phase.** A bicycle — to turn left you steer right first. A boost converter, where asking for more volts makes them sag. **And a biped taking a step: the centre of mass must move the wrong way to unload the foot about to swing.**

**You cannot design this away, which is why you find it before writing a controller.** Feedback reacts to the output it sees; if the short-term direction is backwards from the long-term one, then **reacting fast means reacting wrongly, fast.** The rule of thumb is a hard bandwidth ceiling of roughly **z over two**, and it holds for **every** controller — PID, LQR, H-infinity, a neural network. **A property of the plant, not of your design.**

Three corrections. **A zero does not make a system unstable** — stability is about poles; a right-half *pole* is an instability, a right-half *zero* is a stable system that is awkward. **A plant's zeros do not move the plant's poles, but they decide where the closed-loop poles end up**, because closing the loop puts the numerator into the denominator — **inert open-loop, decisive closed-loop.** Turn the gain up and the closed-loop poles walk *toward* the zeros, which is what a root locus is. **And feedback does not move the zeros: closed-loop poles are yours to place, open-loop zeros are yours to live with.**

Where they come from: **PD gives a zero at minus K-p over K-d, designed whether you meant it or not.** **Lead** is a zero to lift phase plus a pole to stop the gain climbing — exactly **a D term with a filter on it, the only kind anyone ships.** And **a flexible link with the sensor not at the actuator gives a zero pair below the resonant pole pair — inherent, from geometry and stiffness.**

That last one is worth landing. **Collocated sensing — measuring at the actuator — interlaces poles and zeros and is very forgiving. Non-collocated sensing — measuring past the flexibility — is where the nasty zeros live.** If they ask why end-effector feedback is harder than joint feedback on a compliant arm, that is the answer.

And where people get hurt: **cancellation.** Putting a controller zero on a plant pole is fine for a well-damped, well-known, stable pole. **Never cancel a pole you are afraid of** — it is exact only if your model is exact. Cancel a lightly damped resonance and a five percent payload shift leaves it uncancelled with your full loop gain around it. Cancel an *unstable* pole and the mode is still there, still growing, merely invisible: **the transfer function is clean and the machine is not.**

---

## The ten sentences

One. **Order is the number of independent energy stores. Dampers never count.**

Two. **K-p is a spring and K-d is a damper; setting impedance gains is placing a pole pair, so you chose the overshoot whether you meant to or not.**

Three. **Omega-n is root K over J; zeta is the damping you have over the damping that would kill the oscillation. Double K alone and zeta falls by root two.**

Four. **Overshoot depends only on zeta; settling only on zeta omega-n, the real part. Separate knobs — which is why "it overshoots, so slow it down" is bad advice.**

Five. **For first order, the pole, the corner and the bandwidth are one number. Rise time times bandwidth is zero point three five.**

Six. **Open-loop bandwidth is crossover; closed-loop bandwidth is the minus three dB point; the second is about one and a half times the first.**

Seven. **Phase margin is damping: PM is about a hundred zeta, and you can run it either direction.**

Eight. **A plain plant cannot be destabilised by proportional feedback. Instability needs a third pole, a delay, or a resonance — something that supplies phase without attenuation.**

Nine. **A drivetrain resonance caps crossover at about two zeta-r times omega-res. An SEA trades bandwidth for force fidelity, and the exchange rate is two zeta-r.**

Ten. **A right-half-plane zero caps closed-loop bandwidth at about z over two for every controller that will ever exist, because it is a property of the plant.**

---

## The questions to rehearse

*How would you tune an impedance controller for a Spot arm joint?* Lead with omega-n and zeta rather than K and B. Name the drivetrain resonance as the ceiling, and say you would measure it with a tap test before touching a gain.

*Your arm oscillates when it touches a stiff surface. Debug it.* Contact raises the effective stiffness, which raises omega-n and **lowers** zeta — the same root-two trap. Contact also changes the plant, so a gain tuned in free space is a different loop in contact. Mention coupled stability and passivity.

*Why is there a limit to how stiff a virtual spring can be?* Torque limit, noise through the D term, drivetrain resonance, sampling and delay — then the passivity point.

*What is your loop bandwidth and how do you know?* Never give a number without saying which definition, and how you measured it.

*You have a harmonic drive with a torsional resonance. What do you do?* The inequality, then the three levers in order: add damping, because it is the linear term and the best value; stiffen and accept the trade; notch and accept the fragility.

*Why is end-effector feedback harder than joint feedback on a compliant arm?* Non-collocation, and the zeros it introduces.

*What breaks going from simulation to the real arm?* Coulomb friction and stiction, delay, unmodelled flexibility, and a payload that changes the plant.

That is pages two to fifteen. Sixteen and seventeen — making it stable, and lead, lag and notch — are the design half, where the root locus and the compensator recipes live.
