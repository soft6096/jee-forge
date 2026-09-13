#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-standards CLI：机械执行 SKILL.md 的 33 项代码规范核对。

用法见 scripts/README.md。纯标准库；无需 ast-grep；rg 可选（未使用亦可）。
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cs_checks  # noqa: E402
import cs_java as J  # noqa: E402
import cs_report  # noqa: E402

TOOL_VERSION = "1.0.0"


def _now_local():
    return datetime.datetime.now()


def _force_utf8_stdio():
    """把标准输出/错误切到 UTF-8，避免 Windows GBK 控制台下写中文乱码或抛 UnicodeEncodeError。

    对没有 reconfigure 的流（如被替换的 StringIO）静默跳过。
    """
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def _build_java_scope(project, path, changed):
    """确定扫描范围的 Java 文件，返回 (files, scope, scope_path, note)。

    - ``--path`` / ``--changed`` 优先；
    - 默认只扫 Maven ``src/main/java``。
    """
    if changed:
        files, note = J.git_changed_java_files(project)
        return files, "changed", project, note
    if path:
        ap = os.path.abspath(path)
        files = J.iter_java_files([ap])
        return files, "path", ap, "指定路径扫描"
    roots = J.find_maven_java_roots(project)
    if not roots:
        src = os.path.join(project, "src")
        roots = [src] if os.path.isdir(src) else [project]
    files = J.iter_java_files(roots)
    return files, "project", project, "全项目扫描（默认，src/main/java）"


def build_context(args):
    """根据命令行参数构建 :class:`cs_checks.Context` 与基础元信息。"""
    project = os.path.abspath(args.project or os.getcwd())
    java_files, scope, scope_path, scope_note = _build_java_scope(
        project, args.path, args.changed)
    mode, mode_note, constraint_path = cs_checks.detect_mode(project)
    if args.mode and args.mode != "auto":
        mode = args.mode
        mode_note = "由 --mode 强制指定"
    if args.constraints:
        constraint_path = os.path.abspath(args.constraints)
        mode_note = "由 --constraints 指定约束文件"
    ctx = cs_checks.Context(
        project=project,
        java_files=java_files,
        scope=scope,
        scope_path=scope_path,
        mode=mode,
        mode_note=mode_note,
        constraint_path=constraint_path,
        changed_set=set(java_files) if scope == "changed" else set(),
        max_findings=args.max_findings,
    )
    return ctx, scope_note


def _apply_renames(project, renames):
    """执行 --fix-renames：只重命名 docs/ 下的 .md，返回已执行列表。"""
    applied = []
    docs_root = os.path.abspath(os.path.join(project, "docs"))
    for r in renames:
        if not r.get("apply") or not r.get("new"):
            continue
        old_abs = os.path.abspath(os.path.join(project, r["old"]))
        new_abs = os.path.abspath(os.path.join(project, r["new"]))
        if not old_abs.startswith(docs_root + os.sep):
            continue
        if not old_abs.lower().endswith(".md"):
            continue
        if os.path.exists(new_abs):
            continue
        parent = os.path.dirname(new_abs)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        os.rename(old_abs, new_abs)
        applied.append((r["old"], r["new"]))
    return applied


def build_report(ctx, scope_note, max_findings):
    """执行核对并组装报告 dict。"""
    renames_raw = cs_checks.detect_renames(ctx.project)
    items, summary = cs_checks.run_all(ctx, only=ctx._only, skip=ctx._skip)
    pending = [it.id for it in items if it.status == cs_checks.STATUS_FAIL]
    renames = [{"old": r["old"], "new": r["new"], "reason": r["reason"]}
               for r in renames_raw]
    report = {
        "project": ctx.project,
        "scope": ctx.scope,
        "scope_path": ctx.scope_path,
        "scope_note": scope_note,
        "mode": ctx.mode,
        "mode_note": ctx.mode_note,
        "constraint_path": ctx.constraint_path or "",
        "generated_at": _now_local().astimezone().isoformat(timespec="seconds"),
        "tool_version": TOOL_VERSION,
        "renames": renames,
        "items": [it.to_dict() for it in items],
        "summary": summary,
        "pending_confirmation": pending,
    }
    return report, renames_raw


def main(argv=None):
    """CLI 主入口，返回退出码（0 无失败 / 1 有失败 / 2 用法或内部错误）。"""
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="check_standards.py",
        description="机械执行 check-standards 的 33 项代码规范核对（Python 标准库）",
    )
    parser.add_argument("--project", default=None, help="项目根目录（默认当前目录）")
    parser.add_argument("--path", default=None, help="src 代码扫描范围：目录或文件")
    parser.add_argument("--changed", action="store_true", help="只扫 git 改动文件")
    parser.add_argument("--mode", choices=["auto", "standard", "legacy"], default="auto")
    parser.add_argument("--constraints", default=None, help="显式 2.1 约束文件")
    parser.add_argument("--format", choices=["md", "json"], default="md")
    parser.add_argument("--output", default=None, help="写入文件而非 stdout")
    parser.add_argument("--only", default=None, help="只跑这些检查 id，逗号分隔")
    parser.add_argument("--skip", default=None, help="跳过这些检查 id，逗号分隔")
    parser.add_argument("--max-findings", type=int, default=20, help="每项证据条数上限")
    parser.add_argument("--fix-renames", action="store_true", help="实际执行 docs/ 重命名")
    parser.add_argument("-q", "--quiet", action="store_true", help="不输出进度到 stderr")
    parser.add_argument("--self-test", action="store_true", help="运行内置自检后退出")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    def log(msg):
        if not args.quiet:
            sys.stderr.write(msg + "\n")

    try:
        ctx, scope_note = build_context(args)
    except Exception as exc:  # pragma: no cover - 防御性
        sys.stderr.write("初始化失败: %s\n" % exc)
        return 2

    ctx._only = _parse_ids(args.only)
    ctx._skip = _parse_ids(args.skip)

    log("[check-standards] 项目=%s 范围=%s(%d java 文件) 模式=%s"
        % (ctx.project, ctx.scope, len(ctx.java_files), ctx.mode))

    try:
        report, renames_raw = build_report(ctx, scope_note, args.max_findings)
    except Exception as exc:  # pragma: no cover - 防御性
        sys.stderr.write("核对执行失败: %s\n" % exc)
        return 2

    if args.fix_renames:
        applied = _apply_renames(ctx.project, renames_raw)
        for old, new in applied:
            log("[renamed] %s → %s" % (old, new))
        if not applied:
            log("[renamed] 无需重命名（或无可机械推导目标）")

    if args.format == "json":
        text = cs_report.render_json(report)
    else:
        text = cs_report.render_md(report, max_findings=args.max_findings)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(text)
                if not text.endswith("\n"):
                    fh.write("\n")
        except OSError as exc:
            sys.stderr.write("写入失败: %s\n" % exc)
            return 2
        log("[check-standards] 报告已写入 %s" % args.output)
    else:
        sys.stdout.write(text + "\n")

    return 1 if report["summary"].get("fail", 0) > 0 else 0


def _parse_ids(text):
    if not text:
        return set()
    out = set()
    for part in text.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


# ---------------------------------------------------------------------------
# 内置自检（--self-test）
# ---------------------------------------------------------------------------

_GOOD_SERVICE = '''package demo;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * 正常服务示例。
 */
@Slf4j
@Service
public class GoodService {

    /**
     * 计算总价。
     *
     * @return 总价
     */
    public int total() {
        // 1. 取基础值
        int base = 1;
        log.info("计算总价 base={}", base);
        return base;
    }
}
'''

_BAD_SERVICE = '''package demo;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 坏服务示例：缺 @Slf4j、缺方法注释、无日志、空 catch、裸 RuntimeException、事务缺 rollbackFor。
 */
@Service
public class BadService {

    public void save() {
        try {
            int x = compute();
        } catch (Exception e) {
        }
        throw new RuntimeException("boom");
    }

    @Transactional
    public void update() {
        log.info("x");
        int a = 1;
    }
}
'''

_ENTITY_A = '''package demo;

import com.baomidou.mybatisplus.annotation.TableName;

/**
 * 楼层实体 A。
 */
@TableName("hotel_floor")
public class HotelFloor {

    /**
     * 主键。
     */
    private Long id;
}
'''

_ENTITY_B = '''package demo;

import com.baomidou.mybatisplus.annotation.TableName;

/**
 * 楼层实体 B（同表重复映射）。
 */
@TableName("hotel_floor")
public class HotelFloorBak {

    /**
     * 主键。
     */
    private Long id;
}
'''

_FORM = '''package demo;

import jakarta.validation.constraints.NotBlank;

/**
 * 表单示例。
 */
public class DemoForm {

    /**
     * 名称。
     */
    @NotBlank(message = "参数错误")
    private String name;
}
'''

_DOCS_BAD_JSON = '''# 接口清单

（命名不规范示例，用于自检 FIX1）
'''

_MAPPER_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="demo.DemoMapper">
    <select id="selectOne" resultType="demo.HotelFloor">
        select * from hotel_floor where id = ${id}
    </select>
    <update id="updateName">
        UPDATE hotel_floor SET name = #{name}
    </update>
</mapper>
'''


def _write_fixture_project(root):
    """把自检用的内联 Java/XML 夹具写入临时工程目录。"""
    files = {
        "src/main/java/demo/GoodService.java": _GOOD_SERVICE,
        "src/main/java/demo/BadService.java": _BAD_SERVICE,
        "src/main/java/demo/HotelFloor.java": _ENTITY_A,
        "src/main/java/demo/HotelFloorBak.java": _ENTITY_B,
        "src/main/java/demo/DemoForm.java": _FORM,
        "docs/xwd-mall-center-接口清单（前后端通用）.md": _DOCS_BAD_JSON,
        "src/main/resources/mapper/demo/DemoMapper.xml": _MAPPER_XML,
    }
    for rel, content in files.items():
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
    return files


def _selftest_report(tmp):
    """用夹具工程跑一次核对，返回 (report, renames)。"""
    ns = argparse.Namespace(project=tmp, path=None, changed=False,
                            mode="auto", constraints=None, max_findings=50)
    ctx, scope_note = build_context(ns)
    ctx._only = set()
    ctx._skip = set()
    return build_report(ctx, scope_note, 50)


def _item_of(report, cid):
    for it in report["items"]:
        if it["id"] == cid:
            return it
    return None


def run_self_test():
    """运行内置夹具自检：断言关键核对项命中预期状态，返回 0/1。"""
    import tempfile

    expected = {
        1: "fail",     # BadService 方法缺 Javadoc
        2: "fail",     # BadService.save 无日志
        5: "fail",     # BadService 缺 @Slf4j
        9: "manual",   # 接口清单存在但命名不符合 3.x.2 → manual（FIX1）
        12: "fail",    # mapper XML ${id}
        13: "fail",    # UPDATE 无 WHERE
        14: "fail",    # @Transactional 缺 rollbackFor
        18: "fail",    # 空 catch + RuntimeException
        19: "fail",    # catch (Exception e)
        22: "skip",    # 无 pageSize 字段声明 → skip（FIX2）
        23: "fail",    # message = "参数错误"
        33: "fail",    # hotel_floor 重复映射
    }
    failures = []
    with tempfile.TemporaryDirectory(prefix="cs_selftest_") as tmp:
        _write_fixture_project(tmp)
        report, renames = _selftest_report(tmp)
        status = {it["id"]: it["status"] for it in report["items"]}
        for cid, want in expected.items():
            got = status.get(cid)
            if got != want:
                failures.append("#%d 期望 %s，实际 %s" % (cid, want, got))

        item1 = _item_of(report, 1)
        note1 = item1["note"] if item1 else ""
        if "src/main/java" not in note1:
            failures.append("#1 未声明扫描范围: %r" % note1)
        if not any(r["old"].endswith("接口清单（前后端通用）.md") and r["new"] == ""
                   for r in renames):
            failures.append("第0步未标记非规范接口清单命名: %r" % renames)

        # 顺带验证 JSON 渲染不抛异常
        try:
            cs_report.render_json(report)
            cs_report.render_md(report)
        except Exception as exc:  # pragma: no cover - 防御性
            failures.append("报告渲染异常: %s" % exc)

    if failures:
        sys.stderr.write("[self-test] FAIL\n")
        for f in failures:
            sys.stderr.write("  - %s\n" % f)
        return 1
    sys.stderr.write("[self-test] PASS（%d 项状态断言 + FIX1/2/3 行为断言全部符合预期）\n"
                     % len(expected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
