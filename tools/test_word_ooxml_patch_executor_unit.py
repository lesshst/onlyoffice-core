#!/usr/bin/env python3

from __future__ import annotations

import unittest
from xml.etree import ElementTree as ET

from word_ooxml_patch_executor import (
    PatchIssue,
    PatchOperation,
    apply_operations_to_document_xml,
    paragraph_text_for_matching,
    resolve_ooxml_path,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _doc_xml() -> ET.Element:
    xml = f"""
    <w:document xmlns:w="{W_NS}">
      <w:body>
        <w:p>
          <w:r><w:t>第一段保留不变。</w:t></w:r>
        </w:p>
        <w:p>
          <w:r><w:t>为</w:t></w:r>
          <w:r><w:t>进一步进一步</w:t></w:r>
          <w:r><w:t>提升共享效率。</w:t></w:r>
        </w:p>
        <w:tbl>
          <w:tblPr/>
          <w:tblGrid/>
          <w:tr>
            <w:tc>
              <w:p>
                <w:r><w:t>责任部门：待补录待补录，请立即修正。</w:t></w:r>
              </w:p>
            </w:tc>
          </w:tr>
        </w:tbl>
      </w:body>
    </w:document>
    """
    return ET.fromstring(xml)


class PatchExecutorTests(unittest.TestCase):
    def test_resolve_ooxml_path_matches_mapper_style_indexes(self):
        root = _doc_xml()

        body_paragraph = resolve_ooxml_path(root, "/w:document/w:body/p[2]")
        self.assertIsNotNone(body_paragraph)
        self.assertEqual(paragraph_text_for_matching(body_paragraph)[0], "为进一步进一步提升共享效率。")

        table_paragraph = resolve_ooxml_path(root, "/w:document/w:body/tbl[3]/tr[3]/tc[1]/p[1]")
        self.assertIsNotNone(table_paragraph)
        self.assertEqual(paragraph_text_for_matching(table_paragraph)[0], "责任部门：待补录待补录，请立即修正。")

    def test_apply_operations_to_document_xml_replaces_body_paragraph_text(self):
        root = _doc_xml()
        operations = [
            PatchOperation(
                issue=PatchIssue(
                    matched_text="进一步进一步",
                    suggested_text="进一步",
                    start=1,
                    end=7,
                ),
                applied_ooxml_path="/w:document/w:body/p[2]",
                applied_preferred_start=1,
            )
        ]

        result = apply_operations_to_document_xml(root, operations)
        paragraph = resolve_ooxml_path(root, "/w:document/w:body/p[2]")
        self.assertEqual(result.applied_count, 1)
        self.assertEqual(paragraph_text_for_matching(paragraph)[0], "为进一步提升共享效率。")

    def test_apply_operations_to_document_xml_replaces_table_cell_paragraph_text(self):
        root = _doc_xml()
        operations = [
            PatchOperation(
                issue=PatchIssue(
                    matched_text="待补录待补录",
                    suggested_text="待补录",
                    start=5,
                    end=11,
                ),
                applied_ooxml_path="/w:document/w:body/tbl[3]/tr[3]/tc[1]/p[1]",
                applied_preferred_start=5,
            )
        ]

        result = apply_operations_to_document_xml(root, operations)
        paragraph = resolve_ooxml_path(root, "/w:document/w:body/tbl[3]/tr[3]/tc[1]/p[1]")
        self.assertEqual(result.applied_count, 1)
        self.assertEqual(paragraph_text_for_matching(paragraph)[0], "责任部门：待补录，请立即修正。")


if __name__ == "__main__":
    unittest.main()
