#include <type_traits>
#include <utility>
#include "check.hpp"
#include "joint_state.hpp"

template <class T, class = void> struct ConstSettable : std::false_type {};
template <class T>
struct ConstSettable<T, std::void_t<decltype(std::declval<const T&>().set(0, 0.0, 0.0))>> : std::true_type {};

int main() {
    JointState s(2);
    s.set(0, 0.3, 2.0);
    s.set(1, -0.1, -1.0);
    const JointState& view = s;
    CHECK_EQ("dof() works through a const reference", view.dof(), std::size_t(2));
    CHECK_NEAR("kineticEnergy compiles and is right", kineticEnergy(s, {0.5, 2.0}),
               0.5 * 0.5 * 4.0 + 0.5 * 2.0 * 1.0, 1e-12);
    using P = decltype(view.positions());
    CHECK("positions() returns const std::vector<double>& (no copy)",
          (std::is_same_v<P, const std::vector<double>&>));
    CHECK_NEAR("positions() reads the data", view.positions()[0], 0.3, 0.0);
    CHECK("set() is still NOT callable on a const JointState", !ConstSettable<JointState>::value);
    DONE();
}
