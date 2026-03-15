#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent / "word_html_mapper.py"
SPEC = importlib.util.spec_from_file_location("word_html_mapper", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class WordHtmlMapperUnitTest(unittest.TestCase):
    def test_heading_and_paragraph_consume_distinct_paragraph_nodes(self) -> None:
        html = "<h1>标题</h1><p>正文</p>"
        nodes = [
            MODULE.OoxmlNode("p", "/w:document/w:body/p[1]", 1, "Heading1", "body/p0"),
            MODULE.OoxmlNode("p", "/w:document/w:body/p[2]", 2, None, "body/p1"),
        ]

        mapped = MODULE.annotate_html(html, nodes)

        self.assertIn('<h1 data-ooxml-id="p-1"', mapped)
        self.assertIn('<p data-ooxml-id="p-2"', mapped)
        self.assertIn('data-docx-anchor="body/p0"', mapped)
        self.assertIn('data-docx-anchor="body/p1"', mapped)
        self.assertEqual(mapped.count('data-ooxml-id="p-1"'), 1)
        self.assertEqual(mapped.count('data-ooxml-id="p-2"'), 1)

    def test_run_and_text_mapping_are_emitted_together_for_span(self) -> None:
        html = "<p><span>字</span></p>"
        nodes = [
            MODULE.OoxmlNode("p", "/w:document/w:body/p[1]", 1, None),
            MODULE.OoxmlNode("r", "/w:document/w:body/p[1]/r[1]", 1, None),
            MODULE.OoxmlNode("t", "/w:document/w:body/p[1]/r[1]/t[1]", 1, None),
        ]

        mapped = MODULE.annotate_html(html, nodes)

        self.assertIn('data-ooxml-r-id="r-1"', mapped)
        self.assertIn('data-ooxml-r-path="/w:document/w:body/p[1]/r[1]"', mapped)
        self.assertIn('data-ooxml-t-id="t-1"', mapped)
        self.assertIn('data-ooxml-t-path="/w:document/w:body/p[1]/r[1]/t[1]"', mapped)

    def test_table_mapping_preserves_document_order(self) -> None:
        html = "<table><tr><td>单元格</td></tr></table>"
        nodes = [
            MODULE.OoxmlNode("tbl", "/w:document/w:body/tbl[1]", 1, None),
            MODULE.OoxmlNode("tr", "/w:document/w:body/tbl[1]/tr[1]", 1, None),
            MODULE.OoxmlNode("tc", "/w:document/w:body/tbl[1]/tr[1]/tc[1]", 1, None),
        ]

        mapped = MODULE.annotate_html(html, nodes)

        self.assertIn('<table data-ooxml-id="tbl-1"', mapped)
        self.assertIn('<tr data-ooxml-id="tr-1"', mapped)
        self.assertIn('<td data-ooxml-id="tc-1"', mapped)


if __name__ == "__main__":
    unittest.main()
