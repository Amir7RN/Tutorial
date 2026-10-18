"""
Grader for the C++ RRPR workshop (page 125).

The learner's functions live in cpp/workshop/my_rrpr.cpp. This module writes a
test main() that calls them on fixed inputs and prints every result on one
"@@ tag numbers..." line, then compares each result with the Python reference
in ctrlcore.robokin. For a wrong answer it also tries a list of known mistakes
(transpose, sign of -w x q, M on the wrong side, off-by-one Jacobian column,
...) and, when one matches, says which.

No Qt here: the page drives compiling and running; the tests drive this module
directly with the reference solution.
"""

from __future__ import annotations

import math
import os
import re
import shutil
from dataclasses import dataclass, field

import numpy as np

from . import robokin as rk

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "cpp", "workshop"))
STARTER = os.path.join(ROOT, "rrpr_starter.cpp")
SOLUTION = os.path.join(ROOT, "rrpr_solution.cpp")
WORKBOOK = os.path.join(ROOT, "my_rrpr.cpp")
BUILD = os.path.join(ROOT, "build")

# ---------------------------------------------------------------- the robot
S_LIST = np.array([
    rk.screw_axis([0, 0, 0], [0, 0, 1]),
    rk.screw_axis([0, 0, 1], [0, -1, 0]),
    [0, 0, 0, 1, 0, 0],
    rk.screw_axis([1, 0, 1], [1, 0, 0]),
], float).T
M_HOME = rk.rp_to_T(np.diag([1.0, -1.0, -1.0]), [1.5, 0, 0.8])
B_LIST = rk.adjoint(rk.inv_T(M_HOME)) @ S_LIST
JOINT_NAMES = ("θ1 waist", "θ2 shoulder", "d3 slide", "θ4 roll")

POSES = {
    "P1": np.array([0.3, 0.5, 0.2, -0.4]),
    "P2": np.array([-1.0, 1.2, 0.5, 2.0]),
}
QDOT = np.array([0.5, -0.3, 0.2, 1.0])
WRENCH = np.array([0.1, -0.2, 0.3, 1.0, 2.0, -3.0])

EXERCISES = {
    1: "skew and unskew",
    2: "Rodrigues: expRot",
    3: "transforms: makeT, invT",
    4: "screw axes and M",
    5: "adjoint and body axes",
    6: "exponential of a twist",
    7: "forward kinematics",
    8: "space and body Jacobians",
    9: "twist, torques, wrench",
    10: "finite-difference check",
}


# which earlier exercises each one calls: a failure there cascades here
DEPENDS = {1: (), 2: (1,), 3: (), 4: (3,), 5: (1, 3, 4), 6: (1, 2, 3),
           7: (4, 5, 6), 8: (4, 5, 6), 9: (3, 5, 8), 10: (3, 7)}


def blocking(ex: int, passed: dict) -> list[int]:
    """Earlier exercises (direct or indirect) that `ex` relies on and that fail."""
    seen, stack = set(), list(DEPENDS[ex])
    while stack:
        d = stack.pop()
        if d not in seen:
            seen.add(d)
            stack.extend(DEPENDS[d])
    return sorted(d for d in seen if not passed.get(d, False))


def fk_points(q):
    """Base, shoulder, wrist (start of joint 4) and tool position in {s}."""
    q = np.asarray(q, float)
    T3 = np.eye(4)
    for i in range(3):
        T3 = T3 @ rk.exp6(S_LIST[:, i], q[i])
    wrist = T3[:3, :3] @ np.array([1.0, 0, 1]) + T3[:3, 3]
    T = rk.fk_space(M_HOME, S_LIST, q)
    return np.array([[0, 0, 0], [0, 0, 1.0], wrist, T[:3, 3]])


def find_gxx():
    for name in ("g++", "g++.exe"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\mingw64\bin\g++.exe", r"C:\msys64\ucrt64\bin\g++.exe",
              r"C:\msys64\mingw64\bin\g++.exe", "/usr/bin/g++"):
        if os.path.exists(p):
            return p
    return None


def ensure_workbook() -> str:
    os.makedirs(BUILD, exist_ok=True)
    if not os.path.exists(WORKBOOK):
        shutil.copyfile(STARTER, WORKBOOK)
    return WORKBOOK


def solution_block(ex: int) -> str:
    """The reference code for one exercise, cut from rrpr_solution.cpp."""
    with open(SOLUTION, encoding="utf-8") as f:
        src = f.read()
    m = re.search(rf"// ==== ex{ex} ====\n(.*?)// ==== end ====", src, re.S)
    return m.group(1).strip("\n") if m else ""


def marker_line(src: str, ex: int) -> int:
    """0-based line of '// ==== exN' in a workbook, or -1."""
    for i, line in enumerate(src.splitlines()):
        if line.startswith(f"// ==== ex{ex} ===="):
            return i
    return -1


# ---------------------------------------------------------------- C++ text
def _num(x) -> str:
    return repr(float(x))


def lit(kind: str, a) -> str:
    a = np.asarray(a, float)
    if kind in ("Vec3", "Vec6", "Joints"):
        return f"{kind}{{{', '.join(_num(x) for x in a)}}}"
    rows = ", ".join("{" + ", ".join(_num(x) for x in r) + "}" for r in a)
    return f"{kind}{{{{{rows}}}}}"


# ---------------------------------------------------------------- the tests
@dataclass
class Test:
    ex: int
    tag: str
    label: str
    call: str               # C++ expression
    kind: str               # vec | mat | cols (6 x 4 stored by column)
    expected: np.ndarray
    wrongs: list = field(default_factory=list)   # (array, message)
    tol: float = 1e-6


def _exps(screws, q, sign=1.0, order=None):
    T = np.eye(4)
    for i in (order if order is not None else range(len(q))):
        T = T @ rk.exp6(sign * screws[:, i], q[i])
    return T


def _js_offbyone(q):
    J = np.zeros((6, 4))
    for i in range(4):
        J[:, i] = rk.adjoint(_exps(S_LIST, q, order=range(i + 1))) @ S_LIST[:, i]
    return J


def _jb_positive(q):
    J = np.zeros((6, 4))
    for i in range(4):
        J[:, i] = rk.adjoint(_exps(B_LIST, q, order=range(3, i, -1))) @ B_LIST[:, i]
    return J


def _jb_offbyone(q):
    J = np.zeros((6, 4))
    for i in range(4):
        J[:, i] = rk.adjoint(_exps(B_LIST, q, -1.0, order=range(3, i - 1, -1))) @ B_LIST[:, i]
    return J


def _rodrigues_variants(w, th):
    K = rk.skew(w)
    I = np.eye(3)
    s, c = math.sin(th), math.cos(th)
    return [
        (I + s * K, "the (1 − cos θ)[ω̂]² term is missing."),
        (I + s * K - (1 - c) * K @ K, "the [ω̂]² term needs a plus sign: I + sin θ[ω̂] + (1 − cos θ)[ω̂]²."),
        (I + s * K + (1 - c) * K, "the last term uses [ω̂]², the square of the skew matrix, not [ω̂]."),
        (I + c * K + (1 - s) * K @ K, "sin and cos are swapped."),
    ]


def build_tests() -> list[Test]:
    t: list[Test] = []
    P1, P2 = POSES["P1"], POSES["P2"]

    # 1 -- skew / unskew
    for k, w in enumerate(([1, 2, 3], [-0.5, 0.2, 0.9])):
        t.append(Test(1, f"skew{k}", f"skew({_short(w)})", f"skew({lit('Vec3', w)})",
                      "mat", rk.skew(w)))
    W = rk.skew([0.3, -1.0, 2.0])
    t.append(Test(1, "unskew", "unskew([(0.3, −1, 2)])", f"unskew({lit('Mat3', W)})",
                  "vec", np.array([0.3, -1.0, 2.0]),
                  [(-np.array([0.3, -1.0, 2.0]), "every sign is flipped: read the entries "
                    "ω₁ = W[2][1], ω₂ = W[0][2], ω₃ = W[1][0] (below / above / below the diagonal).")]))

    # 2 -- Rodrigues
    for k, (w, th) in enumerate((([0, 0, 1], math.pi / 2),
                                 (np.ones(3) / math.sqrt(3), 2.0),
                                 ([0.6, 0, 0.8], -1.2),
                                 ([0, 1, 0], 0.0))):
        w = np.asarray(w, float)
        t.append(Test(2, f"rod{k}", f"expRot({_short(w)}, {th:.3g})",
                      f"expRot({lit('Vec3', w)}, {_num(th)})", "mat",
                      rk.rot_exp(w * th), _rodrigues_variants(w, th)))

    # 3 -- transforms
    R = rk.rot_exp([0.3, -0.2, 0.5])
    p = np.array([1.0, -2.0, 0.5])
    T = rk.rp_to_T(R, p)
    t.append(Test(3, "makeT", "makeT(R, (1, −2, 0.5))", f"makeT({lit('Mat3', R)}, {lit('Vec3', p)})",
                  "mat", T, [(T.T, "p went into the bottom row; it belongs in the last column, "
                              "and the bottom row is (0, 0, 0, 1).")]))
    t.append(Test(3, "invT", "invT(T)", f"invT({lit('Mat4', T)})", "mat", rk.inv_T(T),
                  [(rk.rp_to_T(R.T, -p), "the position part must be −Rᵀp, not −p: "
                    "undo the rotation before undoing the shift."),
                   (rk.rp_to_T(R.T, -R @ p), "use Rᵀ, not R, on p: −Rᵀp."),
                   (rk.rp_to_T(R.T, R.T @ p), "missing minus sign: −Rᵀp."),
                   (rk.rp_to_T(R, -R.T @ p), "the rotation block of T⁻¹ is Rᵀ, not R.")]))

    # 4 -- screw axes, M
    for k, (w, q) in enumerate((([0, 0, 1], [1, 2, 0]), ([0.6, 0.8, 0], [0.5, -1, 2]))):
        S = rk.screw_axis(q, w)
        t.append(Test(4, f"rev{k}", f"revoluteAxis(ω={_short(w)}, q={_short(q)})",
                      f"revoluteAxis({lit('Vec3', w)}, {lit('Vec3', q)})", "vec", S,
                      [(np.r_[w, np.cross(w, q)], "sign of v: v = −ω × q (equivalently q × ω). "
                        "Picture the origin's velocity when the body spins about an axis through q.")]))
    t.append(Test(4, "pri", "prismaticAxis((0, 0.6, 0.8))",
                  f"prismaticAxis({lit('Vec3', [0, 0.6, 0.8])})", "vec",
                  np.array([0, 0, 0, 0, 0.6, 0.8])))
    t.append(Test(4, "Sspace", "rrprScrewsSpace()", "rrprScrewsSpace()", "cols", S_LIST))
    t.append(Test(4, "M", "rrprHome()", "rrprHome()", "mat", M_HOME,
                  [(rk.rp_to_T(np.eye(3), [1.5, 0, 0.8]), "the position is right, but the "
                    "tool's z-axis points down: R = diag(1, −1, −1).")]))

    # 5 -- adjoint, body axes
    Ad = rk.adjoint(T)
    wrong_rp = Ad.copy()
    wrong_rp[3:, :3] = R @ rk.skew(p)
    wrong_tr = np.zeros((6, 6))
    wrong_tr[:3, :3] = R
    wrong_tr[3:, 3:] = R
    wrong_tr[:3, 3:] = rk.skew(p) @ R
    t.append(Test(5, "adj", "adjoint(T)", f"adjoint({lit('Mat4', T)})", "mat", Ad,
                  [(wrong_rp, "the bottom-left block is [p]R (skew first, then R), not R[p]."),
                   (wrong_tr, "[p]R belongs bottom-left, under R, not top-right.")]))
    t.append(Test(5, "Sbody", "rrprScrewsBody()", "rrprScrewsBody()", "cols", B_LIST,
                  [(rk.adjoint(M_HOME) @ S_LIST, "you used [Ad_M]; to see the axes from the "
                    "tool you need [Ad_{M⁻¹}] = [Ad_{T_bs}]."),
                   (S_LIST, "these are the space axes Sᵢ unchanged; apply [Ad_{M⁻¹}].")]))

    # 6 -- exponential of a twist
    pitched = rk.screw_axis([0.2, 0.1, 0], [0, 0, 1], 0.1)
    for k, (S, th, name) in enumerate(((S_LIST[:, 1], 0.7, "S2, θ = 0.7"),
                                       (S_LIST[:, 2], 0.35, "S3 (prismatic), θ = 0.35"),
                                       (S_LIST[:, 3], -1.1, "S4, θ = −1.1"),
                                       (pitched, 1.3, "pitch-0.1 screw, θ = 1.3"),
                                       (S_LIST[:, 0], 0.0, "S1, θ = 0"))):
        E = rk.exp6(S, th)
        w, v = S[:3], S[3:]
        K = rk.skew(w)
        wr = []
        if np.linalg.norm(w) > 0:
            wr.append((rk.rp_to_T(E[:3, :3], v * th), "for a revolute (ω ≠ 0) the "
                       "translation is G(θ)v, not vθ: the origin moves on an arc, not a line."))
            G2 = np.eye(3) * th + (1 - math.cos(th)) * K
            wr.append((rk.rp_to_T(E[:3, :3], G2 @ v), "G(θ) is missing (θ − sin θ)[ω]²."))
            wr.append((rk.rp_to_T(E[:3, :3].T, E[:3, 3]), "the rotation block is transposed "
                       "(sign of the sin θ term in Rodrigues)."))
        t.append(Test(6, f"exp{k}", f"expTwist({name})", f"expTwist({lit('Vec6', S)}, {_num(th)})",
                      "mat", E, wr))

    # 7 -- FK
    for name, q in (("P1", P1), ("P2", P2), ("home", np.zeros(4))):
        T_ok = rk.fk_space(M_HOME, S_LIST, q)
        t.append(Test(7, f"fks{name}", f"fkSpace({name} = {_short(q)})", f"fkSpace({lit('Joints', q)})",
                      "mat", T_ok,
                      [(M_HOME @ _exps(S_LIST, q), "M must go on the RIGHT in the space form: "
                        "e^{[S1]θ1} ⋯ e^{[S4]θ4} M."),
                       (_exps(S_LIST, q, order=range(3, -1, -1)) @ M_HOME, "the exponentials are "
                        "in reverse order; joint 1 (nearest the base) comes first, on the left.")]))
    for name, q in (("P1", P1), ("P2", P2)):
        t.append(Test(7, f"fkb{name}", f"fkBody({name})", f"fkBody({lit('Joints', q)})", "mat",
                      rk.fk_body(M_HOME, B_LIST, q),
                      [(M_HOME @ _exps(S_LIST, q), "body form uses the body axes Bᵢ, not Sᵢ."),
                       (_exps(B_LIST, q) @ M_HOME, "in body form M goes on the LEFT: "
                        "M e^{[B1]θ1} ⋯ e^{[B4]θ4}.")]))

    # 8 -- Jacobians
    for name, q in (("P1", P1), ("P2", P2)):
        Js = rk.jacobian_space(S_LIST, q)
        Jb = rk.jacobian_body(B_LIST, q)
        t.append(Test(8, f"js{name}", f"jacobianSpace({name})", f"jacobianSpace({lit('Joints', q)})",
                      "cols", Js,
                      [(_js_offbyone(q), "off by one: column i must be carried by the joints "
                        "BEFORE joint i only. Update T after using it, not before."),
                       (Jb, "this is the body Jacobian J_b; the space one uses Sᵢ and [Ad] of "
                        "the exponentials before joint i."),
                       (S_LIST, "every column is still Sᵢ at home: the joints before each "
                        "axis have to carry it with [Ad_{e^{[S1]θ1}⋯}].")]))
        t.append(Test(8, f"jb{name}", f"jacobianBody({name})", f"jacobianBody({lit('Joints', q)})",
                      "cols", Jb,
                      [(_jb_positive(q), "use e^{−[B]θ} (minus sign) for the joints after "
                        "joint i: you are undoing them to look back from the hand."),
                       (_jb_offbyone(q), "off by one: only the joints AFTER joint i carry "
                        "column i; joint i itself must not."),
                       (Js, "this is the space Jacobian J_s."),
                       (B_LIST, "every column is still Bᵢ at home.")]))

    # 9 -- twist, torques, wrench
    Js1 = rk.jacobian_space(S_LIST, P1)
    Jb1 = rk.jacobian_body(B_LIST, P1)
    Tsb = rk.fk_space(M_HOME, S_LIST, P1)
    t.append(Test(9, "Vs", "handTwistSpace(P1, θ̇)",
                  f"handTwistSpace({lit('Joints', P1)}, {lit('Joints', QDOT)})", "vec", Js1 @ QDOT,
                  [(Jb1 @ QDOT, "this is V_b = J_b θ̇; use J_s.")]))
    t.append(Test(9, "tau", "jointTorques(P1, F_s)",
                  f"jointTorques({lit('Joints', P1)}, {lit('Vec6', WRENCH)})", "vec", Js1.T @ WRENCH,
                  [(Jb1.T @ WRENCH, "you used J_b with a wrench written in {s}: frames must match "
                    "(J_sᵀ F_s or J_bᵀ F_b).")]))
    Ad_sb = rk.adjoint(Tsb)
    t.append(Test(9, "Fb", "wrenchToBody(T_sb(P1), F_s)",
                  f"wrenchToBody({lit('Mat4', Tsb)}, {lit('Vec6', WRENCH)})", "vec", Ad_sb.T @ WRENCH,
                  [(Ad_sb @ WRENCH, "missing transpose: wrenches move with [Ad]ᵀ, twists with [Ad]."),
                   (rk.adjoint(rk.inv_T(Tsb)) @ WRENCH, "that is how a TWIST moves from {s} to {b}; "
                    "a wrench uses F_b = [Ad_{T_sb}]ᵀ F_s, so power Vᵀ F stays the same."),
                   (rk.adjoint(rk.inv_T(Tsb)).T @ WRENCH, "right idea, wrong transform: use "
                    "T_sb, not T_bs, inside [Ad]ᵀ.")]))

    # 10 -- finite differences
    for name, q in (("P1", P1), ("P2", P2)):
        Vs = rk.jacobian_space(S_LIST, q) @ QDOT
        Vb = rk.jacobian_body(B_LIST, q) @ QDOT
        t.append(Test(10, f"fd{name}", f"twistFromFK({name}, θ̇)",
                      f"twistFromFK({lit('Joints', q)}, {lit('Joints', QDOT)})", "vec", Vs,
                      [(Vb, "you computed T⁻¹Ṫ = [V_b]. The space twist is Ṫ T⁻¹ (T⁻¹ on the right).")],
                      tol=1e-5))
    return t


def _short(v) -> str:
    return "(" + ", ".join(f"{x:.3g}" for x in np.asarray(v, float)) + ")"


TESTS = build_tests()


def harness_source(workbook: str = WORKBOOK) -> str:
    """Test main(): no args runs every test; 4 numbers print FK and J at that pose."""
    inc = workbook.replace("\\", "/")
    body = "\n".join(f'    emit("{t.tag}", {t.call});' for t in TESTS)
    return f"""// generated by ctrlcore/rrpr_check.py -- do not edit
#define RRPR_TEST_HARNESS
#include "{inc}"
#include <cstdio>
#include <cstdlib>

template <std::size_t N>
void emit(const char* tag, const Vec<N>& v) {{
    std::printf("@@ %s", tag);
    for (double x : v) std::printf(" %.17g", x);
    std::printf("\\n");
    std::fflush(stdout);
}}
template <std::size_t R, std::size_t C>
void emit(const char* tag, const Mat<R, C>& A) {{
    std::printf("@@ %s", tag);
    for (const auto& row : A) for (double x : row) std::printf(" %.17g", x);
    std::printf("\\n");
    std::fflush(stdout);
}}

int main(int argc, char** argv) {{
    if (argc == 5) {{
        Joints q{{std::atof(argv[1]), std::atof(argv[2]), std::atof(argv[3]), std::atof(argv[4])}};
        emit("pose_fks", fkSpace(q));
        emit("pose_fkb", fkBody(q));
        emit("pose_js", jacobianSpace(q));
        emit("pose_jb", jacobianBody(q));
        return 0;
    }}
{body}
    std::printf("@@ done\\n");
    return 0;
}}
"""


def compile_command(gxx: str, harness: str, exe: str) -> list[str]:
    return [gxx, "-std=c++17", "-O1", "-fdiagnostics-color=never", f"-I{ROOT}",
            "-static-libgcc", "-static-libstdc++", harness, "-o", exe]


# ---------------------------------------------------------------- grading
def parse_output(text: str) -> tuple[dict, str]:
    """{tag: array} from '@@' lines, plus everything else the program printed."""
    vals, other = {}, []
    for line in text.splitlines():
        if line.startswith("@@ "):
            parts = line[3:].split()
            if parts:
                try:
                    vals[parts[0]] = np.array([float(x) for x in parts[1:]])
                except ValueError:
                    vals[parts[0]] = np.array([math.nan])
        else:
            other.append(line)
    return vals, "\n".join(other)


def shape_as(kind: str, raw: np.ndarray, expected: np.ndarray):
    if raw.size != expected.size:
        return None
    if kind == "cols":
        return raw.reshape(expected.shape[1], expected.shape[0]).T
    return raw.reshape(expected.shape)


def _close(a, b, tol):
    return a.shape == b.shape and np.all(np.isfinite(a)) and \
        float(np.max(np.abs(a - b))) <= tol * (1 + float(np.max(np.abs(b))))


@dataclass
class Result:
    test: Test
    ok: bool
    got: np.ndarray | None
    err: float
    why: str


def grade(test: Test, got) -> Result:
    exp = test.expected
    if got is None:
        return Result(test, False, None, math.inf,
                      "no output: the program stopped before this test (crash or infinite loop?).")
    if not np.all(np.isfinite(got)):
        return Result(test, False, got, math.inf,
                      "NaN or inf: a division by zero? (e.g. normalising ω = 0 for the "
                      "prismatic joint, or θ = 0).")
    err = float(np.max(np.abs(got - exp)))
    if _close(got, exp, test.tol):
        return Result(test, True, got, err, "")
    if not np.any(got):
        return Result(test, False, got, err, "all zeros: still the TODO stub.")
    for wrong, msg in test.wrongs:
        if _close(got, np.asarray(wrong, float), 1e-6):
            return Result(test, False, got, err, msg)
    # generic patterns
    if exp.ndim == 2 and exp.shape[0] == exp.shape[1] and _close(got, exp.T, 1e-6):
        return Result(test, False, got, err, "you returned the transpose: check row vs column "
                      "indexing (A[row][col]).")
    if _close(got, -exp, 1e-6):
        return Result(test, False, got, err, "every sign is flipped.")
    if exp.shape == (6,) and _close(np.r_[got[3:], got[:3]], exp, 1e-6):
        return Result(test, False, got, err, "the two halves are swapped: twists are (ω, v) and "
                      "wrenches (m, f), angular part first.")
    if test.kind == "cols":
        good = [i + 1 for i in range(exp.shape[1]) if _close(got[:, i], exp[:, i], test.tol)]
        bad = [i + 1 for i in range(exp.shape[1]) if i + 1 not in good]
        if good:
            return Result(test, False, got, err, f"columns {good} are right; columns {bad} are "
                          "not. Compare them with the formula for those joints.")
    if exp.shape == (4, 4):
        rot_ok = _close(got[:3, :3], exp[:3, :3], test.tol)
        pos_ok = _close(got[:3, 3], exp[:3, 3], test.tol)
        if rot_ok and not pos_ok:
            return Result(test, False, got, err, "the rotation block is right; the position "
                          "column is wrong.")
        if pos_ok and not rot_ok:
            return Result(test, False, got, err, "the position is right; the rotation block "
                          "is wrong.")
    return Result(test, False, got, err, "")


def grade_all(vals: dict) -> list[Result]:
    out = []
    for t in TESTS:
        raw = vals.get(t.tag)
        got = None if raw is None else shape_as(t.kind, raw, t.expected)
        if raw is not None and got is None:
            out.append(Result(t, False, None, math.inf, f"wrong size: got {raw.size} numbers."))
        else:
            out.append(grade(t, got))
    return out
