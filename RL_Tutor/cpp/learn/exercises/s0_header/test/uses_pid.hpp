// A second header that also needs Pid. Including both this and pid.hpp is
// completely normal -- and is exactly what an include guard is for.
#include "pid.hpp"
inline double runOnce(Pid& p, double e) { return p.update(e); }
