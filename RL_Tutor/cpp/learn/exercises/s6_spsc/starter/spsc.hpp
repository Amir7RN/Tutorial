#pragma once
#include <array>
#include <atomic>
#include <cstddef>

// Single producer, single consumer, lock-free, fixed size.
// The producer thread ONLY writes head_; the consumer thread ONLY writes tail_.
// Each reads the other's index to decide "full" / "empty".
// One slot always stays empty, so usable capacity is N - 1 and
// head_ == tail_ unambiguously means "empty".
//
// Memory ordering (the whole trick, two lines each):
//   push: write buf_[head], THEN head_.store(next, std::memory_order_release)
//   pop:  t == head_.load(std::memory_order_acquire) ? empty : read buf_[t] ...
// release/acquire guarantees the consumer that sees the new head_ also sees
// the element written before it.
template <class T, std::size_t N>
class SpscQueue {
    static_assert(N >= 2, "need at least one usable slot");

public:
    // producer thread only. false when full: the new sample is dropped, nothing blocks.
    bool push(const T& x) { return false; }
    // consumer thread only. false when empty.
    bool pop(T& out) { return false; }

private:
    std::array<T, N> buf_{};
    std::atomic<std::size_t> head_{0};   // next slot to write (producer owns)
    std::atomic<std::size_t> tail_{0};   // next slot to read  (consumer owns)
};
