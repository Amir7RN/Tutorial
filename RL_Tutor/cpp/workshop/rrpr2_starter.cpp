// my_rrpr2.cpp -- YOUR workbook for workshop 2 (page 131): statics,
// eigenvalues, manipulability, inverse kinematics and the null space.
//
// Same RRPR arm as page 125. rrpr_lib.hpp gives you working versions of
// fkSpace, fkBody, jacobianSpace, jacobianBody, adjoint, invT, makeT, skew,
// unskew, expRot, expTwist, toolPosition, inv3 (3x3 inverse), dotN/normN
// (dot and length of any Vec<N>) and Vec4 (= Joints).
//
// Jac J stores the 6 x 4 Jacobian BY COLUMN: J[i] is column i, J[i][k] is
// row k of it (k = 0..2 angular, 3..5 linear).
//
// Fill in the TODOs one exercise at a time, then press "check my code".
// Build and run your own main() below from the project folder:
//   g++ -std=c++17 -I cpp/workshop cpp/workshop/my_rrpr2.cpp -o cpp/workshop/build/play2.exe
//   ./cpp/workshop/build/play2.exe
#include "rrpr_lib.hpp"

// ==== ex1 ====  statics (page 126)
Joints holdPayload(const Joints& th, double mass) {
    // TODO: joint torques that hold a payload of `mass` kg at the tool point.
    //       The hand pushes up with f = (0, 0, m g), g = 9.81, at p = toolPosition(th).
    //       Wrench in {s}: F_s = (p × f, f).  Then τ = J_sᵀ F_s.
    return Joints{};
}
// ==== end ====

// ==== ex2 ====  determinant (pages 126-127)
double det3(const Mat3& A) {
    // TODO: the determinant of a 3x3 (cofactor expansion along row 0)
    return 0.0;
}
// ==== end ====

// ==== ex3 ====  the top eigenvector by repetition (page 127)
double powerIteration(const Mat3& A, Vec3& v) {
    // TODO: v comes in as a starting guess. Repeat 2000 times: v = A v / |A v|.
    //       Return λ = vᵀ A v (v is unit length by then). v goes out as the eigenvector.
    return 0.0;
}
// ==== end ====

// ==== ex4 ====  all three eigenvalues of a symmetric PSD 3x3 (page 127)
Vec3 eigSym3(const Mat3& A) {
    // TODO: λ1 = powerIteration(A, v1) from v1 = (1, 0.7, 0.4).
    //       Deflate: A2 = A − λ1 v1 v1ᵀ, then λ2 = powerIteration(A2, v2) from v2 = (−0.4, 1, 0.7).
    //       λ3 = trace(A) − λ1 − λ2.   Return (λ1, λ2, λ3), largest first.
    return Vec3{};
}
// ==== end ====

// ==== ex5 ====  the linear half of J_b (page 128)
Mat3 linearAAT(const Jac& Jb) {
    // TODO: J_bv = rows 3..5 of J_b (the tool's linear velocity, m/s), a 3 x 4 matrix.
    //       Return A = J_bv J_bvᵀ (3 x 3).
    return Mat3{};
}
// ==== end ====

// ==== ex6 ====  the three manipulability measures (page 128)
Vec3 manipulability(const Joints& th) {
    // TODO: A = linearAAT(jacobianBody(th)), λ = eigSym3(A).
    //       Return (μ1, μ2, μ3) = (√(λ1/λ3), λ1/λ3, √det A).
    return Vec3{};
}
// ==== end ====

// ==== ex7 ====  solving A x = b (the tool for every inverse)
Vec4 solve4(Mat4 A, Vec4 b) {
    // TODO: Gaussian elimination with partial pivoting, then back substitution.
    return Vec4{};
}
// ==== end ====

// ==== ex8 ====  least squares with a tall Jacobian (pages 129-130)
Joints pinvSolve(const Jac& J, const Vec6& V, double lambda) {
    // TODO: θ̇ = (JᵀJ + λ²I)⁻¹ JᵀV.  JᵀJ is 4 x 4: entry (i, j) = column i · column j.
    return Joints{};
}
// ==== end ====

// ==== ex9 ====  matrix log of a pose (page 129)
Vec6 logT(const Mat4& T) {
    // TODO: return S·θ with e^{[S]θ} = T.   θ = acos((tr R − 1)/2).
    //       θ ≈ 0: (0, 0, 0, p).  Else [ω̂] = (R − Rᵀ)/(2 sin θ),
    //       G⁻¹ = I/θ − [ω̂]/2 + (1/θ − cot(θ/2)/2)[ω̂]²,  v = G⁻¹p.  Return (ω̂θ, vθ).
    return Vec6{};
}
// ==== end ====

// ==== ex10 ====  Newton–Raphson inverse kinematics (page 129)
Joints ikNewton(const Mat4& Tsd, const Joints& guess) {
    // TODO: up to 100 times: V_b = logT(invT(fkBody(θ)) * Tsd);
    //       stop when |ω_b| < 1e-10 and |v_b| < 1e-10; else θ += pinvSolve(J_b(θ), V_b, 0).
    return guess;
}
// ==== end ====

// ==== ex11 ====  move the joints, keep the tool still (page 130)
Joints nullMotion(const Joints& th, const Joints& q0) {
    // TODO: J_p = the 3 x 4 Jacobian of the tool POINT in {s}: column i = v_i + ω_i × p,
    //       with (ω_i, v_i) = column i of J_s and p = toolPosition(th).
    //       Return N q0 = q0 − J_pᵀ (J_p J_pᵀ)⁻¹ J_p q0.
    return Joints{};
}
// ==== end ====


// Your playground. The page's tests use their own main(), so this one only
// runs when you build the file yourself (see the top of the file).
#ifndef RRPR_TEST_HARNESS
int main() {
    Joints th{0.3, 0.5, 0.2, -0.4};
    print("tau to hold 2 kg", holdPayload(th, 2.0));
    print("manipulability (mu1, mu2, mu3)", manipulability(th));
    Joints guess{0.0, 0.2, 0.1, 0.0};
    print("IK solution", ikNewton(fkBody(th), guess));
    return 0;
}
#endif
