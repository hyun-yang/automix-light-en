#!/usr/bin/env bash
# Linux/macOS entry point for the shared Python guard.
PY=()
for cand in "python3" "python" "py -3"; do
  if [[ "$($cand -c 'import sys; print(sys.version_info[0])' 2>/dev/null)" == 3 ]]; then
    read -r -a PY <<<"$cand"
    break
  fi
done
(( ${#PY[@]} )) || exit 0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v cygpath >/dev/null 2>&1; then
  export AML_GUARD_TEMP_ROOT="$(cygpath -w /tmp)"
fi
"${PY[@]}" "$SCRIPT_DIR/aml-guard.py"
code=$?
[[ $code == 2 ]] && exit 2
exit 0
