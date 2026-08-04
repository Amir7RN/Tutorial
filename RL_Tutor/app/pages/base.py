"""Page scaffolding shared by all tutor pages."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from rlcore.frozen_lake import REWARD_SCHEMES, SLIP_MODELS
from .. import theme
from ..widgets import Card, body


class Page(QWidget):
    """
    Base class. Subclasses fill `self.content` (a vertical layout inside a
    scroll area) and optionally override `on_show()` / `on_hide()`.
    """

    #: shown in the sidebar
    TITLE = "Untitled"
    SUBTITLE = ""
    SECTION = "Start Here"
    #: which handwritten page this maps to
    NOTES = ""
    #: 1-based position, stamped by app/pages/__init__.py from PAGE_CLASSES
    NUM = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        inner = QWidget()
        self.content = QVBoxLayout(inner)
        self.content.setContentsMargins(26, 22, 26, 30)
        self.content.setSpacing(14)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        self._build_header()

    # ------------------------------------------------------------------
    def _build_header(self):
        head = QWidget()
        head.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(head)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(10)
        t = QLabel(f"{self.NUM} · {self.TITLE}" if self.NUM else self.TITLE)
        t.setObjectName("PageTitle")
        top.addWidget(t)
        if self.NOTES:
            b = QLabel(self.NOTES)
            b.setObjectName("PageBadge")
            b.setAlignment(Qt.AlignCenter)
            b.setFixedHeight(20)
            top.addWidget(b, 0, Qt.AlignVCenter)
        top.addStretch(1)
        lay.addLayout(top)

        if self.SUBTITLE:
            s = QLabel(self.SUBTITLE)
            s.setObjectName("PageSub")
            s.setWordWrap(True)
            lay.addWidget(s)

        self.content.addWidget(head)

    # ------------------------------------------------------------------
    def add(self, w):
        if isinstance(w, str):
            w = body(w)
        self.content.addWidget(w)
        return w

    def add_layout(self, l):
        self.content.addLayout(l)
        return l

    def row(self, *widgets, stretches=None, spacing=14):
        """Horizontal row of widgets added to the page."""
        lay = QHBoxLayout()
        lay.setSpacing(spacing)
        for i, w in enumerate(widgets):
            st = stretches[i] if stretches else 0
            lay.addWidget(w, st)
        self.content.addLayout(lay)
        return lay

    def finish(self):
        self.content.addStretch(1)

    # ------------------------------------------------------------------
    def on_show(self):
        pass

    def on_hide(self):
        pass


# --------------------------------------------------------------------------
# Environment selector -- reused on nearly every page
# --------------------------------------------------------------------------

class EnvControls(Card):
    """Slip model + reward scheme + gamma. Emits `changed` on any edit."""

    changed = Signal()

    def __init__(self, parent=None, show_gamma=True, slip="gym", reward="gym",
                 gamma=0.99, heading="environment"):
        super().__init__(heading, parent)
        self._show_gamma = show_gamma

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnStretch(1, 1)

        def lbl(t):
            q = QLabel(t)
            q.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
            return q

        self.slip = QComboBox()
        for key, m in SLIP_MODELS.items():
            self.slip.addItem(m.name, key)
        self.slip.setCurrentIndex(list(SLIP_MODELS).index(slip))
        grid.addWidget(lbl("Slip model"), 0, 0)
        grid.addWidget(self.slip, 0, 1)

        self.reward = QComboBox()
        for key, r in REWARD_SCHEMES.items():
            self.reward.addItem(r.name, key)
        self.reward.setCurrentIndex(list(REWARD_SCHEMES).index(reward))
        grid.addWidget(lbl("Reward"), 1, 0)
        grid.addWidget(self.reward, 1, 1)

        if show_gamma:
            self.gamma = QSlider(Qt.Horizontal)
            self.gamma.setRange(0, 100)
            self.gamma.setValue(int(round(gamma * 100)))
            self.gamma_lbl = QLabel(f"{gamma:.2f}")
            self.gamma_lbl.setStyleSheet(
                f"color:{theme.ACCENT}; font-family:Consolas; font-weight:700;"
                f"background:transparent; min-width:34px;")
            gl = QHBoxLayout()
            gl.addWidget(self.gamma, 1)
            gl.addWidget(self.gamma_lbl)
            grid.addWidget(lbl("Discount γ"), 2, 0)
            grid.addLayout(gl, 2, 1)
            self.gamma.valueChanged.connect(self._gamma_changed)

        self.add_layout(grid)

        self._blurb = body("", dim=True)
        self._blurb.setStyleSheet(f"color:{theme.TEXT_FAINT}; font-size:11px;")
        self.add(self._blurb)

        self.slip.currentIndexChanged.connect(self._emit)
        self.reward.currentIndexChanged.connect(self._emit)
        self._update_blurb()

    def _gamma_changed(self):
        self.gamma_lbl.setText(f"{self.gamma_value():.2f}")
        self.changed.emit()

    def _emit(self):
        self._update_blurb()
        self.changed.emit()

    def _update_blurb(self):
        s = SLIP_MODELS[self.slip_key()]
        r = REWARD_SCHEMES[self.reward_key()]
        self._blurb.setText(f"<b>{s.name}</b> &mdash; {s.blurb}<br><br>"
                            f"<b>{r.name}</b> &mdash; {r.blurb}")

    # -- accessors -----------------------------------------------------
    def slip_key(self) -> str:
        return self.slip.currentData()

    def reward_key(self) -> str:
        return self.reward.currentData()

    def gamma_value(self) -> float:
        if not self._show_gamma:
            return 0.99
        # keep gamma strictly < 1 unless the user pins it to 1.00 exactly
        return self.gamma.value() / 100.0

    def build(self):
        from rlcore.frozen_lake import build_model
        return build_model(self.slip_key(), self.reward_key())

    def make_env(self, seed=None):
        from rlcore.frozen_lake import FrozenLake
        return FrozenLake(slip=self.slip_key(), reward=self.reward_key(), seed=seed)


# --------------------------------------------------------------------------
# Transport controls (play / step / reset / speed)
# --------------------------------------------------------------------------

class Transport(QWidget):
    """Play-pause-step-reset bar driving a QTimer."""

    step = Signal()
    reset = Signal()

    def __init__(self, parent=None, interval=280, show_speed=True):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.btn_play = QPushButton("Play")
        self.btn_play.setObjectName("Primary")
        self.btn_step = QPushButton("Step")
        self.btn_reset = QPushButton("Reset")
        lay.addWidget(self.btn_play)
        lay.addWidget(self.btn_step)
        lay.addWidget(self.btn_reset)

        if show_speed:
            sp = QLabel("Speed")
            sp.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
            lay.addWidget(sp)
            self.speed = QSlider(Qt.Horizontal)
            self.speed.setRange(1, 100)
            self.speed.setValue(55)
            self.speed.setFixedWidth(110)
            self.speed.valueChanged.connect(self._speed_changed)
            lay.addWidget(self.speed)
        else:
            self.speed = None

        lay.addStretch(1)

        self.timer = QTimer(self)
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.step.emit)

        self.btn_play.clicked.connect(self.toggle)
        self.btn_step.clicked.connect(self._manual_step)
        self.btn_reset.clicked.connect(self._do_reset)

    def _speed_changed(self):
        # 1 -> 800 ms, 100 -> 8 ms, log-ish
        v = self.speed.value()
        self.timer.setInterval(int(800 * (0.0105 ** (v / 100.0))))

    def _manual_step(self):
        self.pause()
        self.step.emit()

    def _do_reset(self):
        self.pause()
        self.reset.emit()

    def toggle(self):
        if self.timer.isActive():
            self.pause()
        else:
            self.play()

    def play(self):
        self.timer.start()
        self.btn_play.setText("Pause")

    def pause(self):
        self.timer.stop()
        self.btn_play.setText("Play")

    def is_playing(self) -> bool:
        return self.timer.isActive()
