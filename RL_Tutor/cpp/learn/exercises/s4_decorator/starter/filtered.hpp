#pragma once
#include <memory>
#include <stdexcept>
#include <utility>
#include "controllers.hpp"

// Composition: a FilteredController IS a Controller (so a scheduler can run
// it) and HAS a Controller inside (any kind). It low-pass filters the
// measurement, then hands the filtered value to the inner controller.
// Filtering any controller this way needs one class -- not a FilteredPid,
// a FilteredImpedance, a FilteredLqr...
//
//   constructor: throw std::invalid_argument if inner is null or alpha is
//                not in (0, 1]
//   update:      first call: filt = meas;  later: filt += alpha*(meas - filt)
//                return inner->update(ref, filt, dt)
//   reset:       reset the inner controller AND go back to "first call"
//   name:        "filtered(" + inner name + ")"
class FilteredController : public Controller {
public:
    FilteredController(std::unique_ptr<Controller> inner, double alpha) {}

    double update(double ref, double meas, double dt) override { return 0.0; }
    void reset() override {}
    std::string name() const override { return "filtered()"; }

private:
    // TODO: what does it own, and what does it remember?
};
