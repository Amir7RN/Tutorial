#pragma once
#include <memory>
#include <sstream>
#include <string>
#include "loops.hpp"
#include "scheduler.hpp"

// Project v3: build the whole cascade from TEXT -- no recompiling to retune.
//
// One task per line:      <type> <rateHz> key=value ...
//     position 1000  kp=63   limit=100
//     velocity 8000  kp=0.25 ki=30   limit=5
//     current  32000 kp=4.7  ki=9400 limit=24
// Blank lines and lines starting with '#' are skipped.
// Keys: position takes kp, limit; velocity and current take kp, ki, limit.
// A missing kp/ki defaults to 0. limit is REQUIRED.
//
// On ANY problem return nullptr and set *error to a message that starts with
// "line N: " (N counts from 1, blank and comment lines included), e.g.
//     "line 2: unknown type 'velocty'"
// Problems: unknown type, missing or non-integer rate, a token without '=',
// a bad number, a key the type does not take, missing limit, or a rate the
// scheduler refuses.
inline std::unique_ptr<Scheduler> buildFromConfig(const std::string& text, int baseHz,
                                                  Signals& s, std::string* error) {
    // TODO. Shape that works:
    //   auto sched = std::make_unique<Scheduler>(baseHz);
    //   std::istringstream lines(text); std::string line; int n = 0;
    //   while (std::getline(lines, line)) { ++n; ... parse, build the loop, sched->add ... }
    //   return sched;
    if (error) *error = "not implemented";
    return nullptr;
}
