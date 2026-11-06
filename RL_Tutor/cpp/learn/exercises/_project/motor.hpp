#pragma once
#include <algorithm>
#include "signals.hpp"

// A brushed DC motor, simulated. Given -- you do not edit this.
//   L di/dt = V - R i - Kt w        J dw/dt = Kt i - b w        dtheta/dt = w
struct MotorParams {
    double R = 1.0;      // ohm
    double L = 0.5e-3;   // H     -> electrical time constant L/R = 0.5 ms
    double Kt = 0.05;    // N m/A (= back-EMF constant in SI)
    double J = 2e-5;     // kg m^2
    double b = 1e-5;     // N m s/rad
    double Vmax = 24.0;  // supply
};

class MotorPlant {
public:
    explicit MotorPlant(MotorParams p = {}) : p_(p) {}
    // Advance by dt using s.voltage; write the measurements back into s.
    void step(Signals& s, double dt) {
        const double v = std::clamp(s.voltage, -p_.Vmax, p_.Vmax);
        const int sub = 8;
        const double h = dt / sub;
        for (int k = 0; k < sub; ++k) {
            i_ += h * (v - p_.R * i_ - p_.Kt * w_) / p_.L;
            w_ += h * (p_.Kt * i_ - p_.b * w_) / p_.J;
            th_ += h * w_;
        }
        s.cur = i_;
        s.vel = w_;
        s.pos = th_;
    }

private:
    MotorParams p_;
    double i_ = 0.0, w_ = 0.0, th_ = 0.0;
};
