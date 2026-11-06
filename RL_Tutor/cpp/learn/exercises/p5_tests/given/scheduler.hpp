#pragma once
#include <cstddef>
#include <memory>
#include <stdexcept>
#include <utility>
#include <vector>
#include "controller.hpp"

// The Scheduler from v2 -- with some deliberately broken versions hidden
// behind MUTANT. You are graded on whether YOUR tests notice.
#ifndef MUTANT
#define MUTANT 0
#endif

class Scheduler {
public:
    explicit Scheduler(int baseHz) : baseHz_(baseHz) {
        if (baseHz <= 0) throw std::invalid_argument("Scheduler: baseHz must be positive");
    }

    bool add(std::unique_ptr<Controller> c, int rateHz) {
#if MUTANT == 1
        if (!c || rateHz <= 0 || rateHz > baseHz_) return false;   // forgot divisibility
#else
        if (!c || rateHz <= 0 || rateHz > baseHz_ || baseHz_ % rateHz != 0) return false;
#endif
        const long div = baseHz_ / rateHz;
        auto pos = tasks_.begin();
#if MUTANT == 2
        while (pos != tasks_.end() && pos->divider <= div) ++pos;   // fastest first
#else
        while (pos != tasks_.end() && pos->divider >= div) ++pos;
#endif
        tasks_.insert(pos, Task{std::move(c), div, 0});
        return true;
    }

    void tick() {
#if MUTANT == 3
        ++tick_;                                                       // tick 0 is skipped
#endif
        for (Task& t : tasks_) {
            if (tick_ % t.divider == 0) {
#if MUTANT == 4
                t.ctrl->update(1.0 / baseHz_);                         // wrong dt for slow tasks
#else
                t.ctrl->update(static_cast<double>(t.divider) / baseHz_);
#endif
                ++t.runs;
            }
        }
#if MUTANT != 3
        ++tick_;
#endif
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
