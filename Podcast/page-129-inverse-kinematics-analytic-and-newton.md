# Page 129 — Inverse Kinematics: Triangles, Then Newton

*Listening script. Roughly twenty minutes. Made for the car: audio only, nothing to look at, nothing to write down, nothing to work out in your head. If a number slips past, let it go. The idea is what matters, and the page keeps every number for later.*

---

## The question

So far, kinematics has run in one direction. You give the joint angles. Forward kinematics gives you the hand pose. One input, one answer, always.

This page runs it backwards. **You say where you want the hand. Find the joint angles that put it there.** That's inverse kinematics.

It sounds like the same problem in reverse. It isn't. Going forward is a function: every joint setting puts the hand somewhere definite. Going backward is not a function at all. Ask for a point beyond the arm's reach, and there is **no** answer. Ask for a point right at the edge of reach, and there is exactly **one**: the arm held straight. Ask for a point comfortably inside, and a two-link arm has **two** answers: elbow up, or elbow down. A general six-joint arm can have up to **sixteen**. And an arm with more joints than the task needs has **infinitely many**.

So the first thing to say about inverse kinematics is: **zero, one, two, or infinitely many.** Keep that in your head. It explains almost every difficulty that follows.

---

## Two ways to solve it

There are two families of solution, and the videos cover both.

**The first is analytic.** You use the geometry of this particular robot: triangles, angles, the law of cosines. Out comes a formula. The formula gives you **all** the answers at once, elbow up and elbow down. It needs no starting guess. It runs in a fixed, tiny amount of time. The catch: it only exists for robots whose shape allows it. A two-link arm, yes. A six-joint arm with a spherical wrist, yes. An arbitrary arm, often no.

**The second is numerical.** You guess the joint angles. You compute where the hand actually is. You compare with where you want it. You use the Jacobian to correct the guess. You repeat. This works for **any** robot, with any number of joints. The catch: it gives you **one** answer, the one near your guess. And a bad guess can fail, or quietly hand you the other branch.

Geometry, giving a formula. Or iteration, giving one answer near a guess. That's the whole map of this page.

---

## Tool one: atan2

Every analytic solution leans on two tools. The first is a function called **atan2**.

Here's the problem it solves. Suppose you want the angle of the arrow from the origin to some point, x comma y. The schoolbook answer is the arctangent of y over x. But dividing y by x throws away the signs. The point one comma one, up and to the right, gives y over x equal to one. The point minus one comma minus one, down and to the left, **also** gives y over x equal to one. Plain arctangent says forty-five degrees for both. One of them is wrong by a half turn.

And straight up, the point zero comma one, makes you divide by zero.

**atan2 takes y and x separately**, so it still knows the signs. It knows which quadrant you're in. Up-right comes out forty-five degrees. Down-left comes out minus one hundred thirty-five. Straight up comes out ninety, with no division by zero.

The rule is simple: **in kinematics, always atan2. Never plain arctangent.**

---

## Tool two: the law of cosines

The second tool is the law of cosines. You met it in school. Here's the one fact that makes it useful:

**Three side lengths fix a triangle completely.** If you know all three sides, every angle inside is determined. The law of cosines is the formula that reads an angle off the three sides.

And for a two-link arm, you always know three sides. The shoulder, the elbow, and the hand make a triangle. One side is the first link. One side is the second link. And the third side is the straight-line distance from the shoulder to the target. Call it r.

So the triangle is known. Its angles are known. And the joint angles come straight out of those triangle angles.

One small detail. The inverse cosine only returns angles between zero and one hundred eighty degrees. That's exactly right for an angle inside a triangle. The choice of which way the triangle folds, elbow up or elbow down, is made separately, with a plus or a minus sign.

---

## The two-link recipe

Now put the tools together on a two-link arm.

**First, where can it reach?** Picture the arm sweeping around. Straight out, it reaches a circle with radius equal to both links added. Folded back on itself, it reaches only a small circle, with radius equal to the difference of the links. Everything it can touch is the **ring** between those two circles.

Outside the ring: no solution. On the outer edge: one solution, arm straight. On the inner edge: one solution, arm folded flat. Strictly inside: two solutions.

**Second, the three angles.** The video names them gamma, alpha, and beta.

**Gamma** is the direction from the shoulder to the target. That's atan2 of the target's y and x.

**Alpha** is the angle inside the triangle at the shoulder, between the first link and the line to the target. Law of cosines.

**Beta** is the angle inside the triangle at the elbow, between the two links. Law of cosines again.

**Third, read off the joints.** For one solution, the shoulder angle is gamma minus alpha, and the elbow angle is one hundred eighty degrees minus beta. For the mirror solution, the shoulder angle is gamma plus alpha, and the elbow angle is beta minus one hundred eighty. Same triangle, flipped over the line to the target.

Why one hundred eighty minus beta? Because beta is the angle **inside** the triangle at the elbow. The joint angle is measured from the direction the first link points. That's the angle **outside** the triangle. Inside and outside add up to a straight line.

**A worked example, just to hear the shape.** Links of one metre and point eight metres. Target at one point two, point six. The distance r comes out about one point three four. Gamma is about twenty-seven degrees. Alpha about thirty-six. Beta about ninety-six. So one solution has the shoulder slightly below horizontal, about minus ten degrees, and the elbow bent about eighty-four. The mirror solution has the shoulder up at about sixty-three, and the elbow bent the other way, minus eighty-four. Put either one into forward kinematics, and the hand lands on the target.

You don't need to remember those numbers. Remember the shape: **one triangle, two ways to fold it, same elbow bend with opposite signs.**

---

## Bigger arms

What about six joints?

If the last three joints have axes that cross at one point, a spherical wrist, the problem splits in two. The first three joints place the **wrist centre**. That's a position problem, a lot like the two-link triangle, one dimension up. Then the last three joints set the **orientation**. That's a rotation problem. Each half has a couple of branches, and together you get up to **eight** solutions.

A general six-joint arm with no special structure can have up to **sixteen**, and no tidy formula. That's where the numerical method takes over.

---

## Newton–Raphson in one dimension

Now the second family: iteration.

Write the hand position as some function f of the joint angles. You want f of theta to equal a target, x-d. Move everything to one side, and inverse kinematics becomes **root finding**: find theta where the error, x-d minus f of theta, is zero.

The classic tool for root finding is **Newton–Raphson**. Here's the picture, in one dimension.

You're standing at your guess, somewhere on the error curve. You don't know where the curve crosses zero. But you do know its slope right where you're standing. So you pretend the curve is a straight line with that slope. You slide down that straight line to where it hits zero. That's your next guess.

If the curve really were straight, you'd be done in one step. It's curved, so you're only closer. So you do it again. And again.

**And here's the remarkable part.** Once you're close, each step roughly **doubles the number of correct digits.** That's called quadratic convergence.

Let me give you a feel for it. Take a single link of length one, turning about the origin. Its tip's x coordinate is the cosine of the angle. Ask for x equal to one half. The exact answer is sixty degrees. Start from a guess of one radian, about fifty-seven degrees.

After one Newton step, the error is about seven ten-thousandths of a radian. After the second step, it's about three ten-millionths. A third step, and it's beyond anything a motor could resolve. **Close, closer, done.**

---

## Two warnings

The same simple example shows both ways Newton goes wrong.

**Warning one: more than one root.** Cosine equals one half at plus sixty degrees **and** at minus sixty degrees. Newton finds the root whose neighbourhood your guess sits in. Start on the negative side, and you get minus sixty. That's not a bug. That's the other branch, the mirror solution, and Newton has no way to know which one you meant.

**Warning two: flat stretches.** Near zero degrees, the cosine curve is almost flat. The slope is nearly zero. And Newton divides by the slope. So a tiny slope makes an enormous step, and your next guess lands somewhere wild.

For a robot arm, that flat stretch has a name. It's a **singularity**. The arm is straight, or folded, and some direction of hand motion just isn't available. Newton feels that as a slope near zero, and it lurches.

So: **start close, and stay away from singularities.**

---

## Many joints: the Jacobian takes the slope's place

With several joints, the slope becomes a matrix. And you already know which one: **the Jacobian.**

The reasoning is the same. Near your current guess, the hand moves like a straight-line function of small joint changes. The hand change equals the Jacobian times the joint change. So the error you want to remove equals the Jacobian times the correction you need.

If the Jacobian is square and healthy, you invert it, and you have the correction. But often it isn't square. Three joints for a two-number task. Or four joints for a six-number pose. And sometimes it's singular.

The fix is the **pseudoinverse**, written J-plus. Page 127 built it from the singular value decomposition: divide by each stretch factor that isn't zero, and skip the ones that are. It always exists. And it does the sensible thing in every case.

If the Jacobian is square and healthy, J-plus is just the ordinary inverse. One exact answer.

If there are **more joints than task numbers**, there are infinitely many corrections that would work. J-plus picks the one with **the least joint motion**.

If there are **fewer joints than task numbers**, or the arm is singular, no correction works exactly. J-plus picks the one that makes **the leftover error as small as possible**. Least squares.

Page 130 opens J-plus up completely. For now, think of it as **the best available undo of the Jacobian.**

---

## The algorithm, out loud

Here's the whole numerical method, as steps you could say out loud.

One. Make a guess for the joint angles.

Two. Compute the error: where you want the hand, minus where forward kinematics says it is.

Three. If the error is small enough, stop. You're done.

Four. Otherwise, add J-plus times the error to the joint angles.

Five. Go back to step two.

That's it. Guess, measure, correct, repeat.

---

## Full poses: the error is a twist

There's one wrinkle. A hand pose isn't a list of coordinates. It's a position **and** an orientation, a four-by-four transform. You can't just subtract two transforms and call it an error.

So what plays the role of "target minus actual"?

Three frames. The fixed frame, s. The desired frame, d, where you want the hand. And the body frame, b, where the hand is right now.

First, look at the desired frame **from the hand's point of view**. That's the transform from b to d. You get it by taking the inverse of where the hand is, times where you want it.

Then take the **matrix logarithm** of that transform. Remember page 122: the log of a pose is the screw motion that produces it. So the log gives you a twist. **It's the body twist that, followed for one second, carries the hand exactly onto the target.**

That twist **is** the error. It points from where you are to where you want to be, in the language of motion.

And then the correction is the same as before: add the **body** Jacobian's pseudoinverse, times that twist.

Why the body Jacobian, not the space one? Because the error twist is written in the hand's own frame. The body Jacobian also produces twists in the hand's frame. **Both sides of the equation must speak the same frame.** You could do it all in the space frame instead, as long as you convert the twist with the adjoint. Just never mix them.

**When do you stop?** Check the turning part and the sliding part **separately**. Radians and metres can't be added. Stop when the remaining spin is below something like a thousandth of a radian, **and** the remaining slide is below something like a tenth of a millimetre.

In the video's example, a four-joint arm reaches its target in about four steps. After that, the error is invisible.

---

## When the target can't be reached exactly

Here's a subtle case, and it matters for the workshop arm.

The RRPR arm from page 125 has four joints. A full pose has six numbers: three for turning, three for sliding. So its body Jacobian is **six by four**. Tall. Two directions of hand motion are always missing.

If the target pose was made by the arm itself, some set of joint angles really reaches it, and Newton converges to it.

If the target wasn't, say you tilt it in a direction the arm can't tilt, then no joint angles reach it exactly. Each step, J-plus returns the least-squares correction. The iteration still settles. It settles at **the closest reachable pose**, in the twist sense. The leftover error stops shrinking, and that leftover is exactly the part the arm can't do.

The lab on this page has a "tilt the target" box that shows precisely that.

---

## Damping

Near a singularity, J-plus divides by a stretch factor that's nearly zero. The step blows up. It's the same flat-stretch problem as the cosine curve.

The standard fix is **damping**. Instead of dividing by a stretch factor, sigma, you divide by sigma squared plus a small number, lambda squared, and multiply by sigma on top. In a healthy direction, sigma is big, and lambda barely changes anything. In a weak direction, sigma is tiny, and instead of the step exploding, it fades towards zero.

The price: you need a few more steps. The gain: no wild leaps. This is called damped least squares, or Levenberg–Marquardt.

---

## Inside a real controller

One last practical point, and it takes most of the fear out of Newton.

In a running robot, a new target arrives every millisecond. And it's only slightly different from the last one. So **last cycle's answer is an excellent first guess** for this cycle. One or two Newton steps per cycle are plenty.

The bad-guess problem mostly disappears when you're always tracking a target that moves smoothly. You're never far from the answer, so you never wander onto the wrong branch.

---

## Interview question

**"When would you use analytic inverse kinematics, and when numerical?"**

Analytic, when the robot's structure allows it, like a six-joint arm with a spherical wrist. It's fast, it's deterministic, and it gives **all** the solutions, so you can choose elbow up or elbow down deliberately.

Numerical, for anything else: redundant arms, odd geometries, or when you want to add extra goals. It needs a good starting guess. In a controller, the previous answer provides one. And near singularities, you add damping.

A strong follow-up: **mention atan2**, mention that numerical IK uses the **body twist from the matrix log** as its error, and mention that the step uses the **pseudoinverse**, not the inverse.

---

## Carry forward

**One.** Inverse kinematics can have **zero, one, two, or infinitely many** answers. Out of reach, edge of reach, inside, or redundant.

**Two.** Analytic means **geometry**: atan2 for directions, the law of cosines for triangle angles. The two-link arm is one triangle folded two ways. Always atan2.

**Three.** Numerical means **Newton–Raphson**: guess, measure the error, correct with J-plus, repeat. Near the answer, correct digits double each step. Watch out for the other branch, and for flat stretches near singularities.

**Four.** For a full pose, the error is **the log of the transform from the hand to the target**: a body twist. Use the body Jacobian with it. Check spin and slide separately.

**Five.** J-plus gives the least joint motion when there are spare joints, and the least leftover error when there aren't enough. Damping keeps it calm near singularities.

Next page: **J-plus opened up completely** — the null space, the four pieces of joint space and hand space, and why the pseudoinverse is really "moment arm over moment arm squared."
