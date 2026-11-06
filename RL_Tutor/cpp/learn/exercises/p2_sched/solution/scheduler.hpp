#pragma once
#include <cstddef>
#include <memory>
#include <stdexcept>
#include <utility>
#include <vector>
#include "controller.hpp"

class Scheduler {
public:
    explicit Scheduler(int baseHz) : baseHz_(baseHz) {
        if (baseHz <= 0) throw std::invalid_argument("Scheduler: baseHz must be positive");
    }

    bool add(std::unique_ptr<Controller> c, int rateHz) {
        if (!c || rateHz <= 0 || rateHz > baseHz_ || baseHz_ % rateHz != 0) return false;
        const long div = baseHz_ / rateHz;
        auto pos = tasks_.begin();
        while (pos != tasks_.end() && pos->divider >= div) ++pos;   // slowest first, stable
        tasks_.insert(pos, Task{std::move(c), div, 0});
        return true;
    }

    void tick() {
        for (Task& t : tasks_) {
            if (tick_ % t.divider == 0) {
                t.ctrl->update(static_cast<double>(t.divider) / baseHz_);
                ++t.runs;
            }
        }
        ++tick_;
    }

    std::size_t taskCount() const { return tasks_.size(); }
    long ticks() const { return tick_; }
    int baseHz() const { return baseHz_; }
    long runs(std::size_t i) const { return tasks_.at(i).runs; }

private:
    struct Task {
        std::unique_ptr<Controller> ctrl;
        long divider;
        long runs;
    };
    int baseHz_;
    long tick_ = 0;
    std::vector<Task> tasks_;
};
