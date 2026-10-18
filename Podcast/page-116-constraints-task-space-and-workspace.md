# Page 116 — Constraints, Task Space and Workspace

*Listening script. Roughly twenty-five minutes. What g of q equals zero means physically, why we immediately differentiate it, and where every piece gets used later.*

---

## The question

A constraint is a rule the robot must always obey. There are two kinds, and the whole page is about the difference.

**Rules about where it can be.** "The end of this loop stays bolted to the ground." These are **holonomic** constraints. They remove dimensions from the C-space.

**Rules about which way it can move right now.** "A wheel cannot skid sideways." These are **nonholonomic**. They do *not* shrink the C-space. They only remove directions of motion at each instant.

The second half of the page separates three spaces people constantly mix up: **C-space, task space and workspace.**

---

## Holonomic: the equation, and what it means

The holonomic constraint is written **g of q equals zero.** And the velocity version is written **partial g by partial q, times q dot, equals A of q times q dot, equals zero.**

On the page those two lines sit next to each other, and it is very easy to read them, nod, and have no idea what they are for. So take the smallest example that contains every piece.

**A bead threaded on a circular hoop of radius one.**

Describe the bead with two numbers, q equals x, y. Add one rule: stay on the hoop. That is **g of q equals x squared plus y squared minus one, equals zero.** Two numbers, one rule, so the C-space has dimension two minus one: **one.** The bead can only go round.

---

## Step one: g is a gap meter

**g of q measures how badly the rule is broken.** For the bead: g greater than zero means you are outside the hoop. g less than zero, inside. g equals zero, exactly on it.

So "g of q equals zero" is nothing more mysterious than **"the gap is zero."**

For a four-bar linkage — the real example from the video — g has three entries. Walk around the loop, link by link, adding up where you end. **The first entry is the x-gap between where you ended and where you started. The second is the y-gap. The third is the angle gap** — whether you are facing the same way you started. A loop that is physically pinned together has all three gaps at zero.

Four joint angles, three rules: **four minus three equals one degree of freedom.** Which matches Grübler.

---

## Step two: why differentiate?

If the gap is zero at every instant, **it cannot be changing.** So its time derivative is zero too.

And by the chain rule, the time derivative of g is: **partial g by partial x, times x dot, plus partial g by partial y, times y dot.** Stack the partials into a row and you get **A of q, times q dot.**

**That is all A of q, q dot equals zero is: the rate of change of the gap, set to zero.**

For the bead, A is the row **two x, two y.** So the velocity rule is two x x dot plus two y y dot equals zero.

---

## Step three: what the partial derivatives mean

**Entry j of row i of A is: how fast gap i opens, per unit speed of coordinate j, if only coordinate j moves.**

For the bead, the row is two x, two y — which points **straight outward from the centre of the hoop.** Moving straight outward opens the gap fastest.

So here is the picture to keep. **A row of A, drawn as an arrow, points across the constraint. It is the forbidden direction.**

---

## Step four: the null space

A of q, q dot equals zero says: **the velocity has no component along any forbidden direction.**

The set of all velocities that pass — every q dot with A q dot equal to zero — is called the **null space of A**. For the bead, it is the line tangent to the hoop. Those are exactly the velocities that slide the bead *along* the hoop.

And its size is the DOF: **n minus the rank of A.** Two minus one, one.

So when the four-bar lab shows you "theta dot, with theta-one dot equal to one radian per second — the null space of A," it is showing you **the one direction in four-dimensional joint-velocity space that the mechanism can actually move in.** Every allowed motion is a multiple of that vector.

---

## The subtle point: it is a rule for this instant

In the lab you can propose a velocity and drive the bead along it in a straight line, while tracking the gap.

Point the velocity across the hoop, and the gap starts changing immediately: its slope at the start is exactly A times q dot. **That is literally what the derivative means.**

Now point the velocity along the tangent, so A q dot is zero. The slope at the start is zero. **But a straight line along the tangent still drifts off the circle** — the gap grows like distance squared.

That is the point. **A q dot equals zero is a rule for this instant.** The bead must re-choose a tangent velocity at every instant, and that is how it ends up following the curve.

---

## Physically: the forbidden direction is where the hoop pushes

The red arrow — the row of A — is also **the direction in which the hoop pushes on the bead.** The hoop can push outward or inward. It cannot push along itself.

And a push across the hoop can never speed up or slow down a motion along it. **So the hoop does no work.**

Write that in symbols and you have one of the most useful lines in the block. The constraint force is **A transpose lambda**, where lambda is how hard the constraint pushes. Its power is **q dot transpose, A transpose lambda — which equals, A q dot, transpose, lambda — which is zero**, because A q dot is zero.

Page 131 uses exactly this. A constrained robot obeys **M q double dot plus c plus g, equals tau, plus A transpose lambda.** The rows of A are the directions the constraint pushes. Lambda is the contact force.

---

## So why turn a position rule into a velocity rule at all?

Three reasons.

**One — it is linear.** g is full of sines and cosines of q. A of q, q dot is a plain matrix times a vector. Linear means linear algebra: rank, null space, solve, least squares. And every later page — Jacobian, dynamics, control — works with velocities and is linear in them. So this is the form they can consume.

**Two — one form covers both kinds.** As we are about to see, the car's no-skid rule exists *only* as A of q, q dot equals zero. There is no g behind it. Writing the four-bar's rule the same way lets one toolkit handle both. **"Pfaffian" is just the name for that shape: something times q dot equals zero.**

**Three — dynamics needs it.** That is the A transpose lambda term from a minute ago.

And for the same reason, holonomic constraints are sometimes called **integrable**: their velocity form is the derivative of a position rule, so you can integrate backwards to recover it.

---

## The four-bar, and what a designer reads off it

For closed chains, implicit is usually easier than explicit. Grübler says the four-bar has one DOF, so one number should do — but writing the other three angles as formulas of the crank angle is messy and has subtle singularities. So keep all four angles and impose g of theta equals zero.

The lab lets you pick three linkages, and each one tells a designer something concrete.

**Crank-rocker — a Grashof linkage.** The shortest link turns all the way round. That means a motor spinning round and round at joint one becomes a back-and-forth swing at the output. **Windscreen wipers. Oil pumpjacks.**

**Double-rocker — non-Grashof.** No link turns fully; the crank swings between two limits. **So you cannot drive it with a continuously spinning motor at joint one.** The crank hits its limits.

**Parallelogram.** At zero and 180 degrees all four links line up, and the mechanism can switch from parallelogram to anti-parallelogram. The C-space is two loops touching at those points.

**The assembly mode** — elbow one way or the other — is fixed when you build it. In the crank-rocker the C-space is two separate loops, and turning the crank never takes you from one to the other. The other loop is a different machine made of the same parts.

**The null-space vector is the gear ratio.** Theta-four dot, per one radian per second of crank, is — up to sign — how fast the output rocker swings relative to the ground. Power in equals power out, tau-one theta-one-dot equals tau-four theta-four-dot, so the torque ratio is the inverse. **That is how you size the motor.**

**And the smallest singular value of A is a warning light.** As it falls to zero, the gear ratio blows up: the crank alone stops deciding the motion — a dead point — or the mechanism can flip branch. Designers keep the working range away from those poses. Page 124 calls them actuator singularities.

---

## Nonholonomic: the car

Chassis on a plane. Configuration **q equals phi, x, y**: heading phi, and the point midway between the rear wheels.

Drive forward at speed v, and the rear point moves along the heading: **x dot equals v cos phi, y dot equals v sin phi.** Eliminate v and you get **x dot sin phi minus y dot cos phi equals zero.** As a row: **zero, sine phi, minus cosine phi, times phi dot, x dot, y dot, equals zero.**

Read it physically: **that row, dotted with the velocity, is the car's sideways skid speed.** The rule says: no skidding.

Same Pfaffian shape as the four-bar. **But there is no g of q whose derivative this is.** It is nonholonomic. It removes one direction of *velocity* — sideways — without removing any dimension of *configuration*.

The proof is parallel parking. Forward-left, forward-right, reverse-left, reverse-right. **Every instant obeys the no-skid rule** — the residual in the lab stays at zero the whole time. And yet the net result is a pure sideways shift: x back to zero, heading back to zero, y not zero.

So the car still needs three numbers to describe it — the C-space is still three-dimensional — but at any instant it has only **two velocity choices: drive and steer.** Every pose is reachable, but only by indirect manoeuvres.

And a robot can have both kinds at once. Treat the chassis as a rigid body in space: six-dimensional. Three holonomic constraints keep it on the floor — height zero, no roll, no pitch — leaving three. Then one nonholonomic constraint removes the sideways velocity. **Two velocity freedoms in a three-dimensional C-space.**

---

## Where each piece is used later

Put the whole page into one table you can say out loud.

**g of q equals zero** tells you which poses exist at all. Used in closed-chain inverse kinematics and assembly modes, page 124, and for a hand held against a wall, page 131.

**A equals partial g by partial q** tells you how fast each gap opens per joint speed, and which way the constraint pushes. Used for constraint and contact forces, A transpose lambda, page 131.

**The null space of A** is every velocity the mechanism can actually make. Used to get the speeds of passive joints when the motors turn, page 124 — and it is the same idea as the Jacobian null space of a redundant arm, page 123.

**A rank drop** is a singular pose: the mechanism gains a freedom, locks, or flips. Page 124.

**A q dot equals zero with no g behind it** is nonholonomic. Car and differential-drive planning and control, pages 134 and 139.

**The puzzle so far, in order.** Page 115: q is the list of joint numbers, and you know what shape the space of q is. This page: some q's are not allowed — g of q equals zero throws them out — and at each allowed q, some velocities are not allowed — A q dot equals zero throws them out. **The null space of A is what is left: the motions the robot can really make.** Later, the Jacobian maps those allowed velocities to hand velocity, and the dynamics say what torques produce a given acceleration — plus the constraint force A transpose lambda that keeps the rule true.

---

## Three spaces people confuse

**C-space**: every configuration of the **robot** — every joint value. Depends on the robot only. Two-R arm: a torus.

**Task space**: a space in which the **task** is naturally written. Depends on the task only — **you don't need to know the robot.** A marker tip on a whiteboard: the plane, two numbers. Full position and orientation of a part: six numbers. Pointing a laser: a sphere of directions, two numbers. Welding with a torch that is symmetric about its own axis: a point and a direction, five numbers.

**Workspace**: the end-effector configurations the robot **can reach**. Depends on the robot only — no task involved.

If the robot has more joints than the task has numbers, it is **redundant** for that task, and the spare freedoms can be used for something else: avoiding an obstacle, staying away from joint limits. Put a fingertip on the desk and move your elbow — that's redundancy. **And redundancy depends on the task.** The same six-R arm is redundant by four for writing on a board, by one for welding, and exactly enough for full six-dimensional pose.

---

## Workspace, with numbers

A two-R arm with full rotation reaches an annulus: inner radius **L-one minus L-two**, in absolute value, and outer radius **L-one plus L-two.** Make L-two longer than L-one and a hole opens — the hand cannot fold back to the base.

**Joint limits change the shape.** The video's example: joints limited to 180 and 150 degrees. The full annulus becomes a crescent.

The **dexterous workspace** is the set of positions reachable at *every* orientation. For a planar three-R arm with a wrist link L-three, the hand must sit L-three in front of the wrist, so the reachable set for one fixed yaw is the two-R annulus shifted by L-three. Reachable at every yaw means inside every shifted ring at once: **an annulus from L-one minus L-two plus L-three, out to L-one plus L-two minus L-three.** Make the wrist long enough and the dexterous workspace vanishes entirely — even though the plain workspace got bigger.

And one trap that matters for planners on page 134: **picking joint angles uniformly at random does not spread the hand uniformly over the workspace.** It piles up near the inner and outer edges, where the arm is nearly folded or nearly straight. Random in joints is not random in task space.

---

## Interview question

**"Is a car's rolling constraint holonomic?"**

No. Minus sin phi x dot plus cos phi y dot equals zero does not come from any g of x, y, phi equals zero. The test: the Lie bracket of the two allowed motions — drive and turn — produces the forbidden sideways direction. So the reachable set is the whole C-space. That is Chow's theorem.

And the consequence: a car needs a planner, and **no smooth, time-invariant feedback law can stabilise it to a point.** That is Brockett's result, and page 139 works around it.

---

## Carry forward

**One.** g of q is a gap meter; g equals zero means the rule holds. Each independent rule removes one dimension.

**Two.** Differentiate because a gap that is always zero cannot be changing. **A is how fast each gap opens per joint speed. Its rows are forbidden directions — and the directions the constraint pushes.**

**Three.** The null space of A is the set of motions the robot can actually make. Its size is the DOF. When A loses rank, watch out.

**Four.** Nonholonomic rules have the same shape but no g behind them: they forbid directions, not places. Parallel parking is the proof.

**Five.** C-space is the robot. Task space is the job. Workspace is where the robot can reach. Redundancy is joints minus task numbers.

Next page: orientation, done properly — the rotation matrix, and why it is the implicit representation the book uses everywhere.
