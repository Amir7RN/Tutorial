"""A fixed sinusoidal example of notch selectivity and resonance drift."""
from .lesson_stories import movie, S

NOTCH_MOVIE = movie('A notch turns down one frequency, not every motion', 'notch_signal',
    S('Slow motion passes almost unchanged',
      'The input is a 4 Hz sinusoid. This illustrative notch stays centred at 18 Hz, '
      'with zero damping 0.015 and pole damping 0.15. Well below the notch, output '
      'amplitude is close to input amplitude. The dots show the instantaneous signal values.', f=4),
    S('At 18 Hz, the oscillatory command becomes smaller',
      'At the notch centre, gain is ζ_z / ζ_p = 0.1: only 10% of the input amplitude '
      'passes (−20 dB). Putting this filter before a resonant plant reduces its drive '
      'at that frequency. It does not remove the physical mode or stop an external disturbance.', f=18),
    S('A shifted resonance misses the deepest suppression',
      'Imagine the mode moves to 24 Hz after a payload change. The notch is still at '
      '18 Hz; about 89% of a 24 Hz component now passes. The filter has not failed, '
      'but it no longer targets the mode. Recheck the full loop and its margins in the lab below.', f=24),
    seconds=9)
