# Page 19 — LQR & Optimal Control

*Listening script. Roughly twenty minutes. Stop naming pole locations you have no intuition for and name a price instead — what Q, R and P actually are, and the two worked problems.*

---

## The question pole placement cannot answer

The previous page gave you a complete method. Write down where you want the closed-loop poles, solve for K, done. It works, it is exact, and it runs out of road almost immediately.

Here is where. A trunkless biped has twelve states, so it has **twelve poles**. Where do you put them? "All at minus twenty"? Why minus twenty? Why all together? And why should the ankle and the hip want the same dynamics, when one carries the whole body and the other carries a thigh?

**Nobody has intuition for twelve pole locations.** But everybody has intuition for "I will accept two centimetres of error and I have forty newton-metres of torque."

**LQR is the machine that turns the second sentence into the first.** You choose how much to penalise state error and how much to penalise effort. It solves for K, and the poles come out the other end as a *consequence*. Both methods end at the same place — u equals minus K x — they differ entirely in what you are asked to specify.

One framing to keep hold of from the start: **the cost weights are preferences, not hard limits.** Nothing in LQR enforces a torque limit. You express that torque is expensive, and then you go and check whether the answer respected you.

---

## The cost functional, read as a running bill

The object being minimised is an integral from zero to infinity of two terms: **x transpose Q x, plus u transpose R u**, d t.

Read it as a bill. Every instant you are charged for two things: **how far off you are, and how hard you are pushing.** Integrate over all time and you have a single number attached to a controller. **The best controller is the one with the smallest bill.**

The quadratic form is not arbitrary. Squaring makes the penalty sign-blind — two centimetres left is as bad as two centimetres right. It punishes large errors disproportionately, so a big excursion costs far more than several small ones. And the reason it is actually used: **it is the one choice for which the whole problem has a closed-form solution.**

Written out for a two-state plant with a diagonal Q, the mystery evaporates entirely. The whole integrand is just **q-one-one times x-one squared, plus q-two-two times x-two squared, plus r times u squared.**

That is it. **Q and R are just weights, one per squared quantity.**

**Q** is n by n, positive semi-definite, and it is the price of state error. On a two-state plant, **q-one-one is the price of position squared and q-two-two is the price of velocity squared.** Big q-one-one means "I hate being off target." A **zero** on the diagonal means "I do not care about that state at all" — which is a legitimate and common choice, not a mistake.

**R** is m by m, positive definite, one entry per actuator, and it is the price of effort. Big R means "torque is expensive, be gentle." And R must be **strictly** positive, never zero: if effort were free the optimiser would use infinite gain, and the problem would have no solution at all.

Off-diagonal entries exist too, and they mean "I care about this *combination* of states." We will use exactly one of those later, and it is the interesting part of the page.

One more property worth knowing before you tune anything. **Only the ratio matters.** Multiply Q and R both by a thousand and K does not change — the same controller is still optimal, the bill is merely denominated in different units. So a common scale factor is a redundant degree of freedom. Every adjustment that actually does something is about the relative importance of the states to each other, and to the effort.

---

## The units problem, and Bryson's rule

Now, why naive Q and R behave so strangely in practice.

In the sum q-one-one x-one squared plus q-two-two x-two squared, **x-one is in metres and x-two is in metres per second.** So setting both weights to one does **not** mean "weight them equally." It means "one square metre of position error costs the same as one square metre-per-second of velocity error" — which is a statement about your choice of units and nothing else. Switch from metres to millimetres and those same two numbers now mean something a million times different.

**Bryson's rule removes the problem in one line.** Normalise each term by the largest value you are willing to tolerate:

**Q-i-i equals one over x-i-max squared. R-j-j equals one over u-j-max squared.**

Now every term is **dimensionless**, and equals exactly **one** when that variable sits at its reference scale. The cost has become "how many times over budget am I, summed up" — which is finally a comparison you can make across quantities with different units.

And after Bryson, tuning means scaling blocks by factors of ten, and **each factor of ten has a meaning**: "I care about this ten times more than I first said."

Worked, for a mass-spring-damper. You say: *I will accept two centimetres of position error, thirty centimetres per second of velocity, and I have ten newtons of force.* That gives Q as a diagonal matrix of **one over zero-point-zero-two squared, which is 2500**, and **one over zero-point-three squared, which is 11.1**. And R is **one over ten squared, which is 0.01**.

One caution, because this catches people. The ratio 2500 over 11.1 does **not** mean position is 225 times more important than velocity. Those two raw weights **have different units**. What the scales do is normalise the quantities so they are comparable at all. They remain soft preferences, and the ten-newton figure is a requirement you check afterwards — not a constraint the solver honours.

---

## The answer, and what P actually is

Two equations. The first is the **algebraic Riccati equation**:

**A transpose P, plus P A, minus P B R-inverse B transpose P, plus Q, equals zero.**

And then the gain falls straight out of it:

**K equals R-inverse B transpose P.**

The Riccati equation is **quadratic in P** — that is the minus-P-B-R-inverse-B-transpose-P term — which is why it has several solutions. Under the usual stabilisability and detectability assumptions you take the **stabilising, positive semi-definite** one. The tutor's solver finds it through the stable eigenvectors of the Hamiltonian matrix, which is how it is genuinely done in practice.

Now the part worth slowing down for, because **P is the most important matrix in this tutor.**

**P parameterises the optimal cost-to-go.** Start the system at some state x-nought, run the optimal controller forever, and add up the entire bill. The answer is:

**J star of x-nought equals x-nought transpose, P, x-nought.**

So **P converts "where you are" into "what the rest of your life will cost, assuming you play optimally from here."**

Read that sentence again with reinforcement learning vocabulary in mind, because this is the bridge the whole second half of the tutor walks across. **LQR minimises cost-to-go. RL maximises expected return.** They are the same object with a sign flip — *if* reward is the negative running cost, and the horizon and dynamics conventions match. Under those conditions the optimal return is **minus x-nought transpose P x-nought.**

Be precise about that, because it is easy to overclaim. **P alone is not the value function** — the value function is minus x transpose P x. And **solving a Riccati equation is not automatically value iteration.** What is genuinely true is that for this linear-quadratic problem the value function has a quadratic form, and substituting that form into the continuous-time optimality condition *gives you* the Riccati equation. That is a real connection to Bellman reasoning. It does not make every Riccati numerical solver a reinforcement learning algorithm.

One more honest note on robustness. For the ideal continuous-time model, full-state LQR has classical input-loop robustness results — under their stated assumptions. Those are **not** universal margins for every sensor loop and every sampled implementation. The moment you add an estimator, delay, filters or saturation, you go and check the actual loop.

---

## Worked problem one — returning a carriage to its station

A one-kilogram carriage on a spring, displaced two centimetres and released from rest. Target is zero. The question: can we bring it within plus or minus **0.4 millimetres in 0.40 seconds** and keep it there, while requesting no more than **ten newtons**?

The dynamics are q double dot, plus zero-point-six q dot, plus twenty q, equals u. State is position and velocity. We want the two gains in u equals minus k-one q, minus k-two q dot.

Three attempts, and they are the design loop itself — **not iterations inside the solver.**

**Attempt one, gentle.** Effort scale set low, so force is expensive. The solver returns k-one of **82**, k-two of **13.8**. Peak force **1.6 newtons** — beautifully economical. Recovery time: **0.589 seconds** against a target of 0.4. **Fails on time.**

**Attempt two, fast.** Tighten the position scale to ten millimetres. Now k-one is **980**, k-two is **54.8**. Recovery is **0.141 seconds** — comfortably inside. But peak force is **19.6 newtons**, against ten available. **Fails on force.** And note the solver did not warn you; it gave you exactly what you asked for, because you told it force was cheap.

**Attempt three, balanced.** Position scale back to twenty millimetres, effort scale at ten newtons. k-one is **480**, k-two is **44.9**. Recovery **0.270 seconds** — passes. Peak force **9.6 newtons** — passes, with a sliver to spare. Closed-loop damping ratio comes out at **1.02**, essentially critically damped.

Two things to take from that sequence.

First, **look at the cost numbers**: 0.146, then 0.222, then 0.0911. The balanced design has the *lowest* J star — but that is not why it is the right answer, and this is a trap. **J star is only comparable between controllers that share the same Q and R.** Attempt one and attempt three were optimising *different objectives*, so ranking them by their own bills is meaningless. J star tells you how well a controller serves the objective you gave it. It does not tell you whether you gave it a good objective.

Second, notice what you never did. **You never chose a pole location.** The pole plot in that widget is labelled "nobody placed these" for exactly that reason — the poles are an output, a consequence of a price list.

---

## Worked problem two — a spring-coupled joint, and the one off-diagonal term

Now four states, and this is where Q stops being an abstraction, because **each diagonal entry is a sentence about the machine.**

A series elastic joint: motor inertia 0.02, load 0.25 kilogram metres squared, spring 400 newton-metres per radian. Motor and load start together at 0.20 radians, at rest. Bring the load within 0.004 radians of zero by 0.25 seconds, keep spring deflection under three degrees, and keep motor torque under seventy newton-metres.

The four weights, in plain words. **q-one-one on motor angle** — "the motor must return to its commanded position." Usually the one you care *least* about; nobody is looking at the rotor. **q-two-two on motor speed** — "do not let the rotor whip about," mostly a smoothness term. **q-three-three on load angle** — "the output must be where I said." **This is the one the task cares about**, and it is the state furthest from the actuator. **q-four-four on load speed** — "do not let the output oscillate," and this is what actually damps the resonance.

And then the fifth, which is the interesting one. **q-delta, on motor angle minus load angle — the spring deflection.** Since deflection times k *is* torque, **this is literally a penalty on output torque.** It is an off-diagonal term in Q, and it is the one non-diagonal entry worth knowing how to build.

The construction is worth memorising, because it generalises. To penalise any linear combination **c transpose x**, add **c times c transpose** to Q, with a weight. Here c is the vector one, zero, minus one, zero — and c c transpose times q-delta gives you exactly q-delta times motor-angle-minus-load-angle, squared. **That is how you say "I care about this relationship between states" rather than about the states individually** — the same move that turns a position cost into a tracking-error cost.

The three attempts again.

**Baseline.** Load recovery **0.412 seconds** against 0.25 — too slow. Deflection 2.8 degrees, torque 20 newton-metres, both comfortable. **Fails on time.**

**Faster.** Raise the load-angle weight by a factor of ten. Recovery drops to **0.143 seconds** — passes. But deflection jumps to **7.8 degrees**, well past the three-degree limit. **You bought speed by winding the spring up.** Which makes physical sense: the only way the motor can hurry the load is through the spring, so hurrying means bending.

**Add spring protection.** Keep the fast load-angle weight, and now switch on q-delta. Recovery **0.174 seconds** — still passes. Deflection back down to **2.9 degrees** — passes. Torque 63 newton-metres, inside seventy.

**That third result is the whole point of the page.** You did not retune by hand, you did not add a filter, and you did not go back to choosing poles. **You added one sentence to the price list** — "bending the spring is expensive" — and the optimiser rebalanced all four gains to honour it. Notice the fastest closed-loop pole moved from minus thirty to minus 128; the controller reorganised itself completely, and you never touched a gain.

---

## Pole placement versus LQR, and LQI

**Pole placement:** specify the dynamic response you want, solve for K. Right when the pole locations *themselves* are your requirement.

**LQR:** specify state and effort weights, solve for K, then inspect the response you got. Right when you are balancing several states and inputs against each other, which is nearly always on a real machine.

Both need a good model and access to the states. **Neither enforces actuator limits.** And for LQR, being optimal for an ideal cost is not a universal robustness guarantee — check tracking, disturbances, saturation and the implemented loop either way.

One extension, because it is the same trick PID uses. An unknown constant load leaves a steady offset. **LQI** adds a state whose derivative is the error — an integrator — augments the model, and runs ordinary LQR on the bigger system. The extra diagonal entry in Q is **the price of accumulated error**, and the extra column of K is an integral gain. Steady-state error goes to zero for exactly the reason it does in PI control: there is now a pole at the origin inside the loop. The difference is that the gain came out of the same optimisation as all the others, rather than a separate tuning session. And everything true of integral action stays true — **it still winds up, and it still needs anti-windup. Optimality does not repeal actuator limits.**

---

## Carry forward — three different objects

Keep these three apart and the page has done its job.

**You choose Q and R** — what matters. **The solver returns K** — what action to take. **And it returns P** — how much optimal cost remains. For the same model and objective, starting from x-nought costs x-nought transpose P x-nought.

The reinforcement learning pages later draw the same distinction between a **policy** and a **value function**. With reward equal to negative running cost, and matching conventions, the optimal return is minus x transpose P x. **P alone is not the value function, and solving Riccati is not value iteration** — but the shape of the argument is identical, and that is not a coincidence.

And the question the next page asks: **all of this assumed you knew every state.** On the spring joint that meant four measurements including load velocity, which you very likely do not have. Observers estimate what you cannot measure, from a model and the sensor history — and changing how the states are obtained means checking the implemented loop all over again.
