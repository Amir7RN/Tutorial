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

# matplotlib's mathtext is a SUBSET of LaTeX. A pile of perfectly ordinary
# commands are simply absent from it, and when one appears mathtext throws and
# the WHOLE formula falls through to the plain-text path -- which is how a page
# ends up printing "1-\tfrac{s}{z}" instead of drawing the fraction. So rewrite
# every one of them into a spelling mathtext does know, BEFORE handing it over.
#
# Straight synonyms: same meaning, different name, nothing is lost.
_MATHTEXT_ALIASES = [
    (r"\\tfrac(?![A-Za-z])", r"\\frac"),     # no textstyle fraction macro
    (r"\\dfrac(?![A-Za-z])", r"\\frac"),     # no displaystyle fraction either
    (r"\\nicefrac(?![A-Za-z])", r"\\frac"),
    (r"\\displaystyle(?![A-Za-z])", ""),
    (r"\\textstyle(?![A-Za-z])", ""),
    (r"\\scriptstyle(?![A-Za-z])", ""),
    (r"\\limits(?![A-Za-z])", ""),
    (r"\\nolimits(?![A-Za-z])", ""),
    (r"\\le(?![A-Za-z])", r"\\leq"),
    (r"\\ge(?![A-Za-z])", r"\\geq"),
    (r"\\ne(?![A-Za-z])", r"\\neq"),
    (r"\\iff(?![A-Za-z])", r"\\Leftrightarrow"),
    (r"\\implies(?![A-Za-z])", r"\\Rightarrow"),
    (r"\\impliedby(?![A-Za-z])", r"\\Leftarrow"),
    (r"\\lVert(?![A-Za-z])", r"\\|"),
    (r"\\rVert(?![A-Za-z])", r"\\|"),
    (r"\\lvert(?![A-Za-z])", r"|"),
    (r"\\rvert(?![A-Za-z])", r"|"),
    (r"\\textbf(?![A-Za-z])", r"\\mathbf"),
    (r"\\textit(?![A-Za-z])", r"\\mathit"),
    (r"\\textrm(?![A-Za-z])", r"\\mathrm"),
    (r"\\texttt(?![A-Za-z])", r"\\mathtt"),
    (r"\\mathsf(?![A-Za-z])", r"\\mathrm"),
    # sizing delimiters: mathtext sizes them itself, so the hint just goes
    (r"\\[Bb]igg?[lrm]?(?![A-Za-z])", ""),
    (r"\\(?:mathrel|mathbin|mathord|mathopen|mathclose)(?![A-Za-z])", ""),
    (r"\\boxed(?![A-Za-z])", ""),            # no frame; contents survive
    (r"\\mbox(?![A-Za-z])", r"\\mathrm"),
    (r"\\\[[0-9.]+(?:pt|ex|em)\]", ""),      # row spacing after a \\ break
]

# environment -> the delimiter pair it draws around its rows
_MATH_ENVS = {
    "bmatrix":  (r"\left[", r"\right]"),
    "pmatrix":  (r"\left(", r"\right)"),
    "vmatrix":  (r"\left|", r"\right|"),
    "Vmatrix":  (r"\left\|", r"\right\|"),
    "Bmatrix":  (r"\left\{", r"\right\}"),
    "matrix":   (r"\left.", r"\right."),
    "array":    (r"\left.", r"\right."),
    "cases":    (r"\left\{", r"\right."),
    "aligned":  (r"\left.", r"\right."),
    "align":    (r"\left.", r"\right."),
    "gathered": (r"\left.", r"\right."),
}


def _brace_arg(s: str, i: int):
    """Read a balanced {...} starting at s[i]; return (body, index after it)."""
    if i >= len(s) or s[i] != "{":
        return None, i
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return None, i                      # unbalanced: leave it alone


def _stack(rows: list[str]) -> str:
    r"""
    Stack rows vertically. mathtext has no \begin{...} environments at all,
    but it does have \genfrac -- a fraction whose rule thickness we can set to
    zero, which is exactly a two-row stack. Nest it for more rows.
    """
    rows = [r.strip() or r"\;" for r in rows]
    if len(rows) == 1:
        return rows[0]
    return r"\genfrac{}{}{0}{0}{%s}{%s}" % (rows[0], _stack(rows[1:]))


def _expand_envs(s: str) -> str:
    r"""Turn \begin{bmatrix}a & b \\ c & d\end{bmatrix} into a genfrac stack."""
    import re
    pat = re.compile(r"\\begin\{(" + "|".join(_MATH_ENVS) + r")\*?\}"
                     r"(.*?)"
                     r"\\end\{\1\*?\}", re.S)
    prev = None
    while prev != s:                    # repeat: environments can nest
        prev = s

        def repl(m):
            lo, hi = _MATH_ENVS[m.group(1)]
            rows = re.split(r"\\\\", m.group(2))
            # a row break may carry a spacing hint, \\[2pt]; drop it
            rows = [re.sub(r"^\s*\[[0-9.]+(?:pt|ex|em)\]", "", r) for r in rows]
            # columns are only separated visually -- mathtext cannot align them
            rows = [r"\;\;".join(c.strip() for c in r.split("&")) for r in rows]
            return lo + _stack(rows) + hi

        s = pat.sub(repl, s)
    return s


def _expand_braces(s: str) -> str:
    r"""
    \underbrace{X}_{Y} -> \underset{Y}{\underline{X}}, and the over- twin.
    Not a curly brace, but it keeps the annotation, which is the whole point
    of writing an underbrace on a teaching page.
    """
    for cmd, under in ((r"\underbrace", True), (r"\overbrace", False)):
        while True:
            i = s.find(cmd)
            if i < 0:
                break
            body, j = _brace_arg(s, i + len(cmd))
            if body is None:
                s = s[:i] + s[i + len(cmd):]      # malformed: drop the command
                continue
            mark = "_" if under else "^"
            label = None
            if j < len(s) and s[j] == mark:
                label, j = _brace_arg(s, j + 1)
                if label is None:                 # e.g. \underbrace{X}_y
                    label, j = s[j + 1], j + 2
            rule = r"\underline" if under else r"\overline"
            inner = r"%s{%s}" % (rule, _expand_braces(body))
            if label:
                setter = r"\underset" if under else r"\overset"
                inner = r"%s{%s}{%s}" % (setter, _expand_braces(label), inner)
            s = s[:i] + inner + s[j:]
    return s


def _brace_bare_args(s: str, cmd: str, nargs: int) -> str:
    r"""
    \sqrt\alpha and \tfrac12 are legal LaTeX shorthand -- a single token is an
    argument whether or not it wears braces. mathtext insists on the braces,
    so put them on.
    """
    import re
    out, i = [], 0
    while True:
        j = s.find(cmd, i)
        if j < 0:
            out.append(s[i:])
            return "".join(out)
        # not a prefix of a longer command name (\frac must not match \fracture)
        k = j + len(cmd)
        if k < len(s) and s[k].isalpha():
            out.append(s[i:k])
            i = k
            continue
        out.append(s[i:k])
        for _ in range(nargs):
            while k < len(s) and s[k] == " ":
                k += 1
            if k >= len(s):
                break
            if s[k] == "{":                      # already braced: step over it
                _, k2 = _brace_arg(s, k)
                if k2 == k:                      # unbalanced; give up here
                    break
                out.append(s[k:k2])
                k = k2
                continue
            m = re.match(r"\\[A-Za-z]+|.", s[k:])
            out.append("{" + m.group(0) + "}")
            k += m.end()
        i = k


def _sanitise_mathtext(latex: str) -> str:
    r"""Rewrite full-LaTeX spellings into mathtext-compatible ones."""
    import re
    out = _expand_envs(latex)
    out = _expand_braces(out)
    for pat, rep in _MATHTEXT_ALIASES:
        out = re.sub(pat, rep, out)
    out = _brace_bare_args(out, r"\sqrt", 1)
    out = _brace_bare_args(out, r"\frac", 2)
    out = _brace_bare_args(out, r"\binom", 2)
    return out


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
        fig.text(0, 0, f"${_sanitise_mathtext(latex)}$",
                 fontsize=fontsize, color=colour)
        buf = io.BytesIO()
        try:
            fig.savefig(buf, format="png", bbox_inches="tight",
                        pad_inches=0.06, transparent=True)
        except Exception:
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
                 (r"\\;", " "), (r"\\:", " "), (r"\\!", ""),
                 (r"\\qquad", "    "), (r"\\quad", "   "),
                 (r"\\displaystyle", ""), (r"\\textstyle", ""),
                 (r"\\limits", ""),
                 (r"\\dfrac", r"\\frac"), (r"\\tfrac", r"\\frac")]:
        txt = re.sub(a, b, txt)
    txt = re.sub(r"\\(?:text|mathrm|mathbf|mathit|operatorname)\{([^}]*)\}",
                 r"\1", txt)
    txt = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)", txt)
    txt = re.sub(r"\\sqrt\{([^}]*)\}", r"√(\1)", txt)
    txt = re.sub(r"\\begin\{[a-z]*\}|\\end\{[a-z]*\}", "", txt)
    greek = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "pi": "π",
             "mu": "μ", "sigma": "σ", "theta": "θ", "epsilon": "ε",
             "varepsilon": "ε", "tau": "τ", "phi": "φ", "varphi": "φ",
             "lambda": "λ", "omega": "ω", "Omega": "Ω", "zeta": "ζ",
             "eta": "η", "rho": "ρ", "psi": "ψ", "xi": "ξ", "kappa": "κ",
             "Delta": "Δ", "Sigma": "Σ", "Phi": "Φ", "Lambda": "Λ",
             "sum": "Σ", "prod": "Π", "int": "∫", "partial": "∂",
             "max": "max", "min": "min", "in": "∈", "forall": "∀",
             "mid": "|", "approx": "≈", "cdot": "·", "times": "×",
             "pm": "±", "mp": "∓", "propto": "∝", "sim": "~",
             "Longleftrightarrow": "⟺", "longleftrightarrow": "⟷",
             "Leftrightarrow": "⟺", "leftrightarrow": "↔",
             "Longrightarrow": "⟹", "longrightarrow": "⟶",
             "Longleftarrow": "⟸", "longleftarrow": "⟵",
             "Rightarrow": "⟹", "Leftarrow": "⟸",
             "leftarrow": "←", "rightarrow": "→", "to": "→",
             "infty": "∞", "ll": "≪", "gg": "≫",
             "geq": "≥", "leq": "≤", "ge": "≥", "le": "≤",
             "neq": "≠", "nabla": "∇", "angle": "∠", "deg": "°",
             "mathbb{E}": "E", "arg": "arg", "sqrt": "√"}
    for k, v in sorted(greek.items(), key=lambda kv: -len(kv[0])):
        txt = txt.replace("\\" + k, v)
    txt = txt.replace("\\\\", "   |   ").replace("[6pt]", "")
    # anything still carrying a backslash is a command this table has no
    # spelling for -- show the NAME, never the backslash, so the reader sees
    # "beta" rather than "\beta".
    txt = re.sub(r"\\([A-Za-z]+)", r"\1", txt)
    txt = txt.replace("\\", "")
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
