#include <iostream>
#include <cmath>
#include <map>

using namespace std;

enum State {
    STANCE_FLEXION,
    STANCE_EXTENSION,
    SWING_FLEXION,
    SWING_EXTENSION
};

struct SensorData {
    double KneeAngle;
    double KneeVelocity;
    double loadcell;
};

struct ImpedanceParameter {
    double k;
    double b;
    double theta_eq;
};

class ProsthesisControl {
private:
    State Current_state;

    map<State, ImpedanceParameter> gains;

    const double LOAD_THRESHOLD = 50.0; // Newtons (to detect heel strike)
    const double MAX_FLEXION_ANGLE = 1.0; // rad (approx 60 deg)


public:
    ProsthesisControl(){
        Current_state = STANCE_FLEXION;
        initialize_gains();
    }

    void initialize_gains() {
        // High stiffness for Stance, Low stiffness for Swing
        gains[STANCE_FLEXION]   = {2.5, 0.1, 0.2}; // Loading response
        gains[STANCE_EXTENSION] = {3.0, 0.2, 0.0}; // Push off phase
        gains[SWING_FLEXION]    = {0.5, 0.05, 1.1}; // Leg swings up
        gains[SWING_EXTENSION]  = {0.8, 0.1, 0.0}; // Leg extends for next step
    }

    void check_transitions(const SensorData& data){

        switch (Current_state)
        {
        case STANCE_FLEXION:
            if (data.KneeVelocity < 0.1){
                Current_state = STANCE_EXTENSION;
            }
            break;
        case STANCE_EXTENSION:
                // TOE OFF: If load is gone, we are in Swing
                if (data.loadcell < LOAD_THRESHOLD) {
                    Current_state = SWING_FLEXION;
                    std::cout << "-> Transition: Swing Flexion (Toe Off)" << std::endl;
                }
                break;

            case SWING_FLEXION:
                // If we reach max flexion, start extending leg
                if (data.KneeAngle >= MAX_FLEXION_ANGLE) {
                    Current_state = SWING_EXTENSION;
                    std::cout << "-> Transition: Swing Extension" << std::endl;
                }
                break;

            case SWING_EXTENSION:
                // HEEL STRIKE: If load appears, we hit the ground
                if (data.loadcell >= LOAD_THRESHOLD) {
                    Current_state = STANCE_FLEXION;
                    std::cout << "-> Transition: Stance Flexion (Heel Strike)" << std::endl;
                }
                break;
        }
    }

    double compute_torque(const SensorData& data){
        ImpedanceParameter p = gains[Current_state];

        // 1. Get parameters for the CURRENT state
        

        // 2. Calculate Spring Force (Hooke's Law)
        // (theta_eq - angle) acts as the "error"
        double spring_torque = p.k * (p.theta_eq - data.KneeAngle);

        // 3. Calculate Damping Force (resists motion)
        double damping_torque = -p.b * data.KneeVelocity;

        // 4. Total Torque
        return spring_torque + damping_torque;
    }

    void run_cycle(SensorData& data){
        check_transitions(data);
        double cmd = compute_torque(data);
    }
};


int main(){
    ProsthesisControl robot;

    robot.run_cycle({0.1, 0.5,0.0});

    return 0;
}


