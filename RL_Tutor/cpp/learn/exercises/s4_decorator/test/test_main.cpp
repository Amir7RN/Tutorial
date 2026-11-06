#include "check.hpp"
#include "filtered.hpp"

int main() {
    CHECK_THROWS("null inner is refused", FilteredController(nullptr, 0.5));
    CHECK_THROWS("alpha 0 is refused", FilteredController(std::make_unique<PidController>(1, 0, 0), 0.0));
    CHECK_THROWS("alpha 1.5 is refused", FilteredController(std::make_unique<PidController>(1, 0, 0), 1.5));

    std::unique_ptr<Controller> c =
        std::make_unique<FilteredController>(std::make_unique<PidController>(2.0, 0.0, 0.0), 0.5);
    CHECK_EQ("name wraps the inner name", c->name(), std::string("filtered(pid)"));
    CHECK_NEAR("first call passes meas through", c->update(1.0, 0.4, 0.01), 2.0 * 0.6, 1e-12);
    CHECK_NEAR("second call: filt = 0.4 + 0.5*(0 - 0.4) = 0.2", c->update(1.0, 0.0, 0.01), 2.0 * 0.8, 1e-12);
    c->reset();
    CHECK_NEAR("reset: first-call rule again", c->update(1.0, 0.0, 0.01), 2.0, 1e-12);

    auto twice = std::make_unique<FilteredController>(
        std::make_unique<FilteredController>(std::make_unique<PidController>(1, 0, 0), 0.5), 0.5);
    CHECK_EQ("decorators stack", twice->name(), std::string("filtered(filtered(pid))"));
    DONE();
}
