#pragma once
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include "controllers.hpp"

// A factory turns DATA (a line of config) into an OBJECT, so the code that
// reads the config never names PidController or ImpedanceController.
//
//   "pid kp=2 ki=0.5 kd=0.01"     any missing gain defaults to 0
//   "impedance k=50 b=2"
//
// Return nullptr -- never throw, never crash -- for: an empty line, an unknown
// type, a token without '=', a key the type does not have, or a value that is
// not entirely a number ("2x", "abc", "").
//
// Suggested shape:
//   1. std::istringstream in(line); in >> type;
//   2. read every remaining token into a std::map<std::string, double>,
//      failing on a bad token (helper below)
//   3. check the keys against the type's allowed keys, then construct.
inline bool parseNumber(const std::string& s, double& out) {
    // TODO: true only if ALL of s is a number.  std::stod(s, &used) and check
    //       used == s.size(); catch the exception stod throws on garbage.
    return false;
}

inline std::unique_ptr<Controller> makeController(const std::string& line) {
    return nullptr;   // TODO
}
