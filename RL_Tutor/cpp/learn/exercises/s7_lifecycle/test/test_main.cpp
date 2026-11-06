#include <cmath>
#include "check.hpp"
#include "managed_controller.hpp"

int main() {
    double cmd = 42.0;
    ManagedController c;
    CHECK("starts Unconfigured", c.state() == State::Unconfigured);
    CHECK("cannot activate before configure", !c.activate(&cmd) && c.state() == State::Unconfigured);
    CHECK("update does nothing when not Active", !c.update(1.0, 0.0) && cmd == 42.0);
    CHECK("configure rejects kp < 0", !c.configure(-1.0) && c.state() == State::Unconfigured);
    CHECK("configure rejects NaN", !c.configure(NAN) && c.state() == State::Unconfigured);
    CHECK("configure(2)", c.configure(2.0) && c.state() == State::Inactive);
    CHECK("configure twice is refused", !c.configure(3.0));
    CHECK("activate rejects nullptr", !c.activate(nullptr) && c.state() == State::Inactive);
    CHECK("activate", c.activate(&cmd) && c.state() == State::Active);
    CHECK("update writes kp*(ref-meas)", c.update(1.0, 0.25) && cmd == 1.5);
    CHECK("deactivate", c.deactivate() && c.state() == State::Inactive);
    CHECK("deactivate leaves the command at 0", cmd == 0.0);
    cmd = 7.0;
    CHECK("inactive: update is refused", !c.update(1.0, 0.0) && cmd == 7.0);
    CHECK("cleanup", c.cleanup() && c.state() == State::Unconfigured);
    CHECK("reconfigure and activate", c.configure(1.0) && c.activate(&cmd));
    CHECK("shutdown from Active", c.shutdown() && c.state() == State::Finalized && cmd == 0.0);
    CHECK("nothing works once Finalized", !c.configure(1.0) && !c.shutdown() && !c.update(1, 0));
    DONE();
}
