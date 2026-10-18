#include <array>
#include <vector>
#include <iostream>

using namespace std;

using Vector = vector<double>;
using Batch = vector<Vector>;

class DenseLayer{
private:
    size_t inputSize_;
    size_t outputSize_;

    Vector biases_;
    vector<Vector> weights_;

    Vector gBiases_;
    vector<Vector> gWeights_;

public:

    DenseLayer(size_t inputSize, size_t outputSize) : inputSize_(inputSize), outputSize_(outputSize){};
    Batch forward(const Batch& input);
    Batch backward(const Batch& gOutput);

    void ZeroGradients();
    void update(double learningRate);

};