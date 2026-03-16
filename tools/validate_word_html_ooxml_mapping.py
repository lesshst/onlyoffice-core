#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}

_BLOCK_TAG_KIND = {
    "p": "p",
    "h1": "p",
    "h2": "p",
    "h3": "p",
    "h4": "p",
    "h5": "p",
    "h6": "p",
    "li": "p",
    "table": "tbl",
    "tr": "tr",
    "td": "tc",
    "th": "tc",
}


def _load_patch_executor_module():
    script_path = Path(__file__).resolve().parent / "word_ooxml_patch_executor.py"
    spec = importlib.util.spec_from_file_location("word_ooxml_patch_executor", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load OOXML validation helper module: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


_PATCH_EXECUTOR = _load_patch_executor_module()
paragraph_text_for_matching = _PATCH_EXECUTOR.paragraph_text_for_matching
resolve_ooxml_path = _PATCH_EXECUTOR.resolve_ooxml_path


@dataclass
class HtmlMappingTarget:
    tag: str
    element_id: str | None
    attr_name: str
    path: str
    text: str


@dataclass
class ValidationIssue:
    code: str
    tag: str
    attr_name: str
    path: str
    element_id: str | None = None
    expected_kind: str | None = None
    actual_kind: str | None = None
    html_text: str | None = None
    ooxml_text: str | None = None


@dataclass
class ValidationSummary:
    checked: int
    passed: int
    issues: list[ValidationIssue]


def _normalize_text(text: str) -> str:
    raw = str(text or "").replace("\u00a0", " ")
    return " ".join(raw.split())


def _local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1]


def _extract_document_root(docx_path: Path) -> ET.Element:
    with zipfile.ZipFile(docx_path, "r") as zf:
        data = zf.read("word/document.xml")
    return ET.fromstring(data)


def _run_text(run: ET.Element) -> str:
    parts: list[str] = []
    for child in list(run):
        local = _local_name(child.tag)
        if local == "t":
            parts.append(child.text or "")
        elif local in {"tab", "cr", "br"}:
            parts.append(" ")
    return "".join(parts)


def _node_text_for_validation(node: ET.Element) -> str:
    kind = _local_name(node.tag)
    if kind == "p":
        return paragraph_text_for_matching(node)[0]
    if kind == "r":
        return _run_text(node)
    if kind == "t":
        return node.text or ""
    if kind == "tc":
        return "".join(node.findall(".//w:t", NS)[idx].text or "" for idx in range(len(node.findall(".//w:t", NS))))
    return ""


class _MappedHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[tuple[str, dict | None]] = []
        self.targets: list[HtmlMappingTarget] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        mapping_attrs = [
            ("data-ooxml-path", attr_map.get("data-ooxml-path")),
            ("data-ooxml-r-path", attr_map.get("data-ooxml-r-path")),
            ("data-ooxml-t-path", attr_map.get("data-ooxml-t-path")),
        ]
        frames: list[dict] = []
        for attr_name, value in mapping_attrs:
            if not value:
                continue
            frame = {
                "tag": tag.lower(),
                "element_id": attr_map.get("id") or None,
                "attr_name": attr_name,
                "path": value,
                "text_parts": [],
            }
            self.targets.append(frame)  # placeholder; replaced on endtag
            frames.append(frame)
        self._stack.append((tag.lower(), frames[0] if len(frames) == 1 else {"frames": frames} if frames else None))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if not data:
            return
        for _tag, frame in self._stack:
            if not frame:
                continue
            if "frames" in frame:
                for item in frame["frames"]:
                    item["text_parts"].append(data)
            else:
                frame["text_parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._stack:
            return
        open_tag, frame = self._stack.pop()
        if open_tag != tag.lower() or not frame:
            return

        frames = frame["frames"] if "frames" in frame else [frame]
        for item in frames:
            self.targets[self.targets.index(item)] = HtmlMappingTarget(
                tag=item["tag"],
                element_id=item["element_id"],
                attr_name=item["attr_name"],
                path=item["path"],
                text="".join(item["text_parts"]),
            )


def _parse_mapped_html(html: str) -> list[HtmlMappingTarget]:
    parser = _MappedHtmlParser()
    parser.feed(html or "")
    parser.close()
    return [item for item in parser.targets if isinstance(item, HtmlMappingTarget)]


def validate_docx_html_mapping(docx_path: Path, html: str) -> ValidationSummary:
    root = _extract_document_root(docx_path)
    targets = _parse_mapped_html(html)
    issues: list[ValidationIssue] = []
    passed = 0

    for target in targets:
        node = resolve_ooxml_path(root, target.path)
        expected_kind = None
        if target.attr_name == "data-ooxml-path":
            expected_kind = _BLOCK_TAG_KIND.get(target.tag)
        elif target.attr_name == "data-ooxml-r-path":
            expected_kind = "r"
        elif target.attr_name == "data-ooxml-t-path":
            expected_kind = "t"

        if node is None:
            issues.append(
                ValidationIssue(
                    code="path_not_found",
                    tag=target.tag,
                    attr_name=target.attr_name,
                    path=target.path,
                    element_id=target.element_id,
                    expected_kind=expected_kind,
                )
            )
            continue

        actual_kind = _local_name(node.tag)
        if expected_kind and actual_kind != expected_kind:
            issues.append(
                ValidationIssue(
                    code="node_kind_mismatch",
                    tag=target.tag,
                    attr_name=target.attr_name,
                    path=target.path,
                    element_id=target.element_id,
                    expected_kind=expected_kind,
                    actual_kind=actual_kind,
                )
            )
            continue

        should_compare_text = (
            (target.attr_name == "data-ooxml-path" and expected_kind == "p")
            or target.attr_name in {"data-ooxml-r-path", "data-ooxml-t-path"}
        )
        if should_compare_text:
            html_text = _normalize_text(target.text)
            ooxml_text = _normalize_text(_node_text_for_validation(node))
            if html_text and ooxml_text and html_text != ooxml_text:
                issues.append(
                    ValidationIssue(
                        code="text_mismatch",
                        tag=target.tag,
                        attr_name=target.attr_name,
                        path=target.path,
                        element_id=target.element_id,
                        expected_kind=expected_kind,
                        actual_kind=actual_kind,
                        html_text=html_text,
                        ooxml_text=ooxml_text,
                    )
                )
                continue

        passed += 1

    return ValidationSummary(checked=len(targets), passed=passed, issues=issues)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate HTML OOXML mapping against source docx")
    parser.add_argument("--docx", required=True, type=Path, help="Source docx")
    parser.add_argument("--html", required=True, type=Path, help="Mapped html file")
    parser.add_argument("--report", type=Path, help="Optional json report path")
    args = parser.parse_args()

    html = args.html.read_text(encoding="utf-8")
    summary = validate_docx_html_mapping(args.docx, html)
    payload = {
        "checked": summary.checked,
        "passed": summary.passed,
        "issue_count": len(summary.issues),
        "issues": [asdict(issue) for issue in summary.issues],
    }
    if args.report:
        args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if not summary.issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
