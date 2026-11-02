# Page 96 — Inside the TwinCAT Code: DDPG in Real-Time C++

*Listening script. Roughly twenty minutes. Made for the car: audio only, nothing to look at. It walks the whole code base of the knee-prosthesis learner, file by file, then the timing tricks, then the honest list of what is wrong in it. Every number is said once so you hear its shape. The page keeps them all.*

---

## The question

Most reinforcement learning stories end in Python. You train in a simulator, you export a network, maybe to ONNX, and a runtime on the robot plays it back. The robot never learns. It only replays.

This project is different, and that difference is the whole point of the page. The learner lives on the robot. A knee prosthesis walks, and while it walks, a DDPG agent, an actor and a critic, keeps training, inside TwinCAT, in hand-written C++, with no Python anywhere in the loop. And it does that next to a control loop that must close every single millisecond, without ever missing one.

So the question for this page is simple to say. How do you run gradient descent on a machine that is also responsible for a human being's knee, a thousand times a second, without the learning ever getting in the way of the control?

The answer has three parts. Two clocks. A shared piece of memory that nobody has to lock. And a rule about *when* things are allowed to happen. Let's take them one at a time.

---

## The map of the code

There are two TwinCAT modules. Think of them as two programs living in the same real-time kernel.

The first is **RT Control**. That's the fast one. It reads the sensors, runs the policy, and writes the motor torque.

The second is **RL Trainer**. That's the slow one. It owns the replay buffer, the critic, the target networks, and Adam. It does the learning.

Around them sit a handful of shared files. **DDPG Networks dot h** holds the layers: dense layers, batch norm, ReLU, tanh, written out by hand with fixed-size arrays. There is a copy of it inside each module. **Gait State Estimator** turns a raw stream of knee angle and load into five numbers that describe one stride. **Shared Defs dot h** defines the one structure both modules agree on: the shared memory block. And then there's the project file, the **dot t s proj**, which is the part people forget to read, because it's XML. But it's where the timing actually lives.

---

## Two clocks

Open the project file and you find two tasks.

The **fast task** has a cycle time of ten thousand ticks of one hundred nanoseconds. That's one millisecond. A thousand hertz. Priority one, the highest.

The **slow task** has a cycle time of half a million ticks. That's fifty milliseconds. Twenty hertz. Priority two.

RT Control runs on the fast task. RL Trainer runs on the slow task.

Here's why the priorities matter more than the periods. In a real-time kernel, a higher-priority task *preempts* a lower one. So when the slow trainer is halfway through a matrix multiply and the next millisecond arrives, the trainer is frozen right where it stands, the controller runs its tick, and then the trainer picks up exactly where it stopped. The trainer can take twenty milliseconds of wall-clock time for its work, and the controller still sees every one of its ticks on time.

That is the first idea of the page, and it's worth saying plainly: **the control loop is protected by the scheduler, not by the learner being polite.** You don't have to make the training small enough to fit between ticks. You only have to make sure the fast task's own work fits in a millisecond, and that the slow task finishes inside its fifty.

---

## One millisecond in the life of the controller

Now let's walk through what RT Control does on every tick. Picture the cycle update function from top to bottom.

**First, read.** The knee angle, the knee velocity, and the force from the load cell under the foot.

**Second, feed the gait estimator.** Every tick, the angle goes into a buffer. The buffer has room for two thousand samples, which is two seconds at a kilohertz. Plenty for one stride.

**Third, watch for heel strike.** When the load cell force crosses a threshold of twenty, the foot has just landed. That moment ends one stride and starts the next. Almost every tick is *not* heel strike. One tick per stride is.

**Fourth, compute the torque.** This is an impedance law, a virtual spring and damper. Torque equals a stiffness K times the angle error, minus a damping B times the velocity. The equilibrium angle is zero and the damping is one point five. The stiffness K is the thing the policy chooses.

**Fifth, write.** The torque goes out to the drive.

That's it for an ordinary tick. Notice what's *not* in there. No neural network. On a normal tick, the controller only does a handful of multiplies. The network runs once per stride, not once per tick.

---

## The heel-strike tick

Now the one special tick.

When heel strike happens, the controller has a complete stride sitting in its buffer. So it does four extra things, all on that same tick.

**One: summarise the stride.** The gait estimator takes however many samples the stride had, and resamples them to exactly one hundred points. Then it pulls out five numbers. The angle at heel strike. The peak knee flexion during stance. The valley during stance. The peak during swing. And the correlation between this stride and a reference healthy trajectory. Those five numbers are the **state**.

The **reward** is that correlation, squared. The closer this stride looks like a healthy knee, the higher the reward.

**Two: push the experience.** State, action, reward, next state, packed into a small record of thirteen doubles. That's one hundred and four bytes. It goes into a ring buffer in shared memory, for the trainer to pick up later.

**Three: check for new weights.** If the trainer has finished an update, a flag called *new weights available* is set. If it is, the controller copies the actor's weights out of shared memory into its own private copy, and clears the flag.

**Four: run the actor once.** Five inputs in, through a layer of two hundred and fifty, through a second layer of two hundred and fifty with batch norm, out through tanh to two numbers. The first output sets the stiffness: K equals fifty plus ten times that action, clamped between ten and ninety. That stiffness then holds for the whole next stride.

So the expensive work, the network and the weight copy, all lands on one tick per stride. Which makes the heel-strike tick the **worst-case tick**. And in real-time work, the worst case is the only case that counts. Your average doesn't matter. Your one bad tick does.

---

## The other side: the trainer

Now switch over to the slow task.

Every fifty milliseconds, RL Trainer wakes up. First, it drains the ring buffer: any new strides the controller pushed go into its replay buffer.

Then it asks one question: **have at least four new strides arrived since the last update?** If not, it goes back to sleep. Nothing to do. Most slow-task cycles end right there, in a few microseconds.

If yes, it runs a **train step**. It samples a batch of eight experiences. For each one, it runs the critic forward, computes the temporal-difference target with a discount of zero point nine nine, backpropagates, and lets Adam update the critic with a learning rate of one in a thousand. Then it does the actor update, with a learning rate ten times smaller. Then it flattens the actor's weights into one long array in shared memory, and raises the *new weights available* flag.

And that's the second idea of the page. **Learning is gated by strides, not by time.** One stride of walking is about a second. Four strides is about four seconds. So the network updates every few seconds, in one burst, on the low-priority task, while the high-priority task keeps carving the burst into millisecond slices.

A note on honesty, because an interviewer may push on it. In this code, one train step runs inside a single slow-task call. It is not hand-split into chunks across many cycles. The spreading-out comes from two things: the four-stride gate, which makes updates rare, and preemption, which makes the fast loop immune to how long they take. If you say "I distributed the work over cycles," say it that way: the scheduler distributes it, and the gate keeps it rare.

---

## Shared memory with no locks

So how do the two modules talk?

The trainer owns a block of memory by value: a structure called shared data. The project file contains a link that hands the controller a *pointer* to that same block. One structure, two views of it, no copy in between.

Inside that block there are two channels, going in opposite directions.

**Going up, controller to trainer: experience.** A ring buffer of three hundred slots, each one hundred and four bytes. About thirty kilobytes in total. The controller is the only writer of the head. The trainer is the only writer of the tail. That's the classic **single-producer, single-consumer** ring. Because each index has exactly one writer, nobody needs a mutex. And you never want a mutex in a one-kilohertz loop, because a mutex is a promise that you might wait, and a real-time task can't promise that.

**Going down, trainer to controller: weights.** A one-slot mailbox. The trainer writes the whole array, *then* sets the flag. The controller sees the flag, copies the array, *then* clears the flag. The trainer won't write again until the flag is clear. The flag is the handshake. Order is everything here: data first, flag second, on both sides.

Now the bandwidth. Going up is nothing: a hundred and four bytes per stride. Going down is the interesting one. The weight array that the controller imports is sixty-five thousand two hundred and fifty-two doubles. At eight bytes each, that's about five hundred and twenty-two kilobytes. Averaged over four strides, that's only around a hundred and thirty kilobytes a second. Trivial. But averaged is the wrong word. All five hundred kilobytes move on *one tick*, the heel-strike tick. Bandwidth in real-time is not about throughput. It's about the size of the burst on your worst tick.

---

## The budget in numbers

Let's put numbers on that worst tick, because this is exactly the conversation a robotics team at a company like NVIDIA wants to have.

**The actor forward pass.** Five times two-fifty, plus two-fifty times two-fifty, plus two-fifty times two. That's sixty-four thousand, two hundred and fifty multiply-adds. Call it sixty-four thousand.

**The training step.** A critic forward and backward, an actor forward and backward, times a batch of eight, plus the target computations and Adam over sixty-five thousand parameters each. The page estimates it at about five point one million multiply-adds. Roughly eighty times the forward pass.

Now pick a modest CPU that does, say, one billion multiply-adds a second in this plain C++ style. Then the forward pass is about sixty-four microseconds. Comfortably inside a thousand. The train step is about five milliseconds. Comfortably inside its fifty-millisecond slot. And the weight copy, five hundred kilobytes at a few gigabytes a second, is on the order of a hundred microseconds or two.

Add them up for the heel-strike tick: a forward pass, a weight copy, the resampling of the stride, and the ordinary control law. A few hundred microseconds. Under half the millisecond. That's your margin.

The page has sliders for exactly this. CPU speed, memory bandwidth, batch size, stride period. Drag them and watch which one dominates. The lesson you'll find is a surprising one: on most settings, **copying the weights costs more than using them**. The forward pass touches each weight once. The import touches each weight once *too*, and writes it. Memory, not arithmetic, sets the worst tick. That's a sentence worth bringing into the room.

---

## Determinism by construction

Fast is not the goal. *Predictable* is the goal. A controller that's usually fast and occasionally slow is a broken controller. So here's how this code makes timing predictable, and these are the implementation tricks worth remembering.

**Fixed-size arrays everywhere.** Every layer, every buffer, every gradient is a plain C array with its size known at compile time. No vectors that grow.

**No allocation in the loop.** No new, no malloc, after start-up. An allocator can take a lock, or walk a free list of unknown length. Neither belongs in a cyclic task.

**Same work every time.** The forward pass is the same nested loops, the same counts, no early exits, no data-dependent branches. Its cost on the first stride and the thousandth stride is the same.

**Expensive work at a known moment.** The network and the weight copy only happen at heel strike, and only one stride at a time. You know exactly which tick carries the cost, so you can measure exactly that tick.

**Lock-free hand-off.** One writer per index, a flag for the mailbox. Nobody ever waits on anyone.

**Reproducible starting point.** The initial weights come from a fixed seed, so a run can be repeated, and a bad run can be replayed.

If you remember one sentence from this section: **determinism is a design property, not a tuning result.** You don't get it by optimising. You get it by never letting the loop do anything whose cost depends on the data.

---

## Why not ONNX

The question will come, so have the answer ready.

ONNX, TensorRT, any inference runtime, solves *inference*. Forward pass only. You train somewhere else and ship the frozen result. That's the right tool for a policy trained in simulation, and on a GPU platform like Jetson it's exactly what you'd use.

But this project trains *on the device*, online, while the person walks. That means backward passes, Adam state, target networks, a replay buffer. No inference runtime gives you that inside a hard real-time kernel. Writing the layers yourself gives you three things in return: you know every allocation, because there are none; you know every loop bound, so you can bound the worst case; and you can split the work across two priority levels exactly the way you want.

The cost is honest too. Every layer, every gradient, every optimizer step is code you wrote and code you must test. Which brings us to the next part.

---

## The audit: what's wrong in this code

The page ends with an audit table. These are the things an interviewer could find if they read the code, and you want to have found them first. Here are the important ones, in plain words.

**One. The weight layouts don't match.** The trainer's export function writes the dense layers but skips the batch-norm values. The controller's import function expects the batch-norm values to be in there. So everything after the first gap is read from the wrong place. The actor on the controller is not exactly the actor the trainer trained. This is the biggest one, and it's a classic serialisation bug: two sides of a boundary, each correct by itself, disagreeing about the format.

**Two. The actor update has the wrong sign.** The actor should climb the critic: move toward actions with *higher* Q. Adam *subtracts* the gradient. The code hands Adam the gradient of Q with respect to the action, so it descends. The actor is pushed toward *lower* value. The fix is a minus sign: give Adam the negative of that gradient.

**Three. The critic gradient is taken at the wrong point.** For the actor update, you need the critic evaluated at the state and the actor's *own* action, mu of s. The code calls the critic's backward pass without first running the forward pass at that action, so the gradient comes from whatever the critic last saw, which is the stored action from the replay buffer.

**Four. The target networks never move.** The soft update, the slow blend of the main networks into the targets, is still a to-do. So the targets stay frozen at their starting weights.

**Five. Adam's bias correction is a constant.** It divides by one minus beta, instead of one minus beta to the power t. So the early steps are scaled wrong.

**Six. The stride resampling has the wrong bound.** The interpolation checks that its index is less than one hundred, the target size, instead of less than N, the real number of samples. For a normal stride with hundreds of samples, most of the resampled curve collapses into one repeated value. That quietly damages four of your five states and the reward.

**Seven. No exploration noise.** DDPG needs noise on the action to explore. This code doesn't add any.

And then a few smaller ones. Gradients are overwritten per sample instead of summed, so a batch of eight is really eight small steps in a row. The torque is cast from a double straight into a sixteen-bit integer with no saturation, so a large command can wrap around to the opposite sign. That's the dangerous one for hardware, and the fix is a clamp before the cast. The reward is correlation *squared*, so a stride that's perfectly *anti*-correlated scores as well as a perfect one. The batch size is defined three different ways in three headers. And the second action output is computed and never used.

Here's how to talk about this list. Not as embarrassment. As evidence. You know where on-device learning breaks: at the serialisation boundary, at signs and conventions in the optimizer, at numeric casts going to hardware. Those are exactly the cross-boundary bugs the job description is talking about.

---

## Where the deck and the code disagree

One practical warning before the interview. Your slide on the trainer says it runs at a hundred hertz, with a batch of sixteen and soft target updates. This code says fifty milliseconds, an effective batch of eight, and the soft update left as a to-do. Another slide says Gaussian noise was added to the weights; this code adds none.

Maybe the version that ran on the device was newer. That's fine. Just pick one set of numbers and say it the same way every time. An interviewer who hears a hundred hertz on one slide and fifty milliseconds out of your mouth will ask, and you'd rather spend that minute on something better.

---

## What carries over to a humanoid

Last part. Why does any of this matter to a team building a humanoid reference platform?

Because the shape is the same, just bigger. A humanoid has a fast loop, joint-level torque or impedance control at a kilohertz or more. It has a slower loop, a learned policy running maybe at fifty to a few hundred hertz. And it has something slower still, perception, planning, or adaptation. Each boundary between those loops is the same problem you solved here. What crosses the boundary, how big is the burst, who writes and who reads, and what happens to the fast loop when the slow one runs long.

So the story you tell is this. I ran learning and control on the same real-time machine. I separated them by priority, not by hoping. I moved data between them without locks. I knew the cost of my worst tick, and I knew it was memory, not math. And when the policy misbehaved, I traced it across the boundary, from a reward that looked wrong, back through the state estimator, down to a loop bound in a resampling function.

That's the page. Two clocks. One shared block with no locks. Expensive work at a known moment. And an honest list of what to fix next.
