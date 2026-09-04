# check-standards

> Java 后端代码生成 / 修改完成后的**关键规范兜底自检**（收敛闸门）——用 grep/ast-grep 实际扫描产出，逐项核对关键规范，把没执行到位的项**提示用户确认是否补齐**。

规范条目多、分散在多个规范 skill（java-code-standards / comment-standards / database-standards / build-standards），AI 编码时容易漏执行。本 skill 是**最后一道兜底**：代码写完或改完后，逐项核对**全部核对项（无级别之分）**——方法级注释/日志全覆盖（public + private/抽取方法逐个核对）、框架/产物、SQL 与数据安全、事务与代码质量、场景化，每项附「文件:行号」证据；**任何一项未执行到位（无级别之分）统一提示用户确认是否补齐**。

## 它解决什么问题

- **注释没加全（含抽取的 private 方法）** → #1 方法级注释全覆盖：public + private/抽取方法逐个核对 Javadoc（类/字段/方法），无豁免
- **日志没加全（ServiceImpl 方法零日志）** → #2 方法级日志全覆盖：每个业务方法（含 private 抽取方法）方法体内 ≥1 条 INFO/WARN/ERROR 日志（debug 不算），大段逻辑无 INFO = ❌
- **中间产物命名/路径不规范** → 核对前先矫正（技术方案 3.x.1 / 接口清单 3.x.2 / 核对报告 5.2.x / 验收报告 5.3.x，去文件名中的任务 ID 前缀 T0xx，移入模块版本目录），防核对扫不到、验收引用断裂
- **check-standards 兜底没触发** → 本 skill 独立成可单独触发的 skill（不依赖 ai-dev-workflow 全流程），description 覆盖"写完代码/改完代码/提交前检查"等触发时机

## 安装

将本目录复制到你的 skills 目录：

```bash
# OpenCode / Codex
cp -r check-standards ~/.agents/skills/

# Claude Code
cp -r check-standards ~/.claude/skills/
```

> 建议与配套规范 skill 一起安装：`ai-dev-workflow`、`java-code-standards`、`comment-standards`、`database-standards`、`build-standards`、`test-standards`、`legacy-onboarding`。

## 触发方式

**方式 A：自然语言（推荐）**——代码写完/改完后对 Agent 说：

| 你想做什么 | 对 Agent 说 |
|---|---|
| 写完代码后兜底自检 | "代码写完了，跑一下规范自检" / "帮我核对一下代码规范" |
| 检查注释/日志是否齐全 | "检查一下注释和日志有没有加全" |
| 提交前检查 | "提交前过一遍关键规范核对" |
| 验收复核 | "对照规范核对报告复核" |

**方式 B：配合 ai-dev-workflow 流程**——`/check-standards <项目路径>`（ai-dev-workflow 5.2 规范核对节点 / 5.3 验收时自动触发本 skill）。

## 核对范围（全部核对项无级别之分，任何一项未执行都要与用户确认）

| 组 | 项 |
|---|---|
| 方法与日志覆盖（新代码必核） | #1 方法级注释全覆盖（public + private/抽取方法 Javadoc）/ #2 方法级日志全覆盖（每方法体内 ≥1 条 INFO/WARN/ERROR，debug 不算）/ #3 步骤注释+WHY / #4 禁翻译式 / #5 全类 @Slf4j 无 System.out |
| 框架与产物 | 接口文档支持 / 日志框架支持 / SQL 在 XML / JSON 入参出参产物 |
| SQL 与数据安全 | SQL 注释 / DDL 注释 / SQL 注入 / UPDATE-DELETE 带 WHERE |
| 事务与代码质量 | 事务 rollbackFor / 构造器注入 / 分层边界 / Entity 不暴露 / 异常处理 / 命名 / 统一返回体 / 密码加密 / 分页上限 |
| 场景化 + 其余 | Job 防重入 / Listener 幂等 / 文件上传安全 / 写接口幂等 / 敏感信息 / 集合命名 / 魔法值 / 公共组件复用 |

## 核心原则

1. **实际执行 grep/ast-grep，禁止凭记忆答 ✅**——每项附「文件:行号」证据
2. **所有未到位项（无级别之分）统一提示用户确认是否补齐**——人确认后才动手改代码，不自动默默补，不存在"参考项可跳过"
3. **先判模式**（标准 / 存量适配），选型敏感项按项目约束判定，非规范默认值一刀切

## 配套 skill 生态

| skill | 职责 |
|---|---|
| [ai-dev-workflow](https://github.com/soft6096/ai-dev-workflow) | 流程编排（需求→方案→任务→验收），5.2 规范核对节点调用本 skill |
| [java-code-standards](https://github.com/soft6096/java-code-standards) | Java 代码规范（本 skill 核对项的规范出处） |
| [comment-standards](https://github.com/soft6096/comment-standards) | 注释规范（全量注释含 private/抽取方法） |
| [database-standards](https://github.com/soft6096/database-standards) | SQL/表/索引规范 |
| [build-standards](https://github.com/soft6096/build-standards) | 构建/依赖规范 |
| [test-standards](https://github.com/soft6096/test-standards) | 测试规范 |
| [legacy-onboarding](https://github.com/soft6096/legacy-onboarding) | 存量项目接入 |

## License

MIT
