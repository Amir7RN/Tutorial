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
    # controller design, nonlinear, actuators
    "StabilisingPage": ("stabilising.html", "feedback relocates poles: P, D, I and the upright pendulum"),
    "LeadLagPage": ("leadlag.html", "design a lead from a spec, then lag and notch"),
    "StateFeedbackPage": ("state_feedback.html", "state feedback: choose the poles, solve for the gains"),
    "LQRPage": ("lqr.html", "LQR: weights in, optimal gains out"),
    "ObserverPage": ("observer.html", "observers: speed and load from an encoder"),
    "NonlinearSystemsPage": ("nonlinear_systems.html", "what breaks when superposition goes"),
    "NonlinearControlPage": ("nonlinear_control.html", "six ways to control a nonlinear pendulum"),
    "EffectiveInertiaPage": ("effective_inertia.html", "effective inertia: what the world feels at the joint"),
    "SEAPage": ("sea.html", "series elastic: two bodies and a frequency-dependent inertia"),
    "PEAPage": ("pea.html", "parallel elastic: a spring that carries the load"),
    "ActuatorCompare": ("actuator_compare.html", "direct drive vs SEA vs PEA on one axis"),
    "GearingPage": ("gearing.html", "gearing: torque, speed, N² and transparency"),
    "BipedActuatorsPage": ("biped_actuators.html", "size an actuator for each biped joint"),
    "ArmActuatorsPage": ("arm_actuators.html", "size the arm's three joints, distal first"),
    # real-time + systems and stability
    "RealTimePage": ("realtime.html", "one control cycle: sampling, aliasing, delay, deadline"),
    "ControlProblemPage": ("control_problem.html", "every control problem in four steps, on one joint"),
    "MeasuringPage": ("measuring.html", "identify J, b and k from four bench experiments"),
    "SoftwarePhysicsPage": ("software_physics.html", "a steel spring and a software spring"),
    "FirstOrderPage": ("first_order.html", "one store, one drain: the first-order system"),
    "TimeConstantPage": ("time_constant.html", "the time constant and the pole"),
    "IntegratorPage": ("integrator.html", "the pole at the origin: P vs PI, windup"),
    "FirstOrderFreqPage": ("first_order_freq.html", "shake it: first order in frequency"),
    "SPlanePage": ("splane.html", "the s-plane: e^(st), spirals and every motion"),
    "FreeVibrationPage": ("free_vibration.html", "free vibration from initial conditions"),
    "SecondOrderPage": ("second_order.html", "second order: energy, poles and the four metrics"),
    "StabilityPage": ("stability.html", "stability: poles, Routh and a gain sweep"),
    "BodePage": ("bode.html", "build a loop on a Bode plot and read the margins"),
    "NyquistPage": ("nyquist.html", "the Nyquist plot: one curve, one point, one count"),
    "ZerosPage": ("zeros.html", "what a zero does: the hole, the speed-up, the dip"),
    # neural networks
    "NeuronPage": ("neuron.html", "one neuron: gain, offset, saturation, then layers"),
    "ActivationPage": ("activation.html", "activations judged by their slopes"),
    "ForwardPropPage": ("forward_prop.html", "one input vector crosses the network"),
    "BackpropPage": ("backprop.html", "multiply along each path, sum across paths"),
    "LossPage": ("loss.html", "a loss is a slope generator: MSE, MAE, Huber, CE, RL"),
    "RegularisationPage": ("regularisation.html", "regularise, normalise, initialise, clip"),
    # deep RL and continuous control
    "FunctionApproxPage": ("tables_run_out.html", "tables run out: cells, generalisation, the argmax wall"),
    "ActorCriticPage": ("actor_critic.html", "actor-critic: Q not V, μ(s) versus π(a|s)"),
    "DDPGPage": ("ddpg.html", "DDPG piece by piece, then trained on a known Q"),
    "GradientHandoffPage": ("handoff.html", "∂Q/∂a: the seed of the actor's backward pass"),
    "CriticArchPage": ("critic_arch.html", "where the action enters the critic"),
    "MDPandFamilyPage": ("mdp_family.html", "Markov is about the state; four switches make DDPG"),
    "AgentSkeletonPage": ("agent_skeleton.html", "five shared objects, and where PPO breaks the mould"),
    "KneeRLPage": ("knee_rl.html", "a knee's impedance tuned by DDPG, one stride per step"),
    "DeployRLPage": ("deploy_rl.html", "a 1 kHz controller and a 20 Hz learner sharing memory"),
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

    def __init__(self, html: str, title: str, height: int = 1000, parent=None,
                 prefix: str = "Step through the idea · "):
        super().__init__(prefix + title, parent)
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
