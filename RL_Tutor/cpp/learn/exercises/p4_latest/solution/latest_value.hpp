#pragma once
#include <atomic>
#include <cstdint>

template <class T>
class LatestValue {
public:
    void write(const T& v) {
        slots_[w_] = v;
        const std::uint8_t old = middle_.exchange(static_cast<std::uint8_t>(w_ | FRESH),
                                                  std::memory_order_acq_rel);
        w_ = old & 3;
    }

    bool read(T& out) {
        if (!(middle_.load(std::memory_order_acquire) & FRESH)) {
            out = slots_[r_];
            return false;
        }
        const std::uint8_t old = middle_.exchange(r_, std::memory_order_acq_rel);
        r_ = old & 3;
        out = slots_[r_];
        return true;
    }

private:
    static constexpr std::uint8_t FRESH = 4;
    T slots_[3]{};
    std::uint8_t w_ = 0;
    std::uint8_t r_ = 2;
    std::atomic<std::uint8_t> middle_{1};
};
