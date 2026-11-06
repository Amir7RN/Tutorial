#pragma once
#include "controller.hpp"

// TODO 1: class PidController : public Controller
//   PidController(double kp, double ki, double kd)
//   name() returns "pid"
//   update(ref, meas, dt):
//       e = ref - meas;  integral += e*dt;
//       d = (first call) ? 0 : (e - previous e)/dt;
//       return kp*e + ki*integral + kd*d
//   reset(): integral = 0, back to "first call"
//
// TODO 2: class ImpedanceController : public Controller
//   ImpedanceController(double k, double b)        (stiffness, damping)
//   name() returns "impedance"
//   update(ref, meas, dt):
//       v = (first call) ? 0 : (meas - previous meas)/dt;   velocity estimate
//       return k*(ref - meas) - b*v
//   reset(): back to "first call"
//
// Write `override` on every function you override: then a typo in a
// signature is a compile error instead of a silent new function.
