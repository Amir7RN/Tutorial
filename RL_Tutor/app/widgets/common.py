"""Small reusable building blocks: cards, callouts, headers, math rendering."""

from __future__ import annotations

import io

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import theme


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------

def body(text: str, dim=False, wrap=True) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("Body")
    lb.setWordWrap(wrap)
    lb.setTextFormat(Qt.RichText)
    lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
    if dim:
        lb.setStyleSheet(f"color: {theme.TEXT_DIM};")
    return lb


def mono(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("Mono")
    lb.setWordWrap(True)
    lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lb


def title(text: str, size=15) -> QLabel:
    lb = QLabel(text)
    lb.setStyleSheet(
        f"color:{theme.TEXT}; font-size:{size}px; font-weight:700; "
        f"background:transparent;")
    lb.setWordWrap(True)
    return lb


# --------------------------------------------------------------------------
# Card
# --------------------------------------------------------------------------

class Card(QFrame):
    """A titled panel. `add()` anything into it."""

    def __init__(self, heading: str | None = None, parent=None, pad=14, spacing=9):
        super().__init__(parent)
        self.setObjectName("Card")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(pad, pad, pad, pad)
        self._lay.setSpacing(spacing)
        if heading:
            # Uppercase ASCII only -- str.upper() would turn 'γ' into 'Γ',
            # which is a different symbol, not a styling choice.
            h = QLabel("".join(c.upper() if c.isascii() else c for c in heading))
            h.setObjectName("CardTitle")
            self._lay.addWidget(h)

    def add(self, w):
        if isinstance(w, str):
            w = body(w)
        self._lay.addWidget(w)
        return w

    def add_layout(self, l):
        self._lay.addLayout(l)
        return l

    def add_stretch(self, n=1):
        self._lay.addStretch(n)

    @property
    def lay(self):
        return self._lay


# --------------------------------------------------------------------------
# Callout
# --------------------------------------------------------------------------

_CALLOUT_STYLE = {
    "key":  ("CalloutKey", theme.ACCENT, "KEY IDEA"),
    "warn": ("CalloutWarn", theme.WARN, "WATCH OUT"),
    "good": ("CalloutGood", theme.GOOD, "IN YOUR NOTES"),
    "bad":  ("CalloutBad", theme.BAD, "COMMON MISTAKE"),
}


def callout(text: str, kind="key", label: str | None = None) -> QFrame:
    obj, colour, default_label = _CALLOUT_STYLE[kind]
    f = QFrame()
    f.setObjectName(obj)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(5)
    tag = QLabel(label or default_label)
    tag.setStyleSheet(f"color:{colour}; font-size:10px; font-weight:800; "
                      f"letter-spacing:1px; background:transparent;")
    lay.addWidget(tag)
    lb = QLabel(text)
    lb.setWordWrap(True)
    lb.setTextFormat(Qt.RichText)
    lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lb.setStyleSheet(f"color:{theme.TEXT}; background:transparent; font-size:13px;")
    lay.addWidget(lb)
    return f


# --------------------------------------------------------------------------
# Stat chip row
# --------------------------------------------------------------------------

class Stat(QFrame):
    """A big number with a caption under it."""

    def __init__(self, caption: str, value: str = "--", colour=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{theme.BG_RAISED}; border:1px solid {theme.BORDER};"
            f"border-radius:8px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(11, 8, 11, 8)
        lay.setSpacing(1)
        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color:{colour or theme.TEXT}; font-size:19px; font-weight:800;"
            f"background:transparent; font-family:Consolas,monospace;")
        cap = QLabel(caption.upper())
        cap.setStyleSheet(f"color:{theme.TEXT_FAINT}; font-size:9px; "
                          f"font-weight:700; letter-spacing:0.9px; "
                          f"background:transparent;")
        lay.addWidget(self._val)
        lay.addWidget(cap)

    def set(self, v: str):
        self._val.setText(v)

    def set_color(self, c: str):
        self._val.setStyleSheet(
            f"color:{c}; font-size:19px; font-weight:800; background:transparent;"
            f"font-family:Consolas,monospace;")


def stat_row(*stats) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(8)
    for s in stats:
        lay.addWidget(s)
    lay.addStretch(1)
    return lay


# --------------------------------------------------------------------------
# Maths rendering (matplotlib mathtext -> QPixmap)
# --------------------------------------------------------------------------

_math_cache: dict[tuple, QPixmap] = {}


def math_label(latex: str, fontsize=15, colour=None) -> QLabel:
    r"""
    Render a LaTeX snippet to a pixmap using matplotlib's built-in mathtext
    (no TeX installation required) and wrap it in a QLabel.

    Pass the body WITHOUT the surrounding $ signs, e.g.
        math_label(r"V^\pi(s) = \sum_a \pi(a|s) Q^\pi(s,a)")
    """
    colour = colour or theme.TEXT
    key = (latex, fontsize, colour)

    if key not in _math_cache:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(0.01, 0.01), dpi=200)
        fig.patch.set_alpha(0.0)
        fig.text(0, 0, f"${latex}$", fontsize=fontsize, color=colour)
        buf = io.BytesIO()
        try:
            fig.savefig(buf, format="png", bbox_inches="tight",
                        pad_inches=0.06, transparent=True)
        except ValueError:
            # matplotlib's mathtext is a SUBSET of LaTeX -- no \begin{...}
            # environments, no \text in some versions. Rather than let a bad
            # formula kill an entire page, degrade to readable monospace.
            plt.close(fig)
            return _math_fallback(latex, colour)
        finally:
            plt.close(fig)
        buf.seek(0)
        pm = QPixmap()
        pm.loadFromData(buf.read(), "PNG")
        # rendered at dpi=200 for crispness; show at half size
        pm.setDevicePixelRatio(2.0)
        _math_cache[key] = pm

    lb = QLabel()
    lb.setPixmap(_math_cache[key])
    lb.setStyleSheet("background: transparent;")
    lb.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    return lb


def _math_fallback(latex: str, colour: str) -> QLabel:
    """Plain-text rendering for anything mathtext refuses to parse."""
    import re
    txt = latex
    for a, b in [(r"\\left", ""), (r"\\right", ""), (r"\\,", " "),
                 (r"\\;", " "), (r"\\!", ""), (r"\\quad", "   "),
                 (r"\\displaystyle", ""), (r"\\dfrac", r"\\frac")]:
        txt = re.sub(a, b, txt)
    txt = re.sub(r"\\text\{([^}]*)\}", r"\1", txt)
    txt = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)", txt)
    txt = re.sub(r"\\begin\{[a-z]*\}|\\end\{[a-z]*\}", "", txt)
    greek = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "pi": "π",
             "mu": "μ", "sigma": "σ", "theta": "θ", "epsilon": "ε",
             "varepsilon": "ε", "tau": "τ", "phi": "φ", "lambda": "λ",
             "sum": "Σ", "max": "max", "min": "min", "in": "∈",
             "mid": "|", "approx": "≈", "cdot": "·", "times": "×",
             "leftarrow": "←", "rightarrow": "→", "infty": "∞",
             "geq": "≥", "leq": "≤", "neq": "≠", "nabla": "∇",
             "mathbb{E}": "E", "arg": "arg", "sqrt": "sqrt"}
    for k, v in sorted(greek.items(), key=lambda kv: -len(kv[0])):
        txt = txt.replace("\\" + k, v)
    txt = txt.replace("\\\\", "   |   ").replace("[6pt]", "")
    txt = re.sub(r"[{}]", "", txt).replace("&", " ")
    txt = re.sub(r"\s+", " ", txt).strip()
    lb = QLabel(txt)
    lb.setWordWrap(True)
    lb.setStyleSheet(f"color:{colour}; background:transparent; font-size:14px;"
                     f"font-family:'Cascadia Mono',Consolas,monospace;")
    return lb


def math_card(heading: str, *entries) -> Card:
    """
    entries: alternating (latex, caption) tuples, or bare latex strings.
    """
    c = Card(heading)
    for e in entries:
        if isinstance(e, tuple):
            latex, caption = e
        else:
            latex, caption = e, None
        c.add(math_label(latex))
        if caption:
            lb = body(caption, dim=True)
            lb.setContentsMargins(4, 0, 0, 6)
            c.add(lb)
    return c


# --------------------------------------------------------------------------
# Misc
# --------------------------------------------------------------------------

def hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"background:{theme.BORDER_SOFT}; max-height:1px; border:none;")
    return f


def spacer(h=8) -> QWidget:
    w = QWidget()
    w.setFixedHeight(h)
    w.setStyleSheet("background: transparent;")
    return w


def labelled(text: str, widget: QWidget, width=None) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(8)
    lb = QLabel(text)
    lb.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
    if width:
        lb.setFixedWidth(width)
    lay.addWidget(lb)
    lay.addWidget(widget, 1)
    return lay


def legend(*items) -> QHBoxLayout:
    """items: (colour, text) tuples."""
    lay = QHBoxLayout()
    lay.setSpacing(14)
    for colour, text in items:
        row = QHBoxLayout()
        row.setSpacing(5)
        dot = QLabel("■")
        dot.setStyleSheet(f"color:{colour}; background:transparent; font-size:13px;")
        lb = QLabel(text)
        lb.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent; "
                         f"font-size:11px;")
        row.addWidget(dot)
        row.addWidget(lb)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(row)
        lay.addWidget(w)
    lay.addStretch(1)
    return lay
