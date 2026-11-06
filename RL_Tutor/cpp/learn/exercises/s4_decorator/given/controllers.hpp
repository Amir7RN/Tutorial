#pragma once
#include "controller.hpp"

class PidController : public Controller {
public:
    PidController(double kp, double ki, double kd) : kp_(kp), ki_(ki), kd_(kd) {}
    double update(double ref, double meas, double dt) override {
        double e = ref - meas;
        integral_ += e * dt;
        double d = first_ ? 0.0 : (e - prev_) / dt;
        prev_ = e;
        first_ = false;
        return kp_ * e + ki_ * integral_ + kd_ * d;
    }
    void reset() override { integral_ = 0.0; first_ = true; }
    std::string name() const override { return "pid"; }

private:
    double kp_, ki_, kd_;
    double integral_ = 0.0, prev_ = 0.0;
    bool first_ = true;
};
