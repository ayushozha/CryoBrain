#!/usr/bin/env bash
set -euo pipefail

RELEASE="2026-06-20"
TAG="20260620"
DEST="${HOME}/utils/oss-cad-suite"
ARCHIVE="oss-cad-suite-linux-x64-${TAG}.tgz"
URL="https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${RELEASE}/${ARCHIVE}"

mkdir -p "${HOME}/utils"
cd "${HOME}/utils"

if [[ -x "${DEST}/bin/verilator" && -x "${DEST}/bin/yosys" ]]; then
  echo "OSS CAD Suite already installed at ${DEST}"
else
  echo "Downloading ${URL} ..."
  curl -fsSL -o "${ARCHIVE}" "${URL}"
  rm -rf "${DEST}"
  mkdir -p "${DEST}"
  tar -xzf "${ARCHIVE}" -C "${DEST}" --strip-components=1
  rm -f "${ARCHIVE}"
fi

export PATH="${DEST}/bin:${PATH}"
echo "verilator: $(verilator --version | head -1)"
echo "yosys: $(yosys -V | head -1)"
echo "z3: $(z3 -version | head -1)"
if command -v sby >/dev/null 2>&1; then
  echo "sby: $(sby --version | head -1)"
else
  echo "sby: missing — installing from SymbiYosys ..."
  git clone --depth 1 --branch yosys-0.47 https://github.com/YosysHQ/sby /tmp/sby
  make -C /tmp/sby install PREFIX="${DEST}"
  rm -rf /tmp/sby
  echo "sby: $(sby --version | head -1)"
fi

echo "OSS_CAD_BIN=${DEST}/bin"
