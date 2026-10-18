// my_rrpr.cpp -- YOUR workbook for the RRPR workshop (page 125).
//
// Fill in the TODOs one exercise at a time, then press "check my code" on the
// page. The app compiles this file with g++ and its own test main(), compares
// every number against a reference, and tells you what is wrong.
//
// The robot (metres, radians; {s} at the base, z up):
//   joint 1  R  axis ω = (0, 0, 1)   through q = (0, 0, 0)   waist
//   joint 2  R  axis ω = (0,-1, 0)   through q = (0, 0, 1)   shoulder (+θ lifts)
//   joint 3  P  direction v = (1, 0, 0)                      telescoping slide
//   joint 4  R  axis ω = (1, 0, 0)   through q = (1, 0, 1)   wrist roll
//   home M:  R = diag(1, -1, -1) (tool z points down),  p = (1.5, 0, 0.8)
//
// Build and run your own main() below from the project folder:
//   g++ -std=c++17 -I cpp/workshop cpp/workshop/my_rrpr.cpp -o cpp/workshop/build/play.exe
//   ./cpp/workshop/build/play.exe
#include "mrlite.hpp"

// ==== ex1 ====  [ω] and back
Mat3 skew(const Vec3& w) {
    // TODO: the 3x3 matrix with skew(w) * x == cross(w, x) for every x
    return Mat3{};
}

Vec3 unskew(const Mat3& W) {
    // TODO: undo skew(): read ω back out of [ω]
    return Vec3{};
}
// ==== end ====

// ==== ex2 ====  Rodrigues
Mat3 expRot(const Vec3& omegaHat, double theta) {
    // TODO: e^{[ω̂]θ} = I + sin θ [ω̂] + (1 − cos θ) [ω̂]²   (omegaHat is a unit vector)
    return Mat3{};
}
// ==== end ====

// ==== ex3 ====  homogeneous transforms
Mat4 makeT(const Mat3& R, const Vec3& p) {
    // TODO: [[R, p], [0 0 0 1]]
    return Mat4{};
}

Mat4 invT(const Mat4& T) {
    // TODO: (R, p)⁻¹ = (Rᵀ, −Rᵀp)
    return Mat4{};
}
// ==== end ====

// ==== ex4 ====  screw axes and the home pose
Vec6 revoluteAxis(const Vec3& omega, const Vec3& q) {
    // TODO: S = (ω, −ω × q)
    return Vec6{};
}

Vec6 prismaticAxis(const Vec3& v) {
    // TODO: S = (0, v)
    return Vec6{};
}

std::array<Vec6, 4> rrprScrewsSpace() {
    // TODO: S1..S4 of the robot in the header comment, in {s}
    return {};
}

Mat4 rrprHome() {
    // TODO: M from the header comment
    return Mat4{};
}
// ==== end ====

// ==== ex5 ====  adjoint, and the body screw axes
Mat6 adjoint(const Mat4& T) {
    // TODO: [Ad_T] = [[R, 0], [[p]R, R]]
    return Mat6{};
}

std::array<Vec6, 4> rrprScrewsBody() {
    // TODO: Bᵢ = [Ad_{M⁻¹}] Sᵢ
    return {};
}
// ==== end ====

// ==== ex6 ====  the exponential of a twist
Mat4 expTwist(const Vec6& S, double theta) {
    // TODO: if ω = 0: (I, vθ). Otherwise (e^{[ω]θ}, G(θ) v) with
    //       G(θ) = Iθ + (1 − cos θ)[ω] + (θ − sin θ)[ω]²
    return Mat4{};
}
// ==== end ====

// ==== ex7 ====  forward kinematics, both ways
Mat4 fkSpace(const Joints& th) {
    // TODO: e^{[S1]θ1} e^{[S2]θ2} e^{[S3]θ3} e^{[S4]θ4} M
    return Mat4{};
}

Mat4 fkBody(const Joints& th) {
    // TODO: M e^{[B1]θ1} ... e^{[B4]θ4}
    return Mat4{};
}
// ==== end ====

// ==== ex8 ====  Jacobians
Jac jacobianSpace(const Joints& th) {
    // TODO: J[0] = S1;  J[i] = [Ad_{e^{[S1]θ1} ⋯ e^{[S_i]θ_i}}] S_{i+1}   (0-based i)
    return Jac{};
}

Jac jacobianBody(const Joints& th) {
    // TODO: J[3] = B4;  J[i] = [Ad_{e^{−[B4]θ4} ⋯ e^{−[B_{i+2}]θ_{i+2}}}] B_{i+1}
    return Jac{};
}
// ==== end ====

// ==== ex9 ====  velocity and statics
Vec6 handTwistSpace(const Joints& th, const Joints& thdot) {
    // TODO: V_s = J_s(θ) θ̇
    return Vec6{};
}

Joints jointTorques(const Joints& th, const Vec6& Fs) {
    // TODO: τ = J_s(θ)ᵀ F_s
    return Joints{};
}

Vec6 wrenchToBody(const Mat4& Tsb, const Vec6& Fs) {
    // TODO: F_b = [Ad_{T_sb}]ᵀ F_s
    return Vec6{};
}
// ==== end ====

// ==== ex10 ====  check the Jacobian without it
Vec6 twistFromFK(const Joints& th, const Joints& thdot) {
    // TODO: [V_s] = Ṫ T⁻¹. Get Ṫ by finite differences of fkSpace along θ̇
    //       (central difference, h ≈ 1e-6), then read (ω, v) out of the 4x4.
    return Vec6{};
}
// ==== end ====


// Your playground. The page's tests use their own main(), so this one only
// runs when you build the file yourself (see the top of the file).
#ifndef RRPR_TEST_HARNESS
int main() {
    Joints th{0.3, 0.5, 0.2, -0.4};
    print("T_sb (space)", fkSpace(th));
    print("T_sb (body) ", fkBody(th));
    print("J_s", jacobianSpace(th));
    return 0;
}
#endif
