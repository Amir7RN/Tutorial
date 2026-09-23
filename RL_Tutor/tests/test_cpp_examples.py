"""Check every rendered code card and compile the shared C++ examples."""
import inspect
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QPA_FONTDIR', 'C:/Windows/Fonts')

class CppExamplesTests(unittest.TestCase):
    def test_compile_and_math(self):
        compiler = shutil.which('g++')
        if not compiler:
            self.skipTest('g++ is required for C++ numerical checks')
        with tempfile.TemporaryDirectory() as directory:
            exe = str(Path(directory) / 'examples.exe')
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-I', str(ROOT),
                            str(ROOT / 'tests/cpp_examples.cpp'), '-o', exe], check=True)
            values = subprocess.check_output([exe], text=True)
        import numpy as np
        from rlcore.frozen_lake import build_model
        from rlcore.dp import value_iteration
        expected = value_iteration(build_model('classic', 'shaped'), .99)
        np.testing.assert_allclose(np.fromstring(values, sep=' '), expected[1], atol=1e-7)

    def test_all_code_pages_and_lab_entries(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFont, QFontDatabase
        from PySide6.QtCore import QCoreApplication, QEvent
        from app.pages import LESSON_CLASSES
        from app.widgets import CodePane, get_source
        from app import theme
        app = QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/consola.ttf')
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
        app.setFont(QFont('Segoe UI', 9)); app.setStyleSheet(theme.QSS)
        panes = entries = 0
        out = ROOT / '_shots/cpp'; out.mkdir(parents=True, exist_ok=True)
        for cls in LESSON_CLASSES:
            source = inspect.getsource(cls)
            if not re.search(r'\b(CodePane|_code|get_source)\(', source):
                continue
            with self.subTest(page=cls.__name__):
                page = cls(); page.resize(1250, 1000)
                for obj in getattr(page, '_registry', {}).values():
                    self.assertNotRegex(get_source(obj), r'(?m)^\s*(def |import |from \w+ import)')
                    entries += 1
                for i, pane in enumerate(page.findChildren(CodePane)):
                    text = pane.toPlainText()
                    self.assertTrue(text.startswith('// C++17'))
                    self.assertNotRegex(text, r'(?m)^\s*(def |import |from \w+ import)')
                    self.assertNotIn('np.', text)
                    self.assertGreater(len(text.splitlines()), 2)
                    if 'impedance_torque' in text or 'cached_x=x' in text:
                        pane.resize(1150, 340); pane.grab().save(str(out / f'{cls.__name__}-{i}.png'))
                    panes += 1
                print(cls.__name__, 'C++ cards checked', flush=True)
                page.close(); page.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.assertGreaterEqual(panes, 35)
        self.assertEqual(entries, 30)
        pane = CodePane('int x = 1;\nreturn x;')
        pane.mark_matching('return')
        selections = pane.extraSelections()
        self.assertEqual(selections[0].cursor.blockNumber(), 2)

if __name__ == '__main__':
    unittest.main()
