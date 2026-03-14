# Word→HTML 元素映射（ONLYOFFICE 后处理）

这个脚本用于在 `docx -> html` 后，为 HTML 元素注入可追溯到 Word OOXML 的映射属性：

- 块级：`data-ooxml-id` / `data-ooxml-path`
- run级：`data-ooxml-r-id` / `data-ooxml-r-path`
- text级：`data-ooxml-t-id` / `data-ooxml-t-path`

## 支持映射（v2）

- `w:p` ↔ `<p>`
- `w:p`（Heading 样式）↔ `<h1..h6>`
- `w:tbl` ↔ `<table>`
- `w:tr` ↔ `<tr>`
- `w:tc` ↔ `<td>/<th>`
- `w:r` ↔ `<span>`
- `w:t` ↔ `<span>/<em>/<strong>/<a>`（best-effort）

## 用法

```bash
python3 tools/word_html_mapper.py \
  --docx ./sample.docx \
  --html ./sample.html \
  --out  ./sample.mapped.html
```

## 说明

- 这是“转换后注入映射”的改造，适合先用 ONLYOFFICE 产出 HTML，再补充可追溯信息。
- 如果你要做“字符级（run/text）映射”，可以在此基础上继续扩展到 `w:r` / `w:t`。
