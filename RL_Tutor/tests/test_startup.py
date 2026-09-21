"""Exercise real window startup and lazy navigation without building all lessons."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from app.main import MainWindow

class StartupTests(unittest.TestCase):
    def test_startup_navigation_and_cached_state(self):
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        self.assertTrue(all(p is None for p in window.pages))
        window.show()
        app.processEvents()
        self.assertEqual(sum(p is not None for p in window.pages), 1)
        first = window.pages[0]
        self.assertIs(window.stack.currentWidget(), first)
        sea_index = window._class_indices['SEAPage']
        window.select_page(sea_index)
        sea = window.pages[sea_index]
        self.assertIs(window.stack.currentWidget(), sea)
        original = sea.s_k.value()
        sea.s_k.setValue(original + 1)
        saved = sea.s_k.value()
        sea.navigate_requested.emit('ZerosPage')
        self.assertEqual(window._current, window._class_indices['ZerosPage'])
        window.select_page(sea_index)
        self.assertIs(window.pages[sea_index], sea)
        self.assertEqual(sea.s_k.value(), saved)
        window.next_page()
        window.prev_page()
        self.assertIs(window.stack.currentWidget(), sea)
        window.filter.setText('summary')
        window.filter.clear()
        window.select_page(1)
        self.assertTrue(window.pages[1].IS_SUMMARY)
        window.select_page(0)
        self.assertIs(window.stack.currentWidget(), first)
        self.assertLess(sum(p is not None for p in window.pages), 10)
        window.close()

if __name__ == '__main__':
    unittest.main()
