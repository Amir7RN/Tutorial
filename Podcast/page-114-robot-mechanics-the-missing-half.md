# Page 114 — Robot Mechanics: The Missing Half

*Listening script. Roughly fifteen minutes. Every page before this one controlled a plant somebody handed you. This block derives the plant.*

---

## Why the control pages were not enough

For a hundred-odd pages, the plant was a given. **J theta double dot plus b theta dot equals tau** for one joint. Or, quoted once on the arm capstone, **M of q, q double dot, plus C q dot, plus g, equals tau** — and then straight on to pole placement, PID, LQR.

That is fine until an interviewer asks one level lower. **Where does that equation come from? Why is M symmetric and positive definite? What is the Jacobian's null space for? How do you make the hand follow a straight line while the elbow does something else?**

None of those are control questions. They are **kinematics and dynamics** questions, and no amount of pole placement answers them. That is the missing half, and this block is where it gets filled in.

---

## The whole block in one line

Here is the chain of ideas, and it is genuinely one line long. Every page in the block is one link of it.

**q, goes to T of q, goes to V equals J of q times q dot, goes to tau equals J transpose F, goes to tau equals M of q q double dot plus c plus g.**

Read it like a recipe, left to right.

**q** is the list of joint angles. Think of them as the robot's knob settings.

**T of q** is where the hand is, and which way it points, for those knob settings. That is forward kinematics.

**V equals J q dot.** If the knobs turn at some speeds, J tells you how fast the hand moves. **J is a table of "how much hand motion per unit of each joint's motion."** That is the Jacobian.

**Tau equals J transpose F.** The same table, flipped on its side, tells you which motor torques make the hand push with a force F. That is statics, and the fact that one matrix does both jobs is not a coincidence — it is power conservation, and you will see it derived.

**And the last arrow is Newton's F equals m a, written for a robot.** Torque equals mass times acceleration, plus forces caused by the joints already spinning, plus whatever it takes to hold the weight up.

So the block answers three questions about any arm, in order. **Where is the hand?** That is pages 115 to 119. **How fast and how hard can the hand move when the motors turn?** That is the Jacobian, pages 120 to 124. **What motor torques does a given motion need?** That is dynamics, pages 125 to 131. The pages after that use all three answers to plan and control the arm.

---

## The twelve playlists

The block walks Kevin Lynch and Frank Park's Modern Robotics course from Northwestern — twelve playlists, one per book chapter — in order.

Playlist one, **configuration space**: degrees of freedom, Grübler's formula, constraints, task space and workspace. Playlist two, **rigid-body motions**: rotation matrices, exponential coordinates, twists, screws, wrenches. Three is **forward kinematics** with the product of exponentials. Four is **velocity kinematics and statics**: the Jacobian, singularities, manipulability. Five is **inverse kinematics**. Six, **closed chains** — four-bars, Stewart platforms. Seven, **dynamics of open chains** — Lagrange, the mass matrix, Newton–Euler. Eight, **trajectory generation**. Nine, **motion planning**. Ten, **robot control**. Eleven, **grasping and manipulation**. Twelve, **wheeled mobile robots**.

Every page in the block carries a badge naming its playlist, and opens with a "watch alongside" link. So the videos and the pages can be read side by side.

---

## How to study it: videos first, or pages first?

**Neither on its own.** The pages are compressed; they assume you have seen the derivation once. The videos are slow and careful, but give you nothing to touch. So use them together, one page at a time, in four steps.

**Step one.** Read the page's START HERE box and every IN PLAIN WORDS box first. About five minutes. Skip every formula. The only goal is to know which question the page answers.

**Step two.** Watch that page's playlist. The videos are three to eight minutes each. **Pause on every boxed equation and say what each symbol is, in words.** If you cannot say it, you have not got it yet.

**Step three.** Come back and do the lab. Move one slider at a time. **Predict what will happen before you look.** Then compare with the plain-words box under the lab.

**Step four.** Say the interview answer out loud, without reading it. If you cannot, go back to step one — for that page only.

And one honest warning. **Pages 115 to 118 are vocabulary.** Configuration space, topology, rotation matrices, twists. It is normal for them to feel abstract and a bit pointless. They stop feeling that way around page 120, when the Jacobian starts using every word on every line. If a formula still makes no sense after the video, do not stop there: later pages use the *result*, not the derivation.

---

## What to master for an interview, ranked

Six items, in order of how often they come up.

**One — the Jacobian, both directions.** x dot equals J q dot for velocity. Tau equals J transpose F for force. And *why* the same matrix does both: because power is the same number in every frame.

**Two — singularities and the null space.** A rank-deficient J. The manipulability ellipse. The pseudo-inverse J plus. The null-space projector, I minus J plus J. Self-motion — moving your elbow while your fingertip stays on the desk.

**Three — inverse versus forward dynamics.** Torque from position, velocity and acceleration, by recursive Newton–Euler, in order n time. Acceleration from torque, by solving M q double dot equals tau minus h.

**Four — the properties of M and C.** M is symmetric, positive definite, and changes with configuration. And M dot minus two C is skew-symmetric — which is the passivity property that every Lyapunov proof for robot arms leans on.

**Five — task-space dynamics.** Lambda equals the inverse of J M inverse J transpose: the mass the hand feels. The dynamically consistent inverse. The null-space torque projector.

**Six — the control built on all of it.** Computed torque, operational space control, impedance and hybrid force control.

**Do not try to master the list on the first pass.** Items one and two are the kinematics pages. Three to five are dynamics. Six is robot control. And if you only have time for one idea, take the Jacobian — almost everything else on the list is built out of it.

---

## Why the planar arm, over and over

You will notice the block keeps reusing a two- or three-link planar arm. That is on purpose.

**A planar 2R or 3R arm has every structure a seven-degree-of-freedom manipulator has.** Coupling between joints. Coriolis terms. Gravity. Singularities. Redundancy. All of it — but with matrices small enough to check by hand on a whiteboard.

**Which is exactly where the interview will put you.**

---

## Carry forward

**One.** The block answers three questions in order: where is the hand, how fast and how hard can it move, what torque does a motion need.

**Two.** The whole thing is one chain: **q, to T of q, to J q dot, to J transpose F, to M q double dot plus c plus g.** Every page fills in one arrow.

**Three.** Study each page in four steps: plain-words boxes, then the video, then the lab, then the interview answer out loud.

**Four.** The first few pages are vocabulary. Trust that the Jacobian will make them pay off.

Next page starts the vocabulary: **what is the smallest list of numbers that tells you exactly how a robot is posed — and what shape does the space of all those lists have?**
