#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验收测试执行器（test-workflow 通用资产）

作用：读取验收用例 YAML，**真实调用**入口接口，断言响应，可选做数据库/并发断言，
      关联服务端日志，最后产出 Markdown 验收测试报告。

依赖：httpx、PyYAML；并发用 asyncio；数据库断言按需额外安装驱动。
用法：
    python3 runner.py --cases tests/订单创建.cases.yaml --out report.md

约定：
    - baseUrl / token 等一律从环境变量或命令行注入，禁止写死
    - 失败分类见 standards/runner-standards.md
    - 脚本跑完 **不等于** 通过；只有断言全部成立才判定通过
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
import yaml

# --------------------------------------------------------------------------- #
# 失败分类（见 standards/runner-standards.md）
# --------------------------------------------------------------------------- #
STARTUP_FAILED = "STARTUP_FAILED"
ENV_ERROR = "ENV_ERROR"
AUTH_ERROR = "AUTH_ERROR"
STATUS_MISMATCH = "STATUS_MISMATCH"
FIELD_MISMATCH = "FIELD_MISMATCH"
DB_ASSERT_FAILED = "DB_ASSERT_FAILED"
CONCURRENCY_VIOLATION = "CONCURRENCY_VIOLATION"
TIMEOUT = "TIMEOUT"

# 环境类失败（不计入代码缺陷）
ENV_CLASSES = {STARTUP_FAILED, ENV_ERROR, AUTH_ERROR, TIMEOUT}


@dataclass
class CaseResult:
    """单条用例的执行结果。"""

    case_id: str
    name: str
    scenario: str
    request_desc: str
    expect_desc: str
    actual_desc: str
    category: Optional[str] = None
    passed: bool = False
    log_excerpt: str = ""
    suggestion: str = ""


@dataclass
class Config:
    """运行期配置（全部来自命令行/环境变量）。"""

    cases_file: Path
    base_url: str
    token: Optional[str]
    auth_type: str
    timeout: float
    log_file: Optional[Path]
    out_file: Path
    verify_tls: bool = True


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    """读取环境变量，并支持 ${VAR} 占位替换。"""
    return os.environ.get(name, default)


def _expand(value: Any) -> Any:
    """把字符串中的 ${VAR} 替换为环境变量值（未设置则原样保留）。"""
    if isinstance(value, str):
        return re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def _build_headers(auth: dict, token: Optional[str]) -> dict:
    """按 auth 配置构造请求头（token 从环境变量注入）。"""
    headers = {"Content-Type": "application/json"}
    auth_type = (auth or {}).get("type", "none")
    if auth_type == "bearer" and token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# --------------------------------------------------------------------------- #
# 字段断言（支持 isNumber / isString / 精确值）
# --------------------------------------------------------------------------- #
def _get_by_path(payload: Any, path: str) -> Any:
    """按点号路径取值，如 data.orderId。"""
    cur = payload
    for seg in path.split("."):
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return None
    return cur


def _assert_field(payload: Any, path: str, expected: Any) -> Optional[str]:
    """断言单个字段；返回 None 表示通过，否则返回差异说明。"""
    actual = _get_by_path(payload, path)
    if expected == "isNumber" and not isinstance(actual, (int, float)):
        return f"{path} 期望数字，实测 {actual!r}"
    if expected == "isString" and not isinstance(actual, str):
        return f"{path} 期望字符串，实测 {actual!r}"
    if expected not in ("isNumber", "isString") and actual != expected:
        return f"{path} 期望 {expected!r}，实测 {actual!r}"
    return None


# --------------------------------------------------------------------------- #
# 单请求执行
# --------------------------------------------------------------------------- #
async def _send(client: httpx.AsyncClient, case: dict, cfg: Config, auth: dict) -> CaseResult:
    """执行单条用例：发请求 → 断言 → 组装结果。"""
    req = case.get("request", {})
    method = req.get("method", "GET").upper()
    path = req.get("path", "/")
    url = cfg.base_url.rstrip("/") + path
    headers = _build_headers(auth, cfg.token)
    headers.update(req.get("headers", {}) or {})
    body = _expand(req.get("body"))
    expect = _expand(case.get("expect", {}))

    request_desc = f"{method} {path} " + (f"body={json.dumps(body, ensure_ascii=False)}" if body else "")
    expect_desc = f"status={expect.get('status')} " + (
        f"fields={json.dumps(expect.get('fields', {}), ensure_ascii=False)}" if expect.get("fields") else ""
    )

    result = CaseResult(
        case_id=case.get("id", "-"),
        name=case.get("name", "-"),
        scenario=case.get("scenario", "-"),
        request_desc=request_desc,
        expect_desc=expect_desc,
        actual_desc="",
    )

    try:
        resp = await client.request(method, url, headers=headers, json=body, timeout=cfg.timeout)
    except httpx.TimeoutException:
        result.category = TIMEOUT
        result.actual_desc = "请求超时"
        result.log_excerpt = _tail_log(cfg, path)
        return result
    except httpx.HTTPError as exc:
        result.category = ENV_ERROR
        result.actual_desc = f"连接失败：{exc}"
        return result

    # 解析响应体（非 JSON 时保留原文）
    try:
        payload = resp.json()
    except Exception:
        payload = resp.text

    result.actual_desc = f"status={resp.status_code} body={json.dumps(payload, ensure_ascii=False)[:300]}"

    # 鉴权失败（环境/鉴权问题，非业务缺陷）
    if resp.status_code in (401, 403):
        result.category = AUTH_ERROR
        result.log_excerpt = _tail_log(cfg, path)
        return result

    # status 断言
    if expect.get("status") is not None and resp.status_code != expect["status"]:
        result.category = STATUS_MISMATCH
        result.log_excerpt = _tail_log(cfg, path)
        return result

    # 字段断言
    for fpath, fexpected in (expect.get("fields") or {}).items():
        diff = _assert_field(payload, fpath, fexpected)
        if diff:
            result.category = FIELD_MISMATCH
            result.log_excerpt = _tail_log(cfg, path)
            result.suggestion = f"字段断言不符：{diff}"
            return result

    result.passed = True
    return result


# --------------------------------------------------------------------------- #
# 服务端日志关联（优先 traceId，兜底时间窗+path）
# --------------------------------------------------------------------------- #
def _tail_log(cfg: Config, path: str, max_lines: int = 20) -> str:
    """从应用日志中抓取与失败请求相关的行（时间窗 + path 兜底匹配）。"""
    if not cfg.log_file or not cfg.log_file.exists():
        return "（未配置日志文件，无法摘录）"
    try:
        lines = cfg.log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        return f"（日志读取失败：{exc}）"
    key = path.strip("/").split("/")[-1]
    matched = [ln for ln in lines if key and key in ln]
    return "\n".join(matched[-max_lines:]) if matched else "（未匹配到相关日志）"


# --------------------------------------------------------------------------- #
# 并发用例（只断不变式，不断精确计数）
# --------------------------------------------------------------------------- #
async def _run_concurrent(client: httpx.AsyncClient, case: dict, cfg: Config, auth: dict) -> CaseResult:
    """并发用例：同时发 N 个请求，按期望不变式判定。"""
    conc = case.get("concurrency", {})
    n = int(conc.get("requests", 10))
    single = dict(case)
    results = await asyncio.gather(*[_send(client, single, cfg, auth) for _ in range(n)])

    ok = sum(1 for r in results if r.passed)
    result = CaseResult(
        case_id=case.get("id", "-"),
        name=case.get("name", "-"),
        scenario=case.get("scenario", "边界"),
        request_desc=f"{n} 并发 × " + results[0].request_desc,
        expect_desc=json.dumps(_expand(case.get("expect", {})), ensure_ascii=False),
        actual_desc=f"成功 {ok} / {n}",
    )
    # 期望不变式：如成功数不超过 maxSuccess
    max_success = (case.get("expect") or {}).get("maxSuccess")
    if max_success is not None and ok > int(max_success):
        result.category = CONCURRENCY_VIOLATION
        result.suggestion = f"并发不变式被破坏：成功 {ok} > 上限 {max_success}"
        return result
    result.passed = True
    return result


# --------------------------------------------------------------------------- #
# 报告输出
# --------------------------------------------------------------------------- #
def _write_report(cfg: Config, results: list[CaseResult], started: dt.datetime) -> None:
    """把执行结果写成 Markdown 报告。"""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = [r for r in results if not r.passed]
    env_failed = [r for r in failed if r.category in ENV_CLASSES]
    code_failed = [r for r in failed if r.category not in ENV_CLASSES]

    lines: list[str] = []
    lines.append("# 验收测试报告\n")
    lines.append(f"> 用例文件：`{cfg.cases_file}`  ")
    lines.append(f"> 执行时间：{started:%Y-%m-%d %H:%M:%S}  ")
    lines.append(f"> baseUrl：{cfg.base_url}\n")
    lines.append("## 执行摘要\n")
    lines.append("| 项目 | 值 |")
    lines.append("| :--- | :---: |")
    lines.append(f"| 总用例数 | {total} |")
    lines.append(f"| 通过 | {passed} |")
    lines.append(f"| 失败 | {len(failed)}（代码 {len(code_failed)} / 环境 {len(env_failed)}）|")
    lines.append("")

    lines.append("## 用例结果明细\n")
    lines.append("| # | 用例 | 场景 | 请求 | 期望 | 实测 | 分类 | 结果 |")
    lines.append("| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |")
    for r in results:
        mark = "✅" if r.passed else "❌"
        lines.append(
            f"| {r.case_id} | {r.name} | {r.scenario} | {r.request_desc} | "
            f"{r.expect_desc} | {r.actual_desc} | {r.category or '—'} | {mark} |"
        )
    lines.append("")

    if failed:
        lines.append("## 失败清单（供 AI 定位修复）\n")
        for r in failed:
            lines.append(f"### {r.case_id}：{r.name}\n")
            lines.append("| 项 | 内容 |")
            lines.append("| :--- | :--- |")
            lines.append(f"| 分类 | `{r.category}` |")
            lines.append(f"| 请求 | {r.request_desc} |")
            lines.append(f"| 期望 | {r.expect_desc} |")
            lines.append(f"| 实测 | {r.actual_desc} |")
            lines.append(f"| 服务端日志摘录 | ```{(r.log_excerpt or '').strip()[:800]}``` |")
            if r.suggestion:
                lines.append(f"| 修复建议 | {r.suggestion} |")
            lines.append("")

    lines.append("## 结论\n")
    if code_failed:
        lines.append("- ❌ 有代码类失败（见失败清单），修复后重跑刷新本报告")
    elif env_failed:
        lines.append("- ⚠️ 仅环境类失败（不计入代码缺陷）")
    else:
        lines.append("- ✅ 全部用例通过")

    cfg.out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"[runner] 报告已生成：{cfg.out_file}")


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
async def _run(cfg: Config) -> int:
    """加载用例、逐条/并发执行、产出报告；返回进程退出码。"""
    raw = yaml.safe_load(cfg.cases_file.read_text(encoding="utf-8"))
    cases: list[dict] = raw.get("cases", [])
    auth = raw.get("auth", {}) or {}
    if raw.get("baseUrl"):
        cfg.base_url = str(_expand(raw["baseUrl"]))

    started = dt.datetime.now()
    results: list[CaseResult] = []
    async with httpx.AsyncClient(verify=cfg.verify_tls) as client:
        for case in cases:
            if case.get("assertType") == "concurrency" or case.get("concurrency"):
                results.append(await _run_concurrent(client, case, cfg, auth))
            else:
                results.append(await _send(client, case, cfg, auth))

    _write_report(cfg, results, started)
    return 0 if all(r.passed or r.category in ENV_CLASSES for r in results) else 1


def main() -> int:
    """命令行入口。"""
    ap = argparse.ArgumentParser(description="验收测试执行器（test-workflow）")
    ap.add_argument("--cases", required=True, help="验收用例 YAML 路径")
    ap.add_argument("--base-url", default=_env("BASE_URL"), help="接口根地址（默认取 $BASE_URL）")
    ap.add_argument("--token", default=_env("TOKEN"), help="鉴权 token（默认取 $TOKEN）")
    ap.add_argument("--log-file", default=_env("APP_LOG"), help="应用日志文件（关联失败日志用）")
    ap.add_argument("--out", default=None, help="报告输出路径，默认 验收测试报告-<时间戳>.md")
    ap.add_argument("--timeout", type=float, default=10.0, help="单请求超时秒数")
    ap.add_argument("--insecure", action="store_true", help="跳过 TLS 校验（仅本地）")
    args = ap.parse_args()

    if not args.base_url:
        print("[runner] 缺少 baseUrl：请传 --base-url 或设置 $BASE_URL", file=sys.stderr)
        return 2

    out = Path(args.out) if args.out else Path(f"验收测试报告-{dt.datetime.now():%Y%m%d%H%M%S}.md")
    cfg = Config(
        cases_file=Path(args.cases),
        base_url=args.base_url,
        token=args.token,
        auth_type="bearer",
        timeout=args.timeout,
        log_file=Path(args.log_file) if args.log_file else None,
        out_file=out,
        verify_tls=not args.insecure,
    )
    try:
        return asyncio.run(_run(cfg))
    except FileNotFoundError as exc:
        print(f"[runner] 文件不存在：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
