"""
Headless GUI smoke test: instantiate every page, exercise its interactive
callbacks, and screenshot each one. Catches layout/attribute errors without a
human clicking through 20 tabs.

    python tests/smoke_gui.py [outdir]
"""

import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app import theme  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_shots")
os.makedirs(OUT, exist_ok=True)

QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
app = QApplication(sys.argv[:1])
app.setStyleSheet(theme.QSS)
app.setFont(QFont("Segoe UI", 9))

from app.pages import PAGE_CLASSES  # noqa: E402

failures = []
print(f"Smoke-testing {len(PAGE_CLASSES)} pages -> {OUT}\n")

for i, cls in enumerate(PAGE_CLASSES, start=1):
    name = cls.__name__
    try:
        page = cls()
        page.resize(1300, 1500)
        page.show()
        app.processEvents()
        page.on_show()
        app.processEvents()

        # poke every interactive control we can find
        for attr in dir(page):
            if attr.startswith("_"):
                continue
            obj = getattr(page, attr, None)
            cn = type(obj).__name__
            try:
                if cn == "QSlider":
                    lo, hi = obj.minimum(), obj.maximum()
                    for v in (lo, (lo + hi) // 2, hi):
                        obj.setValue(v)
                        app.processEvents()
                elif cn == "QComboBox":
                    for k in range(obj.count()):
                        obj.setCurrentIndex(k)
                        app.processEvents()
                elif cn == "QCheckBox":
                    obj.setChecked(not obj.isChecked())
                    app.processEvents()
                    obj.setChecked(not obj.isChecked())
                    app.processEvents()
            except Exception:
                raise

        # drive any transport a few frames
        tr = getattr(page, "transport", None)
        if tr is not None:
            for _ in range(6):
                tr.step.emit()
                app.processEvents()
            tr.pause()

        # step generators directly where pages expose them
        for meth in ("do_step", "step_once", "advance"):
            fn = getattr(page, meth, None)
            if callable(fn):
                for _ in range(4):
                    try:
                        fn()
                    except Exception:
                        raise
                    app.processEvents()
                break

        app.processEvents()
        pm = page.grab()
        path = os.path.join(OUT, f"{i:02d}_{name}.png")
        pm.save(path)
        print(f"  OK    {i:02d} {name:<28} {pm.width()}x{pm.height()}")
        page.on_hide()
        page.deleteLater()
        app.processEvents()

    except Exception as e:
        failures.append((name, traceback.format_exc()))
        print(f"  FAIL  {i:02d} {name}: {type(e).__name__}: {e}")

print()
if failures:
    for name, tb in failures:
        print("=" * 70)
        print(name)
        print(tb)
    print(f"{len(failures)} page(s) failed")
    sys.exit(1)
print(f"All {len(PAGE_CLASSES)} pages OK")
