# 存量项目体检接入工作流 (Legacy Onboarding Workflow)

## 适用范围

存量项目（已有代码库，含 AI 之前生成的、他人维护的、长期演进的历史项目）接入 AI 开发规范体系时加载。核心原则：**先扫描摸清现状，再分级整改，不逐行返工**。产出的体检报告是后续 AI 开发的项目事实基线。

## 输入 / 输出

- **输入**：项目路径
- **输出**：`docs/0.0-存量体检报告.md` + `docs/0.0-存量整改清单.md`（分级 A/B/C）

## 执行流程（5 步，扫描阶段只读）

### 1. 前置确认（可构建基线）

- 是否 git 仓库；非 git 建议先 `git init` + 首次 commit（体检前提：有回滚点）
- 构建能否跑通：`mvn compile`（或项目对应构建命令）；**构建不过先修构建**，否则后面扫描无意义
- 技术栈确认：Spring Boot 版本 / ORM / 数据库 / 中间件（对照 build-standards 约束）

### 2. 8 维度扫描（只读，不改代码）

按维度逐项扫描，每项记录：状态（✅ 达标 / ⚠️ 偏差 / ❌ 缺失）+ 证据（文件路径/行号/命令输出）+ 分级（A/B/C）。

| # | 维度 | 扫什么（检查点） | 怎么扫 | 对应规范 |
|:---:|:---|:---|:---|:---|
| 1 | 工程基线 | git 仓库？pom 依赖/驱动版本/模块结构？构建可跑？ | `git status`、`mvn dependency:tree`、读 pom.xml | build-standards `standards/dependency-standards.md` |
| 2 | 配置基线 | 多环境 profile 四件套？HikariCP 池参数？JDBC 字符集/端口/时区？中间件配置？ | 读 resources/ 下所有 yml/properties | java-code-standards `01-java/application-config-standards.md` |
| 3 | 数据基线 | schema 与 Entity 一致性？旧表遗留？建库脚本字符集？索引缺失？**表→Entity 映射清单？同表重复映射？** | 读 db/schema.sql + 全部 Entity + 关键表 DDL；`grep -rhn '@TableName("[^"]*")' src/main/java` 统计各表映射 Entity 清单 | database-standards `standards/table-design-standards.md`（§3.6 同表唯一映射）+ java-code-standards `01-java/entity-standards.md` §1 |
| 4 | 代码基线 | 包结构？命名？公共组件重复？异常/日志/事务/幂等防重入？ | 遍历 src/main/java，抽样 2-3 个核心模块 | java-code-standards（SKILL.md 加载矩阵） |
| 5 | 安全基线 | 鉴权？密钥/密码硬编码？SQL 拼接？文件上传无限制？ | grep 硬编码密码/`${}`/字符串拼接 SQL | java-code-standards `01-java/security-standards.md` |
| 6 | 测试基线 | 有测试？测试可跑？覆盖核心逻辑？测试质量？ | `mvn test`、统计测试类 vs 业务类 | test-standards |
| 7 | 注释基线 | 存量注释完整度（类/字段/方法/步骤注释） | 抽样 3-5 个文件对照自检清单 | comment-standards `standards/comment-standards.md` + `standards/gen-comments-workflow.md` |
| 8 | 文档基线 | README？接口文档？schema 文档？环境说明？ | 读 docs/、README | — |

> 扫描深度按项目规模调节：小项目（<50 文件）全量扫；大项目按模块抽样 + 全局 grep 兜底（硬编码密钥/SQL 拼接这类安全项必须全量 grep）。

> [!IMPORTANT] 数据基线必扫「同表重复映射」（同表唯一映射规则，源头治理）
> `grep -rhn '@TableName("…")' src/main/java` 统计**每张表的映射 Entity 清单**——同一表名出现 >1 个 Entity（如 `MallProduct` 与 `MallServiceProduct` 都映射 `mall_product`）即**重复映射**（B 类整改：无引用类删除、双引用类收敛合并，字段命名差异经 `@TableField` 映射统一，不另建 Entity）。体检报告记录表→Entity 清单，作为后续开发"新建 Entity 前查重"的基线（见 java-code-standards `entity-standards.md` §1）。

### 3. 分级汇总（A / B / C）

| 级别 | 定义 | 判定标准 | 处理 |
|:---:|:---|:---|:---|
| **A 必修** | 影响启动/安全/数据一致性 | 启动报错（连接/字符集/schema/自动填充）、密钥硬编码、SQL 注入、Entity 与 DDL 不一致 | 排期立即整改，整改前不开发新功能 |
| **B 建议修** | 影响规范一致与可维护性 | 命名不合规、注释缺失、公共组件重复、连接池参数缺、测试缺失 | 排入 backlog，随功能开发逐步整改（改到哪修到哪） |
| **C 记录在案** | 存量事实，豁免 | 历史命名风格、无法立即整改的存量设计、一次性迁移成本过高项 | 记录豁免原因，**豁免不扩展到新代码** |

分级示例（真实事故沉淀）：

```
❌ A：application.yml 只有单文件、datasource 无 HikariCP 池参数       → 启动后高并发连接打满
❌ A：JDBC URL 写 characterEncoding=utf8mb4 / 端口 3306 想当然        → 启动报 Unsupported encoding / Access denied
❌ A：实体 @TableField(fill=...) 但无 MetaObjectHandler               → 一插即炸 Column 'create_time' cannot be null
❌ A：库表沿用旧 schema，与 Entity 不一致                             → Unknown column 'real_name'
⚠️ B：Controller 命名/返回体不规范、公共逻辑复制粘贴两处             → 新代码不再犯，存量逐步收敛
⚠️ B：同一张表两个 Entity 映射（MallProduct / MallServiceProduct 都 @TableName 同表）→ 无引用类删除、双引用类收敛合并，字段增减只维护唯一 Entity
📝 C：历史表名无业务前缀（如 order 非 t_order）、存量短变量命名       → 记录豁免，新表/新代码按规范
```

### 4. 产出落盘

- `docs/0.0-存量体检报告.md`：按 `standards/legacy-report-template.md` 填写，8 维度逐项 ✅/⚠️/❌ + 证据 + 分级
- `docs/0.0-存量整改清单.md`：A 类（必修，排期）+ B 类（backlog）+ C 类（豁免记录）

### 5. 整改 + 基线固化

- A 类项立即整改（改配置/加 MetaObjectHandler/重建 schema 对齐 Entity/去硬编码密钥），整改后 `mvn compile` + 启动验证
- 体检报告随整改更新，最终 commit 入仓——报告成为项目"现状基线"
- 接入完成 → 回到 **ai-dev-workflow**「开发场景判定」继续：老代码迭代走 **0.5 存量代码扫描**（轻量：聚焦老项目约定 + 优化决策闸门，可跳过优化）；开发新模块直接走 1.1。新功能必须符合规范，C 类豁免不覆盖新代码

## 执行规则（硬性约束，不可协商）

```
1. 扫描阶段只读：禁止在扫描过程中顺手修改业务代码（发现即记录，进整改清单）
2. 事实优先：每条结论必须带证据（文件路径/命令输出），禁止凭印象写报告
3. 先修构建，再扫代码：构建不过不进入维度扫描
4. 安全项（硬编码密钥/SQL 拼接/未鉴权接口）全量 grep，不抽样
5. 分级不拍脑袋：A 类必须命中"启动/安全/数据"判定标准，其余不得升 A
6. 整改按 A → B 顺序，A 未清不开发新功能
7. 报告落盘 docs/ 并 commit，作为后续 AI 开发的项目事实基线
8. 存量豁免（C 类）只对存量代码生效，新增代码一律按规范
9. 本 skill（完整接入）与 ai-dev-workflow 0.5（轻量迭代）**二选一**：只想在存量项目上快速迭代新需求 → 直接走 0.5（聚焦老项目约定 + 优化决策闸门，可跳过优化），无需本 skill 全量体检与 A/B/C 整改；规则 6 的"A 未清不开发新功能"仅适用于本 skill 完整接入流程
```

## 自检清单

- [ ] 构建基线确认（git + mvn compile 通过）
- [ ] 8 维度全部扫描，无漏维度
- [ ] 每条结论有证据（文件路径/命令输出）
- [ ] 分级正确：A 类全部命中"启动/安全/数据"标准
- [ ] 安全项已全量 grep（非抽样）
- [ ] 体检报告 + 整改清单已落盘 docs/ 并 commit
- [ ] A 类项已整改或已明确排期
- [ ] C 类豁免已记录原因，且明确"不扩展到新代码"
- [ ] 接入后回到 ai-dev-workflow 流程，新代码按规范
