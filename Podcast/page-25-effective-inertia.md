# Page 25 — Effective Inertia

*Listening script. Roughly twenty minutes. Before any controller exists, mechanics has already decided how heavy your robot feels to whoever touches it.*

---

## The question this whole section answers

You grab the output shaft of a robot joint and you shake it. **How much mass do you feel?**

Not "how much does the robot weigh." How much **inertia is presented at the point of contact**. That number is the **effective inertia**, J-eff, and it influences acceleration and contact response. Safety, force estimation and tracking depend on it too — though never on it alone; speed, damping, compliance, sensing and feedback all get a vote.

And here is the claim the next four pages spend themselves proving: **three mechanical layouts give three completely different answers.** Same motor. Same limb. The only thing that changes is where the compliance sits.

---

## Four symbols, and the one people forget

**J-m** is the motor's rotor inertia — the spinning mass inside the motor itself. **J-L** is the limb or load inertia — the arm, leg or tool bolted to the output. **k** is spring stiffness, if there is a spring anywhere in the drivetrain. And **omega** is the frequency of the interaction — how fast the outside world is pushing on the joint.

**That last one is the one people forget, and it is the whole section in miniature.**

**Omega is not a property of the robot.** It is a property of what is *happening* to it. A slow lean and a sharp impact are the same joint at two different frequencies — and on the next two pages they will feel like two completely different machines.

So whenever someone quotes you an effective inertia, the honest question back is: **at what frequency?** For the layout on this page there is no answer to that question, because the number does not depend on it. That is exactly what makes it the baseline.

---

## Direct drive, derived

Direct drive: the motor is rigidly connected to the limb, ratio one to one. Quasi-direct drive — QDD — uses a low-ratio transmission, and there the rotor inertia must first be reflected as **N squared times J-m**, which we will come back to hard at the end.

The derivation is three lines and it is worth having them.

The motor's equation: **J-m theta-m double dot equals tau, minus J-L theta double dot.** Motor and limb are welded into one body, so they share one acceleration — theta-m equals theta. Collect the terms:

**Open bracket J-m plus J-L, close bracket, theta double dot, equals tau.**

Divide by the acceleration and read off what the world feels:

**J-eff equals J-m plus J-L.**

**And there is no omega anywhere in it.**

The answer is the same whether you lean on the joint for ten seconds or hit it in one millisecond. Hit a wall, move slowly — either way you feel the combined mass of motor *and* limb. On a plot of J-eff against frequency it is a **flat line**, and that flatness is the shape to remember, because the next two pages break it in opposite directions.

**Why this is dangerous.** High-torque direct drive is risky around people precisely because there is nothing between the rotor and the person. A fast impact drives the full J-m plus J-L into whatever it hit — and back into the motor's own magnets and bearings on the return trip.

**Unless** you pair it with compliance somewhere else. A soft skin, a compliant end-effector, a remote centre of compliance. Put the give somewhere in the chain and direct drive becomes acceptable again. The spring does not have to be in the actuator; it has to be *somewhere*.

---

## The same inertia, four different questions

J-eff shows up in four distinct calculations, and mixing them up is a standard way to get a wrong answer confidently.

**One — energy at a given speed.** E equals one half J-eff theta-dot squared. Doubling the effective inertia at the same joint speed **doubles the kinetic energy**. How much of that energy actually reaches a contact still depends on compliance and dissipation. And note theta-dot here is **joint angular velocity, not the excitation frequency omega** — two different things that both get written as rates.

**Two — torque and acceleration.** Net torque equals J-eff times angular acceleration. At the same net torque, doubling inertia **halves** acceleration; to keep the same acceleration you need **twice** the net torque. And motor torque has to cover friction, gravity and every other load on top. There is a loop hiding here: a larger motor may bring *more rotor inertia* with it, so sizing is a coupled problem, not a lookup.

**Three — the first-order connection.** For J-eff omega-dot plus b omega equals motor torque, with constant b and a torque step from rest, the time constant is **J-eff over b**. Doubling inertia doubles the time constant, doubles the ten-to-ninety rise time, and doubles the two-percent settling time — which is about four time constants. Initial acceleration halves. But **final speed, motor torque over b, does not change at all.** Worth saying out loud: that is a torque-to-speed model, and a final speed is not automatically a desired position.

**Four — the second-order connection.** For a position loop, J-eff theta double dot, plus total damping theta dot, plus total stiffness theta, equals the input. Natural frequency is **root of total stiffness over J-eff**; damping ratio is **total damping over two root of J-eff times total stiffness**. So changing inertia at fixed gains **changes both at once** — omega-n falls and zeta rises. This is the second-order page's root-two trap arriving from the other direction.

And keep natural frequency, bandwidth and settling time **distinct**. They are related, they are not interchangeable, and the first-order J-over-b rule is not a universal position-loop formula.

---

## Why real robots look the way they do

Inertia about a joint is **sum of m-i times d-i squared.** The distance is **squared**, so mass at the end of the linkage is punished quadratically.

Put a number on that. **A one-kilogram motor at the wrist costs a shoulder joint sixteen times more inertia than the same motor at a quarter of the reach.** Not sixteen percent. Sixteen times.

That single fact explains most of what robot arms look like.

**Proximal actuator placement.** Put the motors in the torso or the upper arm and transmit power outward — tendons and cables, as in 1X's Neo and in essentially every dexterous hand; or belts; or push-rods.

**Parallel and closed-chain mechanisms.** Delta robots and five-bar linkages exist almost entirely to keep actuator mass at the base. Differential wrists are the same idea again.

**Lightweight distal links.** Carbon fibre forearms, hollow sections — and then accepting the structural compliance that comes with them, which is a bill that arrives later as a resonance.

**And biology did all of this first.** Your calf muscles sit high on the shin and pull the foot through the Achilles tendon. There is almost no muscle mass in the foot itself. Evolution found the d-squared term a long time before we did.

---

## The number a datasheet will not give you

For motor selection, the quantity that matters is the **inertia match** — J-L over J-m, reflected through the gearing.

**A ratio of about one to three** is the classic servo sweet spot: best acceleration per amp, well damped, easy to tune.

**A ratio well above ten**, load dominating, and the motor struggles to control the load. Resonances show up. You need a gearbox, or a bigger motor.

**A ratio well below one**, rotor dominating, and you are mostly spending torque accelerating **your own rotor**. That is what over-gearing does to you, and it is the entire subject of the gearing page later in this block.

So J-eff is not only an *output* of the design. **It is the input to motor sizing.** Pick the topology first, compute J-eff, then choose the motor — in that order, because doing it the other way round means choosing a motor for a machine you have not designed yet.

---

## What control can do, and what it cannot

**What control can do.**

**Feedforward, or computed torque.** If you know the inertia matrix as a function of configuration, compute tau equals J of q, times desired acceleration, plus the Coriolis term, plus gravity — and apply it directly. The feedback loop then only has to correct *model error* instead of fighting the full inertia. **This is the single biggest win available and it costs nothing but a model.**

**Inertia shaping.** With force feedback you can make the joint *feel* lighter than it is — admittance control with a virtual mass below the real inertia.

**Input shaping and notch filters**, for the resonances that light distal links introduce.

**Now the important half — what control cannot do.**

Every one of those tricks works **only inside the loop bandwidth.** Above it, the physical inertia is exactly what the world feels, because **the controller has not noticed yet.**

And here is why that matters more than it sounds. **An impact is broadband.** A one-millisecond collision has energy out to hundreds of hertz — far above any joint control loop. So during the precise event that actually decides whether someone is hurt, your inertia-shaping law contributes **nothing**. Whatever J-eff the mechanics presents up there is what hits the person.

How far can inertia shaping be pushed? Rendering a virtual mass much below the real one **demands loop gain**, and loop gain plus delay is instability. A factor of **two to five** is realistic. A factor of a hundred is not.

**You cannot software your way out of a heavy rotor.** That sentence is the reason this block sits before the control paradigms rather than after them.

---

## Big low-inertia motor, versus small motor plus gearbox

Two ways to build the same joint. Both deliver forty newton-metres at the output. They are not remotely the same machine, and the arithmetic is worth hearing in full.

**Direct drive.** Rotor inertia **0.0040** kilogram metres squared — a big rotor. Gear ratio one to one, so the reflected rotor inertia is still 0.0040. Limb inertia 0.025. **Total J-eff: 0.029.**

**Small motor with a fifty-to-one gearbox.** Rotor inertia **0.00004** — a hundred times lighter. But reflected inertia is rotor times N squared, and N squared is **two thousand five hundred**. So 0.00004 times 2500 is **0.100**. Add the same 0.025 limb and you get **J-eff of 0.125.**

**Read that again.** The geared version has a rotor **a hundred times lighter** and still ends up presenting **more than four times the inertia** to the outside world — because the N-squared term beats the mass saving comfortably.

And that inertia arrives with company. The direct drive is **backdriveable** — push it and the rotor turns. The geared one is not; stiction may need twenty newtons before anything moves at all. The direct drive gives you **force sensing for free** from motor current. On the geared one, motor current tells you about the gearbox, not about the world.

There is a third option, and real machines use it: high-ratio gears **plus a torque sensor on the joint output**. KUKA's iiwa and Franka do exactly that. It recovers torque control without backdrivability, at considerable cost.

---

## Three bandwidths, and the bridge to the spring pages

Before leaving, separate three numbers that get confused constantly.

**Current loop:** ten to forty kilohertz, on both topologies. Electrical, and essentially free.

**Joint control loop:** one to four kilohertz. **This is your sample rate, not your bandwidth.**

**Usable force and impedance bandwidth:** this is where topologies diverge, and it is set by **mechanics**, not by the CPU. Direct drive or QDD: **fifty to a hundred hertz and up**, limited by link structural resonance, encoder noise and loop delay — nothing mechanical is filtering the force path. High-ratio geared: **ten to thirty hertz**, limited by friction nonlinearity, backlash and torsional windup of the flexspline — the gearbox is a low-pass filter you did not ask for, and worse, a *nonlinear* one. Series elastic: **ten to twenty hertz**, limited by the spring-load resonance.

**All three sit far below the one-kilohertz loop rate.** That is the answer to "we sample at one kilohertz, so why can't we react in one millisecond?" The sampling is not the constraint. **The mechanics is.**

Which sets up the last thing on the page, and the thing the next two pages are entirely built out of.

Both of those pages bolt a spring on and immediately start quoting a frequency for it. So be precise about where that frequency comes from, because **it is not a property of the spring.**

Ask a spring on its own what its bandwidth is and the question is meaningless — a spring produces torque k theta at any frequency you like, instantly, forever. Ask an inertia on its own and it is equally meaningless. **The frequency appears only when you ask which of the two wins**, and that has an exact answer: set **k theta equal to J omega squared theta**. The theta cancels — which is why the answer does not depend on how hard you push — and you are left with **omega equals root k over J.**

**Below that frequency the spring's torque is the larger and the thing behaves like a spring. Above it the inertial torque wins and it behaves like a mass.** That crossing *is* what "the bandwidth of the elastic element" means, and nothing more.

And here is the sentence that makes the next two pages different from each other. **That formula has a J in it, and which J depends on where you bolt the spring.**

Bolt it **in parallel** and the spring works against the whole rigid machine, so J is J-m plus J-L. **One frequency**, and it is simply the joint's new natural frequency.

Bolt it **in series** and the spring has a different inertia on each end, so it produces **three** frequencies — root k over J-L looking one way, root k over J-m looking the other, and root k over the reduced inertia for the two ends swinging against each other.

**Same spring. Same stiffness. One frequency or three, decided purely by which inertias the spring can see.** Every argument on the next three pages traces back to that.

And one number to carry with you, because the series page measures it rather than asserting it: the crossover you can actually achieve on a series elastic joint lands at about **0.6 times root k over J-L**, and that ratio holds across a hundred-fold range of stiffness. **The spring's frequency is not an analogy for the bandwidth. It is the bandwidth, times a constant near 0.6.**
