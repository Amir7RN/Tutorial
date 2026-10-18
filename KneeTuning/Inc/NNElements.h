#include <vector>
#include <cmath>
#include <numeric>

#pragma once
using namespace std;
namespace ActivationFunction
{
    void ReLU(vector<double>& input){

        size_t i =0;
        for (; i < input.size(); ++i){
            input[i] = (input[i] >0) ? input[i] : 0.0;
        }

    }

    void sigmoid(vector<double>& input){

        size_t i = 0;
        int output = 0;
        for (; i < input.size(); ++i){
            input[i] = (1/(1+exp(-input[i])));
        }
    }
} // namespace ActivationFunction

vector<double> FC_Layer(vector<double> input, int output_size, vector<vector<double>> weights, vector<double> bias){
    
    vector<double> Output(output_size,0);
    for (int t = 0; t < output_size; ++t){
        double sum = 0.0;
        for (size_t i=0; i< input.size(); ++i){
            sum += weights[i][t] * input[i];
        }  
        Output[t] = sum + bias[t];
    }

    return Output;
}

void Batch_Normalization(vector<double> input){

    double sum = accumulate(input.begin(), input.end(), 0.0);
    double mean = sum / static_cast<double>(input.size());

    for (auto& in : input){
        in -= mean;
    }

}