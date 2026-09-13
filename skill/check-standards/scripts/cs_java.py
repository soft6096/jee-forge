#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-standards 工具的 Java 扫描辅助模块（纯标准库实现）。

本模块只负责"把 Java 源码读进来、切成类/方法、做轻量结构分析"，不做任何规范判定。
判定逻辑全部在 ``cs_checks.py``，渲染在 ``cs_report.py``，CLI 在 ``check_standards.py``。

设计要点：
- 只用 Python 标准库，不依赖 ast-grep / javaparser 等外部工具。
- 用"掩码（mask）"把注释与字符串内容替换为空格，保留换行与字符串定界符，便于用大括号/括号定位方法体；
  原始文本另行保留，用于注释与字符串内容的检查。
- 尽量健壮：任何文件解析异常都返回"空解析结果 + 警告"，绝不抛异常中断整体扫描。
"""

from __future__ import annotations

import bisect
import os
import re
import subprocess

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# Java 方法声明里常见的修饰符关键字（用于从签名中剥离出返回类型）
MODIFIER_KEYWORDS = {
    "public", "private", "protected", "static", "final", "abstract",
    "synchronized", "default", "native", "transient", "volatile", "strictfp",
}

# 会被误认成方法名的控制流关键字（其后的 '{' 是代码块而非方法体）
CONTROL_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "synchronized",
    "try", "do", "else", "finally", "return", "new", "assert", "throw",
}

# 需要做"方法级注释/日志"核对的目标类名后缀（见 SKILL.md 组一）
TARGET_SUFFIXES = (
    "Controller", "ServiceImpl", "Service", "Listener", "Job", "Consumer",
)

# 目标类可能带有的 Spring / 框架注解
TARGET_ANNOTATIONS = (
    "@RestController", "@Controller", "@Service",
    "@RabbitListener", "@KafkaListener", "@Scheduled",
)

JAVA_EXT = ".java"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 单文件超过 5MB 视为异常大文件，跳过并告警


# ---------------------------------------------------------------------------
# 文件读取（UTF-8 / GB18030 兼容，CRLF 兼容）
# ---------------------------------------------------------------------------

def read_text(path):
    """读取文本文件，自动兼容 UTF-8(BOM)/GB18030，容忍 CRLF。

    读取失败返回空串（调用方按空文件处理），绝不抛异常。
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except (OSError, IOError):
        return ""
    for enc in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def read_lines(path):
    """读取文件并按行切分（行尾 \\r 已由 splitlines 去除）。"""
    return read_text(path).splitlines()


def iter_files(root, exts=None):
    """递归遍历 root 下的文件，可用扩展名集合过滤；跳过 .git/target/node_modules。

    产出绝对路径（或 root 为相对路径时的相对路径）。
    """
    if not root or not os.path.exists(root):
        return
    skip_dirs = {".git", "target", "node_modules", ".idea", ".gradle", "build", "dist"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            if exts and not name.lower().endswith(exts):
                continue
            yield os.path.join(dirpath, name)


def iter_java_files(paths):
    """遍历若干路径（文件或目录）下的 .java 文件（去重、稳定排序）。"""
    seen = {}
    for p in paths:
        if not p:
            continue
        if os.path.isfile(p):
            if p.lower().endswith(JAVA_EXT):
                seen[os.path.abspath(p)] = True
        elif os.path.isdir(p):
            for fp in iter_files(p, (JAVA_EXT,)):
                seen[os.path.abspath(fp)] = True
    return sorted(seen.keys())


# ---------------------------------------------------------------------------
# Maven / 资源目录探测
# ---------------------------------------------------------------------------

def find_maven_java_roots(project):
    """探测 Maven 多模块工程的 src/main/java 目录，返回绝对路径列表。

    若根目录本身就是 src/main/java（单模块工程），同样识别。
    """
    roots = []
    for dirpath, dirnames, _ in os.walk(project):
        dirnames[:] = [d for d in dirnames if d not in {".git", "target", "node_modules"}]
        norm = dirpath.replace(os.sep, "/")
        if norm.endswith("/src/main/java"):
            roots.append(os.path.abspath(dirpath))
    return sorted(roots)


def find_resources_roots(project):
    """探测 src/main/resources 目录，返回绝对路径列表。"""
    roots = []
    for dirpath, dirnames, _ in os.walk(project):
        dirnames[:] = [d for d in dirnames if d not in {".git", "target", "node_modules"}]
        norm = dirpath.replace(os.sep, "/")
        if norm.endswith("/src/main/resources"):
            roots.append(os.path.abspath(dirpath))
    return sorted(roots)


def find_mapper_xmls(project):
    """探测 MyBatis Mapper XML（路径含 mapper 的 .xml，排除 target）。"""
    result = []
    for fp in iter_files(project, (".xml",)):
        low = fp.replace(os.sep, "/").lower()
        if "/mapper/" in low or low.endswith("mapper.xml"):
            result.append(os.path.abspath(fp))
    return sorted(set(result))


def find_poms(project):
    """探测全部 pom.xml（含多模块子 pom）。"""
    return sorted(set(os.path.abspath(p) for p in iter_files(project, ("pom.xml",))))


def find_sql_files(project):
    """探测 .sql 文件（如 db/schema.sql、sql/*.sql）。"""
    return sorted(set(os.path.abspath(p) for p in iter_files(project, (".sql",))))


def find_log_configs(project):
    """探测日志框架配置文件（logback*.xml / log4j2*.xml 及 properties）。"""
    result = []
    for fp in iter_files(project, (".xml", ".properties", ".yml", ".yaml")):
        base = os.path.basename(fp).lower()
        if base.startswith("logback") or base.startswith("log4j2") or base.startswith("log4j"):
            result.append(os.path.abspath(fp))
    return sorted(set(result))


def find_docs_md(project):
    """探测 docs/ 下的全部 Markdown。"""
    docs = os.path.join(project, "docs")
    if not os.path.isdir(docs):
        return []
    return sorted(set(os.path.abspath(p) for p in iter_files(docs, (".md",))))


def find_docs_dirs(project):
    """探测 docs/ 下的子目录（用于判断是否存在"模块版本目录"）。"""
    docs = os.path.join(project, "docs")
    if not os.path.isdir(docs):
        return []
    out = []
    for name in sorted(os.listdir(docs)):
        full = os.path.join(docs, name)
        if os.path.isdir(full):
            out.append(os.path.abspath(full))
    return out


# ---------------------------------------------------------------------------
# git 改动范围
# ---------------------------------------------------------------------------

def _run_git(project, args):
    """执行 git 命令，失败返回 None。"""
    try:
        proc = subprocess.run(
            ["git", "-C", project] + args,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace")


def git_changed_java_files(project):
    """返回 (changed_java_files, note)。

    优先级：git status（未提交）→ git diff HEAD~1（刚提交）。都不可用返回 ([], note)。
    """
    files = set()
    # 1) 工作区/暂存区未提交改动
    out = _run_git(project, ["status", "--porcelain"])
    if out is not None:
        for line in out.splitlines():
            if not line.strip():
                continue
            path = line[3:].strip()
            if " -> " in path:  # rename
                path = path.split(" -> ")[-1].strip()
            if path.lower().endswith(JAVA_EXT):
                files.add(os.path.abspath(os.path.join(project, path)))
        if files:
            return sorted(files), "git status（未提交改动）"
    # 2) 最近一次提交
    out = _run_git(project, ["diff", "HEAD~1", "--name-only"])
    if out is not None:
        for line in out.splitlines():
            line = line.strip()
            if line.lower().endswith(JAVA_EXT):
                files.add(os.path.abspath(os.path.join(project, line)))
        if files:
            return sorted(files), "git diff HEAD~1（最近一次提交）"
    return [], "git 不可用或无改动"


# ---------------------------------------------------------------------------
# Java 源码掩码 / 轻量解析
# ---------------------------------------------------------------------------

_MASK_CODE = 0
_MASK_LINE_COMMENT = 1
_MASK_BLOCK_COMMENT = 2
_MASK_STRING = 3
_MASK_CHAR = 4


def mask_source(src):
    """把注释内容与字符串/字符字面量内容替换为空格，保留换行、括号、分号与字符串定界符。

    用于按大括号/括号做结构定位；注释与字符串"内容"的检查请用原始文本。
    """
    out = []
    i = 0
    n = len(src)
    state = _MASK_CODE
    while i < n:
        c = src[i]
        if state == _MASK_CODE:
            if c == "/" and i + 1 < n and src[i + 1] == "/":
                state = _MASK_LINE_COMMENT
                out.append("  ")
                i += 2
                continue
            if c == "/" and i + 1 < n and src[i + 1] == "*":
                state = _MASK_BLOCK_COMMENT
                out.append("  ")
                i += 2
                continue
            if c == '"':
                state = _MASK_STRING
                out.append(c)
                i += 1
                continue
            if c == "'":
                state = _MASK_CHAR
                out.append(c)
                i += 1
                continue
            out.append(c)
            i += 1
        elif state == _MASK_LINE_COMMENT:
            if c == "\n":
                state = _MASK_CODE
                out.append(c)
            else:
                out.append("\t" if c == "\t" else " ")
            i += 1
        elif state == _MASK_BLOCK_COMMENT:
            if c == "*" and i + 1 < n and src[i + 1] == "/":
                out.append("  ")
                i += 2
                state = _MASK_CODE
                continue
            out.append("\n" if c == "\n" else ("\t" if c == "\t" else " "))
            i += 1
        elif state == _MASK_STRING:
            if c == "\\" and i + 1 < n:
                out.append("  ")
                i += 2
                continue
            if c == '"':
                state = _MASK_CODE
                out.append(c)
                i += 1
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
        else:  # _MASK_CHAR
            if c == "\\" and i + 1 < n:
                out.append("  ")
                i += 2
                continue
            if c == "'":
                state = _MASK_CODE
                out.append(c)
                i += 1
                continue
            out.append(" ")
            i += 1
    return "".join(out)


def strip_annotations(text):
    """移除注解（``@Name`` 与 ``@Name(...)`` 带平衡括号的参数），保留其余文本。"""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "@":
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] in "_.$"):
                j += 1
            if j < n and text[j] == "(":
                depth = 0
                while j < n:
                    if text[j] == "(":
                        depth += 1
                    elif text[j] == ")":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
            out.append(" ")
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _find_matching_brace(masked, open_pos):
    """给定 '{' 的偏移，返回匹配 '}' 的偏移；找不到返回 len(masked)-1。"""
    depth = 0
    n = len(masked)
    i = open_pos
    while i < n:
        c = masked[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n - 1


class MethodInfo(object):
    """一个 Java 方法（含构造器）的轻量描述。"""

    __slots__ = (
        "name", "sig", "return_type", "modifiers", "annotations",
        "is_constructor", "javadoc", "decl_line", "body_open_line",
        "body_close_line", "body_start_line", "body_end_line",
        "body_orig_lines", "body_masked_lines", "class_name",
    )

    def __init__(self):
        self.name = ""
        self.sig = ""
        self.return_type = ""
        self.modifiers = []
        self.annotations = []
        self.is_constructor = False
        self.javadoc = None
        self.decl_line = 0        # 1-based，声明（含注解）起始行
        self.body_open_line = 0   # 1-based，'{' 所在行
        self.body_close_line = 0  # 1-based，'}' 所在行
        self.body_start_line = 0  # 1-based，方法体第一行
        self.body_end_line = 0    # 1-based，方法体最后一行
        self.body_orig_lines = []
        self.body_masked_lines = []
        self.class_name = ""

    def has_body(self):
        return self.body_close_line >= self.body_open_line > 0

    def code_lines(self):
        """方法体内非空、非纯大括号、非注释的行数（用掩码行判断）。"""
        count = 0
        for ln, orig in zip(self.body_masked_lines, self.body_orig_lines):
            s = ln.strip()
            if not s:
                continue
            if s in ("{", "}"):
                continue
            if s.startswith("//") or s.startswith("*"):
                continue
            count += 1
        return count

    def body_text_masked(self):
        return "\n".join(self.body_masked_lines)

    def body_text_orig(self):
        return "\n".join(self.body_orig_lines)


class ClassInfo(object):
    """一个 Java 顶层类型（类/接口/枚举）的轻量描述。"""

    __slots__ = ("path", "name", "kind", "annotations", "methods", "warnings")

    def __init__(self, path):
        self.path = path
        self.name = ""
        self.kind = "class"   # class | interface | enum | record | unknown
        self.annotations = []
        self.methods = []
        self.warnings = []


_INTERFACE_RE = re.compile(r"\binterface\s+([A-Za-z_$][\w$]*)")
_ENUM_RE = re.compile(r"\benum\s+([A-Za-z_$][\w$]*)")
_CLASS_RE = re.compile(r"\bclass\s+([A-Za-z_$][\w$]*)")
_RECORD_RE = re.compile(r"\brecord\s+([A-Za-z_$][\w$]*)\s*\(")
_ANNOT_RE = re.compile(r"@([A-Za-z_$][\w$.]*)")


def _extract_type_decl(masked):
    """返回 (kind, name)：优先取文件中最靠前的类型声明。"""
    candidates = []
    m = _CLASS_RE.search(masked)
    if m:
        candidates.append((m.start(), "class", m.group(1)))
    m = _INTERFACE_RE.search(masked)
    if m:
        candidates.append((m.start(), "interface", m.group(1)))
    m = _ENUM_RE.search(masked)
    if m:
        candidates.append((m.start(), "enum", m.group(1)))
    m = _RECORD_RE.search(masked)
    if m:
        candidates.append((m.start(), "record", m.group(1)))
    if not candidates:
        return "unknown", ""
    candidates.sort(key=lambda x: x[0])
    _, kind, name = candidates[0]
    return kind, name


def _looks_like_method_sig(seg):
    """判断 ``seg``（'{' 之前的语句片段）是否像一个方法/构造器签名。

    是 → 返回 dict(name, sig, return_type, modifiers, annotations)；否 → None。
    """
    raw = seg.strip()
    if not raw:
        return None
    annotations = _ANNOT_RE.findall(raw)
    sig = strip_annotations(raw).strip()
    if not sig:
        return None
    # 去掉 throws 子句
    sig_no_throws = re.sub(r"\bthrows\b[\w\s.,<>\[\]$]*$", "", sig).strip()
    if not sig_no_throws.endswith(")"):
        return None
    # 找到末尾 ')' 对应的 '('
    close_idx = len(sig_no_throws) - 1
    depth = 0
    open_idx = -1
    for k in range(close_idx, -1, -1):
        ch = sig_no_throws[k]
        if ch == ")":
            depth += 1
        elif ch == "(":
            depth -= 1
            if depth == 0:
                open_idx = k
                break
    if open_idx < 0:
        return None
    before = sig_no_throws[:open_idx].strip()
    if not before:
        return None
    if "->" in before or "=" in before:
        return None
    m = re.search(r"([A-Za-z_$][\w$]*)\s*$", before)
    if not m:
        return None
    name = m.group(1)
    prefix = before[:m.start()].strip()
    prefix_tokens = prefix.split()
    # 控制流关键字（含 else if / do / new 等）不能作为方法名 → 是代码块
    if name in CONTROL_KEYWORDS:
        return None
    # 匿名内部类：new Xxx(...) {
    if "new" in prefix_tokens:
        return None
    # 返回类型 = 前缀去掉修饰符后的剩余
    ret_tokens = [t for t in prefix_tokens if t not in MODIFIER_KEYWORDS]
    return_type = " ".join(ret_tokens).strip()
    modifiers = [t for t in prefix_tokens if t in MODIFIER_KEYWORDS]
    return {
        "name": name,
        "sig": sig_no_throws,
        "return_type": return_type,
        "modifiers": modifiers,
        "annotations": annotations,
        "is_constructor": return_type == "",
    }


def parse_java(path):
    """解析一个 Java 文件为 :class:`ClassInfo`。

    解析失败返回带 warnings 的空 ClassInfo，绝不抛异常。
    """
    info = ClassInfo(path)
    try:
        src = read_text(path)
    except Exception as exc:  # pragma: no cover - 防御性
        info.warnings.append("读取失败: %s" % exc)
        return info
    if not src.strip():
        info.warnings.append("空文件")
        return info
    try:
        lines = src.splitlines()
        masked = mask_source(src)
        masked_lines = masked.splitlines()
        line_starts = [0]
        for ln in lines:
            line_starts.append(line_starts[-1] + len(ln) + 1)

        kind, name = _extract_type_decl(masked)
        info.kind = kind
        info.name = name
        decl_pos = _first_decl_pos(masked)
        head = masked[:decl_pos] if decl_pos is not None else masked
        info.annotations = _ANNOT_RE.findall(head)

        positions = [(mm.start(), mm.group()) for mm in re.finditer(r"[(){};]", masked)]
        stmt_start = 0
        paren_depth = 0
        stack = []
        for pos, ch in positions:
            if ch == "(":
                paren_depth += 1
            elif ch == ")":
                if paren_depth > 0:
                    paren_depth -= 1
            elif ch == "{":
                if paren_depth > 0:
                    continue
                meta = _looks_like_method_sig(masked[stmt_start:pos])
                stack.append(("method" if meta is not None else "block", meta, stmt_start))
                stmt_start = pos + 1
            elif ch == "}":
                if paren_depth > 0:
                    continue
                if stack:
                    ctx_kind, meta, seg_begin = stack.pop()
                    if ctx_kind == "method":
                        _finalize_method(info, lines, masked_lines, masked,
                                         line_starts, meta, seg_begin, pos)
                stmt_start = pos + 1
            elif ch == ";":
                if paren_depth == 0:
                    if len(stack) <= 1:
                        meta = _looks_like_method_sig(masked[stmt_start:pos])
                        if meta is not None:
                            _finalize_abstract(info, lines, masked, line_starts,
                                               meta, stmt_start)
                    stmt_start = pos + 1
        return info
    except Exception as exc:  # pragma: no cover - 防御性
        info.warnings.append("解析异常: %s" % exc)
        return info


def _first_decl_pos(masked):
    """返回类型声明（class/interface/enum/record）关键字最早出现的偏移，找不到返回 None。"""
    positions = []
    for regex in (_CLASS_RE, _INTERFACE_RE, _ENUM_RE, _RECORD_RE):
        m = regex.search(masked)
        if m:
            positions.append(m.start())
    return min(positions) if positions else None


def _finalize_method(info, lines, masked_lines, masked_text, line_starts, meta,
                     seg_begin, close_pos):
    """根据扫描结果补全 MethodInfo（javadoc / 行号 / 方法体行）。"""
    def pos_to_line(pos):
        return bisect.bisect_right(line_starts, pos)

    mi = MethodInfo()
    mi.class_name = info.name
    mi.name = meta["name"]
    mi.sig = meta["sig"]
    mi.return_type = meta["return_type"]
    mi.modifiers = meta["modifiers"]
    mi.annotations = meta["annotations"]
    mi.is_constructor = meta["is_constructor"]

    k = seg_begin
    total = len(masked_text)
    while k < total and masked_text[k] in " \t\r\n":
        k += 1
    mi.decl_line = pos_to_line(k) if k < total else pos_to_line(seg_begin)

    open_pos = masked_text.find("{", seg_begin, close_pos + 1)
    if open_pos < 0:
        open_pos = seg_begin
    mi.body_open_line = pos_to_line(open_pos)
    mi.body_close_line = pos_to_line(close_pos)
    mi.body_start_line = mi.body_open_line + 1
    mi.body_end_line = mi.body_close_line - 1

    s = max(mi.body_open_line, 0)
    e = max(mi.body_close_line - 1, s)
    mi.body_orig_lines = lines[s:e]
    mi.body_masked_lines = masked_lines[s:e]

    mi.javadoc = _find_javadoc_above(lines, mi.decl_line - 1)
    info.methods.append(mi)


def _finalize_abstract(info, lines, masked_text, line_starts, meta, seg_begin):
    """补全无方法体的声明（接口方法 / 抽象方法）：只记录签名、行号与 javadoc。"""
    def pos_to_line(pos):
        return bisect.bisect_right(line_starts, pos)

    mi = MethodInfo()
    mi.class_name = info.name
    mi.name = meta["name"]
    mi.sig = meta["sig"]
    mi.return_type = meta["return_type"]
    mi.modifiers = meta["modifiers"]
    mi.annotations = meta["annotations"]
    mi.is_constructor = meta["is_constructor"]
    k = seg_begin
    total = len(masked_text)
    while k < total and masked_text[k] in " \t\r\n":
        k += 1
    mi.decl_line = pos_to_line(k) if k < total else pos_to_line(seg_begin)
    mi.javadoc = _find_javadoc_above(lines, mi.decl_line - 1)
    info.methods.append(mi)


def _find_javadoc_above(lines, decl_idx):
    """从 0-based 行索引 decl_idx 往上找紧邻的 ``/** ... */``，返回文本或 None。"""
    j = decl_idx - 1
    while j >= 0:
        s = lines[j].strip()
        if s == "":
            j -= 1
            continue
        break
    if j < 0:
        return None
    if not lines[j].rstrip().endswith("*/"):
        return None
    k = j
    while k >= 0:
        if "/**" in lines[k]:
            return "\n".join(lines[k:j + 1])
        if "/*" in lines[k]:
            return None
        k -= 1
    return None


# ---------------------------------------------------------------------------
# 通用小工具
# ---------------------------------------------------------------------------

def iter_code_lines(path):
    """产出 (lineno, original_line, masked_line)：跳过空行与纯注释行（掩码后为空）。

    代码行保留原文（含字符串内容）以便检测，同时给出掩码行（注释已抹除）用于排除注释干扰。
    """
    src = read_text(path)
    if not src:
        return
    lines = src.splitlines()
    masked = mask_source(src).splitlines()
    for i, orig in enumerate(lines):
        m = masked[i] if i < len(masked) else ""
        if not m.strip():
            continue
        yield i + 1, orig, m


def relpath(path, base):
    """尽量返回相对 base 的路径，失败返回原路径。"""
    try:
        return os.path.relpath(path, base)
    except ValueError:  # 跨盘符
        return path
