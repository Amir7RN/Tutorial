#pragma once
// The project's interface. Each loop is bound to a Signals at construction,
// so update() needs only the time step.
class Controller {
public:
    virtual ~Controller() = default;
    virtual void update(double dt) = 0;
    virtual const char* name() const = 0;
};
