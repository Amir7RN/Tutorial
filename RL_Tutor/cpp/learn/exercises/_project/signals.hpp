#pragma once
// The blackboard every loop reads and writes -- one per joint.
// Each field has exactly ONE writer. Write that down; it is what makes the
// later multi-threaded versions possible.
struct Signals {
    double posRef = 0.0;   // rad    written by: the user / planner
    double pos = 0.0;      // rad    written by: the motor (measurement)
    double velRef = 0.0;   // rad/s  written by: PositionLoop
    double vel = 0.0;      // rad/s  written by: the motor
    double curRef = 0.0;   // A      written by: VelocityLoop
    double cur = 0.0;      // A      written by: the motor
    double voltage = 0.0;  // V      written by: CurrentLoop
};
