#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-oo-arm64-runtime-build:latest}"
BUILD_JOBS="${BUILD_JOBS:-2}"

docker build \
  -t "${IMAGE_TAG}" \
  "${ROOT_DIR}/tools/docker/arm64-runtime-builder"

docker run --rm \
  -v "${ROOT_DIR}:/src" \
  -w /src \
  "${IMAGE_TAG}" \
  bash -lc "
    set -euo pipefail
    /usr/lib/qt5/bin/qmake -o /tmp/x2t-runtime.make X2tConverter/build/Qt/X2tConverter.pro
    make -f /tmp/x2t-runtime.make -j${BUILD_JOBS}
    if [ -d /opt/oo-boost-1.74/lib ]; then
      cp -a /opt/oo-boost-1.74/lib/libboost_date_time.so* build/bin/linux_64/
      cp -a /opt/oo-boost-1.74/lib/libboost_regex.so* build/bin/linux_64/
      cp -a /opt/oo-boost-1.74/lib/libboost_filesystem.so* build/bin/linux_64/
      cp -a /opt/oo-boost-1.74/lib/libboost_system.so* build/bin/linux_64/
      cp -a /opt/oo-boost-1.74/lib/libicudata.so* build/bin/linux_64/
      cp -a /opt/oo-boost-1.74/lib/libicui18n.so* build/bin/linux_64/
      cp -a /opt/oo-boost-1.74/lib/libicuuc.so* build/bin/linux_64/
    fi
    python3 tools/test_word_html_mapper_unit.py
    LD_LIBRARY_PATH=/src/build/bin/linux_64:\${LD_LIBRARY_PATH:-} ./build/bin/linux_64/x2t || true
  "
