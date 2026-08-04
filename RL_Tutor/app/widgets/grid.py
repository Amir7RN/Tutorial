"""
GridView -- the Frozen Lake board, custom-painted.

Every page that shows the lake uses this one widget. What it draws is controlled
entirely by attributes you set from outside, so a page can show values only,
arrows only, Q-triangles, a trajectory, or any combination.

Display modes:
    show_values      heat-mapped V(s) with the number printed
    show_policy      one arrow per cell (the greedy action)
    show_q           the cell split into four triangles, one per action
    show_agent       a marker at `agent_state`
    trajectory       a poly-line of the last episode
    highlight        cells to outline (e.g. states that changed this sweep)
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from rlcore.frozen_lake import (
    ACTION_ARROWS,
    GOAL,
    GRID,
    HOLES,
    N_ACTIONS,
    N_STATES,
    START,
    cell_kind,
    to_rc,
)
from .. import theme


class GridView(QWidget):
    """A 4x4 Frozen Lake board with a lot of optional overlays."""

    cellClicked = Signal(int)

    def __init__(self, parent=None, cell=78):
        super().__init__(parent)
        self._cell = cell
        self.setMinimumSize(GRID * cell + 2, GRID * cell + 2)

        # --- data -------------------------------------------------------
        self.V: list[float] | None = None
        self.Q: list[list[float]] | None = None
        self.policy: list[int] | None = None
        self.policy_probs: list[list[float]] | None = None
        self.agent_state: int | None = None
        self.trajectory: list[int] = []
        self.highlight: set[int] = set()
        self.selected: int | None = None
        self.overlay_text: dict[int, str] = {}
        self.arrow_overlay: list[tuple[int, int, float]] = []   # (s, action, prob)

        # --- switches ---------------------------------------------------
        self.show_values = True
        self.show_policy = True
        self.show_q = False
        self.show_agent = False
        self.show_indices = True
        self.value_fmt = "{:.3f}"
        self.clickable = False

        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(GRID * self._cell + 2, GRID * self._cell + 2)

    def set_cell_size(self, px: int):
        self._cell = px
        self.setMinimumSize(GRID * px + 2, GRID * px + 2)
        self.updateGeometry()
        self.update()

    def mousePressEvent(self, ev):
        if not self.clickable:
            return
        origin_x, origin_y, cell = self._layout()
        col = int((ev.position().x() - origin_x) // cell)
        row = int((ev.position().y() - origin_y) // cell)
        if 0 <= row < GRID and 0 <= col < GRID:
            s = row * GRID + col
            self.selected = s
            self.cellClicked.emit(s)
            self.update()

    # ------------------------------------------------------------------
    def _layout(self):
        """Return (origin_x, origin_y, cell_px) for a centred square board."""
        cell = min(self.width() / GRID, self.height() / GRID)
        w = cell * GRID
        return (self.width() - w) / 2.0, (self.height() - w) / 2.0, cell

    def _rect(self, s: int, ox, oy, cell) -> QRectF:
        r, c = to_rc(s)
        return QRectF(ox + c * cell, oy + r * cell, cell, cell)

    def _center(self, s: int, ox, oy, cell) -> QPointF:
        r, c = to_rc(s)
        return QPointF(ox + (c + 0.5) * cell, oy + (r + 0.5) * cell)

    # ------------------------------------------------------------------
    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ox, oy, cell = self._layout()

        # value range for the heat map
        lo = hi = 0.0
        if self.V is not None and self.show_values:
            lo, hi = min(self.V), max(self.V)

        for s in range(N_STATES):
            rect = self._rect(s, ox, oy, cell)
            kind = cell_kind(s)

            # ---- background -------------------------------------------
            if self.show_values and self.V is not None and kind not in ("hole", "goal"):
                base = theme.heat_color(self.V[s], lo, hi)
            elif kind == "hole":
                base = QColor(theme.C_HOLE)
            elif kind == "goal":
                base = QColor(theme.C_GOAL)
            elif kind == "start":
                base = QColor(theme.C_START)
            else:
                base = QColor(theme.C_FROZEN)
            p.fillRect(rect, base)

            # ---- Q triangles ------------------------------------------
            if self.show_q and self.Q is not None and kind not in ("hole", "goal"):
                self._paint_q_cell(p, rect, self.Q[s])

            # ---- border -----------------------------------------------
            p.setPen(QPen(QColor(theme.BORDER), 1))
            p.drawRect(rect)

        # ---- highlight outlines --------------------------------------
        for s in self.highlight:
            p.setPen(QPen(QColor(theme.WARN), 2.4))
            p.setBrush(Qt.NoBrush)
            p.drawRect(self._rect(s, ox, oy, cell).adjusted(1.5, 1.5, -1.5, -1.5))

        if self.selected is not None:
            p.setPen(QPen(QColor(theme.ACCENT), 2.8))
            p.setBrush(Qt.NoBrush)
            p.drawRect(self._rect(self.selected, ox, oy, cell).adjusted(2, 2, -2, -2))

        # ---- per-cell text -------------------------------------------
        for s in range(N_STATES):
            rect = self._rect(s, ox, oy, cell)
            kind = cell_kind(s)

            if self.show_indices:
                p.setPen(QColor(theme.TEXT_FAINT))
                f = QFont("Consolas", max(7, int(cell * 0.115)))
                p.setFont(f)
                p.drawText(rect.adjusted(4, 2, -4, -4),
                           Qt.AlignTop | Qt.AlignLeft, str(s))

            if kind == "hole":
                p.setPen(QColor("#ff8a8a"))
                p.setFont(QFont("Segoe UI", max(8, int(cell * 0.15)), QFont.Bold))
                p.drawText(rect, Qt.AlignCenter, "HOLE")
                continue
            if kind == "goal":
                p.setPen(QColor("#7ee787"))
                p.setFont(QFont("Segoe UI", max(8, int(cell * 0.15)), QFont.Bold))
                p.drawText(rect, Qt.AlignCenter, "GOAL")
                continue

            # policy arrow
            if self.show_policy and self.policy is not None:
                a = self.policy[s]
                p.setPen(QColor(theme.TEXT))
                p.setFont(QFont("Segoe UI", max(11, int(cell * 0.30)), QFont.Bold))
                box = rect if not self.show_values else rect.adjusted(0, -cell * 0.12, 0, -cell * 0.12)
                p.drawText(box, Qt.AlignCenter, ACTION_ARROWS[a])

            # value number
            if self.show_values and self.V is not None:
                p.setPen(QColor(theme.TEXT))
                p.setFont(QFont("Consolas", max(8, int(cell * 0.135)), QFont.Bold))
                box = rect.adjusted(0, 0, 0, -cell * 0.06)
                align = Qt.AlignBottom | Qt.AlignHCenter
                p.drawText(box, align, self.value_fmt.format(self.V[s]))

            # arbitrary overlay text (used by the transition explorer)
            if s in self.overlay_text:
                p.setPen(QColor(theme.CYAN))
                p.setFont(QFont("Consolas", max(8, int(cell * 0.14)), QFont.Bold))
                p.drawText(rect.adjusted(0, cell * 0.18, 0, 0),
                           Qt.AlignCenter, self.overlay_text[s])

            # Don't print START under the agent marker or under a transition
            # arrow/self-loop -- they overlap and both become unreadable.
            if (s == START and not self.show_values and not self.show_policy
                    and not self.show_q and not self.arrow_overlay
                    and not (self.show_agent and self.agent_state == START)):
                p.setPen(QColor(theme.ACCENT))
                p.setFont(QFont("Segoe UI", max(8, int(cell * 0.15)), QFont.Bold))
                p.drawText(rect, Qt.AlignCenter, "START")

        # ---- trajectory ----------------------------------------------
        if len(self.trajectory) > 1:
            path = QPainterPath()
            pts = [self._center(s, ox, oy, cell) for s in self.trajectory]
            path.moveTo(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)
            p.setPen(QPen(QColor(255, 209, 102, 190), 2.6,
                          Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
            p.setBrush(QBrush(QColor(theme.C_AGENT)))
            p.setPen(Qt.NoPen)
            for pt in pts:
                p.drawEllipse(pt, cell * 0.045, cell * 0.045)

        # ---- probability arrows (transition explorer) -----------------
        for (s_from, s_to, prob) in self.arrow_overlay:
            a = self._center(s_from, ox, oy, cell)
            b = self._center(s_to, ox, oy, cell)
            col = QColor(theme.CYAN)
            col.setAlphaF(0.35 + 0.65 * min(1.0, prob))
            p.setPen(QPen(col, 1.5 + 4.5 * min(1.0, prob), Qt.SolidLine,
                          Qt.RoundCap))
            if s_from == s_to:
                r = self._rect(s_from, ox, oy, cell)
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(a, cell * 0.26, cell * 0.26)
            else:
                p.drawLine(a, b)
                self._arrow_head(p, a, b, col, cell)

        # ---- agent ----------------------------------------------------
        if self.show_agent and self.agent_state is not None:
            c = self._center(self.agent_state, ox, oy, cell)
            p.setBrush(QBrush(QColor(theme.C_AGENT)))
            p.setPen(QPen(QColor("#8a6d1f"), 2))
            p.drawEllipse(c, cell * 0.19, cell * 0.19)

        p.end()

    # ------------------------------------------------------------------
    def _arrow_head(self, p: QPainter, a: QPointF, b: QPointF, col, cell):
        import math
        dx, dy = b.x() - a.x(), b.y() - a.y()
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return
        ux, uy = dx / L, dy / L
        tip = QPointF(b.x() - ux * cell * 0.20, b.y() - uy * cell * 0.20)
        size = cell * 0.10
        left = QPointF(tip.x() - ux * size + uy * size * 0.6,
                       tip.y() - uy * size - ux * size * 0.6)
        right = QPointF(tip.x() - ux * size - uy * size * 0.6,
                        tip.y() - uy * size + ux * size * 0.6)
        p.setBrush(QBrush(col))
        p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([tip, left, right]))

    def _paint_q_cell(self, p: QPainter, rect: QRectF, qrow: list[float]):
        """
        Split the square into four triangles meeting at the centre -- one per
        action, positioned where that action points. This is the standard way to
        show a Q-table on a grid: you see all four action-values at once instead
        of only the argmax.
        """
        c = rect.center()
        tl, tr = rect.topLeft(), rect.topRight()
        bl, br = rect.bottomLeft(), rect.bottomRight()

        # LEFT=0, DOWN=1, RIGHT=2, UP=3
        tris = {
            0: QPolygonF([c, tl, bl]),
            1: QPolygonF([c, bl, br]),
            2: QPolygonF([c, br, tr]),
            3: QPolygonF([c, tr, tl]),
        }
        lo, hi = min(qrow), max(qrow)
        best = max(range(N_ACTIONS), key=lambda a: qrow[a])

        span = max(abs(lo), abs(hi), 1e-9)
        for a in range(N_ACTIONS):
            col = theme.heat_color(qrow[a], -span, span)
            p.setBrush(QBrush(col))
            p.setPen(QPen(QColor(theme.BORDER_SOFT), 0.6))
            p.drawPolygon(tris[a])

        # outline the greedy action
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(theme.C_AGENT), 1.8))
        p.drawPolygon(tris[best])

        # numbers
        cell = rect.width()
        p.setFont(QFont("Consolas", max(6, int(cell * 0.095))))
        offs = {
            0: QPointF(-cell * 0.30, 0),
            1: QPointF(0, cell * 0.30),
            2: QPointF(cell * 0.30, 0),
            3: QPointF(0, -cell * 0.30),
        }
        for a in range(N_ACTIONS):
            p.setPen(QColor(theme.TEXT if a == best else theme.TEXT_DIM))
            pt = c + offs[a]
            box = QRectF(pt.x() - cell * 0.20, pt.y() - cell * 0.09,
                         cell * 0.40, cell * 0.18)
            p.drawText(box, Qt.AlignCenter, f"{qrow[a]:.2f}")
