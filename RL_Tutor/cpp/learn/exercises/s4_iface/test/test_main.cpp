#include <memory>
#include <type_traits>
#include <vector>
#include "check.hpp"
#include "controllers.hpp"

int main() {
    CHECK("PidController is a Controller", (std::is_base_of_v<Controller, PidController>));
    CHECK("ImpedanceController is a Controller", (std::is_base_of_v<Controller, ImpedanceController>));
    std::vector<std::unique_ptr<Controller>> all;
    all.push_back(std::make_unique<PidController>(2.0, 1.0, 0.1));
    all.push_back(std::make_unique<ImpedanceController>(50.0, 2.0));
    CHECK_EQ("name through the base pointer", all[0]->name(), std::string("pid"));
    CHECK_EQ("name through the base pointer ", all[1]->name(), std::string("impedance"));

    Controller& pid = *all[0];
    CHECK_NEAR("pid first update (no D kick)", pid.update(1.0, 0.0, 0.01), 2.0 + 0.01, 1e-12);
    CHECK_NEAR("pid second update", pid.update(1.0, 0.5, 0.01),
               2.0 * 0.5 + 1.0 * (0.01 + 0.005) + 0.1 * (0.5 - 1.0) / 0.01, 1e-9);
    pid.reset();
    CHECK_NEAR("pid reset", pid.update(1.0, 0.0, 0.01), 2.01, 1e-12);

    Controller& imp = *all[1];
    CHECK_NEAR("impedance first update: spring only", imp.update(0.1, 0.0, 0.01), 5.0, 1e-12);
    CHECK_NEAR("impedance: spring minus damper", imp.update(0.1, 0.02, 0.01),
               50.0 * 0.08 - 2.0 * 2.0, 1e-9);
    imp.reset();
    CHECK_NEAR("impedance reset", imp.update(0.1, 0.02, 0.01), 50.0 * 0.08, 1e-12);
    DONE();
}
