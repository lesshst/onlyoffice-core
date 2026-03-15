#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-oo-documentserver-docx-html-arm64:latest}"

docker build \
  -f "${ROOT_DIR}/tools/docker/arm64-documentserver-custom/Dockerfile" \
  -t "${IMAGE_TAG}" \
  "${ROOT_DIR}"
