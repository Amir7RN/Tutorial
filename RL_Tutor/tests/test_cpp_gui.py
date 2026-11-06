"""C++ chapter GUI: the editor's keys, and a real check through the exercise card."""

import os
import shutil
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ctrlcore import cpp_course as cc


def _app():
    return QApplication.instance() or QApplication([])


class EditorKeys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _app()
        from app.widgets.cpp_editor import CppEditor
        cls.Ed = CppEditor

    def _ed(self, text=""):
        ed = self.Ed(text)
        ed.show()
        return ed

    def test_tab_inserts_spaces_to_the_next_stop(self):
        ed = self._ed("")
        QTest.keyClicks(ed, "ab")
        QTest.keyClick(ed, Qt.Key_Tab)
        self.assertEqual(ed.toPlainText(), "ab  ")

    def test_enter_keeps_indent_and_opens_blocks(self):
        ed = self._ed("")
        QTest.keyClicks(ed, "int f() {")
        self.assertEqual(ed.toPlainText(), "int f() {}")          # auto-closed
        QTest.keyClick(ed, Qt.Key_Return)
        self.assertEqual(ed.toPlainText(), "int f() {\n    \n}")  # block opened, } on its own line
        QTest.keyClicks(ed, "x = 1;")
        QTest.keyClick(ed, Qt.Key_Return)
        self.assertEqual(ed.toPlainText(), "int f() {\n    x = 1;\n    \n}")

    def test_closing_brace_dedents_and_steps_over(self):
        ed = self._ed("    ")
        ed.moveCursor(QTextCursor.End)
        QTest.keyClicks(ed, "}")
        self.assertEqual(ed.toPlainText(), "}")
        ed2 = self._ed("")
        QTest.keyClicks(ed2, "f(")
        QTest.keyClicks(ed2, ")")
        self.assertEqual(ed2.toPlainText(), "f()")             # stepped over, not doubled

    def test_block_indent_and_dedent(self):
        ed = self._ed("a;\nb;\nc;")
        ed.selectAll()
        QTest.keyClick(ed, Qt.Key_Tab)
        self.assertEqual(ed.toPlainText(), "    a;\n    b;\n    c;")
        QTest.keyClick(ed, Qt.Key_Backtab)
        self.assertEqual(ed.toPlainText(), "a;\nb;\nc;")

    def test_backspace_removes_one_indent_level(self):
        ed = self._ed("        ")
        ed.moveCursor(QTextCursor.End)
        QTest.keyClick(ed, Qt.Key_Backspace)
        self.assertEqual(ed.toPlainText(), "    ")

    def test_toggle_comment_and_move_line(self):
        ed = self._ed("    a;\n    b;")
        ed.selectAll()
        QTest.keyClick(ed, Qt.Key_Slash, Qt.ControlModifier)
        self.assertEqual(ed.toPlainText(), "    // a;\n    // b;")
        QTest.keyClick(ed, Qt.Key_Slash, Qt.ControlModifier)
        self.assertEqual(ed.toPlainText(), "    a;\n    b;")
        ed2 = self._ed("one\ntwo")
        QTest.keyClick(ed2, Qt.Key_Down, Qt.AltModifier)
        self.assertEqual(ed2.toPlainText(), "two\none")

    def test_access_label_indents_next_line(self):
        ed = self._ed("")
        QTest.keyClicks(ed, "public:")
        QTest.keyClick(ed, Qt.Key_Return)
        self.assertEqual(ed.toPlainText(), "public:\n    ")


@unittest.skipIf(cc.find_gxx() is None, "g++ not installed")
class ExerciseCardCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _app()
        cls.tmp = tempfile.mkdtemp(prefix="cppgui_")
        cls.saved = (cc.WORK, cc.BUILD, cc.PROGRESS)
        cc.WORK = os.path.join(cls.tmp, "work")
        cc.BUILD = os.path.join(cls.tmp, "build")
        cc.PROGRESS = os.path.join(cc.WORK, "progress.json")

    @classmethod
    def tearDownClass(cls):
        cc.WORK, cc.BUILD, cc.PROGRESS = cls.saved
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _wait(self, card, timeout=90000):
        loop = QEventLoop()
        got = []
        card.passed.connect(lambda ex, ok: (got.append(ok), loop.quit()))
        QTimer.singleShot(timeout, loop.quit)
        loop.exec()
        return got

    def test_starter_fails_then_solution_passes(self):
        from app.widgets.cpp_exercise import ExerciseCard
        card = ExerciseCard("s1_raii", "1.1")
        card.show()
        card.check()
        self.assertEqual(self._wait(card), [False])
        self.assertFalse(card.report.passed)
        sol = cc.solution_files(cc.EXERCISES["s1_raii"])["sample_buffer.hpp"]
        card.editors["sample_buffer.hpp"].setPlainText(sol)
        card.check()
        self.assertEqual(self._wait(card), [True])
        self.assertTrue(cc.load_progress().get("s1_raii"))
        with open(os.path.join(cc.WORK, "s1_raii", "sample_buffer.hpp"), encoding="utf-8") as f:
            self.assertEqual(f.read(), sol)                 # saved before compiling

    def test_compile_error_marks_the_line(self):
        from app.widgets.cpp_exercise import ExerciseCard
        card = ExerciseCard("s2_const", "2.2")
        card.show()
        card.check()
        self.assertEqual(self._wait(card), [False])
        self.assertFalse(card.report.compiled)
        self.assertTrue(card.editors["joint_state.hpp"].diags)   # a red dot in the gutter
        self.assertIn("joint_state.hpp:", card.results.text())   # a clickable location


class Pages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cpppages_")
        self.saved = (cc.WORK, cc.BUILD, cc.PROGRESS)
        cc.WORK, cc.BUILD = os.path.join(self.tmp, "work"), os.path.join(self.tmp, "build")
        cc.PROGRESS = os.path.join(cc.WORK, "progress.json")

    def tearDown(self):
        cc.WORK, cc.BUILD, cc.PROGRESS = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_labs_are_local_and_every_page_builds(self):
        import re
        _app()
        from app.pages import LESSON_CLASSES
        from app.pages.cpp_course import CPP_PAGES, ExerciseCard
        from app.widgets.step_lab import STEPLAB_DIR
        for name in ("cpp_memory.html", "cpp_build.html", "cpp_rt.html"):
            src = open(os.path.join(STEPLAB_DIR, name), encoding="utf-8").read()
            self.assertFalse(re.findall(r'<script src="http', src), name)
        self.assertEqual([c.NUM for c in CPP_PAGES], list(range(150, 150 + len(CPP_PAGES))))
        self.assertIs(LESSON_CLASSES[-1], CPP_PAGES[-1])
        used = []
        for cls in CPP_PAGES:
            page = cls()
            used += [c.ex.id for c in page.findChildren(ExerciseCard)]
            page.deleteLater()
        self.assertEqual(sorted(used), sorted(cc.EXERCISES))   # every exercise on exactly one page

    def test_sidebar_groups_cover_every_section(self):
        _app()
        from app import theme
        from app.pages import LESSON_CLASSES
        named = {s for _n, _c, secs in theme.SIDEBAR_GROUPS for s in secs}
        self.assertEqual({c.SECTION for c in LESSON_CLASSES} - named, set())
        self.assertEqual(theme.group_of("Beam Balance"), "PhD Project")
        self.assertEqual(theme.group_of("C++ · Project"), "C++")


if __name__ == "__main__":
    unittest.main()
