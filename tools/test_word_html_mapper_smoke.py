#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
import subprocess
import tempfile
from pathlib import Path
import urllib.request
import uuid


def convert_via_onlyoffice(api_url: str, src_path: Path) -> str:
    boundary = f"----WordHtmlMapperSmoke{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(src_path.name)[0] or "application/octet-stream"
    file_bytes = src_path.read_bytes()
    body = []
    body.append(f"--{boundary}\r\n".encode("utf-8"))
    body.append(
        (
            f'Content-Disposition: form-data; name="file"; filename="{src_path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
    )
    body.append(file_bytes)
    body.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    data = b"".join(body)

    request = urllib.request.Request(
        api_url,
        data=data,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    html = payload.get("html") or ""
    if not html:
        raise RuntimeError(f"OnlyOffice returned empty html for {src_path}")
    return html


def assert_mapping(mapped_html: str, src_path: Path) -> None:
    required_tokens = [
        "data-ooxml-id=",
        "data-ooxml-path=",
    ]
    missing = [token for token in required_tokens if token not in mapped_html]
    if missing:
        raise AssertionError(f"{src_path.name}: missing mapping markers: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test word_html_mapper.py on real docx->html samples.")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:18083/convert/word-to-html-onlyoffice",
        help="OnlyOffice-backed convert-to-html endpoint",
    )
    parser.add_argument(
        "--source-dir",
        action="append",
        default=[],
        help="Source directory containing docx files. Can be repeated.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "smoke_output"),
        help="Directory for generated html and report",
    )
    parser.add_argument("--limit", type=int, default=3, help="Max docx files to test")
    args = parser.parse_args()

    script_path = Path(__file__).resolve().parent / "word_html_mapper.py"
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_dirs = [Path(p).resolve() for p in (args.source_dir or [
        "/Users/lizhibo/000-Projects/200-llm_projects/03-write-doc/tests/docs",
        "/Users/lizhibo/000-Projects/200-llm_projects/03-write-doc/tests/docs2",
    ])]

    samples: list[Path] = []
    for source_dir in source_dirs:
        for path in sorted(source_dir.glob("*.docx")):
            if ".anchor-" in path.name:
                continue
            samples.append(path)
    samples = samples[: args.limit]
    if not samples:
        raise SystemExit("no docx samples found")

    report_rows = []
    with tempfile.TemporaryDirectory(prefix="word-html-mapper-smoke-") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        for src_path in samples:
            html = convert_via_onlyoffice(args.api_url, src_path)
            html_path = tmp_dir / f"{src_path.stem}.html"
            mapped_path = tmp_dir / f"{src_path.stem}.mapped.html"
            html_path.write_text(html, encoding="utf-8")

            completed = subprocess.run(
                [
                    shutil.which("python3") or "/usr/bin/python3",
                    str(script_path),
                    "--docx",
                    str(src_path),
                    "--html",
                    str(html_path),
                    "--out",
                    str(mapped_path),
                ],
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"mapper failed for {src_path.name}: stdout={completed.stdout!r} stderr={completed.stderr!r}"
                )

            mapped_html = mapped_path.read_text(encoding="utf-8")
            assert_mapping(mapped_html, src_path)

            final_html_path = output_dir / f"{src_path.stem}.mapped.html"
            final_html_path.write_text(mapped_html, encoding="utf-8")

            report_rows.append(
                {
                    "source": str(src_path),
                    "mapped_html": str(final_html_path),
                    "has_block_mapping": "data-ooxml-id=" in mapped_html,
                    "has_block_path": "data-ooxml-path=" in mapped_html,
                    "has_run_mapping": "data-ooxml-r-id=" in mapped_html,
                    "has_text_mapping": "data-ooxml-t-id=" in mapped_html,
                }
            )

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
