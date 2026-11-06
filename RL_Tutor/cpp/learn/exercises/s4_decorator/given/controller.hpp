#pragma once
#include <string>

class Controller {
public:
    virtual ~Controller() = default;
    virtual double update(double ref, double meas, double dt) = 0;
    virtual void reset() = 0;
    virtual std::string name() const = 0;
};
