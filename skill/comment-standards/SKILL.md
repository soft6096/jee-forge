---
name: comment-standards
description: 约束 AI 生成代码注释的规范集（注释规范 + 存量注释补全工作流）。**只要产出/修改任何代码（Java 或其他语言）就必须加载本 skill——包括不走完整开发流程的零散请求（"写个 XX 接口"/"写个 Controller"/"帮我写这段代码"）：任何代码产物在返回用户前，本 skill 都必须已加载**——全量注释是硬性要求：所有类/变量/字段/方法（含测试方法、private/抽取方法）Javadoc + 方法体步骤注释 + // WHY: 注释，禁止大段代码无注释，**代码无注释 = 未完成，不得交付**。写公开 API 文档注释、行内注释、补全存量代码注释、审查注释质量时加载。触发场景：写注释、补注释、生成注释、注释规范审查、Javadoc 检查、写 Java 类/接口/方法、生成代码、实现功能、**没有需求文档/不走流程的直接写码请求**。WHEN NOT（不要因这些场景触发本 skill）：Java 结构/命名/分层/日志/事务规则 → java-code-standards；SQL/DDL/索引/分页 → database-standards（其中 SQL 注释格式归属 database-standards `standards/sql-standards.md` §1.5，本 skill 只提供"写业务含义、禁翻译 SQL 关键字"的通用原则）；纯 SQL/纯测试场景只加载对应 skill，本 skill 不重复定义。通用原则适用任何语言，示例以 Java 为主。代码生成完成后的注释覆盖率兜底核对见 check-standards skill（方法级注释全覆盖核对项 #1，含 private/抽取方法）。
---

# Comment Standards

约束 AI 生成代码注释的规范集。两层内容：

- **comment-standards.md**：注释规范本体 — 覆盖范围/格式/@param/@return/行内注释/禁止事项/自检清单
- **gen-comments-workflow.md**：存量代码补注释工作流（有 spec 派生 / 无 spec 事实注释，不猜意图）

## 加载矩阵

| 任务类型 | 必读 |
|---|---|
| 生成/补全任意代码注释 | `standards/comment-standards.md` |
| 存量代码补注释（历史代码） | `standards/gen-comments-workflow.md` + `standards/comment-standards.md` |
| 审查注释质量 | `standards/comment-standards.md`（自检清单） |

## 核心规则速查

- 全量注释：**所有类**（DTO/VO/Config 等，仅示例非穷举）必须有类注释，写清「这个类做什么」
- **所有变量/字段**必须有注释，写清业务含义与约束（枚举取值/单位/可空性）
- **所有方法**（含 private、测试方法）必须有方法注释：功能 + @param 业务含义 + @return 业务含义
- **方法体 ≥2 个逻辑步骤**必须有编号步骤注释（`// 1. 参数提取…` `// 2. 基础校验…`），粒度到业务步骤
- 逐行翻译式注释仍禁止（`// 价格乘以数量`）；步骤注释 ≠ 翻译式注释
- 复杂逻辑写 `// WHY:` 解释动机
- 注释与代码事实一致，禁止编造意图
- 存量补注释：有 spec 走 spec，无 spec 只写事实注释

## 与其他 skill 的关系

- **java-code-standards**（代码规范）：引用本 skill 的注释规范（Java 代码注释规则）
- **ai-dev-workflow**（开发流程）：约束模板引用本 skill 注释规范；gen-comments 命令对应本 skill 的存量补注释工作流
- **database-standards**（SQL 规范）：无注释内容，无引用

## 使用要求

生成任何代码注释前，按「任务类型 → 加载矩阵」读取规范；生成后对照 `comment-standards.md` 自检清单逐项核对。违反强制规则即返工。
