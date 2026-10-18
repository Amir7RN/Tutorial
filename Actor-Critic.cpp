#include <iostream>

using namespace std;




class Actor{

public:
    void forward(const double state[3], double action[2]) const{
        action[0] = stiffnessBias;
        action[1] = angleBias;

        for (int i =0; i < 3; ++i){
        action[0] += state[i] * stiffnessWeights[i];
        action[1] += state[i] * angleWeights[i];
        }
    }

    void backward(const double state[3], const double gAction[2]){

        for (int i = 0; i < 3; ++i){
            gStiffnessWeights[i] = gAction[0]*state[i];
            gAngleWeights[i]     = gAction[1]*state[i];
        }

        gStiffnessBias = gAction[0] * 1.0;;
        gAngleBias = gAction[1] * 1.0;
    }

    void updateWeights(double learningRate) {
        for (int i = 0; i < 3; ++i) {
            stiffnessWeights[i] += learningRate * gStiffnessWeights[i];
            angleWeights[i] += learningRate * gAngleWeights[i];
        }

        stiffnessBias += learningRate * gStiffnessBias;
        angleBias += learningRate * gAngleBias;
    }


private:
    double stiffnessBias = 0.1;
    double angleBias = -0.1;
    double stiffnessWeights[3] = {0.5, 0.2, -0.1};
    double angleWeights[3] = {-0.3, 0.4, 0.2};
    double gStiffnessWeights[3];
    double gAngleWeights[3];
    double gStiffnessBias;
    double gAngleBias;

};

int main(){

    double state[3] = {1.0, 2.0, -1.0};

    double stiffnessWeights[3] = {0.5, 0.2, -0.1};
    double stiffnessBias = 0.1;

    double angleWeights[3] = {-0.3, 0.4, 0.2};
    double angleBias = -0.1;

    double stiffness = stiffnessBias;
    double equilibriumAngle = angleBias;

    for (int i =0; i < 3; ++i){
        stiffness += state[i] * stiffnessWeights[i];
        equilibriumAngle += state[i] * angleWeights[i];
    }


    double criticInput[5] = {
        state[0],
        state[1],
        state[2],
        stiffness,
        equilibriumAngle
    };

    double criticWeights[5] = {
        0.1,
        0.2,
        -0.1,
        2.0,
        -1.0
    };

    double criticBias = 0.5;
    double Q = criticBias;

    for (int i = 0; i < 5; ++i){
        Q += criticWeights[i] * criticInput[i];
    }

    double gQ = 1.0;

    double gStiffness = gQ * criticWeights[3];
    double gAngle = gQ * criticWeights[4];

    double gStiffnessWeights[3];
    double gAngleWeights[3];

    for (int i = 0; i < 3; ++i){
        gStiffnessWeights[i] = gStiffness*state[i];
        gAngleWeights[i]     = gAngle*state[i];
    }

    double gStiffnessBias = gStiffness * 1.0;;
    double gAngleBias = gAngle * 1.0;

    double learningRate = 0.01;

    for (int i = 0; i < 3; ++i){
        stiffnessWeights[i] += gStiffnessWeights[i] * learningRate;
        angleWeights[i] += gAngleWeights[i] * learningRate;
    }

    stiffnessBias += gStiffnessBias*learningRate;
    angleBias += gAngleBias*learningRate;


}