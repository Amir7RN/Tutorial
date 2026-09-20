"""Coverage, numerical examples, rendering and timer lifecycle of lesson movies."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"))

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QScrollArea, QVBoxLayout, QWidget
from PySide6.QtTest import QTest

from app import theme
from app.pages import PAGE_CLASSES
from app.widgets.lesson_animation import LessonAnimation
from app.widgets.lesson_stories import STORIES, deterministic_sweeps


class LessonAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # Windows offscreen Qt does not use the desktop font discovery backend.
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        if (fonts / "segoeui.ttf").exists():
            QFontDatabase.addApplicationFont(str(fonts / "segoeui.ttf"))
        cls.app.setFont(QFont("Segoe UI", 9))
        cls.app.setStyleSheet(theme.QSS)

    def test_exact_requested_page_coverage(self):
        self.assertEqual(set(STORIES), {p.__name__ for p in PAGE_CLASSES[15:]})
        self.assertFalse(set(STORIES) & {p.__name__ for p in PAGE_CLASSES[:15]})
        for story in STORIES.values():
            self.assertGreaterEqual(len(story.steps), 3)
            self.assertTrue(all(s.title and s.caption for s in story.steps))

    def test_backup_and_lake_examples_are_valid(self):
        from rlcore.frozen_lake import build_model
        from rlcore.dp import value_iteration
        sweeps = deterministic_sweeps()
        result = value_iteration(build_model("deterministic", "gym"), gamma=.9)
        # value_iteration returns (policy, values, sweep count).
        for actual, expected in zip(sweeps[-1], result[1]):
            self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(sweeps[6][0], .9**5)
        self.assertEqual(sweeps[5][0], 0)
        for values in sweeps:
            for state in (5, 7, 11, 12, 15):
                self.assertEqual(values[state], 0)
        for story in STORIES.values():
            for step in story.steps:
                if story.scene == "backup" and step.data.get("reduce") != "max":
                    self.assertAlmostEqual(sum(step.data.get("weights", (1/3,)*3)), 1)
                if story.scene == "lake":
                    route = step.data.get("route", (0, 4, 8, 9, 13, 14, 15))
                    for a, b in zip(route, route[1:]):
                        self.assertNotIn(a, (5, 7, 11, 12, 15))
                        self.assertLessEqual(abs(a//4-b//4)+abs(a%4-b%4), 1)

    def test_every_scene_renders_and_moves(self):
        messages = []
        previous = qInstallMessageHandler(lambda kind, context, msg: messages.append(msg))
        try:
            for name, story in STORIES.items():
                widget = LessonAnimation(story)
                widget.resize(1100, 500)
                widget.show()
                self.app.processEvents()
                widget.timer.stop()
                for i in range(len(story.steps)):
                    with self.subTest(page=name, scene=i):
                        widget.position = (i+.15)*widget.SECONDS_PER_STEP
                        widget.render_position()
                        self.app.processEvents()
                        first = widget.canvas.grab().toImage()
                        widget.position = (i+.65)*widget.SECONDS_PER_STEP
                        widget.render_position()
                        self.app.processEvents()
                        second = widget.canvas.grab().toImage()
                        self.assertFalse(first.isNull())
                        # Sweeps that have reached a fixed point intentionally hold.
                        if story.scene != "sweep":
                            self.assertNotEqual(first, second)
                        self.assertEqual(widget.canvas.stage, i)
                        self.assertEqual(widget.caption.text(), story.steps[i].caption)
                widget.close()
                widget.deleteLater()
                self.app.processEvents()
        finally:
            qInstallMessageHandler(previous)
        errors = [m for m in messages if any(x in m for x in ("QPainter", "QPaintDevice", "Cannot", "Traceback"))]
        self.assertEqual(errors, [])

    def test_pause_replay_navigation_and_offscreen_suspend(self):
        area = QScrollArea()
        area.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        movie = LessonAnimation(STORIES["SEAPage"])
        layout.addWidget(movie)
        spacer = QWidget()
        spacer.setMinimumHeight(1600)
        layout.addWidget(spacer)
        area.setWidget(inner)
        area.resize(1150, 650)
        area.show()
        QTest.qWait(100)
        self.assertTrue(movie.timer.isActive())
        self.assertGreater(movie.position, 0)
        movie.toggle()
        position = movie.position
        QTest.qWait(80)
        self.assertEqual(movie.position, position)
        self.assertFalse(movie.timer.isActive())
        movie.step(1)
        self.assertEqual(movie.canvas.stage, 1)
        movie.step(-1)
        self.assertEqual(movie.canvas.stage, 0)
        movie.replay()
        self.assertEqual(movie.position, 0)
        self.assertTrue(movie.timer.isActive())
        area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
        self.app.processEvents()
        self.assertFalse(movie.timer.isActive())
        area.verticalScrollBar().setValue(0)
        self.app.processEvents()
        self.assertTrue(movie.timer.isActive())
        area.hide()
        self.assertFalse(movie.timer.isActive())
        area.show()
        self.app.processEvents()
        self.assertTrue(movie.timer.isActive())
        movie.toggle()
        area.hide()
        area.show()
        self.app.processEvents()
        self.assertFalse(movie.timer.isActive())
        area.close()


if __name__ == "__main__":
    unittest.main()
