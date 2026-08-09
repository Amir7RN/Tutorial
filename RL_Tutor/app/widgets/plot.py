"""Matplotlib canvas wired into the dark theme."""

from __future__ import annotations

import matplotlib

matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from .. import theme  # noqa: E402


class MplCanvas(FigureCanvasQTAgg):
    """A themed figure. Call `.ax` for a single-axes figure."""

    def __init__(self, parent=None, width=5.0, height=3.0, dpi=110, nrows=1, ncols=1):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor(theme.BG_PANEL)
        super().__init__(self.fig)
        self.setParent(parent)
        if nrows == 1 and ncols == 1:
            self.ax = self.fig.add_subplot(111)
            self.axes = [self.ax]
            self.style(self.ax)
        else:
            self.axes = self.fig.subplots(nrows, ncols).ravel().tolist()
            for a in self.axes:
                self.style(a)
            self.ax = self.axes[0]
        self.fig.tight_layout()
        self.setStyleSheet(f"background:{theme.BG_PANEL};")

    @staticmethod
    def style(ax):
        ax.set_facecolor(theme.BG_INPUT)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("left", "bottom"):
            ax.spines[spine].set_color(theme.BORDER)
        ax.tick_params(colors=theme.TEXT_DIM, labelsize=8, length=3)
        ax.xaxis.label.set_color(theme.TEXT_DIM)
        ax.yaxis.label.set_color(theme.TEXT_DIM)
        ax.xaxis.label.set_fontsize(9)
        ax.yaxis.label.set_fontsize(9)
        ax.title.set_color(theme.TEXT)
        ax.title.set_fontsize(10)
        ax.grid(True, color=theme.BORDER_SOFT, linewidth=0.6, alpha=0.7)
        ax.set_axisbelow(True)

    def legend(self, ax=None, **kw):
        ax = ax or self.ax
        leg = ax.legend(facecolor=theme.BG_RAISED, edgecolor=theme.BORDER,
                        labelcolor=theme.TEXT, fontsize=8, framealpha=0.95, **kw)
        return leg

    def refresh(self, layout=True):
        """
        Redraw. `layout=False` skips tight_layout, which is the expensive part
        (roughly 60% of a redraw) and is only needed when the set of artists
        or the tick labels have actually changed. Animated widgets rebuild
        their axes once with layout=True and then push new data every frame
        with layout=False.
        """
        if layout:
            try:
                self.fig.tight_layout()
            except Exception:
                pass
        self.draw_idle()

    def clear(self):
        for a in self.axes:
            a.clear()
            self.style(a)
