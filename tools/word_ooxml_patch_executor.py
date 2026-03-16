#!/usr/bin/env python3
"""
Test/validation-only OOXML patch helper.

This module exists inside ONLYOFFICE-core so the mapper validation tools and
unit tests can reuse the exact same OOXML-path parsing and paragraph-level text
replacement logic when validating `docx -> html` mappings.

It is NOT the production patch executor anymore. The live audit patch chain now
uses the backend-local executor in:

    03-write-doc/backend/app/services/word_ooxml_patch_executor.py

Supported parts:
- word/document.xml
- word/header*.xml
- word/footer*.xml
- word/footnotes.xml
- word/endnotes.xml

Supported target nodes:
- w:p paragraphs, including paragraphs nested inside tables and textboxes
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W_NS}

ET.register_namespace("w", W_NS)

VALIDATION_ONLY_NOTICE = (
    "ONLYOFFICE-core/tools/word_ooxml_patch_executor.py is a test/validation "
    "helper. Production audit patch execution lives in "
    "03-write-doc/backend/app/services/word_ooxml_patch_executor.py."
)

SUPPORTED_PART_PATTERNS = (
    re.compile(r"^word/document\.xml$"),
    re.compile(r"^word/header\d+\.xml$"),
    re.compile(r"^word/footer\d+\.xml$"),
    re.compile(r"^word/footnotes\.xml$"),
    re.compile(r"^word/endnotes\.xml$"),
)


@dataclass
class PatchIssue:
    matched_text: str
    suggested_text: str
    start: int
    end: int


@dataclass
class PatchOperation:
    issue: PatchIssue
    applied_ooxml_path: str
    applied_preferred_start: int | None = None
    applied_part_name: str = "word/document.xml"
    applied_container_id: str | None = None


@dataclass
class PatchResult:
    applied_count: int = 0
    skipped_count: int = 0


def is_supported_part_name(part_name: str) -> bool:
    name = str(part_name or "").strip().lstrip("/")
    return any(pattern.fullmatch(name) for pattern in SUPPORTED_PART_PATTERNS)


def _local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1]


def _parse_segment(segment: str) -> tuple[str, int | None]:
    raw = str(segment or "").strip()
    if not raw:
        raise ValueError("empty OOXML path segment")
    if ":" in raw:
        raw = raw.split(":", 1)[1]
    m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)(?:\[(\d+)\])?", raw)
    if not m:
        raise ValueError(f"invalid OOXML path segment: {segment!r}")
    name = m.group(1)
    index = int(m.group(2)) if m.group(2) else None
    return name, index


def resolve_ooxml_path(root: ET.Element, path: str) -> ET.Element | None:
    segments = [seg for seg in str(path or "").strip().split("/") if seg]
    if not segments:
        return None

    root_name, _ = _parse_segment(segments[0])
    if _local_name(root.tag) != root_name:
        return None

    current = root
    for segment in segments[1:]:
        name, index = _parse_segment(segment)
        children = list(current)
        if index is None:
            next_node = next((child for child in children if _local_name(child.tag) == name), None)
        else:
            if index < 1 or index > len(children):
                return None
            next_node = children[index - 1]
            if _local_name(next_node.tag) != name:
                return None
        if next_node is None:
            return None
        current = next_node
    return current


def _iter_runs(paragraph: ET.Element) -> list[ET.Element]:
    return list(paragraph.findall(".//w:r", NS))


def _run_text(run: ET.Element) -> str:
    parts: list[str] = []
    for node in list(run):
        local = _local_name(node.tag)
        if local == "t":
            parts.append(node.text or "")
        elif local in {"tab", "cr", "br"}:
            parts.append(" ")
    return "".join(parts)


def _set_run_text(run: ET.Element, text: str) -> None:
    preserve = False
    for child in list(run):
        local = _local_name(child.tag)
        if local == "rPr":
            continue
        if local == "t" and child.attrib.get(f"{{{XML_NS}}}space") == "preserve":
            preserve = True
        run.remove(child)

    if not text:
        return

    text_el = ET.Element(f"{{{W_NS}}}t")
    if preserve or text[:1].isspace() or text[-1:].isspace():
        text_el.set(f"{{{XML_NS}}}space", "preserve")
    text_el.text = text
    run.append(text_el)


def paragraph_text_for_matching(paragraph: ET.Element) -> tuple[str, list[int]]:
    chars: list[str] = []
    index_map: list[int] = []
    logical_cursor = 0

    for run in _iter_runs(paragraph):
        for node in list(run):
            local = _local_name(node.tag)
            if local == "t":
                text = node.text or ""
                for ch in text:
                    chars.append(ch)
                    index_map.append(logical_cursor)
                    logical_cursor += 1
                continue
            if local in {"tab", "cr", "br"}:
                chars.append(" ")
                index_map.append(logical_cursor)
                logical_cursor += 1

    return "".join(chars), index_map


def _find_nearest_occurrence(haystack: str, needle: str, prefer_index: int) -> int:
    if not needle:
        return -1
    positions: list[int] = []
    start = 0
    while True:
        pos = haystack.find(needle, start)
        if pos < 0:
            break
        positions.append(pos)
        start = pos + 1
    if not positions:
        return -1
    if prefer_index < 0:
        return positions[0]
    return min(positions, key=lambda pos: (abs(pos - prefer_index), pos))


def _normalize_text_with_index_map(text: str) -> tuple[str, list[int]]:
    raw = str(text or "").replace("\u00a0", " ")
    chars: list[str] = []
    index_map: list[int] = []
    pending_space = False
    pending_space_index = -1

    for idx, ch in enumerate(raw):
        if ch.isspace():
            if chars:
                pending_space = True
                pending_space_index = idx
            continue
        if pending_space:
            chars.append(" ")
            index_map.append(pending_space_index)
            pending_space = False
            pending_space_index = -1
        chars.append(ch)
        index_map.append(idx)

    return "".join(chars), index_map


def resolve_match_range(
    paragraph_text: str,
    paragraph_index_map: list[int],
    matched_text: str,
    start: int,
    end: int,
    prefer_index: int | None,
) -> tuple[int, int] | None:
    if not matched_text:
        return None

    def map_visible_range(start_idx: int, end_idx: int) -> tuple[int, int] | None:
        if start_idx < 0 or end_idx <= start_idx:
            return None
        if start_idx >= len(paragraph_index_map) or end_idx - 1 >= len(paragraph_index_map):
            return None
        return paragraph_index_map[start_idx], paragraph_index_map[end_idx - 1] + 1

    if prefer_index is not None:
        nearest = _find_nearest_occurrence(paragraph_text, matched_text, prefer_index)
        if nearest >= 0:
            return map_visible_range(nearest, nearest + len(matched_text))

    if start >= 0 and end > start and end <= len(paragraph_text) and paragraph_text[start:end] == matched_text:
        return map_visible_range(start, end)

    nearest = _find_nearest_occurrence(paragraph_text, matched_text, -1)
    if nearest >= 0:
        return map_visible_range(nearest, nearest + len(matched_text))

    normalized_paragraph, normalized_to_original = _normalize_text_with_index_map(paragraph_text)
    normalized_matched, _ = _normalize_text_with_index_map(matched_text)
    if not normalized_paragraph or not normalized_matched:
        return None

    normalized_prefer_index = None
    if prefer_index is not None and prefer_index >= 0:
        normalized_prefer_index = len(_normalize_text_with_index_map(paragraph_text[:prefer_index])[0])

    normalized_pos = -1
    if normalized_prefer_index is not None:
        normalized_pos = _find_nearest_occurrence(normalized_paragraph, normalized_matched, normalized_prefer_index)
    if normalized_pos < 0:
        normalized_pos = _find_nearest_occurrence(normalized_paragraph, normalized_matched, -1)
    if normalized_pos < 0:
        return None

    normalized_last = normalized_pos + len(normalized_matched) - 1
    if normalized_last >= len(normalized_to_original):
        return None
    mapped_start = normalized_to_original[normalized_pos]
    mapped_end = normalized_to_original[normalized_last]
    if mapped_start >= len(paragraph_index_map) or mapped_end >= len(paragraph_index_map):
        return None
    return paragraph_index_map[mapped_start], paragraph_index_map[mapped_end] + 1


def _shrink_replacement_range(start: int, end: int, matched_text: str, replacement: str) -> tuple[int, int, str] | None:
    if matched_text == replacement:
        return None

    prefix = 0
    max_prefix = min(len(matched_text), len(replacement))
    while prefix < max_prefix and matched_text[prefix] == replacement[prefix]:
        prefix += 1

    suffix = 0
    max_suffix = min(len(matched_text) - prefix, len(replacement) - prefix)
    while suffix < max_suffix and matched_text[len(matched_text) - 1 - suffix] == replacement[len(replacement) - 1 - suffix]:
        suffix += 1

    new_start = start + prefix
    new_end = end - suffix
    new_replacement = replacement[prefix : len(replacement) - suffix if suffix else len(replacement)]
    return new_start, new_end, new_replacement


def replace_text_in_paragraph(paragraph: ET.Element, start: int, end: int, replacement: str) -> bool:
    if start < 0 or end < start:
        return False
    runs = _iter_runs(paragraph)
    if not runs:
        return False

    cursor = 0
    ranges: list[tuple[int, int]] = []
    for run in runs:
        txt = _run_text(run)
        ranges.append((cursor, cursor + len(txt)))
        cursor += len(txt)

    first_idx = -1
    last_idx = -1
    for idx, (run_start, run_end) in enumerate(ranges):
        if end <= run_start:
            break
        if start < run_end and end > run_start:
            if first_idx < 0:
                first_idx = idx
            last_idx = idx

    if first_idx < 0 or last_idx < 0:
        return False

    first_run = runs[first_idx]
    last_run = runs[last_idx]
    first_start, _ = ranges[first_idx]
    last_start, _ = ranges[last_idx]
    first_text = _run_text(first_run)
    last_text = _run_text(last_run)
    first_before = first_text[: max(0, start - first_start)]
    last_after = last_text[max(0, end - last_start) :]

    if first_idx == last_idx:
        _set_run_text(first_run, f"{first_before}{replacement}{last_after}")
        return True

    _set_run_text(first_run, f"{first_before}{replacement}")
    for idx in range(first_idx + 1, last_idx):
        _set_run_text(runs[idx], "")
    _set_run_text(last_run, last_after)
    return True


def parse_operations(raw: list[dict]) -> list[PatchOperation]:
    operations: list[PatchOperation] = []
    for row in raw:
        issue = row.get("issue") or {}
        operations.append(
            PatchOperation(
                issue=PatchIssue(
                    matched_text=str(issue.get("matched_text") or ""),
                    suggested_text=str(issue.get("suggested_text") or ""),
                    start=int(issue.get("loc", {}).get("start") or 0),
                    end=int(issue.get("loc", {}).get("end") or 0),
                ),
                applied_ooxml_path=str(row.get("applied_ooxml_path") or "").strip(),
                applied_preferred_start=(
                    int(row["applied_preferred_start"])
                    if row.get("applied_preferred_start") is not None
                    else None
                ),
                applied_part_name=str(row.get("applied_part_name") or "word/document.xml"),
                applied_container_id=str(row.get("applied_container_id") or "").strip() or None,
            )
        )
    return operations


def apply_operations_to_xml_root(root: ET.Element, operations: Iterable[PatchOperation]) -> PatchResult:
    result = PatchResult()
    grouped: dict[str, list[PatchOperation]] = {}
    for op in operations:
        if not op.applied_ooxml_path:
            raise ValueError("missing applied_ooxml_path")
        grouped.setdefault(op.applied_ooxml_path, []).append(op)

    for path, path_ops in grouped.items():
        paragraph = resolve_ooxml_path(root, path)
        if paragraph is None:
            raise ValueError(f"OOXML path not found: {path}")
        if _local_name(paragraph.tag) != "p":
            raise ValueError(f"OOXML path does not point to paragraph: {path}")

        paragraph_text, index_map = paragraph_text_for_matching(paragraph)
        resolved_items: list[tuple[int, int, str, PatchOperation]] = []
        for op in path_ops:
            prefer_index = op.applied_preferred_start if op.applied_preferred_start is not None else op.issue.start
            resolved = resolve_match_range(
                paragraph_text,
                index_map,
                op.issue.matched_text,
                op.issue.start,
                op.issue.end,
                prefer_index,
            )
            if not resolved:
                suggested_resolved = resolve_match_range(
                    paragraph_text,
                    index_map,
                    op.issue.suggested_text,
                    op.issue.start,
                    op.issue.end,
                    prefer_index,
                )
                if suggested_resolved:
                    result.skipped_count += 1
                    continue
                raise ValueError(
                    f"target text not found at {path}: matched={op.issue.matched_text!r} paragraph={paragraph_text!r}"
                )

            shrunk = _shrink_replacement_range(resolved[0], resolved[1], op.issue.matched_text, op.issue.suggested_text)
            if shrunk is None:
                result.skipped_count += 1
                continue
            resolved_items.append((shrunk[0], shrunk[1], shrunk[2], op))

        resolved_items.sort(key=lambda item: (-item[0], -item[1]))
        for idx, (start, end, replacement, _op) in enumerate(resolved_items):
            for prev_start, prev_end, _, _ in resolved_items[:idx]:
                if max(start, prev_start) < min(end, prev_end):
                    raise ValueError(f"overlapping replacements at {path}")
            if not replace_text_in_paragraph(paragraph, start, end, replacement):
                raise ValueError(f"failed to replace text at {path}")
            result.applied_count += 1

    return result


def apply_operations_to_document_xml(root: ET.Element, operations: Iterable[PatchOperation]) -> PatchResult:
    return apply_operations_to_xml_root(root, operations)


def apply_operations_to_docx_bytes(docx_bytes: bytes, operations: list[PatchOperation]) -> tuple[bytes, PatchResult]:
    if not docx_bytes:
        raise ValueError("empty docx payload")

    with zipfile.ZipFile(BytesIO(docx_bytes), "r") as zin:
        names = set(zin.namelist())
        if "word/document.xml" not in names:
            raise ValueError("word/document.xml not found")
        grouped: dict[str, list[PatchOperation]] = {}
        for op in operations:
            part_name = str(op.applied_part_name or "word/document.xml").strip().lstrip("/") or "word/document.xml"
            if not is_supported_part_name(part_name):
                raise ValueError(f"unsupported part: {part_name}")
            if part_name not in names:
                raise ValueError(f"{part_name} not found")
            grouped.setdefault(part_name, []).append(op)
        roots = {part_name: ET.fromstring(zin.read(part_name)) for part_name in grouped}

    result = PatchResult()
    patched_xml: dict[str, bytes] = {}
    for part_name, part_ops in grouped.items():
        part_result = apply_operations_to_xml_root(roots[part_name], part_ops)
        result.applied_count += part_result.applied_count
        result.skipped_count += part_result.skipped_count
        patched_xml[part_name] = ET.tostring(roots[part_name], encoding="utf-8", xml_declaration=True)

    src = BytesIO(docx_bytes)
    out = BytesIO()
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            payload = zin.read(info.filename)
            if info.filename in patched_xml:
                payload = patched_xml[info.filename]
            zout.writestr(info, payload)
    return out.getvalue(), result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Apply OOXML-path patch operations in test/validation mode. "
            "Do not use this CLI as the production audit patch entrypoint."
        )
    )
    parser.add_argument("--docx", required=True, type=Path, help="Input docx")
    parser.add_argument("--operations", required=True, type=Path, help="JSON file containing patch operations")
    parser.add_argument("--out", required=True, type=Path, help="Output patched docx")
    parser.add_argument(
        "--test-tool",
        action="store_true",
        help="Acknowledge that this CLI is for local tests/validation only.",
    )
    args = parser.parse_args()

    if not args.test_tool:
        raise SystemExit(
            "refusing to run without --test-tool. "
            + VALIDATION_ONLY_NOTICE
        )

    operations_raw = json.loads(args.operations.read_text(encoding="utf-8"))
    if not isinstance(operations_raw, list):
        raise SystemExit("operations must be a JSON array")
    patched, result = apply_operations_to_docx_bytes(args.docx.read_bytes(), parse_operations(operations_raw))
    args.out.write_bytes(patched)
    print(
        json.dumps(
            {
                "mode": "validation-only",
                "notice": VALIDATION_ONLY_NOTICE,
                "applied_count": result.applied_count,
                "skipped_count": result.skipped_count,
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
