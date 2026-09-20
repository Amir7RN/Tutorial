"""Build pages in order and capture the real page around each movie.

Run: python tests/review_lesson_animations.py
Output: _shots/animations/ (ignored build artifacts).
Unlike smoke_gui.py this does not sweep expensive numerical lab sliders.
"""
import os
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"))

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QScrollArea

from app import theme
from app.pages import PAGE_CLASSES
from app.widgets.lesson_animation import LessonAnimation

parser = argparse.ArgumentParser()
parser.add_argument("--start", type=int, default=1)
parser.add_argument("--end", type=int, default=len(PAGE_CLASSES))
args = parser.parse_args()
if not 1 <= args.start <= args.end <= len(PAGE_CLASSES):
    parser.error("Choose an inclusive page range inside the registry.")

app = QApplication([])
font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf"
if font.exists():
    QFontDatabase.addApplicationFont(str(font))
app.setFont(QFont("Segoe UI", 9))
app.setStyleSheet(theme.QSS)
out = ROOT / "_shots/animations"
out.mkdir(parents=True, exist_ok=True)

for cls in PAGE_CLASSES[args.start-1:args.end]:
    page = cls()
    page.resize(1200, 1000)
    page.show()
    app.processEvents()
    movie = page.lesson_animation
    assert movie.timer.isActive(), f"{cls.NUM}: visible movie did not start"
    movie.position = 1.5 * movie.SECONDS_PER_STEP
    movie.render_position()
    app.processEvents()
    assert page.grab().save(str(out / f"{cls.NUM:02d}_{cls.__name__}.png"))
    movie.toggle()
    assert not movie.timer.isActive()
    movie.replay()
    assert movie.timer.isActive()
    scroll = page.findChild(QScrollArea)
    for index, extra in enumerate(page.findChildren(LessonAnimation)):
        scroll.ensureWidgetVisible(extra.canvas, 0, 15)
        app.processEvents()
        assert extra.timer.isActive(), f"{cls.NUM}: inline movie did not resume"
        extra.position = 1.5 * extra.SECONDS_PER_STEP
        extra.render_position()
        app.processEvents()
        if cls.NUM == 1:
            assert extra.grab().save(str(out / f"01_movie_{index:02d}.png"))
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    app.processEvents()
    if scroll.verticalScrollBar().maximum() > movie.height():
        assert not movie.timer.isActive(), f"{cls.NUM}: offscreen movie still running"
    scroll.verticalScrollBar().setValue(0)
    app.processEvents()
    assert movie.timer.isActive()
    page.on_hide()
    page.hide()
    assert not movie.timer.isActive()
    print(f"OK {cls.NUM:02d} {cls.__name__}", flush=True)
    page.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

print(f"All {args.end-args.start+1} requested pages passed. Screenshots: {out}", flush=True)
