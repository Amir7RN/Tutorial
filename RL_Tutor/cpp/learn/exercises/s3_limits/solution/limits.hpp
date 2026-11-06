#pragma once
#include <stdexcept>

class Limits {
public:
    Limits(double lo, double hi) : lo_(lo), hi_(hi) { validate(lo, hi); }

    double lo() const { return lo_; }
    double hi() const { return hi_; }

    void setRange(double lo, double hi) {
        validate(lo, hi);   // throws before anything changes
        lo_ = lo;
        hi_ = hi;
    }

    double clamp(double x) const { return x < lo_ ? lo_ : (x > hi_ ? hi_ : x); }
    bool contains(double x) const { return lo_ <= x && x <= hi_; }

private:
    static void validate(double lo, double hi) {
        if (!(lo <= hi)) throw std::invalid_argument("Limits: need lo <= hi");
    }
    double lo_, hi_;
};
