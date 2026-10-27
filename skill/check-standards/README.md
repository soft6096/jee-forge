# check-standards

> Java 后端代码生成 / 修改完成后的**关键规范兜底自检**（收敛闸门）——**优先用仓内脚本 `scripts/check_standards.py`（纯 Python 标准库）本地一次跑完 57 项中可机械判定的部分**（零 token、无需模型逐条 grep + 整篇读 Java 文件），不可用时回退 grep/ast-grep；逐项核对关键规范，把没执行到位的项**提示用户确认是否补齐**。

规范条目多、分散在多个规范 skill（java-code-standards / comment-standards / database-standards / build-standards），AI 编码时容易漏执行。本 skill 是**最后一道兜底**：代码写完或改完后，逐项核对**全部核对项（无级别之分）**——方法级注释/日志全覆盖（public + private/抽取方法逐个核对）、框架/产物、SQL 与数据安全、事务与代码质量、场景化，每项附「文件:行号」证据；**任何一项未执行到位（无级别之分）统一提示用户确认是否补齐**。

## 它解决什么问题

- **注释没加全（含抽取的 private 方法）** → #1 方法级注释全覆盖：public + private/抽取方法逐个核对 Javadoc（类/字段/方法），无豁免
- **日志没加全（ServiceImpl 方法零日志）** → #2 方法级日志全覆盖：每个业务方法（含 private 抽取方法）方法体内 ≥1 条 INFO/WARN/ERROR 日志（debug 不算），大段逻辑无 INFO = ❌
- **中间产物命名/路径不规范** → 核对前先矫正（技术方案 3.x.1 / 接口清单 3.x.2 / 核对报告 5.2.x / 需求覆盖报告 5.3.x，去文件名中的任务 ID 前缀 T0xx，移入模块版本目录），防核对扫不到、验收引用断裂
- **check-standards 兜底没触发** → 本 skill 独立成可单独触发的 skill（不依赖 ai-dev-workflow 全流程），description 覆盖"写完代码/改完代码/提交前检查"等触发时机

## 机械核对脚本（零 token 加速）

仓内 `scripts/check_standards.py`（**纯 Python 标准库、无依赖、无网络**）把 57 项中**可机械判定的部分在本地一次跑完**，输出 Markdown / JSON 报告——**替代模型逐条 grep/ast-grep + 整篇读 Java 文件**，模型只读"结论 + 未通过项证据"，语义判断与人确认闸门不变。

```bash
# 默认：只扫本次 git 改动文件（AI 刚写完代码的兜底自检主场景）
python3 scripts/check_standards.py --project <项目根> --format json --output .cs-report.json
python3 scripts/check_standards.py --project <项目根> --verify --before .cs-before.json --after .cs-after.json  # 修复后核对（已修 + 无回退）

# 强制全项目扫描（全量体检/看存量问题才用；默认只扫改动，不需要就不加）
python3 scripts/check_standards.py --project <项目根> --all

python3 scripts/check_standards.py --project <项目根> --path src/main/java/com/x/order   # 指定目录（只传真正改动的目录；相对路径按 CWD 解析，解析不到回退按 --project）
python3 scripts/check_standards.py --project <项目根> --changed                          # 显式只扫本次改动（同默认）
python3 scripts/check_standards.py --self-test                                           # 内置夹具自检
```

- **环境**：Python 3.8+，仅标准库；Windows 用 `py -3` / `python`；未装 Python → 按 SKILL.md「标准检查指令」手工执行（降级，判据完全一致）。
- **默认范围 = 本次改动**：不传 `--path`/`--all` → 只扫 git 改动的 `.java`，报告与 stderr 注明「默认只扫本次改动文件；如需全量请加 `--all`」；**取不到改动 → 回退全项目**并写明「未检测到 git 改动，已回退全项目扫描」（**绝不返回 0 文件全项 PASS 的静默假绿**）。要全量体检才显式 `--all`。
- **别在 AI 流程里传大范围 `--path`**：整模块/项目根会扫出几百上千个存量文件，又慢又把存量违规混进本次核对结论（曾发生传整模块扫 849~4874 个文件的极慢事故）。
- **边界**：脚本只做机械扫描，**语义项（#3/#4/#24~#27/#30~#32 等）标 `manual/warn` 附候选证据，绝不假装通过**；默认只读源码，`--fix-renames` 才动 `docs/` 下的 `.md`。
- **空范围防假绿**：`--path` 扫到 0 个 `.java` → **exit 2**（用法错误，不产出核对结论）；回退/`--all` 的 `project` 范围为空 → 退出码不变，但报告「范围说明」打出 `⚠️ 未扫到任何 .java 文件…结果不可信`。相对 `--path` 按 CWD 解析、失败时回退按 `--project` 解析（详见 [`scripts/README.md`](scripts/README.md)）。
- **详细参数与 57 项映射**见 [`scripts/README.md`](scripts/README.md)。

## 安装

将本目录复制到你的 skills 目录：

```bash
# OpenCode / Codex
cp -r check-standards ~/.agents/skills/

# Claude Code
cp -r check-standards ~/.claude/skills/
```

> 建议与配套规范 skill 一起安装：`ai-dev-workflow`、`java-code-standards`、`comment-standards`、`database-standards`、`build-standards`、`test-workflow`、`legacy-onboarding`。

## 触发方式

**方式 A：自然语言（推荐）**——代码写完/改完后对 Agent 说：

| 你想做什么 | 对 Agent 说 |
|---|---|
| 写完代码后兜底自检 | "代码写完了，跑一下规范自检" / "帮我核对一下代码规范" |
| 检查注释/日志是否齐全 | "检查一下注释和日志有没有加全" |
| 提交前检查 | "提交前过一遍关键规范核对" |
| 验收复核 | "对照规范核对报告复核" |

**方式 B：配合 ai-dev-workflow 流程**——`/check-standards <项目路径>`（ai-dev-workflow 5.2 规范核对节点 / 5.3 需求覆盖时自动触发本 skill）。

## 核对范围（全部核对项无级别之分，任何一项未执行都要与用户确认）

| 组 | 项 |
|---|---|
| 方法与日志覆盖（新代码必核） | #1 方法级注释全覆盖（public + private/抽取方法 Javadoc）/ #2 方法级日志全覆盖（每方法体内 ≥1 条 INFO/WARN/ERROR，debug 不算）/ #3 步骤注释+WHY / #4 禁翻译式 / #5 全类 @Slf4j 无 System.out |
| 框架与产物 | 接口文档支持 / 日志框架支持 / SQL 在 XML / JSON 入参出参产物 |
| SQL 与数据安全 | SQL 注释 / DDL 注释 / SQL 注入 / UPDATE-DELETE 带 WHERE |
| 事务与代码质量 | 事务 rollbackFor / 构造器注入 / 分层边界 / Entity 不暴露 / 异常处理 / 命名 / 统一返回体 / 密码加密 / 分页上限 |
| 场景化 + 其余 | Job 防重入 / Listener 幂等 / 文件上传安全 / 写接口幂等 / 敏感信息 / 集合命名 / 魔法值 / 公共组件复用 |
| 代码格式（#34–#38） | #34 行尾空白与 Tab / #35 行宽超限 / #36 连续空行 / #37 import 卫生 / #38 空格（启发式；花括号类判定归 #57） |
| 命名/结构/卫生（#39–#44） | #39 命名规范（大小写/形式，含方法名非单字母）/ #40 类与文件结构 / #41 书写卫生 / #42 字符串比较（启发式）/ #43 遗留标记 / #44 变量命名（启发式） |
| 缩进·import·规模·成对（#45–#49） | #45 缩进一致性（启发式：4 空格倍数 / 注解对齐 / 续行不少于 +8，超出不报 / case +4（严格）/ 数组初始化 +4 或 +8 均合规 / 枚举常量参数折行不判）/ #46 import 顺序（启发式）/ #47 方法长度 / #48 方法参数个数 / #49 equals/hashCode 成对 |
| 书写细项（#50–#57） | catch 形参命名 / 静态变量命名 / 逗号分号后空格 / 成员之间空行 / 一行一声明 / 一行一语句 / package·import 不换行 / #57 花括号必写与位置（`{` 须在行尾，`}` 与 `else`/`catch`/`finally` 须同行） |

## 核心原则

1. **优先运行脚本、实际执行扫描，禁止凭记忆答 ✅**——机械项优先由 `scripts/check_standards.py` 本地跑出（零 token），无 Python 时用 grep/ast-grep 手工执行；每项附「文件:行号」证据
2. **所有未到位项（无级别之分）统一提示用户确认是否补齐**——人确认后才动手改代码，不自动默默补，不存在"参考项可跳过"
3. **先判模式**（标准 / 存量适配），选型敏感项按项目约束判定，非规范默认值一刀切

## 配套 skill 生态

| skill | 职责 |
|---|---|
| [ai-dev-workflow](https://github.com/soft6096/jee-forge/tree/main/skill/ai-dev-workflow) | 流程编排（需求→方案→任务→验收），5.2 规范核对节点调用本 skill |
| [java-code-standards](https://github.com/soft6096/jee-forge/tree/main/skill/java-code-standards) | Java 代码规范（本 skill 核对项的规范出处） |
| [comment-standards](https://github.com/soft6096/jee-forge/tree/main/skill/comment-standards) | 注释规范（全量注释含 private/抽取方法） |
| [database-standards](https://github.com/soft6096/jee-forge/tree/main/skill/database-standards) | SQL/表/索引规范 |
| [build-standards](https://github.com/soft6096/jee-forge/tree/main/skill/build-standards) | 构建/依赖规范 |
| [test-workflow](https://github.com/soft6096/jee-forge/tree/main/skill/test-workflow) | 验收测试工具（按需生成，默认不生成不执行） |
| [legacy-onboarding](https://github.com/soft6096/jee-forge/tree/main/skill/legacy-onboarding) | 存量项目接入 |
