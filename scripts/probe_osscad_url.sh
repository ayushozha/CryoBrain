#!/usr/bin/env bash
set -euo pipefail
for tag in 2026-06-20 2025-12-22 2025-08-29 2024-11-08; do
  for name in \
    "oss-cad-suite-${tag}-linux-amd64.tar.gz" \
    "oss-cad-suite-$(echo "$tag" | tr -d '-')-linux-amd64.tar.gz" \
    "oss-cad-suite-linux-x64-$(echo "$tag" | tr -d '-').tgz"; do
    url="https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${tag}/${name}"
    code=$(curl -fsSL -o /dev/null -w "%{http_code}" "$url" || true)
    echo "$code $url"
  done
done
