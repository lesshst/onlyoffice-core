#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-oo-documentserver-docx-html-arm64}"
IMAGE_ARCH="${IMAGE_ARCH:-arm64}"
BASE_VERSION="${BASE_VERSION:-0.0.1}"
GIT_REV="${GIT_REV:-$(git -C "${ROOT_DIR}" rev-parse --short=7 HEAD 2>/dev/null || echo "nogit")}"
BUILD_TIME="${BUILD_TIME:-$(date +"%Y%m%d_%H%M%S")}"
DEFAULT_IMAGE_TAG="${IMAGE_REPOSITORY}:${IMAGE_ARCH}.${GIT_REV}.${BUILD_TIME}.${BASE_VERSION}"
IMAGE_TAG="${IMAGE_TAG:-${DEFAULT_IMAGE_TAG}}"
LATEST_ALIAS="${LATEST_ALIAS:-${IMAGE_REPOSITORY}:latest}"
WRITE_TAG_FILE="${WRITE_TAG_FILE:-${ROOT_DIR}/tools/.last_documentserver_image_tag}"
TAG_LATEST_ALIAS="${TAG_LATEST_ALIAS:-true}"

docker build \
  -f "${ROOT_DIR}/tools/docker/arm64-documentserver-custom/Dockerfile" \
  -t "${IMAGE_TAG}" \
  "${ROOT_DIR}"

if [[ "${TAG_LATEST_ALIAS}" == "true" && "${IMAGE_TAG}" != "${LATEST_ALIAS}" ]]; then
  docker tag "${IMAGE_TAG}" "${LATEST_ALIAS}"
fi

mkdir -p "$(dirname "${WRITE_TAG_FILE}")"
printf '%s\n' "${IMAGE_TAG}" > "${WRITE_TAG_FILE}"
printf 'built image: %s\n' "${IMAGE_TAG}"
if [[ "${TAG_LATEST_ALIAS}" == "true" && "${IMAGE_TAG}" != "${LATEST_ALIAS}" ]]; then
  printf 'latest alias: %s\n' "${LATEST_ALIAS}"
fi
printf 'tag file: %s\n' "${WRITE_TAG_FILE}"
