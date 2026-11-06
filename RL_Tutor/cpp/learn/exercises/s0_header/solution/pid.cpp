// pid.cpp -- the SECRET: how a Pid does it.
#include "pid.hpp"

Pid::Pid(double kp, double ki, double kd, double dt)
    : kp_(kp), ki_(ki), kd_(kd), dt_(dt) {}

double Pid::update(double error) {
    integral_ += error * dt_;
    double d = first_ ? 0.0 : (error - prevError_) / dt_;
    prevError_ = error;
    first_ = false;
    return kp_ * error + ki_ * integral_ + kd_ * d;
}

void Pid::reset() {
    integral_ = 0.0;
    prevError_ = 0.0;
    first_ = true;
}

double Pid::integral() const { return integral_; }
