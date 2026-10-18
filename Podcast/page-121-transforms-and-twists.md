# Page 121 — Transforms and Twists: Where a Body Is and How It Moves

*Listening script. Roughly twenty-five minutes. Pages 118 to 120 did orientation. This page adds position: one 4-by-4 matrix for where a body is, one six-number twist for how it is moving right now — and why that twist is always a single screw.*

---

## The question

Pages 118 to 120 handled orientation only. **Now add position.**

This page answers two questions. **Where is the body?** One 4-by-4 matrix, T. **How is it moving right now?** One six-number vector, the twist, V. The next page, 122, asks where a steady twist takes the body, and adds forces.

Before any of that, two orientation cards: **the big picture** — why build all this machinery at all — and **the symbol map**, which puts every symbol in one table with one running example.

---

## The big picture: why all this, when v-B equals v-A plus omega cross r already works?

That's the honest question, so start there.

**There is no new physics on pages 118 to 122.** A twist is still "one spin for the whole body, plus the velocity of one point." The formula you learned in mechanics — the velocity of point B equals the velocity of point A, plus omega cross r — is still the whole truth.

**What changes is the bookkeeping.** It's chosen so that three things are true. It never breaks — no gimbal lock. It chains link by link, by plain multiplication. And it runs as the same code on any robot. Doing one body by hand is easy. **A chain of six or seven bodies, solved by a computer thousands of times a second, is not.**

**The story so far, in one pass.**

**Orientation**: store it as R — nine numbers, six rules — not three angles. Because every three-angle chart has a bad spot, and R has none.

**Its velocity**: R dot has nine numbers but only three are free. Call them omega. Omega is a plain three-vector — legal everywhere, it adds, and it's what a gyro measures.

**Where a steady spin goes**: R equals e to the bracket omega-hat theta, by Rodrigues. Exact, always lands on a real rotation, no drift.

**Add position**: T equals R and p, one 4-by-4 matrix. One object for a whole pose. Chaining frames is multiplying. That's this page.

**Its velocity**: the twist, V equals omega and v — six numbers. T dot has twelve, but only six are free: the spin, and one point's velocity. Also this page.

**Where a steady twist goes**: T equals e to the bracket S theta, times T-zero. Exact motion along a screw. And every joint is a screw. That's page 122.

**Every step does the same two things: choose a representation with no bad spots, then pull out the smallest honest velocity from it.**

---

## Where doing it by hand stops scaling

Picture a six-joint arm with axes pointing in odd directions.

**By hand**: pick coordinates for each link. Write v-B equals v-A plus omega cross r, link to link. Choose angles for each orientation. Differentiate everything. Every new robot is a fresh derivation, the angles bring singularities, and one sign error ruins it.

**The chapter 3 way**: from the robot drawing, write down **one thing per joint** — its screw axis, S-i, at the home pose. Which way the hinge points, and one point on it. **That is the whole input.** Everything else falls out mechanically.

**Where is the hand?** Forward kinematics: T of theta equals e to the S-one theta-one, times e to the S-two theta-two, all the way to S-n theta-n, times the home pose M. One exponential per joint. Page 123.

**How fast is the hand moving?** The Jacobian: V-s equals J-s of theta, times theta dot. Column i is joint i's screw at the current pose. It's the link-by-link velocity sum, written as one matrix. Page 124.

**What torques hold a force?** Statics: tau equals J transpose F, from power — twist dot wrench equals joint speeds dot torques. A load-cell reading becomes joint torques with no new free-body diagram per pose. Page 125.

**Which angles reach a target?** Inverse kinematics: the log gives the pose error as one twist — the screw that would carry you there — and it wraps and takes the short way. Page 126.

**What torques give this motion?** Recursive Newton–Euler: twists passed outward, wrenches passed inward, one frame-change rule per link. Same code for any robot. Page 131.

**And control**: orientation error is log of R-desired transpose R — a three-vector you can multiply by a gain. Forces move between frames with the same rules as twists.

**When is the hand method still right?** For one body, a planar mechanism, or a quick check — it's perfect, and it's the same physics. Use it to sanity-check the matrix results.

**The one sentence to keep: v-B equals v-A plus omega cross r says what the physics is. R, the twist and the exponential are a way to write that physics that never breaks, chains link by link through multiplication, and runs as the same code on any robot.**

---

## The symbol map

These symbols piled up one video at a time. **They are really only three ideas.** A **unit direction** — which way, how a motion is shaped. A **speed** — how fast you go along it. A **distance** — how far you went.

**Unit thing times speed equals a velocity. Unit thing times distance equals a displacement.** A bracket is the same numbers rearranged as a matrix. And the exponential turns a displacement into a pose.

**The running example.** A nut on a vertical threaded rod. The rod points along z and passes through the point q equals zero, 0.5, zero. The thread climbs h equals 0.25 metres per radian. The nut turns at theta dot equals two radians per second.

**Rotation only.**

**Omega-hat**: unit arrow along the spin axis. Here, zero, zero, one.

**Theta dot**: how fast it turns about omega-hat. Two radians per second.

**Omega**: spin velocity, direction and speed in one arrow — omega-hat times theta dot. Zero, zero, two.

**Theta**: how far it has turned in total. After pi over two seconds at two radians per second: pi radians.

**Omega-hat theta**: exponential coordinates, "turn theta about omega-hat." Zero, zero, pi.

**Bracket omega**: omega as a 3-by-3 skew matrix, so bracket omega times v equals omega cross v.

**Rigid body: rotation plus position.**

**S-hat**: the unit direction of the screw axis. It's the same arrow as omega-hat, renamed, **because the axis now also has a location.**

**q**: any point on the screw axis — *where* the axis is. Zero, 0.5, zero.

**h**: the pitch — metres slid along the axis per radian turned. Zero for a hinge, infinite for a slider. Here 0.25.

**S**, equals S-omega and S-v: the screw axis as six numbers. It's **the twist for unit speed** — the *shape* of the motion. S-omega is s-hat. S-v is minus s-hat cross q, plus h s-hat. For the nut: zero, zero, one, then 0.5, zero, 0.25.

And S-v deserves a sentence of its own. At unit speed, it's **the velocity of the body point that's at the frame origin.** Minus s-hat cross q is "carried around the axis." h s-hat is "slide along it." Here, 0.5, zero, zero — plus zero, zero, 0.25.

**V**, equals omega and v: **the twist — how the body moves right now.** V equals S times theta dot. For the nut, zero, zero, two, then one, zero, 0.5.

**v**: velocity of the body point that's at the frame's origin right now — often an imaginary point off the real body.

**S theta**: exponential coordinates of a rigid motion — "ride screw S for theta."

**Bracket V and bracket S**: the six numbers as a 4-by-4 matrix — bracket omega top-left, v top-right, zeros below.

**V-s and V-b**: the same motion written in s numbers or in b numbers, each using its own frame's origin as the reference point.

**The pattern, side by side.** Rotation: omega-hat times theta dot is omega; omega-hat times theta is omega-hat theta; e to the bracket omega-hat theta is R. Rigid body: S times theta dot is V; S times theta is S theta; e to the bracket S theta is T.

**S is to V exactly what omega-hat is to omega: the unit-speed version.** The only new parts are q and h — because a rigid motion's axis has a place in space, and the body may also slide along it.

---

## Video 3.3.1 — T equals R and p, in one 4-by-4 matrix

**What's going on**: one 4-by-4 matrix holds both "which way the body points" and "where its origin is." The extra row is only bookkeeping, so that "turn, then shift" is a single multiplication, and chaining frames is just multiplying matrices.

**One. Packing.** To place b in s you need two things, both in s numbers: **p**, where b's origin is, and **R**, which way its axes point. R top-left, p top-right, bottom row zero, zero, zero, one. That's the **homogeneous transformation matrix T.** The set of all of them is the **special Euclidean group, SE-three.**

**Two. Properties — the same list as for R.** Every T has an inverse: R transpose, and minus R transpose p, over the bottom row. Rotate back, then undo the shift written in the new axes. A product of two T's is a T. Associative, not commutative.

**Three. Three uses — the same list as for R.** **Represent**: T s-b; and T b-s is T s-b inverse — swapping subscripts inverts. **Change the reference frame**: T s-b times T b-c equals T s-c; subscripts cancel. **Displace** a point or a frame.

**Four. Why the extra row and the extra one.** T is 4-by-4, a point has three numbers — the product doesn't fit. So append a one: **p-b, comma, one — homogeneous coordinates.** Then T times that is R p-b plus p, comma, one. Rotate, then shift, in one product. The bottom row keeps the one a one, so products chain.

**Link back.** A rigid body in space has six freedoms, page 115. T has twelve meaningful numbers and six rules. **Twelve minus six is six.** SE-three *is* the C-space of one free body: flat three-space for position, curved SO-three for orientation. T is implicit for the same reason R was — no bad spots. Position is plain explicit numbers because three-space is flat.

---

## Lab: one point, two frames, and the one at the end

**What's going on**: one place in space, two descriptions. Numbers measured from b go in; numbers measured from s come out. The appended one means "this is a location, apply the shift." A zero means "this is a direction, ignore the shift."

Move b's origin, and the point's s numbers move by exactly that much — the shift column at work. Turn b, and the point swings with it. The "back" stat applies T s-b inverse and recovers the b numbers: inverse equals swap subscripts.

**Tick the box that appends a zero instead.** Now moving the origin changes nothing. **A direction — "forward," or a velocity — has no location, so the zero switches off the shift column.**

---

## Use three: T on the left, or T on the right

**What's going on**: one displacement T can be read two ways — as a move described in the world's axes, so put it on the left; or as a move described in the body's own axes, so put it on the right. Different readings, different end poses.

The video's T: **rotate 90 degrees about z-hat, then translate two along y-hat.**

**T times T s-b, on the left**: z-hat and y-hat are read in the **first** subscript's frame, s. So b first swings 90 degrees about the vertical line through s's origin — a big arc, because that axis is far away — then slides two along y of s.

**T s-b times T, on the right**: read in the **second** subscript's frame, b, and the order flips. First b slides two along its own y, tilted 30 degrees, then spins 90 degrees about its own z, which came along for the ride.

**Same T, two different end frames.** Remember it once: **left equals the space-frame recipe; right equals the body-frame recipe.** Forward kinematics on page 123 uses both.

---

## Video 3.3.2, part one — every velocity is a screw

**What's going on**: at any instant, a rigid body's motion is **one spin about some line, plus a slide along that same line.** S describes that line and its pitch, for unit speed. The twist, V equals S theta dot, is the actual motion: how fast it spins, and how fast the body point at the frame origin moves.

**One. Same trick as for omega.** T dot has twelve moving numbers but a body has six velocity freedoms. So T dot isn't the representation — just as R dot wasn't.

**Two. The fact the whole chapter hangs on.** Any instantaneous rigid-body velocity — any mix of spinning and sliding — is the same as **turning about some line in space while sliding along that line.** A **screw motion.** The line is the screw axis, fixed by a point q on it, a unit direction s-hat, and a **pitch** h — speed along the axis divided by turn rate about it.

**Three. Stored differently.** Choose a frame and store **S equals S-omega and S-v**, for a turn rate of one. S-omega is s-hat. S-v is the velocity of the body point at the frame's origin — h s-hat, sliding along the axis, plus minus s-hat cross q, being carried round the axis.

**Four. Infinite pitch.** A pure slide has no turning: pitch infinite. Then S-omega is zero, S-v is a unit vector along the slide, and theta dot is metres per second. So **either S-omega has length one, or S-omega is zero and S-v has length one.**

**Five. The twist.** V equals S theta dot. In b numbers it's the **body twist**; in s numbers, the **spatial twist.** In both, v is the velocity of the body point at *that frame's origin* — for V-s, often **an imaginary point far outside the real body.**

---

## The twist is the rigid-body velocity rule in disguise

**What's going on**: if you know how fast the body spins, and how fast one chosen point moves, you know how fast every point moves — add the "carried round by the spin" part, omega cross r. **Those two arrows, six numbers, are the twist.** And looking for the points whose velocity has no "carried round" part at all finds one special line: the screw axis.

**Step one. The velocity rule already uses six numbers.** **v-P equals v-A plus omega cross r from A to P.** Pick one reference point A. Two vectors — omega, three numbers, and v-A, three numbers — give the velocity of every point of the body. **That pair is the twist.** The book only fixes which point A is.

For the **spatial twist**, A is the body point currently at the world origin — often imaginary — with numbers in s axes. For the **body twist**, A is the body frame's origin, numbers in b axes.

**Step two. Why not T dot?** T dot is R dot and p dot, over zeros. p dot — three numbers — is the velocity of the body origin: the rule's v-A, nothing wrong there. R dot — nine numbers — holds only three real ones, because R dot equals bracket omega R. So T dot has twelve entries and six free. **The twist keeps exactly those six.**

**Step three. Where the single screw comes from — Chasles' theorem.** In plane motion there's an **instant centre** of zero velocity; the body is purely spinning about it. The screw is the 3-D version. In 3-D you usually can't find a point with zero velocity — **but you can always find points whose velocity is parallel to omega.**

Split v-A into a part along omega, v-parallel, and a part across it. Then step away from A by **r equals omega cross v-A, over omega squared.** The triple-product rule says omega cross r is then exactly v-parallel minus v-A. So at the new point, the velocity is v-A plus omega cross r: **just v-parallel. Along omega.**

And so does every point on the line through it in the direction of omega. **That line is the screw axis.** At this instant the whole body spins about that one line at rate omega, while sliding along it — with pitch **h equals omega dot v-A, over omega squared.**

**Step four. Why it's not three screws.** Omega-x, omega-y, omega-z are the components of **one** arrow. Three spins about x, y and z add up to one spin about a tilted axis. Adding v-A doesn't create more screws either — it only moves that one axis sideways, and adds a slide along it.

**Numeric check — the nut.** Omega is zero, zero, two. The body point at the origin moves at one, zero, 0.5.

**Axis point q**: omega cross v, over four — zero, 0.5, zero.

**Pitch h**: omega dot v, over four — **0.25 metres per radian.**

**Velocity at q**: one, zero, 0.5, plus omega cross q, which is minus one, zero, zero — total **zero, zero, 0.5. Parallel to omega.** Check.

**Slide speed**: h times omega, 0.25 times two — 0.5 metres per second. Check.

So the origin's velocity — one, zero, 0.5 — is just this one screw seen from a point 0.5 metres off the axis: **0.5 metres per second of slide, plus two times 0.5 equals one metre per second of being carried around.**

---

## Lab: set a twist, see the one screw it makes

**What's going on**: you type in the six numbers of a twist. The lab finds the one line the body is screwing along, and shows every corner of a box turning round that line and climbing along it at the same rate. **Moving the reference point A changes the six numbers you read — but never the line.**

Take it in order.

**One. General screw.** Drag time: each corner traces a helix around the same pink line, all climbing at the same rate. One screw, even though omega has three components.

**Two. Move A.** Omega stays, v-A changes — but the axis and the pitch stay put. **The six twist numbers depend on where you stand. The screw does not.**

**Three. Put A on the screw axis.** The "around" arrow vanishes and v-A points straight along the axis. **The axis is exactly the set of points whose velocity is parallel to omega.**

**Four. Rolling wheel.** Pitch zero, axis along y, 0.5 metres under the centre — **the 2-D instant centre of zero velocity, stretched into a line.** The contact line with the ground.

**Five. Door hinge.** Pitch zero, axis a metre off to the side. Nudge the vertical velocity up and the hinge becomes a screw going into wood.

**Six. Set omega to zero.** The pitch is infinite, every point has the same velocity, and there's no axis to draw. **A prismatic joint.**

---

## Lab: the turntable

**What's going on**: one physical motion, written down by observers standing in different places and facing different ways. **The spin part only changes when the observer turns. The "velocity of the disc under me" part changes with where the observer stands.**

The video's three cases.

**One.** Frame r sits two units left of the axis. S-omega is zero, zero, one. S-v is zero, minus two, zero: the disc under r moves two units per second in minus y.

**Two.** Move r anywhere else. **S-omega unchanged. S-v changes** — always with length equal to the distance from the axis, pointing round the circle.

**Three.** Put r on the axis, tipped so its y-axis points into the screen. S-v is zero — r is on the axis — and the same upward spin now reads **S-omega equals zero, minus one, zero.**

**The motion never changed; only the frame that describes it.** That's the whole meaning of "a twist is written in some frame."

---

## Video 3.3.2, part two — the adjoint, and twists as 4-by-4 matrices

**What's going on**: moving a twist to another observer — turn both arrows into the new axes, and **add the extra sideways speed the new observer sees, because their origin sits at another place on the spinning body.** The 4-by-4 form is the same six numbers arranged so they can multiply T.

**One. The cancellation rule almost works.** We want V-a from V-b. T a-b times V-b fails: T is 4-by-4, V has six entries. So build a 6-by-6 from T: **the adjoint.** Then **V-a equals Ad of T a-b, times V-b.**

The adjoint for T equals R and p is four 3-by-3 blocks: **R and zero on top; bracket p R, and R, below.** Top row: omega just turns. Bottom row: v turns too — **plus p cross R omega-b, the extra speed a spin produces at a point p away.**

**The merry-go-round.** Stand two metres from the centre. In the centre's frame, the ride only spins. In your frame, you're also being carried sideways at two metres times omega. **The adjoint adds that "carried by the spin" velocity whenever you move a twist to a frame whose origin is somewhere else.** That's exactly how S-v appeared in the turntable lab.

**Two. Matrix form, as for omega.** Bracket omega-b was R inverse R dot. Now: **bracket V-b equals T inverse T dot; bracket V-s equals T dot T inverse.** Bracket V is 4-by-4: bracket omega top-left, v top-right, zeros below. The set is **little se-three.** The bracket is now overloaded — 3-by-3 for a three-vector, 4-by-4 for a six-vector — and what's inside tells you which.

---

## Two routes to the same twist

**What's going on**: the six numbers of a twist can be found two ways. **Look at the mechanism** — which way the axis points, where it is, its pitch and how fast it turns. **Or watch the pose T change over time** and compute the twist from T and T dot. Both give the same numbers.

**Route one, from geometry**: V equals S theta dot, with S equals s-hat, and minus s-hat cross q plus h s-hat. That's how a joint's twist is written — read it off the hardware.

**Route two, from measured motion**: you know T of t, from sensors or forward kinematics. Compute **T dot T inverse** for V-s, or **T inverse T dot** for V-b, and read off omega and v.

**Three details that are easy to get wrong.**

**One. T inverse, not T transpose.** For R, the inverse happened to equal the transpose. T isn't orthogonal — it holds a shift — so T transpose is wrong. T inverse is R transpose and minus R transpose p: turn back, then undo the shift.

**Two. q, not p.** In the screw formula, q is a point *on the screw axis*. p is where the body frame's origin is. Different things. And the order is minus s-hat cross q.

**Three. The outer bracket.** T dot T inverse is the 4-by-4 matrix form, not the six-vector. Read omega from its top-left skew block, and v from its top-right column.

This is the rotation pattern again — bracket omega-s equals R dot R inverse — now with position included. And the 3-D screw lab does route two backwards: you set omega and v, and it recovers s-hat, q and h.

---

## Interview question

**"What is a twist, and why not just use T dot?"**

T dot has twelve entries, but a rigid body has only six velocity freedoms: R dot equals bracket omega R carries three, p dot carries three. **The twist keeps exactly those: V equals omega and v — the spin, plus the velocity of the body point at the frame's origin — so v-P equals v plus omega cross r for every point.**

By Chasles, it's always one screw: a spin about a line through **q equals omega cross v, over omega squared**, plus a slide with pitch **h equals omega dot v, over omega squared.** Get it from hardware as S theta dot, or from motion as T dot T inverse.

---

## Carry forward

**One.** No new physics: **v-P equals v-A plus omega cross r** is still the truth. The matrices are bookkeeping that never breaks and chains by multiplication.

**Two.** **Three ideas behind all the symbols**: a unit direction, a speed, a distance. **S is to V what omega-hat is to omega** — the unit-speed version.

**Three.** **T packs R and p.** Append one for a point, zero for a direction. Left-multiply uses space axes; right-multiply uses body axes.

**Four.** **The twist is omega plus one point's velocity.** By Chasles, it's always one screw — q equals omega cross v over omega squared, h equals omega dot v over omega squared.

**Five.** **Move twists with the adjoint**, which adds the merry-go-round term. Get a twist from hardware as S theta dot, or from motion as T dot T inverse — with T inverse, not T transpose.

Next page: **where a steady twist takes the body** — e to the S theta — and then forces.
