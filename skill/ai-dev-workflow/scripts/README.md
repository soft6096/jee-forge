# ai-dev-workflow/scripts —— 纯标准库工具脚本

## export_html.py —— 中间产物 md → 带左侧导航 HTML 导出器

把「给人读 / 存档」的中间产物导出成自包含单文件 HTML（内嵌 CSS + 左侧标题锚点导航 + 打印友好）。
**md 永远是真源**：脚本只读 md、只写 `.html`，绝不改动任何 md；也不让 AI 回读 html 代替 md。
配套命令：`/export-html`（见 `../commands/export-html.md`）。

- **依赖**：Python 3.8+，仅标准库，**无外部依赖**（不用 pandoc）。
- **≈0 token**：模型只跑一条命令，不在上下文里生成/搬运 html。

### 用法

```bash
# 只校验能否解析（不写文件）
python3 export_html.py <a.md> <b.md> --check

# 导出指定 md（同目录生成同名 .html）
python3 export_html.py docs/订单V1-20261018110000/3.1-*.md

# 导出整个模块目录里的阅读型产物 + 生成 index.html 导航（推荐）
python3 export_html.py docs/订单V1-20261018110000/ --products --index

# 输出到指定目录
python3 export_html.py <输入>... -o docs/订单V1-.../html/ --index
```

### 导出范围（`--products`）

只导阅读/存档型产物：`0.5-*存量*扫描*`、`0.9-*需求*`、`1.1-*功能清单*`、`3.*.1-*`、`5.2.*-*`、`5.3.*-*`。
**排除** `3.*.2-*`（接口清单：保持 md，供前端/测试与 AI 直接读取）；机器读写型产物（约束 / 编码指令 / 任务拆解 / 通用-*）默认不在导出集内。

### 已知限制

- 复选框 `- [ ]`/`- [x]` 静态渲染为 ☐/☑，**点了不保存**（要勾请改 md）。
- mermaid 代码块渲染为纯文本代码块（不联网执行 mermaid.js，保证离线/存档）。
- 支持：ATX 标题（≤3 级进导航）、GFM 表格、围栏代码块、有序/无序/任务列表（含嵌套）、引用块与 `> [!NOTE]/WARNING/…` 提示框、行内 code / 加粗 / 斜体 / 删除线 / 链接 / 图片 / 自动链接。
