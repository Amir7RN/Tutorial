// pid.cpp -- the SECRET: how a Pid does it. When the algorithm changes, only
// this file recompiles; nothing that includes pid.hpp has to.
#include "pid.hpp"

// TODO 2: define the four members declared in pid.hpp, out of line. The
// `Pid::` prefix tells the compiler which class each definition belongs to.
//
//   Pid::Pid(double kp, double ki, double kd, double dt)
//       : kp_(kp), ki_(ki), kd_(kd), dt_(dt) {}
//
//   double Pid::update(double error) {
//       integral_ += error * dt_;
//       double d = first_ ? 0.0 : (error - prevError_) / dt_;
//       ...remember error, clear first_, return the sum
//   }
//
//   void Pid::reset() { ... }
//   double Pid::integral() const { ... }
