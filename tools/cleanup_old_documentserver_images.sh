#!/usr/bin/env bash
set -euo pipefail

IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-oo-documentserver-docx-html-arm64}"
LATEST_ALIAS="${LATEST_ALIAS:-latest}"
DRY_RUN="${DRY_RUN:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRITE_TAG_FILE="${WRITE_TAG_FILE:-${SCRIPT_DIR}/.last_documentserver_image_tag}"

build_sort_key() {
  local tag="$1"
  if [[ "${tag}" =~ ^arm64\.([0-9a-f]{7,})\.([0-9]{8}_[0-9]{6})\.0\.0\.1$ ]]; then
    printf '3:%s\n' "${BASH_REMATCH[2]}"
    return
  fi
  if [[ "${tag}" =~ ^arm64\.([0-9]{8}_[0-9]{4,6})\.0\.0\.1$ ]]; then
    local ts="${BASH_REMATCH[1]}"
    if [[ "${#ts}" -eq 13 ]]; then
      ts="${ts}00"
    fi
    printf '2:%s\n' "${ts}"
    return
  fi
  printf '1:%s\n' "${tag}"
}

image_rows=()
while IFS= read -r row; do
  image_rows+=("${row}")
done < <(
  docker images --format '{{.Repository}} {{.Tag}} {{.ID}} {{.CreatedAt}}' "${IMAGE_REPOSITORY}" \
    | awk '$2 != "<none>"'
)

if [[ "${#image_rows[@]}" -eq 0 ]]; then
  printf 'No images found for repository %s\n' "${IMAGE_REPOSITORY}"
  exit 0
fi

latest_tag=""
latest_id=""
latest_sort_key=""

for row in "${image_rows[@]}"; do
  tag="$(awk '{print $2}' <<<"${row}")"
  image_id="$(awk '{print $3}' <<<"${row}")"

  if [[ "${tag}" == "${LATEST_ALIAS}" ]]; then
    continue
  fi

  sort_key="$(build_sort_key "${tag}")"

  if [[ -z "${latest_sort_key}" || "${sort_key}" > "${latest_sort_key}" ]]; then
    latest_sort_key="${sort_key}"
    latest_tag="${tag}"
    latest_id="${image_id}"
  fi
done

if [[ -z "${latest_tag}" ]]; then
  printf 'No versioned image tags found for repository %s\n' "${IMAGE_REPOSITORY}" >&2
  exit 1
fi

printf 'Keeping latest image: %s:%s (%s)\n' "${IMAGE_REPOSITORY}" "${latest_tag}" "${latest_id}"

latest_alias_target_id="$(
  docker images --format '{{.Repository}} {{.Tag}} {{.ID}}' "${IMAGE_REPOSITORY}" \
    | awk -v alias="${LATEST_ALIAS}" '$2 == alias { print $3; exit }'
)"

if [[ "${latest_alias_target_id}" != "${latest_id}" ]]; then
  if [[ "${DRY_RUN}" == "true" ]]; then
    if [[ -n "${latest_alias_target_id}" ]]; then
      printf '[dry-run] docker rmi %s:%s\n' "${IMAGE_REPOSITORY}" "${LATEST_ALIAS}"
    fi
    printf '[dry-run] docker tag %s:%s %s:%s\n' "${IMAGE_REPOSITORY}" "${latest_tag}" "${IMAGE_REPOSITORY}" "${LATEST_ALIAS}"
  else
    if [[ -n "${latest_alias_target_id}" ]]; then
      docker rmi "${IMAGE_REPOSITORY}:${LATEST_ALIAS}" >/dev/null 2>&1 || true
    fi
    docker tag "${IMAGE_REPOSITORY}:${latest_tag}" "${IMAGE_REPOSITORY}:${LATEST_ALIAS}"
  fi
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  printf '[dry-run] write latest tag to %s\n' "${WRITE_TAG_FILE}"
else
  printf '%s:%s\n' "${IMAGE_REPOSITORY}" "${latest_tag}" > "${WRITE_TAG_FILE}"
fi

for row in "${image_rows[@]}"; do
  tag="$(awk '{print $2}' <<<"${row}")"
  image_id="$(awk '{print $3}' <<<"${row}")"

  if [[ "${tag}" == "${latest_tag}" ]]; then
    continue
  fi

  if [[ "${tag}" == "${LATEST_ALIAS}" && "${image_id}" == "${latest_id}" ]]; then
    continue
  fi

  if [[ "${DRY_RUN}" == "true" ]]; then
    printf '[dry-run] docker rmi %s:%s\n' "${IMAGE_REPOSITORY}" "${tag}"
  else
    docker rmi "${IMAGE_REPOSITORY}:${tag}"
  fi
done

printf 'Cleanup finished for %s\n' "${IMAGE_REPOSITORY}"
