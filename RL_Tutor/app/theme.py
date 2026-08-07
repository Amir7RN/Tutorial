"""Colour palette and Qt stylesheet for the tutor."""

from __future__ import annotations

from PySide6.QtGui import QColor

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------

BG          = "#0e1117"
BG_PANEL    = "#161b22"
BG_RAISED   = "#1c2230"
BG_INPUT    = "#0b0f16"
BORDER      = "#2a3140"
BORDER_SOFT = "#212836"

TEXT        = "#e6edf3"
TEXT_DIM    = "#9aa7b8"
TEXT_FAINT  = "#6b7788"

ACCENT      = "#4c9aff"
ACCENT_DIM  = "#2d5f9e"
GOOD        = "#3fb950"
WARN        = "#d29922"
BAD         = "#f85149"
VIOLET      = "#a371f7"
CYAN        = "#39c5cf"
PINK        = "#f778ba"
ORANGE      = "#f0883e"
TEAL        = "#2dd4bf"
INDIGO      = "#8b8cf7"

# Grid cell colours
C_FROZEN    = "#1d2733"
C_HOLE      = "#3d1620"
C_GOAL      = "#14361f"
C_START     = "#1a2a3d"
C_AGENT     = "#ffd166"

# Value heat-map endpoints (negative -> zero -> positive)
HEAT_NEG    = QColor("#7d1128")
HEAT_ZERO   = QColor("#1d2733")
HEAT_POS    = QColor("#1f7a4d")

# Per-page accent used by the sidebar
SECTION_COLORS = {
    # control & dynamics
    "Real-Time":         BAD,
    "Systems & Stability": ORANGE,
    "Controller Design": TEAL,
    "Nonlinear":         INDIGO,
    "Actuators":         CYAN,
    "Control Paradigms": ACCENT,
    "Robot Design":      GOOD,
    "Proprioception":    VIOLET,
    "Force Feedback":    WARN,
    "Bio → Robot":       PINK,
    # reinforcement learning
    "Start Here":      ACCENT,
    "Value Functions": VIOLET,
    "Dynamic Prog.":   GOOD,
    "Monte Carlo":     WARN,
    "Beyond":          PINK,
}


def heat_color(v: float, lo: float, hi: float) -> QColor:
    """Map a value onto the heat map. Zero always lands on HEAT_ZERO."""
    if hi - lo < 1e-12:
        return QColor(HEAT_ZERO)
    if v >= 0:
        t = 0.0 if hi <= 0 else max(0.0, min(1.0, v / hi))
        a, b = HEAT_ZERO, HEAT_POS
    else:
        t = 0.0 if lo >= 0 else max(0.0, min(1.0, v / lo))
        a, b = HEAT_ZERO, HEAT_NEG
    return QColor(
        int(a.red()   + (b.red()   - a.red())   * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue()  + (b.blue()  - a.blue())  * t),
    )


# --------------------------------------------------------------------------
# Stylesheet
# --------------------------------------------------------------------------

QSS = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG}; border: none; }}

/* ---------- sidebar ---------- */
#Sidebar {{ background: {BG_PANEL}; border-right: 1px solid {BORDER}; }}
#SidebarTitle {{
    font-size: 17px; font-weight: 700; color: {TEXT};
    padding: 16px 14px 2px 16px; background: transparent;
}}
#SidebarSub {{
    font-size: 11px; color: {TEXT_FAINT};
    padding: 0 16px 12px 16px; background: transparent;
}}
#SectionLabel {{
    font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
    color: {TEXT_FAINT}; padding: 14px 16px 4px 16px;
    background: transparent; text-transform: uppercase;
}}
QListWidget {{
    background: transparent; border: none; outline: none;
    padding: 0 8px;
}}
QListWidget::item {{
    padding: 7px 10px; border-radius: 6px; color: {TEXT_DIM};
    margin: 1px 0;
}}
QListWidget::item:hover {{ background: {BG_RAISED}; color: {TEXT}; }}
QListWidget::item:selected {{
    background: {ACCENT_DIM}; color: #ffffff; font-weight: 600;
}}

/* ---------- sidebar tree (collapsible sections) ---------- */
QTreeWidget {{
    background: transparent; border: none; outline: none;
    padding: 0 6px; show-decoration-selected: 1;
}}
QTreeWidget::item {{
    padding: 5px 6px; border-radius: 6px; color: {TEXT_DIM};
    margin: 1px 0;
}}
QTreeWidget::item:hover {{ background: {BG_RAISED}; color: {TEXT}; }}
QTreeWidget::item:selected {{
    background: {ACCENT_DIM}; color: #ffffff; font-weight: 600;
}}
QTreeWidget::branch {{ background: transparent; }}
QTreeWidget::branch:has-children:closed {{
    image: none; border-image: none;
}}
QTreeWidget::branch:has-children:open {{
    image: none; border-image: none;
}}
#NavFilter {{
    background: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: 6px;
    padding: 5px 9px; margin: 0 14px 8px 14px; color: {TEXT};
    font-size: 12px;
}}
#NavFilter:focus {{ border-color: {ACCENT_DIM}; }}

/* ---------- cards ---------- */
#Card {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
/* no text-transform here: Card uppercases ASCII in Python so Greek survives */
#CardTitle {{
    font-size: 12px; font-weight: 700; letter-spacing: 0.8px;
    color: {TEXT_DIM}; background: transparent;
}}
#PageTitle {{
    font-size: 26px; font-weight: 800; color: {TEXT}; background: transparent;
}}
#PageSub {{
    font-size: 13px; color: {TEXT_DIM}; background: transparent;
}}
#PageBadge {{
    font-size: 10px; font-weight: 700; letter-spacing: 1px;
    color: {BG}; background: {ACCENT}; border-radius: 4px;
    padding: 3px 8px;
}}
#Body {{ background: transparent; color: {TEXT}; font-size: 13px; }}
#Mono {{
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px; background: transparent;
}}

/* ---------- callouts ---------- */
#CalloutKey  {{ background: rgba(76,154,255,0.10); border: 1px solid {ACCENT_DIM};
                border-radius: 8px; }}
#CalloutWarn {{ background: rgba(210,153,34,0.10); border: 1px solid #6b4e13;
                border-radius: 8px; }}
#CalloutGood {{ background: rgba(63,185,80,0.10);  border: 1px solid #1f5c2b;
                border-radius: 8px; }}
#CalloutBad  {{ background: rgba(248,81,73,0.10);  border: 1px solid #6e2422;
                border-radius: 8px; }}

/* ---------- controls ---------- */
QPushButton {{
    background: {BG_RAISED}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 6px;
    padding: 6px 14px; font-weight: 600;
}}
QPushButton:hover  {{ background: #262e3d; border-color: {ACCENT_DIM}; }}
QPushButton:pressed{{ background: {ACCENT_DIM}; }}
QPushButton:disabled {{ color: {TEXT_FAINT}; background: {BG_PANEL}; }}
QPushButton#Primary {{
    background: {ACCENT_DIM}; border-color: {ACCENT}; color: #ffffff;
}}
QPushButton#Primary:hover {{ background: {ACCENT}; }}

QComboBox {{
    background: {BG_INPUT}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 5px 10px; min-height: 20px;
}}
QComboBox:hover {{ border-color: {ACCENT_DIM}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {BG_RAISED}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM}; outline: none;
}}

QSlider::groove:horizontal {{
    height: 4px; background: {BORDER}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT}; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}}
QSlider::sub-page:horizontal {{ background: {ACCENT_DIM}; border-radius: 2px; }}

QCheckBox, QRadioButton {{ background: transparent; spacing: 7px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px; height: 15px;
    border: 1px solid {BORDER}; background: {BG_INPUT}; border-radius: 3px;
}}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {ACCENT}; border-color: {ACCENT};
}}

QSpinBox, QDoubleSpinBox {{
    background: {BG_INPUT}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 4px 8px;
}}

QTextEdit, QPlainTextEdit {{
    background: {BG_INPUT}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 8px;
    font-family: "Cascadia Mono", "Consolas", monospace; font-size: 12px;
    selection-background-color: {ACCENT_DIM};
}}

QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 8px; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {TEXT_DIM};
    padding: 7px 14px; border: 1px solid transparent;
    border-top-left-radius: 7px; border-top-right-radius: 7px;
}}
QTabBar::tab:selected {{
    background: {BG_PANEL}; color: {TEXT};
    border-color: {BORDER}; border-bottom-color: {BG_PANEL};
}}
QTabBar::tab:hover:!selected {{ color: {TEXT}; }}

QTableWidget {{
    background: {BG_INPUT}; gridline-color: {BORDER_SOFT};
    border: 1px solid {BORDER}; border-radius: 8px;
    selection-background-color: {ACCENT_DIM};
}}
QHeaderView::section {{
    background: {BG_RAISED}; color: {TEXT_DIM};
    border: none; border-right: 1px solid {BORDER_SOFT};
    border-bottom: 1px solid {BORDER_SOFT}; padding: 5px 8px;
    font-weight: 600; font-size: 11px;
}}
QTableCornerButton::section {{ background: {BG_RAISED}; border: none; }}

QScrollBar:vertical   {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle {{ background: #333c4d; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:hover {{ background: #47536a; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QProgressBar {{
    background: {BG_INPUT}; border: 1px solid {BORDER};
    border-radius: 6px; text-align: center; height: 16px; font-size: 11px;
}}
QProgressBar::chunk {{ background: {ACCENT_DIM}; border-radius: 5px; }}

QSplitter::handle {{ background: {BORDER_SOFT}; }}
QToolTip {{
    background: {BG_RAISED}; color: {TEXT};
    border: 1px solid {BORDER}; padding: 5px;
}}
"""
