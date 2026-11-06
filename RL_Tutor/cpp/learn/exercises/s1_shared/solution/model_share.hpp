#pragma once
#include <memory>
#include <string>
#include <utility>

struct Model {
    std::string name;
    double mass;
};

class Planner {
public:
    explicit Planner(std::shared_ptr<const Model> m) : model_(std::move(m)) {}
    double mass() const { return model_ ? model_->mass : 0.0; }

private:
    std::shared_ptr<const Model> model_;
};

class Logger {
public:
    explicit Logger(const std::shared_ptr<const Model>& m) : model_(m) {}
    bool modelAlive() const { return !model_.expired(); }
    std::string describe() const {
        if (auto m = model_.lock()) return m->name;
        return "gone";
    }

private:
    std::weak_ptr<const Model> model_;
};
