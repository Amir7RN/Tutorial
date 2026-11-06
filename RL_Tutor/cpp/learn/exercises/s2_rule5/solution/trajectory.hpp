#pragma once
#include <algorithm>
#include <cstddef>
#include <utility>

class Trajectory {
public:
    explicit Trajectory(std::size_t n = 0) : n_(n), q_(n ? new double[n]() : nullptr) {}
    ~Trajectory() { delete[] q_; }

    Trajectory(const Trajectory& other)
        : n_(other.n_), q_(other.n_ ? new double[other.n_] : nullptr) {
        std::copy(other.q_, other.q_ + other.n_, q_);
    }

    Trajectory& operator=(const Trajectory& other) {
        Trajectory tmp(other);          // may throw: *this is untouched if it does
        swap(tmp);                      // cannot throw
        return *this;                   // tmp's destructor frees our old buffer
    }

    Trajectory(Trajectory&& other) noexcept
        : n_(std::exchange(other.n_, 0)), q_(std::exchange(other.q_, nullptr)) {}

    Trajectory& operator=(Trajectory&& other) noexcept {
        if (this != &other) {
            delete[] q_;
            n_ = std::exchange(other.n_, 0);
            q_ = std::exchange(other.q_, nullptr);
        }
        return *this;
    }

    void swap(Trajectory& o) noexcept {
        std::swap(n_, o.n_);
        std::swap(q_, o.q_);
    }

    std::size_t size() const { return n_; }
    double& operator[](std::size_t i) { return q_[i]; }
    double operator[](std::size_t i) const { return q_[i]; }
    const double* data() const { return q_; }

private:
    std::size_t n_;
    double* q_;
};
