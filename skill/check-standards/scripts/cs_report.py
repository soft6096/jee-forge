#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-standards 报告渲染：Markdown + JSON（纯标准库实现）。

Markdown 对齐 SKILL.md「输出格式」；JSON 为稳定机读结构（见 README）。
"""

from __future__ import annotations

import json

STATUS_SYMBOL = {
    "pass": "[✅]",
    "fail": "[❌]",
    "warn": "[⚠️ 需人工]",
    "manual": "[⚠️ 需人工]",
    "skip": "[⏭ 跳过]",
}


def _evidence_text(item, max_findings):
    parts = []
    shown = item.get("evidence", [])[:max_findings]
    for e in shown:
        loc = e.get("file", "")
        if e.get("line"):
            loc = "%s:%s" % (loc, e["line"])
        detail = e.get("detail", "")
        parts.append(("%s %s" % (loc, detail)).strip())
    text = "；".join(parts) if parts else "无"
    total = len(item.get("evidence", []))
    if total > len(shown):
        text += " ...(+%d more)" % (total - len(shown))
    return text


def render_md(report, max_findings=20):
    """把报告 dict 渲染为 Markdown 文本。"""
    lines = []
    lines.append("=== 关键规范核对报告 ===")
    lines.append("项目: %s    时间: %s    模式: %s    核对范围: %s"
                 % (report.get("project", ""), report.get("generated_at", ""),
                    report.get("mode", ""), _scope_text(report)))
    lines.append("")

    renames = report.get("renames", [])
    if renames:
        lines.append("产物矫正记录（第 0 步）:")
        for r in renames:
            new = r.get("new") or "<无法机械推导，需人工确认>"
            lines.append("  %s → %s（%s）" % (r.get("old", ""), new, r.get("reason", "")))
    else:
        lines.append("产物矫正记录（第 0 步）: 无，命名/路径已合规")
    lines.append("")

    if report.get("scope_note"):
        lines.append("范围说明: %s" % report["scope_note"])
        lines.append("")
    if report.get("mode_note"):
        lines.append("模式说明: %s" % report["mode_note"])
        lines.append("")

    for item in report.get("items", []):
        sym = STATUS_SYMBOL.get(item.get("status"), "[?]")
        ev = _evidence_text(item, max_findings)
        note = item.get("note", "")
        line = "%s %s %s" % (sym, item.get("id"), item.get("name"))
        if note:
            line += "   说明: %s" % note
        line += "   证据: %s" % ev
        lines.append(line)

    summary = report.get("summary", {})
    total = sum(summary.get(k, 0) for k in ("pass", "fail", "warn", "manual", "skip"))
    manual = summary.get("warn", 0) + summary.get("manual", 0)
    lines.append("")
    lines.append("结论: %d 项核对项：通过 %d / 未通过 %d / 需人工 %d / 跳过 %d"
                 % (total, summary.get("pass", 0), summary.get("fail", 0),
                    manual, summary.get("skip", 0)))

    pending = report.get("pending_confirmation", [])
    lines.append("⚠️ 待用户确认清单（未执行到位项，一次确认，无级别之分）:")
    if pending:
        for cid in pending:
            name = _name_of(report, cid)
            lines.append("  #%s %s" % (cid, name))
    else:
        lines.append("  （无）")
    return "\n".join(lines)


def _name_of(report, cid):
    for item in report.get("items", []):
        if item.get("id") == cid:
            return item.get("name", "")
    return ""


def _scope_text(report):
    scope = report.get("scope", "")
    if scope == "project":
        return "全项目"
    if scope == "changed":
        return "本轮改动（git 界定）"
    if scope == "path":
        return "指定路径: %s" % report.get("scope_path", "")
    return scope or "全项目"


def render_json(report):
    """把报告 dict 渲染为 JSON 文本。"""
    return json.dumps(report, ensure_ascii=False, indent=2)
