"""Exact two-inertia teaching model; all motor coordinates are output-referred.

No grounding stiffness or active control. The undamped harmonic solution is a
particular solution, not a transient simulation. Singular resonances are explicit.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SeaModel:
    jm: float = .04
    jl: float = .06
    k: float = 300.

    def __post_init__(self):
        if min(self.jm, self.jl, self.k) <= 0:
            raise ValueError('Inertias and stiffness must be positive')

    @property
    def wn(self):
        """Imposed motor-angle resonance; also motor driving-point antiresonance."""
        return math.sqrt(self.k / self.jl)

    @property
    def wa(self):
        """Load driving-point antiresonance."""
        return math.sqrt(self.k / self.jm)

    @property
    def wr(self):
        """Free two-inertia relative-mode natural frequency."""
        return math.sqrt(self.k * (1 / self.jm + 1 / self.jl))

    def harmonic(self, omega, drive='load', damping=0.):
        """Complex angles for 1 N m torque at one port; the other torque is zero."""
        if drive not in ('motor', 'load'):
            raise ValueError(drive)
        d = complex(self.k, damping * omega)
        am, al = d - self.jm * omega**2, d - self.jl * omega**2
        determinant = am * al - d*d
        if abs(determinant) < 1e-10 * max(abs(am*al), abs(d*d), 1):
            raise ValueError('No bounded undamped forced response at this resonance')
        return (al / determinant, d / determinant) if drive == 'motor' else (d / determinant, am / determinant)

    def imposed_motor(self, omega, damping=0.):
        d = complex(self.k, damping * omega)
        denominator = d - self.jl * omega**2
        if abs(denominator) < 1e-10 * self.k:
            raise ValueError('Imposed-motion resonance: no bounded undamped response')
        return 1+0j, d / denominator

    def apparent_inertia(self, omega):
        xm, xl = self.harmonic(omega, 'load')
        if abs(xl) < 1e-12:
            return math.inf
        return (1 / (-omega**2 * xl)).real
