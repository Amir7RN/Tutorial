// check.hpp -- the tiny test harness every exercise's test_main.cpp uses.
// Each check prints one line: "PASS name" or "FAIL name | why".
// The tutor reads those lines; you can read them too.
#pragma once
#include <cmath>
#include <iostream>
#include <sstream>
#include <string>

namespace chk {
inline int& failures() { static int f = 0; return f; }

inline void report(const std::string& name, bool ok, const std::string& why = "") {
    std::cout << (ok ? "PASS " : "FAIL ") << name;
    if (!ok && !why.empty()) std::cout << " | " << why;
    std::cout << std::endl;
    if (!ok) ++failures();
}

template <class A, class B>
std::string gotWant(const A& got, const B& want) {
    std::ostringstream s;
    s << "got " << got << ", expected " << want;
    return s.str();
}
}  // namespace chk

#define CHECK(name, cond) ::chk::report(name, static_cast<bool>(cond), "this was false: " #cond)
#define CHECK_EQ(name, got, want) do { auto g_ = (got); auto w_ = (want); \
    ::chk::report(name, g_ == w_, ::chk::gotWant(g_, w_)); } while (0)
#define CHECK_NEAR(name, got, want, tol) do { double g_ = (got), w_ = (want); \
    ::chk::report(name, std::fabs(g_ - w_) <= (tol), ::chk::gotWant(g_, w_)); } while (0)
#define CHECK_THROWS(name, expr) do { bool t_ = false; try { (void)(expr); } catch (...) { t_ = true; } \
    ::chk::report(name, t_, "expected an exception from: " #expr); } while (0)
#define CHECK_NOTHROW(name, expr) do { bool t_ = true; try { (void)(expr); } catch (...) { t_ = false; } \
    ::chk::report(name, t_, "unexpected exception from: " #expr); } while (0)
#define DONE() do { std::cout << "DONE" << std::endl; return 0; } while (0)
