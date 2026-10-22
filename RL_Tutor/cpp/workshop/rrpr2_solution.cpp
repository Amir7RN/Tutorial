// rrpr2_solution.cpp -- reference answers for workshop 2 (page 131).
//
// The app shows one block at a time when you press "show solution"; each
// block sits between "// ==== exN" markers. Try the exercise first.
#include "rrpr_lib.hpp"

// ==== ex1 ====
Joints holdPayload(const Joints& th, double mass) {
    // the hand pushes UP on the payload with f = (0, 0, m g), applied at the tool point p;
    // as a wrench in {s}: F_s = (p × f, f).  τ = J_sᵀ F_s
    const double g = 9.81;
    const Vec3 f{0.0, 0.0, mass * g};
    const Vec3 p = toolPosition(th);
    const Vec6 Fs = stack(cross(p, f), f);
    const Jac J = jacobianSpace(th);
    Joints tau{};
    for (int i = 0; i < 4; ++i) tau[i] = dotN(J[i], Fs);
    return tau;
}
// ==== end ====

// ==== ex2 ====
double det3(const Mat3& A) {
    // expand along the first row
    return A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1])
         - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
         + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]);
}
// ==== end ====

// ==== ex3 ====
double powerIteration(const Mat3& A, Vec3& v) {
    // apply A again and again: every direction except the top eigenvector dies away
    v = (1.0 / norm(v)) * v;
    for (int k = 0; k < 2000; ++k) {
        const Vec3 w = A * v;
        const double n = norm(w);
        if (n < 1e-300) return 0.0;          // A v = 0: v is in the null space
        v = (1.0 / n) * w;
    }
    return dot(v, A * v);                     // Rayleigh quotient: λ = vᵀAv for a unit v
}
// ==== end ====

// ==== ex4 ====
Vec3 eigSym3(const Mat3& A) {
    // λ1 by power iteration; remove it (deflation) and repeat for λ2; trace gives λ3
    Vec3 v1{1.0, 0.7, 0.4};
    const double l1 = powerIteration(A, v1);
    Mat3 A2 = A;
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) A2[i][j] -= l1 * v1[i] * v1[j];
    Vec3 v2{-0.4, 1.0, 0.7};
    const double l2 = powerIteration(A2, v2);
    const double l3 = A[0][0] + A[1][1] + A[2][2] - l1 - l2;
    return {l1, l2, l3};
}
// ==== end ====

// ==== ex5 ====
Mat3 linearAAT(const Jac& Jb) {
    // J_bv = the bottom three rows of J_b (linear velocity, m/s);  A = J_bv J_bvᵀ
    Mat3 A{};
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 3; ++c)
            for (int i = 0; i < 4; ++i) A[r][c] += Jb[i][3 + r] * Jb[i][3 + c];
    return A;
}
// ==== end ====

// ==== ex6 ====
Vec3 manipulability(const Joints& th) {
    // linear-velocity ellipsoid of the tool:  μ1 = √(λmax/λmin), μ2 = λmax/λmin, μ3 = √det A
    const Mat3 A = linearAAT(jacobianBody(th));
    const Vec3 l = eigSym3(A);
    return {std::sqrt(l[0] / l[2]), l[0] / l[2], std::sqrt(det3(A))};
}
// ==== end ====

// ==== ex7 ====
Vec4 solve4(Mat4 A, Vec4 b) {
    // Gaussian elimination with partial pivoting, then back substitution
    for (int k = 0; k < 4; ++k) {
        int piv = k;
        for (int i = k + 1; i < 4; ++i)
            if (std::fabs(A[i][k]) > std::fabs(A[piv][k])) piv = i;
        std::swap(A[k], A[piv]);
        std::swap(b[k], b[piv]);
        for (int i = k + 1; i < 4; ++i) {
            const double m = A[i][k] / A[k][k];
            for (int j = k; j < 4; ++j) A[i][j] -= m * A[k][j];
            b[i] -= m * b[k];
        }
    }
    Vec4 x{};
    for (int i = 3; i >= 0; --i) {
        double s = b[i];
        for (int j = i + 1; j < 4; ++j) s -= A[i][j] * x[j];
        x[i] = s / A[i][i];
    }
    return x;
}
// ==== end ====

// ==== ex8 ====
Joints pinvSolve(const Jac& J, const Vec6& V, double lambda) {
    // tall J (6 x 4): least squares θ̇ = (JᵀJ + λ²I)⁻¹ JᵀV   (λ = 0: plain pseudoinverse)
    Mat4 G{};
    Vec4 r{};
    for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) G[i][j] = dotN(J[i], J[j]);
        G[i][i] += lambda * lambda;
        r[i] = dotN(J[i], V);
    }
    return solve4(G, r);
}
// ==== end ====

// ==== ex9 ====
Vec6 logT(const Mat4& T) {
    // the twist S·θ with e^{[S]θ} = T  (θ < π)
    const Mat3 R = rotPart(T);
    const Vec3 p = posPart(T);
    const double c = std::max(-1.0, std::min(1.0, (R[0][0] + R[1][1] + R[2][2] - 1.0) / 2.0));
    const double th = std::acos(c);
    if (th < 1e-9) return stack({0.0, 0.0, 0.0}, p);          // pure translation
    const Vec3 w = (1.0 / (2.0 * std::sin(th))) * unskew(R + (-1.0) * transpose(R));
    const Mat3 K = skew(w);
    const Mat3 Ginv = (1.0 / th) * eye<3>() + (-0.5) * K
                    + (1.0 / th - 0.5 / std::tan(th / 2.0)) * (K * K);
    return stack(th * w, th * (Ginv * p));
}
// ==== end ====

// ==== ex10 ====
Joints ikNewton(const Mat4& Tsd, const Joints& guess) {
    // θ ← θ + J_b⁺ V_b with [V_b] = log(T_sb⁻¹ T_sd), until V_b is tiny
    Joints th = guess;
    for (int k = 0; k < 100; ++k) {
        const Vec6 Vb = logT(invT(fkBody(th)) * Tsd);
        if (norm(top(Vb)) < 1e-10 && norm(bottom(Vb)) < 1e-10) break;
        const Joints d = pinvSolve(jacobianBody(th), Vb, 0.0);
        for (int i = 0; i < 4; ++i) th[i] += d[i];
    }
    return th;
}
// ==== end ====

// ==== ex11 ====
Joints nullMotion(const Joints& th, const Joints& q0) {
    // tool-point position Jacobian (3 x 4): column i = v_i + ω_i × p   (from J_s)
    const Jac Js = jacobianSpace(th);
    const Vec3 p = toolPosition(th);
    Mat<3, 4> Jp{};
    for (int i = 0; i < 4; ++i) {
        const Vec3 col = bottom(Js[i]) + cross(top(Js[i]), p);
        for (int r = 0; r < 3; ++r) Jp[r][i] = col[r];
    }
    // N q0 = q0 − Jpᵀ (Jp Jpᵀ)⁻¹ Jp q0
    const Vec3 y = inv3(Jp * transpose(Jp)) * (Jp * q0);
    const Vec4 back = transpose(Jp) * y;
    Joints out{};
    for (int i = 0; i < 4; ++i) out[i] = q0[i] - back[i];
    return out;
}
// ==== end ====
