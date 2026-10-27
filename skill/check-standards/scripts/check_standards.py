#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-standards CLI：机械执行 SKILL.md 的 57 项代码规范核对。

用法见 scripts/README.md。纯标准库；无需 ast-grep；rg 可选（未使用亦可）。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cs_checks  # noqa: E402
import cs_java as J  # noqa: E402
import cs_registry  # noqa: E402
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


_DEFAULT_CHANGED_HINT = "默认只扫本次改动文件；如需全量请加 --all"


def _build_java_scope(project, path, changed, scan_all=False):
    """确定扫描范围的 Java 文件，返回 (files, scope, scope_path, note)。

    优先级（高 → 低）：

    1. ``--path`` / ``--changed``（显式指定，行为与旧版一致）；
    2. ``--all`` → 强制全项目扫描；
    3. 默认（什么都不传）→ 先尝试 git 改动文件：取到 ≥1 个 ``.java`` 走 ``changed``，
       否则**回退全项目扫描**。

    WHY: 「AI 刚写完代码跑兜底自检」才是主场景，默认扫全仓既慢又没必要（曾发生调用方
    传整模块 ``--path`` 扫 849~4874 个文件导致极慢的事故）。但**绝不能**因「无 git /
    无改动」就返回 0 文件全项 PASS——那正是本工具踩过的「静默假通过」坑，故默认取不到
    git 改动时必须回退全项目，而不是空范围。

    空范围（0 个 .java）必须在 note 里显式告警：否则范围解析错误会被下游当成
    「无违规 → 全项 PASS」，产出假绿结论。
    """
    if changed:
        files, note = J.git_changed_java_files(project)
        if not files:
            note = (note + "；" if note else "") + "本次无 Java 改动（空范围为合法结果）"
        return files, "changed", project, note
    if path:
        ap = os.path.abspath(path)
        # WHY: 相对 --path 按 CWD 解析；当 CWD 与 --project 不是同一个目录时会解析到错误位置，
        #       表现为「扫到 0 个文件 → 所有核对项假 PASS」。此处回退按 project 再解析一次，
        #       只有仍不存在才认定为空。
        if not os.path.exists(ap) and not os.path.isabs(path):
            alt = os.path.abspath(os.path.join(project, path))
            if os.path.exists(alt):
                ap = alt
        files = J.iter_java_files([ap])
        if not files:
            return (files, "path", ap,
                    "⚠️ --path 未扫到任何 .java 文件（解析为 %s）：结果不可信，"
                    "请确认路径存在；相对路径按当前工作目录解析，跨目录请用绝对路径" % ap)
        return files, "path", ap, "指定路径扫描"
    fallback_note = ""
    if not scan_all:
        # 默认：先试 git 改动（与显式 --changed 同一口径），取到就只扫改动
        hit, git_note = J.git_changed_java_files(project)
        if hit:
            return (hit, "changed", project,
                    "%s（%s）" % (_DEFAULT_CHANGED_HINT, git_note or "git 改动"))
        # 取不到改动 → 回退全项目（绝不返回空范围，防「静默假通过」）
        fallback_note = ("未检测到 git 改动（%s），已回退全项目扫描；%s"
                         % (git_note or "无改动", _DEFAULT_CHANGED_HINT))
    roots = J.find_maven_java_roots(project)
    if not roots:
        src = os.path.join(project, "src")
        roots = [src] if os.path.isdir(src) else [project]
    files = J.iter_java_files(roots)
    if not files:
        return (files, "project", project,
                "⚠️ 未扫到任何 .java 文件（默认范围 src/main/java）：结果不可信，"
                "请确认 --project 是否正确")
    if scan_all:
        return files, "project", project, "全项目扫描（--all 显式指定）"
    return files, "project", project, fallback_note


def build_context(args):
    """根据命令行参数构建 :class:`cs_checks.Context` 与基础元信息。"""
    project = os.path.abspath(args.project or os.getcwd())
    java_files, scope, scope_path, scope_note = _build_java_scope(
        project, args.path, args.changed, getattr(args, "scan_all", False))
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
        resources_scope=getattr(args, "resources_scope", "auto"),
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


def _attach_judgment(item):
    """给单个核对项附加判据摘要。

    WHY 写进报告：模型对 manual/warn 项做人工判定时，若回读 references/checklist.md（≈19KB）
    等于把瘦身省下的 token 又付回去；判据随结论一起给出，模型只需读这几行。
    """
    item["judgment"] = cs_checks.CHECK_GUIDE.get(item.get("id"), "")
    return item


def _print_explain():
    """打印 57 项的 id / 名称 / 判据摘要（--explain）。"""
    for cid in sorted(cs_checks.CHECK_NAMES):
        print("#%d %s" % (cid, cs_checks.CHECK_NAMES[cid]))
        guide = cs_checks.CHECK_GUIDE.get(cid, "")
        print("    判据: %s" % (guide if guide else "（未登记，见 references/checklist.md）"))
    return 0


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
        "registry_manifest": cs_registry.scan_registry_manifest(
            ctx.project, ctx.java_files),
        "items": [_attach_judgment(it.to_dict()) for it in items],
        "summary": summary,
        "pending_confirmation": pending,
    }
    return report, renames_raw


def run_verify(before_path, after_path):
    """对比两份报告 JSON，断言「原未通过项已修（红→绿）+ 无任何项回退」。

    WHY: 修复后只"重跑一次"并不构成验证——必须由脚本断言：① 原 fail/warn/manual 的项已变
    pass；② 原 pass 的项没有变坏（快照对照，防"改 A 坏 B"）。两类断言均为回归测试的成熟做法。
    manual→manual 的项脚本判不了，单列「无机器验证」交人工确认。

    只读，不写任何文件。退出码：0 = 达标；1 = 存在未修好或回退；2 = 用法/读取错误。
    """
    if not before_path or not after_path:
        sys.stderr.write("用法错误：--verify 需同时提供 --before 与 --after 两份 JSON 报告\n")
        return 2
    try:
        with open(before_path, encoding="utf-8") as fh:
            before = json.load(fh)
        with open(after_path, encoding="utf-8") as fh:
            after = json.load(fh)
    except (OSError, ValueError) as exc:
        sys.stderr.write("读取报告失败：%s\n" % exc)
        return 2

    def by_id(rep):
        return {it.get("id"): it for it in rep.get("items", [])}

    b, a = by_id(before), by_id(after)
    bad = ("fail", "warn", "manual")
    fixed, still, regressed, unverifiable = [], [], [], []

    for cid in sorted(set(b) | set(a)):
        ib, ia = b.get(cid) or {}, a.get(cid) or {}
        sb, sa = ib.get("status"), ia.get("status")
        name = ia.get("name") or ib.get("name") or ""
        if sb in bad and sa == "pass":
            fixed.append((cid, name, len(ib.get("evidence", []))))
        elif sb in bad and sa in bad:
            if sb == "manual" and sa == "manual":
                unverifiable.append((cid, name))
            else:
                still.append((cid, name, len(ia.get("evidence", []))))
        elif sb == "pass" and sa in bad:
            regressed.append((cid, name, sa))

    if fixed:
        print("✅ 已修（红→绿）：" + "、".join(
            "#%d %s（原 %d 处 → 0）" % (c, n, e) for c, n, e in fixed))
    for c, n, e in still:
        print("❌ #%d %s：原问题仍在（%d 处）" % (c, n, e))
    for c, n, s in regressed:
        print("⚠️ 回退：#%d %s 由 pass 变为 %s" % (c, n, s))
    if unverifiable:
        print("ℹ️ 无机器验证（manual 项，需人工确认）："
              + "、".join("#%d %s" % (c, n) for c, n in unverifiable))
    ok = not still and not regressed
    print("结论：%s（已修 %d；未修好 %d；回退 %d；无机器验证 %d）"
          % ("✅ 通过" if ok else "❌ 未通过",
             len(fixed), len(still), len(regressed), len(unverifiable)))
    return 0 if ok else 1


def main(argv=None):
    """CLI 主入口，返回退出码（0 无失败 / 1 有失败 / 2 用法或内部错误）。"""
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="check_standards.py",
        description="机械执行 check-standards 的 57 项代码规范核对（Python 标准库）",
    )
    parser.add_argument("--project", default=None, help="项目根目录（默认当前目录）")
    parser.add_argument("--path", default=None, help="src 代码扫描范围：目录或文件")
    parser.add_argument("--changed", action="store_true", help="只扫 git 改动文件")
    parser.add_argument("--all", dest="scan_all", action="store_true",
                        help="强制全项目扫描（默认只扫本次 git 改动文件；"
                             "无改动或取不到改动时自动回退全项目）")
    parser.add_argument("--mode", choices=["auto", "standard", "legacy"], default="auto")
    parser.add_argument("--constraints", default=None, help="显式 2.1 约束文件")
    parser.add_argument("--format", choices=["md", "json"], default="md")
    parser.add_argument("--output", default=None, help="写入文件而非 stdout")
    parser.add_argument("--only", default=None, help="只跑这些检查 id，逗号分隔")
    parser.add_argument("--skip", default=None, help="跳过这些检查 id，逗号分隔")
    parser.add_argument("--max-findings", type=int, default=20, help="每项证据条数上限")
    parser.add_argument("--resources-scope", choices=["auto", "path", "project"],
                        default="auto",
                        help="资源类文件（pom/日志配置/Mapper XML/SQL/文档）的收敛范围："
                             "auto=--path 子树 + 集中目录下按模块命名的文件（默认）；"
                             "path=仅 --path 子树；project=全项目（旧行为）")
    parser.add_argument("--verify", action="store_true",
                        help="对比两份报告（--before 基线 + --after 修复后）：断言原未通过项已修"
                             "（红→绿）且无任何项回退；只读，不写文件")
    parser.add_argument("--before", default=None, help="--verify 用的基线 JSON 报告")
    parser.add_argument("--after", default=None, help="--verify 用的修复后 JSON 报告")
    parser.add_argument("--fix-renames", action="store_true", help="实际执行 docs/ 重命名")
    parser.add_argument("-q", "--quiet", action="store_true", help="不输出进度到 stderr")
    parser.add_argument("--self-test", action="store_true", help="运行内置自检后退出")
    parser.add_argument("--explain", action="store_true",
                        help="只打印 57 项的判据摘要后退出（供模型判 manual/warn 项，"
                             "免读 references/checklist.md 全篇）")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if args.explain:
        return _print_explain()

    if args.verify:
        return run_verify(args.before, args.after)

    cs_checks.PROGRESS_QUIET = args.quiet

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
    # 范围说明单独一行打进 stderr：默认只扫改动/回退全项目都要让调用方一眼看见，防误判
    if scope_note:
        log("[check-standards] 范围说明：%s" % scope_note)

    # --path 指定了范围却扫到 0 个 Java 文件 → 用法错误，避免「空范围全绿」被当成通过
    if ctx.scope == "path" and not ctx.java_files:
        sys.stderr.write(
            "[check-standards] 错误：--path 未扫到任何 Java 文件（%s），"
            "按用法错误退出（exit 2），不产出核对结论。\n" % ctx.scope_path)
        return 2

    # 成本护栏：先把规模与预计耗时摊开，大范围必须由调用方显式承担代价。
    # WHY 拒绝「>2000 且未显式 --all」：曾出现单次扫 4874 文件跑 55 分钟才被中止的事故，
    #     默认踩进大范围属设计缺陷——"全量"必须是显式选择，而不是顺着 --path 掉进去。
    n_files = len(ctx.java_files)
    log("[check-standards] 本次范围 %d 个 java 文件，预计约 %.1f 秒"
        % (n_files, n_files * 0.02))
    if n_files > 2000 and not args.scan_all:
        sys.stderr.write(
            "[check-standards] 错误：本次范围 %d 个文件（> 2000）且未显式指定 --all。\n"
            "  请二选一：加 --all（确认做全量体检）；或去掉大范围 --path，"
            "改用默认（只扫本次改动）或限定到本次真正改动的目录。\n" % n_files)
        return 2
    if n_files > 1000:
        log("[check-standards] ⚠️ 范围较大（%d 个文件），建议用默认范围"
            "（只扫本次改动）以大幅提速" % n_files)

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

    /**
     * 字符串比较（#42 正例：字符串字面量用 ==）。
     *
     * @param name 名称
     * @return 是否为 x
     */
    public boolean isX(String name) {
        return name == "x";
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


_MULTILINE_ANNO_API = '''package demo;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 误报回归夹具：多行注解 + 泛型 + 接口内嵌套类。
 */
@SuppressWarnings({
        "unchecked",
        "rawtypes"
})
public interface MultiLineAnnoApi {

    /**
     * 统计数量。
     *
     * @param ids 标识列表
     * @return 数量
     */
    default int count(List<Long> ids) {
        Map<Long, String> map = new HashMap<>();
        return ids.size() + map.size();
    }

    /**
     * 内部载荷。
     */
    class Payload {

        /**
         * 名称。
         */
        private String name;

        /**
         * 取名称。
         *
         * @return 名称
         */
        public String getName() {
            return name;
        }
    }
}
'''

_DEMO_STATUS = '''package demo;

/**
 * 演示状态枚举。
 */
public enum DemoStatus {

    /** 成功。 */
    OK,

    /** 失败。 */
    FAIL;
}
'''

_ENUM_COMPARE_SERVICE = '''package demo;

import lombok.extern.slf4j.Slf4j;

/**
 * 枚举比较回归夹具：枚举用 == 是正确写法，不应被判为字符串比较。
 */
@Slf4j
public class EnumCompareService {

    /**
     * 判断订单是否为成功状态。
     *
     * @param orderStatus 订单状态
     * @return 是否成功
     */
    public boolean isSuccess(DemoStatus orderStatus) {
        // 1. 枚举比较：Java 推荐写法
        log.info("判断订单状态 orderStatus={}", orderStatus);
        // 2. 返回比较结果
        return orderStatus == DemoStatus.OK;
    }
}
'''

_LONG_METHOD_BODY = "\n".join("        int value%d = %d;" % (i, i) for i in range(105))

_LONG_METHOD_SERVICE = '''package demo;

/**
 * 超长方法夹具（#47 MethodLength 正例）。
 */
public class LongMethodComponent {

    /**
     * 超长方法：代码行数超过 100。
     *
     * @return 合计
     */
    public int huge() {
%s
        return 0;
    }
}
''' % _LONG_METHOD_BODY

_VIOLATION_SERVICE = '''package demo;

import java.util.List;
import org.springframework.stereotype.Service;

/**
 * 违规夹具：import 顺序（java.* 前置）、缩进非 4 倍数、形参过多、equals 缺 hashCode。
 */
@Service
public class ViolationService {

    /** 标识列表。 */
    private List<String> idList;

   /**
    * 八参方法。
    *
    * @param a 参数 a
    * @param b 参数 b
    * @param c 参数 c
    * @param d 参数 d
    * @param e 参数 e
    * @param f 参数 f
    * @param g 参数 g
    * @param h 参数 h
    * @return 合计
    */
   public int many(int a, int b, int c, int d, int e, int f, int g, int h) {
      return a + b + c + d + e + f + g + h;
   }

    /**
     * 仅重写 equals，缺 hashCode。
     *
     * @param other 其他对象
     * @return 是否相等
     */
    @Override
    public boolean equals(Object other) {
        return other instanceof ViolationService;
    }
}
'''


_FORMAT_BAD = '''package demo;

import java.util.List;

/**
 * 格式回归夹具（反例）：单字母方法名（#39）、`}` 与 else 换行分离（#57）、
 * 续行/case/数组初始化缩进不齐（#45 候选）。
 */
public class FormatSample {

    /**
     * 正常方法名（#39 正例）。
     *
     * @return 常量
     */
    public int ok() {
        // 1. 返回常量
        return 1;
    }

    /**
     * 单字母方法名（#39 反例）。
     *
     * @return 常量
     */
    public int a() {
        // 1. 返回常量
        return 2;
    }

    /**
     * 右花括号与 else 换行分离（#57 反例）。
     *
     * @param flag 开关
     * @return 结果
     */
    public int pick(boolean flag) {
        // 1. 分支判断
        if (flag) {
            return 1;
        }
        else {
            return 0;
        }
    }

    /**
     * 续行缩进不足（#45 反例：应相对语句起始行 +8）。
     *
     * @param valueList 值列表
     * @return 合计
     */
    public int sum(List<Integer> valueList) {
        // 1. 流式求和
        int total = valueList.stream()
            .mapToInt(Integer::intValue)
            .sum();
        // 2. 返回合计
        return total;
    }

    /**
     * case 标签缩进不齐（#45 反例：应相对 switch 缩进 +4）。
     *
     * @param type 类型
     * @return 名称
     */
    public String name(int type) {
        // 1. 分支选择
        switch (type) {
        case 1:
            return "a";
        default:
            return "b";
        }
    }

    /**
     * 数组初始化元素缩进不齐（#45 反例：应相对初始化起始行 +4）。
     *
     * @return 数值数组
     */
    public int[] numbers() {
        // 1. 返回初始化数组
        int[] arr = {
          1,
          2,
        };
        return arr;
    }
}
'''

_FORMAT_GOOD = '''package demo;

import java.util.List;

/**
 * 格式回归夹具（正例）：方法名、右花括号、续行/case/数组初始化缩进均合规，不应产生候选。
 */
public class FormatGoodSample {

    /**
     * 右花括号与 else 同行（#39/#57 正例）。
     *
     * @param flag 开关
     * @return 结果
     */
    public int pick(boolean flag) {
        // 1. 分支判断
        if (flag) {
            return 1;
        } else {
            return 0;
        }
    }

    /**
     * 续行缩进合规（#45 正例：相对语句起始行 +8）。
     *
     * @param valueList 值列表
     * @return 合计
     */
    public int sum(List<Integer> valueList) {
        // 1. 流式求和
        int total = valueList.stream()
                .mapToInt(Integer::intValue)
                .sum();
        // 2. 返回合计
        return total;
    }

    /**
     * case 标签缩进合规（#45 正例：相对 switch +4）。
     *
     * @param type 类型
     * @return 名称
     */
    public String flagName(int type) {
        // 1. 分支选择
        switch (type) {
            case 1:
                return "a";
            default:
                return "b";
        }
    }

    /**
     * 数组初始化元素缩进合规（#45 正例：相对初始化起始行 +4）。
     *
     * @return 数值数组
     */
    public int[] numbers() {
        // 1. 返回初始化数组
        int[] arr = {
            1,
            2,
        };
        return arr;
    }
}
'''

_FORMAT_EXCESS = '''package demo;

import java.util.List;

/**
 * 缩进「过量」回归夹具（正例）：续行缩进超出期望、数组元素相对 +8 均不应产生候选。
 * 对齐实测口径——续行只报「不足」（大于期望不报），数组初始化期望值为一组（+4 或 +8）。
 */
public class FormatExcessSample {

    /**
     * 续行超出期望（语句起始行缩进 8，续行缩进 24 = 相对 +16）→ 不报。
     *
     * @param valueList 值列表
     * @return 合计
     */
    public int sum(List<Integer> valueList) {
        // 1. 流式求和
        int total = valueList.stream()
                        .mapToInt(Integer::intValue)
                        .sum();
        // 2. 返回合计
        return total;
    }

    /**
     * 数组初始化元素相对 +8（初始化起始行缩进 8，元素缩进 16）→ 不报。
     *
     * @return 数值数组
     */
    public int[] numbers() {
        // 1. 返回初始化数组
        int[] arr = {
                1,
                2,
        };
        return arr;
    }
}
'''

_ENUM_FOLD = '''package demo;

/**
 * 枚举常量参数折行回归夹具（#45 正例）：枚举常量参数手工折行不参与缩进判定
 * （对齐实测口径——该工具对枚举常量参数折行不做 lineWrappingIndentation 判定）。
 */
public enum EnumFoldSample {

    /** 续行 +4（不应产生候选）。 */
    A(1, "x",
        "y"),

    /** 续行 +0（不应产生候选）。 */
    B(2, "x",
    "y"),

    /** 参数整体换行（不应产生候选）。 */
    C(
        3,
        "y");

    /** 值。 */
    private final int v;

    /** 名。 */
    private final String n;

    EnumFoldSample(int v, String n) {
        this.v = v;
        this.n = n;
    }
}
'''


def _write_fixture_project(root):
    """把自检用的内联 Java/XML 夹具写入临时工程目录。"""
    files = {
        "src/main/java/demo/GoodService.java": _GOOD_SERVICE,
        "src/main/java/demo/BadService.java": _BAD_SERVICE,
        "src/main/java/demo/HotelFloor.java": _ENTITY_A,
        "src/main/java/demo/HotelFloorBak.java": _ENTITY_B,
        "src/main/java/demo/DemoForm.java": _FORM,
        "src/main/java/demo/MultiLineAnnoApi.java": _MULTILINE_ANNO_API,
        "src/main/java/demo/DemoStatus.java": _DEMO_STATUS,
        "src/main/java/demo/EnumCompareService.java": _ENUM_COMPARE_SERVICE,
        "src/main/java/demo/LongMethodComponent.java": _LONG_METHOD_SERVICE,
        "src/main/java/demo/ViolationService.java": _VIOLATION_SERVICE,
        "src/main/java/demo/FormatSample.java": _FORMAT_BAD,
        "src/main/java/demo/FormatGoodSample.java": _FORMAT_GOOD,
        "src/main/java/demo/FormatExcessSample.java": _FORMAT_EXCESS,
        "src/main/java/demo/EnumFoldSample.java": _ENUM_FOLD,
        "docs/demo-mall-接口清单（前后端通用）.md": _DOCS_BAD_JSON,
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
    ns = argparse.Namespace(project=tmp, path=None, changed=False, scan_all=False,
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
    import subprocess
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
        38: "pass",    # FIX4：List<Long>/Map<Long,String> 泛型不再被误判为运算符缺空格
        40: "pass",    # FIX5：@SuppressWarnings 跨行注解不再导致"顶层类型缺 Javadoc"
        41: "pass",    # FIX6：接口内嵌套类的 public getter 不再被判为"接口冗余修饰符"
        39: "fail",    # 新增：FormatSample.a() 单字母方法名
        42: "fail",    # FIX7：枚举 == 已排除（EnumCompareService），但仍能命中 name == "x"
        45: "fail",    # 语句起始行缩进非 4 倍数 → fail（续行/case/数组仍为 manual 候选）
        46: "fail",    # ViolationService java.* 置于 org.* 之前 → import 顺序 fail
        47: "fail",    # 新增：LongMethodComponent.huge 代码 106 行 > 100
        48: "fail",    # 新增：ViolationService.many 形参 8 个 > 7
        49: "fail",    # 新增：ViolationService 重写 equals 未重写 hashCode
        57: "fail",    # 新增：FormatSample `}` 与 else 换行分离（RightCurly）
    }
    failures = []
    scope_trace = []
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

        def _ev_text(cid):
            """取某核对项的「说明 + 文件」全文，用于断言命中/未误报。"""
            it = _item_of(report, cid)
            if not it:
                return ""
            return " ".join(e["detail"] + " @" + e["file"] for e in it["evidence"])

        ev39 = _ev_text(39)
        if "方法名单字母: a" not in ev39:
            failures.append("#39 未命中单字母方法名反例: %r" % ev39)
        if "FormatGoodSample" in ev39:
            failures.append("#39 正例被误报: %r" % ev39)

        ev57 = _ev_text(57)
        if "右花括号" not in ev57:
            failures.append("#57 未命中 `}` 与 else 换行分离反例: %r" % ev57)
        if "FormatGoodSample" in ev57:
            failures.append("#57 正例被误报: %r" % ev57)

        ev45 = _ev_text(45)
        for kw in ("续行缩进", "case/default 缩进", "数组初始化元素缩进"):
            if kw not in ev45:
                failures.append("#45 未命中候选（%s）: %r" % (kw, ev45))
        if "FormatGoodSample" in ev45:
            failures.append("#45 正例被误报: %r" % ev45)
        # 过量方向锁：续行 > +8 与数组元素 +8 都应放行（超过期望不报 / 期望为一组）
        if "FormatExcessSample" in ev45:
            failures.append("#45 过量缩进被误报（续行应只报不足、数组期望为一组）: %r" % ev45)
        # 枚举常量参数折行不判定（实测口径）：该夹具不得出现任何 #45 证据
        if "EnumFoldSample" in ev45:
            failures.append("#45 枚举常量参数折行被误报: %r" % ev45)
        # 真阳性锁：普通方法链续行不足（缩进 12 < 期望 16）必须仍被报出，防误伤
        if "续行缩进 12 不足" not in ev45:
            failures.append("#45 未命中普通方法链续行不足（真阳性丢失）: %r" % ev45)

        # CLI 作用域回归：相对 --path 跨目录回退、坏路径显式告警、空 --path 按用法错误退出
        cwd_saved = os.getcwd()
        try:
            with tempfile.TemporaryDirectory(prefix="cs_scope_") as proj:
                demo_dir = os.path.join(proj, "src", "main", "java", "demo")
                os.makedirs(demo_dir)
                with open(os.path.join(demo_dir, "X.java"), "w",
                          encoding="utf-8") as fh:
                    fh.write(_GOOD_SERVICE)
                os.chdir(tempfile.gettempdir())      # CWD 与 --project 分离，复现原始缺陷

                files, _, scope_path, note = _build_java_scope(
                    proj, "src/main/java", False)
                if not files:
                    failures.append("相对 --path 跨目录未回退到 --project: %r" % note)
                elif not os.path.abspath(scope_path).startswith(
                        os.path.abspath(proj) + os.sep):
                    failures.append("相对 --path 回退后 scope_path 不在 --project 下: %r"
                                    % scope_path)

                bad_files, _, _, bad_note = _build_java_scope(proj, "no/such/dir", False)
                if bad_files or "未扫到任何 .java" not in bad_note:
                    failures.append("坏 --path 未给出空范围告警: files=%d note=%r"
                                    % (len(bad_files), bad_note))

                devnull = open(os.devnull, "w", encoding="utf-8")
                err_saved = sys.stderr
                sys.stderr = devnull
                try:
                    rc = main(["--project", proj, "--path", "no/such/dir",
                               "--only", "57", "-q"])
                finally:
                    sys.stderr = err_saved
                    devnull.close()
                if rc != 2:
                    failures.append("空 --path 未按用法错误退出：rc=%r（应为 2）" % rc)
        finally:
            os.chdir(cwd_saved)

        # 默认扫描范围回归：临时 git 仓库（已提交基线）验证 默认 changed / 无改动回退 project
        # / --all 强制全量 / --path 优先；防「无改动 → 0 文件全项 PASS」的静默假通过
        def _git_run(cwd, *argv):
            """在指定目录跑 git（带内联身份配置，不依赖全局 config），成功返回 True。"""
            cmd = ["git",
                   "-c", "user.email=selftest@example.com",
                   "-c", "user.name=selftest",
                   "-c", "commit.gpgsign=false"] + list(argv)
            try:
                proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, timeout=60)
            except (OSError, subprocess.SubprocessError):
                return False
            return proc.returncode == 0

        cwd_saved_default = os.getcwd()
        try:
            with tempfile.TemporaryDirectory(prefix="cs_default_scope_") as gproj:
                gsrc = os.path.join(gproj, "src", "main", "java", "demo")
                os.makedirs(gsrc)
                alpha = os.path.join(gsrc, "Alpha.java")
                with open(alpha, "w", encoding="utf-8") as fh:
                    fh.write(_GOOD_SERVICE)
                with open(os.path.join(gsrc, "Beta.java"), "w", encoding="utf-8") as fh:
                    fh.write(_GOOD_SERVICE)
                # 基线提交（含 .java）+ 一次不含 .java 的空提交，构成「无未提交改动」的干净状态
                git_ok = (_git_run(gproj, "init", "-q")
                          and _git_run(gproj, "add", ".")
                          and _git_run(gproj, "commit", "-q", "-m", "baseline")
                          and _git_run(gproj, "commit", "-q", "--allow-empty",
                                       "-m", "no java change"))
                if not git_ok:
                    failures.append("默认范围回归：临时 git 仓库初始化失败（git 不可用？）")
                else:
                    os.chdir(tempfile.gettempdir())   # CWD 与项目分离，贴近真实调用

                    # 断言 2：无未提交改动 → 默认回退 project，且文件数 > 0（而不是 0 个假绿）
                    f2, s2, _, n2 = _build_java_scope(gproj, None, False, False)
                    if s2 != "project":
                        failures.append("默认范围（无改动）应回退 project，实际 %s：%r" % (s2, n2))
                    elif not f2:
                        failures.append("默认范围（无改动）回退后文件数为 0（静默假通过）: %r" % n2)

                    # 制造未提交改动
                    with open(alpha, "a", encoding="utf-8") as fh:
                        fh.write("\n// selftest: uncommitted change\n")

                    # 断言 1：有改动 → 默认 changed，且只含被改动的那个文件
                    f1, s1, _, n1 = _build_java_scope(gproj, None, False, False)
                    if s1 != "changed":
                        failures.append("默认范围（有改动）应为 changed，实际 %s：%r" % (s1, n1))
                    elif [os.path.basename(x) for x in f1] != [os.path.basename(alpha)]:
                        failures.append("默认 changed 范围应只含被改动文件: %r" % f1)
                    if "--all" not in n1:
                        failures.append("默认 changed 范围说明未提示 --all：%r" % n1)

                    # 断言 3：--all 在有改动时仍强制全量
                    f3, s3, _, n3 = _build_java_scope(gproj, None, False, True)
                    if s3 != "project" or len(f3) < 2:
                        failures.append("--all 应强制全项目扫描（≥2 个 java），实际 %s/%d：%r"
                                        % (s3, len(f3), n3))

                    # 断言 4：--path 优先于 --all
                    f4, s4, _, n4 = _build_java_scope(gproj, "src/main/java/demo", False, True)
                    if s4 != "path" or not f4:
                        failures.append("--path 应优先于 --all，实际 %s/%d：%r"
                                        % (s4, len(f4), n4))

                    # 断言 5：新目录里的新文件也算「本次改动」（AI 生成新包/新模块的典型形态）。
                    # 若 git status 不加 -uall，未跟踪目录会被折叠成 `?? dir/` → 取不到文件，
                    # 默认范围会退化回全项目扫描（本断言即为该退化的锁）。
                    newdir = os.path.join(gproj, "src", "main", "java", "newfeat")
                    os.makedirs(newdir, exist_ok=True)
                    with open(os.path.join(newdir, "Gamma.java"), "w", encoding="utf-8") as fh:
                        fh.write(_GOOD_SERVICE)
                    f5, s5, _, n5 = _build_java_scope(gproj, None, False, False)
                    if s5 != "changed":
                        failures.append("新目录中的新文件应使默认范围保持 changed，实际 %s：%r"
                                        % (s5, n5))
                    elif not any(os.path.basename(x) == "Gamma.java" for x in f5):
                        failures.append("默认 changed 未包含新目录里的新文件: %r" % f5)

                    scope_trace.append("默认(无改动)=%s(%d 文件)" % (s2, len(f2)))
                    scope_trace.append("默认(有改动)=%s(%s)"
                                       % (s1, ",".join(os.path.basename(x) for x in f1)))
                    scope_trace.append("--all=%s(%d 文件)" % (s3, len(f3)))
                    scope_trace.append("--path+--all=%s(%d 文件)" % (s4, len(f4)))
        finally:
            os.chdir(cwd_saved_default)

        # 顺带验证 JSON 渲染不抛异常
        try:
            cs_report.render_json(report)
            cs_report.render_md(report)
        except Exception as exc:  # pragma: no cover - 防御性
            failures.append("报告渲染异常: %s" % exc)

    if scope_trace:
        sys.stderr.write("[self-test] 默认扫描范围实测：" + " / ".join(scope_trace) + "\n")
    if failures:
        sys.stderr.write("[self-test] FAIL\n")
        for f in failures:
            sys.stderr.write("  - %s\n" % f)
        return 1
    sys.stderr.write("[self-test] PASS（%d 项状态断言 + 第 0 步/报告渲染行为断言全部符合预期；"
                     "含 FIX4~FIX7 误报回归、#45~#49 新增项、#39/#45/#57 证据级断言"
                     "（正向命中 + 正例/过量不误报），以及 CLI 作用域回归"
                     "（相对 --path 跨目录回退 / 空 --path 按用法错误 exit 2）"
                     "与默认扫描范围回归（默认 changed / 无改动回退 project / --all / --path 优先））\n"
                     % len(expected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
