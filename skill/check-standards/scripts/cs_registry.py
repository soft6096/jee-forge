#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规范加载清单校验（独立小节，不占 #1~#57 编号）。

WHY 独立成节、不并入 57 项：核对项的计数必须保持 57（下游报告/README/流程文档都按 57 引用），
而「生成代码时是否真加载了对应规范」属于**过程证据**，与「代码本身是否合规」是两件事；
故只做独立小节，既不参与 57 项计数，也不影响退出码。

校验三件事：
1. docs/ 下存在 5.1 相关产物（编码完成报告 / 编码指令）时，断言其中含「规范加载清单」行且非空；
2. 按本次扫描到的 Java 产物类型做**映射校验**（有 Controller → 清单里应有 controller-standards.md …）；
3. 找不到 5.1 产物 → 标 ``manual``，不假装通过（无过程产物即无从校验，需人确认）。

纯标准库、只读，不写任何文件。
"""

from __future__ import annotations

import os
import re

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_MANUAL = "manual"

# 产物类型 → (展示名, 文件名后缀, 可接受的规范文件名)
# WHY 用「文件名后缀」判类型而不是读全 AST：脚本已按 #1/#2/#5 识别过目标类，
# 这里只需粗判「本次有没有这类产物」来决定该要求哪份规范，误判代价仅为多要/少要一个文件名。
# WHY ServiceImpl 同时接受 service-impl-standards.md 与 service-standards.md：
# 前者是本仓库的细分规范，后者是两类 Service 共同的父规范，加载任一都算「规范真加载了」。
_TYPE_RULES = (
    ("controller", "Controller", "Controller", ("controller-standards.md",)),
    ("service_impl", "ServiceImpl", "ServiceImpl",
     ("service-impl-standards.md", "service-standards.md")),
    ("service", "Service", "Service", ("service-standards.md",)),
    ("listener", "Listener", "Listener", ("listener-standards.md",)),
    ("job", "Job", "Job", ("job-standards.md",)),
)

# 注解兜底：文件名不含后缀但注解表明类型（如 ChatConsumer 带 @RabbitListener）
_ANNOTATION_RULES = {
    "controller": re.compile(r"@(?:Rest)?Controller\b"),
    "listener": re.compile(
        r"@(?:RabbitListener|KafkaListener|RocketMQMessageListener|JmsListener)\b"),
    "job": re.compile(r"@Scheduled\b|implements\s+Job\b"),
}

# 5.1 产物判定：docs/ 下 .md 文件名含 5.1 或「编码完成报告」
_PRODUCT_RE = re.compile(r"5\.1|编码完成报告")
# 「规范加载清单」行：允许中英文冒号，取冒号后剩余内容为清单
_MANIFEST_RE = re.compile(r"^\s*[-*]?\s*规范加载清单\s*[:：]\s*(.*)$")


def _read_text(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError:
            return ""
    return ""


def _docs_md_files(project):
    """列出项目 docs/ 下的全部 .md（相对路径，正斜杠）。找不到 docs/ 返回空列表。"""
    root = os.path.join(project, "docs")
    if not os.path.isdir(root):
        return []
    out = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(".md"):
                full = os.path.join(dirpath, name)
                out.append((os.path.relpath(full, project).replace(os.sep, "/"), full))
    return sorted(out)


def find_51_products(project):
    """返回 docs/ 下 5.1 相关产物 (相对路径, 绝对路径) 列表。"""
    return [(rel, full) for rel, full in _docs_md_files(project)
            if _PRODUCT_RE.search(os.path.basename(rel))]


def detect_artifact_types(java_files):
    """按文件名后缀 + 注解粗判本次扫描范围内存在哪些高价值产物类型。

    返回按 :data:`_TYPE_RULES` 顺序去重的展示名列表（如 ``["Controller", "ServiceImpl"]``）。
    """
    found = []
    for key, label, suffix, _accepts in _TYPE_RULES:
        hit = False
        for f in java_files:
            stem = os.path.splitext(os.path.basename(f))[0]
            if stem.endswith(suffix):
                hit = True
                break
            anno = _ANNOTATION_RULES.get(key)
            if anno is not None and anno.search(_read_text(f)):
                hit = True
                break
        if hit:
            found.append((key, label))
    return found


def _extract_manifest(text):
    """从产物文本中取「规范加载清单」内容；返回 (原始行内容, 是否非空)。

    WHY 允许清单续行：md 里长清单常被折到下一行；仅当本行冒号后为空、且下一行看起来
    是路径列表（含 ``/`` 或 ``.md``）时才续接，避免把后续小节正文误当清单。
    """
    lines = text.split("\n")
    for idx, line in enumerate(lines):
        m = _MANIFEST_RE.match(line)
        if not m:
            continue
        value = m.group(1).strip()
        if not value:
            for nxt in lines[idx + 1:idx + 3]:
                nxt = nxt.strip().lstrip("-*").strip()
                if not nxt or (("：" in nxt or ":" in nxt) and ".md" not in nxt):
                    break
                if "/" in nxt or ".md" in nxt:
                    value = (value + " " + nxt).strip()
                    continue
                break
        return value, bool(value)
    return "", False


def scan_registry_manifest(project, java_files):
    """执行规范加载清单校验，返回独立小节结果 dict。

    ``status``：``pass``（清单在且映射齐） / ``fail``（清单缺、空、或映射缺规范）
    / ``manual``（未找到 5.1 产物，无法校验）。
    """
    products = find_51_products(project)
    types = detect_artifact_types(java_files)
    required = []
    for key, label in types:
        for rule_key, _lbl, _suffix, accepts in _TYPE_RULES:
            if rule_key == key:
                required.append((label, accepts))
                break

    result = {
        "status": STATUS_MANUAL,
        "note": "",
        "manifest": "",
        "manifest_file": "",
        "products": [rel for rel, _full in products],
        "artifact_types": [label for _key, label in types],
        "required": [accepts[0] for _label, accepts in required],
        "missing": [],
    }

    if not products:
        result["note"] = "未找到 5.1 编码完成报告，无法校验规范加载"
        return result

    manifest_value = ""
    manifest_src = products[0][0]
    empty_hit = False
    for rel, full in products:
        text = _read_text(full)
        value, non_empty = _extract_manifest(text)
        if value or "规范加载清单" in text:
            manifest_src = rel
            manifest_value = value
            empty_hit = not non_empty
            break
    result["manifest_file"] = manifest_src
    result["manifest"] = manifest_value

    if empty_hit or not manifest_value:
        result["status"] = STATUS_FAIL
        result["note"] = ("5.1 产物（%s）未见「规范加载清单」行或该行内容为空"
                          % (manifest_src or "未定位"))
        return result
    # 逐类型校验清单里是否含对应规范文件
    missing = []
    for label, accepts in required:
        if not any(name in manifest_value for name in accepts):
            missing.append("%s → 应含 %s" % (label, accepts[0]))
    result["missing"] = missing
    if missing:
        result["status"] = STATUS_FAIL
        result["note"] = "规范加载清单缺少本次产物类型的规范：%s" % "；".join(missing)
        return result

    result["status"] = STATUS_PASS
    result["note"] = ("规范加载清单已声明%s"
                      % ("（本次产物：%s）" % "、".join(l for _k, l in types) if types else ""))
    return result
