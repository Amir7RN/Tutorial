#pragma once
#include <array>
#include <cstddef>

template <class T>
const T& clampT(const T& x, const T& lo, const T& hi) {
    return x < lo ? lo : (hi < x ? hi : x);
}

template <class T, std::size_t N>
class RingBuffer {
    static_assert(N > 0, "a ring needs at least one slot");

public:
    void push(const T& x) {
        buf_[next_] = x;
        next_ = (next_ + 1) % N;
        if (count_ < N) ++count_;
    }
    std::size_t size() const { return count_; }
    static constexpr std::size_t capacity() { return N; }
    bool full() const { return count_ == N; }
    const T& at(std::size_t i) const { return buf_[(next_ + N - count_ + i) % N]; }
    const T& latest() const { return buf_[(next_ + N - 1) % N]; }
    void clear() { next_ = 0; count_ = 0; }

private:
    std::array<T, N> buf_{};
    std::size_t next_ = 0;    // where the next push writes
    std::size_t count_ = 0;   // how many are stored (<= N)
};
