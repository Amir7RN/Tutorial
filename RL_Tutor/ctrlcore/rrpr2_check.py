"""
Grader for C++ workshop 2 (page 131): statics, eigenvalues, manipulability,
inverse kinematics and the null space on the RRPR arm of page 125.

The learner's functions live in cpp/workshop/my_rrpr2.cpp and build on the
ready-made arm in rrpr_lib.hpp. Same machinery as rrpr_check (test main() that
prints "@@ tag numbers", compared with numpy references, known mistakes named);
the generic parts (Test, grade, parse_output, ...) are reused from there.
"""

from __future__ import annotations

import math
import os
import shutil

import numpy as np

from . import robokin as rk
from . import rrpr_check as rc
from .rrpr_check import (BUILD, ROOT, Result, Test, compile_command,
                         find_gxx, grade, marker_line, parse_output, shape_as)

STARTER = os.path.join(ROOT, "rrpr2_starter.cpp")
SOLUTION = os.path.join(ROOT, "rrpr2_solution.cpp")
WORKBOOK = os.path.join(ROOT, "my_rrpr2.cpp")
HARNESS = "harness2"
DEPS = ("mrlite.hpp", "rrpr_lib.hpp")

S_LIST, B_LIST, M_HOME = rc.S_LIST, rc.B_LIST, rc.M_HOME
P1, P2 = rc.POSES["P1"], rc.POSES["P2"]
G = 9.81

EXERCISES = {
    1: "statics: hold a payload",
    2: "determinant of a 3 × 3",
    3: "power iteration",
    4: "eigenvalues of a symmetric 3 × 3",
    5: "the linear half of J_b",
    6: "manipulability measures",
    7: "solve A x = b",
    8: "least squares / damped pseudoinverse",
    9: "matrix log of a pose",
    10: "Newton–Raphson IK",
    11: "null-space motion",
}

DEPENDS = {1: (), 2: (), 3: (), 4: (3,), 5: (), 6: (2, 4, 5), 7: (), 8: (7,),
           9: (), 10: (8, 9), 11: ()}


def blocking(ex: int, passed: dict) -> list[int]:
    seen, stack = set(), list(DEPENDS[ex])
    while stack:
        d = stack.pop()
        if d not in seen:
            seen.add(d)
            stack.extend(DEPENDS[d])
    return sorted(d for d in seen if not passed.get(d, False))


def ensure_workbook() -> str:
    os.makedirs(BUILD, exist_ok=True)
    if not os.path.exists(WORKBOOK):
        shutil.copyfile(STARTER, WORKBOOK)
    return WORKBOOK


def solution_block(ex: int) -> str:
    import re
    with open(SOLUTION, encoding="utf-8") as f:
        src = f.read()
    m = re.search(rf"// ==== ex{ex} ====\n(.*?)// ==== end ====", src, re.S)
    return m.group(1).strip("\n") if m else ""


def lit(kind: str, a) -> str:
    if kind == "Jac":
        return rc.lit("Jac", np.asarray(a, float).T)
    return rc.lit(kind, a)


# ---------------------------------------------------------------- references
def hold_payload(q, m):
    p = rk.fk_space(M_HOME, S_LIST, q)[:3, 3]
    f = np.array([0, 0, m * G])
    F = np.r_[np.cross(p, f), f]
    return rk.jacobian_space(S_LIST, q).T @ F


def linear_aat(Jb):
    Jv = Jb[3:]
    return Jv @ Jv.T


def manip(q, J=None):
    J = rk.jacobian_body(B_LIST, q) if J is None else J
    A = linear_aat(J)
    lam = np.sort(np.linalg.eigvalsh(A))[::-1]
    return np.array([math.sqrt(lam[0] / lam[2]), lam[0] / lam[2], math.sqrt(np.linalg.det(A))])


def log_twist(T):
    S, th = rk.log6(T)
    return S * th


def ik_newton(Tsd, guess):
    th = np.array(guess, float)
    for _ in range(100):
        Vb = log_twist(rk.inv_T(rk.fk_body(M_HOME, B_LIST, th)) @ Tsd)
        if np.linalg.norm(Vb[:3]) < 1e-10 and np.linalg.norm(Vb[3:]) < 1e-10:
            break
        J = rk.jacobian_body(B_LIST, th)
        th = th + np.linalg.solve(J.T @ J, J.T @ Vb)
    return th


def tool_point_jacobian(q):
    Js = rk.jacobian_space(S_LIST, q)
    p = rk.fk_space(M_HOME, S_LIST, q)[:3, 3]
    return np.array([Js[3:, i] + np.cross(Js[:3, i], p) for i in range(4)]).T


def null_motion(q, q0):
    Jp = tool_point_jacobian(q)
    return q0 - Jp.T @ np.linalg.solve(Jp @ Jp.T, Jp @ q0)


def _short(v) -> str:
    return "(" + ", ".join(f"{x:.3g}" for x in np.asarray(v, float)) + ")"


# ---------------------------------------------------------------- tests
SPD = (np.array([[4.0, 1.0, 0.5], [1.0, 3.0, 0.2], [0.5, 0.2, 1.0]]),
       np.array([[2.0, -0.6, 0.3], [-0.6, 1.5, 0.4], [0.3, 0.4, 0.6]]))
VTWIST = np.array([0.2, -0.1, 0.3, 0.5, -0.2, 0.1])


def build_tests() -> list[Test]:
    t: list[Test] = []

    # 1 -- statics
    for name, q, m in (("P1", P1, 2.0), ("P2", P2, 0.5)):
        exp = hold_payload(q, m)
        p = rk.fk_space(M_HOME, S_LIST, q)[:3, 3]
        f = np.array([0, 0, m * G])
        Js, Jb = rk.jacobian_space(S_LIST, q), rk.jacobian_body(B_LIST, q)
        t.append(Test(1, f"hold{name}", f"holdPayload({name}, {m} kg)",
                      f"holdPayload({lit('Joints', q)}, {m!r})", "vec", exp,
                      [(Js.T @ np.r_[np.zeros(3), f], "the moment part is missing: a force at p "
                        "also makes a moment p × f about the {s} origin. F_s = (p × f, f)."),
                       (Js.T @ np.r_[np.cross(f, p), f], "moment sign: it is p × f (arm first, then force)."),
                       (Jb.T @ np.r_[np.cross(p, f), f], "F_s is written in {s}, so it needs J_s, not J_b.")]))

    # 2 -- det3
    for k, A in enumerate((np.array([[2.0, -1.0, 0.5], [0.3, 1.5, -2.0], [1.0, 0.4, 0.7]]), SPD[0])):
        t.append(Test(2, f"det{k}", f"det3(A{k})", f"det3({lit('Mat3', A)})", "vec",
                      np.array([np.linalg.det(A)])))

    # 3 -- power iteration
    A = SPD[0]
    lam, V = np.linalg.eigh(A)
    v = V[:, -1]
    kmax = int(np.argmax(np.abs(v)))
    v = v * np.sign(v[kmax])
    t.append(Test(3, "plam", "powerIteration(A): λ", "[&]{ Vec3 v{1.0, 0.7, 0.4}; return powerIteration("
                  f"{lit('Mat3', A)}, v); }}()", "vec", np.array([lam[-1]])))
    t.append(Test(3, "pvec", "powerIteration(A): v (unit, sign fixed)",
                  f"[&]{{ Vec3 v{{1.0, 0.7, 0.4}}; powerIteration({lit('Mat3', A)}, v); "
                  f"if (v[{kmax}] < 0) v = -v; return v; }}()", "vec", v,
                  tol=1e-6))

    # 4 -- eigSym3
    for k, A in enumerate(SPD):
        lam = np.sort(np.linalg.eigvalsh(A))[::-1]
        t.append(Test(4, f"eig{k}", f"eigSym3(A{k})", f"eigSym3({lit('Mat3', A)})", "vec", lam,
                      [(lam[::-1], "the order is reversed: return the largest first.")]))

    # 5 -- linear half of J_b
    Jb1 = rk.jacobian_body(B_LIST, P1)
    Js1 = rk.jacobian_space(S_LIST, P1)
    t.append(Test(5, "aat", "linearAAT(J_b(P1))", f"linearAAT({lit('Jac', Jb1)})", "mat",
                  linear_aat(Jb1),
                  [(Jb1[:3] @ Jb1[:3].T, "these are the ANGULAR rows (0..2); the linear "
                    "velocity is rows 3..5.")]))

    # 6 -- manipulability
    for name, q in (("P1", P1), ("P2", P2)):
        exp = manip(q)
        Js = rk.jacobian_space(S_LIST, q)
        wr = manip(q, Js)
        t.append(Test(6, f"mu{name}", f"manipulability({name})", f"manipulability({lit('Joints', q)})",
                      "vec", exp,
                      [(wr, "you used J_s: its linear rows are the velocity of the point at the "
                        "{s} origin, not of the tool. Use J_b."),
                       (np.r_[exp[1], exp[1], exp[2]], "μ1 needs the square root: √(λmax/λmin)."),
                       (np.r_[exp[0], exp[1], exp[2] ** 2], "μ3 is √det A, not det A.")]))

    # 7 -- solve4
    A4 = np.array([[0.0, 2.0, 1.0, -1.0], [3.0, 1.0, 0.0, 2.0], [1.0, -1.0, 4.0, 0.5],
                   [2.0, 0.5, -1.0, 3.0]])
    b4 = np.array([1.0, -2.0, 0.5, 3.0])
    t.append(Test(7, "sol0", "solve4(A with A[0][0] = 0, b)", f"solve4({lit('Mat4', A4)}, "
                  f"{lit('Joints', b4)})", "vec", np.linalg.solve(A4, b4)))
    G4 = Jb1.T @ Jb1
    t.append(Test(7, "sol1", "solve4(J_bᵀJ_b, b)", f"solve4({lit('Mat4', G4)}, {lit('Joints', b4)})",
                  "vec", np.linalg.solve(G4, b4)))

    # 8 -- least squares
    for k, lamd in enumerate((0.0, 0.1)):
        exp = np.linalg.solve(Jb1.T @ Jb1 + lamd ** 2 * np.eye(4), Jb1.T @ VTWIST)
        wr = [(np.linalg.solve(Jb1.T @ Jb1 + lamd * np.eye(4), Jb1.T @ VTWIST),
               "the damping term is λ²I, not λI.")] if lamd else []
        t.append(Test(8, f"ls{k}", f"pinvSolve(J_b(P1), V, λ = {lamd})",
                      f"pinvSolve({lit('Jac', Jb1)}, {lit('Vec6', VTWIST)}, {lamd!r})", "vec", exp, wr))

    # 9 -- log
    T1 = rk.fk_space(M_HOME, S_LIST, P1)
    Tp = rk.rp_to_T(np.eye(3), [0.3, -0.5, 1.2])
    T3 = rk.exp6(rk.screw_axis([0.4, 0.1, 0], [0, 0.6, 0.8], 0.2), 0.9)
    for k, (T, name) in enumerate(((T1, "T_sb(P1)"), (Tp, "pure translation"), (T3, "pitch-0.2 screw, θ = 0.9"))):
        exp = log_twist(T)
        wr = []
        S, th = rk.log6(T)
        if th > 1e-9 and np.linalg.norm(S[:3]) > 0:
            wr.append((S, "that is the unit screw axis S; multiply by θ: return (ω̂θ, vθ)."))
            wr.append((np.r_[S[:3] * th, T[:3, 3]], "v is G⁻¹(θ)p times θ, not p itself."))
        t.append(Test(9, f"log{k}", f"logT({name})", f"logT({lit('Mat4', T)})", "vec", exp, wr))

    # 10 -- Newton IK
    for k, (qd, g0) in enumerate(((np.array([0.5, 0.6, 0.3, 0.8]), np.array([0.3, 0.4, 0.15, 0.5])),
                                  (P1, np.array([0.0, 0.2, 0.1, 0.0])))):
        Tsd = rk.fk_body(M_HOME, B_LIST, qd)
        exp = ik_newton(Tsd, g0)
        t.append(Test(10, f"ik{k}", f"ikNewton(T_sd = T({_short(qd)}), guess {_short(g0)})",
                      f"ikNewton({lit('Mat4', Tsd)}, {lit('Joints', g0)})", "vec", exp,
                      [(g0, "θ did not change: the loop never updated the guess.")], tol=1e-6))

    # 11 -- null space
    for k, q0 in enumerate((np.array([1.0, 0, 0, 0]), np.array([0.3, -0.2, 0.5, 1.0]))):
        exp = null_motion(P1, q0)
        Jp = tool_point_jacobian(P1)
        Js = rk.jacobian_space(S_LIST, P1)
        wrongJ = Js[3:]
        t.append(Test(11, f"null{k}", f"nullMotion(P1, q0 = {_short(q0)})",
                      f"nullMotion({lit('Joints', P1)}, {lit('Joints', q0)})", "vec", exp,
                      [(q0 - wrongJ.T @ np.linalg.solve(wrongJ @ wrongJ.T, wrongJ @ q0),
                        "you used the bottom rows of J_s as they are: that is the velocity of the "
                        "point at the {s} origin. Move it to the tool point: v + ω × p."),
                       (Jp.T @ np.linalg.solve(Jp @ Jp.T, Jp @ q0), "that is J⁺J q0, the part that "
                        "MOVES the tool. The null motion is q0 minus it.")]))
    return t


TESTS = build_tests()


def harness_source(workbook: str = WORKBOOK) -> str:
    """Test main(): no args runs every test; 8 numbers (θ_d, guess) run IK and μ."""
    inc = workbook.replace("\\", "/")
    body = "\n".join(f'    emit("{t.tag}", {t.call});' for t in TESTS)
    return f"""// generated by ctrlcore/rrpr2_check.py -- do not edit
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
void emit(const char* tag, double x) {{
    std::printf("@@ %s %.17g\\n", tag, x);
    std::fflush(stdout);
}}

int main(int argc, char** argv) {{
    if (argc == 9) {{
        Joints qd{{std::atof(argv[1]), std::atof(argv[2]), std::atof(argv[3]), std::atof(argv[4])}};
        Joints g{{std::atof(argv[5]), std::atof(argv[6]), std::atof(argv[7]), std::atof(argv[8])}};
        emit("pose_ik", ikNewton(fkBody(qd), g));
        emit("pose_mu", manipulability(g));
        return 0;
    }}
{body}
    std::printf("@@ done\\n");
    return 0;
}}
"""


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
