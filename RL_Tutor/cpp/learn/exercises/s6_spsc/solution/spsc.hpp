#pragma once
#include <array>
#include <atomic>
#include <cstddef>

template <class T, std::size_t N>
class SpscQueue {
    static_assert(N >= 2, "need at least one usable slot");

public:
    bool push(const T& x) {
        const std::size_t h = head_.load(std::memory_order_relaxed);   // only we write it
        const std::size_t next = (h + 1) % N;
        if (next == tail_.load(std::memory_order_acquire)) return false;   // full
        buf_[h] = x;
        head_.store(next, std::memory_order_release);   // publish AFTER the write
        return true;
    }

    bool pop(T& out) {
        const std::size_t t = tail_.load(std::memory_order_relaxed);   // only we write it
        if (t == head_.load(std::memory_order_acquire)) return false;   // empty
        out = buf_[t];
        tail_.store((t + 1) % N, std::memory_order_release);   // hand the slot back
        return true;
    }

private:
    std::array<T, N> buf_{};
    std::atomic<std::size_t> head_{0};
    std::atomic<std::size_t> tail_{0};
};
