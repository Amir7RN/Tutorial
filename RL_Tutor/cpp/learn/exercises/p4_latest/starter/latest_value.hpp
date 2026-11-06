#pragma once
#include <atomic>
#include <cstdint>

// Project v4: hand data from the 1 kHz control thread to a slow reader
// (a 20 Hz logger, or an RL learner) with NO locks, NO blocking, and NO torn
// reads -- the reader must never see half of an old T and half of a new one.
//
// Triple buffer. Three slots: the writer owns one, the reader owns one, and
// the third is the hand-off ("middle"). middle_ holds the index of the
// hand-off slot in bits 0-1, and bit 2 (FRESH) set when it holds a value the
// reader has not taken yet.
//
//   write(v): slots_[w_] = v;
//             old = middle_.exchange(w_ | FRESH, std::memory_order_acq_rel);
//             w_ = old & 3;                    // the old hand-off slot is ours now
//   read(out): if (!(middle_.load(std::memory_order_acquire) & FRESH)) {
//                  out = slots_[r_]; return false;   // nothing new: repeat the last
//              }
//              old = middle_.exchange(r_, std::memory_order_acq_rel);
//              r_ = old & 3; out = slots_[r_]; return true;
//
// Neither side ever waits for the other. exchange() is ONE atomic step, so
// both can never own the same slot.
template <class T>
class LatestValue {
public:
    void write(const T& v) {}
    bool read(T& out) { return false; }   // true when a new value arrived since the last read

private:
    static constexpr std::uint8_t FRESH = 4;
    T slots_[3]{};
    std::uint8_t w_ = 0;                       // writer's slot (writer thread only)
    std::uint8_t r_ = 2;                       // reader's slot (reader thread only)
    std::atomic<std::uint8_t> middle_{1};      // hand-off slot | FRESH
};
