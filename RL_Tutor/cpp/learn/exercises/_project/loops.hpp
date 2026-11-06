#pragma once
#include <algorithm>
#include "controller.hpp"
#include "signals.hpp"

// The three loops of a cascade, outermost first.
// Each holds a REFERENCE to the Signals it works on: a loop cannot exist
// without a joint, and must never outlive it.

// P controller on position: velRef = clamp(kp*(posRef - pos), +-velLimit)
class PositionLoop : public Controller {
public:
    PositionLoop(Signals& s, double kp, double velLimit) : s_(s), kp_(kp), lim_(velLimit) {}
    void update(double) override { s_.velRef = std::clamp(kp_ * (s_.posRef - s_.pos), -lim_, lim_); }
    const char* name() const override { return "position"; }

private:
    Signals& s_;
    double kp_, lim_;
};

// A PI with output limit and anti-windup: the integral is clamped so that
// ki*integral alone never exceeds the limit.
struct Pi {
    double kp, ki, lim;
    double integral = 0.0;
    double step(double e, double dt) {
        integral += e * dt;
        if (ki > 0.0) integral = std::clamp(integral, -lim / ki, lim / ki);
        return std::clamp(kp * e + ki * integral, -lim, lim);
    }
};

// PI on velocity -> current reference
class VelocityLoop : public Controller {
public:
    VelocityLoop(Signals& s, double kp, double ki, double curLimit) : s_(s), pi_{kp, ki, curLimit} {}
    void update(double dt) override { s_.curRef = pi_.step(s_.velRef - s_.vel, dt); }
    const char* name() const override { return "velocity"; }

private:
    Signals& s_;
    Pi pi_;
};

// PI on current -> voltage
class CurrentLoop : public Controller {
public:
    CurrentLoop(Signals& s, double kp, double ki, double vLimit) : s_(s), pi_{kp, ki, vLimit} {}
    void update(double dt) override { s_.voltage = pi_.step(s_.curRef - s_.cur, dt); }
    const char* name() const override { return "current"; }

private:
    Signals& s_;
    Pi pi_;
};
