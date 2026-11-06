#pragma once
// Declarations only: every .cpp that includes this learns that clamp and
// g_ticks exist, and the linker finds the one definition in helpers.cpp.
double clamp(double x, double lo, double hi);
extern int g_ticks;
