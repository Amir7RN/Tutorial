"""
Page 127 -- the matrix ideas behind singularity and manipulability, from scratch.

    a matrix is a machine      Ax = weighted sum of columns; J's columns
    determinant                area / volume factor; 0 = flattened
    eigenvectors               directions A only stretches, Av = λv
    symmetric matrices         real λ, perpendicular axes, A = QΛQᵀ, ellipsoids
    non-square matrices        no eigenvectors; the SVD J vᵢ = σᵢ uᵢ
    toolbox                    where each idea comes back (128 onward)

Three labs: a 2 × 2 machine with a test arrow, a symmetric 3 × 3 shown as
rotate-stretch-rotate in 3-D, and the SVD of the planar 3R Jacobian with the
joint-speed sphere drawn in 3-D.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QPushButton

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, callout, math_label, stat_row
from .base import Page
from .robo_common import (SEC_KIN, deg, draw_arm, interview, labelled_slider, mat_html,
                          plain, square, start_here)
from .robo_space_rigid import in_words, link_back
from .robo_space_topo import _clear, _layout

COL1, COL2, COL3 = theme.BAD, theme.VIOLET, theme.TEAL


def _tenth(v):
    return f"{v / 10:+.1f}"


def _cell_table(head, rows):
    cell = f"style='padding:3px 10px; border-bottom:1px solid {theme.BORDER}'"
    h = "".join(f"<th {cell} align='left'>{x}</th>" for x in head)
    r = "".join("<tr>" + "".join(f"<td {cell}>{x}</td>" for x in row) + "</tr>"
                for row in rows)
    return f"<table style='border-collapse:collapse'><tr>{h}</tr>{r}</table>"


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1.0, 0], [-s, 0, c]])


def _sphere(nu=22, nv=12):
    u, v = np.meshgrid(np.linspace(0, 2 * math.pi, nu), np.linspace(0, math.pi, nv))
    return np.stack([np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), np.cos(v)])


def _wire(ax, P, col, lw=0.6, alpha=0.8):
    ax.plot_wireframe(P[0], P[1], P[2], color=col, lw=lw, alpha=alpha)


def _arrow3(ax, p, d, col, lw=2.4, label=None):
    p = np.asarray(p, float)
    d = np.asarray(d, float)
    if np.linalg.norm(d) < 1e-9:
        ax.plot(*p, "o", color=col, ms=6)
    else:
        ax.quiver(*p, *d, color=col, lw=lw, arrow_length_ratio=0.12)
    if label:
        ax.text(*(p + 1.12 * d), label, color=col, fontsize=9, fontweight="bold")


# ==========================================================================
# 1. a matrix is a machine that moves arrows
# ==========================================================================

def machine_card() -> Card:
    c = Card("1 · a matrix is a machine that moves arrows: Ax is a weighted sum of columns")
    c.add(in_words(
        "Forget rows of numbers for a moment. A matrix A takes an arrow x and "
        "returns a new arrow Ax. That is all it is. And it is completely "
        "described by where it sends the basic arrows: column 1 is where the "
        "x-axis arrow (1, 0) lands, column 2 is where (0, 1) lands. Every "
        "other arrow is a mix of those two, so it lands on the same mix of "
        "the columns."))
    c.add(math_label(r"A=[\,a_1\ \ a_2\,]\quad\Rightarrow\quad Ax=x_1\,a_1+x_2\,a_2", 17))
    c.add(body(
        "<b>Example.</b> A = [2 1; 0 1] has columns a₁ = (2, 0) and a₂ = (1, 1). "
        "For x = (1, 2): Ax = 1·(2, 0) + 2·(1, 1) = (4, 2). Row-times-column "
        "gives the same numbers (2·1 + 1·2 = 4, 0·1 + 1·2 = 2), but the column "
        "reading is the one with a picture."))
    c.add(body(
        "<b>You have already been doing this.</b> The Jacobian is exactly such "
        "a machine. Its input is the list of joint speeds θ̇, its output the "
        "hand velocity, and column i is the hand velocity of joint i alone at "
        "1 rad/s: ω̂ᵢ × (moment arm), your picture from page 124. "
        "v = Jθ̇ = θ̇₁·(column 1) + θ̇₂·(column 2) + …, each joint's moment-arm "
        "velocity scaled by how fast that joint turns."))
    c.add(body(
        "<b>Three things to look at</b> when a machine is applied to a whole "
        "circle (or sphere) of arrows, all of them visible in the lab below:"))
    c.add(body(_cell_table(
        ("what happens", "the number that measures it", "what it means for J"),
        [("the circle becomes an ellipse", "its half-axes: the <b>singular values</b> σ₁ ≥ σ₂",
          "fast and slow hand directions"),
         ("the area is scaled", "|det A| = σ₁σ₂ (square A only)",
          "2R: |det J| = L₁L₂|sin θ₂|"),
         ("some arrows keep their direction", "the <b>eigenvectors</b>, stretched by λ",
          "<i>not</i> what matters for J; see section 5")])))
    c.add(plain(
        "Picture a sheet of rubber with a grid printed on it. The matrix "
        "grabs the sheet and stretches, shears, turns or flips it, always "
        "keeping grid lines straight, parallel and evenly spaced, and always "
        "keeping the origin fixed. That is what 'linear' means. The two "
        "column arrows tell you where the corner of the first grid square "
        "went; everything else follows."))
    return c


class MatrixMachineLab:
    """A 2 × 2 matrix acting on the plane, with a test arrow that hunts eigenvectors."""

    PRESETS = {
        "stretch: diag(2, 0.5)": (2, 0, 0, 0.5),
        "symmetric [[2, 1], [1, 2]]": (2, 1, 1, 2),
        "shear [[1, 1], [0, 1]]": (1, 1, 0, 1),
        "rotation by 90°": (0, -1, 1, 0),
        "flip: diag(1, −1)": (1, 0, 0, -1),
        "singular [[1, 2], [0.5, 1]]": (1, 2, 0.5, 1),
        "2R Jacobian at θ = (0°, 90°)": (-0.8, -0.8, 1, 0),
        "2R Jacobian, elbow straight": (0, 0, 1.8, 0.8),
    }

    def __init__(self):
        c = self.card = Card("lab: drive a 2 × 2 machine and hunt its eigenvectors")
        c.add(in_words(
            "Set the four numbers (or pick a preset). Left: the faint grid and "
            "circle are the input; the green ellipse and skewed grid are what "
            "the machine makes of them; the red and violet arrows are the two "
            "columns. The cyan arrow x is a test input and the orange arrow is "
            "Ax. Turn x with the angle slider or press Sweep. Usually Ax points "
            "somewhere else. When the two line up, x is an eigenvector. Right: "
            "how far Ax turns away from x, for every direction of x. Each zero "
            "crossing is an eigen-direction."))
        row = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.addItems(list(self.PRESETS))
        self.combo.currentTextChanged.connect(self._preset)
        self.btn = QPushButton("Sweep the test arrow round")
        self.btn.clicked.connect(self._sweep)
        row.addWidget(self.combo)
        row.addWidget(self.btn)
        row.addStretch(1)
        c.add_layout(row)
        self._mute = False
        init = self.PRESETS["stretch: diag(2, 0.5)"]
        names = ("a (row 1, col 1)", "b (row 1, col 2)", "c (row 2, col 1)", "d (row 2, col 2)")
        self.m = [labelled_slider(c, n, -25, 25, int(round(10 * v)), _tenth, self._draw)
                  for n, v in zip(names, init)]
        self.phi = labelled_slider(c, "test arrow x: angle", 0, 359, 30, deg, self._draw)
        self.st_det = Stat("det A (area factor)", "--", theme.ACCENT)
        self.st_l = Stat("eigenvalues λ₁, λ₂", "--", theme.PINK)
        self.st_s = Stat("singular values σ₁, σ₂", "--", theme.GOOD)
        self.st_t = Stat("Ax turns away from x by", "--", theme.WARN)
        c.add_layout(stat_row(self.st_det, self.st_l, self.st_s, self.st_t))
        self.txt = body("")
        c.add(self.txt)
        self.cv = MplCanvas(width=7.8, height=3.9, ncols=2)
        c.add(self.cv)
        c.add(plain(
            "<b>Try, in this order.</b> (1) <b>stretch</b>: the x-axis arrow "
            "doubles, the y-axis arrow halves, both keep direction: λ = 2 and "
            "0.5, eigenvectors along the axes. (2) <b>symmetric</b>: the "
            "eigen-directions are now the diagonals (1, 1) with λ = 3 and "
            "(1, −1) with λ = 1. They are perpendicular, and they are exactly "
            "the ellipse's axes. (3) <b>shear</b>: only one direction survives "
            "(the x-axis, λ = 1, counted twice). (4) <b>rotation</b>: Ax always "
            "turns by 90°, the curve never crosses zero, there is no real "
            "eigenvector: λ = ±i. (5) <b>flip</b>: λ = −1 means 'same line, "
            "pointing backwards'. (6) <b>singular</b>: det = 0, the plane is "
            "crushed onto a line; the direction that gets crushed to zero "
            "length is the eigenvector with λ = 0. (7) The two <b>2R "
            "Jacobians</b>: at θ = (0°, 90°) the eigenvalues are complex, yet "
            "the arm is perfectly fine; the ellipse (σ) is what tells you so. "
            "Straight elbow: σ₂ = 0, the ellipse is a line."))
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self._draw()

    def _preset(self, name):
        self._mute = True
        for s, v in zip(self.m, self.PRESETS[name]):
            s.setValue(int(round(10 * v)))
        self._mute = False
        self._draw()

    def _sweep(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn.setText("Sweep the test arrow round")
            return
        self.btn.setText("stop")
        self.timer.start(40)

    def _tick(self):
        self.phi.setValue((self.phi.value() + 3) % 360)

    def A(self):
        return np.array([s.value() / 10 for s in self.m]).reshape(2, 2)

    def _draw(self, *_):
        if self._mute:
            return
        A = self.A()
        phi = math.radians(self.phi.value())
        x = np.array([math.cos(phi), math.sin(phi)])
        y = A @ x
        lam = np.linalg.eigvals(A)
        s = np.linalg.svd(A, compute_uv=False)
        det = float(np.linalg.det(A))
        self.st_det.set(f"{det:+.2f}")
        if np.all(np.abs(lam.imag) < 1e-9):
            lr = np.sort(lam.real)[::-1]
            self.st_l.set(f"{lr[0]:+.2f}, {lr[1]:+.2f}")
        else:
            self.st_l.set(f"{lam[0].real:+.2f} ± {abs(lam[0].imag):.2f} i")
        self.st_s.set(f"{s[0]:.2f}, {s[1]:.2f}")
        turn = self._turn(A, phi)
        self.st_t.set("Ax = 0" if turn is None else f"{turn:+.0f}°")
        on = turn is not None and (abs(turn) < 2 or abs(abs(turn) - 180) < 2)
        self.st_t.set_color(theme.PINK if on or turn is None else theme.WARN)
        self.txt.setText(
            f"A = {mat_html(A, 2)} x = ({x[0]:+.2f}, {x[1]:+.2f}) → Ax = ({y[0]:+.2f}, {y[1]:+.2f})"
            + ("&nbsp;&nbsp;<b style='color:" + theme.PINK + "'>x is an eigenvector: Ax = "
               + f"{(y @ x):+.2f}·x</b>" if on else "")
            + (f"&nbsp;&nbsp;<b style='color:{theme.PINK}'>x is crushed to zero: λ = 0</b>"
               if turn is None else ""))
        c = self.cv
        c.clear()
        a1, a2 = c.axes
        g = np.linspace(-1, 1, 5)
        for k in g:
            for P in (np.array([[k, k], [-1, 1]]), np.array([[-1, 1], [k, k]])):
                a1.plot(*P, color=theme.BORDER, lw=0.7)
                a1.plot(*(A @ P), color=theme.TEXT_FAINT, lw=0.7, alpha=0.8)
        t = np.linspace(0, 2 * math.pi, 120)
        circ = np.vstack([np.cos(t), np.sin(t)])
        a1.plot(*circ, color=theme.TEXT_DIM, lw=1, ls=":")
        a1.plot(*(A @ circ), color=theme.GOOD, lw=2, label="A · (unit circle)")
        if np.all(np.abs(lam.imag) < 1e-9):
            w, V = np.linalg.eig(A)
            for j in range(2):
                v = np.real(V[:, j])
                a1.plot(*np.vstack([-3 * v, 3 * v]).T, "--", color=theme.PINK, lw=1,
                        label="eigen-direction" if j == 0 else None)
        for col, vec, name in ((COL1, A[:, 0], "column 1"), (COL2, A[:, 1], "column 2")):
            a1.annotate("", xy=vec, xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=2.2))
            a1.text(*(1.08 * vec), name, color=col, fontsize=8)
        a1.annotate("", xy=x, xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color=theme.CYAN, lw=2.2))
        a1.annotate("", xy=y, xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color=theme.ORANGE, lw=2.6))
        a1.text(*(1.1 * x), "x", color=theme.CYAN, fontsize=10, fontweight="bold")
        a1.text(*(y + 0.08), "Ax", color=theme.ORANGE, fontsize=10, fontweight="bold")
        r = max(2.0, 1.15 * float(np.max(np.abs(A @ circ))))
        square(a1, min(r, 4.5))
        c.legend(a1, loc="lower left")
        a1.set_title("input grid (faint) → output grid; cyan x → orange Ax")
        ph = np.radians(np.arange(0, 360, 1.0))
        tr = np.array([self._turn(A, p) for p in ph], dtype=float)
        a2.plot(np.degrees(ph), tr, color=theme.WARN, lw=1.8)
        a2.axhline(0, color=theme.PINK, lw=1)
        a2.axhline(180, color=theme.PINK, lw=0.6, ls=":")
        a2.axhline(-180, color=theme.PINK, lw=0.6, ls=":")
        a2.axvline(self.phi.value(), color=theme.CYAN, lw=1.2, ls="--")
        a2.set_xlim(0, 360)
        a2.set_ylim(-190, 190)
        a2.set_xlabel("direction of x (deg)")
        a2.set_ylabel("angle from x to Ax (deg)")
        a2.set_title("zero (or ±180°) = eigen-direction")
        c.refresh()

    @staticmethod
    def _turn(A, phi):
        x = np.array([math.cos(phi), math.sin(phi)])
        y = A @ x
        if np.linalg.norm(y) < 1e-6:
            return None
        return math.degrees(math.atan2(x[0] * y[1] - x[1] * y[0], x @ y))


# ==========================================================================
# 2-3. determinant, then eigenvectors
# ==========================================================================

def det_card() -> Card:
    c = Card("2 · the determinant: how much area (or volume) the machine creates")
    c.add(in_words(
        "Apply A to the unit square. It becomes a parallelogram spanned by "
        "the two columns. Its area is |det A|. In 3-D the unit cube becomes a "
        "slanted box of volume |det A|. A negative sign means the machine "
        "also flipped the plane over, like a mirror."))
    c.add(math_label(
        r"A=[a\ b;\ c\ d]:\ \ \det A=ad-bc\qquad\det A=0\ \Leftrightarrow\ "
        r"\mathrm{columns\ parallel}\ \Leftrightarrow\ Ax=0\ \mathrm{for\ some}\ x\neq0", 15))
    c.add(body(
        "<b>det = 0 is the key event.</b> The area collapses to zero, which "
        "means the two columns lie on one line. Then some whole direction of "
        "inputs gets crushed to zero output (the <b>null space</b>), and some "
        "direction of outputs can never be produced. There is no way to undo "
        "the machine: A⁻¹ does not exist. <b>Rank</b> = the number of "
        "independent directions that survive (2 for a healthy 2 × 2, 1 if "
        "crushed onto a line, 0 for the zero matrix)."))
    c.add(body(
        "<b>For the 2R arm</b>, columns = the two joints' moment-arm "
        "velocities. det J = L₁L₂ sin θ₂ is the area of the parallelogram they "
        "span. At θ₂ = 0 the arm is straight, both moment arms lie along the "
        "same line, both columns point the same way, the area is zero: "
        "singularity. 'Singular matrix' and 'singular pose' are the same "
        "word for the same event."))
    c.add(plain(
        "det answers 'is anything flattened?' with one number, but only for a "
        "square matrix and only as a yes/no with a size. It cannot tell you "
        "<i>which</i> direction is getting thin, and a 6 × 7 Jacobian has no "
        "determinant at all. The next sections give tools that do both."))
    return c


def eigen_card() -> Card:
    c = Card("3 · eigenvectors: the directions the machine does not turn")
    c.add(in_words(
        "Most arrows come out of A pointing in a new direction. A few special "
        "ones come out on the same line they went in: longer, shorter, or "
        "reversed, but not turned. Those are the eigenvectors ('own "
        "vectors' in German). The stretch factor is the eigenvalue λ."))
    c.add(math_label(r"A\,v=\lambda\,v\qquad(v\neq0)", 18))
    c.add(body(_cell_table(
        ("λ", "what happens to v", "picture"),
        [("λ &gt; 1", "same direction, longer", "stretched"),
         ("0 &lt; λ &lt; 1", "same direction, shorter", "squeezed"),
         ("λ &lt; 0", "same line, pointing backwards", "flipped"),
         ("λ = 0", "crushed to zero: v is in the null space", "the det = 0 direction"),
         ("complex (a ± bi)", "no real direction survives: the machine turns every arrow",
          "rotation; |λ| is the size change, the angle of λ the turn")])))
    c.add(body(
        "<b>How to find them by hand.</b> Av = λv means (A − λI)v = 0 has a "
        "non-zero solution, so A − λI must be singular: its determinant is "
        "zero. That gives a polynomial in λ (the <i>characteristic "
        "equation</i>). Solve it, then put each λ back to find v."))
    c.add(math_label(
        r"A=[2\ 1;\ 1\ 2]:\quad\det(A-\lambda I)=(2-\lambda)^2-1=0"
        r"\ \Rightarrow\ \lambda=3,\ 1", 15))
    c.add(body(
        "λ = 3: (A − 3I)v = 0 gives −v₁ + v₂ = 0, so v = (1, 1). "
        "λ = 1: v₁ + v₂ = 0, so v = (1, −1). Check: A(1, 1) = (3, 3) = 3·(1, 1). "
        "Two shortcuts that always hold: <b>λ₁ + λ₂ = trace</b> (sum of the "
        "diagonal, 2 + 2 = 4) and <b>λ₁λ₂ = det</b> (4 − 1 = 3). In n "
        "dimensions: n eigenvalues, sum = trace, product = det, so det = 0 "
        "exactly when some λ = 0."))
    c.add(body(
        "<b>Why eigenvectors are useful.</b> Along an eigenvector a matrix "
        "is just a number. Applying A ten times multiplies that direction by "
        "λ¹⁰, so it is easy to see what grows and what dies away. That is why "
        "eigenvalues of the state matrix are the <b>poles</b> of a linear "
        "system (page 21): each mode e<sup>λt</sup> grows if Re λ &gt; 0 and "
        "decays if Re λ &lt; 0."))
    c.add(plain(
        "Think of a door on its hinge. Swing it, and every point of the door "
        "moves to a new place except the points on the hinge line: they stay "
        "on that line. The hinge line is the eigenvector of that rotation, "
        "with λ = 1. (A 3-D rotation matrix always has one: its axis ω̂, page "
        "119.) Eigenvectors are 'the lines the machine leaves alone, except "
        "for scaling'."))
    return c


# ==========================================================================
# 4. symmetric matrices: rotate, stretch, rotate back
# ==========================================================================

def symmetric_card() -> Card:
    c = Card("4 · symmetric matrices: the well-behaved case, and where ellipsoids come from")
    c.add(in_words(
        "If A equals its own transpose (Aᵀ = A, mirror-image across the "
        "diagonal), everything becomes clean: the eigenvalues are real, the "
        "eigenvectors are perpendicular, and the machine is just 'turn the "
        "eigenvectors onto the x, y, z axes, stretch each axis by its λ, turn "
        "back'. A sphere goes in, an ellipsoid comes out, and the ellipsoid's "
        "axes are the eigenvectors."))
    c.add(math_label(
        r"A=A^T\ \Rightarrow\ A=Q\,\Lambda\,Q^T,\quad "
        r"Q=\left[\ v_1\ v_2\ v_3\ \right]\ (\mathrm{a\ rotation}),\quad "
        r"\Lambda=\mathrm{diag}(\lambda_1,\lambda_2,\lambda_3)", 15))
    c.add(body(
        "Read Q Λ Qᵀ x from right to left: <b>Qᵀ</b> measures x along the "
        "eigenvectors (it turns the eigen-directions onto the axes), "
        "<b>Λ</b> scales each of those three numbers, <b>Q</b> turns the "
        "result back. Q is a rotation matrix like the ones on page 118 "
        "(QᵀQ = I), so it never changes lengths; all the stretching is in Λ."))
    c.add(body(
        "<b>Positive definite</b> (written A ≻ 0) means every λ &gt; 0. "
        "Equivalently xᵀAx &gt; 0 for every x ≠ 0: the 'energy' ½xᵀAx is a "
        "bowl with its bottom at the origin. Three you will meet:"))
    c.add(body(_cell_table(
        ("matrix", "why symmetric, why positive", "page"),
        [("JJᵀ", "symmetric by construction; positive unless J lost a direction", "128 manipulability"),
         ("mass matrix M(q)", "kinetic energy ½q̇ᵀMq̇ &gt; 0 whenever anything moves", "134"),
         ("stiffness K (a spring)", "potential energy ½xᵀKx stored when stretched any way", "143–145")])))
    c.add(body(
        "<b>Two ellipsoids from one A ≻ 0.</b> Push the unit sphere through A: "
        "you get an ellipsoid with half-axes λᵢ along vᵢ. Or draw the "
        "level set xᵀA⁻¹x = 1: an ellipsoid with half-axes √λᵢ along vᵢ. "
        "Manipulability uses the second with A = JJᵀ, which is why the "
        "velocity ellipsoid's half-axes are √λ(JJᵀ) = σ, the singular values "
        "of section 5."))
    c.add(plain(
        "A symmetric matrix is a stretch with no twist: it has three "
        "perpendicular 'grain' directions, like wood, and it only pulls along "
        "them. The lab shows the three steps separately: watch the coloured "
        "eigen-arrows swing onto the x, y, z axes, get stretched, and swing "
        "back. Set one λ to 0 and the ellipsoid becomes a flat pancake: rank 2, "
        "det = 0, one direction crushed."))
    return c


class SymmetricLab:
    """A = Q Λ Qᵀ in 3-D, played as three steps on a wireframe sphere."""

    def __init__(self):
        c = self.card = Card("lab (3-D): a symmetric 3 × 3 is turn → stretch → turn back")
        c.add(in_words(
            "Choose the three eigenvalues and where the eigenvectors point "
            "(two angles). The step slider plays A = QΛQᵀ on the unit sphere: "
            "0 → 1 is Qᵀ (a pure turn: the sphere still looks like a sphere, "
            "but watch the coloured arrows swing onto the x, y, z axes), 1 → 2 "
            "is Λ (stretch along the axes), 2 → 3 is Q (turn back). At step 3 "
            "the arrows are λᵢvᵢ: the ellipsoid's half-axes."))
        self.lam = [labelled_slider(c, f"λ{i+1}", -10, 25, v, _tenth, self._draw)
                    for i, v in enumerate((20, 10, 4))]
        self.yaw = labelled_slider(c, "eigenvectors: turn about z", -180, 180, 35, deg, self._draw)
        self.tilt = labelled_slider(c, "eigenvectors: tilt", -90, 90, 25, deg, self._draw)
        self.step = labelled_slider(c, "step (0 sphere → 3 = A applied)", 0, 300, 300,
                                    lambda v: f"{v / 100:.2f}", self._draw)
        row = QHBoxLayout()
        self.btn = QPushButton("▶ play the three steps")
        self.btn.clicked.connect(self._play)
        row.addWidget(self.btn)
        row.addStretch(1)
        c.add_layout(row)
        self.txt = body("")
        c.add(self.txt)
        self.cv = MplCanvas(width=7.8, height=5.0)
        _layout(self.cv, ["3d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Press play and watch only the arrows: turn, "
            "stretch, turn. (2) Set λ₁ = λ₂ = λ₃: the turns do nothing at all, "
            "the sphere just grows. A = λI has every direction as an "
            "eigenvector. (3) Set λ₃ = 0: a flat pancake. The teal direction is "
            "crushed; that is the null space, and det A = λ₁λ₂λ₃ = 0. (4) Make "
            "λ₃ negative: the ellipsoid looks the same, but the teal arrow now "
            "points backwards: that axis was flipped. (5) Read A's numbers: "
            "they look like an unrelated jumble, yet A is just three stretches "
            "along three perpendicular lines. Eigen-decomposition is how you "
            "see that."))
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self._draw()

    def _play(self):
        self.step.setValue(0)
        self.timer.start(45)

    def _tick(self):
        v = self.step.value()
        if v >= 300:
            self.timer.stop()
            return
        self.step.setValue(min(300, v + 6))

    def _parts(self):
        lam = np.array([s.value() / 10 for s in self.lam])
        psi, beta = math.radians(self.yaw.value()), math.radians(self.tilt.value())
        return lam, psi, beta, _rz(psi) @ _ry(beta)

    @staticmethod
    def _partial(s, lam, psi, beta):
        """The map after `s` of the three steps (s in 0..3)."""
        t1, t2, t3 = (min(1.0, max(0.0, s - k)) for k in range(3))
        QT = _ry(-beta * t1) @ _rz(-psi * t1)
        L = np.diag(1 + (lam - 1) * t2)
        Q = _rz(psi * t3) @ _ry(beta * t3)
        return Q @ L @ QT

    def _draw(self, *_):
        lam, psi, beta, Q = self._parts()
        A = Q @ np.diag(lam) @ Q.T
        s = self.step.value() / 100
        Mp = self._partial(s, lam, psi, beta)
        stage = ("start: the unit sphere and the three eigenvectors vᵢ",
                 "step 1, Qᵀ: turning the eigenvectors onto x, y, z (no stretching)",
                 "step 2, Λ: stretching along x, y, z by λ₁, λ₂, λ₃",
                 "step 3, Q: turning back. Done: this is A applied")[
            0 if s <= 0 else min(3, int(math.ceil(s)))]
        self.txt.setText(
            f"A = QΛQᵀ = {mat_html(A, 2)} det A = λ₁λ₂λ₃ = {np.prod(lam):+.2f}, "
            f"trace = λ₁+λ₂+λ₃ = {lam.sum():+.2f}. "
            f"<span style='color:{theme.TEXT_DIM}'>{stage}</span>")
        _clear(self.cv)
        ax = self.cv.ax
        S = _sphere()
        _wire(ax, S, theme.BORDER, lw=0.5, alpha=0.6)
        P = np.einsum("ij,jkl->ikl", Mp, S)
        _wire(ax, P, theme.GOOD, lw=0.7, alpha=0.9)
        # one painted meridian so a pure rotation is visible on the wireframe
        tt = np.linspace(0, math.pi, 40)
        mer = np.vstack([np.sin(tt), np.zeros_like(tt), np.cos(tt)])
        ax.plot(*(Mp @ mer), color=theme.ORANGE, lw=2.2)
        for i, col in enumerate((COL1, COL2, COL3)):
            _arrow3(ax, (0, 0, 0), Mp @ Q[:, i], col, label=f"v{i+1}" if s <= 0 else f"λ{i+1}v{i+1}"
                    if s >= 3 else None)
        for k, col in enumerate(("#55606f",) * 3):
            e = np.zeros(3)
            e[k] = 1.15 * max(1.0, float(np.max(np.abs(lam))))
            ax.plot(*np.vstack([-e, e]).T, color=col, lw=0.6)
        r = 1.1 * max(1.0, float(np.max(np.abs(lam))))
        for nm in ("x", "y", "z"):
            getattr(ax, f"set_{nm}lim")(-r, r)
        ax.set_box_aspect((1, 1, 1), zoom=1.35)
        ax.view_init(elev=20, azim=-55)
        ax.set_title(f"step {s:.2f} of 3", color=theme.TEXT, fontsize=9)
        self.cv.fig.subplots_adjust(left=0, right=1, bottom=0, top=0.94)
        self.cv.refresh(layout=False)


# ==========================================================================
# 5. non-square matrices: the SVD
# ==========================================================================

def svd_card() -> Card:
    c = Card("5 · Jacobians are rarely square, and even square ones need the SVD, not eigenvalues")
    c.add(in_words(
        "The planar 3R arm's position Jacobian is 2 × 3: three joint speeds "
        "in, two hand-velocity numbers out. Input and output live in "
        "different spaces, so 'comes out in the same direction it went in' "
        "makes no sense: no eigenvectors. Ask a better question instead: "
        "which input directions come out <i>perpendicular</i> to each other, "
        "and how much is each one stretched? The answer is the "
        "<b>singular value decomposition</b> (SVD), and it exists for every "
        "matrix, any shape."))
    c.add(math_label(
        r"J=U\,\Sigma\,V^T,\qquad J\,v_i=\sigma_i\,u_i,\qquad "
        r"\sigma_1\geq\sigma_2\geq\cdots\geq0", 17))
    c.add(body(_cell_table(
        ("piece", "lives in", "meaning for an arm"),
        [("vᵢ (columns of V)", "joint-speed space (n numbers)",
          "special joint-speed mixes; perpendicular to each other"),
         ("σᵢ (diagonal of Σ)", "a plain number ≥ 0", "the gain: hand speed per unit joint speed along vᵢ"),
         ("uᵢ (columns of U)", "hand-velocity space (m numbers)",
          "where vᵢ ends up: the ellipse's axes; perpendicular too"),
         ("vᵢ with σᵢ = 0, and any extra vᵢ when n &gt; m", "joint-speed space",
          "the <b>null space</b>: joint motion the hand does not feel")])))
    c.add(body(
        "Same three-step story as the symmetric case, but the two turns are "
        "different: <b>Vᵀ</b> turns the joint-speed sphere so its special "
        "directions line up with the axes, <b>Σ</b> stretches (and drops any "
        "extra dimensions), <b>U</b> turns the result into the hand's "
        "directions. The unit sphere of joint speeds always becomes an "
        "ellipsoid of hand velocities with half-axes σᵢ along uᵢ."))
    c.add(body(
        "<b>The link to section 4</b>, and the reason manipulability is "
        "written with JJᵀ: multiply J vᵢ = σᵢuᵢ by Jᵀ and you find"))
    c.add(math_label(
        r"JJ^T\,u_i=\sigma_i^2\,u_i,\qquad J^TJ\,v_i=\sigma_i^2\,v_i"
        r"\qquad\Rightarrow\qquad\sigma_i=\sqrt{\lambda_i(JJ^T)}", 16))
    c.add(body(
        "So the singular values of J are the square roots of the eigenvalues "
        "of the symmetric, positive matrix JJᵀ, and the axes uᵢ are its "
        "eigenvectors. Every formula on the next page is one of these facts."))
    c.add(body(
        "<b>Why not the eigenvalues of J itself, when J is square?</b> Because "
        "they answer the wrong question. For the 2R arm at θ = (0°, 90°), "
        "L = (1, 0.8), the eigenvalues of J are −0.4 ± 0.8i: complex, telling "
        "you only that J turns every arrow. Its singular values are 1.40 and "
        "0.57: the hand moves up to 1.40 m/s and at least 0.57 m/s per 1 rad/s "
        "of joint speed. Only the σ's have that physical meaning. Eigenvalues "
        "are for a matrix that maps a space to <i>itself</i> (a state "
        "matrix, M, K, JJᵀ). Singular values are for a map between two different "
        "spaces (joints → hand)."))
    c.add(plain(
        "Picture the 3R arm. Its three joint speeds form a 3-D 'joint-speed "
        "ball'. The Jacobian flattens that ball onto the 2-D plane of hand "
        "velocities. One direction through the ball (the null direction v₃) "
        "gets squashed to nothing: those joint motions only swing the elbow "
        "while the hand stays still. The other two get stretched by σ₁ and "
        "σ₂ into the ellipse. In the lab the left picture is the ball, the "
        "right one is the hand."))
    return c


class SVDLab:
    """Planar 3R position Jacobian: joint-speed sphere (3-D) → hand ellipse (2-D)."""

    L = (1.0, 0.8, 0.5)

    def __init__(self):
        c = self.card = Card("lab (3-D): the SVD of the 3R arm's Jacobian, ball in, ellipse out")
        c.add(in_words(
            "Left: the space of joint speeds (θ̇₁, θ̇₂, θ̇₃), with the unit ball "
            "of all mixes of length 1. Green and orange arrows are v₁ and v₂; "
            "the red arrow is v₃, the null direction. The highlighted great "
            "circle is every mix of v₁ and v₂. Right: the arm, and what J does "
            "to the ball. The dots are 400 random unit joint-speed vectors, "
            "pushed through J. They fill the ellipse, because a 3-D ball "
            "flattens onto a filled 2-D disc. The highlighted circle becomes "
            "the ellipse's rim, and the red null arrow lands on the hand point "
            "itself: zero hand velocity."))
        self.q = [labelled_slider(c, f"θ{i+1}", -180, 180, v, deg, self._draw)
                  for i, v in enumerate((20, 60, 50))]
        self.chk = QCheckBox("show the 400 random joint-speed vectors")
        self.chk.setChecked(True)
        self.chk.stateChanged.connect(self._draw)
        c.add(self.chk)
        self.st_s = Stat("σ₁, σ₂ (ellipse half-axes)", "--", theme.GOOD)
        self.st_r = Stat("rank J", "--", theme.ACCENT)
        self.st_n = Stat("null direction v₃", "--", theme.BAD)
        self.st_c = Stat("σ₁ / σ₂", "--", theme.VIOLET)
        c.add_layout(stat_row(self.st_s, self.st_r, self.st_n, self.st_c))
        self.txt = body("")
        c.add(self.txt)
        self.cv = MplCanvas(width=8.0, height=4.4)
        _layout(self.cv, ["3d", "2d"])
        c.add(self.cv)
        c.add(plain(
            "<b>Try.</b> (1) Read J's three columns in the text: each is one "
            "joint's moment-arm velocity, ẑ × (tip − joint). J v₃ = 0 means "
            "the three columns, weighted by v₃'s numbers, cancel exactly. "
            "(2) Set θ₂ = θ₃ = 0 (arm straight): σ₂ → 0, the ellipse becomes a "
            "line, and the rank drops to 1. Now two whole directions of the "
            "ball are crushed. (3) Fold the arm (θ₂ ≈ 120°, θ₃ ≈ 90°) and find "
            "a pose where σ₁/σ₂ is close to 1, a nearly round ellipse: the "
            "hand is equally quick in every direction. (4) Change θ₁ only: the "
            "σ's do not change, the whole picture just turns. The shape of the "
            "ellipse depends only on how the arm is bent."))
        rng = np.random.default_rng(3)
        X = rng.normal(size=(3, 400))
        self.ball = X / np.linalg.norm(X, axis=0)
        self._draw()

    def _draw(self, *_):
        q = np.radians([s.value() for s in self.q])
        J = rk.planar_jacobian(self.L, q)
        U, s, Vt = np.linalg.svd(J)
        V = Vt.T
        rank = int(np.sum(s > 1e-6))
        self.st_s.set(f"{s[0]:.2f}, {s[1]:.2f}")
        self.st_r.set(str(rank))
        self.st_r.set_color(theme.ACCENT if rank == 2 else theme.BAD)
        v3 = V[:, 2] * (1 if V[np.argmax(np.abs(V[:, 2])), 2] > 0 else -1)
        self.st_n.set("(" + ", ".join(f"{x:+.2f}" for x in v3) + ")")
        self.st_c.set("∞" if s[1] < 1e-9 else f"{s[0] / s[1]:.2f}")
        self.txt.setText(
            f"J = {mat_html(J, 2)} columns = what each joint alone does to the hand. "
            f"J v₃ = ({(J @ v3)[0]:+.1e}, {(J @ v3)[1]:+.1e}) ≈ 0.")
        _clear(self.cv)
        ax, bx = self.cv.axes
        S = _sphere(20, 11)
        _wire(ax, S, theme.BORDER, lw=0.45, alpha=0.55)
        t = np.linspace(0, 2 * math.pi, 100)
        gc = np.outer(V[:, 0], np.cos(t)) + np.outer(V[:, 1], np.sin(t))
        ax.plot(*gc, color=theme.CYAN, lw=2.2)
        if self.chk.isChecked():
            ax.scatter(*self.ball, s=2, color=theme.TEXT_FAINT, alpha=0.5, depthshade=False)
        _arrow3(ax, (0, 0, 0), V[:, 0], theme.GOOD, label="v₁")
        _arrow3(ax, (0, 0, 0), V[:, 1], theme.WARN, label="v₂")
        _arrow3(ax, (0, 0, 0), v3, theme.BAD, label="v₃ (null)")
        for k, nm in enumerate(("θ̇₁", "θ̇₂", "θ̇₃")):
            e = np.zeros(3)
            e[k] = 1.25
            ax.plot(*np.vstack([-e, e]).T, color="#55606f", lw=0.7)
            ax.text(*(1.04 * e), nm, color=theme.TEXT_DIM, fontsize=8)
        for nm in ("x", "y", "z"):
            getattr(ax, f"set_{nm}lim")(-1.3, 1.3)
        ax.set_box_aspect((1, 1, 1), zoom=1.2)
        ax.view_init(elev=22, azim=-50)
        ax.set_title("joint-speed space: the unit ball", color=theme.TEXT, fontsize=9)
        pts = draw_arm(bx, self.L, q)
        tip = pts[-1]
        k = 0.45
        if self.chk.isChecked():
            D = J @ self.ball
            bx.plot(*(tip[:, None] + k * D), ".", color=theme.TEXT_FAINT, ms=2, alpha=0.6)
        E = U @ np.diag(s) @ np.vstack([np.cos(t), np.sin(t)])
        bx.plot(*(tip[:, None] + k * E), color=theme.CYAN, lw=2)
        for j, col, nm in ((0, theme.GOOD, "σ₁u₁"), (1, theme.WARN, "σ₂u₂")):
            d = k * s[j] * U[:, j]
            bx.annotate("", xy=tip + d, xytext=tip,
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=2.2))
            bx.text(*(tip + 1.15 * d + 0.03), nm, color=col, fontsize=9)
        bx.plot(*tip, "o", color=theme.BAD, ms=6)
        square(bx, sum(self.L) + 0.2)
        bx.set_title("hand: J · ball = filled ellipse (×0.45)")
        self.cv.fig.subplots_adjust(left=0.0, right=0.97, bottom=0.08, top=0.92, wspace=0.12)
        self.cv.refresh(layout=False)


# ==========================================================================
# 6-7. worked by hand, and the toolbox
# ==========================================================================

def worked_card() -> Card:
    c = Card("6 · worked by hand: the 2R arm at θ = (0°, 90°), L = (1, 0.8)")
    c.add(in_words(
        "Everything above, on one Jacobian, with a calculator. This is the "
        "exact computation the next page automates for every pose."))
    c.add(body(
        "<b>1. The Jacobian.</b> With s₁ = sin θ₁ = 0, c₁ = 1, s₁₂ = sin 90° = 1, "
        "c₁₂ = 0, the 2R formula J = [−L₁s₁ − L₂s₁₂, −L₂s₁₂; L₁c₁ + L₂c₁₂, L₂c₁₂] gives"))
    c.add(body(_cell_table(
        ("J", "JJᵀ", "trace, det of JJᵀ"),
        [("[ −0.8 &nbsp; −0.8 ]<br>[ 1.0 &nbsp;&nbsp;&nbsp; 0.0 ]",
          "[ 1.28 &nbsp; −0.80 ]<br>[ −0.80 &nbsp; 1.00 ]",
          "trace = 2.28<br>det = 1.28 − 0.64 = 0.64")])))
    c.add(body(
        "Column 1 (−0.8, 1): joint 1 swings the hand about the base, at right "
        "angles to the line base → hand. Column 2 (−0.8, 0): joint 2 swings it "
        "about the elbow, straight left."))
    c.add(body(
        "<b>2. Eigenvalues of JJᵀ</b> from λ² − (trace)λ + det = 0:"))
    c.add(math_label(
        r"\lambda=\frac{2.28\pm\sqrt{2.28^2-4(0.64)}}{2}=\frac{2.28\pm1.624}{2}"
        r"=1.952,\ \ 0.328", 15))
    c.add(body(
        "<b>3. Singular values</b> σ = √λ = <b>1.397</b> and <b>0.573</b>. "
        "Check: σ₁σ₂ = 0.800 = |det J| = L₁L₂|sin 90°|. ✓<br>"
        "<b>4. Axis of the long direction</b>: (JJᵀ − 1.952 I)u = 0 gives "
        "−0.672u₁ − 0.8u₂ = 0, so u₁ ∝ (0.766, −0.643), pointing 40° below the "
        "x-axis (or the opposite way, 140°: an axis has no arrowhead).<br>"
        "<b>5. Read it.</b> One rad/s of joint speed, spent in the best mix, "
        "moves the hand at 1.40 m/s along ±(0.766, −0.643). Spent in the worst "
        "mix it gives only 0.57 m/s, along the perpendicular direction. The "
        "ellipse is 2.44 times longer than wide (σ₁/σ₂). The force ellipse "
        "has the same axes with half-lengths 1/σ = 0.72 and 1.75: the hand "
        "pushes hardest along the slow direction.<br>"
        "<b>6. And J's own eigenvalues?</b> trace J = −0.8, det J = 0.8, so "
        "λ² + 0.8λ + 0.8 = 0 and λ = −0.4 ± 0.8i. Complex, useless for "
        "speeds. Section 5 in one example."))
    return c


def toolbox_card() -> Card:
    c = Card("7 · the toolbox: which idea answers which robotics question")
    c.add(in_words(
        "Keep this table. Every later page that says 'singular', 'ellipsoid', "
        "'condition number', 'pseudo-inverse', 'positive definite' or 'pole' "
        "is using one row of it."))
    c.add(body(_cell_table(
        ("idea", "the question it answers", "where it comes back"),
        [("Ax = weighted sum of columns", "what does each input do on its own?",
          "J's columns (124), Jᵀ's rows give torques (126)"),
         ("det A, rank", "is anything flattened? how many directions survive?",
          "singular poses (126), closed chains (132)"),
         ("eigen: Av = λv", "which directions only scale? does a mode grow or die?",
          "poles = eig(A) (21), rotation axis (119), M(q) ≻ 0 (134)"),
         ("symmetric A = QΛQᵀ, ≻ 0", "what shape is this energy / ellipsoid?",
          "JJᵀ (128), mass matrix (134), task-space inertia Λ (138), stiffness K (143–145)"),
         ("SVD: J vᵢ = σᵢuᵢ", "fast and slow directions of a map between two spaces",
          "velocity ellipse (124), manipulability (128)"),
         ("σ<sub>min</sub> → 0", "how close to losing a direction?",
          "singularities (126), μ measures (128)"),
         ("σ₁/σ<sub>min</sub> (condition number)", "how lopsided? how much does an error get amplified?",
          "μ₁ (128), IK conditioning (129)"),
         ("null space: vᵢ with σᵢ = 0", "which inputs do nothing at the output?",
          "redundancy and self-motion (130), OSC posture (144)"),
         ("pseudo-inverse J⁺ = V Σ⁺ Uᵀ (1/σ)", "undo J as well as possible",
          "Newton IK (129), J⁺ and I − J⁺J (130)"),
         ("damped σ/(σ² + λ²)", "undo J without exploding near σ = 0",
          "damped least squares (129)")])))
    c.add(body(
        "<b>One line to remember.</b> Inverting a matrix divides by its "
        "singular values. Near a singularity σ<sub>min</sub> is tiny, so "
        "1/σ<sub>min</sub> is huge: that is the 'huge joint speeds near a "
        "singularity' you will meet in inverse kinematics, and damping replaces "
        "1/σ by σ/(σ² + λ²) to keep it bounded."))
    return c


class EigenPage(Page):
    TITLE = "Matrices as Machines: Eigenvectors and the SVD"
    SUBTITLE = ("Before manipulability: what a matrix does to arrows, what det, "
                "eigenvalues and eigenvectors mean, why a symmetric matrix is a "
                "stretch along perpendicular axes, and why a Jacobian needs "
                "singular values instead of eigenvalues.")
    SECTION = SEC_KIN

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "The next page measures how close an arm is to a singularity by "
            "looking at an ellipsoid built from J. To read it you need four "
            "ideas from linear algebra: a matrix as a machine that moves "
            "arrows, the determinant, eigenvectors, and the singular value "
            "decomposition. This page builds them from nothing, with pictures "
            "first and formulas second, and ties each one back to the "
            "moment-arm picture of the Jacobian."))
        self.add(link_back(
            "124–126",
            "Page 124: column i of J = ω̂ᵢ × (moment arm), joint i's velocity "
            "contribution. Page 126: at a singularity those columns become "
            "parallel and the ellipse goes flat. This page explains the "
            "matrix language for that ('rank', 'σ', 'eigenvector', "
            "'positive definite') so page 128 can be read without hand-waving."))
        self.add(machine_card())
        self.machine_lab = MatrixMachineLab()
        self.add(self.machine_lab.card)
        self.add(det_card())
        self.add(eigen_card())
        self.add(symmetric_card())
        self.sym_lab = SymmetricLab()
        self.add(self.sym_lab.card)
        self.add(svd_card())
        self.svd_lab = SVDLab()
        self.add(self.svd_lab.card)
        self.add(worked_card())
        self.add(toolbox_card())
        self.add(callout(
            "Eigenvectors: directions a matrix only <b>scales</b> (Av = λv), for "
            "a map of a space to itself. Symmetric matrices scale along "
            "perpendicular axes: A = QΛQᵀ, sphere → ellipsoid. Singular "
            "vectors: input directions that come out perpendicular "
            "(J vᵢ = σᵢuᵢ), for any matrix. For a Jacobian, read the σ's: "
            "σᵢ = √λᵢ(JJᵀ) are the ellipse's half-axes, and σ<sub>min</sub> = 0 "
            "is a singularity.", "key"))
        self.add(interview(
            "<b>“Your Jacobian is square. Can you judge how close the arm is to "
            "a singularity from J's eigenvalues?”</b> No. Eigenvalues describe "
            "a map from a space to itself; J maps joint speeds to hand "
            "velocities, two different spaces, and its eigenvalues can be "
            "complex at a perfectly healthy pose. Use singular values: "
            "σ<sub>min</sub>(J) (or σ<sub>min</sub>/σ<sub>max</sub>, or "
            "√det JJᵀ = Πσᵢ). Only |det J| = Π|λᵢ| = Πσᵢ coincides, which is "
            "why det J = 0 still flags the singularity itself."))
        self.finish()
