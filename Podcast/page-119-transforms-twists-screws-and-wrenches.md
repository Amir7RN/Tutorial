# Page 119 — Transforms, Twists, Screws and Wrenches

*Listening script. Roughly twenty-five minutes. Page 118 again with position added: where a body is, how it moves, what pushes on it — and why power ties the last two together.*

---

## The question

Page 118 handled orientation only. **Now add position.**

Four things to write down for one rigid body. **T**, a 4-by-4 matrix, for where it is and which way it points. A **twist**, V equals omega and v, for how it moves. A **wrench**, F equals m and f, for what pushes on it. And the one fact that connects the last two: **V dot F is power, and power is the same in every frame.**

The page walks the last five videos of chapter 3. The homogeneous transform and its three uses. The twist — every velocity is a screw. Moving a twist between frames, with the adjoint. Following a screw for a while: the exponential of a twist. And forces and torques as one six-vector: the wrench.

**The trick for the whole episode: every step copies a step of page 118.** R becomes T. Omega becomes V. Little so-three becomes little se-three. Rodrigues becomes its 4-by-4 version. If a step feels new, find its twin on page 118 first. In C-space words: **this page is about the six-dimensional C-space of one free body, and its six-dimensional velocities and forces.**

---

## Video 3.3.1 — T equals R and p, in one matrix

**Packing.** To place frame b in frame s, you need two things, both in s numbers. **p**: where b's origin is. **R**: which way b's axes point. Put R in the top-left, p in the top-right, and a bottom row zero, zero, zero, one — which is only there to make the algebra work.

The result is the **homogeneous transformation matrix, T.** The set of all of them is the **special Euclidean group, SE-three.** T s-b is b as seen from s.

**Properties — the same list as for R.** Every T has an inverse: **R transpose, and minus R transpose p**, over zero, zero, zero, one. In words: rotate back, then undo the shift written in the new axes. A product of two T's is a T. Multiplication is associative, but not commutative.

**Three uses — the same list as for R.**

**Represent** a configuration: T s-b. And T b-s equals T s-b inverse. **Swapping subscripts inverts.**

**Change the reference frame**: T s-b times T b-c equals T s-c. Subscripts cancel. Walking back: T c-s is T b-c inverse times T s-b inverse.

**Displace** a point or a frame — the lab after next.

**Why the extra row and the extra one?** T is 4-by-4, but a point has three numbers. The product doesn't even fit. So append a one to the point: **p-b, comma, one — its homogeneous coordinates.** Then T times that gives **R p-b plus p, comma, one.** Rotate, then shift, in one product. The bottom row keeps the one a one, so products chain.

**And the link back.** A rigid body in space has m equals six freedoms, page 115. T has twelve meaningful numbers — nine in R, three in p — and six rules, R transpose R equals I. **Twelve minus six equals six.** SE-three *is* the C-space of one free body: flat three-space for position, the curved SO-three for orientation. T is implicit for the same reason R was — no bad spots. The position part is plain explicit numbers because three-space is flat. **Only the orientation needed the implicit trick.**

---

## The lab — one point, two frames, and the one at the end

Seen from above. Three sliders place b: a turn psi, an origin x and y. Two more set a point in **b numbers.** The readout gives its s numbers, from T s-b times p, one.

Move b's origin, and p-s moves by exactly that much — that's the shift column at work. Turn psi, and the point swings with b. And the "back" stat applies T s-b inverse, which is T b-s, and recovers p-b: **inverse equals swap subscripts.**

**Now tick the box that appends a zero instead of a one.** Now moving the origin changes nothing. The arrow turns with the frame, but doesn't shift with it. **A direction — "forward," or a velocity — has no location, so the zero switches off the shift column.** One means point. Zero means direction.

---

## T on the left, or T on the right

Any configuration can be reached from the start by first rotating, then translating. The video's T: **rotate 90 degrees about z-hat, translate two along y-hat.**

Where do z-hat and y-hat point? **It depends on the side** — by the same rule as for rotations.

**T times T s-b, on the left.** Omega-hat and p are read in the **first** subscript's frame: s. So b first swings 90 degrees about z of s — a vertical line through s's origin — then slides two along y of s.

**T s-b times T, on the right.** Read in the **second** subscript's frame: b. And the order flips: first slide two along b's own y, then spin 90 degrees about b's own z, which travelled with the frame.

The lab animates both. **Left, the blue path**: the first half swings b round s's origin in a big arc — because the axis is far away — then slides straight up the page. **Right, the violet path**: the first half slides along b's own green axis, tilted 30 degrees, then b spins in place about its own z.

**Same T, two different end frames.** Remember it once: **left equals the space-frame recipe. Right equals the body-frame recipe.** Forward kinematics on page 120 uses both.

---

## Video 3.3.2, part one — every velocity is a screw

**One. Same trick as for omega.** T dot has twelve moving numbers, but a body has six velocity freedoms. So T dot is not the representation — just as R dot was not.

**Two. The fact the whole chapter hangs on.** Any instantaneous rigid-body velocity — any mix of spinning and sliding — is the same as **turning about some line in space while sliding along that line.** A **screw motion.** The line is the **screw axis**, fixed by three things: a point q on it; a unit direction s-hat; and a **pitch h**, which is speed along the axis divided by turn rate about it. Then theta dot says how fast you turn.

**Three. Stored differently.** q, s-hat, h is a nice picture but awkward to compute with. So choose a reference frame and store a six-vector, **S equals S-omega and S-v**, both in that frame's numbers, for a turn rate of one.

**S-omega equals s-hat**: the angular velocity.

**S-v is the linear velocity of the point of the body that is at the frame's origin.** It has two parts: **h s-hat** — sliding along the axis — and **minus s-hat cross q** — being carried round the axis, because the origin is some distance away from it.

**Four. Infinite pitch.** A pure slide has no turning, so h is speed over zero: infinite. Then S-omega is zero, S-v is a unit vector along the slide, and theta dot is a linear speed in metres per second instead of a turn rate. So the normalisation is: **either S-omega has length one, or S-omega is zero and S-v has length one.**

**Five. The twist.** **V equals S times theta dot** is the full velocity: angular part omega, linear part v. Written in b numbers, it's the **body twist**, V-b. In s numbers, the **spatial twist**, V-s. Same motion, two descriptions.

**And here is the trap.** In both, v means the velocity of the body point currently at *that frame's origin*. For V-s, that is often **an imaginary point far outside the real body** — a point glued to the body that happens to be at the world origin right now. Strange, but it makes the algebra clean. V-b doesn't care where s is. V-s doesn't care where b is.

**The link back.** On page 117, a velocity was a list of joint rates. For a free body the "coordinates" are T — an implicit representation — so the velocity is not T dot but a six-vector in the tangent space of SE-three. Exactly as omega was the three-vector in the tangent space of SO-three. **Twelve numbers minus six differentiated rules: six.**

---

## The turntable

A turntable spins about a vertical axis through the world origin, coming out of the screen. Pitch zero: pure turning. Put a reference frame r anywhere, and read S in its numbers.

**The video's three cases.**

**One.** r sits two units left of the axis. S-omega is zero, zero, one. S-v is zero, minus two, zero. **The disc under r moves two units per second in minus y.**

**Two.** Move r anywhere else. **S-omega is unchanged. S-v is not.** It always has length equal to the distance from the axis, and points round the circle.

**Three.** Put r on the axis and tip it so its y-axis points into the screen. Now S-v is zero — r is on the axis — and because r's y-axis points into the screen, the same upward spin reads **S-omega equals zero, minus one, zero.**

**The motion never changed. Only the frame that describes it.** That is the whole meaning of "a twist is written in some frame." And spin the turntable: S doesn't change, because the axis is fixed.

---

## Video 3.3.2, part two — the adjoint, and twists as matrices

**One. The cancellation rule almost works.** We want V-a from V-b. "T a-b times V-b" fails: T is 4-by-4, V has six entries. We need a six-by-six matrix built from T a-b: the **adjoint**, Ad of T. With it the rule is back: **V-a equals Ad of T a-b, times V-b.**

The adjoint, for T equals R and p, is four three-by-three blocks: **R, zero, on top; bracket p times R, and R, below.**

Read it row by row. Top row: **omega just turns**, omega-a equals R omega-b. Bottom row: **v turns too — plus p cross R omega-b**, the extra speed a spin produces at a point p away.

**Why that bracket-p-R block?** Stand on a merry-go-round two metres from the centre. In the centre's frame, the ride only spins. In your frame, you are also being carried sideways at two metres times omega. **The adjoint adds that "carried by the spin" velocity whenever you move a twist to a frame whose origin is somewhere else.** In the turntable lab, that is exactly how S-v appeared.

**Two. Matrix form, as for omega.** Angular velocity had a matrix form: bracket omega-b equals R inverse R dot. Twists have one too, from T:

**Bracket V-b equals T inverse T dot. Bracket V-s equals T dot T inverse.**

Bracket V is a 4-by-4 matrix: the skew matrix bracket omega in the top-left, v in the top-right, and a bottom row of zeros. The set of these is **little se-three**, named after SE-three as little so-three was after SO-three.

And notice: the bracket is now **overloaded.** Bracket omega is 3-by-3, for a three-vector. Bracket V is 4-by-4, for a six-vector. Which one is meant is clear from what's inside. These 4-by-4 matrices are what the rigid-body exponential takes — next video.

---

## Video 3.3.3 — following a screw: the exponential of a twist

**This video is video 3.2.3 again, with S in place of omega-hat.** Read across, rotation on the left, rigid-body motion on the right.

**Configuration**: R in SO-three, 3-by-3 — becomes T in SE-three, 4-by-4.

**Unit velocity**: a unit axis omega-hat — becomes a screw axis S.

**How far**: theta, the angle turned — still theta, or the distance slid if it's a pure translation.

**Exponential coordinates**: omega-hat theta, three numbers — becomes **S theta, six numbers.**

**Matrix form**: bracket omega-hat theta in little so-three — becomes bracket S theta in little se-three.

**Velocity from configuration**: bracket omega-s equals R dot R inverse — becomes bracket V-s equals T dot T inverse.

**Exp and log**: little so-three to SO-three and back — becomes little se-three to SE-three and back.

**Change frame**: omega-s equals R omega-b — becomes V-s equals Ad of T, times V-b.

**The closed forms.** Pure slide, S-omega zero: orientation unchanged, position equals S-v times theta. With turning: the rotation part is plain Rodrigues, and the position part is a matrix times S-v — **I theta, plus one minus cosine theta bracket omega, plus theta minus sine theta bracket omega squared, all times v.**

**Which side?** To move b by theta along a screw: **if S is written in b numbers, multiply on the right** — T s-b times e to the bracket S-b theta. **If in s numbers, on the left** — e to the bracket S-s theta, times T s-b. The same left-right rule as for T and R.

**And why it matters.** Every one-DOF joint is a screw. **Revolute: pitch zero. Prismatic: pitch infinite. Helical: finite pitch.** So chapter 4's forward kinematics is **one exponential per joint, multiplied together.** That's page 120.

---

## Ride a screw

The lab twists a frame about an orange screw axis at one radian per second, and draws its origin's path. Take it in order.

**One. Pitch zero.** A revolute joint. The origin swings on a flat circle round the axis, and S-v equals minus s-hat cross q.

**Two. Raise the pitch.** The circle becomes a helix, climbing h times theta per turn. **A screw going into wood.**

**Three. Infinite pitch.** S-omega is zero, S-v is s-hat, and the frame slides without turning. **A prismatic joint.**

**Four. Push theta past 180 degrees.** "Log T to theta" stops following and comes back down. The log returns the **shortest** screw to the same pose, with rotation angle between zero and 180. For a revolute joint, 360 and zero are the same pose, so the log can't tell them apart. With pitch, it returns a different screw that still lands on T.

**Five.** The last stat measures T inverse T dot numerically and compares with bracket V-b. **Zero.** So the 4-by-4 velocity formula is right. And notice: V-b changes as the frame twists — S, written in s, never does.

---

## One screw, two sets of numbers, and the classic bug

A hinge — vertical axis, pitch zero — through a point q swings b. Write the axis in s numbers, S-s, and in b numbers, S-b, which is Ad of T b-s times S-s. Three candidate answers are drawn.

**Blue**: e to the S-s theta, times T s-b. Space numbers, on the left. **Correct.**

**Cyan dashed**: T s-b times e to the S-b theta. Body numbers, on the right. **Correct.**

**Red**: e to the S-b theta, times T s-b. **Body numbers on the wrong side. The classic bug.**

Blue and cyan always coincide: one physical screw, described twice, used on the matching side. Red puts b-numbers where s-numbers belong, so it swings about the wrong hinge — the point that has q's b-coordinates, misread in s.

**Try:** move q onto b's origin. S-b's linear part becomes zero, and b spins in place. **The red one still flies off, round s's origin.** That's the space-form versus body-form choice of page 120 — and the bug you will write at least once.

---

## Video 3.4 — wrenches

**One. The question.** A robot hand holds an apple. A force-torque sensor at the wrist reads in its own frame. Knowing the apple's mass, which way gravity points, and where the apple sits — **what does the sensor read?** We need a way to write forces and torques, and to move them between frames.

**Two. Force and moment.** A force f-b, acting along a line through a point r-b, creates a moment about b's origin: **m-b equals r-b cross f-b.** Stack them, moment first: the six-vector **wrench**, F-b equals m-b and f-b. Same packing as the twist: angular thing on top, linear below.

**Three. The one fact used.** **Twist dot wrench equals power**: omega dot m, plus v dot f, in watts. Power is physical — a motor either spends five watts or it doesn't — so **it cannot depend on which frame you write V and F in.** V-b transpose F-b equals V-s transpose F-s.

**Four. Derive the rule in three lines.** Change the twist's frame with the adjoint. Use the transpose of a product. Notice the result must hold for **every** twist V-s, so the two vectors it's dotted with must be equal. Out drops:

**F-s equals Ad of T b-s, transposed, times F-b.**

**Twists go across with Ad. Wrenches go across with Ad-transpose — of the reverse transform.** Written out: the force just turns, f-s equals R s-b f-b. The moment turns *and picks up the lever arm*: **m-s equals R s-b m-b, plus p s-b cross f-s.** That's "moment equals r cross f" from school, applied to the shift between the two origins.

**And the link back to page 117.** There, a constraint force A transpose lambda did no work, because the allowed motions satisfy A q dot equals zero: power equals q dot transpose A transpose lambda, equals A q dot, transposed, times lambda — zero. **That was this card's argument, in joint coordinates.** A force paired with a velocity through a dot product, and the dot product — power — as the thing that's physical. **On page 122 the same argument, with the Jacobian in place of Ad, gives tau equals J transpose F.**

---

## The apple

Frame a sits at the apple's centre of mass, y pointing up. There, gravity is simply **zero, zero, zero, zero, minus m g, zero** — no moment, because the force passes through a's origin. The sensor frame f sits a distance L from the apple along its own x-axis, and can be tilted. Then F-f equals Ad of T a-f, transposed, times F-a.

**At wrist angle zero you get the video's answer**: a moment of minus m g L about z of f, and a force of minus m g along y of f. With a 0.2-kilogram apple at ten centimetres: **force minus 1.96 newtons, moment minus 0.196 newton-metres.**

**Double L** — the force is unchanged, the moment doubles. Lever arm.

**Tilt the wrist to plus 90** so the apple sits straight above the sensor — the moment vanishes, because gravity's line now passes through the sensor's origin, and the whole minus m g shows up along minus x of f.

And the power check pairs one fixed twist with the wrench in both frames: **always the same number.** That's the rule the whole derivation rested on.

---

## Interview question

**"A force sensor at the wrist reads F-b. What torque does that force produce about the base?"**

Transform it: **F-s equals Ad of T b-s, transposed, times F-b.** The moment part picks up p cross f. Then joint torques are **tau equals J-b transpose F-b, which equals J-s transpose F-s** — the same answer, because both are power balances.

---

## Carry forward

**One.** **T packs R and p into one 4-by-4 matrix.** Twelve numbers, six rules, six DOF. Append a one for a point, a zero for a direction.

**Two.** **Left-multiply uses space axes; right-multiply uses body axes** — for R, for T, and for exponentials of screws.

**Three.** **Every rigid-body velocity is a screw.** Store it as S equals S-omega and S-v; the twist is S theta dot. In V-s, v is the velocity of the body point at the world origin — often imaginary.

**Four.** **The adjoint moves twists between frames**, adding the "carried by the spin" velocity. T equals e to the bracket S theta follows a screw, and every joint is a screw — which is all forward kinematics is.

**Five.** **A wrench is moment over force. Power V dot F is frame-independent**, so wrenches move with Ad-transpose of the reverse transform — and the same argument becomes tau equals J transpose F.

Next page: **forward kinematics** — write the home pose and one screw axis per joint, and multiply the exponentials.
