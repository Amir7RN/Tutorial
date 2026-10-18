#include <algorithm>
#include <iostream>
#include <cmath>
#include <cstdint>


using namespace std;


class PID {

private:
    float K_, D_, I_;
    constexpr static float delta_t = 0.001f;
    float prevError = 0.0f;
    float cumsumError = 0.0f;
    float saturation_;
    bool firstUpdate = true;

public:
    PID(float k, float d, float i, float sat) : K_(k), D_(d), I_(i), saturation_(sat) {
        //static_assert();
    } 
    ~PID() = default;


    float update (float error) {

        float P_Term = K_ * error;
        float D_Term = (firstUpdate)? 0.0 : D_ * (error - prevError) / delta_t;
        firstUpdate = false;
        prevError = error;

        cumsumError += error * delta_t;

        float I_Term = I_ * cumsumError;

        float output = P_Term + D_Term + I_Term;

        if (output > saturation_){
            output = saturation_;
            cumsumError -= error * delta_t;
        }else if (output < -saturation_){
            output = -saturation_;
            cumsumError -= error * delta_t;
        }

        return output;
    }

    void reset(){
        prevError = 0.0f;
        cumsumError = 0.0f;
        firstUpdate = true;
    }

};