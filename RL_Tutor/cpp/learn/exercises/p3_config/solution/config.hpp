#pragma once
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include "loops.hpp"
#include "scheduler.hpp"

inline std::unique_ptr<Scheduler> buildFromConfig(const std::string& text, int baseHz,
                                                  Signals& s, std::string* error) {
    auto fail = [&](int n, const std::string& msg) {
        if (error) *error = "line " + std::to_string(n) + ": " + msg;
        return std::unique_ptr<Scheduler>();
    };
    auto num = [](const std::string& t, double& out) {
        try {
            std::size_t used = 0;
            out = std::stod(t, &used);
            return used == t.size();
        } catch (...) {
            return false;
        }
    };

    auto sched = std::make_unique<Scheduler>(baseHz);
    std::istringstream lines(text);
    std::string line;
    int n = 0;
    while (std::getline(lines, line)) {
        ++n;
        std::istringstream in(line);
        std::string type, rateTok, tok;
        if (!(in >> type) || type[0] == '#') continue;

        std::set<std::string> allowed;
        if (type == "position") allowed = {"kp", "limit"};
        else if (type == "velocity" || type == "current") allowed = {"kp", "ki", "limit"};
        else return fail(n, "unknown type '" + type + "'");

        double rate = 0;
        if (!(in >> rateTok) || !num(rateTok, rate) || rate != static_cast<int>(rate))
            return fail(n, "missing or non-integer rate");

        std::map<std::string, double> kv;
        while (in >> tok) {
            auto eq = tok.find('=');
            if (eq == std::string::npos) return fail(n, "expected key=value, got '" + tok + "'");
            std::string key = tok.substr(0, eq);
            double v;
            if (!num(tok.substr(eq + 1), v)) return fail(n, "bad number in '" + tok + "'");
            if (!allowed.count(key)) return fail(n, type + " has no key '" + key + "'");
            kv[key] = v;
        }
        if (!kv.count("limit")) return fail(n, "missing limit");
        double kp = kv.count("kp") ? kv["kp"] : 0.0, ki = kv.count("ki") ? kv["ki"] : 0.0;

        std::unique_ptr<Controller> c;
        if (type == "position") c = std::make_unique<PositionLoop>(s, kp, kv["limit"]);
        else if (type == "velocity") c = std::make_unique<VelocityLoop>(s, kp, ki, kv["limit"]);
        else c = std::make_unique<CurrentLoop>(s, kp, ki, kv["limit"]);
        if (!sched->add(std::move(c), static_cast<int>(rate)))
            return fail(n, "the scheduler refused rate " + rateTok);
    }
    return sched;
}
