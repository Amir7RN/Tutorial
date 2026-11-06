#pragma once
#include <algorithm>
#include "controller.hpp"
#include "signals.hpp"

// Project v0-v1: the three loops of a cascade, outermost first.
// Each holds a REFERENCE to the Signals it works on: a loop cannot exist
// without a joint, and must never outlive it.

// Done for you -- the pattern to copy.
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

// TODO 1: a PI with output limit and anti-windup.
//   step(e, dt): integral += e*dt;
//                if ki > 0, clamp integral to +-lim/ki   (ki*integral alone never exceeds lim)
//                return clamp(kp*e + ki*integral, +-lim)
// Both loops below use it: write the arithmetic ONCE.
struct Pi {
    double kp, ki, lim;
    double integral = 0.0;
    double step(double e, double dt) { return 0.0; }
};

// TODO 2: curRef = PI(velRef - vel); name() "velocity"
class VelocityLoop : public Controller {
public:
    VelocityLoop(Signals& s, double kp, double ki, double curLimit) : s_(s), pi_{kp, ki, curLimit} {}
    void update(double dt) override {}
    const char* name() const override { return "velocity"; }

private:
    Signals& s_;
    Pi pi_;
};

// TODO 3: voltage = PI(curRef - cur); name() "current"
class CurrentLoop : public Controller {
public:
    CurrentLoop(Signals& s, double kp, double ki, double vLimit) : s_(s), pi_{kp, ki, vLimit} {}
    void update(double dt) override {}
    const char* name() const override { return "current"; }

private:
    Signals& s_;
    Pi pi_;
};
