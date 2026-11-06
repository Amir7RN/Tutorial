#pragma once
#include <memory>
#include <utility>

// Given: a tiny PD controller.
struct Pd {
    double kp, kd;
    double prev = 0.0;
    double update(double e, double dt) {
        double d = (e - prev) / dt;
        prev = e;
        return kp * e + kd * d;
    }
};

// TODO 1: return a new Pd owned by a unique_ptr. Use std::make_unique<Pd>(...)
//         (Pd is an aggregate, so Pd{kp, kd} builds one).
inline std::unique_ptr<Pd> makePd(double kp, double kd) {
    return nullptr;
}

// A Joint OWNS at most one controller. unique_ptr says that in the type:
// it cannot be copied, only moved, so there can never be two owners.
class Joint {
public:
    // TODO 2: take ownership. A unique_ptr parameter BY VALUE means "hand it
    //         to me": the caller writes joint.setController(std::move(p)).
    //         Store it with ctrl_ = std::move(c). The old one (if any) is freed.
    void setController(std::unique_ptr<Pd> c) {
    }

    // TODO 3: a unique_ptr converts to bool: true when it owns something.
    bool hasController() const { return false; }

    // TODO 4: run the controller; return 0.0 when there is none (a joint with
    //         no controller is limp, not a crash).
    double command(double error, double dt) { return 0.0; }

    // TODO 5: hand ownership back to the caller; afterwards the joint has none.
    //         return std::move(ctrl_);
    std::unique_ptr<Pd> releaseController() { return nullptr; }

private:
    std::unique_ptr<Pd> ctrl_;
};
