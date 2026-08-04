#!/usr/bin/env bash
# ===================================================================
#  RL Tutor -- macOS / Linux launcher
#
#      chmod +x run.sh     (once)
#      ./run.sh
#
#  First run creates a private virtual environment in .venv and
#  installs the dependencies INTO IT. Nothing touches your system
#  Python. To uninstall completely: delete this folder.
# ===================================================================
set -e
cd "$(dirname "$0")"

VENV=".venv"
VPY="$VENV/bin/python"

if [ ! -x "$VPY" ]; then
    echo
    echo "  First run - setting up. This happens once."
    echo

    PY=""
    for c in python3.13 python3.12 python3.11 python3.10 python3 python; do
        if command -v "$c" >/dev/null 2>&1 && \
           "$c" -c 'import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)' 2>/dev/null; then
            PY="$c"; break
        fi
    done

    if [ -z "$PY" ]; then
        echo "  ================================================================"
        echo "   Python 3.10 or newer was not found."
        echo
        echo "     macOS:         brew install python@3.12"
        echo "     Debian/Ubuntu: sudo apt install python3 python3-venv python3-pip"
        echo "     Or:            https://www.python.org/downloads/"
        echo "  ================================================================"
        exit 1
    fi

    echo "  Using: $($PY --version)"
    echo "  Creating virtual environment in .venv ..."
    "$PY" -m venv "$VENV"

    echo "  Installing PySide6, numpy, matplotlib ..."
    "$VPY" -m pip install --upgrade pip --quiet
    "$VPY" -m pip install -r requirements.txt --quiet
    echo "  Done."
    echo
fi

exec "$VPY" -m app.main "$@"
