// pid.hpp -- the CONTRACT: what the rest of the program may ask of a Pid.
#pragma once

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
