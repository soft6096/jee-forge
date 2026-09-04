---
name: legacy-onboarding
description: 存量项目（老项目/历史项目/既有项目）接入 AI 开发规范体系的体检与整改流程。当用户说"老项目接入规范""存量项目体检""扫描这个项目""评估代码现状""历史项目怎么用规范""把这个项目纳入规范体系"时加载。触发场景：存量项目、老项目、历史代码、项目体检、基线扫描、规范接入、现状评估、legacy。核心产出：8 维度体检报告 + A/B/C 分级整改清单 + 存量豁免记录。适用范围：任何已有代码库（Java 服务端为主），接入后回到 ai-dev-workflow 流程继续开发。存量代码补注释/补日志见 comment-standards（gen-comments-workflow）与 ai-dev-workflow（/gen-comments /gen-logs）。
---

# Legacy Onboarding（存量项目体检接入）

存量项目接入 AI 开发规范体系的流程 skill。管「怎么把已存在的项目摸清现状、分级整改、设定基线」；规范本身仍引用现有 6 个规范 skill，不重复造规范。

## 核心原则

1. **不是全量返工**：存量项目 ≠ 新项目，历史代码不逐行重写
2. **动线区分**：正在改的文件按规范执行；存量基线记录在案；必修项排期整改
3. **事实优先**：先扫描记录"现状是什么"，再决定"改哪些"，禁止扫描阶段顺手改代码
4. **分级整改**：A 必修（影响启动/安全/数据）→ B 建议修（影响规范一致）→ C 记录在案（存量豁免，仅新代码生效）

## 加载矩阵

| 任务类型 | 必读 |
|---|---|
| 存量项目接入/体检 | `standards/legacy-onboarding-workflow.md` + 各维度对应的规范 skill（见工作流内引用表） |
| 写体检报告 | `standards/legacy-report-template.md` + `standards/legacy-onboarding-workflow.md` |
| 存量项目开发新功能 | ai-dev-workflow（0.5 + 1.1~5.3）+ 本 skill 的 C 类豁免记录（新代码不豁免）；轻量迭代直接走 0.5，无需本 skill 全量体检 |
| 存量补注释 | comment-standards `standards/gen-comments-workflow.md` |

## 核心流程速查

```
1. 前置确认 ──→ 项目路径 + 可构建基线（git？mvn compile 通？）
2. 8 维度扫描 ──→ 工程/配置/数据/代码/安全/测试/注释/文档 基线
3. 分级汇总 ──→ A 必修 / B 建议修 / C 记录在案
4. 产出落盘 ──→ 体检报告 + 整改清单（docs/ 目录）
5. 整改 + 固化 ──→ A 类整改 → 报告入仓 → 回到 ai-dev-workflow「开发场景判定」继续（老代码迭代走 0.5，新模块走 1.1）
```

## 与其他 skill 的关系

| skill | 关系 |
|---|---|
| **ai-dev-workflow** | 本 skill 管**完整接入**（8 维度体检 + A/B/C 整改）；ai-dev-workflow **0.5 存量代码扫描**管**轻量迭代**（聚焦老项目约定 + 优化决策闸门，可跳过优化，二选一）。接入后回到其「开发场景判定」：新项目→0.0 / 老代码迭代→0.5 / 已接入规范→1.1 |
| **java-code-standards** | 配置基线（application-config）/代码基线/安全基线引用 |
| **database-standards** | 数据基线（schema 一致性/字符集/索引）引用 |
| **build-standards** | 工程基线（依赖/驱动版本/模块）引用 |
| **test-standards** | 测试基线引用 |
| **comment-standards** | 注释基线（存量补注释工作流）引用 |

## 使用要求

存量项目接入时，先加载本 skill 工作流，再按维度加载对应规范 skill 执行扫描。扫描结果落盘为体检报告，作为后续 AI 开发的项目事实基线。禁止扫描阶段修改业务代码。
