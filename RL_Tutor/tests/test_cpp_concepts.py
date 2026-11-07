"""The C++ beginner layer says what the compiler does; check every claim against the real g++.

- every Try-it compiles and prints what it says it prints;
- every "change it and run again" edit produces the message or output the card promises;
- every cell of the header/.cpp linkage table fails (or runs) at the stage it claims;
- every error-decoder example produces a message its own pattern recognises;
- the widgets build and run a program through the GUI.
"""

import os
import re
import shutil
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ctrlcore import cpp_concepts as k
from ctrlcore import cpp_course as cc

HAVE_GXX = cc.find_gxx() is not None


class _TempDirs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="cppconcepts_")
        cls.saved = (cc.WORK, cc.BUILD, cc.PROGRESS)
        cc.WORK = os.path.join(cls.tmp, "work")
        cc.BUILD = os.path.join(cls.tmp, "build")
        cc.PROGRESS = os.path.join(cc.WORK, "progress.json")

    @classmethod
    def tearDownClass(cls):
        cc.WORK, cc.BUILD, cc.PROGRESS = cls.saved
        shutil.rmtree(cls.tmp, ignore_errors=True)


# (tryit, file, old, new, kind, expected)
#   kind "log": compile/link fails and the log contains `expected`
#   kind "out": it runs and the output contains `expected`
#   kind "not": it runs and the output does NOT contain `expected`
EDITS = [
    ("t_include", "limits.hpp", '#pragma once                       // "paste me at most once into each .cpp"\n', "",
     "log", "redefinition of 'const double kMaxTorque'"),
    ("t_include", "main.cpp",
     "double clampTorque(double u) {\n    if (u >  kMaxTorque) return  kMaxTorque;\n"
     "    if (u < -kMaxTorque) return -kMaxTorque;\n    return u;\n}\n", "",
     "log", "undefined reference to `clampTorque(double)'"),
    ("t_include", "main.cpp", '#include "limits.hpp"    // OUR', '#include "limit.hpp"    // OUR',
     "log", "limit.hpp: No such file or directory"),
    ("t_class", "pid.cpp", "double Pid::update(", "double update(", "log", "'integral_' was not declared in this scope"),
    ("t_class", "pid.cpp", "    return integral_;                        // reading",
     "    return integral_ += 1;                   // reading", "log",
     "assignment of member 'Pid::integral_' in read-only object"),
    ("t_class", "pid.cpp", "double Pid::integral() const {", "double Pid::integral() {",
     "log", "no declaration matches 'double Pid::integral()'"),
    ("t_class", "main.cpp", "// right.integral_ = 5.0;", "right.integral_ = 5.0;",
     "log", "'double Pid::integral_' is private within this context"),
    ("t_class", "pid.hpp", "};                                           // <-- this",
     "}                                            // <-- this", "log", "expected ';' after class definition"),
    ("t_this", "main.cpp", "        ++n;                // the compiler", "        ++this->n;          // the compiler",
     "out", "n = 3"),
    ("t_lifetime", "main.cpp", "    delete h;  ", "    // delete h;  ", "not", "destroy   heap"),
    ("t_lifetime", "main.cpp", '        std::printf("  inner block ends\\n");',
     '        if (true) return 0;\n        std::printf("  inner block ends\\n");', "out", "- destroy   a"),
    ("t_refs", "main.cpp", "    double q = 1.0;\n", "    double q = 1.0;\n    double& broken;\n",
     "log", "'broken' declared as reference but not initialized"),
    ("t_refs", "main.cpp", "double read(const double& x)  { return x; }",
     "double read(const double& x)  { x = 5; return x; }", "log", "assignment of read-only reference 'x'"),
    ("t_refs", "main.cpp", "    byValue(a);", "    byRef(3.0);\n    byValue(a);", "log",
     "cannot bind non-const lvalue reference of type 'double&' to an rvalue of type 'double'"),
    ("t_unique", "main.cpp", "    // std::unique_ptr<Motor> b = a;", "    std::unique_ptr<Motor> b2 = a;",
     "log", "use of deleted function"),
    ("t_special", "main.cpp", "    v.reserve(2);", "", "out", "MOVE ctor     (from 7)"),
    ("t_default_delete", "main.cpp", "    Sample() = default;", "", "log",
     "no matching function for call to 'Sample::Sample()'"),
    ("t_default_delete", "main.cpp", "    // MotorHandle copy = m;", "    MotorHandle copy = m;", "log",
     "use of deleted function 'MotorHandle::MotorHandle(const MotorHandle&)'"),
    ("t_default_delete", "main.cpp", "void report(const MotorHandle& m) {", "void report(MotorHandle m) {",
     "log", "use of deleted function"),
    ("t_const", "main.cpp", "    // double broken() const", "    double broken() const", "log",
     "assignment of member 'Joint::q_' in read-only object"),
    ("t_const", "main.cpp", "    double position() const { return q_; }", "    double position() { return q_; }",
     "log", "discards qualifiers"),
    ("t_const", "main.cpp", "    // kDt = 0.002;", "    kDt = 0.002;", "log", "assignment of read-only variable 'kDt'"),
    ("t_explicit", "main.cpp", "    // setGain(0.5);", "    setGain(0.5);", "log", "could not convert"),
    ("t_explicit", "main.cpp", "Limits bad(2.0, 1.0);", "Limits bad(0.0, 0.0 / 0.0);", "out", "refused"),
    ("t_virtual", "main.cpp", "    // Controller c;", "    Controller c;", "log",
     "cannot declare variable 'c' to be of abstract type 'Controller'"),
    ("t_virtual", "main.cpp", "    virtual ~Controller()", "    ~Controller()", "not", "~P"),
    ("t_virtual", "main.cpp", "    double update(double e) override { return kp_ * e; }",
     "    double update(float e) override { return kp_ * e; }", "log", "marked 'override', but does not override"),
    ("t_template", "main.cpp", "    // clampT(42, 0.0, 10);", "    clampT(42, 0.0, 10);", "log",
     "deduced conflicting types for parameter 'T' ('int' and 'double')"),
    ("t_template", "main.cpp", "    // clampT(42, 0.0, 10);", "    clampT<double>(42, 0.0, 10);", "out", "mean 3.50"),
    ("t_template", "main.cpp", "History<double, 4> h;", "History<int, 4> h;", "out", "mean 3.00"),
    ("t_threads", "main.cpp", '    std::printf("scale(3)', '    gain = 5.0;\n    std::printf("scale(3)', "out",
     "scale(3) = 6.0"),
    ("t_threads", "main.cpp", "[gain](double x)", "[&gain](double x)", "out", "scale(3) = 6.0"),
]


@unittest.skipUnless(HAVE_GXX, "g++ not installed")
class TryIts(_TempDirs):
    def test_every_tryit_runs_and_prints_its_line(self):
        for t in k.TRYITS.values():
            with self.subTest(t.id):
                ok, log, out = k.run_tryit(t)
                self.assertTrue(ok, log)
                self.assertIn(t.expect, out)
                self.assertNotIn("warning", log)        # the unchanged program is clean

    def test_the_suggested_edits_do_what_the_cards_say(self):
        for tid, name, old, new, kind, want in EDITS:
            with self.subTest(f"{tid}: {want}"):
                files = dict(k.TRYITS[tid].files)
                self.assertIn(old, files[name], "the edit's anchor must exist in the original")
                files[name] = files[name].replace(old, new)
                ok, log, out = k.run_tryit(k.TRYITS[tid], files)
                if kind == "log":
                    self.assertFalse(ok, out)
                    self.assertIn(want, log)
                elif kind == "out":
                    self.assertTrue(ok, log)
                    self.assertIn(want, out)
                else:
                    self.assertTrue(ok, log)
                    self.assertNotIn(want, out)

    def test_destruction_order_is_what_the_card_explains(self):
        ok, _, out = k.run_tryit(k.TRYITS["t_lifetime"])
        order = [ln.strip()[len("- destroy"):].strip() for ln in out.splitlines() if "- destroy" in ln]
        self.assertEqual(order, ["c", "b", "f's local", "heap", "a", "global"])

    def test_a_join_forgotten_aborts(self):
        t = k.TRYITS["t_threads"]
        files = dict(t.files)
        files["main.cpp"] = files["main.cpp"].replace("    t2.join();", "")
        k.run_tryit(t, files)
        _, _, exe = k.tryit_build(t)
        import subprocess
        self.assertNotEqual(subprocess.run([exe], capture_output=True).returncode, 0)

    def test_preprocessor_view_shows_the_header_pasted_once(self):
        t = k.TRYITS["t_include"]
        k.run_tryit(t)
        import subprocess
        r = subprocess.run(k.preprocess_argv("main.cpp"), cwd=k.tryit_dir(t), capture_output=True, text=True)
        view = k.user_view(r.stdout, k.tryit_dir(t))
        self.assertEqual(view.count("const double kMaxTorque = 24.0;"), 1)
        self.assertIn("// ===== from limits.hpp =====", view)
        self.assertIn("lines pasted here from the standard library", view)
        self.assertNotIn("#include", view)
        self.assertIn("int main()", view)


@unittest.skipUnless(HAVE_GXX, "g++ not installed")
class LinkageTable(_TempDirs):
    def test_every_cell_fails_or_runs_where_it_says(self):
        import subprocess
        gxx = cc.find_gxx()
        for kind, spec in k.LINK.items():
            self.assertEqual(set(spec["cells"]), {(h, c) for h in range(len(spec["header"]))
                                                  for c in range(len(spec["cpp"]))})
            for (h, c), cell in spec["cells"].items():
                with self.subTest(f"{kind} {h},{c}"):
                    d = os.path.join(cc.BUILD, "lt", f"{kind}{h}{c}")
                    os.makedirs(d)
                    for n, text in k.link_files(kind, h, c).items():
                        with open(os.path.join(d, n), "w", encoding="utf-8") as f:
                            f.write(text)
                    exe = os.path.join(d, "a.exe")
                    comp = subprocess.run([gxx, "-std=c++17", "-fdiagnostics-color=never", "-static", "-c",
                                           "helpers.cpp", "motor.cpp", "sensor.cpp", "main.cpp"],
                                          cwd=d, capture_output=True, text=True)
                    if cell.stage == "compile":
                        self.assertNotEqual(comp.returncode, 0)
                        where, _, msg = cell.message.partition(": error: ")
                        self.assertIn(msg, comp.stderr)
                        self.assertIn(where.split(":")[0] + ":" + where.split(":")[1] + ":", comp.stderr)
                        continue
                    self.assertEqual(comp.returncode, 0, comp.stderr)
                    link = subprocess.run([gxx, "-static", "helpers.o", "motor.o", "sensor.o", "main.o",
                                           "-o", exe], cwd=d, capture_output=True, text=True)
                    if cell.stage == "link":
                        self.assertNotEqual(link.returncode, 0)
                        self.assertIn(cell.message.split(";")[0], link.stderr)
                        continue
                    self.assertEqual(link.returncode, 0, link.stderr)
                    out = subprocess.run([exe], capture_output=True, text=True).stdout
                    want = cell.message.split("prints: ")[-1]
                    self.assertIn(want, out)


@unittest.skipUnless(HAVE_GXX, "g++ not installed")
class Decoder(_TempDirs):
    def test_every_example_produces_its_own_message(self):
        for e in k.ERRORS.values():
            with self.subTest(e.id):
                log = k.compile_example(e)
                self.assertRegex(log, e.pattern)
                self.assertIn(e, k.decode(log, limit=5))

    def test_the_session_errors_are_decoded(self):
        log = ("s0_header\\pid.cpp:20:19: error: qualified-id in declaration before '(' token\n"
               "s0_header\\pid.cpp:26:74: error: expected '}' at end of input\n")
        self.assertEqual([e.id for e in k.decode(log)], ["qualified_id", "eoi"])
        self.assertEqual(k.decode("all good"), [])


class Widgets(_TempDirs):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_link_table_every_cell_selectable(self):
        from app.widgets.cpp_tryit import LinkTable
        w = LinkTable()
        for kind, spec in k.LINK.items():
            w.set_kind(kind)
            for (h, c) in spec["cells"]:
                w.select(h, c)
                self.assertIn(spec["cells"][(h, c)].message.split("'")[0][:20], w.verdict.text())

    def test_decoder_paste(self):
        from app.widgets.cpp_tryit import ErrorDecoder
        w = ErrorDecoder()
        w.paste.setPlainText("main.cpp:3:5: error: use of deleted function 'X::X(const X&)'")
        self.assertIn("cannot be copied", w.found.text())
        for i in range(w.pick.count()):
            w._show_pick(i)

    @unittest.skipUnless(HAVE_GXX, "g++ not installed")
    def test_tryit_card_runs_and_marks_errors(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from app.widgets.cpp_tryit import TryItCard
        card = TryItCard("t_class")
        card.show()

        def wait():
            loop = QEventLoop()
            QTimer.singleShot(90000, loop.quit)
            t = QTimer()
            t.timeout.connect(lambda: (not card._busy) and loop.quit())
            t.start(100)
            loop.exec()

        card.run()
        wait()
        self.assertIn("tick 2: u = 2.030", card.out.toPlainText())
        self.assertTrue(card.after.isVisible() or not card.isVisible())
        ed = card.editors["pid.cpp"]
        ed.setPlainText(ed.toPlainText().replace("double Pid::update(", "double update("))
        card.run()
        wait()
        self.assertTrue(ed.diags)                                   # red line in pid.cpp
        self.assertIn("Unknown name", card.decoded.text())          # explained in plain words
        with open(os.path.join(card.dir, "pid.cpp"), encoding="utf-8") as f:
            self.assertIn("double update(", f.read())               # saved before compiling
        card.reset()
        self.assertIn("double Pid::update(", ed.toPlainText())


if __name__ == "__main__":
    unittest.main()
