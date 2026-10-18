#include <iostream>


class Actor {

private:
    double state[];
    double weights[];
public:

    void forward(double state, double weight);
    void backward(double state, double weight);
    void update(double weights, double bias, double learning);


};