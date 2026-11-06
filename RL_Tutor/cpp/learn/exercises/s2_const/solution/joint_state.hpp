#pragma once
#include <cstddef>
#include <vector>

class JointState {
public:
    explicit JointState(std::size_t n) : q_(n, 0.0), qd_(n, 0.0) {}

    std::size_t dof() const { return q_.size(); }
    const std::vector<double>& positions() const { return q_; }
    double velocity(std::size_t i) const { return qd_[i]; }
    void set(std::size_t i, double q, double qd) { q_[i] = q; qd_[i] = qd; }

private:
    std::vector<double> q_, qd_;
};

inline double kineticEnergy(const JointState& s, const std::vector<double>& inertia) {
    double e = 0.0;
    for (std::size_t i = 0; i < s.dof(); ++i)
        e += 0.5 * inertia[i] * s.velocity(i) * s.velocity(i);
    return e;
}
