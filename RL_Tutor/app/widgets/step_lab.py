"""Interactive step-by-step labs (HTML in app/assets/steplab) embedded in a page.

A page listed in STEP_LABS shows its lab at the top in place of the
"Watch the idea" movie. Each lab is a self-contained web page: a picture you
can change, numbered steps, and the live math for the current step.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from .. import theme
from .common import Card, body

STEPLAB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "steplab")

#: page class name -> (html file, card title)
STEP_LABS = {
    # kinematics
    "PoEPage": ("poe.html", "forward kinematics, one exponential at a time"),
    "JacobianPage": ("jacobian.html", "the space Jacobian, column by column"),
    "RRPRWorkshopPage": ("workshop1.html", "what your C++ functions compute, step by step"),
    "StaticsPage": ("statics.html", "τ = Jᵀ F: from a hand force to joint torques"),
    "EigenPage": ("eigen.html", "a matrix as a machine: eigenvectors and the SVD"),
    "ManipulabilityPage": ("manipulability.html", "from J to the manipulability ellipse"),
    "IKPage": ("ik.html", "inverse kinematics: triangle, then Newton step by step"),
    "NullSpacePage": ("null_space_obstacle.html", "follow the target and dodge the obstacle with N"),
    "RRPRWorkshop2Page": ("workshop2.html", "power iteration and deflation: what eigSym3 does"),
    "ClosedChainPage": ("closed_chain.html", "a four-bar: close the loop, count the freedom"),
    # dynamics
    "LagrangePage": ("lagrange.html", "Lagrange on the 2R arm: energy in, torques out"),
    "MassMatrixPage": ("mass_matrix.html", "the mass matrix: circles, ellipses and energy"),
    "NewtonEulerPage": ("newton_euler.html", "recursive Newton–Euler, one pass at a time"),
    "InverseDynamicsPage": ("inverse_dynamics.html", "a quintic move: torque term by term"),
    "ForwardDynamicsPage": ("forward_dynamics.html", "one simulation tick, then many"),
    "TaskDynamicsPage": ("task_dynamics.html", "the mass the hand feels: Λ, μ and p"),
    "ConstrainedDynamicsPage": ("constrained.html", "a hand on a wall: the multiplier is the contact force"),
}


def lab_path(name: str) -> str:
    return os.path.join(STEPLAB_DIR, name)


class StepLab(Card):
    """Card holding one step lab in a QWebEngineView, with an open-in-browser link."""

    def __init__(self, html: str, title: str, height: int = 1000, parent=None):
        super().__init__("Step through the idea · " + title, parent)
        url = QUrl.fromLocalFile(lab_path(html))
        self.view = None
        QWebEngineView = None
        # QtWebEngine needs AA_ShareOpenGLContexts set before QApplication exists
        # (app/main.py does that). Without it, show only the browser link.
        from PySide6.QtCore import QCoreApplication
        if QCoreApplication.testAttribute(Qt.AA_ShareOpenGLContexts):
            try:
                from PySide6.QtWebEngineWidgets import QWebEngineView
            except ImportError:
                pass
        if QWebEngineView is not None:
            self.view = QWebEngineView()
            self.view.setMinimumHeight(height)
            self.view.loadFinished.connect(
                lambda ok: self.view.page().runJavaScript(
                    "document.documentElement.dataset.theme='dark'"))
            self.view.load(url)
            self.add(self.view)
        link = body(f"<a href='open' style='color:{theme.CYAN}'>Open this lab in the browser</a>"
                    + ("" if self.view else " (the embedded view needs Qt WebEngine, started from app/main.py)"))
        link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link.linkActivated.connect(lambda _: QDesktopServices.openUrl(url))
        self.add(link)
