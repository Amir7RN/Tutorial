#pragma once
#include <cstddef>
#include <utility>

// Owns n waypoints on the heap. The members the compiler would generate copy
// the POINTER: two objects then own one buffer and both delete[] it.
// When a class owns a raw resource, write all five special members
// (or better -- see the page -- own it with std::vector and write none).
class Trajectory {
public:
    explicit Trajectory(std::size_t n = 0) : n_(n), q_(n ? new double[n]() : nullptr) {}
    ~Trajectory() { delete[] q_; }

    // TODO 1: copy constructor -- a DEEP copy: a new buffer with the same numbers.
    Trajectory(const Trajectory& other) : n_(other.n_), q_(other.q_) {}

    // TODO 2: copy assignment -- must survive  t = t;  and must not leak the old buffer.
    //         The copy-and-swap idiom does both:  Trajectory tmp(other); swap with tmp.
    Trajectory& operator=(const Trajectory& other) {
        n_ = other.n_;
        q_ = other.q_;
        return *this;
    }

    // TODO 3: move constructor -- STEAL the buffer, then leave other empty
    //         (n_ = 0, q_ = nullptr) so its destructor frees nothing. No allocation.
    Trajectory(Trajectory&& other) noexcept : n_(other.n_), q_(other.q_) {}

    // TODO 4: move assignment -- free yours, steal theirs, leave them empty.
    Trajectory& operator=(Trajectory&& other) noexcept {
        n_ = other.n_;
        q_ = other.q_;
        return *this;
    }

    std::size_t size() const { return n_; }
    double& operator[](std::size_t i) { return q_[i]; }
    double operator[](std::size_t i) const { return q_[i]; }
    const double* data() const { return q_; }

private:
    std::size_t n_;
    double* q_;
};
