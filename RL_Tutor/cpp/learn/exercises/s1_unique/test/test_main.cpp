#include <type_traits>
#include "alloc_count.hpp"
#include "check.hpp"
#include "joint.hpp"

int main() {
    long base = chk::liveAllocs();
    {
        auto p = makePd(2.0, 0.0);
        CHECK("makePd returns an owner (not null)", p != nullptr);
        if (p) CHECK_NEAR("with the gains you asked for", p->kp, 2.0, 0.0);

        Joint j;
        CHECK("a new joint has no controller", !j.hasController());
        CHECK_NEAR("no controller -> limp (0), not a crash", j.command(1.0, 0.01), 0.0, 0.0);

        j.setController(std::move(p));
        CHECK("after std::move the caller's pointer is empty", p == nullptr);
        CHECK("and the joint owns it", j.hasController());
        CHECK_NEAR("command runs the controller", j.command(0.5, 0.01), 1.0, 1e-12);

        long before = chk::liveAllocs();
        j.setController(makePd(1.0, 0.0));
        CHECK_EQ("replacing a controller frees the old one", chk::liveAllocs(), before);

        auto back = j.releaseController();
        CHECK("release hands it back", back != nullptr);
        CHECK("and the joint is empty again", !j.hasController());
        CHECK("Joint cannot be copied (it owns a unique_ptr)", !std::is_copy_constructible_v<Joint>);
    }
    CHECK_EQ("nothing leaked", chk::liveAllocs() - base, 0L);
    DONE();
}
