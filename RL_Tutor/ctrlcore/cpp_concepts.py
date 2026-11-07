"""
The C++ chapter's beginner layer: small runnable programs ("Try it"), the
header/.cpp linkage table, and a decoder for g++ error messages. No Qt here.

A Try-it is a short, heavily commented program that runs as-is. It shows one
idea, prints what happens, and lists small edits to make next ("delete Pid::
and run it again"). Its files are copied to cpp/learn/work/tryit/<id>/ and
compiled there with the same flags as the exercises, from inside that folder,
so compiler messages read "pid.cpp:12:5", not a long absolute path.

Every claim here is checked against the real compiler by
tests/test_cpp_concepts.py: each Try-it compiles and prints what it says,
each linkage-table cell gives the stage and message it shows, and each
decoder example produces an error that its pattern matches.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field

from . import cpp_course as cc


# =====================================================================
# Try-it programs
# =====================================================================

@dataclass(frozen=True)
class TryIt:
    id: str
    title: str
    files: tuple            # ((name, text), ...): the first one opens first
    expect: str             # a line the unchanged program prints (checked by the tests)
    intro: str = ""         # what to look at, before running
    predict: str = ""       # a question to answer before pressing Run
    after: str = ""         # the explanation, shown once it has run
    tasks: tuple = ()       # edits to try next
    preprocess: str = ""    # file to offer "after the preprocessor" for


def _t(id, title, files, expect, **kw):
    files = tuple((n, txt.strip("\n") + "\n") for n, txt in files)
    return TryIt(id, title, files, expect, **{k: (tuple(v) if k == "tasks" else v) for k, v in kw.items()})


_TRY = [
    # ---------------------------------------------------------------- Stage 0
    _t("t_include", "#include pastes text", [
        ("main.cpp", r"""
// main.cpp
#include <cstdio>        // the standard library's printf: thousands of lines pasted here
#include "limits.hpp"    // OUR header: its text is pasted right here, word for word
#include "limits.hpp"    // pasted a second time on purpose: #pragma once makes it paste nothing

// limits.hpp only DECLARED clampTorque (no body). This is its DEFINITION.
double clampTorque(double u) {
    if (u >  kMaxTorque) return  kMaxTorque;
    if (u < -kMaxTorque) return -kMaxTorque;
    return u;
}

int main() {
    std::printf("clampTorque(30.0) = %.1f\n", clampTorque(30.0));
    std::printf("clampTorque(-3.5) = %.1f\n", clampTorque(-3.5));
    return 0;
}
"""),
        ("limits.hpp", r"""
// limits.hpp
#pragma once                       // "paste me at most once into each .cpp"

const double kMaxTorque = 24.0;    // a constant every file that includes this can read
double clampTorque(double u);      // a DECLARATION: "this function exists somewhere". No body.
""")],
        "clampTorque(30.0) = 24.0",
        intro=("The preprocessor runs before the compiler and only edits text. "
               "<code>#include \"limits.hpp\"</code> means: <i>delete this line and paste the whole of "
               "limits.hpp in its place.</i> Nothing smarter than that. Press <b>main.cpp after the "
               "preprocessor</b> to see the file the compiler really receives."),
        after=("The <code>#include</code> lines are gone. In their place is the text of limits.hpp, once, "
               "even though main.cpp asked for it twice, because of <code>#pragma once</code>. The standard "
               "library's own headers are pasted in too; the view folds those into one line. "
               "Whatever is pasted, the compiler sees a single long file, called a <b>translation "
               "unit</b>. That is why a header must contain only things that are safe to paste into "
               "many .cpp files: declarations, classes, constants, inline functions."),
        tasks=["Delete the <code>#pragma once</code> line from limits.hpp and press <b>Run</b>. The header is "
               "now pasted twice, so main.cpp contains <code>kMaxTorque</code> twice: "
               "<code>redefinition of 'const double kMaxTorque'</code>. Look at the preprocessor view "
               "again to see both copies. Then put the line back.",
               "In main.cpp, delete the whole body of <code>clampTorque</code> (the four lines from "
               "<code>double clampTorque(double u) {</code> to its <code>}</code>) and Run. It still "
               "<i>compiles</i>, because the declaration in the header is a promise. Then the "
               "<b>linker</b> fails: <code>undefined reference to `clampTorque(double)'</code>. The "
               "compiler trusts declarations; the linker is the one that checks them.",
               "Change <code>#include \"limits.hpp\"</code> to <code>#include \"limit.hpp\"</code> "
               "(a typo): <code>fatal error: limit.hpp: No such file or directory</code>. The "
               "preprocessor stops before the compiler ever starts."],
        preprocess="main.cpp"),

    _t("t_class", "A class from zero: pid.hpp, pid.cpp, main.cpp", [
        ("pid.hpp", r"""
// pid.hpp -- the CONTRACT: declarations only, what a Pid can do.
#pragma once

class Pid {                                  // a new TYPE called Pid
public:                                      // anyone may use what follows
    Pid(double kp, double ki, double dt);    // the constructor: runs when a Pid is created
    double update(double error);             // a member function ("method")
    double integral() const;                 // const: promises not to change the Pid
private:                                     // only Pid's own member functions may touch these
    double kp_, ki_, dt_;                    // every Pid object has its OWN copy of each
    double integral_ = 0.0;                  // default member initializer: starts at 0
};                                           // <-- this semicolon is required
"""),
        ("pid.cpp", r"""
// pid.cpp -- the SECRET: the bodies of what pid.hpp promised.
#include "pid.hpp"     // paste the class in, so this file knows what Pid looks like

// "Pid::" means "belonging to class Pid". Read Pid::Pid as "the constructor of Pid".
// After the colon is the member initializer list: it sets each member BEFORE
// the body { } runs. Here the body is empty because there is nothing left to do.
Pid::Pid(double kp, double ki, double dt) : kp_(kp), ki_(ki), dt_(dt) {}

// "the update that belongs to Pid". Because of "Pid::", this body is INSIDE the
// class, so integral_, kp_ ... are visible and mean THIS object's members.
double Pid::update(double error) {
    integral_ += error * dt_;                // the compiler reads: this->integral_ += error * this->dt_;
    return kp_ * error + ki_ * integral_;
}

// const must be repeated here: it is part of the function's signature.
double Pid::integral() const {
    return integral_;                        // reading is allowed; writing would be an error
}
"""),
        ("main.cpp", r"""
#include <cstdio>
#include "pid.hpp"     // main only needs the contract, never pid.cpp

int main() {
    Pid left(2.0, 10.0, 0.001);     // two OBJECTS of one class: the constructor runs for each.
    Pid right(2.0, 10.0, 0.001);    // Same code, separate data.

    for (int k = 0; k < 3; ++k) {
        double u = left.update(1.0);           // "." calls a member function on an object
        std::printf("tick %d: u = %.3f   left.integral() = %.3f\n", k, u, left.integral());
    }
    std::printf("right was never updated: right.integral() = %.3f\n", right.integral());
    // right.integral_ = 5.0;      // uncomment: error, integral_ is private
    return 0;
}
""")],
        "tick 2: u = 2.030",
        intro=("The same three-file shape as Exercise 0.1, small enough to read in a minute. The comments "
               "are the lesson: read pid.hpp first, then pid.cpp, then main.cpp. Run it, then make each "
               "edit below. Breaking it on purpose shows what each part is for."),
        after=("<b>Two objects, one class.</b> <code>left</code> and <code>right</code> run the same code, "
               "but each has its own <code>integral_</code>. That is why <code>right.integral()</code> is "
               "still 0. Inside <code>Pid::update</code>, the name <code>integral_</code> means \"the "
               "integral_ of the object this was called on\": <code>left.update(1.0)</code> changes "
               "left's. The next card shows how the compiler knows which object that is."),
        tasks=["In pid.cpp, delete <code>Pid::</code> from <code>double Pid::update</code> and Run. Now it is "
               "an ordinary function named <code>update</code> that belongs to no class, so its body cannot "
               "see the members: <code>'integral_' was not declared in this scope</code>. That is what "
               "<code>Pid::</code> is for.",
               "Put it back. Change the body of <code>integral()</code> to <code>return integral_ += 1;</code> "
               "and Run: <code>assignment of member 'Pid::integral_' in read-only object</code>. "
               "<code>const</code> is a promise the compiler enforces.",
               "Undo that. Remove only the <code>const</code> from the definition in pid.cpp (keep it in "
               "pid.hpp): <code>no declaration matches 'double Pid::integral()'</code>. The .cpp "
               "must repeat the header's signature exactly.",
               "In main.cpp, uncomment <code>right.integral_ = 5.0;</code>: <code>'double "
               "Pid::integral_' is private within this context</code>. Only Pid's own functions may write "
               "it, which is how a class keeps its promises.",
               "In pid.hpp, delete the <code>;</code> after the class's closing <code>}</code>: "
               "<code>expected ';' after class definition</code>."]),

    _t("t_this", "The hidden this pointer", [
        ("main.cpp", r"""
#include <cstdio>

struct Counter {            // struct = a class whose members are public by default
    int n = 0;
    void bump() {
        ++n;                // the compiler reads this as:  ++this->n;
        std::printf("bump() on the object at %p   n = %d\n", (void*)this, n);
    }
};

// What the compiler actually generates for bump(), written by hand: an ordinary
// function whose hidden first parameter is a pointer to the object.
void bump_by_hand(Counter* self) {
    ++self->n;              // "->" means "the member of the object this pointer points to"
    std::printf("bump_by_hand  on the object at %p   n = %d\n", (void*)self, self->n);
}

int main() {
    Counter a, b;
    std::printf("&a = %p   &b = %p\n", (void*)&a, (void*)&b);
    a.bump();               // inside bump: this == &a
    a.bump();
    b.bump();               // same code, other object: this == &b
    bump_by_hand(&a);       // exactly what a.bump() does
    return 0;
}
""")],
        "n = 3",
        intro=("A member function is compiled <b>once</b>, yet <code>a.bump()</code> changes a and "
               "<code>b.bump()</code> changes b. The trick: <code>a.bump()</code> is compiled as "
               "<code>bump(&amp;a)</code>. The address of the object is passed as a hidden parameter "
               "called <code>this</code>, and every bare member name inside the function means "
               "<code>this-&gt;member</code>."),
        predict="What will the last line print for n, and why is it not 1?",
        after=("The address printed inside <code>bump()</code> equals <code>&amp;a</code> for the first two "
               "calls and <code>&amp;b</code> for the third. <code>bump_by_hand(&amp;a)</code> continues a's "
               "count, 2 → 3, because it is the same operation spelled out. That is also why you do not "
               "write <code>Pid::integral_</code> inside a member function: inside <code>Pid::update</code>, "
               "<code>integral_</code> is already <code>this-&gt;integral_</code>. You need "
               "<code>Pid::</code> only <i>outside</i> the class, to say which class a definition "
               "belongs to. You need <code>this-&gt;</code> only when a parameter has the same name as a "
               "member."),
        tasks=["Inside <code>bump()</code>, replace <code>++n;</code> with <code>++this-&gt;n;</code>. "
               "Same output: you just wrote what the compiler already did.",
               "Add a parameter with the same name: <code>void bump(int n) { n = n + 1; }</code> changes the "
               "parameter, not the member. <code>this-&gt;n = n;</code> is how you reach the member then. "
               "This is why members get a trailing underscore (<code>n_</code>): it avoids the clash."]),

    # ---------------------------------------------------------------- Stage 1
    _t("t_lifetime", "Constructor and destructor: when exactly do they run?", [
        ("main.cpp", r"""
#include <cstdio>

struct Noisy {
    const char* name;
    // constructor: same name as the class, no return type
    Noisy(const char* n) : name(n) { std::printf("  + construct %s\n", name); }
    // destructor: ~ and the class name. Runs AUTOMATICALLY when the object dies.
    ~Noisy()                      { std::printf("  - destroy   %s\n", name); }
};

Noisy g("global");                  // static storage: created before main, destroyed after it

void f() {
    Noisy local("f's local");       // created when f reaches this line
    std::printf("  f is returning\n");
}                                   // ...destroyed here, at f's closing brace

int main() {
    std::printf("main starts\n");
    Noisy a("a");
    {                               // a block: a new scope
        Noisy b("b");
        Noisy c("c");
        std::printf("  inner block ends\n");
    }                               // c dies, then b: reverse order of creation
    f();
    Noisy* h = new Noisy("heap");   // heap: lives until someone deletes it
    std::printf("  deleting heap\n");
    delete h;                       // its destructor runs HERE, not at any brace
    std::printf("main ends\n");
    return 0;
}                                   // a dies here; the global dies after main returns
""")],
        "- destroy   global",
        intro=("A <b>constructor</b> is the function that runs when an object is created; it sets the "
               "object up. A <b>destructor</b> (<code>~Noisy</code>) runs when the object is destroyed; "
               "it cleans up. You never call either by name. C++ calls them, and <i>when</i> it calls "
               "the destructor is exact: for a local object, at the closing brace of its scope."),
        predict="Before you press Run: in what order will the six \"destroy\" lines appear?",
        after=("<b>Stack objects die at their closing brace, in reverse order of creation</b> (c before b), "
               "like a stack of plates. The heap object dies exactly when <code>delete</code> runs. The "
               "global is created before <code>main</code> starts and destroyed after it returns. Python's "
               "<code>__del__</code> runs \"some time later\" when the garbage collector decides. A C++ "
               "destructor runs at a known line, and that is what makes RAII work: put the cleanup in a "
               "destructor and it cannot be skipped, even by an early <code>return</code> or an "
               "exception.<br><br><b>What a constructor does, step by step:</b> (1) memory for the "
               "object is reserved: on the stack for a local, on the heap for <code>new</code>; (2) each "
               "member is initialised <i>in the order the members are declared</i>, from the initializer "
               "list if it names it, otherwise from its default initializer; (3) the body "
               "<code>{ }</code> runs. Destruction is the mirror image: the destructor body, then the "
               "members in reverse order, then the memory is released."),
        tasks=["Comment out <code>delete h;</code> and Run. \"destroy heap\" never appears: nothing ever "
               "calls its destructor. That is a <b>leak</b>.",
               "Now fix it the modern way. Add <code>#include &lt;memory&gt;</code> at the top, change the "
               "line to <code>std::unique_ptr&lt;Noisy&gt; h = std::make_unique&lt;Noisy&gt;(\"heap\");</code> "
               "and delete the <code>delete</code> line. The heap object now dies at main's closing brace, "
               "just before a. The owner's destructor deletes it for you; that is RAII.",
               "Right after <code>Noisy c(\"c\");</code>, add <code>if (true) return 0;</code> and Run. "
               "c, b and a are still destroyed: an early return cannot skip a destructor."]),

    _t("t_refs", "References, pointers, & and *", [
        ("main.cpp", r"""
#include <cstdio>

void byValue(double x)        { x = 99; std::printf("inside byValue, x = %.0f\n", x); }  // a COPY
void byRef(double& x)         { x = 99; }    // gets the caller's variable itself, under another name
void byPtr(double* x)         { *x = 99; }   // gets an address; *x is "the thing at that address"
double read(const double& x)  { return x; }  // a reference that may not write: no copy, no risk

int main() {
    double q = 1.0;
    double& alias = q;      // & in a TYPE:            a reference, another name for q
    double* where = &q;     // & before a VARIABLE:    "the address of q"
                            // * in a TYPE:            a pointer, holds an address
    alias = 2.0;            // writes q
    *where = 3.0;           // * before a POINTER:     "the thing it points at", so this writes q
    std::printf("q = %.0f   alias = %.0f   *where = %.0f\n", q, alias, *where);
    std::printf("where holds %p, and &q is %p\n", (void*)where, (void*)&q);

    double a = 1, b = 1, c = 1;
    byValue(a);  byRef(b);  byPtr(&c);
    std::printf("after byValue a = %.0f, after byRef b = %.0f, after byPtr c = %.0f\n", a, b, c);
    std::printf("read(q) = %.0f\n", read(q));
    return 0;
}
""")],
        "after byValue a = 1, after byRef b = 99",
        intro=("<code>&amp;</code> and <code>*</code> each mean two different things, depending on "
               "where they stand. <b>In a type</b>: <code>double&amp;</code> is a reference and "
               "<code>double*</code> is a pointer. <b>In an expression</b>: <code>&amp;q</code> takes "
               "q's address and <code>*p</code> follows a pointer to what it points at. Read each "
               "comment next to the line it describes."),
        after=("A <b>reference</b> is another name for an existing variable: it must be bound when "
               "created, can never be null, and never re-points. A <b>pointer</b> is a variable holding "
               "an address: it can be null, can be changed to point elsewhere, and needs <code>*</code> "
               "or <code>-&gt;</code> to reach the object. Rule of thumb for parameters: small values "
               "(<code>double</code>, <code>int</code>) by value; big things you only read by "
               "<code>const T&amp;</code>; things you must modify by <code>T&amp;</code>; a pointer only "
               "when \"nothing\" (<code>nullptr</code>) is a valid answer."),
        tasks=["Write <code>double&amp; broken;</code> inside main (a reference bound to nothing): "
               "<code>'broken' declared as reference but not initialized</code>.",
               "Change <code>read</code> to try writing: <code>{ x = 5; return x; }</code>: "
               "<code>assignment of read-only reference 'x'</code>.",
               "Call <code>byRef(3.0);</code>: <code>cannot bind non-const lvalue reference of type "
               "'double&amp;' to an rvalue of type 'double'</code>. A non-const reference needs a real "
               "variable to write into; a literal is not one. <code>read(3.0)</code> is fine, because "
               "a const reference only reads."]),

    _t("t_unique", "unique_ptr: one owner, moved, never copied", [
        ("main.cpp", r"""
#include <cstdio>
#include <memory>       // std::unique_ptr, std::make_unique
#include <utility>      // std::move

struct Motor {
    int id;
    explicit Motor(int i) : id(i) { std::printf("  + Motor %d\n", id); }
    ~Motor()                      { std::printf("  - Motor %d\n", id); }
};

std::unique_ptr<Motor> makeMotor(int id) {
    return std::make_unique<Motor>(id);       // "new", wrapped in an owner straight away
}

int main() {
    std::unique_ptr<Motor> a = makeMotor(1);  // a owns Motor 1
    // std::unique_ptr<Motor> b = a;          // uncomment: error, a unique_ptr cannot be COPIED
    std::unique_ptr<Motor> b = std::move(a);  // ownership MOVES to b; a is now empty (null)
    std::printf("a is %s, b owns Motor %d\n", a ? "full" : "empty", b->id);
    b.reset();                                // destroy it now (rarely needed)
    std::printf("b is %s\n", b ? "full" : "empty");
    auto c = makeMotor(2);
    std::printf("main ends\n");
    return 0;                                 // c's destructor deletes Motor 2: no "delete" written anywhere
}
""")],
        "- Motor 2",
        intro=("<code>std::unique_ptr&lt;T&gt;</code> is an object that owns one heap object and deletes "
               "it in its own destructor. \"Unique\" means exactly one owner at a time, so copying is "
               "forbidden (two owners would delete twice). Ownership can be <b>moved</b>, though, and the "
               "source becomes empty."),
        after=("Motor 1 is destroyed at <code>b.reset()</code>. Motor 2 is destroyed at main's closing "
               "brace, because <code>c</code> dies there and takes its Motor with it. There is no "
               "<code>delete</code> anywhere in the program and no leak is possible. <code>auto</code> "
               "means \"the compiler writes the type for me\"; here it is "
               "<code>std::unique_ptr&lt;Motor&gt;</code>."),
        tasks=["Uncomment the copy line: <code>use of deleted function 'std::unique_ptr&lt;...&gt;::unique_ptr(const "
               "std::unique_ptr&lt;...&gt;&amp;)'</code>. The copy constructor is <code>= delete</code>d, on "
               "purpose. You will meet <code>= delete</code> properly in Stage 2.",
               "After the move, add <code>std::printf(\"%d\\n\", a-&gt;id);</code>. It compiles, then "
               "crashes or prints garbage, because <code>a</code> is null. A moved-from object is "
               "valid but empty; do not use it."]),

    # ---------------------------------------------------------------- Stage 2
    _t("t_special", "The six special member functions, announcing themselves", [
        ("main.cpp", r"""
#include <cstdio>
#include <utility>
#include <vector>

// A class that prints a line from each of the six special member functions.
struct Loud {
    int v;
    Loud() : v(0)                      { std::printf("     default ctor\n"); }
    Loud(int x) : v(x)                 { std::printf("     ctor(int %d)\n", x); }     // an ordinary ctor
    Loud(const Loud& o) : v(o.v)       { std::printf("     COPY ctor     (from %d)\n", o.v); }
    Loud(Loud&& o) noexcept : v(o.v)   { o.v = -1; std::printf("     MOVE ctor     (from %d)\n", v); }
    Loud& operator=(const Loud& o)     { v = o.v; std::printf("     COPY assign   (= %d)\n", v); return *this; }
    Loud& operator=(Loud&& o) noexcept { v = o.v; o.v = -1; std::printf("     MOVE assign   (= %d)\n", v); return *this; }
    ~Loud()                            { std::printf("     dtor          (%d)\n", v); }
};

int main() {
    std::printf("1. Loud a(7);\n");               Loud a(7);
    std::printf("2. Loud b = a;\n");              Loud b = a;              // NEW object from an existing one
    std::printf("3. Loud c = std::move(a);\n");   Loud c = std::move(a);   // NEW object, steals from a
    std::printf("4. Loud d;\n");                  Loud d;
    std::printf("5. d = b;\n");                   d = b;                   // EXISTING object overwritten
    std::printf("6. d = Loud(9);\n");             d = Loud(9);             // a temporary, moved from
    std::printf("7. two push_backs\n");
    std::vector<Loud> v;
    v.reserve(2);                                 // room for 2, so the vector never has to grow
    v.push_back(b);                               // copies b into the vector
    v.push_back(std::move(c));                    // moves c into the vector
    std::printf("8. end of main\n");
    return 0;
}
""")],
        "MOVE assign   (= 9)",
        intro=("Six member functions are special: if you do not write them, the compiler may write them "
               "for you. Every class has them, even an empty one. This class writes all six and prints "
               "from each, so you can see which one each line of main calls."),
        predict="Line 2, <code>Loud b = a;</code>, has an <code>=</code> in it. Copy assignment, or copy constructor?",
        after=("<b>Construct vs assign:</b> if the object on the left is <i>new</i>, a constructor runs, "
               "even when you write <code>=</code> (line 2). If it already exists, <code>operator=</code> "
               "runs (line 5). <b>Copy vs move:</b> a copy leaves the source intact; a move takes the "
               "source's insides and leaves it empty (here v = -1). <code>std::move(a)</code> does not move "
               "anything by itself; it only marks <code>a</code> as \"may be stolen from\", so the "
               "compiler picks the move version. A temporary like <code>Loud(9)</code> is moved from "
               "automatically, because nobody can use it afterwards.<br><br><table cellpadding='3'>"
               "<tr><td><code>T()</code></td><td>default constructor</td><td><code>T x;</code></td></tr>"
               "<tr><td><code>T(const T&amp;)</code></td><td>copy constructor</td><td><code>T y = x;</code>, "
               "pass by value</td></tr>"
               "<tr><td><code>T(T&amp;&amp;)</code></td><td>move constructor</td><td><code>T y = "
               "std::move(x);</code>, return a local</td></tr>"
               "<tr><td><code>operator=(const T&amp;)</code></td><td>copy assignment</td><td><code>y = x;</code></td></tr>"
               "<tr><td><code>operator=(T&amp;&amp;)</code></td><td>move assignment</td><td><code>y = "
               "std::move(x);</code></td></tr>"
               "<tr><td><code>~T()</code></td><td>destructor</td><td>end of scope, <code>delete</code></td></tr>"
               "</table><br>"
               "<b>Rule of zero:</b> if your members already manage themselves (<code>double</code>, "
               "<code>std::vector</code>, <code>std::unique_ptr</code>), write none of the six; the "
               "compiler's versions copy or move member by member and are correct. Write them only "
               "when the class holds a raw resource itself (rule of five)."),
        tasks=["Delete the line <code>v.reserve(2);</code> and Run. The vector now starts with room for one, "
               "so the second push_back has to grow: it allocates a bigger buffer and <b>moves</b> the "
               "old element across (an extra MOVE ctor and dtor).",
               "Now also delete the word <code>noexcept</code> from the move constructor. The vector "
               "<b>copies</b> instead of moving when it grows. A move that might throw could leave "
               "the vector half-moved, so the vector refuses to use it. This is why move constructors "
               "are marked <code>noexcept</code>.",
               "Delete the two copy functions (copy ctor and copy assign) and Run: line 2 now fails with "
               "<code>use of deleted function</code>. Declaring a move constructor makes the compiler "
               "<i>delete</i> the copy operations it would otherwise have written."]),

    _t("t_default_delete", "= default and = delete", [
        ("main.cpp", r"""
#include <cstdio>

// = default : "compiler, write this one for me, the normal way"
// = delete  : "this one must not exist; any use is a compile error"

class Sample {
public:
    Sample() = default;                          // brings back the no-argument constructor (see task 1)
    Sample(double t, double v) : t_(t), v_(v) {}
    double t() const { return t_; }
    double v() const { return v_; }
private:
    double t_ = 0.0;                             // what Sample() = default uses
    double v_ = 0.0;
};

// A handle to ONE physical motor port. Two copies would mean two owners of one
// port, both closing it, so copying is forbidden outright.
class MotorHandle {
public:
    explicit MotorHandle(int port) : port_(port) { std::printf("  open port %d\n", port_); }
    ~MotorHandle()                               { std::printf("  close port %d\n", port_); }
    MotorHandle(const MotorHandle&) = delete;             // no copy construction
    MotorHandle& operator=(const MotorHandle&) = delete;  // no copy assignment
    int port() const { return port_; }
private:
    int port_;
};

class Controller {
public:
    virtual ~Controller() = default;   // an empty destructor, but VIRTUAL (Stage 4 explains why)
};

void report(const MotorHandle& m) {    // const&: uses the caller's handle, no copy needed
    std::printf("  using port %d\n", m.port());
}

int main() {
    Sample s;                          // uses Sample() = default: t_ = 0, v_ = 0
    Sample r(0.5, 1.25);
    std::printf("s = (%.2f, %.2f)   r = (%.2f, %.2f)\n", s.t(), s.v(), r.t(), r.v());
    MotorHandle m(3);
    report(m);
    // MotorHandle copy = m;           // uncomment: error, use of deleted function
    return 0;
}
""")],
        "close port 3",
        intro=("You can say three things about each special member function: <b>nothing</b> (the "
               "compiler decides whether to write it), <b><code>= default</code></b> (\"write it, the "
               "normal way\"), or <b><code>= delete</code></b> (\"it must not exist\"). "
               "<code>= default</code> on a constructor means \"initialise each member the usual way\"; "
               "on a destructor, \"destroy each member, nothing extra\"."),
        after=("<b>Why <code>Sample() = default;</code> is there:</b> as soon as a class declares <i>any</i> "
               "constructor, the compiler stops writing the no-argument one. "
               "<code>= default</code> asks for it back, with the members taking their default "
               "initializers (<code>= 0.0</code>). <b>Why <code>= delete</code>:</b> it turns a "
               "dangerous operation into a compile error with your class's name on it, instead of a "
               "double-close at run time. <b>Why <code>virtual ~Controller() = default;</code></b>: the "
               "body is empty, so <code>= default</code> is the honest way to write it, but it must "
               "exist so it can be <code>virtual</code>. That makes <code>delete</code> through a "
               "<code>Controller*</code> run the derived class's destructor too (Stage 4 shows what "
               "goes wrong without it).<br><br><b>When does the compiler write them for you?</b> The "
               "default constructor only if you declared no constructor. Copy constructor and copy "
               "assignment only if you declared no move operation. The move operations only if you "
               "declared none of: copy, copy-assign, move-assign, destructor. Easiest rule: write none "
               "of them (rule of zero), or <code>= default</code> / <code>= delete</code> the ones you "
               "mean."),
        tasks=["Delete the line <code>Sample() = default;</code> and Run: <code>no matching function for "
               "call to 'Sample::Sample()'</code>. The two-argument constructor took the default one "
               "away.",
               "Uncomment <code>MotorHandle copy = m;</code>: <code>use of deleted function "
               "'MotorHandle::MotorHandle(const MotorHandle&amp;)'</code>.",
               "Change <code>report</code> to take <code>MotorHandle m</code> (by value, no <code>const&amp;</code>). "
               "Passing by value means copying, so this is the same error. A const reference was the "
               "right parameter type all along."]),

    _t("t_const", "const in four places", [
        ("main.cpp", r"""
#include <cstdio>
#include <vector>

class Joint {
public:
    explicit Joint(double limit) : limit_(limit) {}
    double position() const { return q_; }     // const member function: may read, may not write
    double limit() const    { return limit_; }
    void   move(double dq)  { q_ += dq; }      // not const: it changes the joint
    // double broken() const { q_ = 0; return q_; }  // uncomment: error, a const function writes
private:
    const double limit_;     // a const MEMBER: set once, in the initializer list, never again
    double q_ = 0.0;
};

double total(const std::vector<double>& xs) {  // const&: read the caller's vector, no copy
    double s = 0;
    for (double x : xs) s += x;                // "for each x in xs"
    // xs.push_back(1);      // uncomment: error, xs is const here
    return s;
}

void show(const Joint& j) {                    // a read-only view of a Joint
    std::printf("q = %.2f (limit %.2f)\n", j.position(), j.limit());   // OK: both are const
    // j.move(1.0);          // uncomment: error, move() is not const
}

int main() {
    const double kDt = 0.001;                  // 1. a const variable
    // kDt = 0.002;          // uncomment: error, assignment of read-only variable
    Joint j(3.14);
    j.move(0.5);
    show(j);                                   // 2. a const& parameter
    std::printf("total = %.1f, dt = %.3f\n", total({1, 2, 3}), kDt);
    return 0;
}
""")],
        "total = 6.0",
        intro=("<code>const</code> means \"read-only from here\". It shows up in four places: on a "
               "variable, on a reference or pointer parameter, on a member function (after the "
               "parameter list), and on a member. The rule that ties them together: through a "
               "<code>const Joint&amp;</code> you may only call member functions marked "
               "<code>const</code>."),
        after=("Every uncommented line obeys the rules. Each commented line breaks one; uncomment them "
               "one at a time and read the error. Mark a member function <code>const</code> whenever it "
               "does not change the object. If you forget, it cannot be called through a "
               "<code>const&amp;</code>, and the error appears far away, in someone else's "
               "code: <code>passing 'const Joint' as 'this' argument discards qualifiers</code>. "
               "Inside a const member function, <code>this</code> is a pointer to a <i>const</i> object, "
               "so every member is read-only."),
        tasks=["Uncomment <code>broken()</code>: <code>assignment of member 'Joint::q_' in read-only "
               "object</code>.",
               "Remove <code>const</code> from <code>position()</code> (keep the body): now "
               "<code>show</code> fails with <code>discards qualifiers</code>, because it holds a const Joint.",
               "Uncomment <code>j.move(1.0);</code> in show, then <code>xs.push_back(1);</code>, then "
               "<code>kDt = 0.002;</code>, one at a time."]),

    # ---------------------------------------------------------------- Stage 3
    _t("t_explicit", "A constructor that refuses, and explicit", [
        ("main.cpp", r"""
#include <cstdio>
#include <stdexcept>      // std::invalid_argument

// The invariant: lo_ <= hi_ for EVERY Limits object that exists.
class Limits {
public:
    Limits(double lo, double hi) : lo_(lo), hi_(hi) {
        if (!(lo <= hi))                                  // written this way, it also rejects NaN
            throw std::invalid_argument("Limits: lo > hi");
    }
    double clamp(double x) const { return x < lo_ ? lo_ : (x > hi_ ? hi_ : x); }
private:
    double lo_, hi_;      // private: nobody outside can break the invariant later
};

// explicit: this one-argument constructor will NOT be used for a silent conversion.
class Gain {
public:
    explicit Gain(double k) : k_(k) {}
    double k() const { return k_; }
private:
    double k_;
};

void setGain(Gain g) { std::printf("gain set to %.2f\n", g.k()); }

int main() {
    Limits ok(-1.0, 1.0);
    std::printf("clamp(5) = %.1f\n", ok.clamp(5.0));
    try {
        Limits bad(2.0, 1.0);                     // throws: 'bad' never comes into existence
        std::printf("never printed\n");
    } catch (const std::invalid_argument& e) {
        std::printf("refused: %s\n", e.what());
    }
    setGain(Gain(0.5));       // clear: a Gain is made on purpose
    // setGain(0.5);          // uncomment: error. Delete 'explicit' above and it compiles silently.
    return 0;
}
""")],
        "refused: Limits: lo > hi",
        intro=("A constructor's job is to establish the invariant. If the arguments make that "
               "impossible, it <b>throws</b>, and then the object is never created: there is no "
               "half-built <code>Limits</code> to forget to check. <code>explicit</code> stops a "
               "one-argument constructor from being used behind your back to turn a <code>double</code> "
               "into a <code>Gain</code>."),
        after=("Because the constructor validates and the members are private, every <code>Limits</code> "
               "anywhere in the program satisfies lo ≤ hi, and <code>clamp()</code> never needs to check "
               "again. That is the sense in which a class <i>protects an invariant</i>. Mark one-argument "
               "constructors <code>explicit</code> by default; leave it off only when the conversion is "
               "truly harmless (a <code>std::string</code> from a <code>const char*</code>)."),
        tasks=["Uncomment <code>setGain(0.5);</code>: <code>could not convert '5.0e-1' from 'double' to "
               "'Gain'</code>. Delete <code>explicit</code> and it compiles: C++ silently built a Gain from "
               "0.5. Harmless here; a disaster when the double was a position and the class wanted a "
               "velocity.",
               "Change <code>Limits bad(2.0, 1.0);</code> to <code>Limits bad(0.0, 0.0 / 0.0);</code> (a NaN). "
               "It is still refused, because <code>NaN &lt;= x</code> is false. <code>if (lo &gt; hi)</code> "
               "would have let it through."]),

    # ---------------------------------------------------------------- Stage 4
    _t("t_virtual", "virtual, override, = 0, and the virtual destructor", [
        ("main.cpp", r"""
#include <cstdio>
#include <memory>
#include <vector>

class Controller {                                         // an interface
public:
    virtual ~Controller() { std::printf("    ~Controller\n"); }   // try removing 'virtual' (task 2)
    virtual double update(double e) = 0;                   // = 0: "pure": no body; every derived class MUST write it
    virtual const char* name() const { return "controller"; }     // virtual WITH a default body
    void describe() const { std::printf("  I am a %s\n", name()); } // not virtual, but calls a virtual
};

class P : public Controller {                              // P IS-A Controller
public:
    explicit P(double kp) : kp_(kp) {}
    ~P() { std::printf("    ~P\n"); }
    double update(double e) override { return kp_ * e; }   // override: compiler checks it matches the base
    const char* name() const override { return "P controller"; }
private:
    double kp_;
};

class Bang : public Controller {                           // keeps the default name()
public:
    ~Bang() { std::printf("    ~Bang\n"); }
    double update(double e) override { return e > 0 ? 1.0 : -1.0; }
};

int main() {
    std::vector<std::unique_ptr<Controller>> loops;        // owns controllers of DIFFERENT types
    loops.push_back(std::make_unique<P>(2.0));
    loops.push_back(std::make_unique<Bang>());
    for (const auto& c : loops) {                          // c is a pointer to Controller...
        c->describe();                                     // ...yet the RIGHT name() runs
        std::printf("  update(0.5) = %.2f\n", c->update(0.5));
    }
    // Controller c;          // uncomment: error, an abstract class cannot be created
    std::printf("main ends: the vector deletes both through Controller pointers\n");
    return 0;
}
""")],
        "    ~P",
        intro=("The loop only knows it holds <code>Controller</code> pointers, yet each object runs its "
               "own <code>update()</code> and <code>name()</code>. That is what <code>virtual</code> buys: "
               "the function is chosen at run time from the object's real type (through its vtable), not "
               "at compile time from the pointer's type."),
        after=("<code>P</code> overrides <code>name()</code>; <code>Bang</code> does not, so it gets the "
               "base's \"controller\". At the end, each object is destroyed through a "
               "<code>Controller*</code>: the derived destructor runs first (<code>~P</code>), then the "
               "base part (<code>~Controller</code>), and that only works because <code>~Controller</code> "
               "is virtual. The usual way to write it, when it has nothing to print, is "
               "<code>virtual ~Controller() = default;</code>.<br><br><code>= 0</code> makes a function "
               "<b>pure virtual</b>: the class is then <b>abstract</b> (an interface) and cannot be "
               "created on its own; only derived classes that implement every pure function can. "
               "<code>override</code> adds no behaviour. It is a check: \"this must replace a virtual in "
               "the base\", so a typo in the signature becomes a compile error instead of a silent new "
               "function."),
        tasks=["Uncomment <code>Controller c;</code>: <code>cannot declare variable 'c' to be of abstract "
               "type 'Controller'</code>.",
               "Remove the word <code>virtual</code> from <code>~Controller</code> and Run. Now only "
               "\"~Controller\" prints: <code>~P</code> and <code>~Bang</code> never run, so anything "
               "they own would leak. Officially this is undefined behaviour, and g++ says nothing: the "
               "delete happens inside unique_ptr, in a standard header, where warnings are switched off.",
               "Put it back. In <code>P</code>, change <code>update(double e)</code> to <code>update(float e)</code>: "
               "<code>marked 'override', but does not override</code>. Without <code>override</code> it "
               "would compile here and fail elsewhere with a worse message: P would not replace <code>update(double)</code>, "
               "so P would still be abstract and <code>make_unique&lt;P&gt;</code> would be refused.",
               "Remove <code>virtual</code> from <code>name()</code> in Controller (and both "
               "<code>override</code>s on name). Both controllers now say \"controller\": the call is "
               "chosen by the pointer's type at compile time."]),

    # ---------------------------------------------------------------- Stage 5
    _t("t_template", "A template is a recipe the compiler cooks per type", [
        ("main.cpp", r"""
#include <array>
#include <cstddef>
#include <cstdio>

// A function template: no code exists until you USE it with a type.
template <typename T>
T clampT(T x, T lo, T hi) {
    return x < lo ? lo : (x > hi ? hi : x);
}

// A class template with a SIZE parameter: N is part of the type.
template <typename T, std::size_t N>
class History {
public:
    void push(T x) {
        buf_[head_] = x;
        head_ = (head_ + 1) % N;
        if (count_ < N) ++count_;
    }
    T mean() const {
        T s{};                                   // T{} is "zero" for numbers
        for (std::size_t i = 0; i < count_; ++i) s += buf_[i];
        return count_ ? s / T(count_) : T{};
    }
    std::size_t size() const { return count_; }
private:
    std::array<T, N> buf_{};                     // N values stored INSIDE the object: no heap
    std::size_t head_ = 0, count_ = 0;
};

int main() {
    std::printf("clampT(42, 0, 10)      = %d\n",   clampT(42, 0, 10));      // the compiler writes clampT<int>
    std::printf("clampT(0.7, 0.0, 0.5)  = %.2f\n", clampT(0.7, 0.0, 0.5));  // ...and clampT<double>
    // clampT(42, 0.0, 10);  // uncomment: error, T cannot be int and double at once
    History<double, 4> h;                                                   // one generated class
    for (double x : {1.0, 2.0, 3.0, 4.0, 5.0}) h.push(x);                   // 5 overwrites 1
    std::printf("History<double, 4>: size %d, mean %.2f, sizeof %d bytes\n",
                (int)h.size(), (double)h.mean(), (int)sizeof(h));
    return 0;
}
""")],
        "mean 3.50",
        intro=("A template is not code yet; it is a pattern with a blank (<code>T</code>). When you call "
               "<code>clampT(42, 0, 10)</code>, the compiler <i>deduces</i> T = int and writes a real "
               "function <code>clampT&lt;int&gt;</code> for you. Call it with doubles and it writes a "
               "second one. This is also why templates live in headers: the compiler needs the whole "
               "pattern in every .cpp that uses it."),
        after=("<code>History&lt;double, 4&gt;</code> is a complete class generated for exactly that type "
               "and size: 4 doubles (32 bytes) plus two counters (16 bytes) = 48 bytes, all inside the "
               "object, so creating one never touches the heap. That is why <code>std::array</code> and "
               "Eigen's fixed-size matrices suit a control loop. <code>History&lt;double, 8&gt;</code> "
               "would be a different, unrelated type."),
        tasks=["Uncomment the mixed call: <code>no matching function for call to 'clampT(int, double, int)'</code> "
               "and the note <code>deduced conflicting types for parameter 'T' ('int' and 'double')</code>. "
               "Fix it with <code>clampT&lt;double&gt;(42, 0.0, 10)</code>: naming T yourself turns the ints "
               "into doubles.",
               "Change <code>History&lt;double, 4&gt;</code> to <code>History&lt;int, 4&gt;</code>: the mean "
               "becomes 3.00, because <code>T</code> is int everywhere in the generated class, division included."]),

    # ---------------------------------------------------------------- Stage 6
    _t("t_threads", "Lambdas, a thread, and an atomic", [
        ("main.cpp", r"""
#include <atomic>
#include <cstdio>
#include <thread>

int main() {
    // A lambda is an unnamed function written in place:  [captures](parameters) { body }
    double gain = 2.0;
    auto scale = [gain](double x) { return gain * x; };          // [gain]  : copies gain in
    int calls = 0;
    auto counted = [&calls](double x) { ++calls; return x; };    // [&calls]: refers to calls itself
    std::printf("scale(3) = %.1f\n", scale(3.0));
    counted(1); counted(2);
    std::printf("counted was called %d times\n", calls);

    // Two threads doing ++ on a plain int at the same time is a DATA RACE:
    // undefined behaviour. std::atomic makes each increment indivisible.
    std::atomic<int> ticks{0};
    auto worker = [&ticks] {
        for (int i = 0; i < 100000; ++i) ticks.fetch_add(1, std::memory_order_relaxed);
    };
    std::thread t1(worker), t2(worker);      // both start running now, in parallel
    t1.join();                               // wait for t1 to finish...
    t2.join();                               // ...and t2. Never let a std::thread die un-joined.
    std::printf("ticks = %d\n", ticks.load());
    return 0;
}
""")],
        "ticks = 200000",
        intro=("A <b>lambda</b> is a small function you write where you need it. The square brackets say "
               "which outside variables it may use: <code>[x]</code> takes a copy, <code>[&amp;x]</code> uses "
               "the original. A <code>std::thread</code> runs a function (often a lambda) at the same "
               "time as the rest of the program."),
        after=("<code>scale</code> took its own copy of <code>gain</code>, so changing <code>gain</code> "
               "later would not affect it. <code>counted</code> captured <code>calls</code> by reference, "
               "so it changed main's variable. The two threads made 200 000 increments between them, and "
               "the atomic counted every one. <code>join()</code> waits for a thread to finish. "
               "Destroying a <code>std::thread</code> that was never joined ends the program "
               "(<code>std::terminate</code>)."),
        tasks=["Set <code>gain = 5.0;</code> after creating <code>scale</code> but before calling it: still 6.0. "
               "Change the capture to <code>[&amp;gain]</code>: now 15.0.",
               "Delete <code>t2.join();</code> and Run: the program aborts (<code>terminate called "
               "without an active exception</code>) at the end of main, when t2 is destroyed while "
               "still joinable.",
               "Replace <code>std::atomic&lt;int&gt; ticks{0};</code> with <code>int ticks = 0;</code>, the "
               "<code>fetch_add</code> with <code>++ticks</code> and <code>ticks.load()</code> with "
               "<code>ticks</code>. Run a few times. You may see less than 200 000, or the right "
               "number by luck: the optimiser may merge the loop into one addition. That is what "
               "undefined behaviour means: no guarantee in either direction."]),
]

TRYITS = {t.id: t for t in _TRY}


def tryit_dir(t: TryIt) -> str:
    return os.path.join(cc.WORK, "tryit", t.id)


def ensure_tryit(t: TryIt) -> str:
    """Copy the starting files once; after that the learner's edits are kept."""
    d = tryit_dir(t)
    os.makedirs(d, exist_ok=True)
    for n, text in t.files:
        p = os.path.join(d, n)
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
    return d


def reset_tryit(t: TryIt) -> dict:
    d = tryit_dir(t)
    os.makedirs(d, exist_ok=True)
    for n, text in t.files:
        with open(os.path.join(d, n), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return dict(t.files)


def tryit_build(t: TryIt, gxx: str | None = None) -> tuple:
    """(compile argv, cwd, exe). Compiled from inside the folder, so messages say 'pid.cpp:12'."""
    gxx = gxx or cc.find_gxx() or "g++"
    src = tryit_dir(t)
    out = os.path.join(cc.BUILD, "tryit", t.id)
    os.makedirs(out, exist_ok=True)
    exe = os.path.join(out, "run" + (".exe" if os.name == "nt" else ""))
    cpps = sorted(n for n in os.listdir(src) if n.endswith(".cpp"))
    return [gxx, *cc.CXXFLAGS, "-I.", *cpps, "-o", exe], src, exe


def preprocess_argv(name: str, gxx: str | None = None) -> list:
    return [gxx or cc.find_gxx() or "g++", "-std=c++17", "-E", "-I.", name]


_MARK = re.compile(r'^#\s*(\d+)\s+"((?:[^"\\]|\\.)*)"')


def user_view(pre: str, src: str) -> str:
    """g++ -E output, with the learner's own text kept and system headers folded into one line each.

    Line markers ('# 12 "limits.hpp" 1') say which file the following lines came from; a file
    is the learner's if it is a relative path that exists in their folder."""
    def mine(path):
        return not os.path.isabs(path) and os.path.exists(os.path.join(src, path))

    out, cur, hidden, last = [], None, 0, None
    for line in pre.splitlines():
        m = _MARK.match(line)
        if m:
            cur = m.group(2).replace("\\\\", "\\")
            continue
        if cur is None or not mine(cur):
            if line.strip():
                hidden += 1
            continue
        if hidden:
            out.append(f"// ... {hidden} lines pasted here from the standard library's headers ...")
            hidden = 0
        if cur != last:
            out.append(f"// ===== from {cur} =====")
            last = cur
        if line.strip():
            out.append(line)
    if hidden:
        out.append(f"// ... {hidden} lines from the standard library's headers ...")
    return "\n".join(out)


def run_tryit(t: TryIt, files: dict | None = None, timeout: float = 30.0) -> tuple:
    """For tests: write `files` (default: the originals), compile, run. -> (compiled, log, output)."""
    d = tryit_dir(t)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    for n, text in (files or dict(t.files)).items():
        with open(os.path.join(d, n), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    argv, cwd, exe = tryit_build(t)
    r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        return False, r.stdout + r.stderr, ""
    p = subprocess.run([exe], capture_output=True, text=True, timeout=timeout)
    return True, r.stdout + r.stderr, p.stdout


# =====================================================================
# the linkage table: what goes in the header, what goes in the .cpp
# =====================================================================

CLAMP_BODY = "double clamp(double x, double lo, double hi) { return x < lo ? lo : (x > hi ? hi : x); }"

LINK_FILES = {
    "motor.cpp": '#include "helpers.hpp"\n\ndouble motorCommand(double u) {\n    ++g_ticks;\n'
                 '    return clamp(u, -24.0, 24.0);\n}\n',
    "sensor.cpp": '#include "helpers.hpp"\n\ndouble sensorRead(double raw) {\n    ++g_ticks;\n'
                  '    return clamp(raw * 0.01, -1.0, 1.0);\n}\n',
    "main.cpp": '#include <cstdio>\n#include "helpers.hpp"\n\ndouble sensorRead(double raw);\n'
                'double motorCommand(double u);\n\nint main() {\n    double s = sensorRead(42);\n'
                '    double m = motorCommand(30);\n'
                '    std::printf("sensor %.2f  motor %.2f  ticks %d\\n", s, m, g_ticks);\n}\n',
}


@dataclass(frozen=True)
class Cell:
    stage: str      # "compile" | "link" | "ok" | "wrong"
    message: str    # what the tools print (shortened), or what the program prints
    why: str


# options: (label shown, the line itself)
LINK = {
    "var": {
        "title": "a variable: int g_ticks",
        "header": [("(nothing)", ""), ("extern int g_ticks;", "extern int g_ticks;"),
                   ("int g_ticks = 0;", "int g_ticks = 0;"), ("inline int g_ticks = 0;", "inline int g_ticks = 0;"),
                   ("static int g_ticks = 0;", "static int g_ticks = 0;")],
        "cpp": [("(nothing)", ""), ("int g_ticks = 0;", "int g_ticks = 0;")],
        "fixed": ("double clamp(double x, double lo, double hi);", CLAMP_BODY),   # (header, cpp) for the other one
        "cells": {
            (0, 0): Cell("compile", "motor.cpp:4: error: 'g_ticks' was not declared in this scope",
                         "Nothing anywhere mentions g_ticks, so the word is unknown in motor.cpp."),
            (0, 1): Cell("compile", "motor.cpp:4: error: 'g_ticks' was not declared in this scope",
                         "helpers.cpp does create g_ticks, but motor.cpp, sensor.cpp and main.cpp are each "
                         "compiled alone and never see helpers.cpp. Every file that uses a name needs a "
                         "declaration of it, and the header is how they get one. Removing the "
                         "<code>extern</code> line is not a harmless simplification: it removes the only "
                         "thing that told the other files g_ticks exists."),
            (1, 0): Cell("link", "undefined reference to `g_ticks'",
                         "Every file compiles, because the header promises g_ticks exists. Nobody defined "
                         "it, so the linker cannot find the memory that promise refers to."),
            (1, 1): Cell("ok", "sensor 0.42  motor 24.00  ticks 2",
                         "<b>The classic pattern.</b> <code>extern</code> in the header is a declaration: "
                         "\"an int called g_ticks exists somewhere\", with no memory. helpers.cpp holds "
                         "the one definition, which is the actual 4 bytes. Every object file refers to that "
                         "name, and the linker connects them all to the same 4 bytes."),
            (2, 0): Cell("link", "multiple definition of `g_ticks'; helpers.cpp: first defined here",
                         "A definition in a header is pasted into all four .cpp files, so each object file "
                         "has its own 4 bytes called g_ticks. Each compiles fine alone; the linker finds four "
                         "and refuses. <code>#pragma once</code> cannot help: it only works inside one .cpp."),
            (2, 1): Cell("compile", "helpers.cpp:3: error: redefinition of 'int g_ticks'",
                         "helpers.cpp now contains two definitions in one translation unit, one pasted from "
                         "the header and one written below it. The compiler catches this before the "
                         "linker runs."),
            (3, 0): Cell("ok", "sensor 0.42  motor 24.00  ticks 2",
                         "<b>The C++17 pattern.</b> An <code>inline</code> variable may be defined in every "
                         ".cpp that includes it, as long as every copy is identical; the linker keeps exactly "
                         "one. All files share one g_ticks, and helpers.cpp needs nothing."),
            (3, 1): Cell("compile", "helpers.cpp:3: error: redefinition of 'int g_ticks'",
                         "<code>inline</code> allows one definition per translation unit. helpers.cpp has "
                         "two in the same file."),
            (4, 0): Cell("wrong", "builds and runs, but prints: ticks 0",
                         "<b>No error, wrong answer: the worst kind.</b> At file level, <code>static</code> "
                         "means \"private to this .cpp\" (internal linkage). Each .cpp gets its own separate "
                         "g_ticks: motor.cpp increments motor's, sensor.cpp increments sensor's, and main "
                         "prints main's, which nobody touched."),
            (4, 1): Cell("compile", "helpers.cpp:3: error: redefinition of 'int g_ticks'",
                         "helpers.cpp sees the static one from the header and a second one below it."),
        },
    },
    "fn": {
        "title": "a function: clamp(x, lo, hi)",
        "header": [("(nothing)", ""), ("double clamp(...);", "double clamp(double x, double lo, double hi);"),
                   ("double clamp(...) { ... }", CLAMP_BODY), ("inline double clamp(...) { ... }", "inline " + CLAMP_BODY),
                   ("static double clamp(...) { ... }", "static " + CLAMP_BODY)],
        "cpp": [("(nothing)", ""), ("double clamp(...) { ... }", CLAMP_BODY)],
        "fixed": ("extern int g_ticks;", "int g_ticks = 0;"),
        "cells": {
            (0, 0): Cell("compile", "motor.cpp:5: error: 'clamp' was not declared in this scope",
                         "No file declares clamp before motor.cpp uses it."),
            (0, 1): Cell("compile", "motor.cpp:5: error: 'clamp' was not declared in this scope",
                         "The body exists in helpers.cpp, but motor.cpp is compiled alone and has never "
                         "heard of it. A call needs a declaration in the same translation unit."),
            (1, 0): Cell("link", "undefined reference to `clamp(double, double, double)'",
                         "The declaration let every call compile. No object file contains the body, so the "
                         "linker has nothing to point the calls at."),
            (1, 1): Cell("ok", "sensor 0.42  motor 24.00  ticks 2",
                         "<b>The classic pattern.</b> The header declares (the signature, ending in "
                         "<code>;</code>); one .cpp defines (the body). Change the body later, and only "
                         "helpers.cpp recompiles."),
            (2, 0): Cell("link", "multiple definition of `clamp(double, double, double)'",
                         "The body is pasted into four .cpp files, so four object files each contain a "
                         "clamp, and the one-definition rule allows one."),
            (2, 1): Cell("compile", "helpers.cpp:2: error: redefinition of 'double clamp(double, double, double)'",
                         "helpers.cpp sees the body from the header and its own body: two in one file."),
            (3, 0): Cell("ok", "sensor 0.42  motor 24.00  ticks 2",
                         "<b>Header-only.</b> <code>inline</code> tells the linker the copies are "
                         "intentional and identical, so it keeps one. A member function written inside "
                         "<code>class { }</code> is inline automatically, and so is every template; that is "
                         "why both can live in headers."),
            (3, 1): Cell("compile", "helpers.cpp:2: error: redefinition of 'double clamp(double, double, double)'",
                         "Two bodies in one translation unit, inline or not."),
            (4, 0): Cell("ok", "sensor 0.42  motor 24.00  ticks 2",
                         "It works: each .cpp gets its own private copy, which the linker never compares. "
                         "That is harmless for a function with no state, but the program now contains four "
                         "copies of the machine code. Prefer <code>inline</code>. Compare the variable table: "
                         "the same <code>static</code> silently gave each file its own counter."),
            (4, 1): Cell("compile", "helpers.cpp:2: error: redefinition of 'double clamp(double, double, double)'",
                         "The header's static body and the .cpp's body meet in helpers.cpp."),
        },
    },
}


def link_files(kind: str, h: int, c: int) -> dict:
    """The five files for one cell of the table."""
    spec = LINK[kind]
    fixed_h, fixed_c = spec["fixed"]
    h_line, c_line = spec["header"][h][1], spec["cpp"][c][1]
    if kind == "var":
        hdr = [fixed_h, h_line]
        cpp = [fixed_c, c_line]
    else:
        hdr = [h_line, fixed_h]
        cpp = [c_line, fixed_c]
    files = dict(LINK_FILES)
    files["helpers.hpp"] = "#pragma once\n" + "\n".join(hdr) + "\n"
    files["helpers.cpp"] = '#include "helpers.hpp"\n' + "\n".join(cpp) + "\n"
    return files


# =====================================================================
# the error decoder
# =====================================================================

@dataclass(frozen=True)
class ErrorHint:
    id: str
    pattern: str
    title: str
    meaning: str
    example: tuple = field(default=())     # ((name, text), ...) that produces this message


def _e(id, pattern, title, meaning, example):
    if isinstance(example, str):
        example = (("main.cpp", example.strip("\n") + "\n"),)
    return ErrorHint(id, pattern, title, meaning, tuple(example))


_ERR = [
    _e("qualified_id", r"qualified-id in declaration before '\(' token",
       "You are still inside the previous function",
       "The compiler thinks the next <code>Pid::something()</code> is being declared <i>inside</i> another "
       "function's body, which is not allowed. Almost always, a <code>}</code> is missing somewhere above: "
       "the previous function was never closed. Find the function just above the marked line and count its "
       "braces. It usually comes with <code>expected '}' at end of input</code>.",
       """
struct Pid { double update(double e); void reset(); double i_ = 0; };

double Pid::update(double e) {
    i_ += e;
    return i_;
// <-- the closing brace of update is missing here

void Pid::reset() { i_ = 0; }
"""),
    _e("eoi", r"expected '\}' at end of input",
       "A { was never closed",
       "The file ended while a block was still open. The note <code>to match this '{'</code> points at "
       "the brace that was never closed. Editors help: put the cursor after a <code>{</code> and its "
       "partner lights up.",
       """
int main() {
    if (true) {
        return 0;
}
"""),
    _e("class_semi", r"expected ';' after (class|struct) definition",
       "Missing ; after a class",
       "A class or struct definition ends with <code>};</code>. The semicolon is required, unlike after a "
       "function body.",
       """
class Pid {
    double kp_;
}
int main() {}
"""),
    _e("missing_semi", r"expected '[,;]' (or '[,;]' )?before",
       "Missing ; on the line before",
       "The previous statement has no <code>;</code>. The compiler reports the error where it noticed, "
       "which is the start of the <i>next</i> statement, so look one line up.",
       """
int main() {
    int x = 1
    return x;
}
"""),
    _e("not_declared", r"'[^']+' was not declared in this scope",
       "Unknown name at this point in this file",
       "In <i>this</i> .cpp file, at <i>this</i> line, nothing has declared the name yet. Usual causes: "
       "(1) a missing <code>#include</code> or declaration (each .cpp is compiled alone and knows only what "
       "is pasted into it); (2) a typo; (3) a member used inside a function that is not a member, because "
       "you wrote <code>double update(…)</code> instead of <code>double Pid::update(…)</code>, so the body "
       "is outside Pid and cannot see <code>integral_</code>; (4) using a name above the line that declares it.",
       """
struct Pid { double update(double e); double integral_ = 0; };

double update(double e) {          // forgot Pid::  -> a free function, not the member
    integral_ += e;
    return integral_;
}
"""),
    _e("readonly", r"in read-only object|assignment of read-only",
       "Writing to something that is const",
       "You are changing a value that is const at this point. Inside a <code>const</code> member function "
       "every member is read-only, because <code>this</code> points to a const object. Either the function "
       "should not write, or it should not be const. For a <code>const T&amp;</code> parameter: take it by "
       "value or <code>T&amp;</code> if you really must change it.",
       """
struct Pid {
    double integral_ = 0;
    double integral() const { return integral_ += 1; }   // a getter that writes
};
"""),
    _e("discards", r"discards qualifiers",
       "Calling a non-const member on a const object",
       "You hold the object through a <code>const T&amp;</code> (or it is const), and you called a member "
       "function that is not marked <code>const</code>, so the compiler must assume it writes. If the "
       "function only reads, add <code>const</code> after its parameter list, in the header <i>and</i> "
       "the .cpp.",
       """
struct Joint {
    double q_ = 0;
    double position() { return q_; }        // reads only, but not marked const
};
double show(const Joint& j) { return j.position(); }
"""),
    _e("no_decl_matches", r"no declaration matches",
       "The .cpp signature differs from the header",
       "You defined <code>Pid::something</code> in the .cpp, but the class declares no member with exactly "
       "that signature. Compare character by character: <code>const</code> at the end, parameter types, "
       "<code>&amp;</code>, return type. The note shows the candidate the class does have. If the message "
       "says <code>int Pid::update</code> when you meant double, the return type is missing: C++ "
       "guessed int.",
       """
struct Pid { double integral() const; double i_ = 0; };

double Pid::integral() { return i_; }       // header says const, this does not
"""),
    _e("undefined_ref", r"undefined reference to",
       "Declared, but never defined (a linker error)",
       "Every file compiled, because a declaration promised the thing exists. When the linker joined the "
       "object files, none of them contained it. Causes: the body was never written; it was written "
       "without <code>Pid::</code> (defining a different, free function); its signature differs (const, "
       "parameter types); an <code>extern</code> variable was never defined in any .cpp; or the .cpp "
       "holding it is not part of the build.",
       """
double clamp(double x);                      // declared...

int main() { return (int)clamp(1.0); }       // ...used... and never defined
"""),
    _e("multiple_def", r"multiple definition of",
       "Defined in more than one .cpp (a linker error)",
       "A definition (a function body, or a variable with storage) sits in a header that two or more .cpp "
       "files include, so each object file carries its own copy and the linker finds several. Keep a "
       "declaration in the header and define it once in a .cpp, or mark it <code>inline</code> (C++17 "
       "also allows <code>inline</code> variables). <code>#pragma once</code> does not help: it only "
       "works inside one .cpp.",
       (("twice.hpp", "#pragma once\nint twice(int x) { return 2 * x; }\n"),
        ("twice.cpp", '#include "twice.hpp"\n'),
        ("main.cpp", '#include "twice.hpp"\nint main() { return twice(1); }\n'))),
    _e("redefinition", r"redefinition of",
       "Defined twice in one file",
       "One translation unit sees two definitions of the same thing. Either a header without "
       "<code>#pragma once</code> was pasted twice (directly and through another header), or the same "
       "thing is defined in the header and again in the .cpp that includes it.",
       """
int g_ticks = 0;
int g_ticks = 0;
int main() {}
"""),
    _e("deleted", r"use of deleted function",
       "Copying something that cannot be copied",
       "That function was removed with <code>= delete</code>, either explicitly or because the compiler "
       "could not write it. Most common: copying a <code>std::unique_ptr</code>, a class that holds one, a "
       "<code>std::thread</code>, a <code>std::atomic</code> or a <code>std::mutex</code>, often by "
       "passing it <i>by value</i>. Transfer ownership with <code>std::move(x)</code>, or pass a "
       "reference.",
       """
#include <memory>
int main() {
    auto a = std::make_unique<int>(1);
    auto b = a;                              // a copy of a unique_ptr
}
"""),
    _e("no_match", r"no matching function for call to",
       "No function accepts these arguments",
       "Nothing with that name takes these argument types and count. Read the <code>note: candidate</code> "
       "lines below it: each is a function that does exist, with the reason it did not fit. Constructors "
       "too: <code>Pid p;</code> fails when Pid only has <code>Pid(double kp)</code>, because declaring any "
       "constructor removes the default one (<code>Pid() = default;</code> brings it back).",
       """
struct Pid {
    Pid(double kp) : kp_(kp) {}
    double kp_;
};
int main() { Pid p; }                        // no Pid() exists
"""),
    _e("deduce", r"deduced conflicting types",
       "A template's T would be two types at once",
       "In <code>clampT(42, 0.0, 10)</code>, the first argument says T = int and the second says "
       "T = double. Make the arguments the same type (<code>42.0</code>), or name T yourself: "
       "<code>clampT&lt;double&gt;(42, 0.0, 10)</code>.",
       """
template <typename T> T clampT(T x, T lo, T hi) { return x < lo ? lo : (x > hi ? hi : x); }
int main() { return (int)clampT(42, 0.0, 10); }
"""),
    _e("private", r"is private within this context",
       "Touching a private member from outside",
       "Only the class's own member functions may use its private members. That is deliberate: the class "
       "keeps its invariant by being the only code that writes them. Call a public member function "
       "instead, or ask whether the outside code ought to be a member.",
       """
class Pid { double integral_ = 0; };
int main() { Pid p; p.integral_ = 5; }
"""),
    _e("abstract", r"abstract type|invalid new-expression of abstract|abstract class type",
       "Creating an object of an interface",
       "The class has a pure virtual function (<code>= 0</code>) that nobody overrode, so it is abstract "
       "and no object of it can exist. Either you tried to create the interface itself, or a derived class "
       "missed one pure function. The note names it, and the cause is often a small difference in "
       "its signature.",
       """
struct Controller {
    virtual ~Controller() = default;
    virtual double update(double e) = 0;
};
int main() { Controller c; }
"""),
    _e("override", r"marked '?override'?, but does not override",
       "override, but there is nothing to override",
       "The base has no virtual function with exactly this signature: a missing <code>const</code>, a "
       "different parameter type, or the base function is not virtual. This error is exactly why you write "
       "<code>override</code>. Without it, the typo would silently create a new, unrelated function.",
       """
struct Controller {
    virtual ~Controller() = default;
    virtual double update(double e) const = 0;
};
struct P : Controller {
    double update(double e) override { return e; }   // the base's is const
};
"""),
    _e("not_member_std", r"is not a member of 'std'",
       "Missing #include for a standard name",
       "<code>std::X</code> exists, but its header is not included in this file. "
       "<code>unique_ptr</code>/<code>make_unique</code> → <code>&lt;memory&gt;</code>, "
       "<code>vector</code> → <code>&lt;vector&gt;</code>, <code>move</code> → <code>&lt;utility&gt;</code>, "
       "<code>printf</code> → <code>&lt;cstdio&gt;</code>, <code>atomic</code> → <code>&lt;atomic&gt;</code>, "
       "<code>thread</code> → <code>&lt;thread&gt;</code>, <code>string</code> → <code>&lt;string&gt;</code>. "
       "g++'s note usually names the header.",
       """
int main() { std::vector<int> v; }
"""),
    _e("not_a_type", r"does not name a type",
       "Unknown type name",
       "The compiler does not know this type at this point. Missing <code>#include</code>, missing "
       "<code>std::</code>, a typo, or the type is declared further down the file.",
       """
Vector3 position;
int main() {}
"""),
    _e("incomplete", r"incomplete type",
       "Only forward-declared",
       "The compiler has seen <code>class Robot;</code> but not the class itself, so it does not know the "
       "size or the members. That is enough for a pointer or reference, not for using members or creating "
       "one. Include the header that defines it in the .cpp that uses it.",
       """
class Robot;
int id(Robot& r) { return r.id; }
"""),
    _e("pointer_dot", r"which is of pointer type",
       "Use -> on a pointer",
       "<code>p</code> holds an address, not an object. Reach the object's member with "
       "<code>p-&gt;member</code> (short for <code>(*p).member</code>). The dot is for objects and "
       "references.",
       """
struct A { int x = 0; };
int main() { A* p = new A; int v = p.x; delete p; return v; }
"""),
    _e("arrow_nonptr", r"base operand of '->' has non-pointer type",
       "Use . on an object",
       "This is an object or a reference, not a pointer, so use <code>a.member</code>. (Smart pointers "
       "such as <code>unique_ptr</code> do use <code>-&gt;</code>, because they behave like pointers.)",
       """
struct A { int x = 0; };
int main() { A a; return a->x; }
"""),
    _e("bind_ref", r"cannot bind non-const lvalue reference",
       "A temporary passed where T& is required",
       "A non-const reference parameter must refer to a real variable it can write into. A temporary such "
       "as <code>3.0</code> or the result of <code>f()</code> is not one. If the function only reads, take "
       "<code>const T&amp;</code>; if it needs its own copy, take it by value.",
       """
void set(double& x) { x = 1; }
int main() { set(3.0); }
"""),
    _e("ref_uninit", r"declared as reference but not initialized",
       "A reference must be bound when it is created",
       "A reference is another name for an existing object, so it needs that object at once: "
       "<code>double&amp; r = q;</code>. It can never be null or re-bound later. If you need \"maybe "
       "nothing\", use a pointer.",
       """
int main() { double& r; }
"""),
    _e("no_convert", r"could not convert|conversion from '[^']+' to non-scalar type",
       "No conversion between these types",
       "The value has a different type and there is no allowed way to turn it into the one wanted. A "
       "frequent reason is an <code>explicit</code> constructor: write the conversion out, as in "
       "<code>Gain(0.5)</code>.",
       """
struct Gain { explicit Gain(double k) : k_(k) {} double k_; };
void setGain(Gain g) {}
int main() { setGain(0.5); }
"""),
    _e("no_member", r"has no member named",
       "No member with that name",
       "A typo, the wrong object type, or a member declared in a different class. Through a base-class "
       "pointer you can only call what the base declares.",
       """
struct Pid { double update(double e) { return e; } };
int main() { Pid p; p.updat(1.0); }
"""),
    _e("reorder", r"will be initialized after",
       "Initializer list in a different order from the members (a warning)",
       "Members are always initialised in the order they are <i>declared</i> in the class, whatever order "
       "you write them after the colon. If one uses another, it may read garbage. Write the initializer "
       "list in declaration order.",
       """
struct P {
    P(double dt) : b_(dt), a_(b_ * 2) {}     // a_ is declared first, so it is set first, from garbage b_
    double a_;
    double b_;
};
int main() { P p(1.0); return (int)p.a_; }
"""),
    _e("no_return", r"control reaches end of non-void function|no return statement in function returning non-void",
       "A path with no return (a warning you should treat as an error)",
       "The function promises a value, but some path reaches the closing brace without a "
       "<code>return</code>. That is undefined behaviour: with optimisation on, it can do anything at all. "
       "Add the missing <code>return</code>.",
       """
double sign(double x) {
    if (x > 0) return 1.0;
    if (x < 0) return -1.0;
}
int main() { return (int)sign(0.0); }
"""),
    _e("no_file", r"No such file or directory",
       "#include cannot find the file",
       "The preprocessor stops at once. Check the spelling and the folder. <code>#include \"x.hpp\"</code> "
       "looks next to the current file first; <code>#include &lt;x&gt;</code> looks only in the "
       "include paths.",
       """
#include "pidd.hpp"
int main() {}
"""),
]

ERRORS = {e.id: e for e in _ERR}
_COMPILED = [(e, re.compile(e.pattern)) for e in _ERR]


def decode(log: str, limit: int = 3) -> list:
    """The hints for the messages in a g++ log, in the order they first appear."""
    found = []
    for line in log.splitlines():
        for e, rx in _COMPILED:
            if e not in found and rx.search(line):
                found.append(e)
                break
        if len(found) >= limit:
            break
    return found


def compile_example(e: ErrorHint, timeout: float = 120.0) -> str:
    """For tests and the decoder's 'compile it' button: build e.example, return g++'s output."""
    d = os.path.join(cc.BUILD, "decoder", e.id)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    for n, text in e.example:
        with open(os.path.join(d, n), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    argv = example_argv(e)
    r = subprocess.run(argv, cwd=d, capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr


def example_dir(e: ErrorHint) -> str:
    return os.path.join(cc.BUILD, "decoder", e.id)


def example_argv(e: ErrorHint, gxx: str | None = None) -> list:
    """Compile (and link, so linker errors show) the example from inside its folder."""
    cpps = [n for n, _ in e.example if n.endswith(".cpp")]
    exe = "a" + (".exe" if os.name == "nt" else "")
    flags = [f for f in cc.CXXFLAGS if f != "-static"]
    return [gxx or cc.find_gxx() or "g++", *flags, "-I.", *cpps, "-o", exe]
