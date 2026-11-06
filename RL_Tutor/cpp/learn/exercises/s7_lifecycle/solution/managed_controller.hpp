#pragma once

enum class State { Unconfigured, Inactive, Active, Finalized };

class ManagedController {
public:
    State state() const { return state_; }

    bool configure(double kp) {
        if (state_ != State::Unconfigured || !(kp >= 0.0)) return false;
        kp_ = kp;
        state_ = State::Inactive;
        return true;
    }
    bool activate(double* cmd) {
        if (state_ != State::Inactive || cmd == nullptr) return false;
        cmd_ = cmd;
        state_ = State::Active;
        return true;
    }
    bool deactivate() {
        if (state_ != State::Active) return false;
        *cmd_ = 0.0;
        cmd_ = nullptr;
        state_ = State::Inactive;
        return true;
    }
    bool cleanup() {
        if (state_ != State::Inactive) return false;
        kp_ = 0.0;
        state_ = State::Unconfigured;
        return true;
    }
    bool shutdown() {
        if (state_ == State::Finalized) return false;
        if (state_ == State::Active) deactivate();
        state_ = State::Finalized;
        return true;
    }
    bool update(double ref, double meas) noexcept {
        if (state_ != State::Active) return false;
        *cmd_ = kp_ * (ref - meas);
        return true;
    }

private:
    State state_ = State::Unconfigured;
    double kp_ = 0.0;
    double* cmd_ = nullptr;
};
