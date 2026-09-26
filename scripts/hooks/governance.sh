#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd -P)"
cd "$root"
# -I -S ignore PYTHON* variables, the working directory and site-packages, and the
# repository is appended last, so agent-created json.py/hashlib.py cannot shadow stdlib.
exec python3 -I -S -c 'import sys; sys.path.append(sys.argv.pop(1)); from governance.hooks import main; main()' "$root" "$1"
