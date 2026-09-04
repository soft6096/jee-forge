# legacy-onboarding

存量项目（老项目/历史项目）接入 AI 开发规范体系的体检与整改流程 skill。核心产出：8 维度体检报告 + A/B/C 分级整改清单 + 存量豁免记录。

## 解决的问题

规范体系（ai-dev-workflow + 6 个规范 skill）面向新项目/新模块，存量项目是盲区：不摸清现状就开发，基础设施缺陷会连环引爆（真实事故：配置缺失/表结构不匹配/MetaObjectHandler 缺失导致启动 4 层报错）。本 skill 把"存量接入"固化为流程——**先扫描摸清现状，再分级整改，不逐行返工**，体检报告成为后续 AI 开发的项目事实基线。

## 核心原则

- **不是全量返工**：存量项目 ≠ 新项目，历史代码不逐行重写
- **动线区分**：正在改的文件按规范执行；存量基线记录在案；必修项排期整改
- **事实优先**：每条结论带证据（文件路径/命令输出），禁止凭印象
- **分级整改**：A 必修（启动/安全/数据）→ B 建议修（规范一致）→ C 记录在案（存量豁免，仅新代码生效）

## 规范文件

| 文件 | 覆盖 |
|---|---|
| [SKILL.md](SKILL.md) | skill 入口 + 加载矩阵 + 流程速查 |
| [standards/legacy-onboarding-workflow.md](standards/legacy-onboarding-workflow.md) | 主工作流：5 步流程 + 8 维度扫描清单 + A/B/C 分级规则 |
| [standards/legacy-report-template.md](standards/legacy-report-template.md) | 体检报告模板（8 维度表格 + 分级汇总 + 整改记录） |

## 与其他 skill 的关系

| skill | 关系 |
|---|---|
| [ai-dev-workflow](https://github.com/soft6096/jee-forge/tree/main/skill/ai-dev-workflow) | 本 skill 管**完整接入**（8 维度体检 + A/B/C 分级整改）；ai-dev-workflow **0.5 存量代码扫描**管**轻量迭代**（聚焦老项目约定 + 优化决策闸门，可跳过优化，二选一）。接入完成后回到其「开发场景判定」继续：新项目→0.0；老代码迭代→0.5；已接入规范→1.1 |
| [java-code-standards](https://github.com/soft6096/jee-forge/tree/main/skill/java-code-standards) | 配置基线（application-config）/代码基线/安全基线引用 |
| [database-standards](https://github.com/soft6096/jee-forge/tree/main/skill/database-standards) | 数据基线（schema 一致性/字符集/索引）引用 |
| [build-standards](https://github.com/soft6096/jee-forge/tree/main/skill/build-standards) | 工程基线（依赖/驱动版本/模块）引用 |
| [test-standards](https://github.com/soft6096/jee-forge/tree/main/skill/test-standards) | 测试基线引用 |
| [comment-standards](https://github.com/soft6096/jee-forge/tree/main/skill/comment-standards) | 注释基线（存量补注释工作流）引用 |

## 使用

触发场景自动加载：存量项目接入、老项目体检、扫描项目现状、规范接入。也可显式要求：`用 legacy-onboarding 扫描这个项目`。

## 维护

- 工作流文件按「适用范围 → 执行流程 → 执行规则 → 自检清单」结构编写，新增扫描维度保持此结构
- 8 维度引用各规范 skill，规范本体不在本仓库复制（单点维护）
- 改流程后更新 SKILL.md 加载矩阵与速查
