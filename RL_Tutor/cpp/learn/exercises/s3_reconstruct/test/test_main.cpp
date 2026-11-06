#include <type_traits>
#include "check.hpp"
#include "rate_limiter.hpp"

int main() {
    CHECK("no default constructor", !std::is_default_constructible_v<RateLimiter>);
    CHECK_THROWS("rejects maxRate <= 0", RateLimiter(0.0, 0.001));
    CHECK_THROWS("rejects dt <= 0", RateLimiter(1.0, 0.0));
    RateLimiter r(2.0, 0.01);
    const RateLimiter& view = r;
    CHECK_NEAR("maxStep = maxRate*dt (const)", view.maxStep(), 0.02, 1e-15);
    CHECK_NEAR("starts at 0 (const output())", view.output(), 0.0, 0.0);
    CHECK_NEAR("big target: moves by maxStep", r.step(1.0), 0.02, 1e-15);
    CHECK_NEAR("again", r.step(1.0), 0.04, 1e-15);
    CHECK_NEAR("small move is taken whole", r.step(0.05), 0.05, 1e-15);
    CHECK_NEAR("downward is limited too", r.step(-1.0), 0.03, 1e-15);
    r.reset(5.0);
    CHECK_NEAR("reset jumps", r.output(), 5.0, 0.0);
    DONE();
}
