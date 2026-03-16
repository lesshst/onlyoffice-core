#!/usr/bin/env python3

from __future__ import annotations

from io import BytesIO
import unittest
import zipfile
from xml.etree import ElementTree as ET

from word_ooxml_patch_executor import (
    PatchIssue,
    PatchOperation,
    apply_operations_to_docx_bytes,
    apply_operations_to_document_xml,
    is_supported_part_name,
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


def _minimal_docx_bytes() -> bytes:
    parts = {
        "[Content_Types].xml": b"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
</Types>
""",
        "_rels/.rels": b"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
""",
        "word/document.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{W_NS}" xmlns:v="urn:schemas-microsoft-com:vml">
  <w:body>
    <w:p>
      <w:r><w:t>正文：进一步进一步推进。</w:t></w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:pict>
          <v:shape>
            <v:textbox>
              <w:txbxContent>
                <w:p>
                  <w:r><w:t>文本框：规范规范执行。</w:t></w:r>
                </w:p>
              </w:txbxContent>
            </v:textbox>
          </v:shape>
        </w:pict>
      </w:r>
    </w:p>
  </w:body>
</w:document>
""".encode("utf-8"),
        "word/header1.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<w:hdr xmlns:w="{W_NS}">
  <w:p>
    <w:r><w:t>页眉：逐项逐项推进。</w:t></w:r>
  </w:p>
</w:hdr>
""".encode("utf-8"),
        "word/footer1.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<w:ftr xmlns:w="{W_NS}">
  <w:p>
    <w:r><w:t>页脚：内部内部参考。</w:t></w:r>
  </w:p>
</w:ftr>
""".encode("utf-8"),
        "word/footnotes.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<w:footnotes xmlns:w="{W_NS}">
  <w:footnote w:id="-1" w:type="separator"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>
  <w:footnote w:id="0" w:type="continuationSeparator"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
  <w:footnote w:id="2">
    <w:p><w:r><w:t>脚注：关于关于事项。</w:t></w:r></w:p>
  </w:footnote>
</w:footnotes>
""".encode("utf-8"),
        "word/endnotes.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<w:endnotes xmlns:w="{W_NS}">
  <w:endnote w:id="-1" w:type="separator"><w:p><w:r><w:separator/></w:r></w:p></w:endnote>
  <w:endnote w:id="0" w:type="continuationSeparator"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:endnote>
  <w:endnote w:id="2">
    <w:p><w:r><w:t>尾注：说明说明事项。</w:t></w:r></w:p>
  </w:endnote>
</w:endnotes>
""".encode("utf-8"),
    }
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        for name, payload in parts.items():
            zf.writestr(name, payload)
    return out.getvalue()


class PatchExecutorTests(unittest.TestCase):
    def test_supported_part_names_cover_story_parts(self):
        self.assertTrue(is_supported_part_name("word/document.xml"))
        self.assertTrue(is_supported_part_name("word/header12.xml"))
        self.assertTrue(is_supported_part_name("word/footer3.xml"))
        self.assertTrue(is_supported_part_name("word/footnotes.xml"))
        self.assertTrue(is_supported_part_name("word/endnotes.xml"))
        self.assertFalse(is_supported_part_name("word/comments.xml"))

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

    def test_apply_operations_to_docx_bytes_updates_multiple_story_parts(self):
        docx_bytes = _minimal_docx_bytes()
        operations = [
            PatchOperation(
                issue=PatchIssue(
                    matched_text="逐项逐项",
                    suggested_text="逐项",
                    start=3,
                    end=7,
                ),
                applied_part_name="word/header1.xml",
                applied_ooxml_path="/w:hdr/p[1]",
                applied_preferred_start=3,
            ),
            PatchOperation(
                issue=PatchIssue(
                    matched_text="内部内部",
                    suggested_text="内部",
                    start=3,
                    end=7,
                ),
                applied_part_name="word/footer1.xml",
                applied_ooxml_path="/w:ftr/p[1]",
                applied_preferred_start=3,
            ),
            PatchOperation(
                issue=PatchIssue(
                    matched_text="关于关于",
                    suggested_text="关于",
                    start=3,
                    end=7,
                ),
                applied_part_name="word/footnotes.xml",
                applied_ooxml_path="/w:footnotes/w:footnote[3]/w:p[1]",
                applied_preferred_start=3,
            ),
            PatchOperation(
                issue=PatchIssue(
                    matched_text="说明说明",
                    suggested_text="说明",
                    start=3,
                    end=7,
                ),
                applied_part_name="word/endnotes.xml",
                applied_ooxml_path="/w:endnotes/w:endnote[3]/w:p[1]",
                applied_preferred_start=3,
            ),
        ]

        patched, result = apply_operations_to_docx_bytes(docx_bytes, operations)
        self.assertEqual(result.applied_count, 4)
        with zipfile.ZipFile(BytesIO(patched), "r") as zf:
            self.assertIn("页眉：逐项推进。", zf.read("word/header1.xml").decode("utf-8"))
            self.assertIn("页脚：内部参考。", zf.read("word/footer1.xml").decode("utf-8"))
            self.assertIn("脚注：关于事项。", zf.read("word/footnotes.xml").decode("utf-8"))
            self.assertIn("尾注：说明事项。", zf.read("word/endnotes.xml").decode("utf-8"))

    def test_apply_operations_to_docx_bytes_updates_textbox_paragraph(self):
        docx_bytes = _minimal_docx_bytes()
        operations = [
            PatchOperation(
                issue=PatchIssue(
                    matched_text="规范规范",
                    suggested_text="规范",
                    start=4,
                    end=8,
                ),
                applied_part_name="word/document.xml",
                applied_ooxml_path="/w:document/w:body/p[2]/r[1]/pict[1]/shape[1]/textbox[1]/txbxContent[1]/p[1]",
                applied_preferred_start=4,
            )
        ]

        patched, result = apply_operations_to_docx_bytes(docx_bytes, operations)
        self.assertEqual(result.applied_count, 1)
        with zipfile.ZipFile(BytesIO(patched), "r") as zf:
            self.assertIn("文本框：规范执行。", zf.read("word/document.xml").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
