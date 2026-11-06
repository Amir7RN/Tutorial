#pragma once
#include <stdexcept>

// Invariant: maxStep_ > 0. Everything else follows from it.
class RateLimiter {
public:
    RateLimiter(double maxRate, double dt) {
        if (!(maxRate > 0.0) || !(dt > 0.0))
            throw std::invalid_argument("RateLimiter: maxRate and dt must be positive");
        maxStep_ = maxRate * dt;           // store the product: it is all step() needs
    }

    double step(double target) {
        double d = target - y_;
        if (d > maxStep_) d = maxStep_;
        else if (d < -maxStep_) d = -maxStep_;
        return y_ += d;
    }

    double output() const { return y_; }
    double maxStep() const { return maxStep_; }
    void reset(double value) { y_ = value; }

private:
    double maxStep_;
    double y_ = 0.0;
};
