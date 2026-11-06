#include "check.hpp"
#include "factory.hpp"

int main() {
    double v = 0;
    CHECK("parseNumber accepts 2.5", parseNumber("2.5", v) && v == 2.5);
    CHECK("parseNumber rejects 2x", !parseNumber("2x", v));
    CHECK("parseNumber rejects empty", !parseNumber("", v));
    CHECK("parseNumber rejects abc", !parseNumber("abc", v));

    auto p = makeController("pid kp=2 ki=0.5");
    CHECK("pid line builds something", p != nullptr);
    if (p) {
        CHECK_EQ("it is a pid", p->name(), std::string("pid"));
        CHECK_NEAR("kp=2, ki=0.5, kd defaulted to 0", p->update(1.0, 0.0, 0.01), 2.005, 1e-12);
    }
    auto q = makeController("  impedance   k=50  b=2 ");
    CHECK("extra spaces are fine", q != nullptr);
    if (q) CHECK_NEAR("impedance gains", q->update(0.1, 0.0, 0.01), 5.0, 1e-12);

    CHECK("empty line -> nullptr", makeController("") == nullptr);
    CHECK("unknown type -> nullptr", makeController("lqr q=1") == nullptr);
    CHECK("bad number -> nullptr", makeController("pid kp=abc") == nullptr);
    CHECK("half a number -> nullptr", makeController("pid kp=2x") == nullptr);
    CHECK("unknown key -> nullptr", makeController("pid kq=1") == nullptr);
    CHECK("key of the other type -> nullptr", makeController("impedance kp=1") == nullptr);
    CHECK("token without = -> nullptr", makeController("pid kp=2 fast") == nullptr);
    DONE();
}
