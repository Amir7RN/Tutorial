"""Small prerequisite bridge with optional shared terminology, not another essay."""
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QPushButton

from .common import Card, body
from ..lesson_connections import VOCABULARY
from .. import theme


class LessonConnection(Card):
    navigate = Signal(str)

    def __init__(self, connection, classes, number, parent=None):
        super().__init__('Connect this lesson to what you know', parent)
        self.add(body(connection.text))
        self.links = body('Earlier lessons: ' + ' · '.join(
            f'<a style="color:{theme.CYAN}" href="{key}">{cls.NUM} · {escape(cls.TITLE)}</a>'
            for key in connection.previous
            for cls in classes if cls.__name__ == key))
        self.links.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.links.setOpenExternalLinks(False)
        self.links.linkActivated.connect(self.navigate.emit)
        if connection.previous:
            self.add(self.links)
        keys = ('Control',) if number < 25 else ('Control', 'Interaction') if number < 52 else ('Learning',) if number < 80 else ('Learning', 'Networks')
        self.definitions = body('<br><br>'.join(f'<b>{key} notation.</b> {VOCABULARY[key]}' for key in keys))
        self.toggle = QPushButton('Show terminology reminder')
        self.toggle.setCheckable(True)
        self.toggle.toggled.connect(self._toggle)
        self.add(self.toggle)
        self.add(self.definitions)
        self.definitions.hide()

    def _toggle(self, checked):
        self.definitions.setVisible(checked)
        self.toggle.setText('Hide terminology reminder' if checked else 'Show terminology reminder')
