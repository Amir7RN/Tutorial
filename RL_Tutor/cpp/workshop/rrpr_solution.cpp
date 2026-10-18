// rrpr_solution.cpp -- reference answers for the RRPR workshop (page 125).
//
// The app shows one block at a time when you press "show solution"; each
// block sits between "// ==== exN" markers. Try the exercise first: typing a
// formula yourself and watching it fail is where the learning happens.
#include "mrlite.hpp"

// ==== ex1 ====
Mat3 skew(const Vec3& w) {
    return {{{0.0, -w[2], w[1]},
             {w[2], 0.0, -w[0]},
             {-w[1], w[0], 0.0}}};
}

Vec3 unskew(const Mat3& W) {
    return {W[2][1], W[0][2], W[1][0]};
}
// ==== end ====

// ==== ex2 ====
Mat3 expRot(const Vec3& omegaHat, double theta) {
    // Rodrigues: I + sin θ [ω̂] + (1 − cos θ) [ω̂]²
    const Mat3 K = skew(omegaHat);
    return eye<3>() + std::sin(theta) * K + (1.0 - std::cos(theta)) * (K * K);
}
// ==== end ====

// ==== ex3 ====
Mat4 makeT(const Mat3& R, const Vec3& p) {
    Mat4 T = eye<4>();
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) T[i][j] = R[i][j];
        T[i][3] = p[i];
    }
    return T;
}

Mat4 invT(const Mat4& T) {
    // (R, p)⁻¹ = (Rᵀ, −Rᵀp): no general 4x4 inverse needed
    const Mat3 Rt = transpose(rotPart(T));
    return makeT(Rt, -(Rt * posPart(T)));
}
// ==== end ====

// ==== ex4 ====
Vec6 revoluteAxis(const Vec3& omega, const Vec3& q) {
    // unit spin about the axis; the point at the origin moves with −ω × q
    return stack(omega, -cross(omega, q));
}

Vec6 prismaticAxis(const Vec3& v) {
    return stack({0.0, 0.0, 0.0}, v);
}

std::array<Vec6, 4> rrprScrewsSpace() {
    return {revoluteAxis({0, 0, 1}, {0, 0, 0}),     // waist
            revoluteAxis({0, -1, 0}, {0, 0, 1}),    // shoulder
            prismaticAxis({1, 0, 0}),               // telescoping slide
            revoluteAxis({1, 0, 0}, {1, 0, 1})};    // wrist roll
}

Mat4 rrprHome() {
    // tool frame 1.5 out, 0.8 up, its z-axis pointing down
    return makeT({{{1, 0, 0}, {0, -1, 0}, {0, 0, -1}}}, {1.5, 0.0, 0.8});
}
// ==== end ====

// ==== ex5 ====
Mat6 adjoint(const Mat4& T) {
    const Mat3 R = rotPart(T);
    const Mat3 pR = skew(posPart(T)) * R;
    Mat6 A{};
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) {
            A[i][j] = R[i][j];          // top-left      R
            A[i + 3][j + 3] = R[i][j];  // bottom-right  R
            A[i + 3][j] = pR[i][j];     // bottom-left   [p]R
        }
    return A;
}

std::array<Vec6, 4> rrprScrewsBody() {
    // the same axes, seen from the tool at home: Bᵢ = [Ad_{M⁻¹}] Sᵢ
    const Mat6 A = adjoint(invT(rrprHome()));
    const auto S = rrprScrewsSpace();
    std::array<Vec6, 4> B{};
    for (int i = 0; i < 4; ++i) B[i] = A * S[i];
    return B;
}
// ==== end ====

// ==== ex6 ====
Mat4 expTwist(const Vec6& S, double theta) {
    const Vec3 w = top(S), v = bottom(S);
    if (norm(w) < 1e-12)                       // prismatic: pure slide
        return makeT(eye<3>(), theta * v);
    const Mat3 K = skew(w);
    const Mat3 G = theta * eye<3>() + (1.0 - std::cos(theta)) * K
                 + (theta - std::sin(theta)) * (K * K);
    return makeT(expRot(w, theta), G * v);
}
// ==== end ====

// ==== ex7 ====
Mat4 fkSpace(const Joints& th) {
    // T = e^[S1]θ1 e^[S2]θ2 e^[S3]θ3 e^[S4]θ4 M   (M on the right)
    const auto S = rrprScrewsSpace();
    Mat4 T = eye<4>();
    for (int i = 0; i < 4; ++i) T = T * expTwist(S[i], th[i]);
    return T * rrprHome();
}

Mat4 fkBody(const Joints& th) {
    // T = M e^[B1]θ1 ... e^[B4]θ4   (M on the left)
    const auto B = rrprScrewsBody();
    Mat4 T = rrprHome();
    for (int i = 0; i < 4; ++i) T = T * expTwist(B[i], th[i]);
    return T;
}
// ==== end ====

// ==== ex8 ====
Jac jacobianSpace(const Joints& th) {
    // column i = Sᵢ carried by the joints BEFORE it
    const auto S = rrprScrewsSpace();
    Jac J{};
    Mat4 T = eye<4>();
    for (int i = 0; i < 4; ++i) {
        J[i] = adjoint(T) * S[i];
        T = T * expTwist(S[i], th[i]);
    }
    return J;
}

Jac jacobianBody(const Joints& th) {
    // column i = Bᵢ carried back by the joints AFTER it
    const auto B = rrprScrewsBody();
    Jac J{};
    Mat4 T = eye<4>();
    for (int i = 3; i >= 0; --i) {
        J[i] = adjoint(T) * B[i];
        T = T * expTwist(-B[i], th[i]);
    }
    return J;
}
// ==== end ====

// ==== ex9 ====
Vec6 handTwistSpace(const Joints& th, const Joints& thdot) {
    const Jac J = jacobianSpace(th);
    Vec6 V{};
    for (int i = 0; i < 4; ++i) V = V + thdot[i] * J[i];
    return V;
}

Joints jointTorques(const Joints& th, const Vec6& Fs) {
    // τ = J_sᵀ F_s: entry i is column i dotted with the wrench
    const Jac J = jacobianSpace(th);
    Joints tau{};
    for (int i = 0; i < 4; ++i)
        for (int k = 0; k < 6; ++k) tau[i] += J[i][k] * Fs[k];
    return tau;
}

Vec6 wrenchToBody(const Mat4& Tsb, const Vec6& Fs) {
    // F_b = [Ad_{T_sb}]ᵀ F_s   (wrenches move with the TRANSPOSE)
    return transpose(adjoint(Tsb)) * Fs;
}
// ==== end ====

// ==== ex10 ====
Vec6 twistFromFK(const Joints& th, const Joints& thdot) {
    // [V_s] = Ṫ T⁻¹, with Ṫ from a central difference along θ̇
    const double h = 1e-6;
    Joints a = th, b = th;
    for (int i = 0; i < 4; ++i) { a[i] += h * thdot[i]; b[i] -= h * thdot[i]; }
    const Mat4 Tdot = (1.0 / (2 * h)) * (fkSpace(a) - fkSpace(b));
    const Mat4 X = Tdot * invT(fkSpace(th));
    return {X[2][1], X[0][2], X[1][0], X[0][3], X[1][3], X[2][3]};
}
// ==== end ====
