#pragma once
#include <stdexcept>

// First-order low-pass filter, discretised:
//     y[k] = y[k-1] + alpha * (x[k] - y[k-1])
//     alpha = dt / (dt + 1/(2*pi*fc))        which is always in (0, 1]
//
// Design question first: what must this object REMEMBER between calls, and
// what can it compute ONCE in the constructor? (It does not need fc or dt
// after construction.) Declare exactly that in the private section.
//
// Invariant: 0 < alpha <= 1. Constructor throws std::invalid_argument unless
// cutoffHz > 0 and dt > 0 (NaN must be rejected too).
class LowPass {
public:
    LowPass(double cutoffHz, double dt) {}

    double update(double x) { return 0.0; }       // returns the new output
    void reset(double value = 0.0) {}             // output jumps to value
    double value() const { return 0.0; }
    double alpha() const { return 0.0; }

private:
    // TODO: your members here
};
