#pragma once
#include <atomic>
#include <chrono>
#include <functional>
#include <thread>

// Runs fn() every period on its own thread until stop().
//
// The trap this exercise is about: if a std::thread object is destroyed while
// still joinable, the program calls std::terminate(). So stop() must join,
// and the destructor must call stop().
//
//   start(period, fn): false if already running. Otherwise launch the thread:
//       next = now; while (running_) { fn(); ++ticks_; next += period;
//                                       std::this_thread::sleep_until(next); }
//       (sleep_until(next), not sleep_for(period): the error does not pile up)
//   stop():  running_ = false, then join if joinable. Safe to call twice.
//   ticks(): how many times fn has run (read from another thread -> atomic)
class PeriodicWorker {
public:
    ~PeriodicWorker() {}   // TODO

    bool start(std::chrono::microseconds period, std::function<void()> fn) { return false; }
    void stop() {}
    long ticks() const { return 0; }
    bool running() const { return false; }

private:
    std::thread thread_;
    std::atomic<bool> running_{false};
    std::atomic<long> ticks_{0};
};
