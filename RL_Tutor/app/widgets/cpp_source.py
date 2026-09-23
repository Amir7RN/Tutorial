"""Load reviewed C++ regions; never silently show Python in a C++ code card."""
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'cpp'

@lru_cache(maxsize=1)
def catalog():
    regions = {}
    for path in ROOT.glob('*.hpp'):
        active = {}
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith('// BEGIN '):
                active[line.removeprefix('// BEGIN ')] = []
            elif line.startswith('// END '):
                key = line.removeprefix('// END ')
                if key in regions:
                    raise ValueError(f'Duplicate C++ example: {key}')
                import textwrap
                regions[key] = textwrap.dedent('\n'.join(active.pop(key)))
            else:
                for lines in active.values():
                    lines.append(line)
        if active:
            raise ValueError(f'Unclosed C++ examples in {path}')
    return regions

def get_example(key):
    return catalog()['example.' + key]

def get_cpp_source(obj):
    key = obj.__module__ + '.' + obj.__qualname__
    return catalog()[key]
