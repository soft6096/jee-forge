#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-standards 的 57 项核对判定逻辑（纯标准库实现）。

严格对照 SKILL.md「检查项清单」实现。可机械判定的项给出 pass/fail；语义/需人眼判断的项
一律标记 manual/warn 并附证据，绝不假装 pass。扫描范围与模式由 :class:`Context` 承载。

来源说明：本模块为原创 Python 实现。#34~#57 的格式/命名核对项仅在
**规则口径**上对齐 Checkstyle 10.x（LGPL-2.1），未复制其任何代码、文档或发行物；其余核对项
出自本项目规范 skill 与 Java 社区通用工程惯例。参考源对照见仓库根 COPYRIGHT.md §2。

对外主要接口：
- :data:`CHECK_NAMES`：id → 名称（1..57）
- :func:`detect_mode`：判定 standard / legacy
- :func:`detect_renames`：第 0 步产物命名矫正（只检测，不落盘）
- :func:`run_all`：按 --only/--skip 执行全部核对，返回报告 dict
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict

import cs_java as J

PROGRESS_QUIET = False

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
    34: "行尾空白与 Tab",
    35: "行宽超限",
    36: "连续空行",
    37: "import 卫生",
    38: "空格（启发式）",
    39: "命名规范（大小写/形式）",
    40: "类与文件结构",
    41: "书写卫生",
    42: "字符串比较",
    43: "遗留标记",
    44: "变量命名（启发式）",
    45: "缩进一致性",
    46: "import 顺序",
    47: "方法长度",
    48: "方法参数个数",
    49: "equals/hashCode 成对",
    50: "catch 形参命名",
    51: "静态变量命名",
    52: "逗号分号后空格",
    53: "成员之间空行",
    54: "一行一声明",
    55: "一行一语句",
    56: "package/import 不换行",
    57: "花括号必写与位置",
}

# ---------------------------------------------------------------------------
# 核对项判据摘要（id -> 一句话判据）
# ---------------------------------------------------------------------------
# WHY 单独维护判据摘要而不是让模型回读 references/checklist.md：
# 57 项完整清单约 19KB，模型对 manual/warn 项判定时若回读整篇，等于把省下的 token 又付回去。
# 判读顺序：脚本输出 status=manual/warn → 用本表的 judgment 判 → 仍不足才查 checklist.md 对应项。
# 维护约束：改 references/checklist.md 的「判定标准」必须同步改这里（反之亦然），
# 否则模型会按旧判据判定（属于"两处不一致"类缺陷，见 docs/skill-maintenance-checklist.md）。
CHECK_GUIDE = {
    1: "目标类所有方法（含 private 抽取方法）有 Javadoc，写功能与 @param/@return 业务含义；豁免 @Override、getter/setter 单行透传、<2 行短方法",
    2: "目标类每个业务方法体内 ≥1 条 INFO/WARN/ERROR（debug 不算）；≥10 行逻辑无日志、或只在开头 1 条=半覆盖 → ❌",
    3: "方法内每个业务段有编号注释（覆盖到最后一段），复杂逻辑有 // WHY:；≥10 行连续逻辑零注释 → ❌",
    4: "注释写业务含义，不逐行翻译式复述代码",
    5: "目标类全类 @Slf4j，无 System.out，无散落 Logger 混用",
    6: "有依赖或注解即 ✅；两者都无时看约束文件：写明选型 → ❌，未写明选型/无约束 → ✅（不确定当正常）",
    7: "有 logback/log4j2 配置文件 → ✅；仅 pom 声明无配置 → manual；都无时口径同 #6",
    8: "标准模式：无注解 SQL、手写 SQL 全在 XML 且 namespace 一致；老项目按 0.5 数据访问约定判",
    9: "每个 Controller 功能项已生成 3.x.2 接口清单，URL+方法+入参/出参（成功/失败）与方案一致",
    10: "方案内所有 SQL 带注释：DDL 每字段 COMMENT，查询/DML 每条 -- 用途注释（含归属 Mapper 与关键条件）",
    11: "CREATE TABLE 每个字段有 COMMENT + 表级 COMMENT，无裸字段",
    12: "XML 无 ${} 拼接值、Java 无字符串拼 SQL、无 apply()/last() 传用户输入",
    13: "所有 UPDATE/DELETE 必须带 WHERE，无 WHERE → ❌",
    14: "每个 @Transactional 都带 rollbackFor = Exception.class",
    15: "无字段注入（@Autowired），统一 @RequiredArgsConstructor + final；老项目按老约定",
    16: "Controller 不注入 Mapper、不写业务逻辑/SQL/事务",
    17: "接口出入参用 DTO/VO，不暴露 Entity",
    18: "无裸 RuntimeException，无空 catch 吞异常",
    19: "无单字母类名、无泛称变量名（异常参数命名见 #50）",
    20: "Controller 返回 Response<T>/PageResult<T>（老项目按老返回体），无 Map 裸返回",
    21: "无 MD5/SHA1 存密码，用 BCrypt 等慢哈希",
    22: "分页入参 pageSize 有 @Max 或上限校验",
    23: "校验注解 message 含业务字段名 + 具体原因；仅由笼统词（参数/数据/不合法/错误…）构成 → ❌",
    24: "有分布式锁或状态位防重入、批处理带 LIMIT、无长事务（有 @Scheduled 才核）",
    25: "消费幂等、重试有上限 + 死信队列、无 catch 静默（有监听注解才核）",
    26: "扩展名 + MIME 双白名单、UUID 重命名、大小限制（有 MultipartFile 才核）",
    27: "写接口有幂等方案（唯一键/令牌/Redis SETNX），幂等键与业务同事务；需人工抽查",
    28: "日志/异常/响应不含密码、token、secret 明文",
    29: "集合字段用 xxxList / xxxSet / xxxMap 后缀",
    30: "无裸魔法值，缓存 key 集中常量定义",
    31: "无 ≥2 处方法体完全相同（去空白后逐字符相等）→ 应抽公共组件",
    32: "日志参数不得含可能 NPE 的调用：.get(x).xxx()、判空前的 getter、list.get(0)、map.get(k).xxx()",
    33: "一张表只允许一个 @TableName 映射；同一表名出现 >1 次 → ❌",
    34: "无行尾空白字符，缩进无 Tab（4 空格）",
    35: "单行 ≤120 字符（package / import / URL 行豁免）",
    36: "无连续 2 行以上空行",
    37: "无通配符 import、无 sun.* / com.sun.*、无未使用 import",
    38: "运算符与关键字两侧有空格（启发式，需人工确认）",
    39: "包名全小写；类/接口/枚举 UpperCamelCase 非单字母；方法 lowerCamelCase；常量 UPPER_SNAKE（log 豁免）；缩写连续大写 ≤3",
    40: "必须声明 package；一文件一顶层类；顶层类有 Javadoc",
    41: "修饰符顺序正确无冗余；数组写 int[] a；long 用大写 L；无 printStackTrace()",
    42: "字符串用 equals 比较、常量前置；枚举/常量比较（==）不计入（启发式）",
    43: "无 TODO / FIXME，唯一例外 // TODO(收敛)",
    44: "成员/局部/参数/lambda 变量 lowerCamelCase；含 _ 或首字母大写 → ❌",
    45: "语句起始行缩进为 4 空格倍数（续行/注解对齐/数组初始化按候选人工判，只报不足）",
    46: "分组顺序 第三方 → javax → java/jdk/sun，组内字典序；static import 不参与",
    47: "方法体代码行 ≤100（注释/空行/纯大括号行不计）",
    48: "形参个数 ≤7（枚举常量不算方法）",
    49: "手写 equals 必须同时手写 hashCode；豁免 record 与 Lombok @Data/@Value",
    50: "catch 形参为 e/t/ex/_，或小写开头且长度 ≥3 的纯字母名",
    51: "非 final 的 static 字段须 lowerCamelCase（static final 由 #39 核对）",
    52: ", ; 之后须有空白（行尾除外）；类型转换 ) 与控制关键字后须有空白",
    53: "方法/构造器之前须有空行；豁免类型体首个成员、上一成员是字段",
    54: "一条声明语句内不得定义多个变量",
    55: "同一行不得出现多条语句（for 头部分号、do-while 除外）",
    56: "package 与 import 语句须单行，不得被换行拆断",
    57: "if/for/while/do/else 必须带 {}；{ 在行尾且其后换行；} 与 else/catch/finally 同行",
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


def _merge_hints(bag, hint_bag, limit):
    """主袋（可靠判定）证据 + 启发式子袋证据合并，供 fail 时一并展示。

    WHY: 子袋若在 fail 时被整体丢弃，「有检测但不显示」在效果上等价于漏报——静态检查侧
    会报出的问题在这边看不到。合并后可靠证据在前、候选提示随后（受同一上限约束）；
    候选条目的 detail 自带「疑似/候选」字样，不会与可靠判定混淆。
    """
    items = list(bag.items)
    for ev in hint_bag.items:
        if len(items) >= limit:
            break
        items.append(ev)
    return items


# 集中存放资源文件的常见目录（项目根直属）：这些目录下的文件按「模块关键词」纳入范围
_CENTRAL_RESOURCE_DIRS = frozenset(
    ("sql", "db", "ddl", "script", "scripts", "doc", "docs", "design", "deploy"))


def _module_keywords(scope_path):
    """由扫描路径推出模块关键词，用于识别按模块命名的集中资源文件。

    ``xwd-modules/xwd-mall-center`` → ``{xwd-mall-center, mall-center}``。
    仅保留长度 ≥4 的关键词，避免过泛匹配（如 ``xwd`` 这类前缀被排除）。
    """
    base = os.path.basename(os.path.abspath(scope_path))
    if not base:
        return ()
    keys = {base}
    if "-" in base:
        parts = base.split("-")
        if parts[0] in ("xwd", "tms", "sys", "app"):
            keys.add("-".join(parts[1:]))
        keys.add(parts[0])
    return tuple(k for k in keys if len(k) >= 4)


def _is_central_named_resource(path, project, keys):
    """判断是否「集中目录下、文件名含模块关键词」的资源文件（如 ``sql/0930/0831-mall-center-init.sql``）。"""
    if not keys:
        return False
    rel = os.path.relpath(path, project).replace("\\", "/")
    if rel.split("/", 1)[0].lower() not in _CENTRAL_RESOURCE_DIRS:
        return False
    name = os.path.basename(rel).lower()
    return any(k.lower() in name for k in keys)


class Context(object):
    """一次扫描的上下文：范围、模式、文件集合与解析缓存。"""

    def __init__(self, project, java_files, scope, scope_path, mode, mode_note,
                 constraint_path, changed_set, max_findings=20,
                 resources_scope="auto"):
        self.project = os.path.abspath(project)
        self.java_files = list(java_files)
        self.scope = scope
        self.scope_path = scope_path
        self.mode = mode
        self.mode_note = mode_note
        self.constraint_path = constraint_path
        self.changed = set(changed_set or ())
        self.max_findings = max_findings
        self.resources_scope = resources_scope
        # 资源类文件（pom / 日志配置 / Mapper XML / SQL / 文档）同样受 --path 收敛，
        # 否则扫某模块时会带出同仓库其它子项目、参考 SQL 的大量无关问题。
        self.poms = self._scope_resources(J.find_poms(self.project))
        self.mapper_xmls = self._scope_resources(J.find_mapper_xmls(self.project))
        self.sql_files = self._scope_resources(J.find_sql_files(self.project))
        self.docs_md = self._scope_resources(J.find_docs_md(self.project))
        self.docs_dirs = self._scope_resources(J.find_docs_dirs(self.project))
        self.log_configs = self._scope_resources(J.find_log_configs(self.project))
        self._classes = None
        self._targets = None

    def _scope_resources(self, paths):
        """把资源类文件收敛到扫描范围。

        - ``resources_scope=project``：不收敛（旧行为，全项目）；
        - ``path``：严格取 ``--path`` 子树内的资源文件；
        - ``auto``（默认）：``--path`` 子树 ∪ 集中目录（``sql/``、``db/``、``docs/`` …）下
          **文件名含模块关键词**的资源文件——兼顾「DDL 集中放项目级并按模块命名」的常见布局
          （如扫 ``xwd-mall-center`` 时纳入 ``sql/0930/0831-mall-center-init.sql``）。
        """
        if not self.scope_path or self.resources_scope == "project":
            return list(paths)
        root = os.path.abspath(self.scope_path)
        if os.path.isfile(root):
            root = os.path.dirname(root)
        if not os.path.isdir(root):
            return list(paths)
        keys = _module_keywords(root)
        out = []
        for p in paths:
            ap = os.path.abspath(p)
            if ap == root or ap.startswith(root + os.sep):
                out.append(p)
            elif self.resources_scope == "auto" and _is_central_named_resource(
                    ap, self.project, keys):
                out.append(p)
        return out

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


# 抑制注释：静态检查通行的两种写法（块级 OFF/ON、近邻 ignore）
_SUPPRESS_OFF_RE = re.compile(r"CHECKSTYLE:OFF\s+(\S+)")
_SUPPRESS_ON_RE = re.compile(r"CHECKSTYLE:ON\s+(\S+)")
_SUPPRESS_NEAR_RE = re.compile(r"checkstyle:ignore\s+(\S+)")


def _suppression_lines(text, rule=None):
    """返回被抑制注释覆盖的 1-based 行号集合。

    支持静态检查通行的两种写法：

    1. 块级：``// CHECKSTYLE:OFF <规则名>`` … ``// CHECKSTYLE:ON <规则名>`` 之间的所有行；
    2. 近邻：``// checkstyle:ignore <规则名>`` 所在行与其后一行。

    ``rule`` 为具体规则名时只匹配该规则（``ALL`` 视为匹配全部）；为 ``None`` 时匹配任意
    规则名，供报告侧统一过滤证据使用。
    """
    lines = text.split("\n")
    out = set()
    active = set()
    for i, line in enumerate(lines, 1):
        on = _SUPPRESS_ON_RE.search(line)
        if on and (rule is None or on.group(1) in (rule, "ALL")):
            active.discard(on.group(1))
        if active:
            out.add(i)
        off = _SUPPRESS_OFF_RE.search(line)
        if off and (rule is None or off.group(1) in (rule, "ALL")):
            active.add(off.group(1))
        near = _SUPPRESS_NEAR_RE.search(line)
        if near and (rule is None or near.group(1) in (rule, "ALL")):
            out.add(i)
            out.add(i + 1)
    return out


def _file_suppressions(ctx, rel_path):
    """按相对路径取「抑制行集合」，带缓存避免重复读文件。"""
    cache = getattr(ctx, "_suppress_cache", None)
    if cache is None:
        cache = {}
        ctx._suppress_cache = cache
    if rel_path not in cache:
        try:
            cache[rel_path] = _suppression_lines(_read(os.path.join(ctx.project, rel_path)))
        except Exception:      # pragma: no cover - 防御性
            cache[rel_path] = set()
    return cache[rel_path]


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


def _method_anns(m):
    """方法注解的简单名集合。"""
    return set(a.split(".")[-1] for a in m.annotations)


def check_01(ctx):
    """#1 方法级注释全覆盖。

    范围与口径对齐主流静态检查的「public 方法需 Javadoc」：

    - 组一目标类（Controller/ServiceImpl/Service/Listener/Job/Consumer）：全部方法（含 private）；
    - 其余类型：仅显式 ``public`` 的方法与构造器（接口里未写 public 的方法是隐式 public，
      静态检查按显式修饰符判定，故不纳入，避免大批误报）。

    豁免：``@Override`` 方法、getter/setter 等单行透传、方法体行数 < 2 的短方法
    （静态检查的 ``minLineCount`` 口径：大括号之间不足 2 行不要求 Javadoc）。
    """
    bag = Bag(ctx.max_findings)
    total = 0
    for ci in ctx.classes():
        is_target = is_target_class(ci)
        for m in ci.methods:
            if not is_target:
                if "public" not in m.modifiers:
                    continue
                if "Override" in _method_anns(m):
                    continue
                if m.has_body() and (m.body_close_line - m.body_open_line - 1) < 2:
                    continue
                if _is_trivial_accessor(m):
                    continue
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
    hard = Bag(ctx.max_findings)
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
                    hard.add(ctx.rel(ci.path), m.body_open_line + run_start + 1,
                             "%s 连续 %d 行无任何注释" % (m.name, run))
                    run = 0
                    run_start = None
                    break
            if code >= 20 and numbered > 0 and last_numbered < (len(m.body_orig_lines) * 2 // 3):
                bag.add(ctx.rel(ci.path), m.body_open_line,
                        "%s 长方法(%d 行)编号注释未覆盖到后半段" % (m.name, code))
    if total == 0:
        return Item(3, CHECK_NAMES[3], STATUS_PASS, "未发现需核对的业务方法")
    if hard.total:
        return Item(3, CHECK_NAMES[3], STATUS_FAIL,
                    "%d 处连续 ≥10 行代码无任何注释" % hard.total,
                    _merge_hints(hard, bag, ctx.max_findings))
    if bag.total:
        return Item(3, CHECK_NAMES[3], STATUS_MANUAL,
                    "%d 处疑似步骤注释缺失（启发式，需人工核对）" % bag.total, bag.items)
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


_DOC_SELECTION_RE = re.compile(r"springdoc|knife4j|swagger|springfox|apifox", re.I)
_LOG_SELECTION_RE = re.compile(r"logback|log4j2?", re.I)


def _constraint_selection(ctx, pattern):
    """约束文件（2.1 / 0.5）里是否写明了该项选型；命中返回选型名，否则 None。

    WHY 只在约束写明选型时才判 fail：没写明时"该项目该用哪套"无从判断，按仓库原则
    「不确定当正常」处理——否则会把"用 Apifox 外部维护文档"这类合法项目误判为违规。
    """
    p = getattr(ctx, "constraint_path", None)
    if not p or not os.path.isfile(p):
        return None
    try:
        m = pattern.search(J.read_text(p))
    except Exception:
        return None
    return m.group(0) if m else None


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
        sel = _constraint_selection(ctx, _DOC_SELECTION_RE)
        if sel:
            return Item(6, CHECK_NAMES[6], STATUS_FAIL,
                        "约束要求接口文档选型「%s」，但代码中既无依赖也无注解" % sel, evidence)
        return Item(6, CHECK_NAMES[6], STATUS_PASS,
                    "未发现接口文档痕迹；%s未写明选型 → 按「不确定当正常」处理"
                    % ctx.mode_note)
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
    sel = _constraint_selection(ctx, _LOG_SELECTION_RE)
    if sel:
        return Item(7, CHECK_NAMES[7], STATUS_FAIL,
                    "约束要求日志框架「%s」，但未发现配置文件与依赖" % sel, evidence)
    return Item(7, CHECK_NAMES[7], STATUS_PASS,
                "未发现日志框架痕迹；%s未写明选型 → 按「不确定当正常」处理"
                % ctx.mode_note)


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
                tm = _TABLE_NAME_RE.search(block)
                table = _simple_name(tm.group(1)) if tm else ""
                pg_cols, pg_loose, _pg_tables = _pg_comment_index(block)
                for offset, raw in enumerate(block.splitlines()):
                    s = raw.strip()
                    if not s or s.startswith("--") or s.startswith("(") or s.startswith(")"):
                        continue
                    if re.match(r"^(PRIMARY|UNIQUE|KEY|INDEX|CONSTRAINT|FOREIGN|CHECK|FULLTEXT|SPATIAL)\b",
                                s, re.I):
                        continue
                    if not re.match(r"^[`\"\w]", s):
                        continue
                    if "COMMENT" in s.upper():
                        continue
                    col = _simple_name(re.match(r"^([`\"\w]+)", s).group(1))
                    if (table, col) in pg_cols or col in pg_loose:
                        continue      # 已由 COMMENT ON COLUMN 覆盖
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


# PostgreSQL 注释语句（列/表注释写在建表语句之外）
_COMMENT_ON_COLUMN_RE = re.compile(
    r"COMMENT\s+ON\s+COLUMN\s+([\w.\"]+)\s+IS\s", re.I)
_COMMENT_ON_TABLE_RE = re.compile(
    r"COMMENT\s+ON\s+TABLE\s+([\w.\"]+)\s+IS\s", re.I)
# CREATE TABLE 头部的表名（可带 schema 与引号/反引号）
_TABLE_NAME_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.\"`]+)", re.I)


def _pg_comment_index(text):
    """收集 PG 风格 ``COMMENT ON`` 已覆盖的 (表, 列) 与表名。

    WHY: PostgreSQL 的列/表注释写在建表语句之外（``COMMENT ON COLUMN t.c IS '...'``），
    只按 MySQL 的「字段行内联 COMMENT」判定，会把 PG 项目的 DDL 整片误报为缺注释。
    返回 ``(cols, loose_cols, tables)``：cols 为 (表, 列)，loose_cols 为仅知列名的情形，
    tables 为已注释的表名。
    """
    cols = set()
    loose = set()
    tables = set()
    for m in _COMMENT_ON_COLUMN_RE.finditer(text):
        parts = [p.strip('"').strip("`").lower() for p in m.group(1).split(".")]
        parts = [p for p in parts if p]
        if len(parts) >= 2:
            cols.add((parts[-2], parts[-1]))
        elif len(parts) == 1:
            loose.add(parts[0])
    for m in _COMMENT_ON_TABLE_RE.finditer(text):
        parts = [p.strip('"').strip("`").lower() for p in m.group(1).split(".")]
        parts = [p for p in parts if p]
        if parts:
            tables.add(parts[-1])
    return cols, loose, tables


def _simple_name(token):
    """取库对象名末段并去引号/反引号、转小写。"""
    return token.split(".")[-1].strip('"').strip("`").lower()


def _check_ddl_block(rel, base_line, block, bag, pg_cols=frozenset(),
                     pg_loose=frozenset(), pg_tables=frozenset()):
    open_idx = block.find("(")
    close_idx = block.rfind(")")
    if open_idx < 0 or close_idx < 0:
        return
    body = block[open_idx + 1:close_idx]
    head_text = block[:open_idx]
    head_offset = block[:open_idx].count("\n")
    tm = _TABLE_NAME_RE.search(head_text)
    table = _simple_name(tm.group(1)) if tm else ""
    skip_depth = 0
    for offset, raw in enumerate(body.splitlines()):
        s = raw.strip().rstrip(",").strip()
        if skip_depth > 0:
            # 多行表约束（CHECK (...) 跨行）的续行：按括号配对整体跳过，
            # 否则会把 `AND xxx >= 0)` 这类续行当成字段误报「缺 COMMENT」
            skip_depth += s.count("(") - s.count(")")
            continue
        if not s or s.startswith("--"):
            continue
        if _COL_KEYWORD_RE.match(s):
            skip_depth = max(0, s.count("(") - s.count(")"))
            continue
        if not re.match(r"^[`\"\w]", s):
            continue
        if "COMMENT" in s.upper():
            continue
        col = _simple_name(re.match(r"^([`\"\w]+)", s).group(1))
        if (table, col) in pg_cols or col in pg_loose:
            continue          # 已由 COMMENT ON COLUMN 覆盖
        bag.add(rel, base_line + head_offset + offset + 1,
                "字段缺 COMMENT: %s" % s[:70])
    tail = block[close_idx:]
    if not re.search(r"\bCOMMENT\b", tail, re.I) and table not in pg_tables:
        bag.add(rel, base_line + block[:close_idx].count("\n"),
                "表级缺 COMMENT（) 之后或 COMMENT ON TABLE 缺失）")


def check_11(ctx):
    """#11 DDL 字段注释：字段与表均须有注释。

    同时支持两种写法——MySQL 的字段行内联 ``COMMENT '...'``／``COMMENT='...'``，
    以及 PostgreSQL 的 ``COMMENT ON COLUMN`` / ``COMMENT ON TABLE`` 独立语句。
    """
    bag = Bag(ctx.max_findings)
    sources = list(ctx.sql_files) + list(ctx.docs_md)
    found = 0
    for p in sources:
        text = _read(p)
        if not re.search(r"CREATE\s+TABLE", text, re.I):
            continue
        pg_cols, pg_loose, pg_tables = _pg_comment_index(text)
        for m, line in _finditer_pos(_CREATE_TABLE_RE, text):
            found += 1
            _check_ddl_block(ctx.rel(p), line, m.group(0), bag,
                             pg_cols, pg_loose, pg_tables)
    if found == 0:
        return Item(11, CHECK_NAMES[11], STATUS_SKIP, "未发现 CREATE TABLE 语句")
    if bag.total:
        return Item(11, CHECK_NAMES[11], STATUS_FAIL,
                    "%d 张表 DDL 注释缺失 %d 处" % (found, bag.total), bag.items)
    return Item(11, CHECK_NAMES[11], STATUS_PASS,
                "%d 张表 DDL 字段与表注释齐备（兼容 MySQL 内联与 PG COMMENT ON）" % found)


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
    for f, line, tok in hits:
        text = _read(f)
        has_lock = bool(_LOCK_RE.search(text))
        has_limit = bool(_LIMIT_RE.search(text))
        bag.add(ctx.rel(f), line,
                "%s；防重入痕迹=%s，批处理 LIMIT=%s → 请确认：多实例部署需分布式锁/状态位，"
                "批量处理需 LIMIT 分批"
                % (tok, "有" if has_lock else "无", "有" if has_limit else "无"))
    return Item(24, CHECK_NAMES[24], STATUS_MANUAL,
                "%d 个定时任务待决策（防重入/LIMIT 是否要做、怎么做由人定，本项不判 fail）"
                % len(hits), bag.items)


_RABBIT_RE = re.compile(r"@RabbitListener\b")
_KAFKA_RE = re.compile(r"@KafkaListener\b")


def check_25(ctx):
    hits = _scan_pattern(ctx, _RABBIT_RE) + _scan_pattern(ctx, _KAFKA_RE)
    if not hits:
        return Item(25, CHECK_NAMES[25], STATUS_SKIP, "无 @RabbitListener/@KafkaListener")
    bag = Bag(ctx.max_findings)
    files = sorted(set(h[0] for h in hits))
    for f, line, tok in hits:
        text = _read(f)
        has_deadletter = bool(re.search(r"dead.?letter|死信|DLX|Retry|retry", text, re.I))
        has_idem = bool(re.search(r"幂等|idempot|去重|唯一键|SETNX|duplicate", text, re.I))
        bag.add(ctx.rel(f), line,
                "%s；重试/死信线索=%s，幂等线索=%s → 请确认：at-least-once 投递需消费幂等，"
                "重试需上限 + 死信队列"
                % (tok, "有" if has_deadletter else "无", "有" if has_idem else "无"))
    return Item(25, CHECK_NAMES[25], STATUS_MANUAL,
                "%d 个消息监听待决策（幂等/死信是否要做、怎么做由人定，本项不判 fail）"
                % len(hits), bag.items)


_MULTIPART_RE = re.compile(r"\bMultipartFile\b")
# 扩展名白名单线索：显式扩展名字面量、`endsWith(...)` 判断、常见常量/变量名、中文写法。
# WHY 不止图片后缀：批量导入类上传普遍用 Excel/CSV 白名单，只认图片会漏判为「无白名单」。
_EXT_WHITELIST_RE = re.compile(
    r"\.(?:xlsx?|csv|pdf|docx?|pptx?|jpe?g|png|gif|bmp|zip|txt)\b"
    r"|endsWith\s*\("
    r"|allowedExt|allowedExtensions?|allowExtensions?|ALLOWED_EXT"
    r"|extensions?\s*[:=]|suffix|扩展名|白名单", re.I)
# 大小限制线索：上传大小配置、`getSize()` 判断、`n * 1024` 与 `n MB` 字面量
_FILE_SIZE_RE = re.compile(
    r"MaxUploadSize|getSize\s*\(\)|maxSize|maxFileSize|MAX_FILE_SIZE"
    r"|\d+\s*\*\s*1024|\d+\s*MB", re.I)
# 重命名/唯一化线索：UUID、纳秒/毫秒时间戳、时间格式化
_UNIQUE_NAME_RE = re.compile(
    r"UUID|uuid|nanoTime|currentTimeMillis|LocalDateTime\.now|DateTimeFormatter"
    r"|System\.currentTime|timestamp", re.I)


def check_26(ctx):
    """#26 文件上传安全：核对上传点的扩展名白名单 / 重命名唯一化 / 大小限制。

    只报**实现侧**上传点：接口（`@FeignClient`、Service/API 接口）仅声明 `MultipartFile`
    形参，校验逻辑在实现类，报告接口只会制造噪音。
    """
    hits = _scan_pattern(ctx, _MULTIPART_RE)
    if not hits:
        return Item(26, CHECK_NAMES[26], STATUS_SKIP, "无 MultipartFile 上传")
    bag = Bag(ctx.max_findings)
    files = sorted(set(h[0] for h in hits))
    checked = 0
    for f in files:
        try:
            if J.parse_java(f).kind == "interface":
                continue
        except Exception:      # pragma: no cover - 防御性
            pass
        checked += 1
        # 去注释但保留字符串：白名单证据常在字符串字面量里，注释里提到不算
        text = J.strip_comments(_read(f))
        whitelist = bool(_EXT_WHITELIST_RE.search(text))
        unique_name = bool(_UNIQUE_NAME_RE.search(text))
        size_limit = bool(_FILE_SIZE_RE.search(text))
        bag.add(ctx.rel(f), 1,
                "上传点：扩展名白名单=%s，重命名/唯一化=%s，大小限制=%s → 请确认："
                "公网上传建议三者齐备，内部/受信上传可放宽"
                % (whitelist, unique_name, size_limit))
    if checked == 0:
        return Item(26, CHECK_NAMES[26], STATUS_SKIP,
                    "%d 个文件含 MultipartFile，但均为接口声明，无实现侧上传点" % len(files))
    return Item(26, CHECK_NAMES[26], STATUS_MANUAL,
                "%d 个文件上传点待决策（安全措施要求由人定，本项不判 fail）" % checked, bag.items)


_WRITE_MAPPING_RE = re.compile(r"@(PostMapping|PutMapping)\b")
_IDEMPOTENT_RE = re.compile(
    r"幂等|idempot|唯一键|unique|token|令牌|SETNX|setIfAbsent|@RepeatSubmit|防重|duplicate",
    re.I)


def check_27(ctx):
    hits = _scan_pattern(ctx, _WRITE_MAPPING_RE)
    if not hits:
        return Item(27, CHECK_NAMES[27], STATUS_SKIP, "无 POST/PUT 写接口")
    bag = Bag(ctx.max_findings)
    cache = {}
    for f, line, tok in hits:
        if f not in cache:
            cache[f] = _read(f)
        has_idem = bool(_IDEMPOTENT_RE.search(cache[f]))
        bag.add(ctx.rel(f), line,
                "%s；本类幂等痕迹=%s → 请确认：该接口是否需要幂等、用哪种方案"
                "（唯一键 / 令牌 / Redis SETNX）"
                % (tok, "有" if has_idem else "无"))
    return Item(27, CHECK_NAMES[27], STATUS_MANUAL,
                "%d 个写接口待决策（是否需要幂等、怎么做由人定，本项不判 fail）"
                % len(hits), bag.items)


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
    return Item(31, CHECK_NAMES[31], STATUS_FAIL,
                "%d 组方法体完全相同（应抽公共组件）" % len(dups), bag.items)


_LOG_LINE_RE = re.compile(r"\b(?:log|LOG|logger|LOGGER)\.(?:debug|info|warn|error)\s*\(([^;]*)\)\s*;")
# 取值链：`.get(...)` 后紧跟成员访问 —— 空集合 / 键不存在时先得到 null 再取成员 = 必 NPE
_NPE_CHAIN_ARG_RE = re.compile(r"\.\s*get\s*\([^)]*\)\s*\.")


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
            if _NPE_CHAIN_ARG_RE.search(call_zone):
                bag.add(ctx.rel(f), lineno,
                        "日志参数含取值链（.get(...). 取值可能为 null → eager 求值 NPE）")
    if bag.total:
        return Item(32, CHECK_NAMES[32], STATUS_FAIL,
                    "%d 处日志参数含高危取值链（可能 NPE）" % bag.total, bag.items)
    return Item(32, CHECK_NAMES[32], STATUS_PASS, "未发现日志参数高风险取值链")


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
# 组六：格式与机械卫生（#34~#38，标准/存量两模式均执行）
# ---------------------------------------------------------------------------

_TRAILING_WS_RE = re.compile(r"[ \t]+$")
_LEADING_TAB_RE = re.compile(r"^\t|^[ ]*\t")


def check_34(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        lines = J.read_lines(f)
        for i, line in enumerate(lines):
            issues = []
            # WHY 证据自带「应改成什么」：模型不必回读源码即可精确改这几行（改哪、改成什么）
            if _TRAILING_WS_RE.search(line):
                issues.append("行尾有空白字符（应删除）")
            if _LEADING_TAB_RE.search(line):
                issues.append("缩进含 Tab（应改为 4 空格）")
            if issues:
                bag.add(ctx.rel(f), i + 1,
                        "%s: %r" % ("、".join(issues), line[:60]))
    if bag.total:
        return Item(34, CHECK_NAMES[34], STATUS_FAIL,
                    "%d 行存在行尾空白/缩进 Tab" % bag.total, bag.items)
    return Item(34, CHECK_NAMES[34], STATUS_PASS, "无行尾空白、无缩进 Tab")


_LONG_LINE_LIMIT = 120
_URL_RE = re.compile(r"https?://")


def check_35(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        lines = J.read_lines(f)
        for i, line in enumerate(lines):
            if len(line) <= _LONG_LINE_LIMIT:
                continue
            if line.startswith("package ") or line.startswith("import "):
                continue
            if _URL_RE.search(line):
                continue
            bag.add(ctx.rel(f), i + 1, "行长 %d > %d" % (len(line), _LONG_LINE_LIMIT))
    if bag.total:
        return Item(35, CHECK_NAMES[35], STATUS_FAIL,
                    "%d 行超过 %d 字符" % (bag.total, _LONG_LINE_LIMIT), bag.items)
    return Item(35, CHECK_NAMES[35], STATUS_PASS,
                "无超过 %d 字符的长行" % _LONG_LINE_LIMIT)


_CONSEC_BLANK_RE = re.compile(r"\n[ \t]*\n[ \t]*\n")


def check_36(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        text = _read(f).replace("\r\n", "\n").replace("\r", "\n")
        for m in _CONSEC_BLANK_RE.finditer(text):
            bag.add(ctx.rel(f), _line_of(text, m.start()) + 1, "连续空行")
    if bag.total:
        return Item(36, CHECK_NAMES[36], STATUS_FAIL,
                    "发现 %d 处连续空行" % bag.total, bag.items)
    return Item(36, CHECK_NAMES[36], STATUS_PASS, "无连续空行")


_IMPORT_RE = re.compile(r"^[ \t]*import\s+(static\s+)?([\w.]+?)(\.\*)?\s*;", re.M)
# java.lang 直接子类型才是隐式导入；java.lang.reflect.* 之类的子包不算冗余
_JAVA_LANG_IMPORT_RE = re.compile(r"java\.lang\.[A-Za-z_$][\w$]*$")


def check_37(ctx):
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        rel = ctx.rel(f)
        text = _read(f)
        # 使用判定只看「代码 + Javadoc」：注释与字符串中的同名字面量不算真实引用，
        # 但 Javadoc 内的 {@link X} 引用按惯例视为已使用（与主流静态检查口径一致）。
        body = _IMPORT_RE.sub("", J.mask_source(text))
        body += "\n" + "\n".join(re.findall(r"/\*\*.*?\*/", text, re.S))
        pkg_match = _PACKAGE_RE.search(text)
        self_pkg = pkg_match.group(1) if pkg_match else ""
        seen = {}
        for m, line in _finditer_pos(_IMPORT_RE, text):
            total += 1
            import_text = m.group(0).strip()
            package = m.group(2)
            if m.group(3):
                bag.add(rel, line, "通配符 import: %s" % import_text)
                continue
            if package.startswith("sun.") or package.startswith("com.sun."):
                bag.add(rel, line, "JDK 内部 API import: %s" % import_text)
                continue
            # 冗余 import：重复、java.lang（隐式可见）、与当前包同包
            if package in seen:
                bag.add(rel, line, "重复 import（第 %d 行已导入）: %s"
                        % (seen[package], import_text))
                continue
            seen[package] = line
            if _JAVA_LANG_IMPORT_RE.match(package):
                bag.add(rel, line, "冗余 import（java.lang 隐式可见）: %s" % import_text)
                continue
            if self_pkg and package.rsplit(".", 1)[0] == self_pkg:
                bag.add(rel, line, "冗余 import（与当前包 %s 相同）: %s"
                        % (self_pkg, import_text))
                continue
            # 未使用：静态导入与普通导入同样按末位简单名核对
            simple = package.split(".")[-1]
            if simple and not re.search(r"\b%s\b" % re.escape(simple), body):
                bag.add(rel, line, "疑未使用 import: %s" % import_text)
    if bag.total:
        return Item(37, CHECK_NAMES[37], STATUS_FAIL,
                    "%d 条 import 不合规（通配符/内部 API/冗余/疑未使用；未使用为字面启发式）"
                    % bag.total, bag.items)
    return Item(37, CHECK_NAMES[37], STATUS_PASS,
                "共 %d 条 import，无通配符/内部 API/冗余/疑未使用" % total)


# 运算符 token（长 token 在前，确保 `<<=`/`>>>`/`->` 不被拆成两个短 token）。
# 口径：双目与赋值类运算符、三目 `?`/`:`、lambda `->` 两侧均须有空白。
_OPERATOR_TOKENS = (
    ">>>=", "<<=", ">>=", "==", "!=", "<=", ">=", "&&", "||",
    "<<", ">>>", ">>", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "->",
    "+", "-", "*", "/", "%", "&", "|", "^", "<", ">", "=", "?", ":",
)
_OPERATOR_TOKEN_RE = re.compile("|".join(re.escape(t) for t in _OPERATOR_TOKENS))
# 前一字符为「操作数结尾」时该 +/-/* 才是双目运算符（排除 -1、a * -1 等单目写法）
_OPERAND_END_RE = re.compile(r"[A-Za-z0-9_$)\]\"]")
# 紧随这些关键字之后的 +/-/* 一律是单目写法（`return -x`、`throw -x`、`case -1` 等）
_PRE_UNARY_KEYWORD_RE = re.compile(
    r"\b(?:return|throw|case|assert|yield|new|instanceof|else|do)$")
# 仅三目表达式的 `:` 参与空格核对；switch 分支 / for-each / 标号 的冒号不计
_TERNARY_BEFORE_RE = re.compile(r"\?[^?:;{}]*$")
# 关键字后须有空白（WhitespaceAfter/WhitespaceAround 的 LITERAL_* 口径）；
# 紧随 `;` 的 `return;` 形态不属违规，故排除分号
_KEYWORD_BLANK_RE = re.compile(
    r"\b(if|for|while|switch|catch|synchronized|try|do|else|finally)\b(?=[^\s;])")
_BRANCH_RE = re.compile(r"\b(if|for|while)\s*\(")
_BRACE_NEWLINE_KEYWORD_RE = re.compile(r"\}\s*\n\s*(else|catch|finally)\b")
# 泛型实参/形参内容：仅含类型字符（含嵌套泛型、逗号、数组、通配符）
_GENERIC_INNER_OK_RE = re.compile(
    r"^[\w\s.,?$\[\]]*(?:<[\w\s.,?$\[\]]*>[\w\s.,?$\[\]]*)*$")
# 成员声明起始位置（修饰符之后 / 行首 / 语句块起始），用于识别方法级泛型形参 `<T>`
_MEMBER_START_BEFORE_RE = re.compile(
    r"(?:\b(?:public|protected|private|static|final|abstract|synchronized"
    r"|default|native|strictfp)\s+|\A|[{;}]\s*)$")


def _generic_span_end(masked, i):
    """``i`` 处的 ``<`` 若能配对到 ``>`` 则返回该 ``>`` 偏移，否则返回 -1。"""
    depth = 0
    n = len(masked)
    j = i
    while j < n:
        c = masked[j]
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
            if depth == 0:
                return j
        elif c in "{};":
            return -1
        j += 1
    return -1


def _strip_generic_spans(masked):
    """把泛型 ``<...>`` 片段替换为等长空格。

    WHY: ``List<Long>`` 里的 ``t<L``、``private <T> T foo()`` 里的 ``<T>`` 会被运算符
    空格核对误判为「小于号/大于号缺空格」，必须先剔除泛型片段再判运算符。识别两类：

    1. 类型使用/声明：``<`` 紧跟标识符、``)``、``]``、``.``（``List<Long>``、
       ``Wrappers.<T>lambdaQuery()``）；
    2. 方法级泛型形参：``<`` 位于成员声明起始处（``private <T> T withLock(...)``）。

    两类都要求内部全是类型字符，避免吞掉真实比较表达式（如 ``if (i<n)``）。
    """
    out = list(masked)
    i = 0
    n = len(masked)
    while i < n:
        if masked[i] == "<":
            prev_ch = masked[i - 1] if i > 0 else ""
            prev_ok = bool(prev_ch) and (prev_ch.isalnum() or prev_ch in "_$).]")
            type_param = bool(_MEMBER_START_BEFORE_RE.search(masked[:i]))
            if prev_ok or type_param:
                end = _generic_span_end(masked, i)
                if end > i and _GENERIC_INNER_OK_RE.match(masked[i + 1:end]):
                    for k in range(i, end + 1):
                        out[k] = " "
                    i = end + 1
                    continue
        i += 1
    return "".join(out)


def _is_ternary_colon(masked, pos):
    """判断 pos 处的 ``:`` 是否为三目运算符的第二段。

    WHY: ``:`` 在 switch 分支、for-each、语句标号里都不要求前置空白，只有三目表达式的
    第二段才要求两侧空白。用「同一语句段内是否出现过 ``?``」区分，避免成片误报。
    """
    start = max(masked.rfind(";", 0, pos), masked.rfind("{", 0, pos),
                masked.rfind("}", 0, pos), masked.rfind(":", 0, pos))
    return "?" in masked[start + 1:pos]


def _operator_spacing_hits(masked):
    """产出 (偏移, 说明)——运算符两侧缺空白、或关键字后缺空白的写法。

    WHY: 只报「双目/赋值/三目/lambda」运算符，且用「前一个非空字符是否为操作数结尾」
    排除单目写法（``-1``、``a * -1``）；泛型 ``<...>`` 已被 :func:`_strip_generic_spans`
    剔除，不会把 ``List<Long>`` 判成 ``t<L``。
    """
    for m in _OPERATOR_TOKEN_RE.finditer(masked):
        tok = m.group(0)
        s, e = m.start(), m.end()
        if tok in ("+", "-"):
            # 自增/自减 `++`、`--` 不是双目运算符（相邻出现同符号即为自增自减）
            if masked[s - 1:s] == tok or masked[e:e + 1] == tok:
                continue
        if tok in ("+", "-", "*"):
            j = s - 1
            while j >= 0 and masked[j] in " \t\r\n":
                j -= 1
            # 前一 token 是 return/throw/case 等关键字时，该符号是单目（如 `return -x`）
            if _PRE_UNARY_KEYWORD_RE.search(masked[:j + 1]):
                continue
            if j < 0 or not _OPERAND_END_RE.match(masked[j]):
                continue
            if tok == "*" and masked[s - 1] == ".":
                continue
        if tok == ":" and not _is_ternary_colon(masked, s):
            continue
        before = masked[s - 1] if s > 0 else "\n"
        after = masked[e] if e < len(masked) else "\n"
        if before not in " \t\r\n":
            yield s, "运算符 %s 前缺空格（应补 1 个空格）" % tok
        if after not in " \t\r\n":
            yield e, "运算符 %s 后缺空格（应补 1 个空格）" % tok
    for m in _KEYWORD_BLANK_RE.finditer(masked):
        yield m.end(), "关键字 %s 后缺空格（应补 1 个空格）" % m.group(1)


def check_38(ctx):
    """#38 空格（启发式）：运算符/关键字两侧空白。

    WHY 记 manual 不记 fail：运算符空白受泛型、单目、lambda、switch 分支等上下文影响，
    本实现为字面启发式，宁多列候选交人工核对，也不冒险把正常代码判成失败。
    花括号类判定均为可靠项，已全部独立到 #57（必写 / ``{`` 位置 / ``}`` 与 else·catch·finally 同行），
    本项不再重复给出花括号候选。
    """
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = _strip_generic_spans(J.mask_source(_read(f)))
        for pos, detail in _operator_spacing_hits(masked):
            bag.add(rel, _line_of(masked, pos), detail)
    if bag.total:
        return Item(38, CHECK_NAMES[38], STATUS_FAIL,
                    "%d 处空格不规范（运算符/关键字两侧应有空格）" % bag.total, bag.items)
    return Item(38, CHECK_NAMES[38], STATUS_PASS, "未发现空格不规范")


def _match_paren(masked, open_pos):
    """给定 '(' 的偏移，返回匹配 ')' 的偏移（掩码文本内）；找不到返回 -1。"""
    depth = 0
    i = open_pos
    n = len(masked)
    while i < n:
        c = masked[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


# ---------------------------------------------------------------------------
# 组七：命名 / 结构 / 书写卫生（#39~#44，标准/存量两模式均执行）
# ---------------------------------------------------------------------------

_PACKAGE_RE = re.compile(r"^[ \t]*package[ \t]+([A-Za-z_$][\w$.]*)[ \t]*;", re.M)
_PACKAGE_SEGMENT_RE = re.compile(r"^[a-z][a-z0-9]*$")
_UPPER_CAMEL_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_LOWER_CAMEL_RE = re.compile(r"^[a-z][A-Za-z0-9]*$")
_UPPER_SNAKE_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")
# 仅匹配单行内可判定的 static final 字段声明（非贪婪，避免跨语句误吞）
_STATIC_FINAL_FIELD_RE = re.compile(
    r"\bstatic\s+final\s+[\w.$<>\[\],\s?]+?\s+([A-Za-z_$][\w$]*)\s*[=;,]")
# 顶层类型声明的泛型形参（只判 class/interface/enum 名后的 <...>，避免把类型使用误判为声明）
_GENERIC_PARAM_RE = re.compile(
    r"\b(?:class|interface|enum)\s+[A-Za-z_$][\w$]*\s*<\s*([^<>]+?)\s*>")
# 泛型形参命名口径：单个大写字母，或大写字母 + 1 位数字（如 T、E、T1）
_TYPE_PARAM_NAME_RE = re.compile(r"^[A-Z][0-9]?$")
# 方法级泛型形参声明：修饰符与注解之后、返回类型之前的 `<...>`
_METHOD_TYPE_PARAM_RE = re.compile(
    r"^\s*(?:(?:%s)\s+)*<\s*([^<>]+?)\s*>\s"
    % "|".join(("public", "protected", "private", "static", "final",
                "abstract", "synchronized", "default", "native", "strictfp")))
# 连续大写缩写超过 3 个视为可疑；常见缩写豁免
_ABBREV_EXEMPT = frozenset(
    ("DAO", "ID", "DTO", "VO", "PO", "BO", "SQL", "URL", "URI",
     "HTTP", "JSON", "XML", "API"))
_ABBREV_RUN_RE = re.compile(r"[A-Z]{4,}")
_IDENT_RE = re.compile(r"\b[A-Za-z_$][\w$]*\b")


def _check_package_name(masked, rel, bag):
    """package 声明须全小写（每段 ^[a-z][a-z0-9]*$，不含大写/下划线）。"""
    m = _PACKAGE_RE.search(masked)
    if not m:
        return
    pkg = m.group(1)
    for seg in pkg.split("."):
        if not _PACKAGE_SEGMENT_RE.match(seg):
            bag.add(rel, _line_of(masked, m.start()),
                    "package 段非全小写: %s（包名 %s）" % (seg, pkg))
            break


def _top_level_types(masked):
    """扫描掩码文本，返回顶层类型 (kind, name, line)：大括号深度为 0 才算顶层。"""
    out = []
    pos = 0
    depth = 0
    for m in re.finditer(r"\b(class|interface|enum|record)\s+([A-Za-z_$][\w$]*)", masked):
        while pos < m.start():
            ch = masked[pos]
            if ch == "{":
                depth += 1
            elif ch == "}" and depth > 0:
                depth -= 1
            pos += 1
        if depth == 0:
            out.append((m.group(1), m.group(2), _line_of(masked, m.start())))
    return out


_TYPE_DECL_RE = re.compile(r"\b(class|interface|enum|record)\s+([A-Za-z_$][\w$]*)")


def _all_types(masked):
    """全部类型声明 ``(kind, name, line, depth)``；depth > 0 即嵌套类型。"""
    out = []
    pos = 0
    depth = 0
    for m in _TYPE_DECL_RE.finditer(masked):
        while pos < m.start():
            ch = masked[pos]
            if ch == "{":
                depth += 1
            elif ch == "}" and depth > 0:
                depth -= 1
            pos += 1
        out.append((m.group(1), m.group(2), _line_of(masked, m.start()), depth))
    return out


def _check_package_dir(rel_path, masked, bag):
    """核对 package 声明与文件所在目录是否一致（不一致属结构问题，记候选不 fail）。"""
    m = _PACKAGE_RE.search(masked)
    if not m:
        return
    posix = rel_path.replace("\\", "/")
    expect = m.group(1).replace(".", "/") + "/" + os.path.basename(posix)
    if not posix.endswith(expect):
        bag.add(rel_path, _line_of(masked, m.start()),
                "package 与目录不一致: package %s，路径 %s" % (m.group(1), posix))


def _check_type_params(inner, rel, line, bag):
    """核对一段泛型形参声明的形参名（``T`` / ``T1`` / ``T extends Object``）。"""
    for param in inner.split(","):
        head = param.strip().split()[0] if param.strip() else ""
        if re.match(r"^[A-Za-z_$][\w$]*$", head) and not _TYPE_PARAM_NAME_RE.match(head):
            bag.add(rel, line, "泛型形参命名不规范（应为单个大写字母）: %s" % head)


def _unallowed_abbrev_run(run):
    """在连续大写段里找出「未被豁免、且连续大写 >3」的部分；无则返回 None。

    WHY 不能只判「整段是否在豁免表里」：`JSONObject` 的连续大写段是 `JSONO`
    （= `JSON` + `O`），整段不在豁免表 → 会把合法的 `JSON` 前缀一并报出（实测
    193 个文件里 25 处候选全是这类误报）。需按豁免词逐段剥离后再看剩余长度。
    """
    i = 0
    n = len(run)
    while i < n:
        for w in _ABBREV_EXEMPT:
            if run.startswith(w, i):
                i += len(w)
                break
        else:
            j = i
            while j < n and run[j].isupper():
                j += 1
            if j - i > 3:
                return run[i:j]
            i = j if j > i else i + 1
    return None


def check_39(ctx):
    bag = Bag(ctx.max_findings)         # 可靠子项：直接 fail
    manual_bag = Bag(ctx.max_findings)  # 缩写连写等启发式子项：manual
    for ci in ctx.classes():
        rel = ctx.rel(ci.path)
        masked = J.mask_source(_read(ci.path))
        # 1) 包名全小写
        _check_package_name(masked, rel, bag)
        # 2) 类型名 UpperCamelCase 且非单字母——覆盖**全部类型声明**（含嵌套类型/接口/枚举）
        #    WHY 不只用 ci.name：轻量解析器每个文件只给顶层类型，嵌套 `class badname` 会漏查。
        for _kind, tname, tline, _depth in _all_types(masked):
            if not _UPPER_CAMEL_RE.match(tname) or len(tname) < 2:
                bag.add(rel, tline, "类型名非 UpperCamelCase: %s" % tname)
        # 3) 方法名 lowerCamelCase 且非单字母（跳过构造器 / 与类同名的构造器 / 全大写枚举常量）
        for m in ci.methods:
            if m.is_constructor or m.name == ci.name:
                continue
            # 枚举常量（UPPER_SNAKE）会被轻量解析器误当方法名，全大写名一律跳过
            if re.match(r"^[A-Z][A-Z0-9_]*$", m.name):
                continue
            # 单字母方法名（如 `void a()`）与顶层类型同口径：先于 lowerCamelCase 判定，给专门证据
            if len(m.name) < 2:
                bag.add(rel, m.decl_line, "方法名单字母: %s" % m.name)
            elif not _LOWER_CAMEL_RE.match(m.name):
                bag.add(rel, m.decl_line, "方法名非 lowerCamelCase: %s" % m.name)
        # 4) static final 常量名 UPPER_SNAKE_CASE（豁免 log/logger 与 serialVersionUID）
        for fm in _STATIC_FINAL_FIELD_RE.finditer(masked):
            name = fm.group(1)
            if name.lower() in ("log", "logger", "serialversionuid"):
                continue
            if not _UPPER_SNAKE_RE.match(name):
                bag.add(rel, _line_of(masked, fm.start()),
                        "常量名非 UPPER_SNAKE_CASE: %s" % name)
        # 5) 泛型形参命名：类型级（class/interface/enum）与方法级均须为单个大写字母
        for gm in _GENERIC_PARAM_RE.finditer(masked):
            _check_type_params(gm.group(1), rel, _line_of(masked, gm.start()), bag)
        for m in ci.methods:
            tm = _METHOD_TYPE_PARAM_RE.match(J.strip_annotations(m.sig or ""))
            if tm:
                _check_type_params(tm.group(1), rel, m.decl_line, bag)
        # 6) 缩写连写 >3 连续大写（整词大写常量跳过；常见缩写豁免）→ 启发式候选
        for im in _IDENT_RE.finditer(masked):
            ident = im.group(0)
            if ident.isupper():
                continue
            for run in _ABBREV_RUN_RE.findall(ident):
                if not _unallowed_abbrev_run(run):
                    continue
                manual_bag.add(rel, _line_of(masked, im.start()),
                               "疑似缩写连写: %s（连续大写 %s）" % (ident, run))
                break
    if bag.total:
        note = "命名违规 %d 处（包名/类型名/方法名/常量名/泛型形参）" % bag.total
        if manual_bag.total:
            note += "；另含 %d 处疑似缩写连写候选（启发式）" % manual_bag.total
        return Item(39, CHECK_NAMES[39], STATUS_FAIL, note,
                    _merge_hints(bag, manual_bag, ctx.max_findings))
    if manual_bag.total:
        return Item(39, CHECK_NAMES[39], STATUS_MANUAL,
                    "可靠命名项通过；%d 处疑似缩写连写（>3 连续大写）需人工核对"
                    % manual_bag.total, manual_bag.items)
    return Item(39, CHECK_NAMES[39], STATUS_PASS, "命名大小写/形式符合规范")


def _javadoc_above(lines, decl_idx0):
    """返回声明上方紧邻的 Javadoc 原文（``/** ... */``）；无则 ``None``。

    WHY 返回原文而不只判存在：JavadocType 类规则还要核对**标签**（如泛型类型的
    ``@param <T>``），只判「有没有 Javadoc」覆盖不到这部分口径。
    WHY 用「最后一个 Javadoc 块 + 其后仅剩注解/空白」判定：注解常跨多行
    （``@FeignClient(name=...,`` 换行 ``configuration=...)``），逐行上跳会中断。
    注意此处取**原文**块——不能先 ``strip_annotations``，否则 Javadoc 里的
    ``@param``/``@return`` 会被当作注解删掉。
    """
    if decl_idx0 <= 0:
        return None
    head = "\n".join(lines[:decl_idx0]).rstrip()
    if not head:
        return None
    blocks = re.findall(r"/\*\*.*?\*/", head, re.S)
    if not blocks:
        return None
    last = blocks[-1]
    tail = head[head.rfind(last) + len(last):]
    if J.strip_annotations(tail).strip():
        return None                # Javadoc 与声明之间还有其它代码 → 不是紧邻
    return last


def _has_javadoc_above(lines, decl_idx0):
    """判断 0-based 行索引上方是否紧邻 ``/** ... */``。"""
    return _javadoc_above(lines, decl_idx0) is not None


# 泛型类型形参的 Javadoc 标签（JavadocType 口径：缺 `@param <T>` 即不合规）
_PARAM_TAG_RE = re.compile(r"@param\s+<([A-Za-z_$][\w$]*)>")


def _type_params(masked, name):
    """取类型声明 ``class/interface/enum/record Name<T, U>`` 的形参名列表。"""
    m = re.search(r"\b(?:class|interface|enum|record)\s+%s\s*<\s*([^<>]+?)\s*>"
                  % re.escape(name), masked)
    if not m:
        return []
    out = []
    for part in m.group(1).split(","):
        toks = _LAMBDA_IDENT_RE.findall(part)
        if toks:
            out.append(toks[0])
    return out


def check_40(ctx):
    """#40 类与文件结构：package 声明与目录、单一顶层类型、类型 Javadoc。

    可靠子项（fail）：缺 package、多顶层类型、顶层类型缺 Javadoc。
    提示子项（manual）：嵌套类型缺 Javadoc、package 与目录不一致——两者在主流静态检查
    中属 warning 级，且受扫描路径写法（相对/绝对、扫描子目录）影响，故只列候选不判失败。
    """
    bag = Bag(ctx.max_findings)
    manual_bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        # module-info.java 本就没有 package/top-level 类型，跳过避免误报
        if os.path.basename(f) == "module-info.java":
            continue
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        lines = J.read_lines(f)
        if not _PACKAGE_RE.search(masked):
            bag.add(rel, 1, "缺少 package 声明")
        types = _top_level_types(masked)
        if len(types) > 1:
            bag.add(rel, types[1][2], "存在多个顶层类型声明（如 %s）" % types[1][1])
        for _kind, name, line in types:
            if not _has_javadoc_above(lines, line - 1):
                bag.add(rel, line, "顶层类型缺 Javadoc: %s" % name)
        for _kind, name, line, depth in _all_types(masked):
            doc = _javadoc_above(lines, line - 1)
            if doc is None:
                if depth > 0:
                    manual_bag.add(rel, line, "嵌套类型缺 Javadoc: %s" % name)
                continue
            # 已有 Javadoc 时核对泛型类型形参标签（JavadocType 口径）
            missing = [t for t in _type_params(masked, name)
                       if t not in set(_PARAM_TAG_RE.findall(doc))]
            if missing:
                manual_bag.add(rel, line, "Javadoc 缺类型形参标签 @param <%s>: %s"
                               % ("> <".join(missing), name))
        _check_package_dir(rel, masked, manual_bag)
    if bag.total:
        note = "类与文件结构问题 %d 处" % bag.total
        if manual_bag.total:
            note += "；另含 %d 处嵌套类型 Javadoc / package 目录一致性候选（启发式）" \
                    % manual_bag.total
        return Item(40, CHECK_NAMES[40], STATUS_FAIL, note,
                    _merge_hints(bag, manual_bag, ctx.max_findings))
    if manual_bag.total:
        return Item(40, CHECK_NAMES[40], STATUS_MANUAL,
                    "可靠项通过；%d 处嵌套类型 Javadoc / package 目录一致性候选需人工核对"
                    % manual_bag.total, manual_bag.items)
    return Item(40, CHECK_NAMES[40], STATUS_PASS,
                "均有 package 声明、单一顶层类型且带 Javadoc")


# JLS 建议的修饰符顺序（仅列可共存的常见修饰符）
_MODIFIER_ORDER = ("public", "protected", "private", "abstract", "default",
                   "static", "final", "transient", "volatile", "synchronized",
                   "native", "strictfp")
_MOD_INDEX = {name: i for i, name in enumerate(_MODIFIER_ORDER)}
_MODIFIER_RUN_RE = re.compile(
    r"(?:\b(?:%s)\b[ \t\r\n]+){2,}" % "|".join(_MODIFIER_ORDER))
# C 风格数组声明 `Type name[]`：Type 须是「基本类型」或「首字母大写的类/泛型名」，
# name 须是 lowerCamelCase 标识符。这样 `String[] a`（正确）与 `new String[]{...}`（正确）
# 都不会命中，只有 `String a[]` 形态才命中。
_PRIMITIVE_TYPE_ALT = r"(?:byte|short|int|long|float|double|char|boolean)"
_TYPE_REF_ALT = (r"(?:%s|[A-Z][\w$]*(?:\.[A-Z][\w$]*)*"
                 r"(?:\s*<[^;{}()]*>)?)" % _PRIMITIVE_TYPE_ALT)
_C_STYLE_ARRAY_RE = re.compile(
    r"\b(%s)\s+([a-z_$][\w$]*)\s*\[\s*\]" % _TYPE_REF_ALT)
_LONG_SUFFIX_L_RE = re.compile(r"\b\d[\d_]*l\b")
_PRINT_STACK_RE = re.compile(r"\.\s*printStackTrace\s*\(\s*\)")


def _match_brace(masked, open_pos):
    """给定 '{' 偏移返回匹配 '}' 偏移；找不到返回 -1。"""
    depth = 0
    i = open_pos
    n = len(masked)
    while i < n:
        c = masked[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _direct_stmts(body):
    """产出类型体内「直接成员」语句 (offset_in_body, text)：嵌套大括号深度 0 的 ';' 结尾段。"""
    depth = 0
    start = 0
    for i, ch in enumerate(body):
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
            if depth == 0:
                start = i + 1
        elif ch == ";" and depth == 0:
            yield start, body[start:i]
            start = i + 1


_INTERFACE_DECL_RE = re.compile(r"\binterface\s+[A-Za-z_$][\w$]*")


def _interface_bodies(masked):
    """产出全部 interface 体（含**嵌套接口**、注解类型）的 (body_start, body_text)。

    WHY 不只取第一个 interface：接口常嵌在类里（如内部契约接口），只判顶层接口会把
    其中显式 ``public`` 方法、``static final`` 常量的冗余修饰符整片漏掉（实测漏报）。
    """
    for m in _INTERFACE_DECL_RE.finditer(masked):
        open_pos = masked.find("{", m.end())
        if open_pos < 0:
            continue
        close_pos = _match_brace(masked, open_pos)
        if close_pos < 0:
            continue
        yield open_pos + 1, masked[open_pos + 1:close_pos]


def _interface_modifier_hits(masked):
    """产出接口体内直接成员的冗余修饰符 (偏移, 说明)。

    WHY 偏移要对准「语句首个非空白字符」：段文本含 `{` 之后的换行/缩进/注释，
    直接用段起点会把行号报到接口声明那一行（实测行号错位、对不上静态检查输出）。
    """
    for base, body in _interface_bodies(masked):
        for off, stmt in _direct_stmts(body):
            s = stmt.strip()
            if not s:
                continue
            pos = base + off + (len(stmt) - len(stmt.lstrip()))
            if re.search(r"\bstatic\b", s) and re.search(r"\bfinal\b", s):
                yield pos, "接口常量冗余修饰符 static final"
            elif re.search(r"\bpublic\b", s):
                if "(" in s:
                    yield pos, "接口方法冗余修饰符 public"
                else:
                    yield pos, "接口字段冗余修饰符 public"


def _depth0_text(body):
    """把 body 中「非直接成员」的内容（嵌套大括号及其内部）置为空格。

    用于只在类型体的直接成员层做正则匹配——嵌套类/方法体里的同名修饰符不应被计入。
    """
    out = list(body)
    depth = 0
    for i, ch in enumerate(body):
        if ch == "{":
            depth += 1
            out[i] = " "
        elif ch == "}":
            if depth > 0:
                depth -= 1
            out[i] = " "
        elif depth > 0:
            out[i] = " "
    return "".join(out)


_FINAL_CLASS_RE = re.compile(r"\bfinal\s+class\s+[A-Za-z_$][\w$]*")
# final 类直接成员里的 final 方法（`public final void m(...)`）；`final 变量 = foo(...)` 因含 `=` 不会命中
_FINAL_METHOD_RE = re.compile(
    r"(?:\b(?:public|protected|private|static|synchronized|native|abstract)\s+)*"
    r"\bfinal\s+(?!class\b)[\w.$<>\[\],\s?]*?\s+([A-Za-z_$][\w$]*)\s*\(")


def _final_class_method_hits(masked):
    """产出「final 类中的 final 方法」偏移（覆盖文件内全部 final 类，含多个顶层类）。"""
    for m in _FINAL_CLASS_RE.finditer(masked):
        open_pos = masked.find("{", m.end())
        if open_pos < 0:
            continue
        close_pos = _match_brace(masked, open_pos)
        if close_pos < 0:
            continue
        body = masked[open_pos + 1:close_pos]
        flat = _depth0_text(body)
        for fm in _FINAL_METHOD_RE.finditer(flat):
            yield open_pos + 1 + fm.start()


def check_41(ctx):
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        # 1) 修饰符顺序（同一修饰符串内的相对顺序须为 JLS 建议顺序）
        for m in _MODIFIER_RUN_RE.finditer(masked):
            tokens = re.findall(r"\b\w+\b", m.group(0))
            idxs = [_MOD_INDEX[t] for t in tokens if t in _MOD_INDEX]
            if any(idxs[i] > idxs[i + 1] for i in range(len(idxs) - 1)):
                bag.add(rel, _line_of(masked, m.start()),
                        "修饰符顺序不规范: %s" % " ".join(tokens))
        # 2) C 风格数组声明（int a[]）
        for m in _C_STYLE_ARRAY_RE.finditer(masked):
            bag.add(rel, _line_of(masked, m.start()),
                    "C 风格数组声明: %s[]" % m.group(1))
        # 3) 小写 l 长整型后缀（应为大写 L）
        for m in _LONG_SUFFIX_L_RE.finditer(masked):
            bag.add(rel, _line_of(masked, m.start()),
                    "长整型后缀小写 l（应为大写 L）: %s" % m.group(0))
        # 4) printStackTrace() 调用
        for m in _PRINT_STACK_RE.finditer(masked):
            bag.add(rel, _line_of(masked, m.start()), "调用了 printStackTrace()")
    # 5) 冗余修饰符：接口（含**嵌套接口**）方法显式 public、字段显式 static final / public
    #    WHY 改为纯文本扫描全部 interface 体：`ctx.classes()` 每个文件只给顶层类型，
    #    类内部的契约接口会被整片漏掉（实测漏报）。嵌套 class/enum 的成员由 _direct_stmts
    #    的括号深度过滤排除，不会误判为接口成员。
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        for off, detail in _interface_modifier_hits(masked):
            bag.add(rel, _line_of(masked, off), detail)
    # 6) final 类中的 final 方法：final 类不可被继承，方法再加 final 属多余修饰符
    #    WHY 改为纯文本扫描全部 final 类：`ctx.classes()` 每文件只给顶层类型，
    #    文件内第二个顶层类（或嵌套 final 类）会被漏掉（实测漏报）。
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        for pos in _final_class_method_hits(masked):
            bag.add(rel, _line_of(masked, pos), "final 类中方法冗余修饰符 final")
    if bag.total:
        return Item(41, CHECK_NAMES[41], STATUS_FAIL,
                    "书写卫生问题 %d 处" % bag.total, bag.items)
    return Item(41, CHECK_NAMES[41], STATUS_PASS,
                "修饰符顺序/冗余修饰符/数组写法/长整型后缀/printStackTrace 均正常")


_COMPARE_OP_RE = re.compile(r"[!=]=")
_EQUALS_NON_LITERAL_RE = re.compile(
    r"([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\.\s*equals\s*\(\s*\"")
_STRISH_NAME = r"(?:[A-Za-z_$][\w$]*(?:Str|String|Name|Code|Type|Status|Msg|Text))"
_STRISH_CMP_LEFT_RE = re.compile(
    r"\b" + _STRISH_NAME + r"\b\s*(?:==|!=)\s*(?!(?:null|true|false)\b)[A-Za-z_$\"]")
_STRISH_CMP_RIGHT_RE = re.compile(
    r"[A-Za-z_$\"]\s*(?:==|!=)\s*\b" + _STRISH_NAME + r"\b")
# 限定常量形态：`Type.CONST`（项目内枚举、跨模块枚举、常量类均属此类）
_ENUM_QUALIFIED_AFTER_RE = re.compile(r"\s*([A-Z][\w$]*)\s*\.\s*[A-Z][A-Z0-9_]*\b")
_ENUM_QUALIFIED_BEFORE_RE = re.compile(r"\b([A-Z][\w$]*)\s*\.\s*[A-Z][A-Z0-9_]*\s*$")
# 裸常量形态：`UPPER_SNAKE`（≥2 字符）
_BARE_CONST_AFTER_RE = re.compile(r"\s*[A-Z][A-Z0-9_]{1,}\b")
_BARE_CONST_BEFORE_RE = re.compile(r"\b[A-Z][A-Z0-9_]{1,}\s*$")
# 声明形态 `EnumType varName`（用于识别"变量本身就是枚举"）
_ENUM_VAR_DECL_RE = re.compile(r"\b([A-Za-z_$][\w$]*)\s+([a-z_$][\w$]*)\s*(?=[=;,)\]])")
_OP_IN_TEXT_RE = re.compile(r"[!=]=")


def _enum_type_names(ctx):
    """项目内全部枚举类型名（#42 用于排除枚举比较）。"""
    return set(ci.name for ci in ctx.classes() if ci.kind == "enum" and ci.name)


def _enum_var_names(masked, enum_types):
    """收集声明类型为「项目内枚举」的变量名。"""
    if not enum_types:
        return frozenset()
    out = set()
    for m in _ENUM_VAR_DECL_RE.finditer(masked):
        if m.group(1) in enum_types:
            out.add(m.group(2))
    return out


def _is_enum_comparison(masked, op_start, op_end, enum_types, enum_vars):
    """判断该 ``==``/``!=`` 是否属于「常量/枚举比较」（应排除，不算字符串比较）。

    WHY: 枚举与常量用 ``==`` 比较是 Java 推荐写法，但 #42 的"名字像字符串"启发式会把
    ``orderStatus == DemoStatus.OK``、``completionStatus == TransactionSynchronization.STATUS_X``
    误判为字符串比较。排除三类：``Type.CONST`` 限定常量、裸 ``UPPER_SNAKE`` 常量、
    以及声明类型为项目内枚举的变量。
    """
    after = masked[op_end:op_end + 96]
    before = masked[max(0, op_start - 96):op_start]
    if _ENUM_QUALIFIED_AFTER_RE.match(after) or _ENUM_QUALIFIED_BEFORE_RE.search(before):
        return True
    if _BARE_CONST_AFTER_RE.match(after) or _BARE_CONST_BEFORE_RE.search(before):
        return True
    if not enum_types:
        return False
    left = re.search(r"([A-Za-z_$][\w$]*)\s*$", before)
    right = re.match(r"\s*([A-Za-z_$][\w$]*)", after)
    for tok in (left.group(1) if left else None, right.group(1) if right else None):
        if tok and tok in enum_vars:
            return True
    return False


def check_42(ctx):
    bag = Bag(ctx.max_findings)         # 明确命中：字符串字面量用 == / !=
    manual_bag = Bag(ctx.max_findings)  # 启发式候选：常量未前置的 equals / 疑似字符串 ==
    enum_types = _enum_type_names(ctx)
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        enum_vars = _enum_var_names(masked, enum_types)
        # 1) 明确命中：== / != 任一侧紧邻字符串字面量
        for m in _COMPARE_OP_RE.finditer(masked):
            li = m.start() - 1
            while li >= 0 and masked[li] in " \t":
                li -= 1
            ri = m.end()
            while ri < len(masked) and masked[ri] in " \t":
                ri += 1
            left = masked[li] if li >= 0 else ""
            right = masked[ri] if ri < len(masked) else ""
            if left == '"' or right == '"':
                bag.add(rel, _line_of(masked, m.start()),
                        "字符串字面量用 %s 比较（应 equals）" % m.group(0))
        # 2) 启发式：常量未前置的 equals（接收者非字面量）
        for m in _EQUALS_NON_LITERAL_RE.finditer(masked):
            manual_bag.add(rel, _line_of(masked, m.start()),
                           "equals 常量未前置（接收者非字面量）: %s.equals(...)" % m.group(1))
        # 3) 启发式：疑似字符串用 == / != 比较（名字含 Str/String/Name/...；排除枚举比较）
        for regex in (_STRISH_CMP_LEFT_RE, _STRISH_CMP_RIGHT_RE):
            for m in regex.finditer(masked):
                op = _OP_IN_TEXT_RE.search(m.group(0))
                if op is None:
                    continue
                if _is_enum_comparison(masked, m.start() + op.start(),
                                       m.start() + op.end(), enum_types, enum_vars):
                    continue
                manual_bag.add(rel, _line_of(masked, m.start()),
                               "疑似字符串 == 比较: %s" % m.group(0).strip())
    if bag.total:
        note = "明确的字符串比较问题 %d 处" % bag.total
        if manual_bag.total:
            note += ("；另含 %d 处候选（常量未前置的 equals / 疑似字符串 ==）"
                     % manual_bag.total)
        return Item(42, CHECK_NAMES[42], STATUS_FAIL, note,
                    _merge_hints(bag, manual_bag, ctx.max_findings))
    if manual_bag.total:
        return Item(42, CHECK_NAMES[42], STATUS_MANUAL,
                    "%d 处疑似字符串比较需人工核对（启发式，已排除项目内枚举比较）"
                    % manual_bag.total, manual_bag.items)
    return Item(42, CHECK_NAMES[42], STATUS_PASS,
                "未发现字符串用 == 比较或常量未前置的 equals（枚举比较不计入）")


# 只认「注释里的」TODO/FIXME：// 注释、/* 块、块注释续行、以及紧跟注释起始的标记
_LEGACY_MARK_RE = re.compile(
    r"(?:"
    r"//[^\n]*?"
    r"|/\*+[^\n]*?"
    r"|^[ \t]*\*[^\n]*?"
    r"|^[ \t]*"
    r")\b(TODO|FIXME)\b", re.M)
_LAX_TODO_CONVERGENCE_RE = re.compile(r"^\s*\(\s*收敛\s*\)")


def check_43(ctx):
    """#43 遗留标记：TODO/FIXME 应清理，仅「显式抑制注释」可豁免。

    WHY 不再整体豁免 ``// TODO(收敛)``：主流静态检查的 TODO 规则按字面 ``TODO|FIXME``
    匹配，任何前后缀写法都会被计入；若继续豁免，交付到静态检查侧仍会报出，属漏报。
    现改为：``// TODO(收敛)`` 降级为 warn 提示（说明其仍会被静态检查计入），
    真正的豁免只有静态检查通行的抑制注释（见 :func:`_suppression_lines`）。
    """
    bag = Bag(ctx.max_findings)
    warn_bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        text = _read(f)
        suppressed = _suppression_lines(text, "TodoComment")
        for m, line in _finditer_pos(_LEGACY_MARK_RE, text):
            if line in suppressed:
                continue
            tag = m.group(1)
            after = text[m.end(1):m.end(1) + 16]
            if tag == "TODO" and _LAX_TODO_CONVERGENCE_RE.match(after):
                warn_bag.add(ctx.rel(f), line,
                             "// TODO(收敛) 为项目约定标记，但静态检查的 TODO 规则不豁免，"
                             "交付前应清理或改注 checkstyle:ignore TodoComment")
                continue
            bag.add(ctx.rel(f), line, "遗留标记 %s（应清理）" % tag)
    if bag.total:
        return Item(43, CHECK_NAMES[43], STATUS_FAIL,
                    "发现 %d 处 TODO/FIXME 遗留标记" % bag.total, bag.items)
    if warn_bag.total:
        return Item(43, CHECK_NAMES[43], STATUS_WARN,
                    "%d 处 // TODO(收敛) 约定标记：静态检查侧仍会报出，建议清理"
                    % warn_bag.total, warn_bag.items)
    return Item(43, CHECK_NAMES[43], STATUS_PASS, "无 TODO/FIXME 遗留标记")


# ---------------------------------------------------------------------------
# 组八：变量命名（#44，启发式，标准/存量两模式均执行）
# ---------------------------------------------------------------------------

# Java 关键字 + 字面量 + 上下文关键字：出现在"类型位"时一律不算声明类型
_JAVA_KEYWORDS = frozenset("""
abstract assert boolean break byte case catch char class const continue default
do double else enum extends final finally float for goto if implements import
instanceof int interface long native new package private protected public return
short static strictfp super switch synchronized this throw throws transient try
void volatile while true false null record var sealed permits yield
""".split())
# 可作为合法"类型位"的关键字（基本类型 + var），不阻断候选发现
_PRIMITIVE_TYPES = frozenset(
    ("boolean", "byte", "char", "short", "int", "long", "float", "double", "var"))
# 变量声明/形参：TYPE NAME，name 后接 = ; , ) : ]（兼容泛型/数组/可变参数）
# WHY 类型与变量名之间必须是空白（`\s+` 而非 `\s*`）：Java 声明中二者总有空白，
# 放宽后会把限定字段访问误切为声明——如 ``java.nio.charset.StandardCharsets.UTF_8``
# 被切成 ``UTF`` + ``_8``，凭空产生「变量名 ``_8`` 不合规」的误报。
_VAR_DECL_RE = re.compile(
    r"(?:[A-Za-z_$][\w$]*\.)*([A-Za-z_$][\w$]*)"
    r"(?:\s*<[^;{}()]*>)?(?:\s*\[\s*\])*"
    r"\s+(?:\.\.\.\s*)?([A-Za-z_$][\w$]*)\s*(?=[=;,):\]])")
_LAMBDA_ARROW_RE = re.compile(r"->")
_LAMBDA_IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")


def _var_name_violates(name, all_upper_violates=False):
    """判断变量/形参名是否明显不符合 lowerCamelCase（含 ``_`` 或首字母大写）。

    ``all_upper_violates=True`` 时**全大写名也算违规**——用于局部 ``final`` 变量与 lambda
    形参：这两处不承载「项目常量」语义，静态检查的命名规则同样要求 lowerCamelCase。
    默认 ``False`` 保持原语义：全大写/UPPER_SNAKE 视为常量，交由 #39 按常量口径核对
    （避免把接口常量 ``int MAX = 1;`` 误报为变量命名违规）。

    跳过：Java 关键字、单字母循环变量（i/j/k、T/E）。
    """
    if not name or name in _JAVA_KEYWORDS:
        return False
    if name.isupper() and not all_upper_violates:
        return False
    if len(name) <= 1:       # 单字母（i/j/k、泛型 T/E 等）允许
        return False
    if name[0].isupper():    # 首字母大写
        return True
    if "_" in name:          # 含下划线
        return True
    return False


def _decl_line_head(masked, pos):
    """返回 ``pos`` 之前的本行文本，用于判断声明的修饰符与上下文。"""
    line_start = masked.rfind("\n", 0, pos) + 1
    return masked[line_start:pos]


def _is_static_final_decl(masked, name_pos):
    """name_pos 所在语句段是否为 ``static final`` 声明（常量，交由 #39 核对）。"""
    head = _decl_line_head(masked, name_pos)
    return bool(re.search(r"\bstatic\b", head) and re.search(r"\bfinal\b", head))


def _match_paren_back(masked, close_pos):
    """给定 ')' 偏移，返回匹配 '(' 偏移；找不到返回 -1。"""
    depth = 0
    i = close_pos
    while i >= 0:
        c = masked[i]
        if c == ")":
            depth += 1
        elif c == "(":
            depth -= 1
            if depth == 0:
                return i
        i -= 1
    return -1


def _param_names(segment):
    """从形参段（逗号分隔）取每段末位标识符作为形参名（兼容带类型/注解写法）。"""
    names = []
    for part in segment.split(","):
        toks = _LAMBDA_IDENT_RE.findall(part)
        if toks:
            names.append(toks[-1])
    return names


def _lambda_params(masked, arrow_pos):
    """返回 lambda 箭头左侧形参名列表（``(a, b) ->`` 或 ``x ->``）；switch 分支跳过。"""
    i = arrow_pos - 1
    while i >= 0 and masked[i] in " \t\r\n":
        i -= 1
    if i < 0:
        return []
    if masked[i] == ")":
        open_pos = _match_paren_back(masked, i)
        if open_pos < 0:
            return []
        return _param_names(masked[open_pos + 1:i])
    m = re.search(r"([A-Za-z_$][\w$]*)\s*$", masked[:i + 1])
    if not m:
        return []
    # switch 表达式分支 `case X ->` / `default ->` 的常量标签不是 lambda 形参
    prefix = masked[:m.start()]
    line_prefix = prefix[prefix.rfind("\n") + 1:]
    if re.search(r"\b(?:case|default)\b[^;{}]*$", line_prefix):
        return []
    return [m.group(1)]


def check_44(ctx):
    """#44 变量命名（启发式）：成员/局部/形参/lambda 变量须 lowerCamelCase。

    启发式项——发现候选一律记 ``manual`` 附证据，**绝不自动 fail**；无候选记 ``pass``。
    """
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        # 1) 有类型的声明/形参：TYPE NAME（基本类型允许，其余关键字类型位排除）
        for m in _VAR_DECL_RE.finditer(masked):
            type_tok = m.group(1)
            name = m.group(2)
            if type_tok in _JAVA_KEYWORDS and type_tok not in _PRIMITIVE_TYPES:
                continue
            head = _decl_line_head(masked, m.start(2))
            if re.search(r"\b(?:import|package)\b", head):
                continue          # import/package 里的限定名不是变量声明
            if _is_static_final_decl(masked, m.start(2)):
                continue          # static final 常量 → #39 按 UPPER_SNAKE 核对
            # 局部 final 变量不承载「项目常量」语义：全大写同样是命名违规
            local_final = bool(re.search(r"\bfinal\b", head))
            if not _var_name_violates(name, all_upper_violates=local_final):
                continue
            bag.add(rel, _line_of(masked, m.start(2)),
                    "疑似变量命名非 lowerCamelCase: %s" % name)
        # 2) 无类型 lambda 形参：x ->  /  (a, b) ->（形参不可能是常量，全大写同样违规）
        for am in _LAMBDA_ARROW_RE.finditer(masked):
            for name in _lambda_params(masked, am.start()):
                if not _var_name_violates(name, all_upper_violates=True):
                    continue
                bag.add(rel, _line_of(masked, am.start()),
                        "疑似 lambda 形参命名非 lowerCamelCase: %s" % name)
    if bag.total:
        return Item(44, CHECK_NAMES[44], STATUS_FAIL,
                    "%d 处变量命名非 lowerCamelCase（含 `_` 或首字母大写）"
                    % bag.total, bag.items)
    return Item(44, CHECK_NAMES[44], STATUS_PASS,
                "变量命名均为 lowerCamelCase")


# ---------------------------------------------------------------------------
# 组九：缩进 / import 顺序 / 方法规模 / equals-hashCode（#45~#49）
#
# 规则口径对齐 Checkstyle 10.x（Indentation / ImportOrder / MethodLength /
# ParameterNumber / EqualsHashCode）；实现为本项目原创，未复制其代码或文档。
# ---------------------------------------------------------------------------

_INDENT_UNIT = 4
# 续行相对「语句起始行」的缩进量（对齐工具类 Indentation 的 lineWrappingIndentation）；
# 实测该工具续行默认 forceStrictCondition=false → 只报「少于期望」，超出不报
_CONT_INDENT = 8
# switch 分支标签相对 switch 语句起始行的缩进量（caseIndent）；实测为严格判定（多/少都报）
_CASE_INDENT = 4
# 数组初始化元素相对初始化起始行的缩进量（arrayInitIndent）；实测该工具接受的是一组（+4 或 +8）
_ARRAY_INIT_INDENT = 4
_ARRAY_INIT_INDENT_ALTS = (_ARRAY_INIT_INDENT, 2 * _ARRAY_INIT_INDENT)
# 续行判定：本行以这些 token 开头，或上一非空行以这些 token 结尾 → 视为续行，
# 其缩进允许对齐（不要求 4 的倍数），避免流式调用/长表达式的正常对齐被误报。
_CONT_HEAD_RE = re.compile(r"^\s*(?:[.,)\]]|&&|\|\||\+|\?|:)")
_CONT_TAIL_RE = re.compile(r"(?:[(\[,=+]|&&|\|\||->|\.)\s*$")
# 语句起始行以这些运算符结尾，说明表达式尚未写完，其后的「尾 token 续行」才可信
_CONT_TAIL_OP_RE = re.compile(r"(?:=|\+|\|\||&&|->|\.)$")
# 参与「未配对左括号」统计的字符
_OPEN_BRACKETS = "([{"
# 枚举常量声明：常量名（UPPER_SNAKE）后紧跟参数表 `(`、或作为最后一个常量以 `,`/`;` 收尾。
# WHY 不含 `{`：带类体的枚举常量（`A { ... }`）大括号内的成员仍应按常规判定续行缩进。
_ENUM_CONST_STMT_RE = re.compile(r"^\s*[A-Z][A-Z0-9_]*\s*[(,;]")


def _is_continuation(prev_line, cur_line):
    """判断 cur_line 是否为上一行语句的续行（启发式）。"""
    s = cur_line.strip()
    if not s:
        return False
    if _CONT_HEAD_RE.match(s):
        return True
    return bool(_CONT_TAIL_RE.search(prev_line.rstrip()))


def _line_indent(line):
    """返回一行文本的前导空格数（Tab 不计入，交由 #34 单独核对）。"""
    return len(line) - len(line.lstrip(" "))


def _open_bracket_balance(text):
    """统计一行内未配对的左括号数（``(``/``[``/``{`` 计 +1，右括号计 -1，**下限 0**）。

    WHY 下限 0：该函数用于「单行自平衡」判定（如 ``foo(a, b)`` 计 0），供语句起始行取初值。
    若用于跨行滚动累加，必须改用 :func:`_bracket_delta`——本函数把「闭合上一行括号」压成 0，
    会让滚动值只增不减。
    """
    depth = 0
    for ch in text:
        if ch in _OPEN_BRACKETS:
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
    return depth


def _bracket_delta(text):
    """一行的括号**净增减**（``(``/``[``/``{`` 各 +1，``)``/``]``/``}`` 各 -1），不夹断下限。

    WHY 需要它：跨行滚动统计语句的括号深度时，「闭合上一行打开的括号」必须记成 ``-1``；
    若沿用 :func:`_open_bracket_balance`（下限 0）则该行记 0，深度只增不减，导致折行语句
    结束后仍被当作「括号未闭合」，其后每一行都被误判为续行。
    """
    delta = 0
    for ch in text:
        if ch in _OPEN_BRACKETS:
            delta += 1
        elif ch in ")]}":
            delta -= 1
    return delta


def _continuation_indent_hits(masked_lines):
    """产出 (行号, 说明)——续行缩进**少于**「语句起始行 + ``_CONT_INDENT``」的行。

    WHY 只报「少于」：``lineWrappingIndentation`` 实测默认 ``forceStrictCondition=false``，
    续行缩进**大于**期望值不报，只有小于期望才报；故 ``==`` 与 ``>`` 一律放行。

    WHY 只覆盖高置信形态：``lineWrappingIndentation`` 只约束「续行」，前提是能可靠识别续行与
    所属语句起始行。因此只认两类：① 本行以 ``.``/``)``/``]``/``,``/``+``/``&&``/``||``/``?``/``:``
    开头（运算符前置折行）；② 上一非空行以 ``(``/``[``/``,`` 结尾且当前语句仍有未配对左括号，
    或以 ``=``/``+``/``&&``/``||``/``->``/``.`` 结尾。无法确定「语句起始行」的形态一律不报，
    避免制造噪音。

    WHY 跳过枚举常量参数折行：实测外部真实 Checkstyle 对「枚举常量参数折行」完全不做
    ``lineWrappingIndentation`` 判定——常量 ``A(1, "x",`` 的续行缩进为 +0 / +4 / +12 均不报；
    故语句起始行命中 :data:`_ENUM_CONST_STMT_RE` 时，该语句的续行一律不产出候选
    （滚动括号/运算符状态照常推进，不影响后续语句）。
    """
    hits = []
    prev_code = None       # 上一非空（掩码后）行，注释行在掩码后即为空白，天然跳过
    stmt_indent = None     # 当前语句起始行缩进
    stmt_open = 0          # 当前语句「滚动」未配对左括号数（每行推进，非起始行冻结值）
    stmt_tail_op = False   # 上一行是否以「表达式未写完」的运算符结尾（每行推进）
    skip_stmt = False      # 当前语句是否为「枚举常量声明」→ 其续行不判定缩进
    for idx, line in enumerate(masked_lines):
        if not line.strip():
            continue
        indent = _line_indent(line)
        head_cont = bool(_CONT_HEAD_RE.match(line))
        tail_cont = bool(prev_code is not None
                         and _CONT_TAIL_RE.search(prev_code.rstrip()))
        is_cont = head_cont or (tail_cont
                                and not prev_code.strip().startswith("@")
                                and (stmt_open > 0 or stmt_tail_op))
        if not is_cont:
            stmt_indent = indent
            stmt_open = _open_bracket_balance(line)
            stmt_tail_op = bool(_CONT_TAIL_OP_RE.search(line.rstrip()))
            skip_stmt = bool(_ENUM_CONST_STMT_RE.match(line))
        else:
            # WHY 必须「滚动」推进括号计数，不能沿用语句起始行的冻结值：枚举常量以 `,` 分隔
            # （不是 `;`），形如 `A(1, "x",\n    "y"),` 的折行常量要到第二行才配平括号。
            # 若沿用起始行冻结的 `stmt_open=1`，其后每一个枚举常量都会被判成「上一句的续行」，
            # 逐行误报（实测 MallExceptionEnum.java 一个文件即误报 243 处）。
            # 滚动配平后括号归零即视为语句结束，下一行重新作为语句起始行，误报消除。
            stmt_open = max(0, stmt_open + _bracket_delta(line))
            stmt_tail_op = bool(_CONT_TAIL_OP_RE.search(line.rstrip()))
            if (not skip_stmt and stmt_indent is not None
                    and indent - stmt_indent < _CONT_INDENT):
                hits.append((idx + 1,
                             "续行缩进 %d 不足（语句起始行缩进 %d，应至少 +%d，即缩进 ≥ %d）"
                             % (indent, stmt_indent, _CONT_INDENT,
                                stmt_indent + _CONT_INDENT)))
        prev_code = line
    return hits


def _case_indent_hits(masked, masked_lines):
    """产出 (行号, 说明)——``case``/``default`` 相对 ``switch`` 起始行缩进非 ``_CASE_INDENT``。

    只在 ``switch (...) { ... }`` 的**直接大括号层**（相对深度 1）识别标签，嵌套块内的
    ``case`` 不参与；标签与 ``switch`` 同行（单行写法）时跳过，避免误报。
    """
    hits = []
    n = len(masked)
    for m in re.finditer(r"\bswitch\b\s*\(", masked):
        close = _match_paren(masked, m.end() - 1)
        if close < 0:
            continue
        j = close + 1
        while j < n and masked[j] in " \t\r\n":
            j += 1
        if j >= n or masked[j] != "{":
            continue                    # 非块状 switch（语法上少见），不判
        depth = 0
        body_end = None
        k = j
        while k < n:
            ch = masked[k]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    body_end = k
                    break
            k += 1
        if body_end is None:
            continue
        switch_line = _line_of(masked, m.start())
        switch_indent = _line_indent(masked_lines[switch_line - 1])
        depth = 0
        k = j
        for lm in re.finditer(r"\b(?:case|default)\b", masked[j:body_end]):
            pos = j + lm.start()
            while k < pos:
                if masked[k] == "{":
                    depth += 1
                elif masked[k] == "}":
                    depth -= 1
                k += 1
            if depth != 1:
                continue
            label_line = _line_of(masked, pos)
            if label_line == switch_line:
                continue                # `case 1: ...` 与 switch 同行，不判
            label_indent = _line_indent(masked_lines[label_line - 1])
            if label_indent - switch_indent != _CASE_INDENT:
                hits.append((label_line,
                             "case/default 缩进 %d 与 switch 起始行 %d 相差 %d"
                             "（应为 +%d，即 %d 空格）"
                             % (label_indent, switch_indent,
                                label_indent - switch_indent, _CASE_INDENT,
                                switch_indent + _CASE_INDENT)))
    return hits


def _array_init_indent_hits(masked, masked_lines):
    """产出 (行号, 说明)——数组初始化元素缩进偏移不在 ``_ARRAY_INIT_INDENT_ALTS`` 内的行。

    WHY 期望值是一组：``arrayInitIndent`` 实测接受 ``+4`` 或 ``+8`` 两种偏移
    （报错原文为「应为以下缩进之一」），且多/少两侧都报，故用「集合成员」判定而非等值判定。

    只识别紧跟在 ``=`` 之后的初始化块（``int[] a = {``），且左花括号后必须换行；
    lambda 体（``() -> {``）、匿名类、``{{`` 双花括号、行内写法一律不报。
    """
    hits = []
    n = len(masked)
    for m in re.finditer(r"=\s*\{", masked):
        open_pos = m.end() - 1
        if open_pos + 1 < n and masked[open_pos + 1] not in "\r\n":
            continue                    # `{` 后同行还有内容 → 行内写法，不判
        depth = 0
        end = -1
        k = open_pos
        while k < n:
            ch = masked[k]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = k
                    break
            k += 1
        if end < 0:
            continue
        open_line = _line_of(masked, open_pos)
        end_line = _line_of(masked, end)
        if end_line <= open_line:
            continue
        base = _line_indent(masked_lines[open_line - 1])
        for idx in range(open_line, end_line - 1):
            line = masked_lines[idx]
            if not line.strip():
                continue
            indent = _line_indent(line)
            offset = indent - base
            if offset not in _ARRAY_INIT_INDENT_ALTS:
                hits.append((idx + 1,
                             "数组初始化元素缩进 %d 与初始化起始行 %d 相差 %d"
                             "（应为 %s 之一，即 %s 空格）"
                             % (indent, base, offset,
                                " 或 ".join("+%d" % a
                                            for a in _ARRAY_INIT_INDENT_ALTS),
                                " 或 ".join("%d" % (base + a)
                                            for a in _ARRAY_INIT_INDENT_ALTS))))
    return hits


# 注解独占一行的写法（成员级注解）
_ANN_LINE_RE = re.compile(r"^[ \t]*@[A-Za-z_$]")
# 成员块起始的上一非空行形态：以 `{`、`;`、`}` 结尾（类型体或语句块开头/前成员结束）
_MEMBER_PREV_OK_RE = re.compile(r"([{;}])\s*$")


def _check_annotation_indent(lines, rel, bag):
    """注解行缩进须与其所注解的成员声明一致。

    WHY: 形如「成员缩进 8 空格、其上的 ``@Schema`` 缩进 4 空格」的写法，缩进量虽是 4 的
    倍数，却与所注解成员错位——这是静态检查缩进规则最常报出的真实缺陷，故单列判定。
    """
    i = 0
    n = len(lines)
    while i < n:
        if not _ANN_LINE_RE.match(lines[i]):
            i += 1
            continue
        k = i - 1
        while k >= 0 and not lines[k].strip():
            k -= 1
        prev = lines[k].strip() if k >= 0 else ""
        if prev and not _MEMBER_PREV_OK_RE.search(prev) \
                and not prev.startswith(("*", "//", "/*")):
            i += 1
            continue          # 形参注解等行内起始注解，不属成员级
        j = i
        depth = 0
        while j < n:
            line = lines[j]
            if depth <= 0 and not _ANN_LINE_RE.match(line):
                break
            depth += line.count("(") - line.count(")")
            j += 1
        if j >= n or not lines[j].strip():
            i += 1
            continue
        if not lines[j - 1].rstrip().endswith(")"):
            i += 1
            continue          # 注解与其成员写在同一行（如 `@X("a") private int a;`）
        decl_indent = len(lines[j]) - len(lines[j].lstrip(" "))
        depth = 0
        for t in range(i, j):
            line = lines[t]
            # 只核对「注解起始行」，跳过注解参数的续行（括号未闭合的行）
            if depth <= 0 and _ANN_LINE_RE.match(line):
                ann_indent = len(line) - len(line.lstrip(" "))
                if ann_indent != decl_indent:
                    bag.add(rel, t + 1, "注解缩进 %d 与所注解成员缩进 %d 不一致"
                            "（应对齐为 %d 空格）" % (ann_indent, decl_indent, decl_indent))
            depth += line.count("(") - line.count(")")
        i = j


def check_45(ctx):
    """#45 缩进一致性：4 空格倍数、注解对齐、续行/case/数组初始化缩进。

    本项为启发式（记 ``manual``），覆盖五类可机械判定、且实际最常出现的缺陷：
    ① 语句起始行缩进非 4 的倍数；② 注解行缩进与所注解成员错位；
    ③ 续行缩进**少于**「语句起始行 + ``_CONT_INDENT``」（超出不报，对齐该工具续行只报不足）；
    **枚举常量参数的折行不在判定范围**（实测该工具对枚举常量参数折行不做 ``lineWrappingIndentation``
    判定，与其缩进量无关）；
    ④ ``case``/``default`` 相对 ``switch`` 起始行缩进非 ``_CASE_INDENT``（严格，多/少都报）；
    ⑤ 数组初始化元素相对初始化起始行缩进不在 ``_ARRAY_INIT_INDENT_ALTS``（即 +4 或 +8）内。
    续行的「相位推进」（嵌套 lambda 内多级折行）不做精确还原：只在能可靠识别续行与语句起始行时
    才报，识别不确定的一律不报，避免制造噪音。
    """
    bag = Bag(ctx.max_findings)
    hard = Bag(ctx.max_findings)
    for f in ctx.java_files:
        rel = ctx.rel(f)
        lines = J.read_lines(f)
        masked_lines = J.mask_source(_read(f)).split("\n")
        masked = "\n".join(masked_lines)
        # WHY 花括号层数只用于证据文案（「第 N 层花括号内」），帮助模型一眼定位应缩进到几级；
        # 用掩码行计数，避免注释/字符串里的花括号干扰；不影响任何判定逻辑。
        depth = 0
        prev = ""
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if not s or s.startswith(("*", "//", "/*")):
                prev = line
                continue
            indent = _line_indent(line)
            if not _is_continuation(prev, line) and indent % _INDENT_UNIT != 0:
                # 期望值 = 向下取整到 4 的倍数（该层花括号应有的缩进）
                want = (indent // _INDENT_UNIT) * _INDENT_UNIT
                layer = "第 %d 层花括号内" % depth if depth else "花括号外（顶层）"
                hard.add(rel, i, "语句起始行缩进 %d 空格（非 %d 的倍数，应为 %d，%s）"
                         % (indent, _INDENT_UNIT, want, layer))
            prev = line
            if i - 1 < len(masked_lines):
                depth += (masked_lines[i - 1].count("{")
                          - masked_lines[i - 1].count("}"))
        _check_annotation_indent(lines, rel, bag)
        # 续行/case/数组初始化三项在掩码文本上识别，注释与字符串内容已被置空，天然跳过
        for line_no, detail in _continuation_indent_hits(masked_lines):
            bag.add(rel, line_no, detail)
        for line_no, detail in _case_indent_hits(masked, masked_lines):
            bag.add(rel, line_no, detail)
        for line_no, detail in _array_init_indent_hits(masked, masked_lines):
            bag.add(rel, line_no, detail)
    if hard.total:
        return Item(45, CHECK_NAMES[45], STATUS_FAIL,
                    "%d 处语句起始行缩进不是 %d 的倍数" % (hard.total, _INDENT_UNIT),
                    _merge_hints(hard, bag, ctx.max_findings))
    if bag.total:
        return Item(45, CHECK_NAMES[45], STATUS_MANUAL,
                    "%d 处缩进疑似不整齐（续行/注解/数组等启发式，需人工核对）"
                    % bag.total, bag.items)
    return Item(45, CHECK_NAMES[45], STATUS_PASS,
                "语句起始行缩进均为 4 空格倍数，注解与成员对齐，续行/case/数组初始化缩进正常")


def _import_group(pkg):
    """#46 import 分组权重：第三方 0 → ``javax`` 1 → ``java``/``jdk``/``sun`` 2。

    口径取自本框架项目实测的多数约定（实测 51 个文件为 javax 在 java 之前、1 个相反），
    与 Checkstyle ``CustomImportOrder`` 的「第三方 → javax → java」常见配置一致。
    """
    if pkg.startswith("javax."):
        return 1
    if pkg.startswith(("java.", "jdk.", "sun.")):
        return 2
    return 0


def check_46(ctx):
    """#46 import 顺序：第三方（组内字典序）→ javax → java，各组内亦按字典序。

    以「相邻逆序」为证据，避免一次刷出整表；static import 不参与排序校验。
    启发式项 → 记 ``manual``。
    """
    bag = Bag(ctx.max_findings)
    for f in ctx.java_files:
        rel = ctx.rel(f)
        seq = []
        for i, line in enumerate(J.read_lines(f), 1):
            m = re.match(r"^\s*import\s+(static\s+)?([\w.]+)\s*;\s*$", line)
            if not m or m.group(1):
                continue
            seq.append((_import_group(m.group(2)), m.group(2), i))
        if len(seq) < 2:
            continue
        for a, b in zip(seq, seq[1:]):
            if (a[0], a[1]) > (b[0], b[1]):
                bag.add(rel, b[2], "import 顺序不规范: %s 应排在 %s 之前"
                        % (b[1], a[1]))
    if bag.total:
        return Item(46, CHECK_NAMES[46], STATUS_FAIL,
                    "%d 处 import 顺序不规范（第三方 → javax → java，各组内字典序）"
                    % bag.total, bag.items)
    return Item(46, CHECK_NAMES[46], STATUS_PASS,
                "import 分组与组内字典序符合约定（第三方 → javax → java）")


_METHOD_LENGTH_LIMIT = 100


def check_47(ctx):
    """#47 方法长度：方法体代码行数 > 100 视为过长（Checkstyle MethodLength 口径）。"""
    bag = Bag(ctx.max_findings)
    for ci in ctx.classes():
        rel = ctx.rel(ci.path)
        for m in ci.methods:
            if not m.has_body():
                continue
            n = m.code_lines()
            if n > _METHOD_LENGTH_LIMIT:
                bag.add(rel, m.decl_line, "方法过长: %s.%s 代码 %d 行（> %d）"
                        % (ci.name, m.name, n, _METHOD_LENGTH_LIMIT))
    if bag.total:
        return Item(47, CHECK_NAMES[47], STATUS_FAIL,
                    "%d 个方法代码行数超过 %d" % (bag.total, _METHOD_LENGTH_LIMIT),
                    bag.items)
    return Item(47, CHECK_NAMES[47], STATUS_PASS,
                "无方法代码行数超过 %d" % _METHOD_LENGTH_LIMIT)


_METHOD_PARAM_LIMIT = 7


def _count_params(sig):
    """从方法签名文本统计顶层逗号分隔的形参个数（0 表示无参）。"""
    text = J.strip_annotations(sig or "")
    m = re.search(r"\(([\s\S]*)\)", text)
    if not m:
        return 0
    inner = m.group(1).strip()
    if not inner:
        return 0
    depth = 0
    count = 1
    for ch in inner:
        if ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
    return count


def check_48(ctx):
    """#48 方法参数个数：形参个数 > 7 视为过多（Checkstyle ParameterNumber 口径）。"""
    bag = Bag(ctx.max_findings)
    for ci in ctx.classes():
        rel = ctx.rel(ci.path)
        for m in ci.methods:
            # 枚举常量带构造实参（如 `OK("成功", 1)`）会被轻量解析器当成方法签名，
            # 其"形参"实为枚举字段值，不属 ParameterNumber 范畴 → 跳过。
            if re.match(r"^[A-Z][A-Z0-9_]*$", m.name):
                continue
            n = _count_params(m.sig)
            if n > _METHOD_PARAM_LIMIT:
                bag.add(rel, m.decl_line, "方法参数过多: %s.%s 共 %d 个（> %d）"
                        % (ci.name, m.name, n, _METHOD_PARAM_LIMIT))
    if bag.total:
        return Item(48, CHECK_NAMES[48], STATUS_FAIL,
                    "%d 个方法形参个数超过 %d" % (bag.total, _METHOD_PARAM_LIMIT),
                    bag.items)
    return Item(48, CHECK_NAMES[48], STATUS_PASS,
                "无方法形参个数超过 %d" % _METHOD_PARAM_LIMIT)


# Lombok 注解：会自动生成 equals/hashCode，无需人工成对
_LOMBOK_EQ_ANNS = frozenset(("Data", "EqualsAndHashCode", "Value"))


def check_49(ctx):
    """#49 equals/hashCode 成对：手写 equals 必须同时手写 hashCode（反之亦然）。

    豁免：枚举/接口（不适用）、record（隐式生成）、带 Lombok
    ``@Data``/``@EqualsAndHashCode``/``@Value`` 的类（由 Lombok 生成）。
    """
    bag = Bag(ctx.max_findings)
    for ci in ctx.classes():
        if ci.kind != "class":
            continue
        if _simple_anns(ci) & _LOMBOK_EQ_ANNS:
            continue
        direct = [m for m in ci.methods if getattr(m, "nested_type_depth", 0) == 0]
        has_eq = any(m.name == "equals" for m in direct)
        has_hc = any(m.name == "hashCode" for m in direct)
        if has_eq == has_hc:
            continue
        rel = ctx.rel(ci.path)
        present = "equals" if has_eq else "hashCode"
        missing = "hashCode" if has_eq else "equals"
        line = next((m.decl_line for m in direct if m.name == present), 1)
        bag.add(rel, line, "重写 %s 但缺少 %s: %s" % (present, missing, ci.name))
    if bag.total:
        return Item(49, CHECK_NAMES[49], STATUS_FAIL,
                    "%d 个类 equals/hashCode 未成对" % bag.total, bag.items)
    return Item(49, CHECK_NAMES[49], STATUS_PASS,
                "重写 equals 的类均已成对重写 hashCode（Lombok/record 已豁免）")


# ---------------------------------------------------------------------------
# 组十：书写细项（#50~#57）
#
# 规则口径对齐 Checkstyle 10.x（CatchParameterName / StaticVariableName /
# WhitespaceAfter / EmptyLineSeparator / MultipleVariableDeclarations /
# OneStatementPerLine / NoLineWrap / NeedBraces / LeftCurly）；实现为本项目原创，
# 未复制其代码、配置或文档。口径均以真实检查工具在本项目代码上的实测结果校准。
# ---------------------------------------------------------------------------

# #50 catch 形参命名
_CATCH_CLAUSE_RE = re.compile(r"\bcatch\s*\(([^()]*)\)")
_CATCH_SHORT_OK = frozenset(("e", "t", "ex", "_"))
_CATCH_LONG_OK_RE = re.compile(r"^[a-z][a-z][a-zA-Z]+$")


def _catch_param_name(inner):
    """取 catch 形参名：形参段最后一个标识符（兼容 ``final`` 修饰与泛型类型）。"""
    toks = _LAMBDA_IDENT_RE.findall(inner)
    return toks[-1] if toks else ""


def _catch_param_ok(name):
    """catch 形参名口径：``e``/``t``/``ex``/``_``，或小写开头、长度 ≥3 的纯字母名。"""
    return name in _CATCH_SHORT_OK or bool(_CATCH_LONG_OK_RE.match(name))


def check_50(ctx):
    """#50 catch 形参命名：须为 e/t/ex、``_``，或小写开头的描述性名称。"""
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        for m in _CATCH_CLAUSE_RE.finditer(masked):
            name = _catch_param_name(m.group(1))
            if not name:
                continue
            total += 1
            if not _catch_param_ok(name):
                bag.add(rel, _line_of(masked, m.start()),
                        "catch 形参命名不规范: %s（应为 e/t/ex 或小写开头的描述性名称）" % name)
    if bag.total:
        return Item(50, CHECK_NAMES[50], STATUS_FAIL,
                    "%d/%d 处 catch 形参命名不规范" % (bag.total, total), bag.items)
    return Item(50, CHECK_NAMES[50], STATUS_PASS,
                "%d 处 catch 子句形参命名均合规" % total)


# #51 静态（非 final）字段命名
_STATIC_FIELD_RE = re.compile(
    r"(?<![.\w])static\s+(?!final\b)(?:[\w.$<>\[\],\s?]+?)\s+"
    r"([A-Za-z_$][\w$]*)\s*(?=[=;,])")


def check_51(ctx):
    """#51 静态变量命名：非 final 的 static 字段须为 lowerCamelCase。

    常量（``static final``）由 #39 按 UPPER_SNAKE_CASE 核对，本项不重复。
    """
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        for m in _STATIC_FIELD_RE.finditer(masked):
            if masked[max(0, m.start() - 7):m.start()] == "import ":
                continue                      # import static ...
            name = m.group(1)
            total += 1
            if not _LOWER_CAMEL_RE.match(name):
                bag.add(rel, _line_of(masked, m.start()),
                        "静态变量命名非 lowerCamelCase: %s" % name)
    if bag.total:
        return Item(51, CHECK_NAMES[51], STATUS_FAIL,
                    "%d/%d 处静态变量命名不规范" % (bag.total, total), bag.items)
    return Item(51, CHECK_NAMES[51], STATUS_PASS,
                "%d 处静态字段命名均合规" % total)


# #52 逗号/分号后空格
_COMMA_SEMI_TIGHT_RE = re.compile(r"[,;](?=[^\s;,)\]}])")
_TYPECAST_TIGHT_RE = re.compile(
    r"\(\s*(?:byte|short|int|long|float|double|char|boolean|[A-Z][\w$.]*(?:\[\])*)\s*\)"
    r"(?=[^\s;)\].,])")


def check_52(ctx):
    """#52 逗号/分号后空格：``,`` ``;`` 之后须有空白，类型转换 ``)`` 之后亦然。

    关键字（``if``/``for``/``while`` 等）后缺空格同属该口径，一并在此报出。
    """
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        for m in _COMMA_SEMI_TIGHT_RE.finditer(masked):
            total += 1
            bag.add(rel, _line_of(masked, m.start()),
                    "'%s' 后缺空格（应补 1 个空格）" % masked[m.start()])
        for m in _TYPECAST_TIGHT_RE.finditer(masked):
            total += 1
            bag.add(rel, _line_of(masked, m.start()),
                    "类型转换 ')' 后缺空格（应补 1 个空格）")
        for m in _KEYWORD_BLANK_RE.finditer(masked):
            total += 1
            bag.add(rel, _line_of(masked, m.end()),
                    "关键字 %s 后缺空格（应补 1 个空格）" % m.group(1))
    if bag.total:
        return Item(52, CHECK_NAMES[52], STATUS_FAIL,
                    "%d 处逗号/分号/关键字后缺空格" % bag.total, bag.items)
    return Item(52, CHECK_NAMES[52], STATUS_PASS,
                "逗号/分号/类型转换/关键字后的空格均合规（核对 %d 处）" % total)


def _member_block_start(lines, decl_idx0):
    """从声明行（0-based）向上并入紧邻的注解与注释行，返回成员块起始行索引。

    WHY: 空行规范核对的是「成员块」而非「声明行」——成员自带的 Javadoc / 注解即使紧贴
    声明，也算成员的一部分，空行要求落在它们之上，否则会把规范的写法误报为缺空行。
    """
    j = decl_idx0
    in_block = False
    while j - 1 >= 0:
        prev = lines[j - 1]
        s = prev.strip()
        if in_block:
            j -= 1
            if "/*" in prev:
                in_block = False
            continue
        if not s:
            break
        if s.endswith("*/"):
            j -= 1
            if not s.startswith("/*"):
                in_block = True
            continue
        if s.startswith(("//", "@")):
            j -= 1
            continue
        break
    return j


def check_53(ctx):
    """#53 成员之间空行：方法/构造器之前须有空行。

    豁免口径经真实检查工具逐例实测校准：

    - 类型体 / 语句块的首个成员（上一非空行以 ``{`` 结尾）；
    - 上一成员是**字段**（含带初始化表达式的字段）——此时允许不空行；
      紧邻的 Javadoc、块注释、注解**都不构成**豁免，仍需空行。
    """
    bag = Bag(ctx.max_findings)
    total = 0
    for ci in ctx.classes():
        rel = ctx.rel(ci.path)
        lines = J.read_lines(ci.path)
        for m in ci.methods:
            if re.match(r"^[A-Z][A-Z0-9_]*$", m.name):
                continue                      # 枚举常量被轻量解析器当成方法
            total += 1
            start = _member_block_start(lines, m.decl_line - 1)
            if start <= 0 or not lines[start - 1].strip():
                continue
            k = start - 1
            while k >= 0 and not lines[k].strip():
                k -= 1
            if k < 0:
                continue
            prev = lines[k].strip()
            if prev.endswith("{"):
                continue                      # 类型体 / 语句块的首个成员
            if prev.endswith("}") or _ABSTRACT_METHOD_LINE_RE.match(prev):
                pass                          # 上一成员是方法/语句块 → 需空行
            else:
                continue                      # 上一成员是字段 → 允许不空行
            bag.add(rel, m.decl_line, "%s 前缺空行（应插入 1 个空行）" % m.name)
    if bag.total:
        return Item(53, CHECK_NAMES[53], STATUS_FAIL,
                    "%d 处方法/构造器前缺空行（共核对 %d 个成员）" % (bag.total, total),
                    bag.items)
    return Item(53, CHECK_NAMES[53], STATUS_PASS,
                "%d 个方法/构造器前均符合空行规范" % total)


# #54 一行一声明（同一声明内多个变量）
# WHY 类型部分不用「含 \s 的宽字符类 + 紧跟 \s+」：掩码会把注释/字符串变成「纯空格长串」，
# 两个都能匹配空白的构造会争抢同一段空白 → 正则灾难性回溯（实测 1270 字符的小文件耗时
# 53ms、整个模块跑不完）。改为显式类型形态（不含 \s），同输入同结果、快约三个数量级。
_MULTI_VAR_DECL_RE = re.compile(
    r"^[ \t]*(?:final[ \t]+)?[A-Za-z_$][\w$.]*(?:<[^;{}]*?>)?(?:[ \t]*\[\s*\])*[ \t]+"
    r"[A-Za-z_$][\w$]*\s*(?:=[^;()]*?)?,\s*[A-Za-z_$][\w$]*\s*(?:=[^;()]+?)?;", re.M)


def check_54(ctx):
    """#54 一行一声明：一条声明语句内不得同时定义多个变量。

    WHY: ``int a = 1, b = 2;`` 中第二个变量定义在视觉上被隐藏。同一行写多条独立声明
    （``int a = 1; int b = 2;``）属「一行一语句」，由 #55 覆盖。
    """
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        for m in _MULTI_VAR_DECL_RE.finditer(masked):
            total += 1
            bag.add(rel, _line_of(masked, m.start()),
                    "一条声明内定义多个变量: %s" % m.group(0).strip()[:60])
    if bag.total:
        return Item(54, CHECK_NAMES[54], STATUS_FAIL,
                    "%d 处一条声明内定义了多个变量" % bag.total, bag.items)
    return Item(54, CHECK_NAMES[54], STATUS_PASS, "未发现一条声明定义多个变量的写法")


# #55 一行一语句
_FOR_HEADER_RE = re.compile(r"\bfor\s*\(")
_DO_WHILE_TAIL_RE = re.compile(r"^\s*\}\s*while\b")
# 抽象方法/接口方法声明行：无赋值号，且以 `名字(...)` 收尾并带分号
_ABSTRACT_METHOD_LINE_RE = re.compile(
    r"^(?!.*=)[\w.$<>\[\],\s]*\s[A-Za-z_$][\w$]*\s*\([^()]*\)\s*;\s*$")


def _strip_for_headers(masked):
    """把 ``for ( ... )`` 头部的分号置为空格（for 头内的分号不属「多语句」）。"""
    out = list(masked)
    for m in _FOR_HEADER_RE.finditer(masked):
        open_pos = m.end() - 1
        close_pos = _match_paren(masked, open_pos)
        if close_pos < 0:
            continue
        for k in range(open_pos, close_pos + 1):
            if out[k] == ";":
                out[k] = " "
    return "".join(out)


def check_55(ctx):
    """#55 一行一语句：同一行不得出现多条语句（``for`` 头部的分号除外）。"""
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        rel = ctx.rel(f)
        stripped = _strip_for_headers(J.mask_source(_read(f)))
        for i, line in enumerate(stripped.split("\n"), 1):
            s = line.strip()
            if not s or s.startswith(("*", "//")):
                continue
            if _DO_WHILE_TAIL_RE.match(line):
                continue                      # do { ... } while (...); 属单条语句
            n = line.count(";")
            if n >= 2:
                total += 1
                bag.add(rel, i, "同一行出现 %d 条语句" % n)
    if bag.total:
        return Item(55, CHECK_NAMES[55], STATUS_FAIL,
                    "%d 行存在多条语句" % bag.total, bag.items)
    return Item(55, CHECK_NAMES[55], STATUS_PASS, "未发现一行多条语句")


# #56 package/import 不换行
def check_56(ctx):
    """#56 package/import 不换行：``package`` 与 ``import`` 语句须写在同一行内。"""
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        for i, line in enumerate(masked.split("\n"), 1):
            s = line.strip()
            if not s or s.startswith(("*", "//")):
                continue
            if not re.match(r"^(package|import)\b", s):
                continue
            total += 1
            if not s.endswith(";"):
                bag.add(rel, i, "%s 语句被换行拆断" % s.split()[0])
    if bag.total:
        return Item(56, CHECK_NAMES[56], STATUS_FAIL,
                    "%d 处 package/import 语句跨行" % bag.total, bag.items)
    return Item(56, CHECK_NAMES[56], STATUS_PASS,
                "%d 条 package/import 语句均在单行内" % total)


# #57 花括号：必写与位置
_ELSE_NO_BRACE_RE = re.compile(r"\belse\b(?!\s*\{)(?!\s*if\b)")
_DO_NO_BRACE_RE = re.compile(r"\bdo\b(?!\s*\{)")
# `{` 独占一行时，若上一非空行以这些字符结尾，视为数组初始化等延续写法，不判违规
_CURLY_OWN_LINE_OK = ("=", ",", "(", "[", "{")
# `{` 后同行还有代码时，若前一个字符属于这些，视为数组初始化 / lambda 体，不判违规
_CURLY_INLINE_OK = "=,([]{]>"


def _left_curly_hits(masked):
    """产出 (偏移, 说明)——``{`` 位置不合规（独占一行，或同行紧跟代码）。"""
    n = len(masked)
    pos = masked.find("{")
    while pos >= 0:
        line_start = masked.rfind("\n", 0, pos) + 1
        line_end = masked.find("\n", pos)
        if line_end < 0:
            line_end = n
        k = pos - 1
        while k >= 0 and masked[k] in " \t\r\n":
            k -= 1
        prev_ch = masked[k] if k >= 0 else ""
        if not masked[line_start:pos].strip():
            prev_end = masked.rfind("\n", 0, line_start - 1)
            prev_line = masked[prev_end + 1:line_start - 1].strip()
            if prev_line and not prev_line.endswith(_CURLY_OWN_LINE_OK):
                yield pos, "'{' 独占一行（应移到前一行的行尾）"
        elif masked[pos + 1:line_end].strip() and prev_ch not in _CURLY_INLINE_OK:
            yield pos, "'{' 后应换行（同一行不得紧跟代码，应将代码移到下一行）"
        pos = masked.find("{", pos + 1)


def check_57(ctx):
    """#57 花括号必写与位置：控制语句必须有 ``{}``，``{`` 须在行尾且其后换行，
    ``}`` 与 ``else``/``catch``/``finally`` 须同行（对应 RightCurly ``option=same``）。
    """
    bag = Bag(ctx.max_findings)
    total = 0
    for f in ctx.java_files:
        rel = ctx.rel(f)
        masked = J.mask_source(_read(f))
        for m in _BRANCH_RE.finditer(masked):
            total += 1
            close_pos = _match_paren(masked, m.end() - 1)
            if close_pos < 0:
                continue
            j = close_pos + 1
            n = len(masked)
            while j < n and masked[j] in " \t\r\n":
                j += 1
            if j < n and masked[j] == "{":
                continue
            bag.add(rel, _line_of(masked, m.start()),
                    "%s 条件后未见 '{'（须补大括号）" % m.group(1))
        for regex, detail in ((_ELSE_NO_BRACE_RE, "else 后未见 '{'（须补大括号）"),
                              (_DO_NO_BRACE_RE, "do 后未见 '{'（须补大括号）")):
            for m in regex.finditer(masked):
                total += 1
                bag.add(rel, _line_of(masked, m.start()), detail)
        for pos, detail in _left_curly_hits(masked):
            total += 1
            bag.add(rel, _line_of(masked, pos), detail)
        # 右花括号位置：`}` 与 else/catch/finally 换行分离（RightCurly option=same）
        for m in _BRACE_NEWLINE_KEYWORD_RE.finditer(masked):
            total += 1
            bag.add(rel, _line_of(masked, m.start()),
                    "右花括号 '}' 与 else/catch/finally 未同行（应写成 `} else {`）")
    if bag.total:
        return Item(57, CHECK_NAMES[57], STATUS_FAIL,
                    "%d 处花括号不合规（共核对 %d 处）" % (bag.total, total), bag.items)
    return Item(57, CHECK_NAMES[57], STATUS_PASS,
                "花括号必写与位置均合规（共核对 %d 处）" % total)


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
    34: check_34, 35: check_35, 36: check_36, 37: check_37, 38: check_38,
    39: check_39, 40: check_40, 41: check_41, 42: check_42, 43: check_43,
    44: check_44,
    45: check_45, 46: check_46, 47: check_47, 48: check_48, 49: check_49,
    50: check_50, 51: check_51, 52: check_52, 53: check_53,
    54: check_54, 55: check_55, 56: check_56, 57: check_57,
}


def _filter_suppressed(ctx, item):
    """按抑制注释过滤证据：静态检查侧会抑制的写法，本工具同样不再报出。"""
    if not item.evidence or item.status == STATUS_SKIP:
        return item
    kept = []
    removed = 0
    for ev in item.evidence:
        if ev.line in _file_suppressions(ctx, ev.file):
            removed += 1
            continue
        kept.append(ev)
    if not removed:
        return item
    item.evidence = kept
    item.note = (item.note + "；已按抑制注释排除 %d 条" % removed).strip("；")
    if not kept:
        item.status = STATUS_PASS
    return item


def run_all(ctx, only=None, skip=None):
    """执行核对，返回 (items, summary)。

    only / skip 为 id 集合；only 非空时只跑这些 id；skip 中的 id 被跳过并计为 skip。
    """
    ids = sorted(CHECK_NAMES.keys())
    todo = [c for c in ids if not (only and c not in only)]
    items = []
    summary = {STATUS_PASS: 0, STATUS_FAIL: 0, STATUS_WARN: 0,
               STATUS_MANUAL: 0, STATUS_SKIP: 0}
    done = 0
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
        item = _filter_suppressed(ctx, item)
        if item.name != name:
            item.name = name
        summary[item.status] = summary.get(item.status, 0) + 1
        items.append(item)
        done += 1
        if (not PROGRESS_QUIET and len(ctx.java_files) >= 200
                and done % 10 == 0 and done < len(todo)):
            sys.stderr.write("[进度] 已完成 %d/%d 项\n" % (done, len(todo)))
    return items, summary
