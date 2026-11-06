#pragma once
#include <memory>
#include <stdexcept>
#include <utility>
#include "controllers.hpp"

class FilteredController : public Controller {
public:
    FilteredController(std::unique_ptr<Controller> inner, double alpha)
        : inner_(std::move(inner)), alpha_(alpha) {
        if (!inner_) throw std::invalid_argument("FilteredController: null inner controller");
        if (!(alpha > 0.0 && alpha <= 1.0)) throw std::invalid_argument("FilteredController: alpha in (0, 1]");
    }

    double update(double ref, double meas, double dt) override {
        filt_ = first_ ? meas : filt_ + alpha_ * (meas - filt_);
        first_ = false;
        return inner_->update(ref, filt_, dt);
    }
    void reset() override { inner_->reset(); first_ = true; }
    std::string name() const override { return "filtered(" + inner_->name() + ")"; }

private:
    std::unique_ptr<Controller> inner_;
    double alpha_;
    double filt_ = 0.0;
    bool first_ = true;
};
