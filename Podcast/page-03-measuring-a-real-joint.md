# Page 3 — Measuring a Real Joint

*Listening script. Roughly twenty minutes. Every experiment, every dropdown option, every table row.*

---

This is page three, Measuring a Real Joint, and it exists because of a question that is easy to skip past: where do the numbers come from?

Every page after this one says things like "the time constant is J over b". Fine. But J and b are not printed on the side of the joint. So before any of that machinery means anything on real hardware, you need to know how you would actually go and get those numbers. That is this page.

The page opens with the point made bluntly. **Nobody looks these numbers up.**

You are handed an elbow. A motor, a gearbox, a shaft, a forearm. Its inertia is whatever the aluminium happens to weigh and wherever it happens to sit. Its friction is whatever the bearings and the seals do today. Its stiffness is whatever the harmonic drive and the shaft add up to. **Every one of those is measured**, and each one has a standard experiment that takes minutes.

---

## The three numbers, and where each one comes from

Let me read the table properly.

**J — inertia — units of kilogram metre squared.**

What it physically is: how much torque it takes to change the speed. And for a joint it is the link's own inertia about the joint axis **plus** the rotor's inertia multiplied by N squared, where N is the gear ratio. On a geared joint that second term usually dominates — which is a whole story on the gearing page later.

How you get it: CAD mass properties are the starting estimate, and they are usually ten to thirty percent wrong, because nobody models every fastener and cable. So you measure it. A **pendulum swing** test, or an **acceleration** test, or the regression at the bottom of this page.

**b — viscous friction — units of newton metre seconds.**

What it physically is: torque lost in proportion to speed. Oil shear, seals, windage. And it is not the whole story, which I will come back to in a moment because it is the trap on this page.

How you get it: a **constant-speed sweep**. Hold several different speeds, record the torque needed at each, and the slope of torque against speed is b. Or a **coast-down**.

**k — stiffness — units of newton metres per radian.**

What it physically is: how much the transmission and the structure wind up under load. Harmonic drives are springs. So are long shafts, belts, and thin links. If it can twist, it is a spring, and it has a stiffness.

How you get it: **static deflection** — lock the output, apply a known torque, measure the twist. Or a **tap test** — hit it and read the ringing frequency, since omega n equals the square root of k over J.

---

## The warning that catches everyone

Now the trap, and the page puts it in a warning box because it catches people constantly.

**Real friction is not b times omega.**

A real joint has **Coulomb friction** — a roughly constant torque that opposes motion regardless of speed — sitting on top of the viscous term. And on top of that it has **stiction**, which is larger still and only shows up at zero speed, when the thing is trying to break away from rest.

So the honest model is: friction torque equals b times omega, plus f c times the sign of omega.

That sign function is the problem. It is not linear. And if you fit only b, you will get a number that is wrong at every speed except the one you happened to fit at.

This is also the honest caveat about the whole first-order picture that the next pages build. Sign of omega is not a linear function, so a joint that is *modelled* as first order still has a dead zone near zero speed where it does something else entirely. The model is a good model. It is not the truth.

---

## The four experiments

Now the interactive. Four bench procedures, each showing what your data logger would display, complete with sensor noise that you can turn up and watch the estimates degrade — which is the honest part of the exercise. Underneath each one is the arithmetic you actually do.

Let me walk through all four.

### Experiment one — coast-down

**The procedure.** Spin the joint up to a comfortable speed, then **cut the drive current** and log the encoder while it coasts to a stop. Nothing is driving it, so the only thing acting is friction. That makes this the cleanest measurement on the bench — no torque constant, no current sensor calibration, no command scaling can contaminate it.

**The arithmetic.** With no input, J omega dot equals minus b omega. So omega decays exponentially, with a time constant tau equal to J over b.

Now the nice part. Plot the logarithm of omega against time, and it is a **straight line whose slope is the pole**. Fit that slope, invert it, and you have tau. That is the same picture as the log-axis widget on page six, and it is the practical reason that picture is worth knowing: on a log axis, exponential decay is a straight line, and fitting a straight line is something you can do reliably even with noisy data.

In the widget, with the default noise, the fit comes out at about six hundred and twenty-six milliseconds against a true value of six hundred and twenty-five. Two tenths of a percent error.

**The catch.** And this is important. This experiment gives you the *ratio* J over b, and nothing else. It cannot split them. To separate J from b you need one more experiment — which is exactly why nobody ever does only one.

### Experiment two — torque step

**The procedure.** Command a constant, known torque. On a motor that means a constant current, since torque equals K t times current. Then log the speed until it stops rising.

**The arithmetic.** Two readings come out of one trace.

The **final speed** gives you the friction directly. At steady state, the torque you applied is exactly balanced by b times omega — the fill equals the leak, to use the language of the next pages. So **b equals tau divided by omega steady state**.

The **sixty-three percent time** gives you the time constant. And since the time constant equals J over b, and you now know b, you get **J equals b times tau**. One experiment, both numbers.

In the widget: four newton metres applied, final speed around nine point nine radians per second, which gives b of about zero point four zero four against a true zero point four. And J comes out at zero point two four nine against a true zero point two five. Three tenths of a percent.

**The catch.** The b you get is contaminated by Coulomb friction, because at a single speed you cannot tell a constant torque loss from a proportional one. Both just make the joint slower.

The fix is the second plot on that panel. Repeat at several torques, and plot torque against steady speed. You get a straight line — and the **slope** is the real b, while the **intercept**, where the line hits the torque axis at zero speed, is **f c**, the Coulomb friction. That one plot separates the two, and it is a five-minute experiment.

### Experiment three — pendulum swing

**The procedure.** Switch the drive off so the joint is completely free. Hold the link out to one side, and let go. Log the encoder while it swings.

You need one thing first: the link's **mass and centre of mass**. A set of scales and a balance point, or CAD you trust. You need it because gravity is the spring in this experiment.

**The arithmetic.** A hanging link is a pendulum. J theta double dot, plus b theta dot, plus m g l sine theta, equals zero. For small swings, sine theta is approximately theta — and that is a mass-spring-damper with stiffness m g l.

So omega n equals the square root of m g l over J. Which means **timing the swings gives you J directly**. Count the period, do the arithmetic, done.

And the shrinking envelope gives you the damping. The ratio of successive peaks is called the **logarithmic decrement**, and it converts straight into zeta, the damping ratio, and then into b. The widget shows this on a log axis as the peak heights, and they fall on a straight line — same trick as the coast-down.

In the widget: period about two point three seconds, J comes out at zero point two five zero against a true zero point two five. Essentially exact.

**Why bother with this one at all?** Because it is the one experiment that measures J with the motor **switched off**. No torque constant, no current sensor, no gearbox efficiency can bias the answer. Everything else on this page goes through the motor and inherits whatever calibration error the motor has. This one does not.

### Experiment four — tap test

**The procedure.** Clamp the motor side. Hit the link with a soft mallet — an instrumented impact hammer if you are being careful — and log the encoder, or an accelerometer. This is called a **modal test**, and it is done exactly this way on real machines, from robot arms to bridges.

**The arithmetic.** The joint rings at its natural frequency. For a mass on a spring that is omega n equals the square root of k over J. You already know J from the swing test, so **k equals J times omega n squared**.

You get omega n either by counting the cycles per second off the trace directly, or by taking an FFT and reading the peak. The widget shows both: the ringing time trace with its decaying envelope, and the spectrum with a clear peak.

In the widget: it rings at about nine point five hertz, which gives k of nine hundred against a true nine hundred.

**Why this one matters most for control.** That ringing frequency is a **hard ceiling on your loop bandwidth**. Push the controller anywhere near it and you will excite it. Everything the tutor says later about notch filters, and about why gearboxes ruin transparency, is about this number.

And it is measured with a hammer, in about thirty seconds.

---

## How it is really done: one trajectory, all the parameters at once

Now the part that is genuinely how industry does it, and it rests on a property that is worth knowing by name.

Write the joint's equation of motion with every effect you believe in:

Tau equals J omega dot, plus b omega, plus f c times sign of omega, plus m g l sine theta.

That equation is **nonlinear in the motion**. There is a sign function and a sine function in there. You cannot use linear methods on the motion.

But look at it as an equation in the **parameters** — J, b, f c and m g l. Each one appears exactly once, multiplied by something you can measure, and added to the rest. Nothing is squared, nothing is inside a function, nothing multiplies anything else.

So it can be written as a row times a column. The row is: omega dot, omega, sign of omega, sine theta — all measured. The column is: J, b, f c, m g l — all unknown.

**That is the whole trick, and it is standard: robot dynamics are linear in the dynamic parameters.**

So here is what you do. Move the joint around while logging torque, position, speed and acceleration. Every single sample gives you one row of that equation. Stack ten thousand rows and solve the least-squares problem, and out come all four numbers at once. No special rig. No locked shafts. No separate experiments.

And for a whole arm the same thing holds, with a bigger row. Tau equals **Y** of q, q dot, q double dot, times **Theta** — where Y is called the **regressor** and Theta holds every mass, every centre of mass and every inertia in the robot. That is how every manipulator you have ever used was calibrated.

---

## And why the trajectory you drive matters more than the maths

Here is the second interactive, and it is the practical lesson.

Same joint, same regression, three different motions. And the number to watch is the **condition number**, which measures how well the data pins the answer down.

**Option one — rich excitation. A sum of sinusoids, both directions.**

The joint sweeps through a range of speeds and accelerations in both directions, so every column of the regressor carries independent information. The condition number comes out around twenty-five, which is small and healthy. Every parameter comes out close: J at zero point two five zero against zero point two five, b at zero point four zero one against zero point four, f c at zero point five nine nine against zero point six, m g l at two point zero zero zero against two point zero. And when you add noise, they degrade gracefully.

**This is what an excitation trajectory is for.** And designing one — usually a finite Fourier series, optimised specifically to minimise that condition number — is a standard step in commissioning a robot. It is a real job that real people do.

**Option two — slow single sine. Hardly any acceleration.**

There is barely any acceleration in this motion, so the omega dot column is small, and J is only weakly determined. The condition number jumps to over a hundred, and the J estimate comes out at zero point two one against a true zero point two five. Sixteen percent off — and it wanders as soon as you add noise, while b and gravity stay respectable.

This is the common real-world failure. The trajectory looked fine. The robot moved. The data logged. But it never asked the joint the question you needed answered.

**Option three — one constant speed. No acceleration at all.**

Omega dot is zero, so the inertia column is **identically zero**. The data contains literally no information about J whatsoever.

And it is worse than that. Sign of omega is also constant, because the joint never reverses, so the Coulomb column and the gravity column cannot be told apart either.

The condition number goes to infinity. J comes back as zero point zero zero zero. Coulomb friction comes back as zero point one eight against a true zero point six.

And here is the line worth carrying: **the solver still returns four confident-looking numbers, most of them meaningless.** Least squares never refuses to answer. It is your job to check whether the question was askable.

---

## What identification gives you, and what it does not

Four honest limits.

**J is not a constant on an arm.** The inertia the elbow motor feels depends on where the wrist is. Arm out, big inertia. Arm folded, small inertia. What you actually identify is the **inertia matrix**, M of q, a function of configuration. On a single joint this shows up as "the time constant changed when I extended the link", which is real and is not a measurement error.

**Gravity depends on configuration too.** M g l sine theta is zero straight down and maximal horizontal. That is exactly why the regressor carries a sine theta column.

**Friction is not stationary.** It changes with temperature, with load, with how long the joint has been running. And it has a stiction hump at zero speed that no linear fit will capture.

**Backlash and hysteresis are invisible to a linear fit**, and they will silently pollute your parameters if the trajectory crosses zero speed a lot.

And the rule that comes out of all four: **a model is only valid where you excited it.** Identify at one radian per second and the model will be wrong at fifty. Identify with the arm folded and it will be wrong with the arm extended.

That is not a flaw in the method. It is the reason robust control and gain scheduling exist, and the reason the nonlinear pages exist later on.

---

## Carrying forward

J, b and k are measurements, not constants handed down. They are what set the plant's poles, and therefore everything the next pages say about speed and settling.

And the next page answers the other half of the question: given that those numbers are welded into the hardware, how can a line of software possibly change what the joint does?

That is page four.
