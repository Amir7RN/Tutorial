#pragma once
#include <memory>
#include <utility>

struct Pd {
    double kp, kd;
    double prev = 0.0;
    double update(double e, double dt) {
        double d = (e - prev) / dt;
        prev = e;
        return kp * e + kd * d;
    }
};

inline std::unique_ptr<Pd> makePd(double kp, double kd) {
    return std::make_unique<Pd>(Pd{kp, kd});
}

class Joint {
public:
    void setController(std::unique_ptr<Pd> c) { ctrl_ = std::move(c); }
    bool hasController() const { return static_cast<bool>(ctrl_); }
    double command(double error, double dt) { return ctrl_ ? ctrl_->update(error, dt) : 0.0; }
    std::unique_ptr<Pd> releaseController() { return std::move(ctrl_); }

private:
    std::unique_ptr<Pd> ctrl_;
};
