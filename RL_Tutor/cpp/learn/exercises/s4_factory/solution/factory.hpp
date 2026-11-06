#pragma once
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include "controllers.hpp"

inline bool parseNumber(const std::string& s, double& out) {
    if (s.empty()) return false;
    try {
        std::size_t used = 0;
        out = std::stod(s, &used);
        return used == s.size();
    } catch (...) {
        return false;
    }
}

inline std::unique_ptr<Controller> makeController(const std::string& line) {
    std::istringstream in(line);
    std::string type, tok;
    if (!(in >> type)) return nullptr;

    std::map<std::string, double> kv;
    while (in >> tok) {
        auto eq = tok.find('=');
        double v;
        if (eq == std::string::npos || !parseNumber(tok.substr(eq + 1), v)) return nullptr;
        kv[tok.substr(0, eq)] = v;
    }
    auto onlyKeys = [&](std::set<std::string> allowed) {
        for (auto& [k, v] : kv) if (!allowed.count(k)) return false;
        return true;
    };
    auto get = [&](const char* k) { auto it = kv.find(k); return it == kv.end() ? 0.0 : it->second; };

    if (type == "pid" && onlyKeys({"kp", "ki", "kd"}))
        return std::make_unique<PidController>(get("kp"), get("ki"), get("kd"));
    if (type == "impedance" && onlyKeys({"k", "b"}))
        return std::make_unique<ImpedanceController>(get("k"), get("b"));
    return nullptr;
}
