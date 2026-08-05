"""
Block diagrams, drawn on a themed matplotlib canvas.

Control theory is a subject about *where the signal goes*, and that is a
picture, not a paragraph. Pages that compare controllers draw the same
canvas twice with one arrow moved, so the difference is visible rather than
described.

    d = BlockDiagram(width=7.4, height=2.2)
    d.block(1, 1, "PID", colour=theme.ACCENT)
    d.sum(0.3, 1, signs=("+", "-"))
    d.arrow(0.5, 1, 0.9, 1, "e")
    d.feedback(3.4, 1, 0.3, 0.45, "measured θ")
    d.done()
"""

from __future__ import annotations

from .. import theme
from .plot import MplCanvas

BOX_W = 1.05
BOX_H = 0.48


class BlockDiagram(MplCanvas):
    """A matplotlib canvas with helpers for boxes, arrows and junctions."""

    def __init__(self, parent=None, width=7.4, height=2.2, xlim=(0, 8),
                 ylim=(0, 2.4)):
        super().__init__(parent, width=width, height=height, dpi=110)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self.ax.axis("off")
        self.ax.grid(False)
        self.fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)

    # ------------------------------------------------------------------
    def block(self, x, y, label, colour=None, w=BOX_W, h=BOX_H, sub=None,
              fontsize=8.5):
        """A labelled box centred on (x, y)."""
        colour = colour or theme.ACCENT
        self.ax.add_patch(_rounded(x - w / 2, y - h / 2, w, h, colour))
        self.ax.text(x, y + (0.06 if sub else 0.0), label, ha="center",
                     va="center", fontsize=fontsize, color=theme.TEXT,
                     fontweight="bold", zorder=6)
        if sub:
            self.ax.text(x, y - 0.13, sub, ha="center", va="center",
                         fontsize=6.8, color=theme.TEXT_DIM, zorder=6)
        return x + w / 2, x - w / 2

    def plant(self, x, y, label="Joint", sub="J θ̈ + b θ̇ = τ", w=1.25):
        """The physical thing being controlled -- drawn distinctly."""
        return self.block(x, y, label, colour=theme.TEXT_FAINT, w=w, sub=sub)

    # ------------------------------------------------------------------
    def sum(self, x, y, signs=("+", "-"), r=0.16):
        """A summing junction. `signs` label the incoming arrows."""
        from matplotlib.patches import Circle
        self.ax.add_patch(Circle((x, y), r, facecolor=theme.BG_RAISED,
                                 edgecolor=theme.TEXT_DIM, lw=1.2, zorder=5))
        self.ax.text(x, y, "Σ", ha="center", va="center", fontsize=9,
                     color=theme.TEXT, zorder=6)
        if len(signs) >= 1:
            self.ax.text(x - r - 0.10, y + 0.13, signs[0], ha="center",
                         fontsize=8, color=theme.TEXT_DIM)
        if len(signs) >= 2:
            self.ax.text(x - 0.13, y - r - 0.16, signs[1], ha="center",
                         fontsize=8, color=theme.TEXT_DIM)
        return x + r

    # ------------------------------------------------------------------
    def arrow(self, x0, y0, x1, y1, label=None, colour=None, dashed=False,
              above=True, fontsize=7.4):
        colour = colour or theme.TEXT_DIM
        self.ax.annotate(
            "", xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(arrowstyle="-|>", color=colour, lw=1.4,
                            linestyle="--" if dashed else "-",
                            shrinkA=0, shrinkB=0))
        if label:
            self.ax.text((x0 + x1) / 2, (y0 + y1) / 2 + (0.14 if above else -0.20),
                         label, ha="center", fontsize=fontsize, color=colour)

    def feedback(self, x_from, y_from, x_to, y_to, label=None, drop=0.55,
                 colour=None):
        """Route a signal back leftwards along a lower rail."""
        colour = colour or theme.TEXT_FAINT
        y_rail = y_from - drop
        self.ax.plot([x_from, x_from], [y_from, y_rail], color=colour, lw=1.3)
        self.ax.plot([x_from, x_to], [y_rail, y_rail], color=colour, lw=1.3)
        self.ax.annotate("", xy=(x_to, y_to), xytext=(x_to, y_rail),
                         arrowprops=dict(arrowstyle="-|>", color=colour, lw=1.3,
                                         shrinkA=0, shrinkB=0))
        if label:
            self.ax.text((x_from + x_to) / 2, y_rail - 0.17, label,
                         ha="center", fontsize=7.2, color=colour)

    def tap(self, x, y, r=0.045, colour=None):
        """A signal take-off dot."""
        self.ax.scatter([x], [y], s=18, color=colour or theme.TEXT_DIM, zorder=7)

    def note(self, x, y, text, colour=None, fontsize=7.2, ha="center"):
        self.ax.text(x, y, text, ha=ha, va="center", fontsize=fontsize,
                     color=colour or theme.TEXT_FAINT)

    def band(self, x0, x1, y0, y1, label, colour):
        """A translucent region grouping several blocks (e.g. 'inner loop')."""
        from matplotlib.patches import FancyBboxPatch
        self.ax.add_patch(FancyBboxPatch(
            (x0, y0), x1 - x0, y1 - y0,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=colour, alpha=0.09, edgecolor=colour, lw=1.0,
            linestyle="--", zorder=1))
        self.ax.text(x0 + 0.08, y1 - 0.12, label, fontsize=6.8, color=colour,
                     ha="left", va="center", fontweight="bold")

    # ------------------------------------------------------------------
    def done(self):
        self.draw_idle()
        return self


def _rounded(x, y, w, h, colour):
    from matplotlib.patches import FancyBboxPatch
    return FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.07",
        facecolor=theme.BG_RAISED, edgecolor=colour, lw=1.6, zorder=4)
