#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent / "validate_word_html_ooxml_mapping.py"
SPEC = importlib.util.spec_from_file_location("validate_word_html_ooxml_mapping", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>第一段保留不变。</w:t></w:r></w:p>
    <w:p>
      <w:r><w:t>为</w:t></w:r>
      <w:r><w:t>进一步进一步</w:t></w:r>
      <w:r><w:t>提升共享效率。</w:t></w:r>
    </w:p>
    <w:tbl>
      <w:tr>
        <w:tc>
          <w:p><w:r><w:t>单元格内容</w:t></w:r></w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
  </w:body>
</w:document>
"""


class ValidateWordHtmlOoxmlMappingUnitTest(unittest.TestCase):
    def _build_docx(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        docx_path = Path(tmp.name) / "sample.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", DOC_XML)
        return docx_path

    def test_validator_accepts_matching_block_and_inline_paths(self) -> None:
        docx_path = self._build_docx()
        html = (
            '<p id="w-e-element-audit-1" data-ooxml-path="/w:document/w:body/p[1]">第一段保留不变。</p>'
            '<p id="w-e-element-audit-2" data-ooxml-path="/w:document/w:body/p[2]">'
            '为<span data-ooxml-r-path="/w:document/w:body/p[2]/r[2]" '
            'data-ooxml-t-path="/w:document/w:body/p[2]/r[2]/t[1]">进一步进一步</span>提升共享效率。'
            '</p>'
            '<table data-ooxml-path="/w:document/w:body/tbl[3]"><tr data-ooxml-path="/w:document/w:body/tbl[3]/tr[1]">'
            '<td data-ooxml-path="/w:document/w:body/tbl[3]/tr[1]/tc[1]">单元格内容</td></tr></table>'
        )

        summary = MODULE.validate_docx_html_mapping(docx_path, html)

        self.assertEqual(summary.checked, 7)
        self.assertEqual(summary.passed, 7)
        self.assertEqual(summary.issues, [])

    def test_validator_reports_text_mismatch_for_wrong_paragraph_path(self) -> None:
        docx_path = self._build_docx()
        html = '<p id="w-e-element-audit-2" data-ooxml-path="/w:document/w:body/p[1]">为进一步进一步提升共享效率。</p>'

        summary = MODULE.validate_docx_html_mapping(docx_path, html)

        self.assertEqual(summary.checked, 1)
        self.assertEqual(len(summary.issues), 1)
        self.assertEqual(summary.issues[0].code, "text_mismatch")

    def test_validator_reports_kind_mismatch_for_wrong_cell_path(self) -> None:
        docx_path = self._build_docx()
        html = '<td id="w-e-element-audit-3" data-ooxml-path="/w:document/w:body/p[2]">单元格内容</td>'

        summary = MODULE.validate_docx_html_mapping(docx_path, html)

        self.assertEqual(summary.checked, 1)
        self.assertEqual(len(summary.issues), 1)
        self.assertEqual(summary.issues[0].code, "node_kind_mismatch")


if __name__ == "__main__":
    unittest.main()
