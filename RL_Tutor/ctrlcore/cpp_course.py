"""
The C++ for Robotics course: exercises, builds and grading -- no Qt in here.

Every exercise lives in cpp/learn/exercises/<id>/:

    starter/    the files you edit (copied once into cpp/learn/work/<id>/)
    solution/   reference versions of the files that change
    given/      read-only files the exercise depends on
    test/       test_main.cpp (+ helpers) that the grader links instead of main.cpp

Project files shared by several exercises (signals.hpp, motor.hpp, ...) live in
cpp/learn/exercises/_project/ and are listed per exercise in `project`.

A test main prints one line per check, "PASS name" or "FAIL name | why", then
"DONE". A mutation exercise is graded the other way round: the learner writes
the tests, and they must pass on the correct code and fail on every mutant.

The GUI runs the same `plan()` with QProcess so nothing blocks; the tests in
tests/test_cpp_course.py run it with subprocess.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "cpp", "learn"))
EXERCISES_DIR = os.path.join(ROOT, "exercises")
PROJECT_DIR = os.path.join(EXERCISES_DIR, "_project")
SUPPORT = os.path.join(ROOT, "support")
WORK = os.path.join(ROOT, "work")
BUILD = os.path.join(ROOT, "build")
PROGRESS = os.path.join(WORK, "progress.json")

CXXFLAGS = ["-std=c++17", "-O1", "-Wall", "-Wextra", "-Wno-unused-parameter",
            "-Wno-unused-variable", "-Wno-unused-but-set-variable",
            "-fdiagnostics-color=never", "-pthread", "-static"]


@dataclass(frozen=True)
class Rule:
    """A check on the learner's SOURCE text, for things a test cannot see."""
    label: str
    pattern: str            # regex, searched in `file` (comments stripped)
    file: str
    must_match: bool = False


@dataclass(frozen=True)
class Exercise:
    id: str
    title: str
    task: str                                  # HTML
    hints: tuple = ()
    explain: str = ""                          # shown with the solution: why it is written this way
    project: tuple = ()                        # files taken from exercises/_project
    starter_compiles: bool = True              # False when the compile error IS the exercise
    rules: tuple = ()
    mutants: tuple = ()                        # ((k, description), ...) -> mutation-graded
    tools: bool = False                        # show "what the compiler sees" buttons
    stage: str = ""


# =====================================================================
# the exercises
# =====================================================================

_EX = [
    # ------------------------------------------------------------ stage 0
    Exercise(
        "s0_header", "Split a PID into a header and a source file",
        "Two things are wrong, and the tools tell you which in order. <b>Check</b> first: "
        "the <i>compiler</i> stops at <code>redefinition of 'class Pid'</code>, because the test "
        "includes <code>pid.hpp</code> twice and it has no include guard. Fix that, check again: "
        "now the <i>linker</i> says <code>undefined reference to Pid::update</code>, because "
        "<code>pid.cpp</code> declares nothing. Define the four members there.",
        hints=("Line 1 of the header: <code>#pragma once</code>.",
               "In pid.cpp every definition needs the class prefix: "
               "<code>double Pid::update(double error) { ... }</code>. Without <code>Pid::</code> you "
               "define a free function nobody calls, and the linker still cannot find the member.",
               "The constructor uses an initialiser list: "
               "<code>Pid::Pid(double kp, double ki, double kd, double dt) : kp_(kp), ki_(ki), kd_(kd), dt_(dt) {}</code>"),
        explain="The header lists what callers may do; the .cpp holds how. Change the algorithm and "
                "only pid.cpp recompiles. <code>integral() const</code> promises not to change the "
                "object, so it can be called through a <code>const Pid&amp;</code>.",
        starter_compiles=False, tools=True, stage="0"),
    Exercise(
        "s0_linker", "Make the linker happy: one definition rule",
        "Every file compiles on its own, then linking fails with <code>multiple definition of "
        "`clamp(double, double, double)'</code> and <code>multiple definition of `g_ticks'</code>. "
        "Each .cpp that includes <code>helpers.hpp</code> gets its own copy of both, and the linker "
        "refuses to choose. Keep exactly one definition of each in the program. Use the "
        "<b>symbols</b> tool on sensor.cpp before and after: a <code>T</code> or <code>B</code> next to a "
        "name means \"defined here\", <code>U</code> means \"needed from elsewhere\".",
        hints=("Header: declarations only. <code>double clamp(double x, double lo, double hi);</code> and "
               "<code>extern int g_ticks;</code>",
               "helpers.cpp: the one real definition of each, the body of clamp and "
               "<code>int g_ticks = 0;</code>",
               "The C++17 alternative is to write <code>inline</code> in front of both in the header. "
               "Either passes; know both."),
        explain="<code>extern</code> means \"declared here, defined in exactly one other place\". "
                "<code>#pragma once</code> works inside one translation unit only, which is why it "
                "could not help here.",
        starter_compiles=False, tools=True, stage="0"),
    # ------------------------------------------------------------ stage 1
    Exercise(
        "s1_raii", "RAII: a buffer that frees itself",
        "Write the constructor and destructor of <code>SampleBuffer</code>. The test counts every "
        "heap allocation in the program, so it can tell whether yours happened and whether the "
        "closing brace gave it back. Copying is already deleted; the page explains why.",
        hints=("Constructor initialiser: <code>: data_(new double[n]()), size_(n)</code>. "
               "The <code>()</code> after <code>[n]</code> zeroes the doubles.",
               "Destructor: <code>delete[] data_;</code>. Use <code>delete[]</code> for "
               "<code>new[]</code>, never plain <code>delete</code>."),
        explain="The destructor runs on every way out of a scope: return, break, exception. That "
                "is the whole of RAII. In real code you would hold a <code>std::vector</code> or "
                "<code>std::unique_ptr&lt;double[]&gt;</code>, and write no destructor at all.",
        stage="1"),
    Exercise(
        "s1_unique", "unique_ptr: exactly one owner",
        "A <code>Joint</code> owns at most one controller. Fill in the five TODOs. The test "
        "moves a controller in, checks that the caller's pointer became empty, replaces it and "
        "checks that the old one was freed, then takes it back out.",
        hints=("<code>return std::make_unique&lt;Pd&gt;(Pd{kp, kd});</code>",
               "<code>ctrl_ = std::move(c);</code> Assigning into a unique_ptr frees whatever it held before.",
               "<code>return ctrl_ ? ctrl_-&gt;update(error, dt) : 0.0;</code>"),
        explain="Pass a <code>unique_ptr</code> by value to mean \"give me this\"; pass a "
                "<code>T&amp;</code> or <code>T*</code> to mean \"let me use it, you keep it\". "
                "Ownership is part of the function signature.",
        stage="1"),
    Exercise(
        "s1_leak", "Find and fix the leak, with no delete",
        "<code>recentMean</code> returns the right numbers and leaks on three of its four "
        "paths. Rewrite it so that every return path frees the memory, without writing "
        "<code>delete</code> anywhere.",
        hints=("<code>std::vector&lt;double&gt; tmp(window);</code> frees itself on every return.",
               "Better still, return early <i>before</i> allocating anything."),
        explain="A raw <code>new</code> paired by hand with a <code>delete</code> is correct only until "
                "someone adds a return in between. An owning type keeps it correct for good.",
        rules=(Rule("no raw delete in your fix", r"\bdelete\b", "window.hpp"),
               Rule("no raw new either", r"\bnew\b", "window.hpp")),
        stage="1"),
    Exercise(
        "s1_shared", "shared_ptr and weak_ptr: owners and observers",
        "A <code>Planner</code> shares ownership of a <code>Model</code>; a <code>Logger</code> only "
        "observes it. The test counts owners with <code>use_count()</code> and then destroys the "
        "owners one at a time.",
        hints=("Planner: <code>: model_(std::move(m))</code>. Moving avoids an extra atomic increment.",
               "Logger: <code>: model_(m)</code>. A weak_ptr is constructed from a shared_ptr.",
               "<code>if (auto m = model_.lock()) return m-&gt;name;</code>"),
        explain="<code>shared_ptr</code> is right when lifetime really is shared, and it costs "
                "an atomic reference count plus a control block. Use it less often than "
                "<code>unique_ptr</code>. <code>weak_ptr</code> breaks reference cycles and lets an "
                "observer check whether the object still exists.",
        stage="1"),
    # ------------------------------------------------------------ stage 2
    Exercise(
        "s2_rule5", "The rule of five, written once",
        "<code>Trajectory</code> owns a raw buffer, so the compiler's member-wise copy is wrong. "
        "Write a deep copy constructor, an assignment operator that is safe for "
        "<code>t = t</code>, and moves that steal the buffer and leave the source empty. The test "
        "checks pointers and allocation counts.",
        hints=("Copy constructor: allocate <code>new double[other.n_]</code>, then <code>std::copy</code>.",
               "Copy assignment, copy-and-swap: <code>Trajectory tmp(other); std::swap(n_, tmp.n_); "
               "std::swap(q_, tmp.q_); return *this;</code>. tmp's destructor frees the old buffer.",
               "Move constructor: <code>: n_(std::exchange(other.n_, 0)), q_(std::exchange(other.q_, nullptr))</code>"),
        explain="Better still is the rule of zero: hold a <code>std::vector&lt;double&gt;</code> and "
                "write none of the five. You write them by hand only when you build an owning type "
                "yourself, such as a real-time pool or a GPU buffer handle.",
        stage="2"),
    Exercise(
        "s2_const", "const correctness",
        "<code>kineticEnergy</code> takes a <code>const JointState&amp;</code>, so this does not "
        "compile until the read-only members say they are read-only. Also stop "
        "<code>positions()</code> from copying the vector on every call.",
        hints=("Add <code>const</code> after the parameter list: <code>std::size_t dof() const</code>.",
               "<code>const std::vector&lt;double&gt;&amp; positions() const { return q_; }</code>"),
        explain="<code>const</code> on a member function is documentation the compiler checks. "
                "A reviewer reading <code>const T&amp;</code> parameters and const getters knows what "
                "cannot change without reading the bodies.",
        starter_compiles=False,
        rules=(Rule("no mutable", r"\bmutable\b", "joint_state.hpp"),
               Rule("no const_cast", r"\bconst_cast\b", "joint_state.hpp")),
        stage="2"),
    # ------------------------------------------------------------ stage 3
    Exercise(
        "s3_limits", "An invariant: lo <= hi, always",
        "<code>Limits</code> promises <code>lo() &lt;= hi()</code> at all times. Make the "
        "constructor and <code>setRange</code> refuse to break that promise, and make a refused "
        "<code>setRange</code> leave the old range intact (the strong guarantee).",
        hints=("Write one private <code>static void validate(double lo, double hi)</code> and call it "
               "from both places.",
               "<code>if (!(lo &lt;= hi)) throw std::invalid_argument(\"...\");</code> also rejects NaN.",
               "In setRange, validate <i>first</i> and assign after."),
        explain="This is why the members are private. With public <code>lo</code> and <code>hi</code> "
                "anyone could break the promise, and every caller of clamp() would have to "
                "re-check it. Inside a class it is checked once, at the door.",
        stage="3"),
    Exercise(
        "s3_lowpass", "Decide what a class stores",
        "Implement the low-pass filter. Before writing any code, decide what it has to remember "
        "between calls. It does not need <code>fc</code> or <code>dt</code> after construction. The "
        "test checks the numbers and that the object is no larger than it needs to be.",
        hints=("Two members: <code>double alpha_;</code> computed once, and <code>double y_ = 0.0;</code>.",
               "<code>alpha_ = dt / (dt + 1.0 / (2.0 * pi * cutoffHz));</code>",
               "<code>double update(double x) { return y_ += alpha_ * (x - y_); }</code>"),
        explain="Store what defines the behaviour, not the inputs that produced it. If you stored "
                "fc and dt as well, you would have two copies of one fact that could disagree.",
        stage="3"),
    Exercise(
        "s3_reconstruct", "Reconstruct a header from its specification",
        "The file contains only a specification. Write the whole class from it. This is the "
        "\"read a header, close it, write it\" habit described on this page. Afterwards, compare "
        "your header with the reference: every difference is a design decision worth one sentence.",
        hints=("Invariant: the maximum step is positive. Store <code>maxStep_ = maxRate * dt</code>, "
               "because that product is all step() uses.",
               "Declaring <code>RateLimiter(double maxRate, double dt)</code> and no default "
               "constructor already makes <code>RateLimiter r;</code> a compile error.",
               "<code>output()</code> and <code>maxStep()</code> are <code>const</code>."),
        explain="Read the specification as three questions: what promise is kept, what must be "
                "stored, and what may callers ask. The header follows from those answers.",
        starter_compiles=False, stage="3"),
    # ------------------------------------------------------------ stage 4
    Exercise(
        "s4_iface", "Two controllers, one interface",
        "Implement <code>PidController</code> and <code>ImpedanceController</code>, both derived from "
        "the given <code>Controller</code>. The test only ever calls them through "
        "<code>Controller&amp;</code> and <code>unique_ptr&lt;Controller&gt;</code>, which is the point.",
        hints=("<code>class PidController : public Controller { public: PidController(double kp, double ki, double kd) : ... {}</code>",
               "<code>double update(double ref, double meas, double dt) override { ... }</code>",
               "Keep a <code>bool first_ = true;</code> in each class for the first-call rule."),
        explain="Code that runs controllers depends only on <code>controller.hpp</code>. Adding an "
                "LQR next month changes no existing file. Each call goes through the vtable: one "
                "indirect call, which matters only inside very tight loops.",
        project=(), starter_compiles=False,
        rules=(Rule("every override says override", r"\boverride\b", "controllers.hpp", must_match=True),),
        stage="4"),
    Exercise(
        "s4_factory", "A factory: config text in, controller out",
        "<code>makeController</code> turns one line of config into a controller and returns "
        "<code>nullptr</code> on any malformed input. The caller never names a concrete class.",
        hints=("<code>std::istringstream in(line); std::string type, tok; if (!(in &gt;&gt; type)) return nullptr;</code>",
               "<code>auto eq = tok.find('='); if (eq == std::string::npos) return nullptr;</code>",
               "Collect into <code>std::map&lt;std::string,double&gt;</code>, then check every key "
               "against the set allowed for the type before constructing."),
        explain="Production factories usually hold a registry, "
                "<code>std::map&lt;std::string, std::function&lt;std::unique_ptr&lt;Controller&gt;(const Params&amp;)&gt;&gt;</code>, "
                "so a new type registers itself instead of adding another if. ros2_control does the "
                "same through pluginlib.",
        stage="4"),
    Exercise(
        "s4_decorator", "Composition: wrap any controller in a filter",
        "<code>FilteredController</code> <i>is</i> a Controller and <i>has</i> a Controller. It "
        "filters the measurement and forwards everything else. One class adds filtering to every "
        "controller, existing or future.",
        hints=("Members: <code>std::unique_ptr&lt;Controller&gt; inner_; double alpha_; double filt_ = 0.0; bool first_ = true;</code>",
               "Initialise <code>inner_(std::move(inner))</code> first, then validate and throw."),
        explain="Inheritance would need FilteredPid, FilteredImpedance and so on, one class per "
                "combination. Composition needs one class. This is the decorator pattern; you will "
                "see it as saturation, rate-limit and logging wrappers.",
        stage="4"),
    # ------------------------------------------------------------ stage 5
    Exercise(
        "s5_ring", "Templates: clampT and a fixed-size ring buffer",
        "Write one function template and one class template. The ring buffer takes its capacity "
        "as a template parameter, keeps its storage inside the object, and must not touch the heap. "
        "The test counts allocations during 1000 pushes.",
        hints=("<code>return x &lt; lo ? lo : (hi &lt; x ? hi : x);</code> uses only <code>operator&lt;</code>.",
               "Members: <code>std::size_t next_ = 0, count_ = 0;</code>. "
               "push: <code>buf_[next_] = x; next_ = (next_ + 1) % N; if (count_ &lt; N) ++count_;</code>",
               "Oldest element: <code>buf_[(next_ + N - count_ + i) % N]</code>"),
        explain="Only <code>N</code> and <code>T</code> vary, so this is a template rather than a class "
                "hierarchy. The size is part of the type, so a full ring is a decision made at "
                "compile time, not a reallocation inside the control loop.",
        stage="5"),
    # ------------------------------------------------------------ stage 6
    Exercise(
        "s6_spsc", "Lock-free single-producer single-consumer queue",
        "Implement <code>push</code> and <code>pop</code> with two atomics and acquire/release. "
        "The test pushes 200,000 numbers from one thread and checks that the other receives every "
        "one, in order.",
        hints=("push: <code>h = head_.load(relaxed); next = (h+1)%N; if (next == tail_.load(acquire)) return false;</code>",
               "then <code>buf_[h] = x; head_.store(next, std::memory_order_release);</code>, "
               "and write the data before publishing the index.",
               "pop mirrors it: load head_ with acquire, read the slot, then store tail_ with release."),
        explain="Each index has one writer, so neither side ever needs a lock. The release store "
                "publishes the data written before it, and the acquire load on the other thread "
                "guarantees it sees that data. The page's ring lab animates this.",
        stage="6"),
    Exercise(
        "s6_periodic", "A periodic thread that stops cleanly",
        "Run a function at a fixed period on its own thread. The part that matters is shutdown: "
        "destroying a <code>std::thread</code> that is still joinable calls "
        "<code>std::terminate()</code>. The last test destroys a running worker on purpose.",
        hints=("Destructor: <code>~PeriodicWorker() { stop(); }</code>",
               "stop: <code>running_ = false; if (thread_.joinable()) thread_.join();</code>",
               "Capture <code>fn</code> by move in the lambda: <code>[this, period, fn = std::move(fn)] { ... }</code>"),
        explain="<code>sleep_until(next)</code> with <code>next += period</code> keeps the long-run rate "
                "exact, while <code>sleep_for(period)</code> accumulates the error from every late "
                "wake-up. On a desktop OS the jitter is still milliseconds, so hard real time needs "
                "an RTOS, PREEMPT_RT, or an EtherCAT master such as TwinCAT.",
        stage="6"),
    # ------------------------------------------------------------ stage 7
    Exercise(
        "s7_lifecycle", "A lifecycle controller, the ros2_control shape",
        "Implement the state machine. Each transition either happens and returns true, or is "
        "refused, returns false, and changes nothing. <code>update()</code> is the real-time path: "
        "it is noexcept and acts only when Active.",
        hints=("Each transition starts with <code>if (state_ != State::Inactive || ...) return false;</code>",
               "deactivate writes <code>*cmd_ = 0.0</code> before forgetting cmd_, so the motor is left safe."),
        explain="Lifecycles keep work that can fail (allocation, parsing, claiming hardware) out of "
                "the real-time loop: it happens in configure/activate, where failing is acceptable. "
                "ros2_control's <code>ControllerInterface</code> has on_configure, on_activate, "
                "on_deactivate and update.",
        stage="7"),
    # ------------------------------------------------------------ project
    Exercise(
        "p1_loops", "Project v0-v1: the cascade loops",
        "Write the shared <code>Pi</code> step and the velocity and current loops. "
        "<code>PositionLoop</code> is done as a pattern to copy. The test checks each loop's "
        "arithmetic, then runs the whole cascade against a simulated DC motor and expects 1 rad "
        "within half a second. <b>Run main</b> prints the response.",
        hints=("<code>integral += e*dt; if (ki &gt; 0) integral = std::clamp(integral, -lim/ki, lim/ki); "
               "return std::clamp(kp*e + ki*integral, -lim, lim);</code>",
               "<code>void update(double dt) override { s_.curRef = pi_.step(s_.velRef - s_.vel, dt); }</code>"),
        explain="Each loop holds a <code>Signals&amp;</code>: it can never be unbound, and it must never "
                "outlive the joint. A reference member also makes the class non-assignable, which is "
                "correct for an object bound to hardware.",
        project=("signals.hpp", "controller.hpp", "motor.hpp"), stage="P"),
    Exercise(
        "p2_sched", "Project v2: a scheduler that owns the loops",
        "Write <code>Scheduler</code>. It owns <code>vector</code> entries holding "
        "<code>unique_ptr&lt;Controller&gt;</code>, runs each at its own divider of a base clock, "
        "runs the slowest first within a tick, and never allocates in <code>tick()</code>.",
        hints=("add: validate, then <code>long div = baseHz_ / rateHz;</code> and find the first task "
               "with a smaller divider, then <code>tasks_.insert(pos, Task{std::move(c), div, 0});</code>",
               "tick: <code>if (tick_ % t.divider == 0) { t.ctrl-&gt;update(double(t.divider)/baseHz_); ++t.runs; }</code>, "
               "and increment tick_ after the loop."),
        explain="Sorting in <code>add()</code>, which happens once, means <code>tick()</code>, which "
                "happens 32,000 times a second, does no sorting, searching or allocation. Do work at "
                "configuration time whenever you can.",
        project=("controller.hpp",), stage="P"),
    Exercise(
        "p3_config", "Project v3: build the cascade from a config file",
        "Parse a small config format into a running <code>Scheduler</code>. Errors must name the "
        "line. The test feeds eight broken configs and one good one, then runs the good one "
        "against the motor.",
        hints=("Count lines with <code>++n</code> before the skip-blank/comment check, so line numbers "
               "match the file.",
               "A lambda <code>auto fail = [&amp;](int n, std::string msg) { *error = \"line \" + "
               "std::to_string(n) + \": \" + msg; return std::unique_ptr&lt;Scheduler&gt;(); };</code> keeps "
               "every error path to one line."),
        explain="This is the factory from Stage 4 applied to the project. The same compiled binary "
                "now runs any cascade, and a tuning change is a text edit.",
        project=("signals.hpp", "controller.hpp", "motor.hpp", "loops.hpp", "scheduler.hpp"), stage="P"),
    Exercise(
        "p4_latest", "Project v4: lock-free latest-value hand-off",
        "A triple buffer: the 1 kHz loop writes state, a slow reader takes the latest, neither "
        "ever waits, and the reader never sees a torn struct. The test runs both sides on two "
        "threads and checks an invariant inside every value read.",
        hints=("write: <code>slots_[w_] = v; auto old = middle_.exchange(w_ | FRESH, std::memory_order_acq_rel); w_ = old &amp; 3;</code>",
               "read: if FRESH is not set, return the old slot; otherwise exchange your slot index in "
               "and take the one that comes out."),
        explain="The SPSC queue delivers every sample, which is right for logging. The triple buffer "
                "delivers only the newest one, which is right for state such as the observation an "
                "RL learner reads. Choose by asking whether the reader needs every sample or only "
                "the current one.",
        stage="P"),
    Exercise(
        "p5_tests", "Project v5: write the tests that catch the bugs",
        "You write the tests. The grader builds them five times, once against the correct "
        "scheduler and once against each of four hidden bugs. They must pass on the first build "
        "and fail on the other four.",
        hints=("Bug 1 accepts a rate that does not divide the base rate.",
               "Bug 2 runs tasks in the wrong order within a tick.",
               "Bug 3 skips the very first tick, and bug 4 gives slow tasks the wrong dt."),
        explain="This is mutation testing. A suite that still passes after a bug is introduced was "
                "not testing that behaviour. GoogleTest gives these checks nicer syntax "
                "(<code>EXPECT_EQ</code>, fixtures, filters) but the same discipline.",
        project=("controller.hpp",),
        mutants=((1, "accepts rates that do not divide the base rate"),
                 (2, "runs fastest-first within a tick"),
                 (3, "skips tick 0"),
                 (4, "gives every task dt = 1/baseHz")),
        stage="P"),
]

EXERCISES = {e.id: e for e in _EX}


# =====================================================================
# files
# =====================================================================

def _ex_dir(ex: Exercise) -> str:
    return os.path.join(EXERCISES_DIR, ex.id)


def _order(names):
    rank = {".hpp": 0, ".h": 0, ".cpp": 1}
    return sorted(names, key=lambda n: (n in ("main.cpp", "my_tests.cpp"), rank.get(os.path.splitext(n)[1], 2), n))


def starter_files(ex: Exercise) -> dict:
    d = os.path.join(_ex_dir(ex), "starter")
    return {n: _read(os.path.join(d, n)) for n in _order(os.listdir(d))}


def solution_files(ex: Exercise) -> dict:
    files = starter_files(ex)
    d = os.path.join(_ex_dir(ex), "solution")
    if os.path.isdir(d):
        for n in os.listdir(d):
            files[n] = _read(os.path.join(d, n))
    return {n: files[n] for n in _order(files)}


def given_files(ex: Exercise) -> dict:
    """{name: path} of the read-only files, project files first."""
    out = {n: os.path.join(PROJECT_DIR, n) for n in ex.project}
    d = os.path.join(_ex_dir(ex), "given")
    if os.path.isdir(d):
        for n in _order(os.listdir(d)):
            out[n] = os.path.join(d, n)
    return out


def editable_names(ex: Exercise) -> list:
    return list(starter_files(ex))


def work_dir(ex: Exercise) -> str:
    return os.path.join(WORK, ex.id)


def ensure_work(ex: Exercise) -> str:
    """Copy the starter files into the learner's work folder (never overwrites)."""
    d = work_dir(ex)
    os.makedirs(d, exist_ok=True)
    for n, text in starter_files(ex).items():
        p = os.path.join(d, n)
        if not os.path.exists(p):
            _write(p, text)
    return d


def reset_file(ex: Exercise, name: str) -> str:
    text = starter_files(ex)[name]
    _write(os.path.join(work_dir(ex), name), text)
    return text


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_sources(ex: Exercise, files: dict, dest: str) -> str:
    os.makedirs(dest, exist_ok=True)
    for n, text in files.items():
        _write(os.path.join(dest, n), text)
    return dest


# =====================================================================
# builds
# =====================================================================

def find_gxx():
    for name in ("g++", "g++.exe"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\mingw64\bin\g++.exe", r"C:\msys64\ucrt64\bin\g++.exe",
              r"C:\msys64\mingw64\bin\g++.exe", "/usr/bin/g++"):
        if os.path.exists(p):
            return p
    return None


def _tool(name):
    gxx = find_gxx()
    if gxx:
        p = os.path.join(os.path.dirname(gxx), name + (".exe" if os.name == "nt" else ""))
        if os.path.exists(p):
            return p
    return shutil.which(name)


@dataclass
class Step:
    label: str
    compile: list
    exe: str
    expect: str = "tests"       # "tests" | "pass" (exit 0) | "fail" (exit != 0) | "run"
    mutant: int = 0


def _stage_given(ex: Exercise, build: str) -> str:
    g = os.path.join(build, "given")
    os.makedirs(g, exist_ok=True)
    for n, p in given_files(ex).items():
        shutil.copyfile(p, os.path.join(g, n))
    return g


def plan(ex: Exercise, src: str, mode: str, gxx: str | None = None, build: str | None = None) -> list:
    """Build steps for `check` (grade) or `run` (the learner's own main)."""
    gxx = gxx or find_gxx() or "g++"
    build = build or os.path.join(BUILD, ex.id)
    os.makedirs(build, exist_ok=True)
    given = _stage_given(ex, build)
    test_dir = os.path.join(_ex_dir(ex), "test")
    cpps = [os.path.join(src, n) for n in sorted(os.listdir(src)) if n.endswith(".cpp")]
    inc = [f"-I{src}", f"-I{given}", f"-I{SUPPORT}"]
    ext = ".exe" if os.name == "nt" else ""

    if mode == "run":
        exe = os.path.join(build, "run" + ext)
        return [Step("your main", [gxx, *CXXFLAGS, *inc, *cpps, "-o", exe], exe, "run")]
    if ex.mutants:
        steps = []
        for k, desc in ((0, "the correct scheduler"), *ex.mutants):
            exe = os.path.join(build, f"mutant{k}{ext}")
            steps.append(Step(desc, [gxx, *CXXFLAGS, f"-DMUTANT={k}", *inc, *cpps, "-o", exe], exe,
                              "pass" if k == 0 else "fail", k))
        return steps
    mine = [c for c in cpps if os.path.basename(c) != "main.cpp"]
    exe = os.path.join(build, "check" + ext)
    return [Step("tests", [gxx, *CXXFLAGS, *inc, f"-I{test_dir}", *mine,
                           os.path.join(test_dir, "test_main.cpp"), "-o", exe], exe, "tests")]


def tool_command(ex: Exercise, src: str, name: str, which: str) -> list:
    """'preprocess' -> g++ -E on one file; 'symbols' -> compile to .o and nm -C it."""
    build = os.path.join(BUILD, ex.id)
    given = _stage_given(ex, build)
    inc = [f"-I{src}", f"-I{given}", f"-I{SUPPORT}"]
    gxx = find_gxx() or "g++"
    path = os.path.join(src, name)
    if which == "preprocess":
        return [[gxx, "-std=c++17", "-E", "-P", *inc, "-x", "c++", path]]
    obj = os.path.join(build, os.path.splitext(name)[0] + ".o")
    return [[gxx, "-std=c++17", "-c", *inc, path, "-o", obj], [_tool("nm") or "nm", "-C", obj]]


# =====================================================================
# grading
# =====================================================================

@dataclass
class Result:
    ok: bool
    name: str
    why: str = ""


@dataclass
class Report:
    compiled: bool = True
    compile_log: str = ""
    results: list = field(default_factory=list)
    output: str = ""            # what the programs printed, non-PASS/FAIL lines
    crashed: bool = False

    @property
    def passed(self) -> bool:
        return self.compiled and not self.crashed and bool(self.results) and all(r.ok for r in self.results)


_LINE = re.compile(r"^(PASS|FAIL) (.*?)(?: \| (.*))?$")


def parse_results(stdout: str) -> tuple:
    """([Result], done, other_lines) from a test program's output."""
    res, other, done = [], [], False
    for line in stdout.splitlines():
        line = line.rstrip("\r")
        m = _LINE.match(line)
        if m:
            res.append(Result(m.group(1) == "PASS", m.group(2), m.group(3) or ""))
        elif line.strip() == "DONE":
            done = True
        elif line.strip():
            other.append(line)
    return res, done, "\n".join(other)


def grade_step(step: Step, rc: int, stdout: str, report: Report):
    res, done, other = parse_results(stdout)
    if step.expect == "tests":
        report.results += res
        report.output += other
        if not done:
            report.crashed = True
            report.results.append(Result(False, "the program finished",
                                         f"it stopped after {len(res)} checks (exit code {rc}): a crash, "
                                         "a null pointer, an out-of-range index, or a hang"))
    else:
        fails = sum(not r.ok for r in res)
        if step.expect == "pass":
            ok = rc == 0 and fails == 0
            report.results.append(Result(ok, "your tests pass on " + step.label,
                                         "" if ok else f"{fails} of your checks failed on the CORRECT code "
                                         f"(exit {rc}) -- a test that fails on correct code is the bug"))
        else:
            ok = rc != 0
            report.results.append(Result(ok, f"your tests catch mutant {step.mutant}: {step.label}",
                                         "" if ok else "every one of your checks passed on this broken version"))
        if step.mutant == 0 and other:
            report.output += other


_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def check_rules(ex: Exercise, src: str) -> list:
    out = []
    for r in ex.rules:
        p = os.path.join(src, r.file)
        text = _COMMENT.sub("", _read(p)) if os.path.exists(p) else ""
        hit = re.search(r.pattern, text) is not None
        ok = hit if r.must_match else not hit
        out.append(Result(ok, r.label, "" if ok else ("not found in " if r.must_match else "found in ") + r.file))
    return out


def grade(ex: Exercise, src: str, timeout: float = 20.0) -> Report:
    """Synchronous grading (tests and command line). The GUI does the same with QProcess."""
    rep = Report()
    for step in plan(ex, src, "check"):
        c = subprocess.run(step.compile, capture_output=True, text=True, errors="replace")
        if c.returncode != 0:
            rep.compiled = False
            rep.compile_log = c.stdout + c.stderr
            return rep
        try:
            r = subprocess.run([step.exe], capture_output=True, text=True, timeout=timeout, errors="replace")
            grade_step(step, r.returncode, r.stdout, rep)
        except subprocess.TimeoutExpired:
            rep.crashed = True
            rep.results.append(Result(False, "the program finished", f"no exit after {timeout:.0f} s: a hang"))
    rep.results += check_rules(ex, src)
    return rep


# compiler messages: "path/file.hpp:12:5: error: ..." -> (file, line, col, kind, msg)
DIAG = re.compile(r"^(?P<path>.*?):(?P<line>\d+):(?P<col>\d+): (?P<kind>fatal error|error|warning|note): (?P<msg>.*)$")


def diagnostics(log: str) -> list:
    out = []
    for line in log.splitlines():
        m = DIAG.match(line.strip())
        if m:
            out.append((os.path.basename(m.group("path")), int(m.group("line")), int(m.group("col")),
                        m.group("kind"), m.group("msg")))
    # the linker does not give a line, only a symbol
    for line in log.splitlines():
        if "undefined reference" in line or "multiple definition" in line:
            out.append(("", 0, 0, "link", line.split(": ", 1)[-1].strip()))
    return out


def clean_log(log: str) -> str:
    """Strip absolute paths so the compiler's text reads like it was run in your folder."""
    for root in (WORK, BUILD, EXERCISES_DIR, SUPPORT):
        for r in (root, root.replace("\\", "/")):
            log = log.replace(r + os.sep, "").replace(r + "/", "")
    return log


# =====================================================================
# progress
# =====================================================================

def load_progress() -> dict:
    try:
        with open(PROGRESS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def mark_passed(ex_id: str, ok: bool):
    p = load_progress()
    if ok:
        p[ex_id] = True
    elif ex_id not in p:
        p[ex_id] = False
    os.makedirs(WORK, exist_ok=True)
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=1)
