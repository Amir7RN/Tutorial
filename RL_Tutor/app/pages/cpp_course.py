"""
C++ for Robotics -- the chapter after Manipulation & Mobility.

The diagnosis this chapter is built on: the gap is software DESIGN, not syntax.
Reading production code is easy; writing it from a blank file is hard, because
nobody says why a class exists. The answer used throughout: a class exists to
protect an invariant. The header is the contract; the .cpp is the secret.

Seven stages, each answering one question, and one project carried through all
of them: a multi-rate controller scheduler (current loop 32 kHz, velocity
8 kHz, position 1 kHz), configured from text, with lock-free hand-off to a slow
reader. Every exercise is compiled with the real g++ and graded by a test main
(ctrlcore/cpp_course.py; files in cpp/learn/).

Visual labs (app/assets/steplab):
    cpp_build.html    preprocess -> compile -> link, with mistakes to switch on
    cpp_memory.html   stack / heap / static in 3D, stepped through real code
    cpp_rt.html       SPSC ring, triple buffer, and a multi-rate tick budget
"""

from __future__ import annotations

import html
import os

from PySide6.QtCore import QCoreApplication, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ctrlcore import cpp_course as cc
from .. import theme
from ..widgets import Card, body, callout
from ..widgets.cpp_editor import CppEditor
from ..widgets.cpp_exercise import ExerciseCard
from ..widgets.cpp_tryit import ErrorDecoder, LinkTable, TryItCard, python_table
from ..widgets.step_lab import STEPLAB_DIR
from .base import Page

SEC_FOUND = "C++ · Foundations"
SEC_DESIGN = "C++ · Design"
SEC_RT = "C++ · Real-Time & Robotics"
SEC_PROJ = "C++ · Project"


# =====================================================================
# small building blocks
# =====================================================================

class WebLab(Card):
    """One of the C++ labs in an embedded browser, opened at `fragment`."""

    def __init__(self, page: str, fragment: str, title: str, height: int = 820):
        super().__init__(title)
        url = QUrl.fromLocalFile(os.path.join(STEPLAB_DIR, page))
        if fragment:
            url.setFragment(fragment)
        self.view = None
        if QCoreApplication.testAttribute(Qt.AA_ShareOpenGLContexts):
            try:
                from PySide6.QtWebEngineWidgets import QWebEngineView
                self.view = QWebEngineView()
                self.view.setMinimumHeight(height)
                self.view.loadFinished.connect(lambda ok: self.view.page().runJavaScript(
                    "document.documentElement.dataset.theme='dark'"))
                self.view.load(url)
                self.add(self.view)
            except ImportError:
                self.view = None
        link = body(f"<a href='open' style='color:{theme.CYAN}'>Open this lab in the browser</a>"
                    + ("" if self.view else " (the embedded view needs Qt WebEngine)"))
        link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link.linkActivated.connect(lambda _: QDesktopServices.openUrl(url))
        self.add(link)


def snippet(code: str, title: str | None = None, lines: int | None = None) -> QWidget:
    """Read-only highlighted C++ (the same editor, locked)."""
    code = code.strip("\n")
    ed = CppEditor(code, read_only=True)
    n = lines or len(code.splitlines())
    ed.setFixedHeight(int(ed.fontMetrics().height() * (n + 1.2) + 14))
    if not title:
        return ed
    c = Card(title)
    c.add(ed)
    return c


class Reveal(Card):
    """A question with the answer behind a button: say it out loud first."""

    def __init__(self, heading: str, items):
        super().__init__(heading)
        for q, a in items:
            row = QVBoxLayout()
            ql = body(f"<b>{q}</b>")
            al = body(a)
            al.hide()
            b = QPushButton("Show my answer")
            b.setCheckable(True)
            b.setMaximumWidth(170)
            b.toggled.connect(lambda on, al=al, b=b: (al.setVisible(on),
                                                      b.setText("Hide" if on else "Show my answer")))
            row.addWidget(ql)
            row.addWidget(b)
            row.addWidget(al)
            self.add_layout(row)


class Choice(Card):
    """Pick an answer; the explanation names why each option is right or wrong."""

    def __init__(self, heading: str, question: str, options):
        super().__init__(heading)
        self.add(body(question))
        self.fb = body("")
        bar = QHBoxLayout()
        for text, ok, why in options:
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, ok=ok, why=why, text=text: self.fb.setText(
                f"<span style='color:{theme.GOOD if ok else theme.BAD}'><b>{'Yes' if ok else 'No'}: "
                f"{html.escape(text)}.</b></span> {why}"))
            bar.addWidget(b)
        bar.addStretch(1)
        self.add_layout(bar)
        self.add(self.fb)


def two_col(left: QWidget, right: QWidget) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background:transparent;")
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(14)
    lay.addWidget(left, 1)
    lay.addWidget(right, 1)
    return w


class CppPage(Page):
    """Exercises on a page share one number sequence: 4.1, 4.2, ..."""

    STAGE = ""

    def exercise(self, ex_id: str) -> ExerciseCard:
        n = len(getattr(self, "cards", [])) + 1
        card = ExerciseCard(ex_id, f"{self.STAGE}.{n}" if self.STAGE else str(n))
        self.cards = getattr(self, "cards", []) + [card]
        self.add(card)
        return card

    def from_zero(self, text: str, *tryits: str):
        """The beginner layer: what a newcomer needs before this stage's exercises, as runnable programs."""
        self.add(callout(text, "good", label="FROM ZERO · NEW TO C++? START HERE"))
        for t in tryits:
            self.add(TryItCard(t))


# =====================================================================
# 1. the roadmap
# =====================================================================

STAGES = [
    ("0", "How does a C++ program get built?", "CppBuildPage", ("s0_header", "s0_linker"),
     "translation units, one-definition rule, declaration vs definition, the linker, CMake"),
    ("1", "Who owns this object, and when does it die?", "CppOwnershipPage",
     ("s1_raii", "s1_unique", "s1_leak", "s1_shared"), "stack vs heap, RAII, unique_ptr, shared_ptr, weak_ptr"),
    ("2", "What happens when I pass this around?", "CppMovePage", ("s2_rule5", "s2_const"),
     "copy vs move, the rule of 0/3/5, const, pass-by-value vs const&"),
    ("3", "What invariant does this class protect?", "CppInvariantPage",
     ("s3_limits", "s3_lowpass", "s3_reconstruct"), "encapsulation, invariants, what belongs inside, when NOT to write a class"),
    ("4", "What varies, and what stays the same?", "CppInterfacePage",
     ("s4_iface", "s4_factory", "s4_decorator"), "abstract interfaces, virtual/override, factories, composition over inheritance"),
    ("5", "What is identical for every type?", "CppTemplatePage", ("s5_ring",),
     "function and class templates -- shallow on purpose"),
    ("6", "How do two rates share data safely?", "CppConcurrencyPage", ("s6_spsc", "s6_periodic"),
     "threads, atomics, acquire/release, SPSC queues, clean shutdown"),
    ("7", "The robotics layer", "CppRoboticsPage", ("s7_lifecycle",),
     "Eigen, ROS 2 lifecycle, ros2_control, reading production code"),
    ("P", "The project: a multi-rate controller scheduler", "CppProjectLoopsPage",
     ("p1_loops", "p2_sched", "p3_config", "p4_latest", "p5_tests"),
     "v0-v1 loops · v2 scheduler · v3 config factory · v4 lock-free hand-off · v5 tests"),
]


class CppRoadmapPage(CppPage):
    TITLE = "C++ for Robotics: The Gap Is Design, Not Syntax"
    SUBTITLE = ("Why reading production C++ is easy and writing it is hard, the seven questions that "
                "close that gap, and the one project that carries you through all of them.")
    SECTION = SEC_FOUND
    NOTES = "C++ · roadmap"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "You can read a header and follow it. What you cannot yet do is start from an empty file, "
            "and the reason is not <code>unique_ptr</code> syntax. Nobody told you why a class "
            "exists. <b>A class exists to protect an invariant</b>: a promise about a condition that is "
            "always true. Members are private so that no outsider can break the promise. Getters exist "
            "because the member is part of a guarantee. Every design question (what goes in, what "
            "stays out, what is public, what is const) follows from <i>what does this thing promise?</i>",
            "key", label="START HERE — THE ONE REFRAME"))
        self.add(callout(
            "Every stage page opens with <b>From zero</b> cards: small programs that run as they are, "
            "with the comments as the lesson, a question to answer before you press Run, and edits to "
            "make afterwards. They cover what the exercises assume: what <code>#include</code> really "
            "does, what a class, a constructor and <code>this</code> are, when destructors run, "
            "references and pointers, <code>= default</code> and <code>= delete</code>, "
            "<code>const</code>, <code>virtual</code>, templates and threads. When a build fails, in a "
            "Try-it or an exercise, the tutor explains the error message in plain words. If C++ is new "
            "to you, do every Try-it on a page before its exercises.", "good", label="NEW TO C++?"))
        self.add(two_col(
            snippet("""
// limits.hpp -- the CONTRACT. Written first, by asking:
// "what must the rest of the program be able to ask of this?"
class Limits {
public:
    Limits(double lo, double hi);        // throws unless lo <= hi
    double clamp(double x) const;        // const: asking never changes it
    void setRange(double lo, double hi); // keeps the promise or refuses
private:
    double lo_, hi_;                     // private: nobody can break lo <= hi
};""", "the header is the contract"),
            snippet("""
// limits.cpp -- the SECRET. Free to change; nobody recompiles.
#include "limits.hpp"
#include <stdexcept>

Limits::Limits(double lo, double hi) : lo_(lo), hi_(hi) {
    if (!(lo <= hi)) throw std::invalid_argument("lo > hi");
}
double Limits::clamp(double x) const {
    return x < lo_ ? lo_ : (x > hi_ ? hi_ : x);
}""", "the .cpp is the secret")))
        self.add(body(
            "So <i>“did they know the getters beforehand, or add them during development?”</i> "
            "Both. The first version of a header comes from the question above. Members are added "
            "later only when a new caller needs to ask something new, and each addition is checked "
            "against the promise. That is the habit this chapter trains."))

        self.track = Card("The spine: seven questions, one project, your progress")
        self.track_body = body("")
        self.track_body.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.track_body.linkActivated.connect(self.navigate_requested.emit)
        self.track.add(self.track_body)
        self.add(self.track)
        self._paint_progress()

        proj = self.add(Card("The project, version by version"))
        proj.add(body(
            "Modern Robotics worked because one robot was carried through every chapter. This chapter "
            "does the same with one program, and the program is almost word for word the job "
            "description that was not a fit: <b>several controllers at different rates, a current loop, "
            "a velocity loop and a position loop, each with its own period, configured from a file, "
            "with safe data hand-off between them.</b> You learn C++ inside a domain you already "
            "understand, so you are never stuck on the language and the problem at the same time."))
        proj.add(body(
            "<table cellspacing='0' cellpadding='4'>"
            "<tr><td><b>v0–v1</b></td><td>a PI shared by the loops; a <code>Controller</code> interface the three loops implement</td><td>Stages 0, 3, 4</td></tr>"
            "<tr><td><b>v2</b></td><td>a <code>Scheduler</code> owning <code>vector&lt;unique_ptr&lt;Controller&gt;&gt;</code>, each task with its own divider</td><td>Stage 1</td></tr>"
            "<tr><td><b>v3</b></td><td>a factory that builds the whole cascade from a config file</td><td>Stage 4</td></tr>"
            "<tr><td><b>v4</b></td><td>a lock-free latest-value hand-off between the 1 kHz loop and a slow reader</td><td>Stage 6</td></tr>"
            "<tr><td><b>v5</b></td><td>tests that catch real bugs, graded by mutation testing</td><td>practice</td></tr></table>"))

        habits = self.add(Card("Two habits worth more than the reading"))
        habits.add(body(
            "<b>1 · Reconstruction.</b> This targets the read-versus-write gap directly. Take a module "
            "at work that you can follow. Read its header, close it, and write that header yourself from "
            "what the class is supposed to do. Then diff against the real one and ask about every "
            "difference: why is that exposed, why is that private, why is that const? Reading is "
            "passive; reconstruction makes it active. Exercise 3.3 is this habit with a grader."))
        habits.add(body(
            "<b>2 · Keep LeetCode in its lane.</b> It trains algorithms and data structures, which is "
            "the right preparation for one interview round and teaches nothing about class design, "
            "ownership or interfaces. Do a problem or two a week for that round, and do not count it "
            "as progress on this gap."))
        res = self.add(Card("Resources, ranked"))
        res.add(body(
            "<b>learncpp.com</b>: free, chapter by chapter, the best structured sequence there is. "
            "Use it as the Modern Robotics of C++ and work it in order.<br>"
            "<b>C++ Software Design</b>, Klaus Iglberger: design principles and patterns in modern C++, "
            "aimed exactly at this gap. Read it after Stage 2; his CppCon talks are a free preview.<br>"
            "<b>A Tour of C++</b>, Stroustrup: a short, dense overview for people who already program.<br>"
            "<b>Effective Modern C++</b>, Scott Meyers: read it item by item, after Stage 2.<br>"
            "<b>C++ Core Guidelines</b>: the \"why\" document. Browse it; do not read it cover to cover.<br>"
            "<b>Timur Doumler's real-time audio talks</b>: audio has the same constraints (no allocation, "
            "no locks, hard deadlines) and has thought about them harder than robotics has.<br>"
            "<b>ros2_control source</b>: a reading target once you reach Stage 4, the "
            "controller-interface-plus-manager architecture you are building here."))
        self.add(callout(
            "Do not try to learn all of C++. Skip template metaprogramming, most corners of "
            "<code>&lt;algorithm&gt;</code>, custom allocators, exception-heavy design and nearly all "
            "pre-C++11 legacy. Depth in ownership, class design and interfaces matters more than breadth "
            "everywhere else, and those three are what a robotics software interview probes. "
            "Budget about ten weeks at an hour a day, with extra time on Stage 3.", "warn"))
        self.finish()

    def _paint_progress(self):
        prog = cc.load_progress()
        rows = []
        for num, q, cls, exs, covers in STAGES:
            done = sum(1 for e in exs if prog.get(e))
            colour = theme.GOOD if done == len(exs) else theme.WARN if done else theme.TEXT_FAINT
            bar = "".join("●" if prog.get(e) else "○" for e in exs)
            rows.append(
                f"<tr><td style='color:{theme.CYAN}; font-weight:700'>{'Stage ' + num if num != 'P' else 'Project'}</td>"
                f"<td><a style='color:{theme.TEXT}' href='{cls}'><b>{html.escape(q)}</b></a><br>"
                f"<span style='color:{theme.TEXT_DIM}'>{html.escape(covers)}</span></td>"
                f"<td style='color:{colour}; font-family:Consolas; white-space:nowrap'>{bar} {done}/{len(exs)}</td></tr>")
        total = sum(len(s[3]) for s in STAGES)
        done = sum(1 for s in STAGES for e in s[3] if prog.get(e))
        self.track_body.setText(
            f"<p>{done} of {total} graded exercises passed. Click a stage to go there. Do not move on "
            "until you can answer its question out loud, the way you can now answer “what is the Jacobian”.</p>"
            f"<table cellspacing='0' cellpadding='5'>{''.join(rows)}</table>")

    def on_show(self):
        self._paint_progress()


# =====================================================================
# 2. Stage 0 -- the build
# =====================================================================

class CppBuildPage(CppPage):
    TITLE = "Stage 0 · How a C++ Program Gets Built"
    SUBTITLE = ("Headers feel arbitrary until you see the compilation model: the compiler sees one "
                ".cpp at a time, and only the linker sees the whole program.")
    SECTION = SEC_FOUND
    NOTES = "C++ · stage 0"
    STAGE = "0"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Header/source separation is not a style convention, it is how C++ is compiled. "
            "<b>#include pastes text.</b> The compiler turns each .cpp, with everything pasted into it "
            "(a <i>translation unit</i>), into an object file that it compiles <i>alone</i>, knowing "
            "nothing about the other .cpp files. The linker then joins the object files: every symbol "
            "something needs (U) must be defined (T) exactly once. Almost every confusing build "
            "error comes from one of those three steps.", "key", label="START HERE"))
        self.add(python_table())
        self.from_zero(
            "Three ideas carry the whole of Stage 0. <b>(1)</b> <code>#include</code> is copy-paste: the "
            "compiler never sees a header on its own, only the .cpp with the header's text pasted in. "
            "<b>(2)</b> A <b>declaration</b> says a thing exists (<code>double clamp(double);</code>, "
            "<code>extern int g;</code>). A <b>definition</b> creates it (a body, or memory). Declare as "
            "often as you like, define once. <b>(3)</b> A class is declared in the header and its member "
            "functions are defined in the .cpp with <code>Pid::</code> in front, which is what lets "
            "their bodies use the members. Run each program, then break it the way the list says.",
            "t_include", "t_class", "t_this")
        self.add(LinkTable())
        self.add(WebLab("cpp_build.html", "", "Lab · switch a mistake on and see which stage catches it", 900))
        self.add(two_col(
            Reveal("Say it out loud", [
                ("Declaration vs definition?",
                 "A declaration says a thing exists and gives its type: <code>double clamp(double, double, double);</code> "
                 "or <code>extern int g;</code>. A definition creates it, with a body or storage. Declare it as "
                 "often as you like; define it exactly once in the program (the one-definition rule)."),
                ("Why does #pragma once not fix “multiple definition”?",
                 "It stops the same header being pasted twice into <i>one</i> translation unit. Two .cpp files "
                 "are two translation units, compiled separately; each legally gets one copy, and the "
                 "linker sees two."),
                ("When is a forward declaration enough?",
                 "When you only use a pointer or reference to the type: <code>class Robot;</code> then "
                 "<code>void attach(Robot&amp;);</code>. The compiler needs the full class only to know its "
                 "size or call its members. Forward-declaring in headers cuts rebuild times."),
                ("Why are templates and inline functions defined in headers?",
                 "The compiler needs the body in every translation unit that uses them. They are exempt "
                 "from the one-definition rule's \"exactly once\" (the copies must be identical), and the "
                 "linker merges them (W in nm)."),
            ]),
            snippet("""
# CMakeLists.txt -- the whole build, declared
cmake_minimum_required(VERSION 3.16)
project(scheduler CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# a library: compiled once, linked by both targets below
add_library(control src/pid.cpp src/scheduler.cpp)
target_include_directories(control PUBLIC include)
target_compile_options(control PRIVATE -Wall -Wextra)

add_executable(demo app/main.cpp)
target_link_libraries(demo PRIVATE control)

add_executable(tests test/test_main.cpp)
target_link_libraries(tests PRIVATE control)

# cmake -S . -B build && cmake --build build""", "CMake: the three lines that matter are add_library, add_executable, target_link_libraries")))
        self.add(body(
            "The exercises below are real multi-file builds with your own g++. Both have a "
            "<b>what the compiler sees</b> toolbar: <i>after the preprocessor</i> shows the translation "
            "unit, and <i>symbols</i> shows the object file's T/U table, the same two views as the "
            "lab above but for your own code. The compile error is the exercise, so press "
            "<b>Check</b> first and read it."))
        self.add(ErrorDecoder())
        self.exercise("s0_header")
        self.exercise("s0_linker")
        self.finish()


# =====================================================================
# 3. Stage 1 -- ownership and lifetime
# =====================================================================

class CppOwnershipPage(CppPage):
    TITLE = "Stage 1 · Who Owns This Object, and When Does It Die?"
    SUBTITLE = ("Stack vs heap, RAII, unique_ptr, shared_ptr: a name for an instinct you already have, "
                "“no allocation in the 1 kHz loop”.")
    SECTION = SEC_FOUND
    NOTES = "C++ · stage 1"
    STAGE = "1"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Every object has exactly one answer to <i>who destroys me, and when?</i> On the "
            "<b>stack</b>, the answer is the closing brace, and it is free. On the <b>heap</b>, the answer "
            "is whoever holds the owning pointer. With a raw <code>new</code> that is you, by "
            "remembering. With RAII it is an object's destructor, which you cannot forget. Modern C++ "
            "almost never writes <code>delete</code>: ownership lives in a type "
            "(<code>vector</code>, <code>unique_ptr</code>, <code>shared_ptr</code>).", "key",
            label="START HERE"))
        self.from_zero(
            "Before ownership makes sense you need two things: the exact moment a <b>constructor</b> "
            "and a <b>destructor</b> run, and what <code>&amp;</code> and <code>*</code> mean. A "
            "constructor runs when an object is created and sets it up. A destructor (<code>~T()</code>) "
            "runs when the object dies and cleans up. For a local variable that happens at its "
            "closing brace, guaranteed. Everything in this stage builds on that one guarantee.",
            "t_lifetime", "t_refs")
        self.add(WebLab("cpp_memory.html", "s=stack_heap,leak,raii,unique,shared,dangling",
                        "Lab · memory in 3D: step through the code, drag to orbit", 860))
        left, right = Card("Which owner?"), Card("Where it bites in a controller")
        self.add(two_col(left, right))
        left.add(body(
            "<b>Default: a value.</b> <code>Pid pid;</code> as a member or local. No pointer at all.<br>"
            "<b>Many of them, owned:</b> <code>std::vector&lt;T&gt;</code>.<br>"
            "<b>Polymorphic or optional, one owner:</b> <code>std::unique_ptr&lt;T&gt;</code>. "
            "It is 8 bytes, has zero overhead, and moves but does not copy.<br>"
            "<b>Lifetime really shared:</b> <code>std::shared_ptr&lt;T&gt;</code>. It costs an atomic "
            "count and a control block. Rarer than you think.<br>"
            "<b>Use without owning:</b> <code>T&amp;</code> (cannot be null) or <code>T*</code> (can be), "
            "never deleted by the user.<br>"
            "<b>Observe something that may die:</b> <code>std::weak_ptr&lt;T&gt;</code>."))
        right.add(body(
            "<code>new</code>/<code>delete</code> and <code>malloc</code> may take a lock, walk free lists, "
            "or ask the OS for pages, so their time is <i>unbounded</i>. In a 1 kHz loop, allocate "
            "everything in <code>configure()</code> and only use it in <code>update()</code>.<br><br>"
            "The traps are hidden allocations: <code>push_back</code> past capacity, building a "
            "<code>std::string</code>, a <code>std::function</code> capturing too much, a "
            "<code>shared_ptr</code> copy (an atomic, not an allocation, but still a cost), and "
            "exceptions. The exercises count allocations, so you can test for this."))
        self.add(Choice(
            "Quick check",
            "A <code>Scheduler</code> holds controllers of different types and is the only thing that "
            "runs them. What should it store?",
            [("std::vector<Controller*>", False,
              "Who deletes them? A raw pointer says nothing about ownership, and someone has to remember."),
             ("std::vector<std::unique_ptr<Controller>>", True,
              "One owner, destroyed with the scheduler, polymorphic through the base pointer. This is "
              "the v2 project design."),
             ("std::vector<std::shared_ptr<Controller>>", False,
              "It works, but it says the lifetime is shared when it is not, and every copy costs an atomic."),
             ("std::vector<Controller>", False,
              "It slices: a PidController copied into a Controller slot loses everything that made it a "
              "PID, and Controller is abstract anyway.")]))
        self.add(TryItCard("t_unique"))
        self.exercise("s1_raii")
        self.exercise("s1_unique")
        self.exercise("s1_leak")
        self.exercise("s1_shared")
        self.finish()


# =====================================================================
# 4. Stage 2 -- copy, move, const
# =====================================================================

class CppMovePage(CppPage):
    TITLE = "Stage 2 · What Happens When I Pass This Around?"
    SUBTITLE = ("Copy vs move, the rule of zero / three / five, and const: free documentation that "
                "the compiler checks.")
    SECTION = SEC_FOUND
    NOTES = "C++ · stage 2"
    STAGE = "2"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Passing an object around raises one question: <b>is a new owner created (copy), or does "
            "ownership change hands (move)?</b> A copy of a vector allocates a new buffer and copies "
            "every element. A move copies three pointers and leaves the source empty. "
            "<code>const</code> answers the other question, <i>may this function change it?</i>, "
            "in the signature where a reviewer can see it.", "key", label="START HERE"))
        self.from_zero(
            "Every class has six <b>special member functions</b>: the default constructor, the copy "
            "constructor, the move constructor, copy assignment, move assignment and the destructor. "
            "If you do not write them, the compiler may write them for you. <code>= default</code> "
            "means \"write it the normal way\" and <code>= delete</code> means \"this must not exist\". "
            "Watch each of the six announce itself, then see <code>= default</code>, "
            "<code>= delete</code> and <code>const</code> at work.",
            "t_special", "t_default_delete", "t_const")
        self.add(WebLab("cpp_memory.html", "s=copy_move,params", "Lab · a copy, a move, and a const&", 820))
        self.add(two_col(
            snippet("""
// pass cheap things by value, owning things by const&
double clampTorque(double tau, double limit);            // 8 bytes: copy
double energy(const std::vector<double>& qd);            // read: no copy
void setTrajectory(std::vector<double> q) {              // SINK: take by value,
    q_ = std::move(q);                                   // then move it in
}
// caller:  ctl.setTrajectory(std::move(plan));   // no copy at all
//          ctl.setTrajectory(plan);              // one copy, on purpose""",
                    "the passing rules, in code"),
            snippet("""
// rule of ZERO (the default): own through members that
// already know how -- write none of the five
class Trajectory {
    std::vector<double> q_;       // copies, moves, frees itself
};

// rule of FIVE: only when YOU wrap a raw resource
class DmaBuffer {
public:
    ~DmaBuffer();
    DmaBuffer(const DmaBuffer&);             // deep copy (or = delete)
    DmaBuffer& operator=(const DmaBuffer&);
    DmaBuffer(DmaBuffer&&) noexcept;         // steal + empty the source
    DmaBuffer& operator=(DmaBuffer&&) noexcept;
};""", "rule of zero vs rule of five")))
        self.add(Reveal("Say it out loud", [
            ("What does std::move do?",
             "Nothing at run time. It is a cast to an rvalue reference, which says \"you may steal from "
             "this\". The move constructor is what does the stealing. Reading a moved-from object, "
             "other than assigning to it, is a bug."),
            ("Why must the move constructor be noexcept?",
             "<code>std::vector</code> reallocation only uses moves when they cannot throw; otherwise "
             "it copies every element to keep its strong guarantee. Without noexcept, your vector of "
             "trajectories quietly deep-copies on every growth."),
            ("What does a const member function promise?",
             "That calling it does not change the object's observable state. It can be called through "
             "<code>const T&amp;</code>, it documents read-only access, and it is thread-safe to call "
             "concurrently as long as nothing else writes."),
        ]))
        self.exercise("s2_rule5")
        self.exercise("s2_const")
        self.finish()


# =====================================================================
# 5. Stage 3 -- invariants
# =====================================================================

class CppInvariantPage(CppPage):
    TITLE = "Stage 3 · What Invariant Does This Class Protect?"
    SUBTITLE = ("The actual gap, and the stage to spend longest on. Encapsulation, invariants, what "
                "belongs inside, and when not to write a class at all.")
    SECTION = SEC_DESIGN
    NOTES = "C++ · stage 3"
    STAGE = "3"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Before typing <code>class</code>, write one sentence: <b>“this object guarantees that "
            "___ is always true.”</b> If you can, that sentence decides the class. Members that the "
            "guarantee depends on become private, every function that could break it validates, "
            "and every function that cannot break it is const. If you cannot write the sentence, "
            "you probably want a <code>struct</code> (plain data, all public) or a free function.",
            "key", label="START HERE"))
        d = self.add(Card("Design a class in five questions, using a joint-limit guard as the example"))
        d.add(body(
            "<b>1 · What does it promise?</b> “The command it outputs is always inside the joint's position "
            "limits, and never moves faster than the velocity limit.”<br>"
            "<b>2 · What must it store to keep that promise?</b> The limits (lo, hi, vmax), the last output, and "
            "dt, or better the product vmax·dt. Store the least that defines the behaviour.<br>"
            "<b>3 · Who may change what?</b> The limits change only through <code>setLimits()</code>, which "
            "validates. The last output changes only through <code>filter()</code>.<br>"
            "<b>4 · What can callers ask?</b> <code>filter(cmd)</code>, plus <code>limits() const</code> and "
            "<code>last() const</code>. Do not add a setter for <code>last_</code>: that would let a caller "
            "teleport the joint and break promise 1.<br>"
            "<b>5 · How can construction fail?</b> lo &gt; hi, vmax ≤ 0, or a NaN: throw from the "
            "constructor, so an invalid guard cannot exist at all."))
        d.add(snippet("""
class JointLimitGuard {
public:
    JointLimitGuard(Limits pos, double vmax, double dt);   // throws: an invalid guard never exists
    double filter(double cmd);                              // the ONLY way last_ changes
    const Limits& limits() const { return pos_; }
    double last() const { return last_; }
private:
    Limits pos_;        // a class that keeps ITS OWN promise (lo <= hi): composition
    double maxStep_;    // vmax * dt -- the only form filter() needs
    double last_ = 0.0;
};"""))
        self.add(Choice(
            "struct or class?",
            "<code>JointState { double q, qd, tau; }</code> as read from the drive every tick: struct or class?",
            [("struct, all public", True,
              "Any combination of values is valid, so there is no invariant to protect. Getters and "
              "setters would be ceremony. The C++ Core Guidelines (C.2) say to use class only if there is an invariant."),
             ("class with getters and setters", False,
              "A setter for every field protects nothing: it is a public member with extra typing. Write "
              "accessors only when they defend something.")]))
        self.add(TryItCard("t_explicit"))
        self.add(Reveal("Say it out loud", [
            ("When should a function be a member, and when a free function?",
             "A member if it needs the private state to keep the invariant. Otherwise a free function "
             "in the same namespace, such as <code>double kineticEnergy(const JointState&amp;, …)</code>. "
             "Fewer members means fewer places that can break the promise."),
            ("What is the strong exception guarantee?",
             "If an operation throws, the object is exactly as it was before. Validate first and assign "
             "after, or build a temporary and swap. Exercise 3.1 tests this."),
            ("Getters for everything?",
             "No. A getter is part of the contract and is hard to remove later. Expose what callers "
             "need to ask, not every field you happen to have."),
        ]))
        self.exercise("s3_limits")
        self.exercise("s3_lowpass")
        self.exercise("s3_reconstruct")
        self.finish()


# =====================================================================
# 6. Stage 4 -- interfaces
# =====================================================================

class CppInterfacePage(CppPage):
    TITLE = "Stage 4 · What Varies, and What Stays the Same?"
    SUBTITLE = ("Abstract interfaces, virtual and override, the factory you were asked about, the cost "
                "of a vtable call, and why composition is the modern default.")
    SECTION = SEC_DESIGN
    NOTES = "C++ · stage 4"
    STAGE = "4"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Find the line between what changes and what does not. The scheduler stays the same; the "
            "controllers vary. Put an <b>interface</b> on that line: a class with only pure virtual "
            "functions that says <i>what</i> a controller can do. Code on the stable side depends only "
            "on the interface, so a new controller changes no existing file. A <b>factory</b> is the one "
            "place that knows the concrete names.", "key", label="START HERE"))
        self.from_zero(
            "<code>virtual</code> makes a call through a base-class pointer run the <i>derived</i> "
            "class's version. <code>= 0</code> makes a function pure, which turns the class into an "
            "interface that cannot be created on its own. <code>override</code> asks the compiler to "
            "check that you really replaced a base function. <code>virtual ~Controller() = default;</code> "
            "is an empty destructor that is virtual, so that deleting through a base pointer destroys "
            "the whole object. All four in one program:", "t_virtual")
        self.add(WebLab("cpp_memory.html", "s=vtable", "Lab · what virtual actually costs", 760))
        self.add(two_col(
            snippet("""
// the stable side depends only on this
class Controller {
public:
    virtual ~Controller() = default;      // ALWAYS, for a base you delete through
    virtual double update(double ref, double meas, double dt) = 0;
    virtual void reset() = 0;
    virtual std::string name() const = 0;
};

class PidController final : public Controller {
public:
    double update(double ref, double meas, double dt) override;
    //                                                ^^^^^^^^ a typo in the
    // signature is now a compile error, not a silent new function
};""", "an interface, and an implementation"),
            snippet("""
// inheritance: one class per combination -- explodes
class FilteredPid : public PidController { ... };
class FilteredImpedance : public ImpedanceController { ... };
class SaturatedFilteredPid ...   // and so on

// composition: one wrapper works on ALL of them
class FilteredController : public Controller {
    std::unique_ptr<Controller> inner_;   // HAS-A
    double alpha_, filt_;
public:
    double update(double r, double m, double dt) override {
        filt_ += alpha_ * (m - filt_);
        return inner_->update(r, filt_, dt);
    }
};""", "composition over inheritance")))
        self.add(Reveal("Say it out loud", [
            ("Why must the base destructor be virtual?",
             "<code>delete base_ptr</code> calls the destructor of the <i>static</i> type unless it is "
             "virtual, so the derived part (its members and resources) is never destroyed. That is "
             "undefined behaviour. <code>unique_ptr&lt;Controller&gt;</code> deletes through the base, "
             "so this applies to you."),
            ("What does a virtual call cost?",
             "Two loads (the vptr, then the vtable slot) and an indirect call, a few ns when cached. The "
             "real cost is that it blocks inlining. In a 32 kHz inner loop over a fixed type, use the "
             "concrete type, a template, or <code>final</code> so the compiler can devirtualise."),
            ("When is inheritance the right answer?",
             "When it models \"is-substitutable-for\": the derived class works everywhere the base is "
             "expected (Liskov). Implementing an interface is the common good case. Inheriting to reuse "
             "code is usually better done by composition."),
            ("Factory vs constructor?",
             "A constructor makes one known type. A factory makes a type chosen by data (config, "
             "message, plugin name) and returns it through the interface, so the caller never names it."),
        ]))
        self.exercise("s4_iface")
        self.exercise("s4_factory")
        self.exercise("s4_decorator")
        self.finish()


# =====================================================================
# 7. Stage 5 -- templates
# =====================================================================

class CppTemplatePage(CppPage):
    TITLE = "Stage 5 · What Is Identical for Every Type?"
    SUBTITLE = ("Templates, shallow on purpose: enough to read the STL comfortably and write one "
                "generic container. Metaprogramming is a rabbit hole with little return for robotics.")
    SECTION = SEC_DESIGN
    NOTES = "C++ · stage 5"
    STAGE = "5"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Stage 4 handled variation at <b>run time</b>: one interface and many types behind a pointer. "
            "Templates handle it at <b>compile time</b>: you write the code once and the compiler stamps "
            "out a copy for each type or size you use. Nothing is looked up at run time, so templates "
            "inline fully. That is why <code>std::array&lt;double, 6&gt;</code> and Eigen's "
            "<code>Matrix&lt;double, 6, 6&gt;</code> fit in a control loop.", "key", label="START HERE"))
        self.from_zero(
            "<code>template &lt;typename T&gt;</code> introduces a blank called T. The function or class "
            "below it is a recipe, not code: each time you use it with a new type, the compiler fills "
            "in T and writes a real function or class for that type.", "t_template")
        self.add(two_col(
            snippet("""
template <class T>                     // works for any T with operator<
const T& clampT(const T& x, const T& lo, const T& hi);

template <class T, std::size_t N>      // N is part of the TYPE
class RingBuffer {
    std::array<T, N> buf_{};           // storage inside the object: no heap
    ...
};

RingBuffer<double, 64> torqueLog;      // one class
RingBuffer<JointState, 8> history;     // another class, generated""",
                    "the two shapes you need"),
            Reveal("Say it out loud", [
                ("Template or virtual?",
                 "If the set of types is known at compile time and speed matters, use a template. If it is "
                 "chosen at run time (from config or a plugin), use virtual. A scheduler of mixed "
                 "controllers chosen by config is virtual; a fixed-size buffer of samples is a template."),
                ("Why are templates in headers?",
                 "The compiler generates code only when it sees a use with concrete types, so the full "
                 "body must be visible in that translation unit."),
                ("What to skip?",
                 "SFINAE gymnastics, variadic metaprogramming, CRTP tricks and expression templates. "
                 "Read them when you meet them in Eigen; do not write them. Concepts (C++20) are the "
                 "readable replacement for most of it."),
            ])))
        self.exercise("s5_ring")
        self.finish()


# =====================================================================
# 8. Stage 6 -- concurrency
# =====================================================================

class CppConcurrencyPage(CppPage):
    TITLE = "Stage 6 · How Do Two Rates Share Data Safely?"
    SUBTITLE = ("Threads, std::atomic, memory ordering, a lock-free single-producer single-consumer "
                "queue: standard names for things you already built in TwinCAT.")
    SECTION = SEC_RT
    NOTES = "C++ · stage 6"
    STAGE = "6"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Two threads touching the same memory, with at least one writing, is a <b>data race</b> "
            "unless something orders them, and a data race is undefined behaviour, not just a wrong "
            "number. A <code>mutex</code> orders them by making one wait, which a 1 kHz loop must never "
            "do on a 20 Hz logger. <b>Atomics with acquire/release</b> order them without waiting. "
            "<b>One writer per variable</b> is the design rule that makes that possible.",
            "key", label="START HERE"))
        self.from_zero(
            "Three pieces of syntax first. A <b>lambda</b> <code>[capture](args) { body }</code> is a "
            "function written in place; it is what you hand to a thread. A <code>std::thread</code> runs "
            "that function in parallel and must be <code>join()</code>ed. <code>std::atomic&lt;T&gt;</code> "
            "is a variable whose reads and writes cannot tear when two threads touch it.", "t_threads")
        self.add(WebLab("cpp_rt.html", "m=ring", "Lab · the SPSC ring and the triple buffer, slowed down", 820))
        self.add(Reveal("Say it out loud", [
            ("What does memory_order_release / acquire actually guarantee?",
             "Writes before a release-store become visible to a thread that acquire-loads the same "
             "atomic and sees that value. So the order \"fill the slot, then publish the index\" is "
             "preserved across cores. Without it, the CPU or compiler may reorder the two."),
            ("Why not just make everything std::atomic?",
             "An atomic struct larger than 8–16 bytes is not lock-free (it uses a hidden lock), and two "
             "separate atomics can still be read half-old and half-new together. Hand off whole snapshots "
             "(the triple buffer) instead."),
            ("volatile?",
             "Not for threads. It is for memory-mapped hardware registers. It provides no atomicity and "
             "no ordering between threads."),
            ("Priority inversion?",
             "A high-priority loop waits on a mutex held by a low-priority thread, which is preempted by "
             "a medium one, so the critical loop misses its deadline. Lock-free hand-off avoids it; "
             "otherwise use priority-inheritance mutexes."),
        ]))
        self.exercise("s6_spsc")
        self.exercise("s6_periodic")
        self.finish()


# =====================================================================
# 9. Stage 7 -- the robotics layer
# =====================================================================

class CppRoboticsPage(CppPage):
    TITLE = "Stage 7 · The Robotics Layer: Eigen, ROS 2, ros2_control"
    SUBTITLE = ("What the libraries assume you already know from Stages 1–6, the pitfalls that are "
                "specific to them, and the lifecycle shape real controllers use.")
    SECTION = SEC_RT
    NOTES = "C++ · stage 7"
    STAGE = "7"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Robotics C++ libraries are Stages 1–6 applied. Eigen is templates (Stage 5) with "
            "expression templates. ROS 2 nodes are classes with a lifecycle that keeps allocation out "
            "of the loop (Stages 1 and 3). ros2_control is an interface, a factory and a scheduler "
            "(Stage 4 and the project). Learn their pitfalls, not their whole API.", "key",
            label="START HERE"))
        self.add(two_col(
            snippet("""
#include <Eigen/Dense>
using Mat6 = Eigen::Matrix<double, 6, 6>;   // FIXED size: on the stack, no heap
using Vec6 = Eigen::Matrix<double, 6, 1>;

Vec6 tau = J.transpose() * F;               // fine
Eigen::MatrixXd A(6, 6);                    // DYNAMIC: heap, allocate in configure()

// pitfall 1: aliasing.  x = A * x  writes x while still reading it
x = A * x;                 // Eigen handles products via a temporary (allocates if dynamic)
y.noalias() = A * x;       // promise there is no alias: no temporary

// pitfall 2: auto with expression templates
auto e = A * x;            // NOT a vector: a lazy expression that refers to A and x
Vec6 v = A * x;            // evaluate now -- write the type

// pitfall 3: solve, never invert
Vec6 qdd = M.ldlt().solve(tau - h);         // M is SPD (page 135)""", "Eigen: the three mistakes everyone makes"),
            snippet("""
// ros2_control's controller, reduced to its shape
class MyController : public controller_interface::ControllerInterface {
    CallbackReturn on_configure(const State&) override;  // read params, ALLOCATE
    CallbackReturn on_activate(const State&) override;   // claim command interfaces
    CallbackReturn on_deactivate(const State&) override; // release, leave safe
    return_type update(const rclcpp::Time&,
                       const rclcpp::Duration& period) override;
    //  ^ real-time: no allocation, no locks, no logging, no throwing
};
// the controller_manager is the project's Scheduler:
// it owns controllers (loaded by name through pluginlib = a factory)
// and calls read() -> update() -> write() at the configured rate""",
                    "ros2_control: interface + factory + scheduler")))
        rd = self.add(Card("Reading production code without drowning"))
        rd.add(body(
            "<b>1.</b> Start at the <i>interface</i> header (<code>controller_interface.hpp</code>), not the "
            "implementation. Ask what it promises.<br>"
            "<b>2.</b> Find who <i>owns</i> instances: grep for <code>unique_ptr&lt;</code> or "
            "<code>shared_ptr&lt;</code> of that type. That is the manager.<br>"
            "<b>3.</b> Find the real-time path (<code>update</code>) and check it against the rules: no "
            "<code>new</code>, no <code>std::string</code> building, no locks. Every library has a few "
            "violations, and finding them is good practice.<br>"
            "<b>4.</b> Then do the reconstruction exercise from Stage 3 on one header."))
        self.exercise("s7_lifecycle")
        self.finish()


# =====================================================================
# 10-12. the project
# =====================================================================

class CppProjectLoopsPage(CppPage):
    TITLE = "Project v0–v1 · A Cascade of Three Loops"
    SUBTITLE = ("Current, velocity and position loops behind one interface, run by hand against a "
                "simulated DC motor. This is the domain you know, so all the new material is C++.")
    SECTION = SEC_PROJ
    NOTES = "C++ · project v0–v1"
    STAGE = "P"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "The cascade: <b>position loop (1 kHz)</b> → velocity reference → <b>velocity loop (8 kHz)</b> "
            "→ current reference → <b>current loop (32 kHz)</b> → voltage → motor. Inner loops are faster "
            "because they control faster physics: the electrical time constant L/R is 0.5 ms, while "
            "the mechanics are tens of milliseconds. All three share a <code>Signals</code> blackboard, "
            "and each field has exactly one writer, which is what makes v4's threads safe.",
            "key", label="START HERE"))
        self.add(two_col(
            snippet("""
struct Signals {               // one per joint
    double posRef, pos;        // writers: planner, motor
    double velRef, vel;        // writers: PositionLoop, motor
    double curRef, cur;        // writers: VelocityLoop, motor
    double voltage;            // writer:  CurrentLoop
};

class Controller {             // the project's interface
public:
    virtual ~Controller() = default;
    virtual void update(double dt) = 0;
    virtual const char* name() const = 0;
};""", "given: the blackboard and the interface"),
            Reveal("Design decisions in this version", [
                ("Why does each loop hold Signals& rather than take it in update()?",
                 "A loop belongs to one joint for its whole life. Binding it in the constructor means "
                 "update(dt) cannot be called with the wrong joint, and the scheduler does not need to "
                 "know what a Signals is. The cost: a reference member makes the class non-assignable, "
                 "which is correct for something bound to hardware."),
                ("Why a Pi struct instead of a PiController base class?",
                 "Velocity and current loops <i>use</i> the same arithmetic; they are not kinds of a PI "
                 "(composition). The Pi struct has no invariant beyond its fields, so it is a struct "
                 "with one function."),
                ("Where do the gains come from?",
                 "Current loop: kp = L·ω<sub>c</sub>, ki = R·ω<sub>c</sub> places the PI zero on the "
                 "electrical pole (ω<sub>c</sub> ≈ 2π·1.5 kHz). The velocity loop treats the current "
                 "loop as ideal: kp = J·ω<sub>v</sub>/K<sub>t</sub>. Position is a P on a velocity "
                 "source. Pages 16–17 cover the method."),
            ])))
        self.exercise("p1_loops")
        self.finish()


class CppProjectSchedPage(CppPage):
    TITLE = "Project v2–v3 · The Scheduler, and the Cascade from a File"
    SUBTITLE = ("A Scheduler that owns the loops and runs each at its own divider of a base clock, "
                "then a factory that builds the whole thing from text.")
    SECTION = SEC_PROJ
    NOTES = "C++ · project v2–v3"
    STAGE = "P"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "v0 had the rates hard-coded in <code>main</code> (<code>if (k % 32 == 0)</code>). v2 moves "
            "that knowledge into a class whose invariant is the timing contract: every rate divides the "
            "base clock, slow loops run first within a tick, and <code>tick()</code> never allocates. "
            "v3 then moves the choice of loops and gains out of the code entirely.",
            "key", label="START HERE"))
        self.add(WebLab("cpp_rt.html", "m=sched", "Lab · does every 31.25 µs tick finish in time?", 780))
        self.exercise("p2_sched")
        self.add(body(
            "With the scheduler done, v3 adds a config format. This is the Stage 4 factory again, "
            "now building your project. Errors must name the line, because someone will mistype "
            "<code>velocty</code> at 2 a.m."))
        self.exercise("p3_config")
        self.finish()


class CppProjectRtPage(CppPage):
    TITLE = "Project v4–v5 · Lock-Free Hand-Off, and Tests That Catch Bugs"
    SUBTITLE = ("The 1 kHz loop publishes state to a slow reader without ever waiting; then you "
                "write the tests, and they are graded against hidden bugs.")
    SECTION = SEC_PROJ
    NOTES = "C++ · project v4–v5"
    STAGE = "P"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Your TwinCAT DDPG system (pages 95–96) ran a 1 kHz controller and a 20 Hz learner sharing "
            "memory. This is the portable C++ version of that hand-off. The reader needs the "
            "<i>current</i> state, not a history, so it gets a triple buffer rather than a queue. "
            "v5 then asks what proves any of this works: tests that fail when someone breaks it.",
            "key", label="START HERE"))
        self.exercise("p4_latest")
        self.add(snippet("""
#include <gtest/gtest.h>          // what v5 looks like with GoogleTest
TEST(Scheduler, RefusesRatesThatDoNotDivideTheBase) {
    Scheduler s(32000);
    EXPECT_FALSE(s.add(std::make_unique<Probe>("x"), 7000));
}
TEST(Scheduler, RunsSlowestFirst) { ... }
// CMake:  find_package(GTest REQUIRED)
//         target_link_libraries(tests PRIVATE control GTest::gtest_main)
//         include(GoogleTest)  gtest_discover_tests(tests)   -> ctest""",
                            "the same checks, in GoogleTest syntax"))
        self.exercise("p5_tests")
        self.add(callout(
            "By v5 you have something you can send someone: a README with the cascade diagram, a "
            "CMakeLists, the tests, and a CI file that runs them on every push. That is an answer to "
            "\"can you deploy and integrate controllers at different rates?\" that you can point at.",
            "good", label="WHAT YOU NOW HAVE"))
        self.finish()


class CppInterviewPage(CppPage):
    TITLE = "Interview Drill: Robotics Software in C++"
    SUBTITLE = ("The questions a robotics software round asks, answered at the depth that "
                "separates “has used it” from “can design with it”. Say each answer before revealing it.")
    SECTION = SEC_PROJ
    NOTES = "C++ · interview"

    def __init__(self):
        super().__init__()
        self.add(callout(
            "Answer every design question in the same order: <b>what is the invariant, who owns "
            "what, what runs in real time, and how do I test it.</b> It is the robotics equivalent of "
            "\"spaces, kinematics, dynamics, control\" on page 149.", "key", label="START HERE"))
        self.add(Reveal("Ownership and lifetime", [
            ("unique_ptr vs shared_ptr vs raw pointer: when do you use each?",
             "unique_ptr for single ownership, which is the default for heap objects. shared_ptr only when "
             "lifetime really is shared and no single owner can be named; it costs an atomic count. A "
             "raw pointer or reference means non-owning use. A raw owning pointer only at a C API boundary, "
             "wrapped immediately."),
            ("What is RAII and why does it matter in a controller?",
             "Resources are tied to object lifetime: acquired in the constructor, released in the "
             "destructor. Cleanup happens on every exit path, including exceptions. In robotics this "
             "covers memory, file handles, mutex locks (lock_guard), and hardware enable/disable: a "
             "motor driver guard that disables the drive on destruction."),
            ("How do you avoid allocation in a real-time loop?",
             "Preallocate in configure/activate (reserve, fixed-size std::array, Eigen fixed-size types, "
             "object pools), take nothing by value that allocates, avoid std::string and std::function "
             "captures in the path, and verify it, either by counting allocations in tests (as these "
             "exercises do) or with a malloc hook that aborts in the RT thread."),
        ]))
        self.add(Reveal("Design", [
            ("Design a system that runs controllers at 32 kHz, 8 kHz and 1 kHz.",
             "Use an interface (Controller::update(dt)) and a scheduler that owns them as "
             "vector&lt;unique_ptr&lt;Controller&gt;&gt; with integer dividers of one base tick. Validate "
             "the rates at add time (each must divide the base), and run outer loops first so the "
             "references are fresh. Nothing allocates in tick(). The configuration comes from a file "
             "through a factory. Measure the worst-case execution time per tick against the 31.25 µs "
             "budget and phase the slow loops so they do not all land on one tick. In production the "
             "current loop usually runs on the drive MCU or FPGA and the others under PREEMPT_RT."),
            ("Inheritance or composition for adding filtering to controllers?",
             "Composition: a FilteredController implements Controller and owns any Controller (a "
             "decorator). Inheritance would need one subclass per combination."),
            ("How would you share data between a 1 kHz loop and a 20 Hz learner?",
             "Lock-free, with one writer per piece of data. For the latest state, a triple buffer "
             "(atomic index exchange, so the reader never sees a torn struct). For every sample, an SPSC "
             "ring sized for rate ratio plus jitter, dropping on full rather than blocking. Never a "
             "mutex the RT thread could block on (priority inversion)."),
            ("How do you know your tests are good?",
             "They fail when the code is wrong. Mutation testing makes that measurable: introduce "
             "plausible bugs and check that the suite catches each one. Test the contract (invariants, "
             "boundaries, ordering) rather than the implementation."),
        ]))
        self.add(Reveal("Language details they probe", [
            ("Why must a polymorphic base have a virtual destructor?",
             "Deleting a derived object through a base pointer without one is undefined behaviour, and "
             "the derived destructor never runs."),
            ("What does std::move do?",
             "It casts to an rvalue reference and nothing more. The move constructor or assignment does "
             "the transfer, leaving the source valid but unspecified (empty, for standard containers)."),
            ("What is the cost of a virtual call?",
             "Two dependent loads and an indirect branch, a few nanoseconds, but it blocks inlining. "
             "It matters in tight inner loops over known types; final or templates fix it there."),
            ("When does const matter for performance?",
             "Rarely. It matters for correctness and API clarity. The real performance tool is passing "
             "large objects by const&amp; instead of by value, and that is about the &amp;, not the const."),
            ("What is a data race, and is volatile a fix?",
             "Two threads access the same memory concurrently, at least one writing, with no "
             "synchronisation. That is undefined behaviour. volatile is not a fix; use std::atomic with "
             "suitable ordering, or a mutex outside RT paths."),
        ]))
        self.finish()


CPP_PAGES = [
    CppRoadmapPage, CppBuildPage, CppOwnershipPage, CppMovePage,
    CppInvariantPage, CppInterfacePage, CppTemplatePage,
    CppConcurrencyPage, CppRoboticsPage,
    CppProjectLoopsPage, CppProjectSchedPage, CppProjectRtPage, CppInterviewPage,
]
for _c in CPP_PAGES:
    _c.NO_RECAP = True      # the roadmap's tracker and the interview drill are this chapter's recaps
