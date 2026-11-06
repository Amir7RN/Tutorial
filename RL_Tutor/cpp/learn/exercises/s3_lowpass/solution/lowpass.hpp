#pragma once
#include <stdexcept>

class LowPass {
public:
    LowPass(double cutoffHz, double dt) {
        if (!(cutoffHz > 0.0) || !(dt > 0.0))
            throw std::invalid_argument("LowPass: cutoff and dt must be positive");
        const double pi = 3.14159265358979323846;
        alpha_ = dt / (dt + 1.0 / (2.0 * pi * cutoffHz));
    }

    double update(double x) { return y_ += alpha_ * (x - y_); }
    void reset(double value = 0.0) { y_ = value; }
    double value() const { return y_; }
    double alpha() const { return alpha_; }

private:
    double alpha_;      // computed once; fc and dt are not needed again
    double y_ = 0.0;    // the only thing that changes between calls
};
