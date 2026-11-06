#pragma once
#include <cstddef>
#include <memory>
#include <stdexcept>
#include <utility>
#include <vector>
#include "controller.hpp"

// Project v2: the Scheduler OWNS the controllers and decides when each runs.
//
// One base clock (32 kHz in the project). A task with rate r runs every
// divider = baseHz / r base ticks, and is told dt = divider / baseHz.
//
// Invariants -- each one is a promise the rest of the program relies on:
//   * baseHz > 0                         (constructor throws std::invalid_argument)
//   * every task's rate divides baseHz   (add() refuses rates that do not)
//   * within one tick, tasks run SLOWEST FIRST: the position loop refreshes
//     velRef before the velocity loop reads it in that same tick
//   * tick() never allocates (the vector is only resized in add())
class Scheduler {
public:
    explicit Scheduler(int baseHz) : baseHz_(baseHz) {}   // TODO: validate

    // Takes ownership. Returns false -- and the controller is simply destroyed --
    // if c is null, rateHz <= 0, rateHz > baseHz, or baseHz % rateHz != 0.
    // Keep tasks_ sorted slowest first (largest divider first); among equal
    // rates, keep the order they were added.
    bool add(std::unique_ptr<Controller> c, int rateHz) { return false; }

    // Run every task whose divider divides the current tick count (tick 0
    // runs everything), then advance the count.
    void tick() {}

    std::size_t taskCount() const { return 0; }
    long ticks() const { return 0; }
    int baseHz() const { return baseHz_; }
    long runs(std::size_t i) const { return 0; }   // how many times task i has run

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
