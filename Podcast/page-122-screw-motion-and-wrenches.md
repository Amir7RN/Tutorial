# Page 122 — Screw Motion: e^[S]θ, Left vs Right, and Wrenches

*Listening script. Roughly twenty-five minutes. Page 121 said how a body moves right now. This page asks where a steady twist takes it — and then adds forces.*

---

## The question

Page 121 gave you the twist: **how a body moves at this instant.** This page asks the next question: **if that twist keeps going steadily, where does the body land?** And then it adds forces.

Video 3.3.3 is unpacked as one card per question. From "how fast" to "where it lands." The rotations-to-rigid-motions table. What e to the S theta actually equals, built by hand in a lab. Riding a screw in 3-D. Which side the exponential goes on, and the classic bug. And why any of it matters: every joint is a screw.

Then video 3.4: forces and torques as one six-vector, the **wrench.**

If a symbol is unclear, the symbol map on page 121 has it in one table.

---

## From "how fast" to "where it lands"

**What's going on**: the twist only says how fast the pose is changing right now. To know where the body ends up, you have to add up all the tiny moves. For a steady twist, that adding-up has an exact answer — **the matrix exponential** — just as a steady spin gave R equals e to the bracket omega-hat theta. **You exponentiate the screw times the angle — not T.** The start pose just sits on the matching side.

**One. The velocity rule, two ways.** The twist acts on the pose the way omega acted on R. Written in s numbers it goes on the left: **T dot equals bracket V-s, times T.** In b numbers, on the right: **T dot equals T times bracket V-b.**

**Two. Steady twist, so exponential.** With V constant, both look like x dot equals a x, whose answer is x of t equals e to the a t times x of zero. Same here, with 4-by-4 matrices: **T of t equals e to the bracket V-s t, times T-zero** — or **T-zero times e to the bracket V-b t.**

**Three. Swap time for angle.** V equals S theta dot, so bracket V times t is bracket S times theta dot t — which is **bracket S times theta**, with theta the total angle turned, or distance slid. **The speed drops out.** Only the shape of the motion, S, and how far you went, theta, matter.

So: **T equals e to the bracket S-s theta, times T-zero — or T-zero times e to the bracket S-b theta.**

In words: **start at T-zero, ride the screw S a distance theta, and you land at T.**

And the common slip: writing "e to the T," or exponentiating something with T inside. **T is never exponentiated.** It's the starting pose that the exponential multiplies.

---

## The same story with one more row

**What's going on**: everything pages 118 to 120 did for rotations has a twin here. Line them up, so each new symbol has an old one to lean on. Video 3.3.3 is video 3.2.3 again, with S in place of omega-hat.

**Configuration**: R in SO-three, 3-by-3 — T in SE-three, 4-by-4.

**Unit velocity**: unit axis omega-hat — screw axis S: S-omega of length one, or S-omega zero and S-v of length one.

**How far**: theta, the angle turned — theta, the angle turned, or the distance slid for a pure translation.

**Exponential coordinates**: omega-hat theta, three numbers — **S theta, six numbers.**

**Matrix form**: bracket omega-hat theta in little so-three, 3-by-3 skew — bracket S theta in little se-three, 4-by-4.

**Velocity from configuration**: bracket omega-s equals R dot R inverse — bracket V-s equals T dot T inverse.

**Exp**: little so-three to SO-three, by Rodrigues — little se-three to SE-three.

**Log**: back the other way, in both.

**Change frame**: omega-s equals R omega-b — V-s equals the adjoint of T, times V-b.

Read down the right-hand column, and you have this page.

---

## What e to the S theta actually is

**What's going on**: e to the bracket S theta is itself a pose — a 4-by-4 T. **It's where the frame s would land if it rode the screw for theta.** Like every pose, it has two parts.

**The rotation part** says which way the body points after turning theta about s-hat. That's **plain Rodrigues** — nothing new.

**The position part** says where the body point that started at the origin ends up. That point moves with velocity S-v at the start — **and its velocity arrow turns along with the body as it goes round the axis.** Adding up all those turned arrows is what a matrix called **G of theta** does.

So e to the bracket S theta has **Rodrigues in the top-left**, and **G of theta times S-v in the top-right.**

**Case one, pure slide.** S-omega is zero — a prismatic joint. Nothing turns, so the rotation part is the identity, and the velocity arrow never turns. **The origin moves in a straight line: position equals S-v times theta**, with theta in metres.

**Case two, with turning.** S-omega has length one. Follow the point that starts at the origin. At angle zero, its velocity is S-v. By angle phi, the body has turned by phi about the axis, and the point's velocity arrow has turned with it: **e to the bracket omega-hat phi, times S-v.** The slide part, h s-hat, lies along the axis, so turning leaves it alone. And where it lands is **the sum of all those arrows** — the integral, from zero to theta, of e to the bracket omega-hat phi, times S-v, d-phi.

**That integral is G of theta times S-v**, where:

**G of theta equals I theta, plus one minus cosine theta, bracket omega-hat, plus theta minus sine theta, bracket omega-hat squared.**

You get it by integrating Rodrigues term by term.

**Reading G's three terms.** **I theta** alone would be "keep going straight at S-v" — the straight-line guess. The **bracket omega-hat** and **bracket omega-hat squared** terms **bend that line into the arc round the axis.** G is to position what Rodrigues is to rotation: an exact closed form. You never sum a series or take small steps.

---

## Check it with numbers

A hinge along z, through q equals zero, 0.5, zero. Pitch zero. Turn it 180 degrees.

S is zero, zero, one, then 0.5, zero, zero — because minus s-hat cross q is 0.5, zero, zero.

**Physically**: the origin is 0.5 metres from the hinge, so a half-turn should put it on the far side, at **zero, one, zero.**

**With G**: bracket omega-hat times S-v is zero, 0.5, zero. Bracket omega-hat squared times S-v is minus 0.5, zero, zero. At theta equals pi, one minus cosine pi is two, and theta minus sine theta is pi. So:

**G S-v equals pi times 0.5, zero, zero; plus two times zero, 0.5, zero; plus pi times minus 0.5, zero, zero.**

The pi terms cancel. **Zero, one, zero.** Check.

**Now add pitch, h equals 0.25.** S-v becomes 0.5, zero, 0.25. The extra zero, zero, 0.25 lies along the axis, so bracket omega-hat kills it and only the I theta term acts. The answer becomes **zero, one, 0.785** — the same swing, plus a climb of h theta, 0.25 pi, about 0.785 metres. **A screw going into wood.** Check.

---

## Lab: build G of theta S-v by hand

**What's going on**: split the ride into N small steps. In each step, the origin point moves a little in the direction of its current velocity — and that direction has turned with the body. **Chain the little arrows head to tail: they bend round into the arc, and with enough steps they land exactly where G of theta S-v says.** A red dashed line shows what you'd get if the arrow never turned — only the I theta term.

Seen from above. A vertical hinge passes through zero, d, zero. The frame origin starts at zero. Defaults: the check-with-numbers example, turned 180 degrees.

**N equals one**: one arrow, S-v theta. The straight guess.

**N equals two, three, six**: the chain bends round the hinge, and its tip closes in on the green dot.

**N equals forty**: almost on top of it. More steps, smaller gap.

**Raise h**: the top view doesn't change — the climb, h theta, is along z, out of the screen — but the third number of every readout grows by h theta.

**Set theta to 360 degrees**: the chain comes back to the start, and only the climb is left — two pi h.

---

## Lab: ride a screw in 3-D

**What's going on**: ride a screw and watch the frame. It turns about the axis and climbs along it, tracing a helix. **e to the S theta gives the frame at any theta. The log runs the movie backwards and recovers the shortest screw.**

The frame starts at s and twists about an orange axis at one radian per second. Theta equals 180 and 360 degrees are the video's "time pi" and "time two pi" snapshots. Take it in order.

**One. Pitch zero.** A revolute joint. The origin swings on a flat circle round the axis, and S-v equals minus s-hat cross q.

**Two. Raise the pitch.** The circle becomes a helix, climbing h theta per turn. A screw going into wood.

**Three. Infinite pitch.** S-omega is zero, S-v is s-hat, and the frame slides without turning. A prismatic joint.

**Four. Push theta past 180.** "Log T to theta" stops following and comes back down. **The log returns the shortest screw to the same pose**, with rotation angle between zero and 180 degrees. For a revolute joint, 360 and zero are the same pose, so the log can't tell them apart. With pitch, it returns a different screw that still lands on T.

**Five.** The last readout measures T inverse T dot numerically and compares it with bracket V-b. **Zero** — so the 4-by-4 velocity formula is right. And notice: **V-b changes as the frame twists. S, written in s, never does.**

---

## Which side does e to the S theta go on?

**What's going on**: the screw is one line in space. To use it, you write it as six numbers — and those numbers depend on **whose axes you measured it with.** The world's, s, or the body's own, b.

**World numbers**: the motion is a move of space itself, so it acts **from the left** on whatever pose the body has.

**Body numbers**: the motion is described by someone riding on the body, so it attaches **on the right** — after "here's where the body is."

**One. Read it with subscripts.** Riding the screw takes the body from pose b to a new pose, b-prime.

**Body numbers**: e to the bracket S-b theta is the new pose as seen from the old body pose — it **is** T b-b-prime. Then T s-b times T b-b-prime equals T s-b-prime. The inner subscripts cancel, exactly as on page 118. **So it goes on the right.**

**World numbers**: e to the bracket S-s theta moves everything in s — every point of space is carried round the fixed line. Apply it to the body wherever the body is. **Left.**

**Two. Physical pictures.** A **door hinge bolted to the wall**: you know its axis in room numbers, so **left.** A **drill spinning about its own bit**: you know the axis relative to the drill, so **right.**

**Three. Both give the same answer.** S-b and S-s are the same line, translated by the adjoint. Used on the matching side, they land on the same b-prime.

**Four. The classic bug.** Body numbers on the left. The numbers describe a line relative to b, but the left side reads them as if measured from s — **so the body swings about the wrong line.**

Same rule as for R on page 118, and for T on page 121: **left equals fixed space axes. Right equals the body's own axes.**

---

## Lab: one screw, two sets of numbers

**What's going on**: one hinge, written twice — with world numbers, and with body numbers. **Each version is right only on its own side of T s-b.** Mixing them up swings the body about the wrong line.

A vertical hinge through a point q swings b. Three candidate answers are drawn.

**Blue**: e to the S-s theta, times T s-b. Space numbers, left. **Correct.**

**Cyan dashed**: T s-b times e to the S-b theta. Body numbers, right. **Correct.**

**Red**: e to the S-b theta, times T s-b. Body numbers on the wrong side. **The classic bug.**

Blue and cyan always coincide: one physical screw, described twice, used on the matching side. Red swings about the wrong hinge point — the point that has q's b-coordinates, misread in s.

**Try**: move q onto b's own origin. S-b's linear part becomes zero, and b spins in place. **The red one still flies off, round s's origin.** That's the space-form versus body-form choice of page 123.

---

## Why it matters: every joint is a screw

**What's going on**: a robot joint lets its child link move one way only — turn about a fixed line, slide along it, or both at a fixed ratio. **That's a screw.** So each joint's motion is one exponential, e to the S-i theta-i, with S-i read off the hardware and theta-i from the encoder. **Multiply them together, and you have where the hand is.**

**Revolute, a hinge**: pitch zero. S is s-hat, and minus s-hat cross q. Theta is an angle, in radians.

**Prismatic, a slider**: pitch infinite. S is zero, and s-hat. Theta is a distance, in metres.

**Helical, a lead screw**: finite pitch. S is s-hat, and minus s-hat cross q plus h s-hat. Theta is an angle — and it also slides h theta.

And then forward kinematics:

**T of theta equals e to the S-one theta-one, times e to the S-two theta-two, and so on up to S-n theta-n, times M.**

**Why this order works.** M is the hand's pose with every joint at zero, and every S-i is written in s numbers at that home pose.

**Move the last joint first**, with all the others still at home. Its axis is exactly where the drawing says, so e to the S-n theta-n, times M, is right — world numbers, left.

**Now move joint n minus one.** It carries joint n and the hand with it, but **its own axis hasn't moved** — it sits closer to the base. So again, multiply on the left.

Repeat down to the base. **Every factor uses the home-pose screw, and nothing has to be re-derived for a new robot.** Page 123 builds this for real arms.

---

## Video 3.4 — wrenches

**What's going on**: forces and torques get the same six-number packing as velocities. **Power — velocity dot force — can't depend on who measures it, and that one fact forces the rule for moving a wrench between frames.**

**One. The question.** A robot hand holds an apple. A force-torque sensor at the wrist reads in its own frame. Knowing the apple's mass, which way gravity points, and where the apple sits — **what does the sensor read?**

**Two. Force and moment.** A force f-b, acting along a line through a point r-b, creates a moment about b's origin: **m-b equals r-b cross f-b.** Stack them, moment first: the **wrench**, F-b equals m-b and f-b. Same packing as the twist: angular on top, linear below.

**Three. The one fact used.** **Twist dot wrench equals power**: omega dot m, plus v dot f, in watts. Power is physical — a motor either spends five watts or it doesn't — **so it can't depend on which frame you write V and F in.** V-b transpose F-b equals V-s transpose F-s.

**Four. Derive the rule in three lines.** Change the twist's frame with the adjoint. Use the transpose of a product. And notice the result must hold for **every** twist V-s — so the two vectors it's dotted with must be equal. Out drops:

**F-s equals the adjoint of T b-s, transposed, times F-b.**

**Twists go across with Ad. Wrenches go across with Ad-transpose — of the reverse transform.**

Written out: **the force just turns**, f-s equals R s-b f-b. **The moment turns and picks up the lever arm**: m-s equals R s-b m-b, plus p s-b cross f-s. That's "moment equals r cross f" from school, applied to the shift between the two origins.

**Link back to page 117.** There, a constraint force A transpose lambda did no work, because the allowed motions satisfy A q dot equals zero: power equals q dot transpose A transpose lambda, equals A q dot, transposed, times lambda — zero. **That was this argument, in joint coordinates.** And on page 125, the same argument with the Jacobian in place of Ad gives **tau equals J transpose F.**

---

## Lab: the apple

**What's going on**: a worked case. Write the apple's weight as a wrench in the apple's frame, then move it into the sensor's frame with the adjoint transpose.

Frame a sits at the apple's centre of mass, y pointing up. There, gravity is simply **zero, zero, zero, then zero, minus m g, zero** — no moment, because the force passes through a's origin. The sensor frame f sits a distance L from the apple along its own x-axis, and can be tilted.

**At wrist angle zero you get the video's answer**: moment minus m g L about z of f, force minus m g along y of f. With a 0.2-kilogram apple at ten centimetres: **force minus 1.96 newtons, moment minus 0.196 newton-metres.**

**Double L**: the force is unchanged, the moment doubles. Lever arm.

**Tilt the wrist to plus 90 degrees**, so the apple sits straight above the sensor. The moment vanishes — gravity's line now passes through the sensor's origin — and the whole minus m g shows up along minus x of f.

And the power check pairs one fixed twist with the wrench in both frames: **always the same number.** That's the rule the whole derivation rested on.

---

## Interview question

**"A force sensor at the wrist reads F-b. What torque does that force produce about the base?"**

Transform it: **F-s equals the adjoint of T b-s, transposed, times F-b.** The moment part picks up p cross f. Then joint torques are **tau equals J-b transpose F-b, which equals J-s transpose F-s** — the same answer, because both are power balances.

---

## Carry forward

**One.** **Start at T-zero, ride screw S a distance theta, land at T.** Exponentiate S theta, never T. The speed drops out.

**Two.** **e to the S theta is Rodrigues for the turn, G of theta S-v for the position.** G bends the straight guess, S-v theta, into the arc round the axis. Half-turn about a hinge 0.5 metres away lands at zero, one, zero.

**Three.** **World-axis numbers go on the left; body-axis numbers on the right.** A wall hinge is left; a drill bit is right. Body numbers on the left is the classic bug.

**Four.** **Every joint is a screw**, so the hand's pose is a product of exponentials, one per joint, times the home pose M — each using its home-pose screw.

**Five.** **A wrench is moment over force. Power is frame-independent**, so wrenches move with Ad-transpose of the reverse transform — and the same argument becomes tau equals J transpose F.

Next page: **forward kinematics for real arms** — the product of exponentials, in space form and body form.
