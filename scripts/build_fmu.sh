#!/usr/bin/env bash
# Compile a Modelica model to an FMU using OpenModelica in Docker.
#
# OpenModelica dropped macOS binaries after v1.16, so on a Mac the container is the
# supported path. The resulting FMU contains Linux binaries, so it must also be *run*
# inside the container -- see scripts/run_fmu.sh.
#
# Usage: scripts/build_fmu.sh model/ToolchainCheck.mo ToolchainCheck

set -euo pipefail

MO_FILE="${1:?usage: build_fmu.sh <path/to/Model.mo> <ModelName>}"
MODEL_NAME="${2:?usage: build_fmu.sh <path/to/Model.mo> <ModelName>}"
IMAGE="${OM_IMAGE:-openmodelica/openmodelica:v1.27.1-ompython}"
OUT_DIR="build"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$REPO_ROOT/$OUT_DIR"

# OpenModelica script: load the file, export an FMU, report any compile errors.
cat > "$REPO_ROOT/$OUT_DIR/build.mos" <<EOF
loadFile("/work/${MO_FILE}");
getErrorString();
translateModelFMU(${MODEL_NAME}, version="2.0", fmuType="cs");
getErrorString();
EOF

docker run --rm \
  -v "$REPO_ROOT":/work \
  -w "/work/$OUT_DIR" \
  "$IMAGE" \
  omc build.mos

echo "FMU written under $OUT_DIR/"
