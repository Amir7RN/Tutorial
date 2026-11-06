#pragma once
#include <stdexcept>

// Limits makes ONE promise, always:   lo() <= hi().
// Every public function either keeps that promise or refuses -- throws -- and
// changes nothing. That promise is the whole reason this is a class with
// private members instead of a struct with two public doubles.
class Limits {
public:
    // TODO 1: throw std::invalid_argument when the range is invalid.
    //         Write the test as  !(lo <= hi)  rather than  lo > hi : it also
    //         rejects NaN, because every comparison with NaN is false.
    Limits(double lo, double hi) : lo_(lo), hi_(hi) {}

    double lo() const { return lo_; }
    double hi() const { return hi_; }

    // TODO 2: same rule. If it throws, the OLD range must still be in place
    //         (check first, assign after).
    void setRange(double lo, double hi) {
        lo_ = lo;
        hi_ = hi;
    }

    // TODO 3: the nearest value inside [lo, hi].
    double clamp(double x) const { return x; }

    // TODO 4: lo <= x <= hi
    bool contains(double x) const { return true; }

private:
    double lo_, hi_;
};
