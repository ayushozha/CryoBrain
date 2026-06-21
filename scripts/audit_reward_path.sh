#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RG_BIN=""
for candidate in rg.exe rg; do
  while IFS= read -r path; do
    if [[ -x "$path" ]]; then
      RG_BIN="$path"
      break 2
    fi
  done < <(type -ap "$candidate" 2>/dev/null || true)
done

if [[ -z "$RG_BIN" ]]; then
  echo "audit_reward_path: ripgrep (rg) is required" >&2
  exit 127
fi

paths=()
for path in cryobrain tasks/cryo_brain_decoder scripts; do
  if [[ -e "$path" ]]; then
    paths+=("$path")
  fi
done

if [[ ${#paths[@]} -eq 0 ]]; then
  echo "audit_reward_path: no production paths found" >&2
  exit 1
fi

sym_a="simulate_candidate"
sym_a+="_ler"
sym_b="decoder_quality"
sym_b+="_multiplier"
module='cryobrain\.accuracy\.decoder_policy'
forbidden="${sym_a}|${sym_b}|${module}"

set +e
matches="$("$RG_BIN" -n \
  --glob '*.py' \
  --glob '*.sh' \
  --glob '!**/tests/**' \
  --glob '!**/__pycache__/**' \
  --glob '!scripts/audit_reward_path.sh' \
  --glob '!tasks/**/donotaccess/grade.pyc' \
  "$forbidden" \
  "${paths[@]}" 2>&1)"
status=$?
set -e

if [[ $status -eq 0 ]]; then
  printf '%s\n' "$matches"
  echo "audit_reward_path: proxy/formula LER path found in production sources" >&2
  exit 1
elif [[ $status -ne 1 ]]; then
  printf '%s\n' "$matches" >&2
  echo "audit_reward_path: source scan failed" >&2
  exit "$status"
fi

echo "audit_reward_path: no proxy/formula LER production references found"
