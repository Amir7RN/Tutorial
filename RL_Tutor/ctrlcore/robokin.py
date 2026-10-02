"""
robokin.py -- configuration space, rigid-body motion and kinematics.

The numerical core of the Robot Mechanics block (Modern Robotics, Lynch &
Park, chapters 2-7 and 10, 12, 13). Everything is plain numpy so the pages and
the tests can call it directly.

    configuration space   grubler, four_bar
    rigid-body motion     skew, rot_exp, rot_log, twist_hat, exp6, log6,
                          adjoint, inv_T
    forward kinematics    fk_space, fk_body (product of exponentials)
    velocity kinematics   jacobian_space, jacobian_body, planar_* helpers,
                          manipulability
    inverse kinematics    ik_2r (analytic), ik_newton (numerical)
    redundancy            pinv_damped, null_projector
    planning              cspace_grid_2r, astar, rrt
    grasping              force_closure_planar
    mobile robots         diff_drive_step

Conventions follow the book: screw axes S = (omega, v) with the angular part
first, twists V = (omega, v), wrenches F = (m, f).
"""

from __future__ import annotations

import heapq
import math

import numpy as np

EPS = 1e-9


# ==========================================================================
# Chapter 2 -- configuration space
# ==========================================================================

def grubler(N: int, joints: list[int], m: int = 3) -> int:
    """
    Gruebler's formula.  N links INCLUDING ground, `joints` lists the freedom
    f_i of each joint, m = 3 (planar) or 6 (spatial).

        dof = m (N - 1 - J) + sum f_i
    """
    J = len(joints)
    return m * (N - 1 - J) + sum(joints)


def four_bar(theta: float, a: float, b: float, c: float, d: float,
             branch: int = 1):
    """
    Closed chain: ground link d between the two fixed pivots, input crank a at
    angle theta, coupler b, rocker c. Returns (A, B) the two moving pivots, or
    None when the loop cannot close at this input angle.
    """
    A = np.array([a * math.cos(theta), a * math.sin(theta)])
    D = np.array([d, 0.0])
    r = np.linalg.norm(D - A)
    if r > b + c or r < abs(b - c) or r < EPS:
        return None
    # intersection of circle (A, b) and circle (D, c)
    x = (b * b - c * c + r * r) / (2 * r)
    h = math.sqrt(max(b * b - x * x, 0.0))
    u = (D - A) / r
    perp = np.array([-u[1], u[0]])
    B = A + x * u + branch * h * perp
    return A, B


# ==========================================================================
# Chapter 3 -- rigid-body motions
# ==========================================================================

def skew(w) -> np.ndarray:
    w = np.asarray(w, float)
    return np.array([[0, -w[2], w[1]],
                     [w[2], 0, -w[0]],
                     [-w[1], w[0], 0]])


def unskew(W) -> np.ndarray:
    return np.array([W[2, 1], W[0, 2], W[1, 0]])


def rot_exp(omega_theta) -> np.ndarray:
    """Rodrigues: exp([w] theta) for an exponential coordinate w*theta."""
    wt = np.asarray(omega_theta, float)
    th = np.linalg.norm(wt)
    if th < EPS:
        return np.eye(3)
    K = skew(wt / th)
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def rot_log(R) -> np.ndarray:
    """Matrix log of R in SO(3), returned as the 3-vector w*theta."""
    R = np.asarray(R, float)
    c = (np.trace(R) - 1) / 2
    c = min(1.0, max(-1.0, c))
    th = math.acos(c)
    if th < 1e-7:
        return np.zeros(3)
    if abs(math.pi - th) < 1e-6:
        # theta = pi: pick the best-conditioned column of R + I
        k = int(np.argmax(np.diag(R)))
        w = (R[:, k] + np.eye(3)[:, k]) / math.sqrt(2 * (1 + R[k, k]))
        return w * math.pi
    W = (R - R.T) / (2 * math.sin(th))
    return unskew(W) * th


def rp_to_T(R, p) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = p
    return T


def inv_T(T) -> np.ndarray:
    R, p = T[:3, :3], T[:3, 3]
    return rp_to_T(R.T, -R.T @ p)


def twist_hat(V) -> np.ndarray:
    """6-vector (omega, v) -> 4x4 se(3) matrix."""
    V = np.asarray(V, float)
    M = np.zeros((4, 4))
    M[:3, :3] = skew(V[:3])
    M[:3, 3] = V[3:]
    return M


def adjoint(T) -> np.ndarray:
    """[Ad_T]: maps a twist in frame {b} to frame {s} when T = T_sb."""
    R, p = T[:3, :3], T[:3, 3]
    A = np.zeros((6, 6))
    A[:3, :3] = R
    A[3:, :3] = skew(p) @ R
    A[3:, 3:] = R
    return A


def exp6(S, theta: float) -> np.ndarray:
    """exp([S] theta) for a screw axis S = (omega, v)."""
    S = np.asarray(S, float)
    w, v = S[:3], S[3:]
    if np.linalg.norm(w) < EPS:
        return rp_to_T(np.eye(3), v * theta)
    K = skew(w)
    R = rot_exp(w * theta)
    G = (np.eye(3) * theta + (1 - math.cos(theta)) * K
         + (theta - math.sin(theta)) * K @ K)
    return rp_to_T(R, G @ v)


def log6(T):
    """Returns (S, theta) with exp([S] theta) = T."""
    R, p = T[:3, :3], T[:3, 3]
    wt = rot_log(R)
    th = np.linalg.norm(wt)
    if th < 1e-7:
        n = np.linalg.norm(p)
        if n < EPS:
            return np.zeros(6), 0.0
        return np.r_[np.zeros(3), p / n], n
    w = wt / th
    K = skew(w)
    Ginv = (np.eye(3) / th - K / 2
            + (1 / th - 0.5 / math.tan(th / 2)) * K @ K)
    return np.r_[w, Ginv @ p], th


def screw_axis(q, s, h: float = 0.0) -> np.ndarray:
    """Screw axis through point q along unit direction s with pitch h."""
    s = np.asarray(s, float)
    q = np.asarray(q, float)
    return np.r_[s, -np.cross(s, q) + h * s]


# ==========================================================================
# Chapter 4 -- forward kinematics (product of exponentials)
# ==========================================================================

def fk_space(M, Slist, thetas) -> np.ndarray:
    """T = e^[S1]th1 ... e^[Sn]thn M, screw axes in the space frame."""
    T = np.eye(4)
    for S, th in zip(np.asarray(Slist).T, thetas):
        T = T @ exp6(S, th)
    return T @ M


def fk_body(M, Blist, thetas) -> np.ndarray:
    """T = M e^[B1]th1 ... e^[Bn]thn, screw axes in the end-effector frame."""
    T = np.array(M, float)
    for B, th in zip(np.asarray(Blist).T, thetas):
        T = T @ exp6(B, th)
    return T


def planar_screws(lengths):
    """Space-frame screw axes and home pose of a planar nR arm along x."""
    n = len(lengths)
    S = np.zeros((6, n))
    x = 0.0
    for i in range(n):
        S[:, i] = screw_axis([x, 0, 0], [0, 0, 1])
        x += lengths[i]
    M = rp_to_T(np.eye(3), [x, 0, 0])
    return S, M


# ==========================================================================
# Chapter 5 -- velocity kinematics and statics
# ==========================================================================

def jacobian_space(Slist, thetas) -> np.ndarray:
    """Column i is S_i carried by the joints before it: Ad(e^[S1]th1...)S_i."""
    Slist = np.asarray(Slist, float)
    J = np.array(Slist, float)
    T = np.eye(4)
    for i in range(1, Slist.shape[1]):
        T = T @ exp6(Slist[:, i - 1], thetas[i - 1])
        J[:, i] = adjoint(T) @ Slist[:, i]
    return J


def jacobian_body(Blist, thetas) -> np.ndarray:
    """Column i is B_i carried back by the joints after it."""
    Blist = np.asarray(Blist, float)
    n = Blist.shape[1]
    J = np.array(Blist, float)
    T = np.eye(4)
    for i in range(n - 2, -1, -1):
        T = T @ exp6(-Blist[:, i + 1], thetas[i + 1])
        J[:, i] = adjoint(T) @ Blist[:, i]
    return J


def planar_points(lengths, q) -> np.ndarray:
    """Joint positions (n+1, 2) of a planar arm, base at the origin."""
    pts = [np.zeros(2)]
    a = 0.0
    for L, qi in zip(lengths, q):
        a += qi
        pts.append(pts[-1] + L * np.array([math.cos(a), math.sin(a)]))
    return np.array(pts)


def planar_fk(lengths, q) -> np.ndarray:
    """(x, y, phi) of the tip."""
    p = planar_points(lengths, q)[-1]
    return np.array([p[0], p[1], float(np.sum(q))])


def planar_jacobian(lengths, q, orientation: bool = False) -> np.ndarray:
    """
    Geometric Jacobian of the tip position (2 x n), or of (x, y, phi) (3 x n)
    when `orientation` is set. Column i = z x (p_tip - p_i) for revolute i.
    """
    pts = planar_points(lengths, q)
    tip = pts[-1]
    n = len(lengths)
    J = np.zeros((3 if orientation else 2, n))
    for i in range(n):
        r = tip - pts[i]
        J[0, i] = -r[1]
        J[1, i] = r[0]
        if orientation:
            J[2, i] = 1.0
    return J


def manipulability(J):
    """
    Velocity ellipsoid of v = J qdot for ||qdot|| = 1: principal axes are the
    left singular vectors, semi-axis lengths the singular values. Returns
    (axes, lengths, mu1 = sqrt(det JJ^T), condition number).
    """
    U, s, _ = np.linalg.svd(J)
    m = J.shape[0]
    s_full = np.zeros(m)
    s_full[:len(s)] = s
    mu = float(np.prod(s_full))
    cond = float(s_full[0] / s_full[-1]) if s_full[-1] > EPS else float("inf")
    return U, s_full, mu, cond


def ellipse_points(A, n: int = 120) -> np.ndarray:
    """Image of the unit circle under the 2x2 map A, as (n, 2)."""
    t = np.linspace(0, 2 * math.pi, n)
    return (A @ np.vstack([np.cos(t), np.sin(t)])).T


# ==========================================================================
# Chapter 6 -- inverse kinematics
# ==========================================================================

def ik_2r(L1: float, L2: float, x: float, y: float, elbow: int = 1):
    """Analytic 2R IK. elbow = +1 / -1 picks the branch. None if unreachable."""
    r2 = x * x + y * y
    c2 = (r2 - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    if c2 < -1 - 1e-12 or c2 > 1 + 1e-12:
        return None
    c2 = min(1.0, max(-1.0, c2))
    q2 = elbow * math.acos(c2)
    q1 = math.atan2(y, x) - math.atan2(L2 * math.sin(q2), L1 + L2 * math.cos(q2))
    return np.array([q1, q2])


def ik_newton(lengths, target, q0, max_iter: int = 50, tol: float = 1e-6,
              damping: float = 0.0):
    """
    Newton-Raphson on the tip position of a planar arm:
        q <- q + J^+ (x_d - f(q))      (damped least squares when damping > 0)
    Returns (q, history of q, history of error norm).
    """
    q = np.array(q0, float)
    target = np.asarray(target, float)
    qs, errs = [q.copy()], []
    for _ in range(max_iter):
        e = target - planar_points(lengths, q)[-1]
        errs.append(float(np.linalg.norm(e)))
        if errs[-1] < tol:
            break
        J = planar_jacobian(lengths, q)
        q = q + pinv_damped(J, damping) @ e
        qs.append(q.copy())
    else:
        e = target - planar_points(lengths, q)[-1]
        errs.append(float(np.linalg.norm(e)))
    return q, np.array(qs), np.array(errs)


def wrap(a):
    return (np.asarray(a) + math.pi) % (2 * math.pi) - math.pi


# ==========================================================================
# Redundancy and null space
# ==========================================================================

def pinv_damped(J, lam: float = 0.0, W=None) -> np.ndarray:
    """
    Right pseudo-inverse J^T (J J^T + lam^2 I)^-1, optionally weighted:
    J_W^+ = W^-1 J^T (J W^-1 J^T)^-1 minimises qdot^T W qdot.
    """
    J = np.asarray(J, float)
    Wi = np.eye(J.shape[1]) if W is None else np.linalg.inv(W)
    A = J @ Wi @ J.T + lam * lam * np.eye(J.shape[0])
    # pinv, not inv: at an exact singularity with lam = 0 the undamped
    # inverse does not exist, and the minimum-norm answer is what J^+ means.
    return Wi @ J.T @ np.linalg.pinv(A)


def null_projector(J, W=None) -> np.ndarray:
    """N = I - J^+ J. J N = 0, so N qdot0 moves the joints without moving x."""
    J = np.asarray(J, float)
    return np.eye(J.shape[1]) - pinv_damped(J, 0.0, W) @ J


# ==========================================================================
# Chapter 10 -- motion planning in C-space
# ==========================================================================

def _seg_circle(p, q, c, r) -> bool:
    d = q - p
    t = np.clip(np.dot(c - p, d) / max(np.dot(d, d), EPS), 0.0, 1.0)
    return np.linalg.norm(p + t * d - c) <= r


def collides_2r(L, q, obstacles) -> bool:
    pts = planar_points(L, q)
    for (cx, cy, r) in obstacles:
        c = np.array([cx, cy])
        for a, b in zip(pts[:-1], pts[1:]):
            if _seg_circle(a, b, c, r):
                return True
    return False


def cspace_grid_2r(L, obstacles, n: int = 90) -> np.ndarray:
    """Boolean occupancy over (q1, q2) in [-pi, pi)^2, row index = q1."""
    qs = np.linspace(-math.pi, math.pi, n, endpoint=False)
    G = np.zeros((n, n), bool)
    for i, a in enumerate(qs):
        for j, b in enumerate(qs):
            G[i, j] = collides_2r(L, (a, b), obstacles)
    return G


def astar(grid, start, goal, wrap_around: bool = True):
    """
    8-connected A* on a boolean grid (True = blocked). Joint angles wrap, so
    the C-space of a 2R arm is a torus and the planner is told so.
    Returns a list of (i, j) or None.
    """
    n, m = grid.shape
    if grid[start] or grid[goal]:
        return None

    def h(a):
        di = abs(a[0] - goal[0])
        dj = abs(a[1] - goal[1])
        if wrap_around:
            di, dj = min(di, n - di), min(dj, m - dj)
        return math.hypot(di, dj)

    openq = [(h(start), 0.0, start)]
    came = {start: None}
    cost = {start: 0.0}
    while openq:
        _, g, cur = heapq.heappop(openq)
        if cur == goal:
            path = [cur]
            while came[path[-1]] is not None:
                path.append(came[path[-1]])
            return path[::-1]
        if g > cost[cur] + 1e-12:
            continue
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                i, j = cur[0] + di, cur[1] + dj
                if wrap_around:
                    i, j = i % n, j % m
                elif not (0 <= i < n and 0 <= j < m):
                    continue
                if grid[i, j]:
                    continue
                ng = g + math.hypot(di, dj)
                if ng < cost.get((i, j), float("inf")):
                    cost[(i, j)] = ng
                    came[(i, j)] = cur
                    heapq.heappush(openq, (ng + h((i, j)), ng, (i, j)))
    return None


def rrt(is_free, start, goal, lo, hi, step: float = 0.15, iters: int = 3000,
        goal_bias: float = 0.1, seed: int = 0):
    """
    Plain RRT in a box. `is_free(q)` checks a configuration; edges are checked
    at a fixed resolution. Returns (path or None, tree nodes, parent indices).
    """
    rng = np.random.default_rng(seed)
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    nodes = [np.asarray(start, float)]
    parent = [-1]
    goal = np.asarray(goal, float)
    for _ in range(iters):
        sample = goal if rng.random() < goal_bias else lo + rng.random(len(lo)) * (hi - lo)
        d = np.linalg.norm(np.array(nodes) - sample, axis=1)
        k = int(np.argmin(d))
        direction = sample - nodes[k]
        dist = np.linalg.norm(direction)
        if dist < EPS:
            continue
        new = nodes[k] + direction / dist * min(step, dist)
        ok = all(is_free(nodes[k] + s * (new - nodes[k])) for s in np.linspace(0, 1, 6))
        if not ok:
            continue
        nodes.append(new)
        parent.append(k)
        if np.linalg.norm(new - goal) < step:
            nodes.append(goal.copy())
            parent.append(len(nodes) - 2)
            path = [len(nodes) - 1]
            while parent[path[-1]] != -1:
                path.append(parent[path[-1]])
            return np.array([nodes[i] for i in path[::-1]]), np.array(nodes), parent
    return None, np.array(nodes), parent


# ==========================================================================
# Chapter 12 -- grasping
# ==========================================================================

def contact_wrenches_planar(points, normals, mu: float) -> np.ndarray:
    """
    Primitive wrenches (m_z, f_x, f_y) of each friction-cone edge, one column
    each. A frictionless contact (mu = 0) contributes its normal only.
    """
    cols = []
    for p, n in zip(points, normals):
        n = np.asarray(n, float) / np.linalg.norm(n)
        t = np.array([-n[1], n[0]])
        edges = [n] if mu <= 0 else [n + mu * t, n - mu * t]
        for f in edges:
            cols.append([p[0] * f[1] - p[1] * f[0], f[0], f[1]])
    return np.array(cols).T


def force_closure_planar(W) -> bool:
    """
    Planar force closure: the columns of W positively span R^3. Equivalent to
    rank 3 and no nonzero n with n . w_k >= 0 for every k. Candidate n are
    the cross products of column pairs (the extreme rays of the dual cone).
    """
    W = np.asarray(W, float)
    if W.shape[1] < 4 or np.linalg.matrix_rank(W, tol=1e-9) < 3:
        return False
    k = W.shape[1]
    for i in range(k):
        for j in range(i + 1, k):
            n = np.cross(W[:, i], W[:, j])
            if np.linalg.norm(n) < 1e-12:
                continue
            for sgn in (1, -1):
                if np.all(sgn * n @ W >= -1e-10):
                    return False
    return True


# ==========================================================================
# Chapter 13 -- wheeled mobile robots
# ==========================================================================

def diff_drive_step(state, wl: float, wr: float, r: float, d: float, dt: float):
    """
    Unicycle/differential drive. Wheel radius r, half axle d. Body twist:
        v = r (wr + wl)/2,  omega = r (wr - wl)/(2d)
    The nonholonomic constraint  -sin(phi) xdot + cos(phi) ydot = 0  holds by
    construction: the robot cannot slide sideways.
    """
    x, y, phi = state
    v = r * (wr + wl) / 2
    w = r * (wr - wl) / (2 * d)
    return np.array([x + v * math.cos(phi) * dt,
                     y + v * math.sin(phi) * dt,
                     phi + w * dt])


def unicycle_track(path_fn, T: float, dt: float = 0.01, k: float = 2.0,
                   offset: float = 0.15, x0=(0.0, -0.4, 0.0)):
    """
    Follow a reference point with the 'look-ahead point' linearisation: the
    point a distance `offset` ahead of the axle IS fully actuated, so
        [v, w] = A(phi)^-1 (pdot_ref + k (p_ref - p))
    Returns times, robot states, reference points.
    """
    s = np.array(x0, float)
    ts = np.arange(0, T, dt)
    xs, refs = [], []
    for t in ts:
        pr, pdr = path_fn(t)
        x, y, phi = s
        p = np.array([x + offset * math.cos(phi), y + offset * math.sin(phi)])
        u = pdr + k * (pr - p)
        A = np.array([[math.cos(phi), -offset * math.sin(phi)],
                      [math.sin(phi), offset * math.cos(phi)]])
        v, w = np.linalg.solve(A, u)
        s = s + dt * np.array([v * math.cos(phi), v * math.sin(phi), w])
        xs.append(s.copy())
        refs.append(pr)
    return ts, np.array(xs), np.array(refs)
