// pid.hpp -- the CONTRACT: what the rest of the program may ask of a Pid.
// Anyone who #includes this file sees these declarations and nothing else.
//
// TODO 1: this header has no include guard. The test includes it twice
//         (once directly, once through uses_pid.hpp), so the compiler sees
//         `class Pid` defined twice in one translation unit. Add `#pragma once`
//         as the first line of code.

class Pid {
public:
    Pid(double kp, double ki, double kd, double dt);
    double update(double error);   // kp*e + ki*integral + kd*de/dt
    void reset();                  // forget the integral and the previous error
    double integral() const;

private:
    double kp_, ki_, kd_, dt_;
    double integral_ = 0.0;
    double prevError_ = 0.0;
    bool first_ = true;            // no derivative kick on the very first call
};
