"""
Shared pieces for the ROBOT MECHANICS block -- the dynamics, configuration
space, task space, Jacobian and null-space material that the control half of
the tutor assumed and never derived.

The block walks the twelve Modern Robotics playlists (Lynch & Park,
Northwestern) in order, one or more pages per playlist. Each page names the
playlist it belongs to in its badge, so the videos and the pages can be read
side by side.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QLabel

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, body, callout
from .motors import slider, slider_row

SEC_CSPACE = "C-Space & Rigid Motion"
SEC_KIN = "Kinematics"
SEC_DYN = "Dynamics"
SEC_PLAN = "Trajectories & Planning"
SEC_CTRL = "Robot Control"
SEC_MANIP = "Manipulation & Mobility"

PL = "https://www.youtube.com/playlist?list="
PLAYLISTS = [
    # (playlist number, chapter, title, playlist id, pages in this block)
    (1, 2, "Configuration Space", "PLggLP4f-rq01z8VLqhDC94W2nWpWpZoMj",
     "C-space, DOF, Grübler; constraints, task space and workspace"),
    (2, 3, "Rigid-Body Motions", "PLggLP4f-rq01NLHOh2vVPPJZ0rxkbVFNc",
     "SO(3), exponential coordinates; SE(3), twists, screws, wrenches"),
    (3, 4, "Forward Kinematics", "PLggLP4f-rq00oA7lrv6dS5C15RYjqj4Zi",
     "product of exponentials, space and body form, D-H"),
    (4, 5, "Velocity Kinematics and Statics", "PLggLP4f-rq01fi62ek1BoV1yiPHLL3Vt-",
     "space/body Jacobian, statics τ = JᵀF, singularities, manipulability"),
    (5, 6, "Inverse Kinematics", "PLggLP4f-rq006EwbPbqZE_UcxAUGghSfA",
     "analytic 2R, Newton–Raphson, redundancy and null space"),
    (6, 7, "Kinematics of Closed Chains", "PLggLP4f-rq02hvwNGpSWJMqjZhLpuDM-Y",
     "four-bar, Stewart platform, actuated vs passive joints"),
    (7, 8, "Dynamics of Open Chains", "PLggLP4f-rq02vX0OQQ5vrCxbJrzamYDfx",
     "Lagrange, M(q), Christoffel, Newton–Euler, forward/inverse, task space"),
    (8, 9, "Trajectory Generation", "PLggLP4f-rq00TQamz2pXjzPWpuxhVN_Vy",
     "cubic/quintic/trapezoid time scaling, time-optimal along a path"),
    (9, 10, "Motion Planning", "PLggLP4f-rq00wo1z_Or2rRPAt1pStwmlY",
     "C-space obstacles, grid A*, RRT, potential fields"),
    (10, 11, "Robot Control", "PLggLP4f-rq01Q3clJrnWFPRtpUwSlr4mG",
     "computed torque, task-space control, force and hybrid control"),
    (11, 12, "Grasping and Manipulation", "PLggLP4f-rq02N54sD6xwdDWlDScvb32Pp",
     "contact, friction cones, form and force closure"),
    (12, 13, "Wheeled Mobile Robots", "PLggLP4f-rq03J3TLUyIW0ZGfejrTjHayw",
     "omnidirectional vs nonholonomic, unicycle control, mobile manipulation"),
]


def playlist_badge(n: int) -> str:
    p = PLAYLISTS[n - 1]
    return f"playlist {p[0]} · MR ch. {p[1]}"


def watch(n: int) -> QLabel:
    """A one-line pointer to the playlist this page follows."""
    p = PLAYLISTS[n - 1]
    lb = body(f'<b>Watch alongside:</b> playlist {p[0]} — '
              f'<a style="color:{theme.CYAN}" href="{PL}{p[3]}">Modern Robotics '
              f'ch. {p[1]}, {p[2]}</a>. This page covers: {p[4]}.', dim=True)
    lb.setOpenExternalLinks(True)
    return lb


def interview(text: str):
    """The question an interviewer actually asks about this page, answered."""
    return callout(text, "warn", label="INTERVIEW QUESTION")


def start_here(text: str):
    """What question the page answers, in everyday words, before any symbols."""
    return callout(text, "key", label="START HERE — WHAT THIS PAGE IS ABOUT")


def plain(text: str):
    """The card it sits in, re-said without jargon: what the symbols mean,
    the picture to hold in your head, and what to try on the sliders."""
    return callout(text, "good", label="IN PLAIN WORDS")


def draw_arm(ax, L, q, color=None, alpha=1.0, lw=4.0, label=None, joints=True,
             ghost=False):
    pts = rk.planar_points(L, q)
    color = color or theme.CYAN
    ax.plot(pts[:, 0], pts[:, 1], "-", color=color, lw=lw if not ghost else 1.5,
            alpha=alpha if not ghost else 0.35, solid_capstyle="round", label=label)
    if joints and not ghost:
        ax.plot(pts[:-1, 0], pts[:-1, 1], "o", color=theme.WARN, ms=6, alpha=alpha)
        ax.plot(pts[-1, 0], pts[-1, 1], "o", color=theme.TEXT, ms=5, alpha=alpha)
    return pts


def square(ax, reach: float):
    ax.set_xlim(-reach, reach)
    ax.set_ylim(-reach, reach)
    ax.set_aspect("equal", adjustable="box")


def labelled_slider(card: Card, text: str, lo: int, hi: int, val: int,
                    fmt, on_change, tracking: bool = True):
    """
    Integer slider with a live readout; fmt(int) -> readout string. With
    tracking=False the readout still follows the drag but on_change only
    fires on release -- for pages that rerun a simulation on every change.
    """
    s = slider(lo, hi, val)
    lb = QLabel()
    card.add_layout(slider_row(text, s, lb))

    def upd(v=None):
        lb.setText(fmt(s.sliderPosition() if v is None else v))

    s.setTracking(tracking)
    s.sliderMoved.connect(upd)
    s.valueChanged.connect(upd)
    s.valueChanged.connect(on_change)
    upd()
    return s


def deg(v: int) -> str:
    return f"{v}°"


def mat_html(A, prec: int = 3) -> str:
    """A small matrix as a monospace HTML table."""
    A = np.atleast_2d(np.asarray(A, float))
    rows = "".join(
        "<tr>" + "".join(f"<td style='padding:1px 8px; text-align:right'>{x:+.{prec}f}</td>"
                         for x in row) + "</tr>" for row in A)
    return (f"<table style='font-family:Consolas; color:{theme.TEXT}'>"
            f"{rows}</table>")
