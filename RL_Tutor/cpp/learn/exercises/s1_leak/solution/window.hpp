#pragma once
#include <cstddef>
#include <vector>

inline double recentMean(const double* data, std::size_t n, std::size_t window) {
    if (window == 0 || window > n) return 0.0;        // nothing allocated yet
    std::vector<double> tmp(data + (n - window), data + n);
    double sum = 0.0;
    for (double x : tmp) sum += x;
    if (sum != sum) return 0.0;                       // tmp's destructor still runs
    return sum / static_cast<double>(window);
}
