#pragma once
#include <cstddef>

class SampleBuffer {
public:
    explicit SampleBuffer(std::size_t n);
    ~SampleBuffer();

    SampleBuffer(const SampleBuffer&) = delete;
    SampleBuffer& operator=(const SampleBuffer&) = delete;

    std::size_t size() const { return size_; }
    double& operator[](std::size_t i) { return data_[i]; }
    double operator[](std::size_t i) const { return data_[i]; }

private:
    double* data_ = nullptr;
    std::size_t size_ = 0;
};

inline SampleBuffer::SampleBuffer(std::size_t n) : data_(new double[n]()), size_(n) {}

inline SampleBuffer::~SampleBuffer() { delete[] data_; }
