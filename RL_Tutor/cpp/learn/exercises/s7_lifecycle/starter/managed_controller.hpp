#pragma once

// A controller with a LIFECYCLE, the shape ros2_control and ROS 2 managed
// nodes use. Construction does nothing risky; resources are claimed in
// configure/activate, and the real-time update() only acts when Active.
//
//        configure          activate
//   Unconfigured ----> Inactive ----> Active
//        ^   cleanup   |    ^ deactivate |
//        +-------------+    +------------+
//   shutdown: from any state except Finalized -> Finalized
//             (an Active controller is deactivated first)
//
// Every transition returns true if it happened. A transition that is not
// allowed from the current state returns false and changes NOTHING.
//
//   configure(kp): Unconfigured -> Inactive. Rejects kp < 0 or NaN (stays Unconfigured).
//   activate(cmd): Inactive -> Active. cmd is where update() writes; rejects nullptr.
//   deactivate():  Active -> Inactive. Writes 0.0 to *cmd (leave the motor safe), forgets cmd.
//   cleanup():     Inactive -> Unconfigured.
//   update(ref, meas): only when Active: *cmd = kp*(ref - meas), return true.
//                      Otherwise return false and touch nothing. noexcept: no throwing in the loop.
enum class State { Unconfigured, Inactive, Active, Finalized };

class ManagedController {
public:
    State state() const { return state_; }
    bool configure(double kp) { return false; }
    bool activate(double* cmd) { return false; }
    bool deactivate() { return false; }
    bool cleanup() { return false; }
    bool shutdown() { return false; }
    bool update(double ref, double meas) noexcept { return false; }

private:
    State state_ = State::Unconfigured;
    double kp_ = 0.0;
    double* cmd_ = nullptr;
};
