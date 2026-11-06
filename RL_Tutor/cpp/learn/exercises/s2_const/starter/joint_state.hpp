#pragma once
#include <cstddef>
#include <vector>

// kineticEnergy() below promises not to modify the state: it takes a
// `const JointState&`. Through a const reference you may only call const
// member functions -- so this file does not compile yet.
//
// TODO 1: mark every member function that does not modify the object `const`.
// TODO 2: positions() copies the whole vector on every call. Return a
//         `const std::vector<double>&` instead (a read-only view, no copy).
// Rules: do not change kineticEnergy, and do not use `mutable` or `const_cast`.
class JointState {
public:
    explicit JointState(std::size_t n) : q_(n, 0.0), qd_(n, 0.0) {}

    std::size_t dof() { return q_.size(); }
    std::vector<double> positions() { return q_; }
    double velocity(std::size_t i) { return qd_[i]; }
    void set(std::size_t i, double q, double qd) { q_[i] = q; qd_[i] = qd; }

private:
    std::vector<double> q_, qd_;
};

// Read-only use: a const reference -- no copy, and no modification.
inline double kineticEnergy(const JointState& s, const std::vector<double>& inertia) {
    double e = 0.0;
    for (std::size_t i = 0; i < s.dof(); ++i)
        e += 0.5 * inertia[i] * s.velocity(i) * s.velocity(i);
    return e;
}
