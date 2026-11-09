#!/usr/bin/env bash
# Probe: can Transcrypt (Python -> JavaScript ahead of time) compile the unchanged engine?
#   bash probes/transcrypt.sh
# It cannot: it handles a "small sane subset" of Python 3.9. The output shows where it stops, first
# as is (relative imports), then with the imports rewritten (validators.py line 30: an `...` body).
set -u
here="$(cd "$(dirname "$0")" && pwd)"; backend="$(cd "$here/../../../../backend" && pwd)"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
python3 -m venv "$work/venv" && "$work/venv/bin/pip" install -q transcrypt==3.9.5
mkdir -p "$work/src/app" && cp "$backend/app/__init__.py" "$work/src/app/" \
  && cp -r "$backend/app/models" "$backend/app/views" "$work/src/app/" && find "$work/src" -name __pycache__ -prune -exec rm -rf {} +
printf 'from app.models import SimulationInput, simulate\nfrom app.views import simulation_to_dict\n' > "$work/src/entry.py"
cd "$work/src"
echo "== as is"
"$work/venv/bin/python" -m transcrypt -b -n entry.py 2>&1 | grep -v '^\s*/' | grep -E "Error|error|import|Aborted|namely" | head -5
echo "== relative imports rewritten to absolute"
sed -i -E 's/^from \.([a-z_]+) import/from app.models.\1 import/' app/models/*.py
sed -i -E 's/^from \.([a-z_]+) import/from app.views.\1 import/' app/views/*.py
"$work/venv/bin/python" -m transcrypt -b -n entry.py 2>&1 | grep -v '^\s*/' | grep -E "Error|error|import|Aborted|namely|File" | head -8
echo '(app/models/validators.py line 30 is "...", the body of the abstract method Validator.validate)'
