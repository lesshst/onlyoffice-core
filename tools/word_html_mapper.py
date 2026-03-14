#!/usr/bin/env python3
"""
Map OOXML (docx) elements to generated HTML elements.

Goal:
- assign stable ids to WordprocessingML nodes in /word/document.xml
- annotate HTML nodes with data-ooxml-id / data-ooxml-path

Current mapping strategy (v2):
- paragraph-level: w:p  <-> <p>
- heading-level:   w:p(style Heading*) <-> <h1..h6>
- table-level:     w:tbl <-> <table>
- row-level:       w:tr  <-> <tr>
- cell-level:      w:tc  <-> <td>/<th>
- run-level:       w:r   <-> <span>
- text-level:      w:t   <-> <span>/<em>/<strong>/<a> (best-effort inline carrier)

This does NOT depend on ONLYOFFICE internals and can be used as a post-step
after any docx->html converter (including ONLYOFFICE conversion output).
"""

from __future__ import annotations

import argparse
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


@dataclass
class OoxmlNode:
    kind: str
    path: str
    idx: int
    style: Optional[str] = None

    @property
    def oid(self) -> str:
        return f"{self.kind}-{self.idx}"


class TinyHtmlNode:
    def __init__(self, tag: str, raw_open: str):
        self.tag = tag
        self.raw_open = raw_open
        self.attrs = {}


def _extract_doc_xml(docx_path: Path) -> ET.Element:
    with zipfile.ZipFile(docx_path, "r") as zf:
        data = zf.read("word/document.xml")
    return ET.fromstring(data)


def _style_of_p(p: ET.Element) -> Optional[str]:
    p_style = p.find("./w:pPr/w:pStyle", NS)
    if p_style is not None:
        return p_style.attrib.get(f"{{{W_NS}}}val")
    return None


def build_ooxml_nodes(docx_path: Path) -> List[OoxmlNode]:
    root = _extract_doc_xml(docx_path)
    body = root.find("./w:body", NS)
    if body is None:
        return []

    nodes: List[OoxmlNode] = []
    p_i = tbl_i = tr_i = tc_i = r_i = t_i = 0

    def walk(elem: ET.Element, xpath: str) -> None:
        nonlocal p_i, tbl_i, tr_i, tc_i, r_i, t_i
        local = elem.tag.rsplit("}", 1)[-1]

        if local == "p":
            style = _style_of_p(elem)
            p_i += 1
            nodes.append(OoxmlNode("p", xpath, p_i, style))
        elif local == "tbl":
            tbl_i += 1
            nodes.append(OoxmlNode("tbl", xpath, tbl_i))
        elif local == "tr":
            tr_i += 1
            nodes.append(OoxmlNode("tr", xpath, tr_i))
        elif local == "tc":
            tc_i += 1
            nodes.append(OoxmlNode("tc", xpath, tc_i))
        elif local == "r":
            r_i += 1
            nodes.append(OoxmlNode("r", xpath, r_i))
        elif local == "t":
            t_i += 1
            nodes.append(OoxmlNode("t", xpath, t_i))

        for idx, child in enumerate(list(elem), start=1):
            c_local = child.tag.rsplit("}", 1)[-1]
            walk(child, f"{xpath}/{c_local}[{idx}]")

    walk(body, "/w:document/w:body")
    return nodes


def _inject_attr(open_tag: str, key: str, value: str) -> str:
    if open_tag.endswith("/>"):
        return open_tag[:-2] + f' {key}="{value}"/>'
    return open_tag[:-1] + f' {key}="{value}">'


def annotate_html(html: str, nodes: List[OoxmlNode]) -> str:
    # lightweight open-tag matcher, avoids external parser dependency
    tag_re = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>", re.M)

    p_nodes = [n for n in nodes if n.kind == "p"]
    h_nodes = [n for n in nodes if n.kind == "p" and (n.style or "").startswith("Heading")]
    tbl_nodes = [n for n in nodes if n.kind == "tbl"]
    tr_nodes = [n for n in nodes if n.kind == "tr"]
    tc_nodes = [n for n in nodes if n.kind == "tc"]
    r_nodes = [n for n in nodes if n.kind == "r"]
    t_nodes = [n for n in nodes if n.kind == "t"]

    p_i = h_i = tbl_i = tr_i = tc_i = r_i = t_i = 0

    out = []
    last = 0
    for m in tag_re.finditer(html):
        out.append(html[last:m.start()])
        open_tag = m.group(0)
        tag = m.group(1).lower()

        chosen: Optional[OoxmlNode] = None
        if tag == "p" and p_i < len(p_nodes):
            chosen = p_nodes[p_i]
            p_i += 1
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and h_i < len(h_nodes):
            chosen = h_nodes[h_i]
            h_i += 1
        elif tag == "table" and tbl_i < len(tbl_nodes):
            chosen = tbl_nodes[tbl_i]
            tbl_i += 1
        elif tag == "tr" and tr_i < len(tr_nodes):
            chosen = tr_nodes[tr_i]
            tr_i += 1
        elif tag in {"td", "th"} and tc_i < len(tc_nodes):
            chosen = tc_nodes[tc_i]
            tc_i += 1
        elif tag == "span" and r_i < len(r_nodes):
            chosen = r_nodes[r_i]
            r_i += 1
        elif tag in {"span", "em", "strong", "a"} and t_i < len(t_nodes):
            # best-effort carrier for text runs
            chosen = t_nodes[t_i]
            t_i += 1

        if chosen:
            key_prefix = "data-ooxml"
            if chosen.kind in {"r", "t"}:
                key_prefix = f"data-ooxml-{chosen.kind}"

            open_tag = _inject_attr(open_tag, f"{key_prefix}-id", chosen.oid)
            open_tag = _inject_attr(open_tag, f"{key_prefix}-path", chosen.path)

        out.append(open_tag)
        last = m.end()

    out.append(html[last:])
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Annotate HTML with docx OOXML mapping")
    ap.add_argument("--docx", required=True, type=Path, help="Input .docx")
    ap.add_argument("--html", required=True, type=Path, help="Input html generated from docx")
    ap.add_argument("--out", required=True, type=Path, help="Output annotated html")
    args = ap.parse_args()

    nodes = build_ooxml_nodes(args.docx)
    html = args.html.read_text(encoding="utf-8")
    annotated = annotate_html(html, nodes)
    args.out.write_text(annotated, encoding="utf-8")

    print(f"mapped_nodes={len(nodes)} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
