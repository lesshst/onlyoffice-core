# Word→HTML 元素映射（ONLYOFFICE 后处理）

这个脚本用于在 `docx -> html` 后，为 HTML 元素注入可追溯到 Word OOXML 的映射属性：

- 块级：`data-ooxml-id` / `data-ooxml-path`
- run级：`data-ooxml-r-id` / `data-ooxml-r-path`
- text级：`data-ooxml-t-id` / `data-ooxml-t-path`

## 支持映射（v2）

- 下一个 `w:p` ↔ 下一个 `<p>/<h1..h6>`
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

## 测试

基础单测不依赖额外 Python 包：

```bash
python3 tools/test_word_html_mapper_unit.py
```

如需校验 `data-ooxml-path` 是否真的能回指到同一个 OOXML 节点，并且段落/行内文本与 HTML 一致，可执行：

```bash
python3 tools/validate_word_html_ooxml_mapping.py \
  --docx ./sample.docx \
  --html ./sample.mapped.html
```

如需在本地测试 `OOXML path -> docx patch` 这套规则，可使用
`tools/word_ooxml_patch_executor.py`。这份脚本在 `ONLYOFFICE-core` 中现在只保留
为测试/验证工具，正式业务 patch 执行链已迁移到：

- `03-write-doc/backend/app/services/word_ooxml_patch_executor.py`

因此它的 CLI 需要显式确认测试模式：

```bash
python3 tools/word_ooxml_patch_executor.py \
  --test-tool \
  --docx ./sample.docx \
  --operations ./operations.json \
  --out ./sample.patched.docx
```

如需对真实样本做 smoke test，可在已启动业务侧 `docx -> html` 接口后执行：

```bash
python3 tools/test_word_html_mapper_smoke.py --limit 3
```

当前 smoke test 也会自动执行上述验证，不再只是检查属性是否存在。

## 当前集成边界

当前建议的源码级集成边界是：

- 只对 `docx -> html` 自动执行映射补注
- 不对 `doc/wps -> html` 直接做映射

也就是说，主链路应收敛为：

- `docx -> html`
  - 由 ONLYOFFICE-core 在生成 `index.html` 后自动调用本脚本
- `doc/wps -> html`
  - 先在业务侧或外层服务中做 `doc/wps -> docx`
  - 再进入 `docx -> html`

## 自动接线时使用的配置项

如果在 `ONLYOFFICE-core` 中启用自动调用，可通过进程 `options` 控制：

- `wordHtmlMapperEnable`
  - 是否启用自动映射
  - 默认：启用
- `wordHtmlMapperScript`
  - mapper 脚本路径
- `wordHtmlMapperPython`
  - python3 解释器路径

## 设计取舍

当前自动接线版本优先保证：

- 主转换链路改动小
- 失败时不影响原始 HTML 产出
- 只在存在原始 `docx` 路径时执行

因此：

- 映射失败时，只打印错误并跳过
- 不会让 `docx -> html` 整体转换失败
