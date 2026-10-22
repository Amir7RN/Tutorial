// rrpr_lib.hpp -- the RRPR arm, ready-made, for workshop 2 (page 131).
//
// Working versions of everything you wrote on page 125: skew, Rodrigues,
// transforms, the adjoint, e^[S]θ, both forward kinematics and both Jacobians.
// Workshop 2 builds on them, so it works even if your page-125 file is not
// finished. (They are the page-125 answers: finish that workshop first.)
//
// Extra helpers for this workshop: Vec4, dot for any length, outer products,
// inv3 (3x3 inverse) and toolPosition.
#pragma once
#include "mrlite.hpp"

using Vec4 = Vec<4>;                   // same type as Joints

template <std::size_t N>
inline double dotN(const Vec<N>& a, const Vec<N>& b) {
    double s = 0;
    for (std::size_t i = 0; i < N; ++i) s += a[i] * b[i];
    return s;
}
template <std::size_t N>
inline double normN(const Vec<N>& a) { return std::sqrt(dotN(a, a)); }

inline Mat3 skew(const Vec3& w) {
    return {{{0.0, -w[2], w[1]}, {w[2], 0.0, -w[0]}, {-w[1], w[0], 0.0}}};
}
inline Vec3 unskew(const Mat3& W) { return {W[2][1], W[0][2], W[1][0]}; }

inline Mat3 expRot(const Vec3& w, double th) {
    const Mat3 K = skew(w);
    return eye<3>() + std::sin(th) * K + (1.0 - std::cos(th)) * (K * K);
}

inline Mat4 makeT(const Mat3& R, const Vec3& p) {
    Mat4 T = eye<4>();
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) T[i][j] = R[i][j];
        T[i][3] = p[i];
    }
    return T;
}

inline Mat4 invT(const Mat4& T) {
    const Mat3 Rt = transpose(rotPart(T));
    return makeT(Rt, -(Rt * posPart(T)));
}

inline Mat6 adjoint(const Mat4& T) {
    const Mat3 R = rotPart(T), pR = skew(posPart(T)) * R;
    Mat6 A{};
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) {
            A[i][j] = R[i][j];
            A[i + 3][j + 3] = R[i][j];
            A[i + 3][j] = pR[i][j];
        }
    return A;
}

inline Mat4 expTwist(const Vec6& S, double th) {
    const Vec3 w = top(S), v = bottom(S);
    if (norm(w) < 1e-12) return makeT(eye<3>(), th * v);
    const Mat3 K = skew(w);
    const Mat3 G = th * eye<3>() + (1.0 - std::cos(th)) * K + (th - std::sin(th)) * (K * K);
    return makeT(expRot(w, th), G * v);
}

inline std::array<Vec6, 4> rrprScrewsSpace() {
    return {Vec6{0, 0, 1, 0, 0, 0}, Vec6{0, -1, 0, 1, 0, 0},
            Vec6{0, 0, 0, 1, 0, 0}, Vec6{1, 0, 0, 0, 1, 0}};
}

inline Mat4 rrprHome() {
    return makeT({{{1, 0, 0}, {0, -1, 0}, {0, 0, -1}}}, {1.5, 0.0, 0.8});
}

inline std::array<Vec6, 4> rrprScrewsBody() {
    const Mat6 A = adjoint(invT(rrprHome()));
    const auto S = rrprScrewsSpace();
    std::array<Vec6, 4> B{};
    for (int i = 0; i < 4; ++i) B[i] = A * S[i];
    return B;
}

inline Mat4 fkSpace(const Joints& th) {
    const auto S = rrprScrewsSpace();
    Mat4 T = eye<4>();
    for (int i = 0; i < 4; ++i) T = T * expTwist(S[i], th[i]);
    return T * rrprHome();
}

inline Mat4 fkBody(const Joints& th) {
    const auto B = rrprScrewsBody();
    Mat4 T = rrprHome();
    for (int i = 0; i < 4; ++i) T = T * expTwist(B[i], th[i]);
    return T;
}

inline Jac jacobianSpace(const Joints& th) {
    const auto S = rrprScrewsSpace();
    Jac J{};
    Mat4 T = eye<4>();
    for (int i = 0; i < 4; ++i) {
        J[i] = adjoint(T) * S[i];
        T = T * expTwist(S[i], th[i]);
    }
    return J;
}

inline Jac jacobianBody(const Joints& th) {
    const auto B = rrprScrewsBody();
    Jac J{};
    Mat4 T = eye<4>();
    for (int i = 3; i >= 0; --i) {
        J[i] = adjoint(T) * B[i];
        T = T * expTwist(-B[i], th[i]);
    }
    return J;
}

inline Vec3 toolPosition(const Joints& th) { return posPart(fkSpace(th)); }

inline Mat3 inv3(const Mat3& A) {
    // adjugate / determinant (fine for the well-conditioned 3x3s used here)
    Mat3 C{};
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) {
            const int r0 = (i + 1) % 3, r1 = (i + 2) % 3, c0 = (j + 1) % 3, c1 = (j + 2) % 3;
            C[j][i] = A[r0][c0] * A[r1][c1] - A[r0][c1] * A[r1][c0];   // transposed cofactor
        }
    const double det = A[0][0] * C[0][0] + A[0][1] * C[1][0] + A[0][2] * C[2][0];
    return (1.0 / det) * C;
}
