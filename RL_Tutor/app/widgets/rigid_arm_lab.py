"""Interactive spatial examples for the chapter 2–3 lessons only."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QSlider

from ctrlcore import robokin as rk
from .. import theme
from .common import Card, body
from .plot import MplCanvas

LAB_PAGES = (
    'RoboRoadmapPage', 'CSpacePage', 'CSpaceTopoPage', 'ConstraintsPage',
    'RotationsPage', 'AngularVelocityPage', 'ExpCoordsPage', 'TwistsPage',
)

# One physical example carries all eight lessons. These are modelling choices,
# not a claim that this four-joint teaching arm reproduces human anatomy.
LESSONS = (
    ('114 · From joint settings to the hand',
     'Move a shoulder or elbow slider. The joint list q determines every link, '
     'then the hand position p and orientation R. The gold curve is the hand path '
     'when only the elbow moves. Predict that curve before moving the elbow.',
     'Follow shoulder → elbow → wrist → hand. Kinematics answers where; later '
     'sections use velocities and loads to answer how fast and how hard.'),
    ('115 · Count configuration freedoms',
     'This teaching arm has shoulder yaw, shoulder elevation, elbow flexion and '
     'wrist roll: four independent coordinates. Change one at a time. Wrist roll '
     'changes the hand frame without moving its centre.',
     'Four joints do not mean an arbitrary six-dimensional hand pose is reachable. '
     'For this spatial open chain, N = 5, J = 4: 6(5 − 1 − 4) + 4 = 4 DOF.'),
    ('116 · A configuration is a point on a space',
     'The right-hand torus shows two ideal, unlimited revolute joints: shoulder '
     'yaw and wrist roll. Cross ±180° using the yaw slider: the marker stays '
     'continuous although the principal-angle readout wraps.',
     'This torus is a two-joint slice, not the whole four-dimensional C-space. '
     'The teaching elbow and elevation have limits (intervals). Actual human '
     'joints also have limits; the unlimited angles here are an idealisation.'),
    ('117 · Constrain the hand to a tabletop',
     'Enable the tabletop constraint. Elbow motion now forces shoulder elevation '
     'to change so the hand stays at z = 1 m. The translucent plane is a '
     'holonomic position constraint g(q) = hand height − 1 = 0.',
     'A position rule removes one independent coordinate here: four become '
     'three. A wheeled base has a different rule (no sideways velocity); that '
     'nonholonomic example remains in the lesson above. The table is a geometric '
     'constraint, not a simulated contact force.'),
    ('118 · See the columns of a rotation matrix',
     'Red, green and blue arrows are the hand’s local x, y and z axes in world '
     'coordinates. Rotate the wrist: its centre stays fixed while two axes turn. '
     'The three arrows are precisely the three columns of R.',
     'R maps a hand-frame vector into world coordinates; Rᵀ maps it back. '
     'The live orthogonality and determinant checks distinguish a rotation '
     'matrix from an arbitrary array of nine numbers.'),
    ('119 · Angular velocity and point velocity',
     'The purple arrow is the elbow rotation axis ω (1 rad/s). The gold arrow '
     'at the hand is its linear velocity ω × (p − elbow). It is tangent to '
     'the faint elbow-sweep curve. Move the elbow and compare the directions.',
     'The same angular velocity has world coordinates ω_s and hand coordinates '
     'ω_b = Rᵀω_s. Their components differ, but their lengths agree. The arrow '
     'lengths use a display scale; read the numbers for physical units.'),
    ('120 · Build a rotation with an exponential',
     'Use Rotation progress to rotate a ghost hand frame from the current '
     'orientation around the gold diagonal axis. The circular arc follows one '
     'local axis. At full progress the rotation is 120°.',
     'R_new = exp([ω̂]θ)R. The live logarithm recovers θ from the relative '
     'rotation. This is a rotation of a rigid hand about its centre, not an '
     'inverse-kinematics solution for the arm joints.'),
    ('121 · Pose, twist, screw and wrench',
     'Choose Rotation, Translation or Screw, then scrub Motion progress. The '
     'ghost hand follows exp([S]θ)T. A screw combines rotation around the world '
     'vertical axis with translation along it. The path shows the hand origin.',
     'A downward 5 N force at the hand creates moment p × f about the world '
     'origin. The readout transforms twist and wrench to the hand frame and '
     'checks that V·F gives the same power. The ghost is a rigid-body example, '
     'not a promise that these four arm joints can follow the whole path.'),
)


def arm_pose(q, tabletop=False):
    """Angles in radians; lengths in metres. Return joints and hand rotation."""
    yaw, elevation, elbow, roll = np.asarray(q, float)
    if tabletop:
        elevation = -np.arctan2(.65 * np.sin(elbow), .8 + .65 * np.cos(elbow))
    rz = rk.rot_exp([0, 0, yaw])
    upper = rz @ rk.rot_exp([0, -elevation, 0])
    fore = upper @ rk.rot_exp([0, -elbow, 0])
    shoulder = np.array([0., 0., 1.])
    joint = shoulder + upper @ [.8, 0, 0]
    hand = joint + fore @ [.65, 0, 0]
    return np.array([shoulder, joint, hand]), fore @ rk.rot_exp([roll, 0, 0]), elevation


def spatial_example(R, p, mode, progress):
    """A unit-rate spatial twist and its force dual, with matching origins."""
    V = (np.array([0., 0, 0, 0, 0, .35]) if mode == 1 else
         np.array([0., 0, 1, 0, 0, .18 if mode == 2 else 0]))
    T = rk.rp_to_T(R, p)
    moved = rk.exp6(V, progress * 2 * np.pi / 3) @ T
    f = np.array([0., 0, -5.])
    F = np.r_[np.cross(p, f), f]
    A = rk.adjoint(T)
    return moved, V, F, np.linalg.solve(A, V), A.T @ F


class RigidArmLab(Card):
    def __init__(self, lesson=0, capstone=False):
        super().__init__('3D arm capstone · pages 114–121' if capstone else 'Interactive 3D lab · human-style arm')
        self.add(body('A simplified shoulder–elbow–wrist manipulator. Drag the 3D view '
                      'to orbit; use the sliders to experiment. Red = local x, green = y, blue = z.'))
        self.lesson = QComboBox()
        self.lesson.addItems([item[0] for item in LESSONS])
        self.lesson.setCurrentIndex(lesson)
        self.lesson.setEnabled(capstone)
        self.add(self.lesson)
        self.prompt = body('')
        self.add(self.prompt)
        self.sliders = []
        for name, low, high, value in (
            ('Shoulder yaw', -360, 360, 30), ('Shoulder elevation', -70, 80, 15),
            ('Elbow flexion', 0, 150, 65), ('Wrist roll', -180, 180, 25),
            ('Motion / rotation progress', 0, 100, 50),
        ):
            row = QHBoxLayout()
            label = body(name)
            label.setMinimumWidth(185)
            row.addWidget(label)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(low, high)
            slider.setValue(value)
            row.addWidget(slider, 1)
            value_label = body('')
            value_label.setMinimumWidth(65)
            row.addWidget(value_label)
            self.add_layout(row)
            self.sliders.append((slider, value_label))
        controls = QHBoxLayout()
        self.constraint = QComboBox()
        self.constraint.addItems(['Free hand', 'Hand on tabletop (z = 1 m)'])
        controls.addWidget(self.constraint)
        self.motion = QComboBox()
        self.motion.addItems(['Rotation', 'Translation', 'Screw'])
        self.motion.setCurrentIndex(2)
        controls.addWidget(self.motion)
        reset = QPushButton('Reset pose & camera')
        reset.clicked.connect(self.reset)
        controls.addWidget(reset)
        if capstone:
            self.back = QPushButton('Previous page')
            self.next = QPushButton('Next page')
            self.back.clicked.connect(lambda: self.lesson.setCurrentIndex(max(0, self.lesson.currentIndex()-1)))
            self.next.clicked.connect(lambda: self.lesson.setCurrentIndex(min(7, self.lesson.currentIndex()+1)))
            controls.addWidget(self.back)
            controls.addWidget(self.next)
        self.add_layout(controls)
        self.cv = MplCanvas(width=9, height=4.8)
        self.cv.setMinimumHeight(450)
        self.cv.fig.clear()
        self.ax = self.cv.fig.add_subplot(121, projection='3d')
        self.detail = self.cv.fig.add_subplot(122, projection='3d')
        self.cv.axes = [self.ax, self.detail]
        self.add(self.cv)
        self.readout = body('')
        self.add(self.readout)
        self.takeaway = body('')
        self.add(self.takeaway)
        for slider, _ in self.sliders:
            slider.valueChanged.connect(self.draw)
        self.constraint.currentIndexChanged.connect(self.draw)
        self.motion.currentIndexChanged.connect(self.draw)
        self.lesson.currentIndexChanged.connect(self.change_lesson)
        self.change_lesson()

    def reset(self):
        for (slider, _), value in zip(self.sliders, (30, 15, 65, 25, 50)):
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
        for ax in (self.ax, self.detail):
            ax.view_init(25, -55)
        self.draw()

    def change_lesson(self):
        i = self.lesson.currentIndex()
        self.prompt.setText('<b>Try it:</b> ' + LESSONS[i][1])
        self.takeaway.setText('<b>What to carry forward:</b> ' + LESSONS[i][2])
        self.constraint.setVisible(i == 3)
        self.motion.setVisible(i == 7)
        self.sliders[4][0].setEnabled(i in (6, 7))
        if hasattr(self, 'back'):
            self.back.setEnabled(i > 0)
            self.next.setEnabled(i < 7)
        self.draw()

    @staticmethod
    def frame(ax, p, R, scale=.25, alpha=1):
        for j, color in enumerate((theme.BAD, theme.GOOD, theme.CYAN)):
            ax.quiver(*p, *(R[:, j]*scale), color=color, alpha=alpha, arrow_length_ratio=.2)

    @staticmethod
    def setup(ax, title, bounds):
        elev, azim = ax.elev, ax.azim
        ax.clear()
        ax.view_init(elev, azim)
        MplCanvas.style(ax)
        ax.set_title(title)
        for setter, lim in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), bounds):
            setter(*lim)
        ax.set_box_aspect([b-a for a, b in bounds])
        ax.set_xlabel('x'); ax.set_ylabel('y'); ax.set_zlabel('z', color=theme.TEXT_DIM)
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            axis.set_pane_color((.08, .10, .14, 1))

    def draw(self, *_):
        i = self.lesson.currentIndex()
        values = [s.value() for s, _ in self.sliders]
        for j, (_, label) in enumerate(self.sliders):
            label.setText(f'{values[j]}' + ('%' if j == 4 else '°'))
        q = np.radians(values[:4])
        constrained = i == 3 and self.constraint.currentIndex() == 1
        self.sliders[1][0].setEnabled(not constrained)
        P, R, elevation = arm_pose(q, constrained)
        if constrained:
            self.sliders[1][1].setText(f'{np.degrees(elevation):.1f}°*')
        p = P[-1]
        self.setup(self.ax, 'Shoulder → elbow → hand (metres)', ((-1.8, 1.8), (-1.8, 1.8), (-.6, 3.4)))
        a = self.ax
        a.plot([0, 0], [0, 0], [0, 1], color=theme.TEXT_DIM, lw=10)
        a.plot(*P.T, color=theme.ACCENT, lw=9, marker='o', markersize=10)
        for point, name in zip(P, ('shoulder', 'elbow', 'hand')):
            a.text(*(point + [0, 0, .12]), name, color=theme.TEXT, fontsize=8)
        self.frame(a, np.zeros(3), np.eye(3))
        self.frame(a, p, R)
        # A small palm plate makes roll visible even without the frame arrows.
        palm = np.array([[0, -.12, -.07], [0, .12, -.07], [0, .12, .07], [0, -.12, .07], [0, -.12, -.07]])
        a.plot(*(p + palm @ R.T).T, color=theme.WARN, lw=3)
        sweep = []
        for angle in np.linspace(0, np.radians(150), 50):
            probe = q.copy(); probe[2] = angle
            sweep.append(arm_pose(probe, constrained)[0][-1])
        a.plot(*np.array(sweep).T, color=theme.WARN, alpha=.5, lw=1.5)
        text = f'Hand p = {np.round(p, 3)} m · four joint coordinates'
        self.setup(self.detail, 'Hand orientation in world coordinates', ((-1, 1), (-1, 1), (-1, 1)))
        d = self.detail
        self.frame(d, np.zeros(3), np.eye(3), .8, .2)
        self.frame(d, np.zeros(3), R, .8)
        if i in (1, 2):
            self.setup(d, 'Two unlimited angles → torus slice', ((-1.5, 1.5), (-1.5, 1.5), (-.6, .6)))
            u, v = np.meshgrid(np.linspace(0, 2*np.pi, 40), np.linspace(0, 2*np.pi, 24))
            d.plot_surface((1+.35*np.cos(v))*np.cos(u), (1+.35*np.cos(v))*np.sin(u), .35*np.sin(v), color=theme.ACCENT, alpha=.25)
            yaw, roll = q[0], q[3]
            d.scatter([(1+.35*np.cos(roll))*np.cos(yaw)], [(1+.35*np.cos(roll))*np.sin(yaw)], [.35*np.sin(roll)], color=theme.WARN, s=65)
            text += f' · principal yaw = {(values[0]+180)%360-180}°; wrist = {values[3]}°'
        if i == 3:
            x, y = np.meshgrid([-1.5, 1.5], [-1.5, 1.5])
            a.plot_surface(x, y, np.ones_like(x), color=theme.GOOD, alpha=.15)
            text += f' · g(q) = z − 1 = {p[2]-1:+.6f} m · independent DOF: {3 if constrained else 4}'
        if i == 4:
            text += f'<br>R = {np.array2string(R, precision=2)}<br>‖RᵀR − I‖ = {np.linalg.norm(R.T@R-np.eye(3)):.2e}; det R = {np.linalg.det(R):.6f}'
        if i == 5:
            omega = rk.rot_exp([0, 0, q[0]]) @ [0, -1., 0]
            velocity = np.cross(omega, p-P[1])
            a.quiver(*P[1], *(omega*.5), color=theme.VIOLET)
            a.quiver(*p, *(velocity*.5), color=theme.WARN)
            d.quiver(0, 0, 0, *omega, color=theme.VIOLET)
            text += f'<br>ω_s = {np.round(omega,3)} rad/s; ω_b = {np.round(R.T@omega,3)} rad/s; hand velocity = {np.round(velocity,3)} m/s'
        if i == 6:
            axis = np.ones(3)/np.sqrt(3)
            theta = values[4]/100 * 2*np.pi/3
            delta = rk.rot_exp(axis*theta)
            self.frame(a, p, delta@R, .45, .6)
            self.frame(d, np.zeros(3), delta@R, .8, .6)
            d.quiver(0, 0, 0, *axis, color=theme.WARN)
            arc = np.array([rk.rot_exp(axis*t)@R[:,0]*.8 for t in np.linspace(0,theta,50)])
            d.plot(*arc.T, color=theme.WARN)
            text += f'<br>θ = {np.degrees(theta):.1f}° · ‖log(R_new Rᵀ)‖ = {np.degrees(np.linalg.norm(rk.rot_log(delta))):.1f}°'
        if i == 7:
            mode = self.motion.currentIndex()
            moved, V, F, Vb, Fb = spatial_example(R, p, mode, values[4]/100)
            self.frame(a, moved[:3,3], moved[:3,:3], .35, .7)
            path = np.array([spatial_example(R,p,mode,t)[0][:3,3] for t in np.linspace(0,1,40)])
            a.plot(*path.T, color=theme.VIOLET, ls='--')
            a.quiver(*p, 0, 0, -.5, color=theme.BAD)
            text += f'<br>World moment = {np.round(F[:3],3)} N·m; force = [0, 0, −5] N<br>V_s = {np.round(V,3)}; V_b = {np.round(Vb,3)}<br>Power: world {V@F:.4f} W = hand {Vb@Fb:.4f} W (unit motion rate)'
        self.readout.setText(text)
        self.cv.fig.subplots_adjust(left=.02, right=.94, bottom=.12, top=.91, wspace=.18)
        self.cv.refresh(layout=False)
