#pragma once
// Reconstruction exercise: write this header from the specification alone.
//
// A RateLimiter makes its output follow a target, but never faster than
// maxRate (units per second). It is called once per control tick of length dt.
//
//   * class RateLimiter
//   * RateLimiter(double maxRate, double dt)
//       throws std::invalid_argument unless maxRate > 0 and dt > 0
//       (there is NO default constructor -- a limiter without a rate is meaningless)
//   * double step(double target)
//       moves the output toward target by at most maxRate*dt; returns the new output
//   * double output() const      the current output (starts at 0)
//   * double maxStep() const     maxRate*dt
//   * void reset(double value)   the output jumps to value
//
// Before you type: what is the invariant? What does it need to store?
// Which functions are const? Then write it.
