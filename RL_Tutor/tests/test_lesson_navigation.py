"""Real-widget checks for the additive SEA panels and prerequisite navigation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.name=='nt':os.environ.setdefault('QT_QPA_FONTDIR',os.path.join(os.environ.get('WINDIR','C:/Windows'),'Fonts'))
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtWidgets import QApplication,QFrame,QScrollArea
from PySide6.QtTest import QSignalSpy
from app import theme
from app.pages import CONNECTIONS,LESSON_CLASSES
from app.pages.motors import SEAPage
from app.widgets.lesson_animation import LessonAnimation
from app.widgets.lesson_connection import LessonConnection


class LessonNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        font=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/segoeui.ttf'
        if font.exists():QFontDatabase.addApplicationFont(str(font))
        cls.app.setFont(QFont('Segoe UI',9));cls.app.setStyleSheet(theme.QSS)

    def test_connection_links_emit_stable_class_target(self):
        widget=LessonConnection(CONNECTIONS['SEAPage'],LESSON_CLASSES,26)
        spy=QSignalSpy(widget.navigate)
        widget.links.linkActivated.emit('ZerosPage')
        self.assertEqual(spy.count(),1)
        self.assertEqual(spy.at(0),['ZerosPage'])
        widget.toggle.click()
        self.assertFalse(widget.definitions.isHidden())
        widget.toggle.click()
        self.assertTrue(widget.definitions.isHidden())
        widget.deleteLater()

    def test_focused_sea_movies_and_original_labs_remain(self):
        page=SEAPage();page.resize(1200,1000);page.show();self.app.processEvents()
        self.assertEqual(len(page.sea_panel_movies),3)
        self.assertEqual(len(page.findChildren(LessonAnimation)),4)
        for panel in page.findChildren(QFrame):
            if panel.objectName().startswith("Callout"):
                self.assertFalse(panel.findChildren(LessonAnimation))
        for panel,movie in page.sea_panel_movies:
            self.assertTrue(panel.isAncestorOf(movie))
            self.assertGreaterEqual(len(movie.story.steps),3)
        for name in ('canvas','canvas_bw','c_ceil','s_jm','s_jl','s_k','s_ckp','s_ckd'):
            self.assertTrue(hasattr(page,name),name)
        scroll=page.findChild(QScrollArea)
        movies=page.findChildren(LessonAnimation)
        out=Path('_shots/terminology');out.mkdir(parents=True,exist_ok=True)
        for i,movie in enumerate(movies):
            scroll.ensureWidgetVisible(movie.canvas,0,15);self.app.processEvents()
            self.assertTrue(movie.timer.isActive(),movie.story.title)
            movie.position=1.3*movie.SECONDS_PER_STEP;movie.render_position()
            if i in (0,1,2,3,8):page.grab().save(str(out/f'sea-panel-{i}.png'))
        page.hide();self.app.processEvents()
        self.assertTrue(all(not m.timer.isActive() for m in movies))
        page.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)


if __name__=='__main__':unittest.main()
