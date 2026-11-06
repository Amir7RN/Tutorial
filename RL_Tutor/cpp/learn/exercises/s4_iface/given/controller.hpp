#pragma once
#include <string>

// The INTERFACE: what every controller can do, and nothing about how.
// Code that runs controllers (a scheduler, a test, a GUI) depends only on
// this file -- so you can add a new controller without touching that code.
class Controller {
public:
    virtual ~Controller() = default;   // deleting through Controller* must reach the real destructor
    virtual double update(double ref, double meas, double dt) = 0;   // = 0: "pure", no default
    virtual void reset() = 0;
    virtual std::string name() const = 0;
};
