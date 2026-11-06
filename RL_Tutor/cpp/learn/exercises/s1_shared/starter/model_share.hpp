#pragma once
#include <memory>
#include <string>

struct Model {
    std::string name;
    double mass;
};

// A Planner needs the Model for as long as the Planner exists. So does the
// controller, and neither one alone decides when the Model dies.
// That is SHARED ownership: the Model dies when the last shared_ptr does.
class Planner {
public:
    // TODO 1: keep a share of the model (store m in model_).
    explicit Planner(std::shared_ptr<const Model> m) {}
    // TODO 2
    double mass() const { return 0.0; }

private:
    std::shared_ptr<const Model> model_;
};

// A Logger reports on the model but must NOT keep it alive: it OBSERVES.
// weak_ptr is a shared_ptr that does not count as an owner.
class Logger {
public:
    // TODO 3: remember m without owning it (a weak_ptr can be built from a shared_ptr).
    explicit Logger(const std::shared_ptr<const Model>& m) {}
    // TODO 4: true while some owner still keeps the model alive   (weak_ptr::expired)
    bool modelAlive() const { return false; }
    // TODO 5: the model's name if it is alive, "gone" otherwise.
    //         auto m = model_.lock();   gives a shared_ptr (empty if it died)
    std::string describe() const { return "gone"; }

private:
    std::weak_ptr<const Model> model_;
};
