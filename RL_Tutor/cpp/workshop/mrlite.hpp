// mrlite.hpp -- the plumbing for the RRPR workshop (page 125).
//
// Fixed-size vectors and matrices built on std::array, plus the handful of
// operations every exercise needs (products, transpose, cross, printing).
// No robotics in here: skew, Rodrigues, adjoint, exponentials and Jacobians
// are yours to write in my_rrpr.cpp.
//
//   Vec3 w{0, 0, 1};          Mat3 R = eye<3>();
//   Vec3 v = R * w;           Mat3 K = R * transpose(R);
//   Mat4 T = ...; T[0][3]     row 0, column 3 (rows first, like the book)
#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdio>

template <std::size_t N>
using Vec = std::array<double, N>;
template <std::size_t R, std::size_t C>
using Mat = std::array<std::array<double, C>, R>;

using Vec3 = Vec<3>;
using Vec6 = Vec<6>;                 // twist (ω, v) or wrench (m, f)
using Mat3 = Mat<3, 3>;
using Mat4 = Mat<4, 4>;
using Mat6 = Mat<6, 6>;
using Joints = std::array<double, 4>; // θ1, θ2, d3 (metres), θ4
using Jac = std::array<Vec6, 4>;      // a 6 x 4 Jacobian stored by COLUMN: J[i] = column i

constexpr double PI = 3.14159265358979323846;

// ---------------------------------------------------------------- building
template <std::size_t N>
Mat<N, N> eye() {
    Mat<N, N> I{};
    for (std::size_t i = 0; i < N; ++i) I[i][i] = 1.0;
    return I;
}

template <std::size_t R, std::size_t C>
Mat<C, R> transpose(const Mat<R, C>& A) {
    Mat<C, R> B{};
    for (std::size_t i = 0; i < R; ++i)
        for (std::size_t j = 0; j < C; ++j) B[j][i] = A[i][j];
    return B;
}

// ---------------------------------------------------------------- products
template <std::size_t R, std::size_t K, std::size_t C>
Mat<R, C> operator*(const Mat<R, K>& A, const Mat<K, C>& B) {
    Mat<R, C> P{};
    for (std::size_t i = 0; i < R; ++i)
        for (std::size_t j = 0; j < C; ++j)
            for (std::size_t k = 0; k < K; ++k) P[i][j] += A[i][k] * B[k][j];
    return P;
}

template <std::size_t R, std::size_t C>
Vec<R> operator*(const Mat<R, C>& A, const Vec<C>& x) {
    Vec<R> y{};
    for (std::size_t i = 0; i < R; ++i)
        for (std::size_t j = 0; j < C; ++j) y[i] += A[i][j] * x[j];
    return y;
}

// ------------------------------------------- element-wise + - and scaling
template <std::size_t N>
Vec<N> operator+(Vec<N> a, const Vec<N>& b) { for (std::size_t i = 0; i < N; ++i) a[i] += b[i]; return a; }
template <std::size_t N>
Vec<N> operator-(Vec<N> a, const Vec<N>& b) { for (std::size_t i = 0; i < N; ++i) a[i] -= b[i]; return a; }
template <std::size_t N>
Vec<N> operator-(Vec<N> a) { for (auto& x : a) x = -x; return a; }
template <std::size_t N>
Vec<N> operator*(double s, Vec<N> a) { for (auto& x : a) x *= s; return a; }

template <std::size_t R, std::size_t C>
Mat<R, C> operator+(Mat<R, C> A, const Mat<R, C>& B) {
    for (std::size_t i = 0; i < R; ++i) for (std::size_t j = 0; j < C; ++j) A[i][j] += B[i][j];
    return A;
}
template <std::size_t R, std::size_t C>
Mat<R, C> operator-(Mat<R, C> A, const Mat<R, C>& B) {
    for (std::size_t i = 0; i < R; ++i) for (std::size_t j = 0; j < C; ++j) A[i][j] -= B[i][j];
    return A;
}
template <std::size_t R, std::size_t C>
Mat<R, C> operator-(Mat<R, C> A) {
    for (auto& row : A) for (auto& x : row) x = -x;
    return A;
}
template <std::size_t R, std::size_t C>
Mat<R, C> operator*(double s, Mat<R, C> A) {
    for (auto& row : A) for (auto& x : row) x *= s;
    return A;
}

// ---------------------------------------------------------------- 3-vectors
inline double dot(const Vec3& a, const Vec3& b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
inline Vec3 cross(const Vec3& a, const Vec3& b) {
    return {a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]};
}
inline double norm(const Vec3& a) { return std::sqrt(dot(a, a)); }

// ------------------------------------------------------ blocks and slices
inline Vec3 top(const Vec6& V) { return {V[0], V[1], V[2]}; }      // ω (or m)
inline Vec3 bottom(const Vec6& V) { return {V[3], V[4], V[5]}; }   // v (or f)
inline Vec6 stack(const Vec3& a, const Vec3& b) { return {a[0], a[1], a[2], b[0], b[1], b[2]}; }

inline Mat3 rotPart(const Mat4& T) {
    Mat3 R{};
    for (int i = 0; i < 3; ++i) for (int j = 0; j < 3; ++j) R[i][j] = T[i][j];
    return R;
}
inline Vec3 posPart(const Mat4& T) { return {T[0][3], T[1][3], T[2][3]}; }

// --------------------------------------------------------------- printing
template <std::size_t N>
void print(const char* name, const Vec<N>& v) {
    std::printf("%s = (", name);
    for (std::size_t i = 0; i < N; ++i) std::printf(i ? ", %8.4f" : "%8.4f", v[i] + 0.0);
    std::printf(")\n");
}
template <std::size_t R, std::size_t C>
void print(const char* name, const Mat<R, C>& A) {
    std::printf("%s =\n", name);
    for (const auto& row : A) {
        std::printf("  [");
        for (std::size_t j = 0; j < C; ++j) std::printf(j ? " %8.4f" : "%8.4f", row[j] + 0.0);
        std::printf(" ]\n");
    }
}
inline void print(const char* name, const Jac& J) {   // prints the 6 x 4 matrix, columns side by side
    std::printf("%s =\n", name);
    for (int r = 0; r < 6; ++r) {
        std::printf("  [");
        for (int c = 0; c < 4; ++c) std::printf(c ? " %8.4f" : "%8.4f", J[c][r] + 0.0);
        std::printf(" ]\n");
    }
}
