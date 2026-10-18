# Page 115 — Configuration Space and Degrees of Freedom

*Listening script. Roughly twenty-five minutes. How many numbers describe a robot, what shape the space of those numbers has, and — the part most courses skip — what you actually do with that information.*

---

## The question

**What is the smallest list of numbers that tells you exactly how the whole robot is posed?**

For a two-motor arm, it is two angles. Give me theta one and theta two and I can draw every point of the arm. The length of that list is the **degrees of freedom**, DOF. And the set of every possible list is the **configuration space**, the C-space.

Hold one picture in your head for the whole episode: **the C-space is a map, and one point on the map is one complete pose of the robot.** As the robot moves, the point slides across the map. Planning, kinematics and dynamics all happen on this map.

The episode asks three questions about it. **How many** numbers — the dimension. **What shape** is the map — its topology. **Which numbers** do we write a point with — its representation. And after each one, the question you are entitled to ask: **so what?**

---

## So what, before anything else

Here is the honest answer up front, because otherwise this page sounds like vocabulary for its own sake.

The goal of the whole block is the equation **tau equals M of q, q double dot, plus c, plus g** — and the controllers built on it. Each idea on this page answers one question that equation, or the code around it, cannot avoid.

**Degrees of freedom** answers "how many numbers are in q?" That sets the size of everything. q has n entries. M is n by n. The Jacobian has n columns. It tells you how many motors fully control the robot, and whether the robot is redundant for a task.

**Topology** answers "does the space wrap round, have walls, or have holes?" That decides how you subtract angles in a PID loop, how a planner measures distance, and whether a joint limit is a wall or a seam.

**Representation** answers "which numbers do I store so nothing explodes?" The answer for arms turns out to be: **joint angles for the joints, a rotation matrix for the hand's orientation.** That single sentence is why page 117 is about rotation matrices.

Think of the block as a jigsaw. DOF is how many pieces. Topology is the rules for combining them. Representation is which pieces won't break when you handle them. Now the details.

---

## Counting freedoms: Grübler's formula

**DOF equals m times, N minus one minus J, plus the sum of f-i.**

That looks opaque, so count it like a budget instead.

A loose body sliding on a table can move three ways: slide in x, slide in y, spin. So in the plane, **m equals three**. A loose body in space can move six ways — three slides, three spins — so in space **m equals six**.

N counts the links, **including the ground**. The ground never moves, so you have N minus one moving bodies, and m times N minus one freedoms to start with.

Each joint then takes some away. A hinge in the plane leaves only one of the three freedoms between the two bodies it connects, so it removes **m minus f**, which is two. Revolute and prismatic joints have f equals one, a universal joint two, a ball joint three.

Freedoms left: m times N minus one, minus the sum of m minus f-i. Rearrange, and you have Grübler.

**Check it by hand.** Planar three-R arm: four links counting ground, three hinges. Three times, four minus one minus three, is zero; plus three. **Three DOF.** Four-bar linkage: four links, four hinges. Three times, four minus one minus four, is minus three; plus four. **One DOF.** Closing the loop cost two freedoms.

And the pattern to notice: **an open chain — an ordinary arm — has as many DOF as joints**, because nothing ties the end down. **A closed chain has fewer**, because the loop forces the joints to agree with each other.

One caveat. The formula assumes the joint constraints are independent. Special geometry — parallel links, the Delta robot's parallelograms — can make it lie. The Delta robot gives nine by Grübler, but six of those are idle spins of the rods about their own axes; the platform itself has three. The true answer is the rank of the constraint matrix, which is next page's subject.

---

## Shape: topology, not just dimension

Two numbers give a two-dimensional map. But a two-dimensional map can have many shapes.

**A plane and the surface of a sphere are both two-dimensional. But the sphere wraps round on itself, and the plane does not.**

The word for shape, here, is topology. Two spaces have the same topology if one can be smoothly stretched and bent into the other **without cutting or gluing**. The classic example: the surface of a doughnut — a torus — can be squashed into a coffee mug. The doughnut's hole becomes the handle's hole. So to a topologist, the mug and the doughnut are the same shape. Neither can become a flat plane without cutting.

The easiest way to think about topology: **it is the shape you could feel with your eyes closed.** Does it go on forever? Does it have edges you bump into? Does walking straight bring you back to where you started? Is there a hole through it?

And the crucial point: **topology is a fact about the robot. It does not change with how you choose to put numbers on it.**

---

## The shapes, built from joints — not memorised

You might ask: do I have to memorise that this system is a torus and that one is a cylinder? **No. You build the shape from the joints.**

A revolute joint with no limits: turn it a full circle and you are back where you started. **A circle, S-one.**

A revolute joint *with* limits: it hits a wall at each end. **A closed interval.**

A prismatic joint — a slider — with no stops: **a line.** With stops: **an interval.**

A pointing direction, like a spherical pendulum or a camera that only cares where it points: **a sphere, S-two.**

A full three-dimensional orientation — a hand, a drone: **SO-three**, which we meet properly on page 117.

And then the one rule: **independent parts multiply.** If the parts don't affect each other, the C-space is the product of their C-spaces — pick one point in each, and you have a configuration.

So a two-R arm with free joints is circle times circle. **And circle times circle is a torus.** Here is why: put theta one on the horizontal axis of a square, theta two on the vertical. Turning theta one by 360 degrees gives the same arm, so the right edge is the same place as the left edge — glue them, and you have a tube. Top equals bottom too — glue those, and the tube closes into a doughnut.

A knob that both turns and slides is circle times line: **a cylinder.** A six-R arm with no limits is a six-torus. The same arm with joint limits is a six-dimensional box. A mobile base carrying it is the plane, times a circle for the heading, times that arm. You read all of this off the robot in seconds.

**One clarification, because it trips people up. The spherical pendulum's C-space is the *surface* of a sphere, not the solid ball.** The rod has a fixed length, so the bob is always exactly L from the pivot. If the rod could telescope, the bob could fill the solid ball, and the C-space would be three-dimensional.

---

## Representation: the numbers we write down

Topology is the shape. **Representation is the numbers we choose to label points on it.** And that choice involves arbitrary decisions.

On a flat plane, you choose an origin and two perpendicular axes, and every point is a pair x, y. Velocity is just x dot, y dot. Nothing strange. That is what we are used to — and it only works this simply because the space is flat.

On a curved space, there are two options.

**Explicit parametrisation**: use the minimum number of coordinates — as many as the dimension. For the sphere: latitude and longitude, two numbers.

**Implicit representation**: treat the space as sitting inside a bigger flat space, use more coordinates, and add constraints. For the sphere: x, y, z, three numbers, with the rule x squared plus y squared plus z squared equals one. **Three numbers minus one rule equals two degrees of freedom.**

The same pattern for orientation. Explicit: three Euler angles, roll, pitch, yaw. Implicit: a rotation matrix, nine numbers, with R transpose R equals the identity — six independent rules — and determinant plus one. **Nine minus six equals three degrees of freedom.**

So the DOF is always: **numbers, minus independent constraints.**

---

## "The numbers misbehave" — what that actually means

Here is where the page earns its keep. When the shape wraps around but the numbers live on a flat sheet, **somewhere the numbers must misbehave even though the robot moves smoothly.** And there are exactly two ways they misbehave. They are not equally bad.

**The first is a jump, at a seam.** Take a free-spinning joint. Write its angle as a number from zero to 360. Turn it smoothly from 359 degrees to 1 degree. The joint moved two degrees. The number went from 359 to 1 — it teleported. The robot did nothing dramatic; the number did.

On the two-R arm, that seam runs along all four edges of the square: drive theta one past 360 and the point on the map leaps from the right edge to the left.

**The second is a blow-up, at a singularity.** Take latitude and longitude. Walk east at a steady one metre per second around a circle of constant latitude. Near the equator, your longitude changes slowly. Near the North Pole, the circle is tiny, so the same walking speed spins your longitude round very fast. **The longitude rate is v over R cos phi — and as you approach the pole, cos phi goes to zero and the rate goes to infinity.** At the pole itself, longitude means nothing at all. And step over the pole and longitude jumps by 180 degrees.

Meanwhile, x, y, z — the implicit coordinates — change at exactly your walking speed, everywhere. **The sphere looks the same at the pole as at the equator. The problem is only in the map.**

---

## So what? The long-way-round bug

Now the practical consequence of a jump. A joint sits at **350 degrees**. You want it at **10 degrees**. A P controller drives it with the error.

The naive error is target minus current: 10 minus 350. **Minus 340 degrees.** So the controller swings the arm almost all the way round the other way — slower, and through whatever is in the way.

The wrapped error respects the circle: take the difference, add 180, take it modulo 360, subtract 180. **Plus 20 degrees.** The short way.

Averaging breaks the same way. Two sensor readings: 350 and 10. Their average on the number line is **180 degrees — pointing exactly the wrong way.** The true average on the circle is zero.

Nothing about the joint changed. **Only whether the code knew it was on a circle.** That is what "the C-space is a torus" buys you. Every angle *difference* — PID errors, planner distances, interpolated paths — has to be wrapped into minus 180 to plus 180. And a grid planner on the torus has to connect the right column to the left, or it misses every short path through the seam.

And the mirror image: **a joint with limits is an interval, not a circle.** There, the long way round is the *only* way, and you must *not* wrap. The ends are real walls; the controller has to slow down before them, not teleport through.

---

## So what? Jumps you can patch, blow-ups you cannot

Here is the recipe that turns all of this into decisions.

**A jump is cheap to fix**: wrap your differences. That is bookkeeping. It works because on a circle, one degree of joint motion is always one degree of the number — everywhere. The speed scale never changes. So a circle only ever jumps; it never blows up.

**A blow-up cannot be fixed by bookkeeping.** When a finite physical speed demands an infinite coordinate rate, a controller that thinks in those coordinates asks for infinite motor speed. That is gimbal lock: a wrist near pitch 90 degrees asking for huge joint speeds to make a small turn. The only fix is to change coordinates, or go implicit.

And the reason you cannot just be cleverer with two numbers on a sphere: **it is a theorem that no pair of numbers covers the whole sphere smoothly.** Same for three numbers on SO-three. Every explicit chart has a bad spot somewhere.

So the decision rule has three cases.

**If your C-space is made only of lines, intervals and circles — use explicit coordinates and wrap the angles.** That covers every serial arm's joint vector. The q in M of q, q double dot, is just the plain joint angles.

**If it contains a sphere or an orientation — use implicit.** A unit vector, a rotation matrix, or a quaternion. Show Euler angles to humans, but never compute with them near their singularity.

**If it contains a closed loop — use implicit.** Keep all the joint angles and write the loop-closure equations. That is the next page.

And implicit is not "always better." It costs extra numbers, and you have to keep the constraints true — renormalise R or the quaternion as numerical error creeps in. **Use it only where explicit would blow up, or where explicit is too hard to write down.**

---

## Velocities are not coordinate rates

One last convention from the book. Because configurations are stored implicitly, velocities are **not** the time derivatives of coordinates.

Angular velocity is a three-vector omega, with R dot equals omega-bracket R. Not the nine numbers of R dot. **Not Euler-angle rates.** And the Jacobian, on page 120, maps joint rates to a *twist* — a physical velocity — not to the rates of some coordinates.

That is the same lesson again: physical speed is well-behaved everywhere; the rates of a particular set of numbers are not.

---

## Interview question

**"How many DOF does a rigid body in space have, and why can't you represent its orientation with three numbers everywhere?"**

Six: three for position, three for orientation. **SO-three is a three-dimensional space that cannot be laid flat onto any piece of ordinary three-dimensional space**, so every three-parameter chart — ZYX Euler, roll-pitch-yaw — has a singularity somewhere. For ZYX it is pitch at plus or minus 90 degrees. Compute with rotation matrices or unit quaternions. Use three-number exponential coordinates only locally.

---

## Carry forward

**One.** The C-space is a map; one point is one whole pose. Its dimension is the DOF: freedoms of the bodies minus constraints of the joints.

**Two.** Build its shape from the joints. Free revolute: circle. Limited joint: interval. Slider: line. Direction: sphere. Orientation: SO-three. Independent parts multiply.

**Three.** Numbers misbehave in two ways. **Jumps** at seams — fix with wrapping. **Blow-ups** at singularities — fix by changing representation.

**Four.** For arms: **joints explicitly by their angles, wrapped; the hand's orientation implicitly by R.**

Next page: the rules that cut the C-space down — and the rules that only restrict which way you can move.
