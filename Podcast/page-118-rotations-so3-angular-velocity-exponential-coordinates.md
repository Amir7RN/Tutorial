# Page 118 — Rotations: SO(3), Angular Velocity, Exponential Coordinates

*Listening script. Roughly twenty-five minutes. Which way is a body pointing, how fast is it turning, and where does a steady turn take it — told as the C-space pages, applied to orientation.*

---

## The question, and the promise

Three questions about one rigid body in 3-D. **Which way is it pointing? How fast is it turning? And if it keeps turning steadily, where does it end up?**

The page walks the first six videos of chapter 3 of Modern Robotics, in order. Frames and the right-hand rule. The rotation matrix and its six rules. The three jobs one rotation matrix does. Angular velocity. The matrix exponential. Rodrigues' formula and the matrix log.

And here is the promise that makes it easier than it sounds: **almost nothing on this page is a new idea.** It is pages 115 to 117 — degrees of freedom, implicit representation, holonomic and Pfaffian constraints — applied to orientation. Chapter 3 sounds like a new subject. It mostly renames things you already have.

---

## The dictionary

Keep this list in your head for the whole episode. Each new word on the left is an old word on the right.

**The configuration of a rigid body** is a point in C-space. A body in space has **six DOF**: three for where it is, three for which way it points. That is m equals six in Grübler.

**SO-three, the space of orientations**, is the orientation piece of that C-space. Three-dimensional — but **curved and closed, like a sphere**, not flat like ordinary three-dimensional space. That was topology, page 116.

**The rotation matrix R, nine numbers**, is an **implicit representation**. More numbers than DOF, tied together by rules, so it has no bad spots. Page 116.

**R transpose R equals the identity** — those are the rules: **six holonomic constraints**, g of R equals zero, that trap nine numbers on a three-dimensional surface. Page 117.

**Determinant plus one** picks one of two **disconnected pieces** — like choosing the four-bar's assembly mode.

**"Angular velocity is not the derivative of three angles"** is page 116's "velocity is not a coordinate rate." Differentiating R transpose R equals I gives a **Pfaffian velocity constraint**, and its null space — three-dimensional — is where omega lives.

**Exponential coordinates, omega-hat theta, three numbers**, are an **explicit** chart. Fine almost everywhere, awkward at 180 degrees.

**If one row stays foggy, that's fine.** But hold onto the fourth one above all. **R transpose R equals I is the same kind of object as the hoop rule, x squared plus y squared minus one equals zero.** A violation meter that must read zero. Everything about angular velocity comes from differentiating it — exactly as A q dot equals zero came from g of q equals zero.

---

## Video 3.1 — frames, and seven sentences

The introduction video says seven things. Each is worth a sentence.

**One. Representations of configurations, velocities and forces.** Three things to write down for a rigid body: where it is and which way it points, how fast that is changing, and what pushes on it. Every later chapter uses these three, so they are chosen with care.

**Two. Implicit representations — the C-space as a surface in a higher-dimensional space.** This is page 116's choice, made for you. Orientation has three DOF but will be stored as nine numbers. Those nine numbers form a nine-dimensional space; the rules carve out a three-dimensional surface inside it; real orientations live only on that surface. **Same picture as the bead: two numbers, one rule, a one-dimensional hoop.**

**Three. Not a minimum set of coordinates, and velocities are not time derivatives of coordinates.** Because the nine numbers are not independent, "the velocity" will not be "the rate of each number." It will be a separate three-vector, omega, that is *not* the derivative of any three numbers.

**Four. Frames.** An origin, plus three unit axes at right angles. To describe a body, glue a frame b to it, fix a frame s in space, and describe b as seen from s.

**Five. Right-handed only.** x cross y equals z. Index finger x, middle finger y, thumb z. A mirror-image frame is never used.

**Six. Frames are stationary.** When the body moves, "frame b" means the fixed frame that coincides with the body *at this instant*. A snapshot. That is what lets us say "the velocity expressed in b" without the frame sliding out from under us.

**Seven. Positive rotation by the right-hand rule.** Thumb along the axis, fingers curl the positive way. Every sign in the chapter comes from this.

And the link back. **Page 116 ended with: plain angles for joints, wrapped; a rotation matrix for anything that can point in any 3-D direction.** Chapter 3 is the second half of that sentence, worked out in full. Joint angles stay explicit. The hand's orientation becomes implicit.

**The lab.** Build a frame with your right hand. Point x anywhere; z equals x cross y comes out automatically, and the determinant reads plus one. Tick the mirror box and z flips, the determinant goes to minus one — **and no slider will bring it back.** A mirror frame cannot be rotated into a right-handed one. They are two separate pieces. Hold that thought; it comes back in a minute.

---

## Video 3.2.1, part one — the rotation matrix

Ignore position. Look only at which way b points.

**Take b's x-axis. Write it as three numbers in s coordinates. Make that column one.** Do the same for b's y-axis — column two — and b's z-axis — column three. Stack them. **That is R s-b.**

The video's example: b is turned 90 degrees about z of s. Then b's x-axis points along plus y of s: zero, one, zero. b's y-axis points along minus x of s: minus one, zero, zero. b's z-axis is unchanged: zero, zero, one. Those three columns are R s-b.

**About the subscripts.** The second one, b, is the frame being described. The first one, s, is the frame doing the describing. **"b as seen from s."**

And the rule for reading it: **read the columns, not the rows.** Red column is where b's red axis points. Green is green. Blue is blue.

**The lab's best slider is the one that breaks things.** It adds a small epsilon to just the top-left entry of R. Only one of nine numbers changes — and immediately the x column is no longer unit length, the violation meter lights up, and the drawn x-axis stretches. **Nine numbers, of which only three are free. Change one alone and you leave the surface.**

That violation meter — the size of R transpose R minus I — is page 117's gap meter g, built the same way. Zero when the rule holds, growing the farther you are from it. And nudging one coordinate alone is the bead nudged off the hoop. **Real rotations move several entries at once, in exactly the ratio that keeps the meter at zero.**

---

## Nine minus six equals three

**The count.** Orientation has three DOF. R has nine entries. So the entries must obey nine minus three: **six independent rules.** Three say "each column has length one." Three say "each pair of columns is at right angles." Written compactly: **R transpose R equals I.** Entry i-j of R transpose R is column i dot column j, so "equals I" says one on the diagonal, zero off it.

**The sign.** Those six rules allow determinant plus one, or minus one. Plus one are right-handed frames; minus one are mirror frames. We keep only plus one. And the set of all three-by-three real matrices with R transpose R equals I and determinant plus one is the **special orthogonal group, SO-three.** "Orthogonal" for R transpose R equals I. "Special" for determinant plus one.

**Five properties follow, each in one line.**

**Inverse equals transpose.** R transpose R equals I is literally the definition of an inverse. So undoing a rotation costs nothing — no matrix inversion, ever.

**Closed under products.** Two rotations multiplied give a rotation. So you can chain frames: s to b to c gives another rotation.

**Associative.** Group long chains in any order you like.

**Not commutative.** R-one R-two is not R-two R-one in general. Turning about x then z ends somewhere other than z then x. **The order of joints, and of multiplications, matters.**

**Keeps lengths.** Rotating a vector never stretches it.

And the link back is three pages at once. **Nine minus six equals three** is the same bookkeeping as Grübler: freedoms minus constraints. **R transpose R equals I** are six holonomic constraints shrinking a nine-dimensional space to a three-dimensional surface, just as the hoop shrank the plane to a circle. **And the surface comes in two pieces**, determinant plus one and minus one, with no path between them. The rules alone allow both; a physical fact — right-handedness — rules one out. Exactly like the four-bar's assembly mode.

That three-dimensional surface is SO-three: curved, closed, finite. Which is why page 116 said it is not flat three-space, and cannot be covered by three angles without a bad spot.

---

## Rotations do not commute

The lab: A is a turn alpha about x. B is a turn beta about z. Left panel shows A times B, right panel B times A. **Same two turns, opposite order.**

At 90 and 90 degrees, the two results point in visibly different directions — they differ by a **120-degree turn.** Set either slider to zero, and the difference vanishes: a turn and "no turn" commute. And small turns *almost* commute. At ten degrees each, the gap is under two degrees; halve both and it drops about fourfold.

**That last fact is why angular velocity can be a plain three-vector** — for an instant, turns are tiny and the order stops mattering. Finite turns must be multiplied in the right order.

**And here is the link that makes this page click.** This is page 117's car again. Turning 90 about x then 90 about z, or the other way, uses the same "amount" of each turn but ends at a different orientation. So **orientation is not a function of "total turn about x, total turn about y, total turn about z."** That is exactly what nonholonomic meant. You cannot integrate the three components of angular velocity into three position-like numbers — just as you could not integrate the car's no-slip rule into a g of x, y, phi. **Hence video 3.1's warning: velocities are not derivatives of coordinates.**

---

## Video 3.2.1, part two — three jobs one matrix does

**Job one: represent an orientation.** R s-c lists c's axes in s numbers. And R c-s — s's axes in c numbers — is its transpose. **Swapping the subscripts transposes the matrix.**

**Job two: change the reference frame.** If you know c as seen from b, and want it as seen from s, premultiply by R s-b. And here is the rule that saves you every time: **subscript cancellation.** In R s-b times R b-c, the second subscript of the first matrix meets the first subscript of the second. They match — b and b — so they cancel, and you are left with R s-c. Vectors obey the same rule: p-s equals R s-b times p-b.

**Treat subscripts like units in physics.** Kilometres per hour times hours gives kilometres.

The lab gives three frames: s; b, which is s turned 90 degrees about z of s; and c, which is b turned minus 90 degrees about its own y-axis. From the dropdown: R s-b times R b-c gives R s-c, and the check confirms it. **R b-c times R s-b puts c next to s — nothing cancels — and the check fails.** The multiplication is legal algebra. It means nothing.

And for the vector: p in b numbers is one, zero, one-half. In s numbers it comes out zero, one, one-half. **The arrow did not move.** Only the frame doing the describing changed — so the numbers changed, and the length did not.

**Job three: rotate a vector or a frame.** R s-b is also just "turn 90 degrees about z." So any rotation matrix can be read as an **operation**: Rot of omega-hat, theta.

On a vector already in s numbers, nothing cancels, so the product is read as a new vector: p-s turned about the axis, still written in s.

On a frame, you can multiply on either side, and **the side decides which axis you turn about.**

**Premultiply** — Rot on the left of R s-c. The axis is read in the frame of the **first** subscript: s. So c swings about the *fixed* z of s.

**Postmultiply** — Rot on the right. The axis is read in the frame of the **second** subscript: c. So c spins about *its own* z.

In the lab, z of s is vertical but z of c lies flat. At 90 degrees, the left panel's frame swings round the vertical; the right panel's spins about the flat axis. **Same matrix, same angle, different axis — so different frames.**

**The rule to keep: left equals about a fixed space axis. Right equals about the body's own axis.** The same rule returns for 4-by-4 transforms on page 119, and for forward kinematics on page 120.

---

## Video 3.2.2 — why R dot is not the angular velocity

**One. The obvious idea fails on count.** R changes in time, so why not call R dot the angular velocity? Because R dot has nine numbers, and a spinning body only has three independent ways to spin. Six of R dot's numbers are redundant.

**Two. Where the three come from.** R of t must obey R transpose R equals I at every instant. **Differentiate both sides**, product rule: R dot transpose R, plus R transpose R dot, equals zero. So **R transpose R dot equals minus its own transpose.**

A matrix equal to minus its own transpose is **skew-symmetric**: zeros on the diagonal, and each entry below the diagonal is minus the one above. **Only three free numbers.** So R dot is forced into a three-dimensional set at each R. Those three numbers are the angular velocity.

**This is page 117, line for line.** The rule g of R equals zero is holonomic. Differentiating it gives a velocity rule, linear in R dot, of the form "something times R dot equals zero" — a Pfaffian constraint. On the hoop, two numbers minus one rule left a one-dimensional tangent line of allowed velocities. Here, nine numbers minus six rules leave a **three-dimensional tangent space.**

**Three. The picture.** SO-three is curved — the video draws it as a sphere. At any point of it, the allowed velocities form a **flat** three-dimensional space touching it there: the tangent space. **A flat space can be described everywhere by three ordinary numbers, with no bad spot.** That is why velocities are easy — a plain three-vector — even though orientations are not.

**Four. Axis and speed.** Any angular velocity is a spin about some axis at some rate. Unit axis omega-hat — the hat means length one — and rate theta dot. Their product, **omega equals omega-hat theta dot**, is the angular velocity vector. Direction: the axis. Length: the speed. Sign: right-hand rule.

**Five. How the axes move.** As b spins, the tip of b's x-axis runs round a circle about the spin axis. Its velocity is tangent to that circle: **omega cross x-hat b.** Same for y and z. Stack the three columns and you get R dot:

**R dot equals omega-s bracket, times R.**

**Six. The bracket.** Crossing with omega is a linear operation, so it is a matrix. **Bracket omega is the three-by-three matrix with bracket omega times y equals omega cross y.** It is skew-symmetric. And the set of all three-by-three skew-symmetric matrices is called **little so-three** — named after SO-three because it is exactly the set of "velocity matrices" R transpose R dot.

**Seven. Body or space numbers.** Omega is one physical arrow. It can be written in s numbers — omega-s — or in b numbers — omega-b. Subscript cancellation: **omega-b equals R inverse omega-s**, and omega-s equals R omega-b. In matrix form: bracket omega-s equals R dot R inverse; bracket omega-b equals R inverse R dot.

**And the drift warning from page 117 applies too.** Step R forward with a straight R dot times delta t, and you leave SO-three slightly — exactly like the dashed tangent line leaving the hoop. The exponential, two videos ahead, is the way to step without leaving.

**The lab.** Spin a frame about an axis you choose, and watch thin arrows at the tips of b's axes — their velocities, omega cross each axis. "R dot measured," computed by actually turning the frame a tiny bit forward and back, agrees with bracket omega-s times R to about ten to the minus eight — rounding. Point the spin axis straight up: **omega-s is zero, zero, theta dot, but omega-b has three nonzero entries**, because b is tilted. Same arrow, other numbers. Turn the spin axis to lie along one of b's own axes: that axis's tip arrow disappears. **An axis does not move when you spin about it.**

---

## Video 3.2.3, part one — why "exponential"

**Three numbers again.** Any orientation can be reached from s by **one** turn: some unit axis omega-hat, by some angle theta. Multiply them: **the three-vector omega-hat theta — direction is the axis, length is the angle — is the exponential coordinates of the orientation.**

**Why exponential?** Read omega-hat as an angular velocity of one radian per second, kept up for theta seconds. The final orientation is what you get by integrating that motion from the start. And integrating a constant-coefficient linear equation is exactly what exponentials do.

**One variable:** x dot equals a x has solution x of t equals e to the a t, times x of zero. And e to the a t is the series one, plus a t, plus a t squared over two factorial, plus a t cubed over three factorial, and so on.

**Many variables:** x dot equals A x, with A a constant matrix, has the same solution with the same series — only the powers are now matrix powers. That series is the **matrix exponential**, e to the A t. For rotations, A is bracket omega-hat, so the answer is **e to the bracket omega-hat, theta.**

**Why it collapses for rotations.** For a unit axis, bracket omega-hat cubed equals minus bracket omega-hat. So every power folds back onto bracket omega-hat or bracket omega-hat squared. Collect the terms, and the scalar series left over are exactly **sine theta** and **one minus cosine theta.**

**The lab** keeps N terms of the series and measures the error. At 120 degrees, four terms are still visibly wrong — the partial sum isn't even a rotation; its determinant and orthogonality are off. By eleven terms the error is about ten to the minus four; by twenty, about ten to the minus twelve. **Bigger angles need more terms.** Which is why code never sums the series: next video has the closed form.

---

## Video 3.2.3, part two — integrate, Rodrigues, log

**Integrate it yourself.** Follow one axis of the frame — call it p. Spinning about omega-hat at one radian per second, its tip runs round a circle, and its velocity is tangent: **p dot equals omega-hat cross p.** That is x dot equals A x, so after theta seconds, p of theta equals e to the bracket omega-hat theta, times p of zero. Do it to all three axes at once, and the matrix of axes goes from I to R. **Exponentiating integrates the angular velocity.**

**The lab integrates the same equation the naive way**: N straight steps, p plus delta t times omega-hat cross p. Every straight step leaves along the tangent, so it lands slightly *outside* the circle. The errors pile up, and p grows longer than one — which no rotation can do. At twelve steps over 270 degrees, **p ends more than twice as long as it started.** At two hundred steps, still about four percent too long. Better, never exact. The exponential needs no steps and keeps the length at one, to rounding.

**This is the hoop's dashed tangent line, run in a loop.** A straight velocity step drifts off the constraint surface, and the gap meter creeps away from zero. **Robot code that integrates orientation with R plus R dot delta t has this bug.** The fix is R times e to the bracket omega-b delta t: an exact turn per step, so R stays on SO-three.

**Rodrigues' formula** is the closed form of the series:

**Rot of omega-hat, theta, equals e to the bracket omega-hat theta, equals I, plus sine theta bracket omega-hat, plus one minus cosine theta, bracket omega-hat squared.**

**The matrix log** runs it backwards. Give it R, and it returns bracket omega-hat theta: the axis and the angle that reach R from the identity. The angle comes from the trace: **cosine theta equals trace of R minus one, over two.**

A way to remember the pair: **exponential is like integration** — velocity and time in, where you end up out. **Log is like differentiation** — where you ended up in, which constant velocity and how long out.

**The lab.** Point an axis, choose theta. Determinant stays one, orthogonality error is about ten to the minus sixteen: **Rodrigues always lands on SO-three.** Now try a negative angle. The log reports a positive angle and the *opposite* axis — because minus 110 degrees about omega-hat is the same R as plus 110 about minus omega-hat, and the log always picks an angle between zero and 180. At exactly 180, both axis signs give the same R, so the log has to choose one. **That is the single awkward spot of these three numbers.**

And the link back. Omega-hat theta is an **explicit** representation: three numbers for three DOF. Page 116 said every three-number chart of SO-three must misbehave somewhere. For this one the trouble is mild and lives only at 180 degrees. So: **compute with R** — implicit, no bad spots — **and use log R when you need three numbers for a short while.** An orientation error for a controller. One joint's turn.

**And the preview of chapter 4:** for a revolute joint, omega-hat is the joint axis and theta is the joint angle. **So each joint's rotation is literally e to the bracket omega-hat theta.**

---

## Interview question

**"Why not Euler angles in a controller?"**

They have a singularity — for ZYX at pitch plus or minus 90 degrees, roll and yaw become the same rotation, and the map from angle rates to omega loses rank. Their composition is not addition. And interpolating them gives curved, speed-varying motion. **Compute with R or quaternions, and express orientation error as the log of R-desired transpose R** — a three-vector you can multiply by a gain.

---

## Carry forward

**One.** R s-b's columns are b's axes written in s. Nine numbers, six rules, **three DOF.** Determinant plus one picks the right-handed piece.

**Two.** **Subscripts cancel like units.** Left-multiply turns about a fixed space axis; right-multiply turns about the body's own axis.

**Three.** Differentiate R transpose R equals I and a **skew-symmetric** matrix falls out. Its three numbers are omega. **R dot equals bracket omega-s times R.** This is page 117's g to A q dot, applied to rotation.

**Four.** Rotations don't commute, so orientation can't be integrated from three angle totals — **orientation is nonholonomic in the angular velocities.**

**Five.** Exponentiating integrates. **R equals e to the bracket omega-hat theta** by Rodrigues; the log goes back. Step orientation with an exponential, never with R plus R dot delta t.

Next page: add position. **R becomes T, omega becomes a twist, Rodrigues gets a 4-by-4 twin — and forces get packed into a wrench.**
