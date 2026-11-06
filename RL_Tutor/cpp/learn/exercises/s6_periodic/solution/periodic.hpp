#pragma once
#include <atomic>
#include <chrono>
#include <functional>
#include <thread>
#include <utility>

class PeriodicWorker {
public:
    ~PeriodicWorker() { stop(); }

    bool start(std::chrono::microseconds period, std::function<void()> fn) {
        if (running_) return false;
        if (thread_.joinable()) thread_.join();
        running_ = true;
        thread_ = std::thread([this, period, fn = std::move(fn)] {
            auto next = std::chrono::steady_clock::now();
            while (running_) {
                fn();
                ++ticks_;
                next += period;
                std::this_thread::sleep_until(next);
            }
        });
        return true;
    }

    void stop() {
        running_ = false;
        if (thread_.joinable()) thread_.join();
    }

    long ticks() const { return ticks_; }
    bool running() const { return running_; }

private:
    std::thread thread_;
    std::atomic<bool> running_{false};
    std::atomic<long> ticks_{0};
};
