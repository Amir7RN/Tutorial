# Page 130 — The Pseudoinverse and the Null Space

*Listening script. Roughly twenty minutes. Made for the car: audio only, nothing to look at, nothing to write down, nothing to work out in your head. Every number is said once so you hear its shape. You don't need to hold on to any of them. The page keeps them all.*

---

## The question

Page 129 ended with one line: the joint speeds equal J-plus times the hand velocity you want. That's **inverse velocity kinematics**. It's one Newton step, without the iteration. You know the twist you want right now, so you undo the Jacobian once.

This page opens up that J-plus completely. What it does. Why it picks the answer it picks. What happens to the motions it throws away. And how a robot uses those thrown-away motions on purpose.

One arm carries the whole story, so you can picture it with your eyes on the road.

---

## The arm

A flat arm with **three joints**, each link one metre long.

The first joint sits at the origin. The first link points straight along the floor, to the right. So the second joint is one metre to the right. The second link points straight up. So the third joint is one metre to the right and one metre up. The third link points right again. So the tip is two metres to the right and one metre up.

Right, up, right. A little staircase.

And the task has **two** numbers: how fast the tip moves sideways, and how fast it moves up and down.

Three joints. Two task numbers. **One spare.** Hold on to that. The spare is what this page is about.

---

## Two spaces

There are two spaces in play, and keeping them apart clears up most of the confusion.

**Joint space** is the list of joint speeds: three numbers, one per joint. It's three-dimensional.

**Hand space** is the tip velocity: sideways and up-down. Two numbers. Two-dimensional.

The Jacobian is the machine that takes a point in joint space and returns a point in hand space. Joint speeds in, tip velocity out.

---

## Reading the Jacobian two ways

The Jacobian is a grid of numbers, two rows by three columns. You can read it two ways, and both matter.

**Read it down the columns.** Each column belongs to one joint. It's the arrow the tip moves along when only that joint turns at one radian per second. That's the moment-arm velocity you met on the statics page. Joint one, at the origin, swings the tip left and strongly up. Joint two swings it left and up, a bit less. Joint three, closest to the tip, only pushes it straight up.

**Read it across the rows.** Each row belongs to one hand direction. It lists how much leverage each joint has on that direction. The up-down row says joint one has the most leverage on vertical motion, because it's farthest from the tip horizontally. Joints two and three have less.

Columns: **what each joint does to the tip.** Rows: **how much each joint can push the tip one particular way.** Same grid. Two readings.

---

## A whole line of answers

Now ask the arm to move its tip straight up, at one metre per second.

Two equations, one for sideways and one for up-down. Three unknowns, one per joint speed. More unknowns than equations means **infinitely many answers.**

And they have a beautiful shape. In joint space, all the answers lie on **one straight line**.

Why a line? Because there's a special joint motion that does **nothing at the tip**. Turn joint one forward a little, and turn joints two and three backward by the same amount. Joint one swings the whole arm up, but joint two and three swinging back cancel it exactly. The tip stays put. The elbows move. The tip doesn't feel a thing.

That do-nothing motion is called the **null space**. Here it's a single direction in joint space. Take any answer that works, add any amount of the do-nothing motion, and it still works. That's your line of answers.

So the question becomes: **of all the points on that line, which one does J-plus pick?**

---

## The four pieces

Before answering, it helps to name four pieces. Two live in joint space. Two live in hand space.

**In joint space:**

The **joint working space** is every joint motion that actually moves the tip. Here it's a flat plane inside the three-dimensional joint space.

The **joint null space** is every joint motion the tip doesn't feel. Here it's the single do-nothing line.

And these two are **perpendicular**. That's not a coincidence. The do-nothing motion gives zero when you dot it with each leverage row. That's exactly what "the tip feels nothing" means. So the null line stands at right angles to the plane the rows span.

**In hand space:**

The **hand reachable space** is every tip velocity the arm can make. In this healthy pose, that's every direction. The whole plane.

The **hand unreachable space** is the tip directions the arm can't make at all. In this pose, there are none. But straighten the arm out, and one appears: the tip can't move along the line of the arm.

If you ever read Strang, his names are row space, null space, column space, and left null space. Same four pieces. Joint working, joint null, hand reachable, hand unreachable.

And here's the picture that makes it all simple. **The Jacobian takes the joint working space and maps it onto the hand reachable space, one to one. It sends the joint null space to zero.** And **J-plus does the exact reverse.** It takes the hand reachable space back onto the joint working space. And whatever's unreachable, it sends to zero.

---

## J-transpose-J and J-J-transpose

Two products come up again and again, and they're easy to mix up. So let's place each one in its space.

**J-transpose times J** is three by three. It lives on the **joint** side. Each entry compares two columns, two joints' tip arrows. On the diagonal, each joint's squared moment arm. Off the diagonal, how much two joints' arrows overlap: positive if they reinforce each other, negative if they fight.

**J times J-transpose** is two by two. It lives on the **hand** side. Each entry compares two rows. Total squared sideways leverage. Total squared vertical leverage. And the cross term: how much sideways and vertical are coupled.

Here's a feel for that coupling. Suppose you try to push the tip purely sideways, by moving each joint in proportion to its sideways leverage. The tip doesn't go purely sideways. It **leaks** downward too, because the joints that push sideways also push vertically. The off-diagonal term of J-J-transpose is the size of that leak.

But there are two special hand directions where there's **no leak.** Aim along one of them, and the tip goes exactly where you aimed. Those are the eigenvectors of J-J-transpose. They're also the axes of the manipulability ellipse. And the amount the tip moves along each is the stretch factor squared.

---

## The SVD in plain words

That brings in the singular value decomposition. Here it is in words only.

There are a few special joint mixes, call them v-one, v-two, v-three, all perpendicular to each other. And a few special hand directions, u-one and u-two, also perpendicular.

**Each joint mix lands on one hand direction, stretched by one number.** v-one lands on u-one, stretched by sigma-one. v-two lands on u-two, stretched by sigma-two. And v-three, the third mix, lands on **nothing**. v-three is the null line.

For this arm, sigma-one is about two and three quarters. Sigma-two is about six tenths. One strong channel, one weaker channel, one dead channel.

So that's how three perpendicular joint mixes fit into a two-dimensional hand space. **One of them lands on nothing.**

And the pair of rules to remember: **J times v equals sigma times u.** And going back, **J-transpose times u equals sigma times v.** Joint mix to hand direction, and hand direction back to joint mix.

---

## J-plus is the SVD run backwards

Now J-plus is easy to say.

**Step one.** Take the tip velocity you want, and split it into its u-one part and its u-two part.

**Step two.** Divide each part by its stretch factor. The strong channel needs only a little joint speed. The weak channel needs a lot.

**Step three.** Turn each part back into its joint mix, v-one and v-two, and add them up.

That's the joint speed J-plus returns.

For straight up at one metre per second, it comes out as: joint one at one third, joint two at minus one third, joint three at two thirds, all in radians per second.

And notice what never happened. **Nothing ever went into v-three.** No null motion at all. J-plus only builds answers out of the working channels. Keep that in mind for one more minute.

---

## The same answer, the leverage way

There's a second formula for J-plus, and it has a lovely physical meaning: **moment arm, divided by moment arm squared.**

Start with one joint and one direction. To make the tip move at speed v, a joint with moment arm r must turn at v over r. Simple division.

But a moment arm is really an arrow. You can't divide by an arrow. So instead, you **dot with the arrow**, and **divide by its squared length**. Same answer, but it works for arrows.

Now several joints, one direction. Each joint gets speed **in proportion to its own lever**, divided by the **total** squared leverage of all the joints together. A joint with twice the leverage does twice the work. Nobody fights.

Now two directions. The total squared leverage isn't one number anymore. It's the two-by-two J-J-transpose, with its leak between sideways and vertical. So you take its inverse. That inverse does two things at once: it divides by the total leverage, and it cancels the leak. Then J-transpose hands the result out to the joints, each in proportion to its leverage.

That's the formula: **J-transpose, times the inverse of J-J-transpose.** And in the SVD picture, the inverse divides each channel by sigma squared, and J-transpose multiplies one sigma back. Net: divide by sigma. Divide by the moment arm. **The two formulas are the same thing.**

---

## Why J-plus is the shortest answer

Back to the line of answers. Why does J-plus pick the point it picks?

Every answer on the line is J-plus's answer plus some amount of null motion. J-plus's answer lives entirely in the joint working plane. The null motion lives on the null line. And those two are perpendicular.

So it's Pythagoras. The squared length of any answer equals J-plus's squared length, **plus** the squared length of the null part. Adding null motion can only make it longer.

For straight up: J-plus's answer has length about point eight. Add one unit of null motion, and it grows to about one point three. Same tip velocity. More joint motion.

So **J-plus is the shortest answer. The least total joint motion.** That's the "minimum norm" you'll read about. And it's shortest precisely because it contains **no** null motion.

---

## The null projector

Now the clever part. That spare joint can be used on purpose.

Take J-plus times J. Read it right to left. Send a joint motion to the hand, then bring it back. The null part is lost on the way. The working part comes back unchanged. So J-plus-J **keeps only the working part.**

And the identity minus J-plus-J keeps **only the null part.** Call it N, the null projector.

So you can take **any** joint motion you'd like, for any reason at all, and pass it through N. What comes out is the piece of it the tip can't feel.

For example, say you'd like joint one to turn. Pass "turn joint one" through N, and what comes out is: turn joint one a little, and turn joints two and three back. The do-nothing motion. The tip stays put.

---

## The redundancy formula

Put the two pieces together, and you get the formula that redundant robots run every millisecond:

**Joint speeds equal J-plus times the task, plus N times whatever else you want.**

The first part does the task. The second part is invisible to the tip. They live in perpendicular pieces of joint space, so they **can't interfere.** Whatever you choose for the second part, stay away from joint limits, avoid an obstacle, keep the elbow up, the task is untouched.

And here's the classic bug. **Forget the N.** Just add your extra joint motion straight on. Then its working part leaks into the hand, and the tip drifts off the path. The lab on this page has a "wrong" switch that shows exactly that.

---

## Using the spare joint to stay healthy

One beautiful use of that second part: **avoiding singularities.**

Remember manipulability, the health score of a pose. It's the product of the stretch factors. It drops to zero at a singularity.

So compute the joint motion that raises the health score fastest. That's its gradient. Pass it through N. Add it to the task.

Now picture the arm nearly folded up, close to a singularity, with the tip asked to hold still. The arm slowly **opens itself up** into a comfortable triangle, the health score climbs, and the **tip doesn't move at all.**

Two honest limits. This fixes posture singularities, where the elbows are badly arranged. It can't fix the edge of reach, where the arm is simply stretched to its limit. And it never costs any tip accuracy, because it lives entirely in the null space.

---

## The other shape: more task than joints

So far, more joints than task numbers. The Jacobian is short and wide. Now flip it.

Take the four-joint RRPR arm from the workshop, with a full six-number pose. Its Jacobian is **six by four**. Tall and narrow.

Now there's no spare joint. There's a missing direction, two of them. The joint null space is empty. But the hand unreachable space is two-dimensional. Some tip twists simply can't be made.

So J-plus can't give an exact answer. It gives **the closest one**: the joint speeds whose twist comes nearest to what you asked for. Least squares. The unreachable part is just dropped.

And the formula flips too. This is the question that trips everybody up. For the tall Jacobian, you **don't** invert J-J-transpose. That's six by six. It's built from only four joint columns, so it has only four healthy directions and two dead ones. Its determinant is zero. It can't be inverted.

Instead, you invert **J-transpose-J**. That's four by four, on the joint side, and it's healthy. The formula becomes: **the inverse of J-transpose-J, times J-transpose.**

The rule of thumb: **always invert the small one.** Short and wide, invert J-J-transpose, on the hand side. Tall and narrow, invert J-transpose-J, on the joint side. The big one is always singular.

And both are the same J-plus, the SVD run backwards. Only the route differs.

---

## Near a singularity, and weighting

Two last refinements.

**Near a singularity**, one sigma gets tiny, and dividing by it gives huge joint speeds. The damped version divides by sigma squared plus a small lambda squared, and multiplies by sigma. In healthy channels, nothing changes. In the weak channel, the answer fades gently to zero instead of blowing up. You lose a little accuracy in that one weak direction, and you gain a calm arm.

**Weighting.** J-plus minimises the plain sum of squared joint speeds. But maybe some joints are expensive to move: a big heavy shoulder. A weighted pseudoinverse makes those joints count more, so the answer leans on the cheap ones. Choose the arm's own mass matrix as the weight, and it minimises kinetic energy. The structure never changes: **among all motions that do the job, pick the cheapest by your measure.**

---

## Interview question

**"Your robot has seven joints and a six-number task. How do you use the extra joint?"**

Joint speeds equal J-plus times the task twist, plus the null projector times a secondary motion. J-plus gives the minimum-norm solution for the task. The null projector, identity minus J-plus-J, strips the secondary motion of anything the hand would feel. Use it to stay away from joint limits, avoid obstacles, or climb the manipulability gradient away from singularities. Add damping near singularities. And never add the secondary motion without the projector.

A strong follow-up: **for a tall Jacobian, invert J-transpose-J, not J-J-transpose.** Interviewers love that one.

---

## Carry forward

**One.** **Two spaces.** Joint space, three numbers here. Hand space, two numbers. The Jacobian goes from joint space to hand space.

**Two.** **Four pieces.** Joint working space and joint null space, perpendicular. Hand reachable space and hand unreachable space, perpendicular. J maps working onto reachable and kills null. J-plus does the reverse.

**Three.** **J-plus is the SVD run backwards.** Split along the u's, divide by each sigma, rebuild with the v's. Or the leverage way: **moment arm over moment arm squared.**

**Four.** **J-plus is the shortest answer** because it has no null part. Any null motion adds length, by Pythagoras.

**Five.** **The null projector, identity minus J-plus-J**, lets the spare joints do other jobs, invisible to the tip. Forget it, and the hand drifts.

**Six.** **Invert the small one.** Short and wide: J-J-transpose. Tall and narrow: J-transpose-J.

Next up: the **C++ workshop**, page 131, where you build all of this yourself, from the determinant to the null motion.
