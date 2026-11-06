#pragma once
#include <cstddef>

// A fixed-size block of samples that OWNS its memory.
// Invariant: data_ points to exactly size_ doubles obtained with new[],
//            and this object is the only one that will ever delete[] them.
// RAII = the constructor acquires, the destructor releases. Nobody has to
// remember to "free the buffer": the closing brace does it.
class SampleBuffer {
public:
    explicit SampleBuffer(std::size_t n);
    ~SampleBuffer();

    // Copying would make two owners of one block -> double delete. Forbid it.
    SampleBuffer(const SampleBuffer&) = delete;
    SampleBuffer& operator=(const SampleBuffer&) = delete;

    std::size_t size() const { return size_; }
    double& operator[](std::size_t i) { return data_[i]; }
    double operator[](std::size_t i) const { return data_[i]; }

private:
    double* data_ = nullptr;
    std::size_t size_ = 0;
};

// TODO 1: allocate n doubles, all zero.   Hint: new double[n]() -- the () zeroes them.
inline SampleBuffer::SampleBuffer(std::size_t n) : size_(n) {
}

// TODO 2: give them back. new[] pairs with delete[] (never plain delete).
inline SampleBuffer::~SampleBuffer() {
}
