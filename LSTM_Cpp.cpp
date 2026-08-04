#include <Eigen/Dense>
#include <iostream>
#include <vector>
#include <cmath>

using namespace Eigen;

class LSTMLayer{
public:

    int hidden_dim = 32; // Hidden Dimension 32 means that instead of having just 1 "conveyor belt," the model has 32 parallel conveyor belts running at the same time.
    //                    // This allows the model to remember 32 different things simultaneously (e.g., one belt might track "Am I in stance phase?", another tracks "
                        // How fast is the force increasing?", another tracks "Is the foot flat?").
    int input_dim = 2;

    MatrixXf Wf, Wi, Wo, Wg; // weight for Inputs side: forget (cont to % of forgetting of long term), input (cont to % of updating long term), 
                            // output (cont to output//updating short term), and cell gates (cont to gnerating new/update for long term) --> inputs
    MatrixXf Uf, Ui, Uo, Ug; //wieght for Hidden state side: forget, input, output, and cell gates --> hidden state
    VectorXf bf, bi, bo, bg;

    VectorXf h, c; // Hidden state and cell state
    // Final layer to get 1 output from 32 hidden values
    RowVectorXf W_out; // 1 x 32
    float b_out;       // scalar bias

    LSTMLayer(){
        h = VectorXf::Zero(hidden_dim); // Short-term memory (Hidden state)
        c = VectorXf::Zero(hidden_dim); // Long-term memory (Cell)
    }

    float sigmoid(float x) {
        return 1 / (1 + std::exp(-x));
    }    

    void forward(const VectorXf &x_t) {
        VectorXf f_t = (Wf * x_t + Uf * h + bf).unaryExpr([this](float elem) { return sigmoid(elem); });
        VectorXf i_t = (Wi * x_t + Ui * h + bi).unaryExpr([this](float elem) { return sigmoid(elem); });
        VectorXf o_t = (Wo * x_t + Uo * h + bo).unaryExpr([this](float elem) { return sigmoid(elem); });
        VectorXf g_t = (Wg * x_t + Ug * h + bg).array().tanh();

        c = f_t.array() * c.array() + i_t.array() * g_t.array();
        h = o_t.array() * c.array().tanh();
    }


    float predict_sequence(const std::vector<Vector2f> &window) {
        h.setZero();
        c.setZero();

        for (const auto& input_sample : window) {
            this->forward(input_sample);
        }
        float prediction = (W_out * h)(0) + b_out;
        return prediction;

    }
};

int main() {
    LSTMLayer myLSTM;

    // ... In a real scenario, you would initialize weights here ...
    // e.g., myLSTM.Wf = MatrixXf::Random(32, 2); 

    // Simulation: A 100ms window of Force and Force_Dot
    std::vector<Vector2f> gait_window;
    for(int i = 0; i < 100; ++i) {
        gait_window.push_back(Vector2f(500.0f, 10.0f)); // Example: 500N load
    }

    // Get the result
    float knee_velocity = myLSTM.predict_sequence(gait_window);

    std::cout << "Predicted Knee Velocity: " << knee_velocity << std::endl;

    return 0;
}