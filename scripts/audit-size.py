#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能体积审计（audit-size）。

用途
----
本仓库的技能是"按需加载进 Agent 上下文"的文本资产，SKILL.md 一旦触发就整篇进上下文，
模板/规范/命令文件则按流程步骤级联读取。文件越长，每次任务付的 token 越多，
且这种膨胀是**渐进且无人察觉**的（每次改动只加几行，几十次后就翻倍）。

本脚本提供两件事：

1. **绝对预算线**：按文件类别设上限，超限即报错（防单文件失控）。
2. **基线对比**：首次运行生成 ``scripts/size-baseline.json`` 记录当前体量，
   之后每次运行与基线比对，涨幅超阈值即报警（防"温水煮青蛙"式回涨）。

另外输出**级联路径估算**：按 ai-dev-workflow SKILL.md 的「配套规范 skill 触发矩阵」，
算出一次典型任务实际要读进上下文的文件总量——这个数字远大于常驻成本，
是优化优先级排序的真正依据。

用法
----
    python3 scripts/audit-size.py                # 审计；有超限或回涨则退出码 1
    python3 scripts/audit-size.py --json         # 机器可读输出
    python3 scripts/audit-size.py --write-baseline   # 优化完成后刷新基线
    python3 scripts/audit-size.py --no-baseline  # 只查绝对预算，不做基线对比
    python3 scripts/audit-size.py --cascade      # 只输出级联路径估算

WHY 纯标准库 + 只读：脚本要在任何装了 Python 3 的机器上零依赖跑起来
（CI、本地、他人机器），且只做统计不写业务文件（--write-baseline 是唯一写操作，需显式指定）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# 仓库根 = 本脚本所在目录的上一级（scripts/ 在仓库根下）
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_ROOT = os.path.join(REPO_ROOT, "skill")
BASELINE_PATH = os.path.join(REPO_ROOT, "scripts", "size-baseline.json")

# 折算系数：UTF-8 中文 3 字节/字，约 1 字 ≈ 1 token；代码/英文约 4 字符 ≈ 1 token
# WHY 不用简单的 bytes/3：代码块与英文路径多的文件会被低估，分开算更接近真实 token 数
CJK_BYTES_PER_CHAR = 3
ASCII_CHARS_PER_TOKEN = 4

# ---------------------------------------------------------------------------
# 绝对预算线
# ---------------------------------------------------------------------------
# 每项 = (类别名, 匹配规则, 字节上限)
# 匹配规则用「相对 skill 根的后缀/目录前缀」表达，避免引入 glob 依赖；
# WHY 用后缀而不用完整路径：技能目录会增删，按类别设限比逐个文件点名更抗变化。
BUDGETS = (
    # SKILL.md 是触发即整篇进上下文的入口，最贵的文件，预算最紧
    ("SKILL 入口", ("::SKILL.md",), 48000),
    # 命令文件：单条命令触发时只读一个，按单文件设限
    ("命令 commands", ("/commands/",), 10000),
    # 类型模板：一次 /design 读 1 个骨架 + 1 个类型模板
    # WHY 3.1（Controller）单列 13000：它承载最复杂类型的全部规则（接口明细 + 数据契约 + 调用骨架 + 关注点 + 特有自检），
    # 已从最初的 19.9KB 瘦到 12.4KB（示例与其余 URL 形态移入 references/），再压会丢规则
    ("技术方案模板", ("/templates/3.",), 13000),
    # 通用模板（样式规范等）：被"每次生成产物前必读"，最该瘦
    ("通用模板", ("/templates/通用-",), 9000),
    # 其他中间产物模板
    ("产物模板", ("/templates/",), 15000),
    # 规范正文：按需加载，但单文件过长会导致"读了前面忘后面"
    ("规范 standards", ("/standards/",), 13000),
    ("规范 java-code", ("/java-code-standards/",), 15000),
    ("规范 mybatis-plus", ("/mybatis-plus/",), 13000),
    # 方法论文档：不进上下文，宽松
    ("方法论文档 docs", ("/docs/",), 50000),
    # references/ 是按需查阅的字典，允许较长
    ("按需参考 references", ("/references/",), 30000),
    # 脚本附带的说明文档：当前只被技能 README（给人看）引用，不进 Agent 上下文，预算放宽；
    # WHY 仍设上限：一旦 SKILL.md 开始引用它（如"详见 scripts/README.md"），它就变成上下文成本，
    # 那时应把它瘦身到 8KB 以内或改为 references/ 下按需查阅
    ("脚本说明", ("/scripts/README.md",), 22000),
    # 技能自带的 README：给人看的，一般不进上下文，预算宽松
    ("技能 README", ("::README.md",), 15000),
)

# 基线对比阈值：超出基线 5% 报警（warn），超出 20% 判失败（fail）
BASELINE_WARN_RATIO = 1.05
BASELINE_FAIL_RATIO = 1.20

# ---------------------------------------------------------------------------
# 级联路径估算
# ---------------------------------------------------------------------------
# 每条路径 = (场景名, 触发条件说明, [必读文件相对 skill/ 的路径或目录])
# WHY 硬编码路径而不是解析 SKILL.md 的触发矩阵：矩阵是自然语言表格，
# 解析它要写一堆正则且随措辞变动而失效；这里只在矩阵变更时手工同步一处，成本可控。
CASCADE_PATHS = (
    (
        "一次 /design（Controller 功能项）",
        "生成单个功能项技术方案 + 接口清单",
        (
            "ai-dev-workflow/SKILL.md",
            "ai-dev-workflow/references/完整流程.md",
            "ai-dev-workflow/commands/design.md",
            "ai-dev-workflow/templates/3.0-技术方案-通用骨架.md",
            "ai-dev-workflow/templates/3.1-技术方案-Controller.md",
            "ai-dev-workflow/templates/3.4-接口清单-前后端通用.md",
            "ai-dev-workflow/templates/通用-中间产物-MD样式规范.md",
            "database-standards/standards/table-design-standards.md",
            "java-code-standards/SKILL.md",
        ),
    ),
    (
        "一次 /implement（写代码）",
        "按方案编码，含规范加载",
        (
            "ai-dev-workflow/SKILL.md",
            "ai-dev-workflow/references/完整流程.md",
            "ai-dev-workflow/commands/implement.md",
            "ai-dev-workflow/templates/5.1-编码指令.md",
            "ai-dev-workflow/templates/通用-中间产物-MD样式规范.md",
            "java-code-standards/SKILL.md",
            "java-code-standards/00-common/01-naming-standards.md",
            "java-code-standards/00-common/04-logging-standards.md",
            "java-code-standards/01-java/controller-standards.md",
            "java-code-standards/01-java/service-impl-standards.md",
            "java-code-standards/01-java/entity-standards.md",
            "comment-standards/SKILL.md",
            "comment-standards/standards/comment-standards.md",
            "database-standards/SKILL.md",
        ),
    ),
    (
        "一次 /check-standards（兜底核对）",
        "代码写完后的规范核对",
        (
            "check-standards/SKILL.md",
            "ai-dev-workflow/SKILL.md",
        ),
    ),
    (
        "轻量模式（写个接口）",
        "无需求文档直接写码的最小路径",
        (
            "ai-dev-workflow/SKILL.md",
            "java-code-standards/SKILL.md",
            "comment-standards/SKILL.md",
            "check-standards/SKILL.md",
        ),
    ),
)


def count_tokens(path: str) -> int:
    """按中英混合口径折算 token 数（中文字数 + ASCII 字符数/4）。

    WHY 失败时抛 SystemExit 而非裸栈：审计脚本读的文件列表是硬编码的，
    重命名/删文件后应当立即失败并指出具体路径，而不是丢一段 traceback。
    """
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        raise SystemExit("[audit-size] 读取失败 %s：%s（检查 CASCADE_PATHS / 文件是否改名）" % (path, exc))
    # WHY 非 ASCII 一律按中文 3 字节估算：本仓库日文/emoji 极少，误差可忽略
    non_ascii = sum(1 for b in data if b >= 0x80)
    ascii_cnt = len(data) - non_ascii
    return int(non_ascii / CJK_BYTES_PER_CHAR + ascii_cnt / ASCII_CHARS_PER_TOKEN)


def iter_markdown_files():
    """遍历 skill/ 下所有 .md，产出 (相对 skill/ 的路径, 绝对路径)。"""
    for dirpath, dirnames, filenames in os.walk(SKILL_ROOT):
        # 跳过缓存目录，避免统计到临时产物
        dirnames[:] = [d for d in dirnames if d not in {"__pycache__", ".git"}]
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            abs_path = os.path.join(dirpath, name)
            yield os.path.relpath(abs_path, SKILL_ROOT), abs_path


def classify(rel_path: str) -> str:
    """按 BUDGETS 的顺序判定文件类别，返回类别名（无匹配归入「未分类」）。"""
    # WHY 补前导 "/"：让 in 判断不会误命中文件名内部的片段（如 "templates" 出现在别的路径里）
    probe = "/" + rel_path
    for category, patterns, _limit in BUDGETS:
        for pattern in patterns:
            # 「::」前缀表示按文件名尾部匹配（如 ::SKILL.md 匹配 <skill>/SKILL.md）
            if pattern.startswith("::"):
                if probe.endswith("/" + pattern[2:]):
                    return category
            elif pattern in probe:
                return category
    return "未分类"


def budget_of(category: str) -> int:
    """返回该类别的字节预算上限；未分类返回 0 表示不设限。"""
    for cat, _patterns, limit in BUDGETS:
        if cat == category:
            return limit
    return 0


def collect():
    """收集所有 md 文件的体积信息，返回按字节降序的列表。"""
    rows = []
    for rel_path, abs_path in iter_markdown_files():
        size = os.path.getsize(abs_path)
        rows.append(
            {
                "path": rel_path,
                "category": classify(rel_path),
                "bytes": size,
                "tokens": count_tokens(abs_path),
                "budget": budget_of(classify(rel_path)),
            }
        )
    rows.sort(key=lambda r: r["bytes"], reverse=True)
    return rows


def evaluate_budget(rows):
    """对比绝对预算线，返回超限行列表。"""
    violations = []
    for row in rows:
        if row["budget"] and row["bytes"] > row["budget"]:
            violations.append(row)
    return violations


def load_baseline():
    """读取基线文件；不存在或损坏时返回 None（不阻断审计）。"""
    if not os.path.exists(BASELINE_PATH):
        return None
    try:
        with open(BASELINE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        # WHY 静默降级：基线损坏不应阻断审计主体（绝对预算仍然有效）
        return None


def evaluate_baseline(rows, baseline):
    """对比基线，返回 (warn 列表, fail 列表)。"""
    if not baseline:
        return [], []
    previous = baseline.get("files", {})
    warns, fails = [], []
    for row in rows:
        old = previous.get(row["path"])
        if not old:
            # 新文件没有历史基线，仅记录不报警（首次出现属正常增量）
            continue
        if row["bytes"] > old * BASELINE_FAIL_RATIO:
            fails.append((row, old))
        elif row["bytes"] > old * BASELINE_WARN_RATIO:
            warns.append((row, old))
    return warns, fails


def cascade_stats():
    """统计每条级联路径的必读体量。"""
    result = []
    for name, desc, files in CASCADE_PATHS:
        total_bytes = 0
        total_tokens = 0
        missing = []
        for rel_path in files:
            abs_path = os.path.join(SKILL_ROOT, rel_path)
            if not os.path.exists(abs_path):
                missing.append(rel_path)
                continue
            total_bytes += os.path.getsize(abs_path)
            total_tokens += count_tokens(abs_path)
        result.append(
            {
                "name": name,
                "desc": desc,
                "file_count": len(files) - len(missing),
                "bytes": total_bytes,
                "tokens": total_tokens,
                "missing": missing,
            }
        )
    return result


def fmt_bytes(num: int) -> str:
    """字节转可读字符串。"""
    if num >= 1024 * 1024:
        return "%.1fMB" % (num / 1024.0 / 1024.0)
    return "%.1fKB" % (num / 1024.0)


def print_report(rows, violations, warns, fails, cascade, use_baseline):
    """打印人读报告。"""
    print("=" * 78)
    print("技能体积审计")
    print("=" * 78)

    # 按类别汇总
    summary = {}
    for row in rows:
        bucket = summary.setdefault(row["category"], {"count": 0, "bytes": 0, "tokens": 0})
        bucket["count"] += 1
        bucket["bytes"] += row["bytes"]
        bucket["tokens"] += row["tokens"]

    print("\n[按类别汇总]")
    print("%-22s %5s %10s %10s" % ("类别", "文件数", "字节", "折算token"))
    print("-" * 78)
    for cat, bucket in sorted(summary.items(), key=lambda kv: -kv[1]["bytes"]):
        print(
            "%-22s %5d %10s %10s"
            % (cat, bucket["count"], fmt_bytes(bucket["bytes"]), "{:,}".format(bucket["tokens"]))
        )
    total_bytes = sum(r["bytes"] for r in rows)
    total_tokens = sum(r["tokens"] for r in rows)
    print("-" * 78)
    print(
        "%-22s %5d %10s %10s"
        % ("合计", len(rows), fmt_bytes(total_bytes), "{:,}".format(total_tokens))
    )

    # 单文件 Top 10
    print("\n[体积 Top 10]")
    print("%-58s %9s %9s" % ("文件", "字节", "token"))
    print("-" * 78)
    for row in rows[:10]:
        print("%-58s %9s %9s" % (row["path"], fmt_bytes(row["bytes"]), "{:,}".format(row["tokens"])))

    # 预算违规
    print("\n[绝对预算]")
    if not violations:
        print("  ✅ 全部在预算线内")
    else:
        for row in violations:
            over = row["bytes"] - row["budget"]
            print(
                "  ❌ %s  %s > 预算 %s（超 %s / %d token）"
                % (
                    row["path"],
                    fmt_bytes(row["bytes"]),
                    fmt_bytes(row["budget"]),
                    fmt_bytes(over),
                    row["tokens"] - int(row["tokens"] * row["budget"] / row["bytes"]),
                )
            )

    # 基线对比
    if use_baseline:
        print("\n[基线回涨比对]")
        if load_baseline() is None:
            print("  ℹ️ 尚无基线，运行 --write-baseline 生成")
        elif not warns and not fails:
            print("  ✅ 无异常涨幅（阈值：+5% 警告 / +20% 失败）")
        else:
            for row, old in fails:
                print("  ❌ %s  %s → %s（+%.0f%%，超 20%%）"
                      % (row["path"], fmt_bytes(old), fmt_bytes(row["bytes"]),
                         (row["bytes"] / old - 1) * 100))
            for row, old in warns:
                print("  ⚠️  %s  %s → %s（+%.0f%%）"
                      % (row["path"], fmt_bytes(old), fmt_bytes(row["bytes"]),
                         (row["bytes"] / old - 1) * 100))

    # 级联路径
    print("\n[级联路径估算：一次任务实际读进上下文的量]")
    print("%-34s %6s %9s %10s" % ("场景", "文件数", "字节", "折算token"))
    print("-" * 78)
    for item in cascade:
        print(
            "%-34s %6d %9s %10s"
            % (item["name"], item["file_count"], fmt_bytes(item["bytes"]), "{:,}".format(item["tokens"]))
        )
        if item["missing"]:
            print("      ⚠️ 路径缺失：%s" % ", ".join(item["missing"]))
    print("-" * 78)
    if cascade:
        worst = max(cascade, key=lambda c: c["tokens"])
        print("最贵路径：%s ≈ %s token" % (worst["name"], "{:,}".format(worst["tokens"])))
    print("\n提示：优化优先级按「级联路径总量」排，不是按单文件；常驻成本只在技能被触发时支付。")


def main() -> int:
    """入口：解析参数 → 审计 → 打印/落盘 → 返回退出码。"""
    parser = argparse.ArgumentParser(description="技能体积审计与预算校验")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--write-baseline", action="store_true", help="把当前体积写为基线")
    parser.add_argument("--no-baseline", action="store_true", help="只查绝对预算，不做基线比对")
    parser.add_argument("--cascade", action="store_true", help="只输出级联路径估算")
    args = parser.parse_args()

    rows = collect()
    cascade = cascade_stats()

    if args.cascade:
        print("[级联路径估算]")
        for item in cascade:
            print("%-34s %6d %9s %10s"
                  % (item["name"], item["file_count"], fmt_bytes(item["bytes"]),
                     "{:,}".format(item["tokens"])))
        return 0

    if args.write_baseline:
        snapshot = {
            "note": "技能体积基线，由 scripts/audit-size.py --write-baseline 生成；优化后刷新，勿手工编辑",
            "files": {row["path"]: row["bytes"] for row in rows},
        }
        try:
            os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
            with open(BASELINE_PATH, "w", encoding="utf-8") as fh:
                json.dump(snapshot, fh, ensure_ascii=False, indent=2, sort_keys=True)
                fh.write("\n")
        except OSError as exc:
            raise SystemExit("[audit-size] 写入基线失败 %s：%s" % (BASELINE_PATH, exc))
        print("已写入基线：%s（%d 个文件）" % (BASELINE_PATH, len(rows)))
        return 0

    violations = evaluate_budget(rows)
    use_baseline = not args.no_baseline
    warns, fails = evaluate_baseline(rows, load_baseline()) if use_baseline else ([], [])

    if args.json:
        payload = {
            "total_bytes": sum(r["bytes"] for r in rows),
            "total_tokens": sum(r["tokens"] for r in rows),
            "files": rows,
            "budget_violations": [r["path"] for r in violations],
            "baseline_warns": [{"path": r["path"], "old": old} for r, old in warns],
            "baseline_fails": [{"path": r["path"], "old": old} for r, old in fails],
            "cascade": cascade,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(rows, violations, warns, fails, cascade, use_baseline)

    # 退出码：预算超限或基线大幅回涨 → 1
    return 1 if (violations or fails) else 0


if __name__ == "__main__":
    sys.exit(main())
