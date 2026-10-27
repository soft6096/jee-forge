#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_html.py —— jee-forge 中间产物 md → 带左侧导航 HTML 导出器（纯标准库，零外部依赖）

定位：md 永远是**真源**（AI 读写只认 md），本脚本只把「给人读 / 存档」的产物导出成
      自包含的单文件 HTML（内嵌 CSS、左侧标题导航、锚点跳转、打印友好），≈0 token。
      不改动任何 md；产物增删一律回到 md。

用法：
  python3 export_html.py <输入.md>...                    # 每个 md 旁生成同名 .html
  python3 export_html.py <目录>                           # 导出目录下 *.md，并生成 index.html
  python3 export_html.py <目录> --products                # 只导出约定的阅读型产物（见 PRODUCT_GLOBS）
  python3 export_html.py a.md b.md -o out/ --index        # 输出到 out/，并生成 out/index.html 导航
  python3 export_html.py <目录> --check                   # 只校验能否解析，不写文件

约定产物（阅读/存档型）：0.5 存量扫描 / 0.9 需求构成 / 1.1 功能清单 / 3.x.1 技术方案 /
  5.2 规范核对报告 / 5.3 需求覆盖报告。**3.x.2 接口清单不导出（保持 md，给前端/测试直接看）**。

限制（如实告知，够用即可）：
  - mermaid 代码块渲染为纯文本代码块（不联网执行 mermaid.js，保证离线/存档）。
  - 复选框 `- [ ]` / `- [x]` 静态渲染为 ☐ / ☑（HTML 不能回填勾选；要勾请改 md）。
"""
import sys
import os
import re
import html
import fnmatch
import glob as _glob
import argparse

# 阅读型产物匹配（--products 时用）；接口清单 3.x.2 故意排除
PRODUCT_GLOBS = [
    "0.5-*存量*扫描*.md", "0.9-*需求*.md", "1.1-*功能清单*.md",
    "3.*.1-*.md", "5.2.*-*.md", "5.3.*-*.md",
]
EXCLUDE_GLOBS = ["3.*.2-*.md"]  # 接口清单：保持 md

# ------------------------------------------------------------------ 行内解析
def _inline(text):
    """把一段（已确保不在代码块内的）文本渲染为内联 HTML；先转义再按标记替换。"""
    # 1) 先把行内代码 `code` 抠出来占位，避免其中的 * _ [ ] 被误当标记
    code_store = []

    def _stash_code(m):
        code_store.append(m.group(1))
        return "\x00%d\x00" % (len(code_store) - 1)

    text = re.sub(r"`([^`]+)`", _stash_code, text)
    # 2) 转义 HTML
    text = html.escape(text, quote=False)
    # 3) 链接 [text](url) 与图片 ![alt](url)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)",
                  lambda m: '<img alt="%s" src="%s">' % (m.group(1), _esc_attr(m.group(2))), text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)[^)]*\)",
                  lambda m: '<a href="%s">%s</a>' % (_esc_attr(m.group(2)), m.group(1)), text)
    # 4) 自动链接 <http://...>
    text = re.sub(r"&lt;(https?://[^&\s]+)&gt;",
                  lambda m: '<a href="%s">%s</a>' % (_esc_attr(m.group(1)), m.group(1)), text)
    # 5) 加粗 / 斜体 / 删除线
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    # 6) 复选框（列表项前缀已处理，这里兜底行内）
    text = text.replace("[ ]", "☐").replace("[x]", "☑").replace("[X]", "☑")
    # 7) 还原行内代码
    def _restore(m):
        return "<code>%s</code>" % html.escape(code_store[int(m.group(1))])
    text = re.sub(r"\x00(\d+)\x00", _restore, text)
    return text


def _esc_attr(u):
    return html.escape(u, quote=True)


# ------------------------------------------------------------------ 块级解析
class Renderer:
    def __init__(self):
        self.toc = []          # (level, text, anchor)
        self._seq = 0

    def _anchor(self, text):
        self._seq += 1
        return "sec-%d" % self._seq

    def render(self, md_text):
        lines = md_text.replace("\r\n", "\n").split("\n")
        out = []
        i, n = 0, len(lines)
        while i < n:
            line = lines[i]
            stripped = line.strip()
            # 围栏代码块 ```
            m = re.match(r"^```(.*)$", line)
            if m:
                lang = m.group(1).strip()
                buf = []
                i += 1
                while i < n and not re.match(r"^```\s*$", lines[i]):
                    buf.append(lines[i])
                    i += 1
                i += 1  # 跳过收尾 ```
                cls = ' class="language-%s"' % html.escape(lang) if lang else ""
                out.append("<pre><code%s>%s</code></pre>" % (cls, html.escape("\n".join(buf))))
                continue
            # ATX 标题
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                level = len(m.group(1))
                text = m.group(2).strip().rstrip("#").strip()
                anchor = self._anchor(text)
                if level <= 3:
                    self.toc.append((level, text, anchor))
                out.append('<h%d id="%s">%s</h%d>' % (level, anchor, _inline(text), level))
                i += 1
                continue
            # 水平线
            if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", stripped) and stripped:
                out.append("<hr>")
                i += 1
                continue
            # 引用块（含 > [!TYPE] 提示框）
            if stripped.startswith(">"):
                buf = []
                while i < n and lines[i].strip().startswith(">"):
                    buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                    i += 1
                out.append(self._blockquote(buf))
                continue
            # 表格（GFM：当前行有 |，下一行是分隔线）
            if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1]):
                tbl, i = self._table(lines, i)
                out.append(tbl)
                continue
            # 列表（ul/ol，含任务列表，按缩进嵌套）
            if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
                block, i = self._list(lines, i)
                out.append(block)
                continue
            # 空行
            if stripped == "":
                i += 1
                continue
            # 段落（聚合连续非空、非块级起始行）
            para = [line]
            i += 1
            while i < n and lines[i].strip() != "" and not self._is_block_start(lines[i]):
                para.append(lines[i])
                i += 1
            out.append("<p>%s</p>" % "<br>".join(_inline(p) for p in para))
        return "\n".join(out)

    def _is_block_start(self, line):
        s = line.strip()
        return (s.startswith("#") or s.startswith(">") or s.startswith("```")
                or re.match(r"^\s*([-*+]|\d+\.)\s+", line) is not None
                or re.match(r"^(-{3,}|\*{3,})\s*$", s))

    def _blockquote(self, buf):
        joined = "\n".join(buf)
        m = re.match(r"^\s*\[!(\w+)\]\s*(.*)", joined, flags=re.S)
        if m:
            typ = m.group(1).upper()
            body = self.render(m.group(2))
            cls = {"NOTE": "callout note", "TIP": "callout tip", "IMPORTANT": "callout important",
                   "WARNING": "callout warning", "CAUTION": "callout caution"}.get(typ, "callout note")
            label = {"NOTE": "说明", "TIP": "提示", "IMPORTANT": "重要",
                     "WARNING": "警告", "CAUTION": "注意"}.get(typ, typ)
            return '<div class="%s"><div class="callout-title">%s</div>%s</div>' % (cls, label, body)
        return "<blockquote>%s</blockquote>" % self.render(joined)

    def _table(self, lines, i):
        header = self._split_row(lines[i])
        aligns = [c.strip() for c in self._split_row(lines[i + 1])]
        i += 2
        rows = []
        while i < len(lines) and "|" in lines[i] and lines[i].strip() != "":
            rows.append(self._split_row(lines[i]))
            i += 1
        def align(j):
            a = aligns[j] if j < len(aligns) else ""
            if a.startswith(":") and a.endswith(":"):
                return ' style="text-align:center"'
            if a.endswith(":"):
                return ' style="text-align:right"'
            return ""
        head = "".join("<th%s>%s</th>" % (align(j), _inline(c)) for j, c in enumerate(header))
        body = []
        for r in rows:
            tds = "".join("<td%s>%s</td>" % (align(j), _inline(c)) for j, c in enumerate(r))
            body.append("<tr>%s</tr>" % tds)
        tbl = "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (head, "".join(body))
        return tbl, i

    @staticmethod
    def _split_row(line):
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [c.strip() for c in line.split("|")]

    def _list(self, lines, i):
        # 收集同级及更深条目，返回一段嵌套 HTML
        items, i, ordered = self._collect_list(lines, i, 0)
        tag = "ol" if ordered else "ul"
        return "<%s>%s</%s>" % (tag, "".join(items), tag), i

    def _collect_list(self, lines, i, base_indent):
        items = []
        ordered = False
        n = len(lines)
        while i < n:
            m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", lines[i])
            if not m:
                break
            indent = len(m.group(1))
            if indent < base_indent:
                break
            if indent > base_indent:
                # 更深一级：递归生成子列表挂到上一项
                sub, i, sub_ord = self._collect_list(lines, i, indent)
                if items:
                    items[-1] = items[-1][: -len("</li>")] + "<%s>%s</%s></li>" % (
                        "ol" if sub_ord else "ul", "".join(sub), "ol" if sub_ord else "ul")
                continue
            marker = m.group(2)
            ordered = ordered or bool(re.match(r"\d+\.", marker))
            content = m.group(3)
            task = re.match(r"^\[( |x|X)\]\s+(.*)$", content)
            if task:
                box = "☑" if task.group(1) in ("x", "X") else "☐"
                content = '<span class="task">%s</span> %s' % (box, task.group(2))
            items.append("<li>%s</li>" % _inline(content))
            i += 1
        return items, i, ordered


# ------------------------------------------------------------------ 页面模板
CSS = """
:root{--bg:#fff;--fg:#1f2328;--muted:#57606a;--border:#d0d7de;--accent:#0969da;--code:#f6f8fa;--nav-w:300px}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
color:var(--fg);background:var(--bg);line-height:1.65;font-size:15px}
.layout{display:flex;min-height:100vh}
nav.toc{width:var(--nav-w);flex:0 0 var(--nav-w);position:sticky;top:0;height:100vh;overflow:auto;
border-right:1px solid var(--border);background:var(--code);padding:16px 14px}
nav.toc h2{font-size:13px;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
nav.toc a{display:block;color:var(--fg);text-decoration:none;padding:3px 8px;border-radius:6px;font-size:13px}
nav.toc a:hover{background:#eaeef2}
nav.toc a.lv2{padding-left:20px}nav.toc a.lv3{padding-left:36px;color:var(--muted)}
main{flex:1;min-width:0;padding:32px 40px;max-width:1000px}
h1{border-bottom:2px solid var(--border);padding-bottom:.3em}
h2{border-bottom:1px solid var(--border);padding-bottom:.3em;margin-top:2em}
h1,h2,h3{line-height:1.3}
code{background:var(--code);padding:.15em .4em;border-radius:5px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:85%}
pre{background:var(--code);padding:14px 16px;border-radius:8px;overflow:auto;border:1px solid var(--border)}
pre code{background:none;padding:0;font-size:90%}
table{border-collapse:collapse;width:100%;margin:1em 0;display:block;overflow:auto}
th,td{border:1px solid var(--border);padding:7px 12px;text-align:left}
th{background:var(--code);font-weight:600}
tr:nth-child(even) td{background:#fbfcfd}
blockquote{margin:1em 0;padding:.4em 1em;border-left:4px solid var(--border);color:var(--muted);background:var(--code)}
.callout{margin:1em 0;padding:12px 16px;border-left:4px solid var(--accent);border-radius:0 8px 8px 0;background:#f0f6ff}
.callout .callout-title{font-weight:700;margin-bottom:6px}
.callout.warning,.callout.caution{border-left-color:#bf8700;background:#fff8e5}
.callout.important{border-left-color:#8250df;background:#fbefff}
.callout.note{border-color:var(--accent)}
.task{font-family:monospace;color:var(--accent)}
hr{border:none;border-top:1px solid var(--border);margin:2em 0}
a{color:var(--accent)}
.toplink{margin-top:3em;padding-top:1em;border-top:1px dashed var(--border);font-size:13px}
.src{color:var(--muted);font-size:12px;margin:0 0 18px}
@media print{nav.toc{display:none}main{padding:0}}
@media (max-width:820px){.layout{flex-direction:column}nav.toc{position:static;width:auto;height:auto;flex:none;border-right:none;border-bottom:1px solid var(--border)}}
"""

def render_page(title, body_html, toc, src_rel=None):
    nav = ['<h2>导航</h2>']
    for level, text, anchor in toc:
        nav.append('<a class="lv%d" href="#%s">%s</a>' % (level, anchor, html.escape(text)))
    src = '<p class="src">源文件（真源）：%s · 本页为导出视图，请勿手改</p>' % html.escape(src_rel) if src_rel else ""
    return ("""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title><style>%s</style></head>
<body><div class="layout">
<nav class="toc">%s</nav>
<main>%s%s
<p class="toplink"><a href="#top">↑ 回到顶部</a></p></main>
</div></body></html>""" % (html.escape(title), CSS, "\n".join(nav), src, body_html)).replace("<main>", '<main id="top">', 1)


def convert_file(md_path):
    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    r = Renderer()
    body = r.render(md)
    title = os.path.splitext(os.path.basename(md_path))[0]
    # 一级标题优先作为页面标题
    m = re.search(r"^#\s+(.*)$", md, flags=re.M)
    if m:
        title = m.group(1).strip()
    return render_page(title, body, r.toc, os.path.basename(md_path))


# ------------------------------------------------------------------ 产物判定
def is_product(name):
    if any(fnmatch.fnmatch(name, g) for g in EXCLUDE_GLOBS):
        return False
    return any(fnmatch.fnmatch(name, g) for g in PRODUCT_GLOBS)


def discover_inputs(args_paths, products_only):
    files = []
    for p in args_paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                if not name.endswith(".md") or name == "index.md":
                    continue
                if products_only and not is_product(name):
                    continue
                files.append(os.path.join(p, name))
        elif p.endswith(".md") and os.path.isfile(p):
            files.append(p)
        else:
            for f in sorted(_glob.glob(p)):
                if f.endswith(".md"):
                    files.append(f)
    return files


def write_index(entries, out_dir):
    links = []
    for md_name, html_name, title in entries:
        links.append('<li><a href="%s">%s</a> <span class="src">← %s</span></li>' % (
            html.escape(html_name), html.escape(title), html.escape(md_name)))
    body = "<h1>模块产物导航</h1><ul>%s</ul>" % "".join(links)
    page = render_page("模块产物导航", body, [], None)
    idx = os.path.join(out_dir, "index.html")
    with open(idx, "w", encoding="utf-8") as f:
        f.write(page)
    return idx


def main(argv=None):
    ap = argparse.ArgumentParser(description="jee-forge 中间产物 md → 带左侧导航 HTML 导出器（纯标准库）")
    ap.add_argument("paths", nargs="+", help="md 文件或目录（可多个）")
    ap.add_argument("-o", "--out", help="输出目录（默认与源 md 同目录）")
    ap.add_argument("--products", action="store_true", help="目录输入时只导出约定阅读型产物（排除 3.x.2 接口清单）")
    ap.add_argument("--index", action="store_true", help="额外生成 index.html 导航首页")
    ap.add_argument("--check", action="store_true", help="只校验解析、不写文件")
    args = ap.parse_args(argv)

    files = discover_inputs(args.paths, args.products)
    if not files:
        print("[export-html] 未发现可导出的 md（路径或过滤条件可能有误）", file=sys.stderr)
        return 1

    written, entries = 0, []
    for md in files:
        try:
            page = convert_file(md)
        except Exception as e:  # noqa: BLE001
            print("[export-html][error] 解析 %s 失败：%s" % (md, e), file=sys.stderr)
            return 2
        if args.check:
            print("[export-html] 可解析：%s" % md)
            continue
        src_dir = os.path.dirname(os.path.abspath(md))
        out_dir = args.out or src_dir
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(md))[0]
        out_path = os.path.join(out_dir, base + ".html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page)
        m = re.search(r"^#\s+(.*)$", open(md, encoding="utf-8").read(), flags=re.M)
        title = m.group(1).strip() if m else base
        entries.append((os.path.basename(md), os.path.basename(out_path), title))
        written += 1
        print("[export-html] %s → %s" % (md, out_path))

    if not args.check and (args.index or len(files) > 1) and entries:
        out_dir = args.out or os.path.dirname(os.path.abspath(files[0]))
        idx = write_index(entries, out_dir)
        print("[export-html] 导航页：%s" % idx)

    if not args.check:
        print("[export-html] 完成：导出 %d 个 HTML（md 仍为真源，本工具不改动任何 md）" % written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
