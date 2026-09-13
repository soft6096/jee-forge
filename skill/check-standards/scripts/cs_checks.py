#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-standards 的 33 项核对判定逻辑（纯标准库实现）。

严格对照 SKILL.md「检查项清单」实现。可机械判定的项给出 pass/fail；语义/需人眼判断的项
一律标记 manual/warn 并附证据，绝不假装 pass。扫描范围与模式由 :class:`Context` 承载。

对外主要接口：
- :data:`CHECK_NAMES`：id → 名称（1..33）
- :func:`detect_mode`：判定 standard / legacy
- :func:`detect_renames`：第 0 步产物命名矫正（只检测，不落盘）
- :func:`run_all`：按 --only/--skip 执行全部核对，返回报告 dict
"""

from __future__ import annotations

import os
import re
from collections import defaultdict

import cs_java as J

# ---------------------------------------------------------------------------
# 核对项名称（顺序即报告顺序）
# ---------------------------------------------------------------------------

CHECK_NAMES = {
    1: "方法级注释全覆盖",
    2: "方法级日志全覆盖",
    3: "步骤注释 + WHY",
    4: "禁翻译式注释",
    5: "全类 @Slf4j + 无 System.out",
    6: "接口文档支持（选型敏感）",
    7: "日志框架支持（选型敏感）",
    8: "SQL 在 XML（选型敏感）",
    9: "JSON 入参/出参产物",
    10: "SQL 注释（方案内）",
    11: "DDL 字段注释",
    12: "SQL 注入",
    13: "UPDATE/DELETE 带 WHERE",
    14: "事务 rollbackFor",
    15: "构造器注入",
    16: "分层边界",
    17: "Entity 不暴露",
    18: "异常处理",
    19: "命名单字母/泛称",
    20: "统一返回体（选型敏感）",
    21: "密码加密",
    22: "分页上限",
    23: "校验 message 具体性",
    24: "Job 防重入 + 批处理",
    25: "Listener 幂等 + 死信",
    26: "文件上传安全",
    27: "写接口幂等",
    28: "敏感信息进日志",
    29: "集合命名",
    30: "魔法值/缓存 key",
    31: "公共组件复用",
    32: "日志参数 NPE",
    33: "同表重复映射",
}

# 目标类（组一方法级核对）后缀与注解
_TARGET_SUFFIXES = ("Controller", "ServiceImpl", "Service", "Listener", "Job", "Consumer")
_TARGET_ANN_SIMPLE = {
    "RestController", "Controller", "Service",
    "RabbitListener", "KafkaListener", "Scheduled",
}

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_WARN = "warn"
STATUS_MANUAL = "manual"
STATUS_SKIP = "skip"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class Evidence(object):
    """单条证据：文件 + 行号 + 说明。"""

    __slots__ = ("file", "line", "detail")

    def __init__(self, file, line, detail=""):
        self.file = file
        self.line = int(line) if line else 0
        self.detail = detail

    def to_dict(self):
        return {"file": self.file, "line": self.line, "detail": self.detail}


class Item(object):
    """单项核对结果。"""

    __slots__ = ("id", "name", "status", "note", "evidence", "extra")

    def __init__(self, cid, name, status, note="", evidence=None, extra=None):
        self.id = cid
        self.name = name
        self.status = status
        self.note = note
        self.evidence = evidence or []
        self.extra = extra or {}

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "note": self.note,
            "evidence": [e.to_dict() for e in self.evidence],
        }


class Bag(object):
    """证据收集器：限制落盘条数，同时记录命中总数。"""

    __slots__ = ("limit", "items", "total")

    def __init__(self, limit):
        self.limit = max(int(limit), 1)
        self.items = []
        self.total = 0

    def add(self, file, line, detail=""):
        self.total += 1
        if len(self.items) < self.limit:
            self.items.append(Evidence(file, line, detail))

    def more(self):
        return max(0, self.total - len(self.items))


class Context(object):
    """一次扫描的上下文：范围、模式、文件集合与解析缓存。"""

    def __init__(self, project, java_files, scope, scope_path, mode, mode_note,
                 constraint_path, changed_set, max_findings=20):
        self.project = os.path.abspath(project)
        self.java_files = list(java_files)
        self.scope = scope
        self.scope_path = scope_path
        self.mode = mode
        self.mode_note = mode_note
        self.constraint_path = constraint_path
        self.changed = set(changed_set or ())
        self.max_findings = max_findings
        self.poms = J.find_poms(self.project)
        self.mapper_xmls = J.find_mapper_xmls(self.project)
        self.sql_files = J.find_sql_files(self.project)
        self.docs_md = J.find_docs_md(self.project)
        self.docs_dirs = J.find_docs_dirs(self.project)
        self.log_configs = J.find_log_configs(self.project)
        self._classes = None
        self._targets = None

    def rel(self, path):
        return J.relpath(path, self.project)

    def is_changed(self, path):
        return os.path.abspath(path) in self.changed

    def tag(self, path):
        if not self.changed:
            return ""
        return "[本次改动] " if self.is_changed(path) else "[存量] "

    def classes(self):
        """全部 Java 文件解析结果（惰性、缓存）。"""
        if self._classes is None:
            self._classes = []
            for f in self.java_files:
                try:
                    self._classes.append(J.parse_java(f))
                except Exception:  # pragma: no cover - 防御性
                    pass
        return self._classes

    def target_classes(self):
        """#2/#5 目标类（Controller/Service/ServiceImpl/Job/Listener）。"""
        if self._targets is None:
            self._targets = [ci for ci in self.classes() if is_target_class(ci)]
        return self._targets

    def javadoc_classes(self):
        """#1 核对对象：生产目标类。"""
        return list(self.target_classes())

    def controller_classes(self):
        out = []
        for ci in self.classes():
            if ci.name.endswith("Controller"):
                out.append(ci)
            elif "RestController" in _simple_anns(ci) or "Controller" in _simple_anns(ci):
                out.append(ci)
        return out


def _simple_anns(ci):
    return set(a.split(".")[-1] for a in ci.annotations)


def is_target_class(ci):
    """判断类是否属于组一（方法级核对）目标类型。"""
    if ci.name.endswith(_TARGET_SUFFIXES):
        return True
    if _simple_anns(ci) & _TARGET_ANN_SIMPLE:
        return True
    return False


# ---------------------------------------------------------------------------
# 模式判定 与 第 0 步命名矫正
# ---------------------------------------------------------------------------

def detect_mode(project):
    """判定 standard / legacy 模式。

    返回 (mode, note, constraint_path)。找不到 2.1 约束时按规范默认（standard）并注明。
    """
    docs = os.path.join(project, "docs")
    if not os.path.isdir(docs):
        return "standard", "按规范默认值判定（未找到 2.1 约束）", None
    all_md = []
    for dirpath, dirnames, filenames in os.walk(docs):
        dirnames[:] = [d for d in dirnames if d not in {".git"}]
        for name in filenames:
            if name.lower().endswith(".md"):
                all_md.append(os.path.join(dirpath, name))
    legacy = []
    standard = []
    for p in all_md:
        base = os.path.basename(p)
        if base.startswith("2.1-项目约束-存量适配"):
            legacy.append(p)
        elif base.startswith("2.1-项目约束"):
            standard.append(p)
        if base.startswith("0.5-存量代码扫描"):
            legacy.append(p)
    if legacy:
        return "legacy", "存量适配模式（命中 0.5/2.1-存量适配）", legacy[0]
    if standard:
        return "standard", "标准模式（命中 2.1-项目约束）", standard[0]
    return "standard", "按规范默认值判定（未找到 2.1 约束）", None


_TASK_ID_RE = re.compile(r"T\d+(?:-\d+)?-")


def detect_renames(project):
    """第 0 步：检测 docs/ 中间产物命名/路径不合规，返回 renames 列表（只检测）。

    每条为 {"old","new","reason","apply"(bool)}；new 为空表示无法机械推导（不参与 --fix）。
    """
    renames = []
    docs = os.path.join(project, "docs")
    if not os.path.isdir(docs):
        return renames
    for dirpath, dirnames, filenames in os.walk(docs):
        dirnames[:] = [d for d in dirnames if d not in {".git"}]
        for name in sorted(filenames):
            if not name.lower().endswith(".md"):
                continue
            full = os.path.join(dirpath, name)
            new_name = name
            reasons = []
            # 1) 技术方案漏 .1：3.<n>-xxx-技术方案.md → 3.<n>.1-xxx-技术方案.md
            m = re.match(r"^3\.(\d+)-(.+)-技术方案\.md$", new_name)
            if m:
                new_name = "3.%s.1-%s-技术方案.md" % (m.group(1), m.group(2))
                reasons.append("技术方案漏功能序号 .1")
            # 2) 任务 ID 前缀 Txx(-yy)-
            if _TASK_ID_RE.search(new_name):
                new_name = _TASK_ID_RE.sub("", new_name, count=1)
                reasons.append("去除任务 ID 前缀")
            # 2b) 接口清单命名不符合 3.x.2 规范（无编号，无法机械推导功能序号）
            if "接口清单" in new_name and not _JSON_PRODUCT_RE.match(new_name):
                reasons.append("接口清单命名不符合 3.x.2 规范（需人工确认功能序号）")
            # 3) 5.2/5.3 报告漏功能序号：尝试从同名技术方案推导
            m = re.match(r"^5\.([23])-(.+)-(规范核对报告|验收报告)\.md$", new_name)
            if m:
                feat = _derive_feature_no(docs, m.group(2))
                if feat is not None:
                    new_name = "5.%s.%s-%s-%s.md" % (m.group(1), feat, m.group(2), m.group(3))
                    reasons.append("补功能序号")
                else:
                    reasons.append("漏功能序号（无法从技术方案推导，需人工确认）")
            # 4) 4.1 任务拆解漏功能序号
            m = re.match(r"^4\.1-(.+)-任务拆解\.md$", new_name)
            if m:
                feat = _derive_feature_no(docs, m.group(1))
                if feat is not None:
                    new_name = "4.1.%s-%s-任务拆解.md" % (feat, m.group(1))
                    reasons.append("补功能序号")
                else:
                    reasons.append("漏功能序号（无法从技术方案推导，需人工确认）")
            # 5) 路径不在模块版本目录下（仅对中间产物命名规则命中的文件）
            is_product = bool(re.match(r"^(3\.\d|4\.1|5\.[23])", name)) or _TASK_ID_RE.search(name)
            if is_product and not _in_module_version_dir(dirpath, docs):
                reasons.append("路径不在 docs/<模块名>V<版本>-<时间戳>/ 下")
            if reasons:
                old_path = J.relpath(full, project)
                new_path = old_path
                if new_name != name:
                    new_path = J.relpath(os.path.join(dirpath, new_name), project)
                renames.append({
                    "old": old_path,
                    "new": new_path if new_name != name else "",
                    "reason": "；".join(reasons),
                    "apply": new_name != name,
                })
    return renames


def _derive_feature_no(docs, feature_name):
    """从同名技术方案文件名 3.<n>.1-<name>-技术方案.md 推导功能序号 n。"""
    pattern = re.compile(r"^3\.(\d+)\.1-.+-技术方案\.md$")
    for dirpath, dirnames, filenames in os.walk(docs):
        for name in filenames:
            m = pattern.match(name)
            if m and feature_name in name:
                return m.group(1)
    return None


def _in_module_version_dir(dirpath, docs):
    """判断目录是否匹配 docs/<模块名>V<版本>-<时间戳>/ 形态。"""
    rel = os.path.relpath(dirpath, docs)
    if rel == ".":
        return False
    first = rel.split(os.sep)[0]
    return bool(re.match(r"^.+V[\w.]+-\d{8,}$", first))


# ---------------------------------------------------------------------------
# 通用匹配小工具
# ---------------------------------------------------------------------------

def _clean_xml(text):
    """移除 XML 注释，便于结构判定。"""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def _line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def _read(path):
    return J.read_text(path)


def _finditer_pos(regex, text):
    for m in regex.finditer(text):
        yield m, _line_of(text, m.start())


def _is_wrapper_sql(expr):
    """判断 ${...} 内是否为 MyBatis-Plus 包装器（框架生成、非直接用户输入）。"""
    low = expr.strip().lower()
    return low.startswith("ew.") or low.startswith("ew.get") or low.startswith("wrapper")


# ---------------------------------------------------------------------------
# 组一：方法与日志
# ---------------------------------------------------------------------------

_LOG_INFO_RE = re.compile(r"\b(?:log|LOG|logger|LOGGER)\.(?:info|warn|error)\s*\(")
_LOG_DEBUG_RE = re.compile(r"\b(?:log|LOG|logger|LOGGER)\.debug\s*\(")
_STEP_COMMENT_RE = re.compile(r"//\s*\d+\s*[.、)]")
_ANY_COMMENT_RE = re.compile(r"//|/\*")


def _is_trivial_accessor(m):
    """纯 getter/setter/单行透传 → 豁免 #2 日志核对。"""
    body = m.body_text_masked().strip()
    body = body.strip("{}").strip()
    body = re.sub(r"\s+", " ", body)
    if re.fullmatch(r"return\s+[\w.$\[\]()\s,]*;", body):
        return True
    if re.fullmatch(r"(?:this\.)?\w+\s*=\s*[\w.$\[\]()\s,]*;", body):
        return True
    return False


def _scope_note_01(ctx):
    """#1 的扫描范围声明。"""
    return "扫描 src/main/java"


def check_01(ctx):
    bag = Bag(ctx.max_findings)
    total = 0
    for ci in ctx.javadoc_classes():
        for m in ci.methods:
            total += 1
            if not m.javadoc:
                bag.add(ctx.rel(ci.path), m.decl_line, "%s 方法缺 Javadoc" % m.name)
    scope = _scope_note_01(ctx)
    if total == 0:
        return Item(1, CHECK_NAMES[1], STATUS_PASS, "未发现需核对的方法；%s" % scope)
    if bag.total:
        return Item(1, CHECK_NAMES[1], STATUS_FAIL,
                    "%d/%d 个方法缺 Javadoc；%s" % (bag.total, total, scope), bag.items)
    return Item(1, CHECK_NAMES[1], STATUS_PASS,
                "%d 个方法均有 Javadoc；%s" % (total, scope))


def check_02(ctx):
    bag = Bag(ctx.max_findings)
    manual_bag = Bag(ctx.max_findings)
    total = 0
    skipped = 0
    for ci in ctx.target_classes():
        for m in ci.methods:
            if not m.has_body() or m.code_lines() == 0:
                continue
            total += 1
            if _is_trivial_accessor(m):
                skipped += 1
                continue
            body = m.body_text_masked()
            info = len(_LOG_INFO_RE.findall(body))
            code = m.code_lines()
            if info == 0:
                has_debug = bool(_LOG_DEBUG_RE.search(body))
                bag.add(ctx.rel(ci.path), m.body_open_line,
                        "%s 方法体无 INFO/WARN/ERROR%s" % (
                            m.name, "（仅 log.debug）" if has_debug else "（零日志）"))
                continue
            if info == 1 and code >= 20:
                first_info_ord = _first_code_line_ordinal(m, _LOG_INFO_RE)
                if first_info_ord is not None and first_info_ord <= 3:
                    manual_bag.add(ctx.rel(ci.path), m.body_open_line,
                                   "%s 疑似'半覆盖'（仅开头 1 条 INFO，方法体 %d 行）"
                                   % (m.name, code))
    notes = "核对 %d 个业务方法" % total
    if skipped:
        notes += "，豁免 %d 个纯 getter/setter/单行透传" % skipped
    if bag.total:
        return Item(2, CHECK_NAMES[2], STATUS_FAIL, notes + "；%d 个无日志" % bag.total,
                    bag.items)
    if manual_bag.total:
        return Item(2, CHECK_NAMES[2], STATUS_MANUAL,
                    notes + "；%d 个疑似半覆盖需人工核对" % manual_bag.total,
                    manual_bag.items)
    return Item(2, CHECK_NAMES[2], STATUS_PASS, notes + "，日志覆盖通过")


def _first_code_line_ordinal(m, regex):
    """返回正则首次命中的行在"代码行序号"中的位置（1-based），找不到返回 None。"""
    ordinal = 0
    for masked, orig in zip(m.body_masked_lines, m.body_orig_lines):
        s = masked.strip()
        if not s or s in ("{", "}"):
            continue
        ordinal += 1
        if regex.search(orig) or regex.search(masked):
            return ordinal
    return None


def check_03(ctx):
    bag = Bag(ctx.max_findings)
    total = 0
    for ci in ctx.target_classes():
        for m in ci.methods:
            if not m.has_body() or m.code_lines() == 0:
                continue
            total += 1
            code = m.code_lines()
            numbered = 0
            last_numbered = -1
            for i, line in enumerate(m.body_orig_lines):
                if _STEP_COMMENT_RE.search(line):
                    numbered += 1
                    last_numbered = i
            if code >= 6 and numbered == 0:
                bag.add(ctx.rel(ci.path), m.body_open_line,
                        "%s 方法体 %d 行但无编号步骤注释(// 1.)" % (m.name, code))
                continue
            run, run_start = 0, None
            for i, (masked, orig) in enumerate(zip(m.body_masked_lines, m.body_orig_lines)):
                s = masked.strip()
                if not s or s in ("{", "}"):
                    continue
                if _ANY_COMMENT_RE.search(orig):
                    run = 0
                    run_start = None
                    continue
                run += 1
                if run == 1:
                    run_start = i
                if run >= 10:
                    bag.add(ctx.rel(ci.path), m.body_open_line + run_start + 1,
                            "%s 连续 %d 行无注释" % (m.name, run))
                    run = 0
                    run_start = None
                    break
            if code >= 20 and numbered > 0 and last_numbered < (len(m.body_orig_lines) * 2 // 3):
                bag.add(ctx.rel(ci.path), m.body_open_line,
                        "%s 长方法(%d 行)编号注释未覆盖到后半段" % (m.name, code))
    if total == 0:
        return Item(3, CHECK_NAMES[3], STATUS_PASS, "未发现需核对的业务方法")
    if bag.total:
        return Item(3, CHECK_NAMES[3], STATUS_MANUAL,
                    "%d 处疑似步骤注释缺失（启发式，需人工通读）" % bag.total, bag.items)
    return Item(3, CHECK_NAMES[3], STATUS_PASS,
                "启发式未发现步骤注释缺失（%d 个方法；语义质量仍需通读）" % total)


_TRANSLATION_HINT_RE = re.compile(r"^\s*//\s*([A-Za-z][\w\s]{0,24})\s*$")
_CAMEL_RE = re.compile(r"[A-Za-z_$][\w$]*")


def check_04(ctx):
    bag = Bag(ctx.max_findings)
    for ci in ctx.target_classes():
        lines = J.read_lines(ci.path)
        for i, line in enumerate(lines):
            m = _TRANSLATION_HINT_RE.match(line)
            if not m:
                continue
            comment = m.group(1).strip().lower()
            if not comment or comment.startswith(("todo", "why", "fixme")):
                continue
            nxt = ""
            for j in range(i + 1, min(i + 3, len(lines))):
                if lines[j].strip():
                    nxt = lines[j]
                    break
            if not nxt:
                continue
            words = set(w.lower() for w in _CAMEL_RE.findall(comment))
            code_words = set()
            for token in _CAMEL_RE.findall(nxt):
                code_words.add(token.lower())
                parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", token)
                for p in parts:
                    code_words.add(p.lower())
            if words and words.issubset(code_words):
                bag.add(ctx.rel(ci.path), i + 1, "疑似逐词翻译注释: %s" % line.strip())
    note = "注释语义判断项，已列出可疑候选（启发式）"
    if bag.total:
        note += "；候选 %d 处" % bag.total
    else:
        note += "；未发现 ASCII 逐词翻译候选（中文注释仍需人工通读）"
    return Item(4, CHECK_NAMES[4], STATUS_MANUAL, note, bag.items)


def check_05(ctx):
    bag = Bag(ctx.max_findings)
    sysout = Bag(ctx.max_findings)
    missing = 0
    checked = 0
    for ci in ctx.target_classes():
        if ci.kind == "interface":
            continue
        checked += 1
        if "Slf4j" not in _simple_anns(ci):
            missing += 1
            bag.add(ctx.rel(ci.path), 1, "%s 缺 @Slf4j" % (ci.name or os.path.basename(ci.path)))
    for f in ctx.java_files:
        try:
            masked = J.mask_source(_read(f))
        except Exception:  # pragma: no cover - 防御性
            continue
        for m in re.finditer(r"System\.(?:out|err)\b", masked):
            sysout.add(ctx.rel(f), _line_of(masked, m.start()),
                       "使用 System.%s" % ("out" if "out" in m.group(0) else "err"))
    if bag.total or sysout.total:
        ev = bag.items + sysout.items
        return Item(5, CHECK_NAMES[5], STATUS_FAIL,
                    "缺 @Slf4j %d 个；System.out/err %d 处" % (missing, sysout.total),
                    ev[:ctx.max_findings])
    return Item(5, CHECK_NAMES[5], STATUS_PASS,
                "%d 个目标类均有 @Slf4j，无 System.out/err" % checked)


# ---------------------------------------------------------------------------
# 组二：框架与产物（选型敏感）
# ---------------------------------------------------------------------------

_DOC_DEP_RE = re.compile(r"springdoc|knife4j|springfox|swagger", re.I)
_DOC_ANN_RE = re.compile(r"@(Tag|Operation|Api|ApiOperation|Schema|ApiModelProperty)\b")
_LOG_FW_DEP_RE = re.compile(r"log4j2|log4j|logback", re.I)
_ANN_SQL_RE = re.compile(r"@(Select|Insert|Update|Delete)\b|<script\b")


def _pom_texts(ctx):
    return [(ctx.rel(p), _read(p)) for p in ctx.poms]


def check_06(ctx):
    dep_hits = []
    for rel, text in _pom_texts(ctx):
        for m in _DOC_DEP_RE.finditer(text):
            dep_hits.append((rel, _line_of(text, m.start()), m.group(0)))
    ann_files = []
    for f in ctx.java_files:
        masked = J.mask_source(_read(f))
        m = _DOC_ANN_RE.search(masked)
        if m:
            ann_files.append((f, _line_of(masked, m.start()), m.group(0)))
    has_dep = bool(dep_hits)
    has_ann = bool(ann_files)
    evidence = [Evidence(r, l, "依赖: %s" % t) for r, l, t in dep_hits[:ctx.max_findings]]
    evidence += [Evidence(ctx.rel(f), l, "注解: %s" % t) for f, l, t in ann_files[:ctx.max_findings]]
    if not has_dep and not has_ann:
        return Item(6, CHECK_NAMES[6], STATUS_MANUAL,
                    "未发现接口文档依赖与注解；%s，需人工确认选型（Apifox/springdoc）"
                    % ctx.mode_note, evidence)
    if has_dep and has_ann:
        return Item(6, CHECK_NAMES[6], STATUS_PASS,
                    "发现接口文档依赖与注解", evidence)
    if has_dep and not has_ann:
        return Item(6, CHECK_NAMES[6], STATUS_MANUAL,
                    "发现接口文档依赖但未见 @Tag/@Operation/@Schema 注解；%s，需人工确认"
                    % ctx.mode_note, evidence)
    return Item(6, CHECK_NAMES[6], STATUS_MANUAL,
                "发现接口文档注解但未见依赖；%s，需人工确认" % ctx.mode_note, evidence)


def check_07(ctx):
    xmlish = [p for p in ctx.log_configs
              if os.path.basename(p).lower().startswith(("logback", "log4j"))]
    dep_hits = []
    for rel, text in _pom_texts(ctx):
        for m in _LOG_FW_DEP_RE.finditer(text):
            dep_hits.append((rel, _line_of(text, m.start()), m.group(0)))
    evidence = [Evidence(ctx.rel(p), 1, "日志配置文件") for p in xmlish]
    evidence += [Evidence(r, l, "pom 依赖: %s" % t) for r, l, t in dep_hits[:ctx.max_findings]]
    if xmlish:
        return Item(7, CHECK_NAMES[7], STATUS_PASS,
                    "发现日志配置文件: %s" % ", ".join(os.path.basename(p) for p in xmlish),
                    evidence)
    if dep_hits:
        return Item(7, CHECK_NAMES[7], STATUS_MANUAL,
                    "pom 声明了日志框架但未发现 logback/log4j2 配置文件；%s，需人工确认"
                    % ctx.mode_note, evidence)
    return Item(7, CHECK_NAMES[7], STATUS_MANUAL,
                "未发现日志框架配置文件与依赖；%s，需人工确认" % ctx.mode_note, evidence)


def check_08(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        masked = J.mask_source(_read(f))
        for m in _ANN_SQL_RE.finditer(masked):
            bag.add(ctx.rel(f), _line_of(masked, m.start()),
                    "注解 SQL/script: %s" % m.group(0).strip())
    mapper_note = "发现 %d 个 Mapper XML" % len(ctx.mapper_xmls)
    if bag.total:
        if ctx.mode == "legacy":
            return Item(8, CHECK_NAMES[8], STATUS_MANUAL,
                        "发现 %d 处注解 SQL；存量适配模式，需按 0.5 数据访问约定确认"
                        % bag.total, bag.items)
        return Item(8, CHECK_NAMES[8], STATUS_FAIL,
                    "标准模式要求手写 SQL 在 XML，发现 %d 处注解 SQL" % bag.total, bag.items)
    return Item(8, CHECK_NAMES[8], STATUS_PASS, "无注解 SQL；%s" % mapper_note)


_JSON_PRODUCT_RE = re.compile(r"^3\.\d+(?:\.\d+)?-.*接口清单（前后端通用）\.md$")
_PLAN_RE = re.compile(r"^3\.\d+(?:\.\d+)?-.*技术方案\.md$")


def check_09(ctx):
    named = [p for p in ctx.docs_md if "接口清单" in os.path.basename(p)]
    compliant = [p for p in named if _JSON_PRODUCT_RE.match(os.path.basename(p))]
    if compliant:
        return Item(9, CHECK_NAMES[9], STATUS_PASS,
                    "发现 %d 个接口清单产物（3.x.2 规范命名）" % len(compliant),
                    [Evidence(ctx.rel(p), 1, "接口清单") for p in compliant[:ctx.max_findings]])
    if named:
        return Item(9, CHECK_NAMES[9], STATUS_MANUAL,
                    "发现接口清单但命名不符合 3.x.2 规范，需第 0 步矫正后确认",
                    [Evidence(ctx.rel(p), 1, "接口清单命名不符合 3.x.2：%s"
                              % os.path.basename(p)) for p in named[:ctx.max_findings]])
    if not ctx.docs_dirs:
        return Item(9, CHECK_NAMES[9], STATUS_MANUAL,
                    "docs/ 下无模块版本目录、无接口清单产物；需人工确认产物是否应生成")
    plans = [p for p in ctx.docs_md if _PLAN_RE.match(os.path.basename(p))]
    if plans:
        return Item(9, CHECK_NAMES[9], STATUS_FAIL,
                    "存在 %d 个技术方案但缺接口清单产物" % len(plans),
                    [Evidence(ctx.rel(p), 1, "缺对应 3.x.2-接口清单（前后端通用）.md")
                     for p in plans[:ctx.max_findings]])
    return Item(9, CHECK_NAMES[9], STATUS_MANUAL,
                "docs/ 有模块目录但未发现接口清单产物；需人工确认")


# ---------------------------------------------------------------------------
# 组三：SQL 与数据安全
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)


def _iter_sql_blocks(text):
    """产出 (line, block)：Markdown 围栏代码块中含 SQL 关键字的块。"""
    for m, line in _finditer_pos(_FENCE_RE, text):
        block = m.group(1)
        if re.search(r"\b(CREATE\s+TABLE|SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b",
                     block, re.I):
            yield line + 1, block


def check_10(ctx):
    plans = [p for p in ctx.docs_md if _PLAN_RE.match(os.path.basename(p))]
    if not plans:
        return Item(10, CHECK_NAMES[10], STATUS_SKIP,
                    "无 3.x.1-*技术方案*.md，方案内 SQL 无适用对象")
    bag = Bag(ctx.max_findings)
    blocks = 0
    for p in plans:
        text = _read(p)
        for line, block in _iter_sql_blocks(text):
            blocks += 1
            if re.search(r"CREATE\s+TABLE", block, re.I):
                for offset, raw in enumerate(block.splitlines()):
                    s = raw.strip()
                    if not s or s.startswith("--") or s.startswith("(") or s.startswith(")"):
                        continue
                    if re.match(r"^(PRIMARY|UNIQUE|KEY|INDEX|CONSTRAINT|FOREIGN|CHECK|FULLTEXT|SPATIAL)\b",
                                s, re.I):
                        continue
                    if re.match(r"^[`\"\w]", s) and "COMMENT" not in s.upper():
                        bag.add(ctx.rel(p), line + offset, "DDL 字段缺 COMMENT: %s" % s[:60])
            else:
                if "--" not in block:
                    bag.add(ctx.rel(p), line, "SQL 查询块缺 -- 注释")
    if blocks == 0:
        return Item(10, CHECK_NAMES[10], STATUS_SKIP, "技术方案内未发现 SQL 代码块")
    if bag.total:
        return Item(10, CHECK_NAMES[10], STATUS_FAIL,
                    "方案内 SQL 注释缺失 %d 处" % bag.total, bag.items)
    return Item(10, CHECK_NAMES[10], STATUS_PASS, "方案内 %d 个 SQL 块注释完整" % blocks)


_CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE\b.*?;", re.I | re.S)
_COL_KEYWORD_RE = re.compile(
    r"^(?:PRIMARY|UNIQUE|KEY|INDEX|CONSTRAINT|FOREIGN|CHECK|FULLTEXT|SPATIAL)\b", re.I)


def _check_ddl_block(rel, base_line, block, bag):
    open_idx = block.find("(")
    close_idx = block.rfind(")")
    if open_idx < 0 or close_idx < 0:
        return
    body = block[open_idx + 1:close_idx]
    head_text = block[:open_idx]
    head_offset = block[:open_idx].count("\n")
    for offset, raw in enumerate(body.splitlines()):
        s = raw.strip().rstrip(",").strip()
        if not s or s.startswith("--"):
            continue
        if _COL_KEYWORD_RE.match(s):
            continue
        if re.match(r"^[`\"\w]", s) and "COMMENT" not in s.upper():
            bag.add(rel, base_line + head_offset + offset + 1,
                    "字段缺 COMMENT: %s" % s[:70])
    tail = block[close_idx:]
    if not re.search(r"\bCOMMENT\b", tail, re.I):
        bag.add(rel, base_line + block[:close_idx].count("\n"),
                "表级缺 COMMENT（) 之后）")


def check_11(ctx):
    bag = Bag(ctx.max_findings)
    sources = list(ctx.sql_files) + list(ctx.docs_md)
    found = 0
    for p in sources:
        text = _read(p)
        if not re.search(r"CREATE\s+TABLE", text, re.I):
            continue
        for m, line in _finditer_pos(_CREATE_TABLE_RE, text):
            found += 1
            _check_ddl_block(ctx.rel(p), line, m.group(0), bag)
    if found == 0:
        return Item(11, CHECK_NAMES[11], STATUS_SKIP, "未发现 CREATE TABLE 语句")
    if bag.total:
        return Item(11, CHECK_NAMES[11], STATUS_FAIL,
                    "%d 张表 DDL 注释缺失 %d 处" % (found, bag.total), bag.items)
    return Item(11, CHECK_NAMES[11], STATUS_PASS, "%d 张表 DDL 字段均带 COMMENT" % found)


_STR_CONCAT_SQL_RE = re.compile(r"\"\s*(?:select|insert|update|delete)\b", re.I)


def check_12(ctx):
    bag = Bag(ctx.max_findings)
    manual = Bag(ctx.max_findings)
    for p in ctx.mapper_xmls:
        text = _read(p)
        for m in re.finditer(r"\$\{([^}]*)\}", text):
            expr = m.group(1)
            if _is_wrapper_sql(expr):
                manual.add(ctx.rel(p), _line_of(text, m.start()),
                           "MyBatis-Plus 包装器 ${%s}（框架生成，确认无用户输入拼入）" % expr.strip())
            else:
                bag.add(ctx.rel(p), _line_of(text, m.start()),
                        "XML ${} 拼接值: ${%s}" % expr.strip())
    for f in ctx.java_files:
        for lineno, orig, _masked in J.iter_code_lines(f):
            if _STR_CONCAT_SQL_RE.search(orig) and "+" in orig:
                bag.add(ctx.rel(f), lineno, "Java 字符串拼接 SQL")
            if re.search(r"\.(apply|last)\s*\(", orig):
                manual.add(ctx.rel(f), lineno, "MyBatis-Plus apply()/last() 需确认入参")
    if bag.total:
        return Item(12, CHECK_NAMES[12], STATUS_FAIL,
                    "发现 SQL 注入风险 %d 处" % bag.total, bag.items)
    if manual.total:
        return Item(12, CHECK_NAMES[12], STATUS_MANUAL,
                    "%d 处需人工确认（包装器/apply 入参）" % manual.total, manual.items)
    return Item(12, CHECK_NAMES[12], STATUS_PASS, "无 ${} 拼接、无字符串拼接 SQL")


_XML_STMT_RE = re.compile(r"<(select|insert|update|delete)\b[^>]*>(.*?)</\1>", re.I | re.S)


def check_13(ctx):
    bag = Bag(ctx.max_findings)
    checked = 0
    for p in ctx.mapper_xmls:
        text = _clean_xml(_read(p))
        for m, line in _finditer_pos(_XML_STMT_RE, text):
            tag = m.group(1).lower()
            body = m.group(2)
            is_write = tag in ("update", "delete")
            if not is_write:
                stripped = body.strip()
                is_write = bool(re.match(r"^(UPDATE|DELETE)\b", stripped, re.I))
            if not is_write:
                continue
            checked += 1
            if not re.search(r"\bWHERE\b", body, re.I):
                bag.add(ctx.rel(p), line, "<%s> 无 WHERE（id=%s）"
                        % (tag, _extract_id(m.group(0))))
    if checked == 0:
        return Item(13, CHECK_NAMES[13], STATUS_PASS, "Mapper XML 中无 UPDATE/DELETE 语句")
    if bag.total:
        return Item(13, CHECK_NAMES[13], STATUS_FAIL,
                    "%d/%d 条 UPDATE/DELETE 缺 WHERE" % (bag.total, checked), bag.items)
    return Item(13, CHECK_NAMES[13], STATUS_PASS, "%d 条 UPDATE/DELETE 均带 WHERE" % checked)


def _extract_id(stmt_head):
    m = re.search(r'id\s*=\s*"([^"]+)"', stmt_head)
    return m.group(1) if m else "?"


# ---------------------------------------------------------------------------
# 组四：事务与代码质量
# ---------------------------------------------------------------------------

_TRANSACTIONAL_RE = re.compile(r"@Transactional\b")


def _annotation_span(masked, start):
    """从注解 '@' 位置解析出完整的注解文本（平衡括号），返回 (text, end_pos)。"""
    i = start
    n = len(masked)
    while i < n and (masked[i].isalnum() or masked[i] in "@_.$"):
        i += 1
    if i < n and masked[i] == "(":
        depth = 0
        while i < n:
            if masked[i] == "(":
                depth += 1
            elif masked[i] == ")":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
    return masked[start:i], i


def check_14(ctx):
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        masked = J.mask_source(_read(f))
        for m in _TRANSACTIONAL_RE.finditer(masked):
            total += 1
            text, _end = _annotation_span(masked, m.start())
            if "rollbackFor" not in text:
                bag.add(ctx.rel(f), _line_of(masked, m.start()),
                        "@Transactional 缺 rollbackFor")
    if total == 0:
        return Item(14, CHECK_NAMES[14], STATUS_PASS, "未发现 @Transactional")
    if bag.total:
        return Item(14, CHECK_NAMES[14], STATUS_FAIL,
                    "%d/%d 个 @Transactional 缺 rollbackFor" % (bag.total, total), bag.items)
    return Item(14, CHECK_NAMES[14], STATUS_PASS, "%d 个 @Transactional 均带 rollbackFor" % total)


def check_15(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        masked = J.mask_source(_read(f))
        for m in re.finditer(r"@Autowired\b", masked):
            bag.add(ctx.rel(f), _line_of(masked, m.start()), "字段/属性 @Autowired 注入")
    if bag.total:
        status = STATUS_FAIL if ctx.mode == "standard" else STATUS_MANUAL
        return Item(15, CHECK_NAMES[15], status,
                    "%d 处 @Autowired 注入（应改构造器注入）" % bag.total, bag.items)
    return Item(15, CHECK_NAMES[15], STATUS_PASS, "无 @Autowired，构造器注入")


def check_16(ctx):
    bag = Bag(ctx.max_findings)
    controllers = ctx.controller_classes()
    for ci in controllers:
        masked = J.mask_source(_read(ci.path))
        for m in re.finditer(r"\bMapper\b", masked):
            bag.add(ctx.rel(ci.path), _line_of(masked, m.start()), "Controller 引用 Mapper")
            break
        for m in _TRANSACTIONAL_RE.finditer(masked):
            bag.add(ctx.rel(ci.path), _line_of(masked, m.start()), "Controller 含 @Transactional")
            break
    if not controllers:
        return Item(16, CHECK_NAMES[16], STATUS_PASS, "未发现 Controller")
    if bag.total:
        return Item(16, CHECK_NAMES[16], STATUS_FAIL,
                    "%d 个 Controller 越界（引用 Mapper / 含事务）" % bag.total, bag.items)
    return Item(16, CHECK_NAMES[16], STATUS_PASS, "%d 个 Controller 分层边界正常" % len(controllers))


def check_17(ctx):
    bag = Bag(ctx.max_findings)
    controllers = ctx.controller_classes()
    for ci in controllers:
        masked = J.mask_source(_read(ci.path))
        for m in re.finditer(r"@TableName\b", masked):
            bag.add(ctx.rel(ci.path), _line_of(masked, m.start()),
                    "Controller 直接引用 @TableName Entity")
        for m in re.finditer(r"\b\w*Entity\b", masked):
            if m.group(0) == "Entity":
                continue
            bag.add(ctx.rel(ci.path), _line_of(masked, m.start()),
                    "Controller 引用 Entity 类型: %s" % m.group(0))
    if not controllers:
        return Item(17, CHECK_NAMES[17], STATUS_PASS, "未发现 Controller")
    if bag.total:
        return Item(17, CHECK_NAMES[17], STATUS_FAIL,
                    "Controller 暴露 Entity %d 处" % bag.total, bag.items)
    return Item(17, CHECK_NAMES[17], STATUS_PASS, "Controller 未暴露 Entity")


def check_18(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        masked = J.mask_source(_read(f))
        for m in re.finditer(r"throw\s+new\s+RuntimeException\b", masked):
            bag.add(ctx.rel(f), _line_of(masked, m.start()), "裸抛 RuntimeException")
        for m in re.finditer(r"catch\s*\([^)]*\)\s*\{\s*\}", masked):
            bag.add(ctx.rel(f), _line_of(masked, m.start()), "空 catch 吞异常")
    if bag.total:
        return Item(18, CHECK_NAMES[18], STATUS_FAIL,
                    "异常处理问题 %d 处" % bag.total, bag.items)
    return Item(18, CHECK_NAMES[18], STATUS_PASS, "无裸 RuntimeException、无空 catch")


def check_19(ctx):
    bag = Bag(ctx.max_findings)
    single_catch = re.compile(r"catch\s*\(\s*[\w.<>\[\],\s?]+\s+([A-Za-z])\s*\)")
    single_class = re.compile(r"\b(?:class|interface|enum|record)\s+([A-Za-z])\b")
    for f in ctx.java_files:
        masked = J.mask_source(_read(f))
        for m in single_catch.finditer(masked):
            bag.add(ctx.rel(f), _line_of(masked, m.start()),
                    "catch 参数单字母: %s" % m.group(1))
        for m in single_class.finditer(masked):
            bag.add(ctx.rel(f), _line_of(masked, m.start()),
                    "单字母类型名: %s" % m.group(1))
    if bag.total:
        return Item(19, CHECK_NAMES[19], STATUS_FAIL,
                    "命名问题 %d 处" % bag.total, bag.items)
    return Item(19, CHECK_NAMES[19], STATUS_PASS, "无单字母异常参数/类型名")


_WRAPPER_RE = re.compile(r"\b(?:Response|R|Result|PageResult|TableDataInfo|AjaxResult)\s*<")
_MAP_RETURN_RE = re.compile(r"\b(?:Map|HashMap|LinkedHashMap|TreeMap)\s*<")


def check_20(ctx):
    bag = Bag(ctx.max_findings)
    wrapper_found = False
    controllers = ctx.controller_classes()
    for ci in controllers:
        masked = J.mask_source(_read(ci.path))
        if _WRAPPER_RE.search(masked):
            wrapper_found = True
        for m in ci.methods:
            if _MAP_RETURN_RE.search(m.return_type or ""):
                bag.add(ctx.rel(ci.path), m.decl_line,
                        "方法 %s 裸返回 Map" % m.name)
    if not controllers:
        return Item(20, CHECK_NAMES[20], STATUS_MANUAL, "未发现 Controller，无法判定返回体")
    if bag.total:
        return Item(20, CHECK_NAMES[20], STATUS_FAIL,
                    "Controller 裸返回 Map %d 处" % bag.total, bag.items)
    if wrapper_found:
        return Item(20, CHECK_NAMES[20], STATUS_PASS, "Controller 使用统一返回体包装")
    return Item(20, CHECK_NAMES[20], STATUS_MANUAL,
                "未发现 Map 裸返回，也未发现统一返回体；%s，需人工确认" % ctx.mode_note)


_CRYPTO_RE = re.compile(
    r"(?:DigestUtils\.\w+|SecureUtil\.md5|MessageDigest\.getInstance|\bmd5\s*\(|\bsha1\s*\()", re.I)
_PWD_HINT_RE = re.compile(r"password|passwd|pwd|密码|凭证|secret", re.I)


def check_21(ctx):
    bag = Bag(ctx.max_findings)
    manual = Bag(ctx.max_findings)
    for f in ctx.java_files:
        for lineno, orig, _masked in J.iter_code_lines(f):
            if not _CRYPTO_RE.search(orig):
                continue
            if _PWD_HINT_RE.search(orig):
                bag.add(ctx.rel(f), lineno, "MD5/SHA1 疑似用于密码: %s" % orig.strip()[:80])
            else:
                manual.add(ctx.rel(f), lineno, "MD5/SHA1 命中（非密码上下文，需确认）")
    if bag.total:
        return Item(21, CHECK_NAMES[21], STATUS_FAIL,
                    "MD5/SHA1 用于密码 %d 处" % bag.total, bag.items)
    if manual.total:
        return Item(21, CHECK_NAMES[21], STATUS_MANUAL,
                    "%d 处 MD5/SHA1 命中但非密码上下文，需人工确认" % manual.total, manual.items)
    return Item(21, CHECK_NAMES[21], STATUS_PASS, "未发现 MD5/SHA1/DigestUtils")


_PAGE_SIZE_RE = re.compile(r"(?:private|protected|public)\s+[\w<>,.\s]+\s+(pageSize)\s*[;=]")
_LIMIT_ANN_RE = re.compile(r"@(?:Max|Min|Size|Range|DecimalMax|DecimalMin|Digits|Positive|PositiveOrZero)\b")


def check_22(ctx):
    bag = Bag(ctx.max_findings)
    found = 0
    for f in ctx.java_files:
        lines = J.read_lines(f)
        for i, line in enumerate(lines):
            if not _PAGE_SIZE_RE.search(line):
                continue
            found += 1
            window = "\n".join(lines[max(0, i - 6):i + 1])
            if not _LIMIT_ANN_RE.search(window):
                bag.add(ctx.rel(f), i + 1, "pageSize 字段缺上限校验(@Max 等)")
    if found == 0:
        return Item(22, CHECK_NAMES[22], STATUS_SKIP,
                    "未发现 pageSize 字段声明（可能走基类/框架分页），本项不适用")
    if bag.total:
        return Item(22, CHECK_NAMES[22], STATUS_FAIL,
                    "%d/%d 个 pageSize 字段缺上限校验" % (bag.total, found), bag.items)
    return Item(22, CHECK_NAMES[22], STATUS_PASS, "%d 个 pageSize 字段有上限校验" % found)


_GENERIC_PREFIX = r"(?:参数|数据|输入|请求|字段|内容|信息)"
_GENERIC_CONCL = r"(?:不合法|错误|非法|无效|有误|不正确|格式不对)"
_GENERIC_MSG_RE = re.compile(r"^" + _GENERIC_PREFIX + r"*" + _GENERIC_CONCL + r"+$")
_MSG_RE = re.compile(r'message\s*=\s*"([^"]*)"')


def check_23(ctx):
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        text = _read(f)
        for m, line in _finditer_pos(_MSG_RE, text):
            total += 1
            msg = m.group(1)
            normalized = re.sub(r"[\s，。、,.;:：!！~\-]+", "", msg)
            if _GENERIC_MSG_RE.match(normalized):
                bag.add(ctx.rel(f), line, '笼统校验文案: message = "%s"' % msg)
    if total == 0:
        return Item(23, CHECK_NAMES[23], STATUS_PASS, "未发现校验 message 文案")
    if bag.total:
        return Item(23, CHECK_NAMES[23], STATUS_FAIL,
                    "%d/%d 条校验 message 笼统（缺字段名/具体原因）" % (bag.total, total), bag.items)
    return Item(23, CHECK_NAMES[23], STATUS_PASS, "%d 条校验 message 均具体" % total)


# ---------------------------------------------------------------------------
# 组五：场景化 + 其余
# ---------------------------------------------------------------------------

def _scan_pattern(ctx, regex):
    hits = []
    for f in ctx.java_files:
        masked = J.mask_source(_read(f))
        for m in regex.finditer(masked):
            hits.append((f, _line_of(masked, m.start()), m.group(0)))
    return hits


_SCHEDULED_RE = re.compile(r"@Scheduled\b")
_QUARTZ_JOB_RE = re.compile(r"\bimplements\s+[\w.,\s]*\bJob\b")
_LOCK_RE = re.compile(r"lock|Redis|SETNX|setIfAbsent|状态位|reentrant|tryLock", re.I)
_LIMIT_RE = re.compile(r"\bLIMIT\b", re.I)


def check_24(ctx):
    hits = _scan_pattern(ctx, _SCHEDULED_RE)
    if not hits:
        hits = _scan_pattern(ctx, _QUARTZ_JOB_RE)
    if not hits:
        return Item(24, CHECK_NAMES[24], STATUS_SKIP, "无 @Scheduled / Quartz Job")
    bag = Bag(ctx.max_findings)
    files = sorted(set(h[0] for h in hits))
    for f in files:
        text = _read(f)
        has_lock = bool(_LOCK_RE.search(text))
        has_limit = bool(_LIMIT_RE.search(text))
        bag.add(ctx.rel(f), 1, "Job 类；检测到锁/状态位=%s，LIMIT=%s（需人工核对）"
                % (has_lock, has_limit))
    return Item(24, CHECK_NAMES[24], STATUS_MANUAL,
                "%d 个 Job 类需人工核对防重入与批处理 LIMIT" % len(files), bag.items)


_RABBIT_RE = re.compile(r"@RabbitListener\b")
_KAFKA_RE = re.compile(r"@KafkaListener\b")


def check_25(ctx):
    hits = _scan_pattern(ctx, _RABBIT_RE) + _scan_pattern(ctx, _KAFKA_RE)
    if not hits:
        return Item(25, CHECK_NAMES[25], STATUS_SKIP, "无 @RabbitListener/@KafkaListener")
    bag = Bag(ctx.max_findings)
    files = sorted(set(h[0] for h in hits))
    for f in files:
        text = _read(f)
        has_deadletter = bool(re.search(r"dead.?letter|死信|DLX|Retry|retry", text, re.I))
        bag.add(ctx.rel(f), 1, "Listener 类；检测到重试/死信线索=%s（需人工核对）" % has_deadletter)
    return Item(25, CHECK_NAMES[25], STATUS_MANUAL,
                "%d 个 Listener 类需人工核对幂等与死信" % len(files), bag.items)


_MULTIPART_RE = re.compile(r"\bMultipartFile\b")


def check_26(ctx):
    hits = _scan_pattern(ctx, _MULTIPART_RE)
    if not hits:
        return Item(26, CHECK_NAMES[26], STATUS_SKIP, "无 MultipartFile 上传")
    bag = Bag(ctx.max_findings)
    files = sorted(set(h[0] for h in hits))
    for f in files:
        text = _read(f)
        whitelist = bool(re.search(r"jpg|jpeg|png|gif|白名单|allowedExt|allowedType", text, re.I))
        uuid = bool(re.search(r"UUID|uuid|nanoTime|currentTimeMillis", text))
        size = bool(re.search(r"MaxUploadSize|getSize\(\)|maxSize|maxFileSize", text))
        bag.add(ctx.rel(f), 1,
                "上传点：扩展名白名单=%s，UUID 重命名=%s，大小限制=%s（需人工核对）"
                % (whitelist, uuid, size))
    return Item(26, CHECK_NAMES[26], STATUS_MANUAL,
                "%d 个文件上传点需人工核对安全措施" % len(files), bag.items)


_WRITE_MAPPING_RE = re.compile(r"@(PostMapping|PutMapping)\b")


def check_27(ctx):
    hits = _scan_pattern(ctx, _WRITE_MAPPING_RE)
    if not hits:
        return Item(27, CHECK_NAMES[27], STATUS_SKIP, "无 POST/PUT 写接口")
    bag = Bag(ctx.max_findings)
    for f, line, _tok in hits:
        bag.add(ctx.rel(f), line, "写接口需核对幂等（唯一键/令牌/Redis SETNX）")
    return Item(27, CHECK_NAMES[27], STATUS_MANUAL,
                "%d 个写接口需人工核对幂等方案" % len(hits), bag.items)


_SENSITIVE_LOG_RE = re.compile(
    r"\b(?:log|LOG|logger|LOGGER)\.(?:debug|info|warn|error)\s*\([^;]*?"
    r"(?:password|passwd|pwd|token|secret|accessKey|apiKey)", re.I)
_MASK_RE = re.compile(r"mask|hide|desensit|\*\*\*|StrUtil\.hide|脱敏", re.I)


def check_28(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        for lineno, orig, _masked in J.iter_code_lines(f):
            if _SENSITIVE_LOG_RE.search(orig):
                masked_ok = bool(_MASK_RE.search(orig))
                bag.add(ctx.rel(f), lineno,
                        "日志含敏感字段%s: %s"
                        % ("（有脱敏线索）" if masked_ok else "（未见脱敏）", orig.strip()[:80]))
    if bag.total:
        return Item(28, CHECK_NAMES[28], STATUS_FAIL,
                    "%d 处日志疑含敏感信息" % bag.total, bag.items)
    return Item(28, CHECK_NAMES[28], STATUS_PASS, "日志未发现明文敏感字段")


_COLLECTION_DECL_RE = re.compile(
    r"\b(List|Set|Map|Collection|ArrayList|HashSet|HashMap|LinkedList|TreeMap)\s*<[^;{}()]*?>\s+([A-Za-z_$][\w$]*)\b")
_BAD_COLLECTION_NAMES = {
    "records", "codes", "values", "list", "map", "set", "data", "datas",
    "items", "item", "result", "results", "array", "arrays", "collection",
    "collections", "elements",
}


def check_29(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        masked = J.mask_source(_read(f))
        for m in _COLLECTION_DECL_RE.finditer(masked):
            name = m.group(2)
            low = name.lower()
            if low in _BAD_COLLECTION_NAMES and not name.endswith(("List", "Set", "Map", "Collection")):
                bag.add(ctx.rel(f), _line_of(masked, m.start()),
                        "集合变量命名不规范: %s（应 xxxList/xxxSet/xxxMap）" % name)
    if bag.total:
        return Item(29, CHECK_NAMES[29], STATUS_FAIL,
                    "集合命名问题 %d 处" % bag.total, bag.items)
    return Item(29, CHECK_NAMES[29], STATUS_PASS, "集合命名符合 xxxList/xxxSet/xxxMap")


_MAGIC_STR_RE = re.compile(r'"([A-Za-z0-9_.:/-]{3,40})"')


def check_30(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        rel = ctx.rel(f)
        if "/constant" in rel.replace(os.sep, "/").lower() or "constants" in os.path.basename(f).lower():
            continue
        text = _read(f)
        for m, line in _finditer_pos(_MAGIC_STR_RE, text):
            val = m.group(1)
            if re.search(r"redis|:\w|KEY|key|CACHE|cache|prefix|PREFIX", val):
                bag.add(rel, line, "疑似缓存 key / 魔法值: %s" % val)
    note = "魔法值/缓存 key 为人工判断项，已列出候选（启发式）"
    if bag.total:
        note += "；候选 %d 处" % bag.total
    else:
        note += "；未发现缓存 key 候选"
    return Item(30, CHECK_NAMES[30], STATUS_MANUAL, note, bag.items)


_DUP_WS_RE = re.compile(r"\s+")


def check_31(ctx):
    groups = defaultdict(list)
    for ci in ctx.classes():
        for m in ci.methods:
            if not m.has_body() or m.code_lines() < 4:
                continue
            body = _DUP_WS_RE.sub("", m.body_text_masked())
            if len(body) < 40:
                continue
            groups[body].append((ci, m))
    dups = [(k, v) for k, v in groups.items() if len(v) > 1]
    if not dups:
        return Item(31, CHECK_NAMES[31], STATUS_PASS, "未发现重复方法体")
    bag = Bag(ctx.max_findings)
    for _key, members in dups:
        for ci, m in members:
            bag.add(ctx.rel(ci.path), m.decl_line, "重复方法体: %s.%s" % (ci.name, m.name))
    return Item(31, CHECK_NAMES[31], STATUS_MANUAL,
                "发现 %d 组重复方法体，需人工确认抽公共组件" % len(dups), bag.items)


_LOG_LINE_RE = re.compile(r"\b(?:log|LOG|logger|LOGGER)\.(?:debug|info|warn|error)\s*\(([^;]*)\)\s*;")
_CALL_IN_ARG_RE = re.compile(r"\.\s*\w+\s*\(")


def check_32(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        for lineno, orig, _masked in J.iter_code_lines(f):
            m = _LOG_LINE_RE.search(orig)
            if not m:
                continue
            args = m.group(1)
            if "{}" not in args:
                continue
            comma = args.find(",")
            call_zone = args[comma + 1:] if comma >= 0 else ""
            if _CALL_IN_ARG_RE.search(call_zone):
                bag.add(ctx.rel(f), lineno,
                        "日志占位符参数含方法调用（eager 求值可能 NPE，需人工核对判空）")
    if bag.total:
        return Item(32, CHECK_NAMES[32], STATUS_MANUAL,
                    "%d 处日志参数含方法调用，需人工核对 NPE" % bag.total, bag.items)
    return Item(32, CHECK_NAMES[32], STATUS_PASS, "未发现日志占位符参数含方法调用")


_TABLENAME_RE = re.compile(r'@TableName\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')


def check_33(ctx):
    table_map = defaultdict(list)
    for f in ctx.java_files:
        text = _read(f)
        for m, line in _finditer_pos(_TABLENAME_RE, text):
            table_map[m.group(1)].append((f, line))
    dups = {t: locs for t, locs in table_map.items() if len(locs) > 1}
    if not dups:
        return Item(33, CHECK_NAMES[33], STATUS_PASS,
                    "共 %d 张表，无同表重复映射" % len(table_map))
    bag = Bag(ctx.max_findings)
    for table, locs in dups.items():
        for f, line in locs:
            bag.add(ctx.rel(f), line, "同表重复映射: %s" % table)
    return Item(33, CHECK_NAMES[33], STATUS_FAIL,
                "%d 张表存在重复 @TableName 映射" % len(dups), bag.items)


# ---------------------------------------------------------------------------
# 运行入口
# ---------------------------------------------------------------------------

CHECK_FUNCS = {
    1: check_01, 2: check_02, 3: check_03, 4: check_04, 5: check_05,
    6: check_06, 7: check_07, 8: check_08, 9: check_09, 10: check_10,
    11: check_11, 12: check_12, 13: check_13, 14: check_14, 15: check_15,
    16: check_16, 17: check_17, 18: check_18, 19: check_19, 20: check_20,
    21: check_21, 22: check_22, 23: check_23, 24: check_24, 25: check_25,
    26: check_26, 27: check_27, 28: check_28, 29: check_29, 30: check_30,
    31: check_31, 32: check_32, 33: check_33,
}


def run_all(ctx, only=None, skip=None):
    """执行核对，返回 (items, summary)。

    only / skip 为 id 集合；only 非空时只跑这些 id；skip 中的 id 被跳过并计为 skip。
    """
    ids = sorted(CHECK_NAMES.keys())
    items = []
    summary = {STATUS_PASS: 0, STATUS_FAIL: 0, STATUS_WARN: 0,
               STATUS_MANUAL: 0, STATUS_SKIP: 0}
    for cid in ids:
        name = CHECK_NAMES[cid]
        if only and cid not in only:
            continue
        if skip and cid in skip:
            item = Item(cid, name, STATUS_SKIP, "由 --skip 跳过")
        else:
            func = CHECK_FUNCS[cid]
            try:
                item = func(ctx)
            except Exception as exc:  # pragma: no cover - 防御性
                item = Item(cid, name, STATUS_MANUAL,
                            "核对执行异常，降级为需人工: %s" % exc)
        if item.name != name:
            item.name = name
        summary[item.status] = summary.get(item.status, 0) + 1
        items.append(item)
    return items, summary
