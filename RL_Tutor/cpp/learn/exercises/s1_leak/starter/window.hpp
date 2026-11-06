#pragma once
#include <cstddef>

// Mean of the last `window` samples of data[0..n).
// It returns the right numbers -- and leaks on three of its four paths.
//
// TODO: fix it WITHOUT writing `delete` anywhere. Give the scratch memory an
//       owner whose destructor runs on every path out of the function:
//         std::vector<double> tmp(window);            (simplest)
//         auto tmp = std::make_unique<double[]>(window);
//       Then every `return` is safe, including ones you add later.
inline double recentMean(const double* data, std::size_t n, std::size_t window) {
    double* tmp = new double[window];
    if (window == 0 || window > n) return 0.0;        // early return: who frees tmp?
    for (std::size_t i = 0; i < window; ++i) tmp[i] = data[n - window + i];
    double sum = 0.0;
    for (std::size_t i = 0; i < window; ++i) sum += tmp[i];
    if (sum != sum) return 0.0;                       // NaN guard: and here?
    double mean = sum / static_cast<double>(window);
    delete[] tmp;
    return mean;
}
