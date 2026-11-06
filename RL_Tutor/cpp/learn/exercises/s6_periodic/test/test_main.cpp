#include <chrono>
#include <thread>
#include "check.hpp"
#include "periodic.hpp"

int main() {
    using namespace std::chrono;
    std::atomic<int> calls{0};
    {
        PeriodicWorker w;
        CHECK("start succeeds", w.start(milliseconds(2), [&] { ++calls; }));
        CHECK("running() after start", w.running());
        CHECK("a second start is refused while running", !w.start(milliseconds(2), [] {}));
        std::this_thread::sleep_for(milliseconds(120));
        w.stop();
        long n = w.ticks();
        CHECK("it ticked several times in 120 ms", n >= 3);
        CHECK("ticks() counts the calls to fn", n == calls.load());
        std::this_thread::sleep_for(milliseconds(30));
        CHECK_EQ("after stop() nothing runs", w.ticks(), n);
        w.stop();
        CHECK("stop() twice is harmless", !w.running());
        CHECK("can start again after stop", w.start(milliseconds(2), [] {}));
        std::this_thread::sleep_for(milliseconds(10));
    }   // destroyed while running: must stop+join, not std::terminate
    CHECK("destroying a running worker did not terminate the program", true);
    DONE();
}
