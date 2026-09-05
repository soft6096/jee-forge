# jee-forge

> Java/AI 工程开发的"规范锻造炉"——把 AI 辅助开发所需的**流程、规范、测试、核对**整合为一套可安装的 Skill 家族，让 AI 生成的代码"规范、不跑偏、可维护"。

**English:** jee-forge is a family of 9 Agent Skills (SKILL.md-based) for AI-driven Java/Spring backend development. One repo, nine skills — install once, use in any agent that supports skills (Claude Code / opencode / Codex / Cursor / CodeBuddy …). The flagship skill `ai-dev-workflow` runs a full SDD/TDD pipeline from requirement to acceptance; the other 8 skills provide code standards, a bug-fix discipline and a final check gate.

> 📘 中文使用指南（含各工具安装细节、生效确认与 FAQ）见 [`docs/usage-zh.md`](docs/usage-zh.md)。

---

## 目录

1. [快速开始](#快速开始)
2. [Skill 家族一览](#skill-家族一览8-个)
3. [技能结构与命令结构](#技能结构与命令结构)
4. [ai-dev-workflow 完整流程](#ai-dev-workflow-完整流程)
5. [规范类技能与核对技能怎么用](#规范类技能与核对技能怎么用)
6. [安装](#安装)
7. [仓库由来与维护](#仓库由来与维护)

---

## 快速开始

```bash
git clone git@github.com:soft6096/jee-forge.git
cd jee-forge
./install.sh          # 自动检测本机 agent 技能目录并安装 8 个技能（也可 --tool claude / --list 先看）
```

安装后新开会话，对你的 Agent 说：

```
/jee-forge 订单模块
```

即可进入完整开发流程（需求 → 方案 → 任务 → 契约测试 → 编码 → 规范核对 → 验收）。写码收尾统一用 `/check-standards` 做兜底核对。

> 看不到 `/jee-forge`？直接说"按流程开发 XX 模块"效果等价（斜杠命令是否出现取决于工具的 skill 命令注册）。

---

## 为什么需要这套技能家族

直接丢给 AI 一句提示词让它写代码，结果往往是：代码能跑但没人敢维护、接口悄悄偏离设计、SQL 没索引、注释稀疏、测试从零开始。这 9 个技能把 AI 编码约束成一条**分工明确、按需加载**的流水线：

- **流程管"怎么走"**：需求 → 方案 → 任务 → 契约测试 → 编码 → 核对 → 验收（ai-dev-workflow）
- **规范管"长什么样"**：代码 / 注释 / SQL / 构建 / 测试 各自成域，谁写谁加载
- **核对管"交付前兜底"**：写完逐项 grep/ast-grep 实际扫描，禁止凭记忆答 ✅

技能间**不冲突**：每个技能一个独立目录、靠任务描述自动触发、按需加载——单个编码会话只叠加与当前任务匹配的规范，防止规范挤占编码上下文。

## Skill 家族一览（9 个）

| skill | 类型 | 职责 | 典型触发说法 |
|---|---|---|---|
| [`ai-dev-workflow`](skill/ai-dev-workflow) | 流程 | 完整开发流程（0.x 前置 + 1.1~5.3 五步 + 18 命令 + 21 模板） | `/jee-forge XX 模块` / "按流程开发 XX 模块" |
| [`bugfix-workflow`](skill/bugfix-workflow) | 流程 | 缺陷修复纪律：复现→assess 根因→最小修复→防回归测试→兜底核对 | `/bugfix` / "这个 bug 帮我修" |
| [`java-code-standards`](skill/java-code-standards) | 代码规范 | Java 代码规范引擎（19 类规范 + 安全/分布式/性能/模板/示例） | "写个接口/写 Controller/写 Service" |
| [`comment-standards`](skill/comment-standards) | 注释规范 | 全量注释规范 + 存量代码补注释工作流 | "给 XX 模块补注释" |
| [`database-standards`](skill/database-standards) | SQL 规范 | SQL / 表设计 / 索引 / 分页 / 反模式 / MyBatis-Plus | "写个 SQL" / "建张表" |
| [`build-standards`](skill/build-standards) | 构建规范 | Maven pom / 依赖管理 / 多模块结构 | "写 pom" / "加个依赖" |
| [`test-standards`](skill/test-standards) | 测试规范 | 单元测试 / 契约测试 / 测试数据 | "写单测" / "写契约测试" |
| [`legacy-onboarding`](skill/legacy-onboarding) | 存量接入 | 存量项目体检与规范接入（8 维度 + A/B/C 分级整改） | "老项目接入规范" / "扫描这个项目" |
| [`check-standards`](skill/check-standards) | 兜底核对 | 代码交付前核对（33 项 + 证据 + 报告 + 确认闸门） | "/check-standards" / "对 xx 跑 check-standards" |

**依赖关系**：`ai-dev-workflow` 编排流程并挂载各规范技能；`java-code-standards` 引用 comment/database/test/build；`check-standards` 的核对项覆盖其余全部技能；`legacy-onboarding` 体检时按 8 维度聚合加载各规范；`bugfix-workflow` 处理缺陷修复并引用 ai-dev-workflow（产物同步）/check-standards（兜底）。合并为单仓库后**一体安装、引用不悬空**。

## 技能结构与命令结构

### 技能目录约定

每个技能 = 一个自包含目录（`skill/<name>/`），入口统一为 `SKILL.md`：

- `SKILL.md` 顶部 frontmatter 的 `name` + `description` 决定 Agent 何时加载它（触发）；正文是加载后 AI 遵循的规则/加载矩阵。
- 命令型技能把斜杠命令放在自己的 `commands/`（文件名 = 命令名）；文档型技能把规范拆在 `standards/` 或按主题分子目录；**当前 9 个技能中 `ai-dev-workflow`（18 命令）与 `bugfix-workflow`（/bugfix）带 commands/，其余规范技能靠自动触发，无需命令。**

### 仓库目录树

```
jee-forge/
├── README.md / LICENSE / COPYRIGHT.md / install.sh / docs/
└── skill/
    ├── ai-dev-workflow/          # ★ 流程技能（唯一命令型）
    │   ├── SKILL.md              # 流程总纲：场景判定/触发矩阵/闸门/硬性约束
    │   ├── commands/             # 18 个斜杠命令（见下节命令表）
    │   ├── templates/            # 21 份中间产物空白模板（0.0~5.3 + req-intake + 00-进度）
    │   └── docs/                 # 方法论文档（流程总览 / Spec-Coding / Vibe 对比）
    ├── bugfix-workflow/          # 缺陷修复纪律：SKILL.md + commands/bugfix.md + templates/bugfix-修复单.md
    ├── java-code-standards/      # 代码规范引擎
    │   ├── SKILL.md + README.md + COPYRIGHT.md
    │   ├── 00-common/            # 全量必读公共规范（命名/日志/异常/公共组件等）
    │   ├── 01-java/              # 19 类 Java 类规范（controller/service/mapper/entity/dto/vo…）
    │   ├── 03-performance/       # 性能/并发/缓存规范
    │   ├── 04-templates/         # 可复制类骨架模板（ConfigTemplate/ServiceImpl 等）
    │   └── 05-examples/          # 完整 CRUD 示例（321 行）
    ├── comment-standards/        # 注释规范：SKILL.md + standards/（comment-standards.md、gen-comments-workflow.md）
    ├── database-standards/       # SQL 规范：SKILL.md + standards/（SQL/表设计/索引/分页/反模式/数据安全）+ mybatis-plus/（3 份）
    ├── build-standards/          # 构建规范：SKILL.md + standards/（maven/dependency/module）
    ├── test-standards/           # 测试规范：SKILL.md + standards/（unit/contract/test-data）
    ├── legacy-onboarding/        # 存量接入：SKILL.md + standards/（workflow/report-template）
    └── check-standards/          # 兜底核对：SKILL.md（33 项核对全部内联）+ README.md
```

> 各技能内部结构各不相同（有 `standards/`、按主题子目录、或单文件内联）是刻意保留——每份 `SKILL.md` 的"加载矩阵"写死了自己的规范路径，统一目录反而会破坏引用与按需加载。

### ai-dev-workflow 命令结构（18 个斜杠命令）

| 命令 | 归属 | 作用 |
|---|---|---|
| `/jee-forge` | 总入口 | 一键完整流程：场景判定 →（大/跨栈需求走 `/req-intake`）→ 五步或轻量模式 |
| `/progress` | 进度/接续 | 读取/更新模块 `00-进度.md`，报告每步状态与断点并从断点续跑（跨会话/换人接手先 `/progress`，禁止从 1.1 重跑） |
| `/0.0-项目初始化` | 0.0 | 脚手架 10 项硬检查（防"启动即炸"，从零建工程必做） |
| `/legacy-scan` | 0.5 | 存量代码扫描与约束适配（老代码迭代必做，含"是否优化存量"决策闸门） |
| `/change-impact` | 0.8 | 迭代变更影响分析（同模块已有产物改逻辑/迭代必做：定位旧产物→变更映射→产物同步计划，人确认） |
| `/req-intake` | 0.9 | 需求入口整形（可选前置：需求跨多 Java 模块/超大/混栈时按模块生成需求 md，非 Java 部分直接忽略，人确认后进 1.1） |
| `/feature-list` | 1.1 | 功能清单（需求准入分档/基线 → 需求点穷尽 → 拆功能项 → 覆盖核对 → MVP） |
| `/req-gate` | 1.2 | 需求质量核对（**强制闸门**：原文回读逐节 + 跨节矛盾 + 术语↔码值对齐） |
| `/clarify` | 1.3 | 澄清歧义/入口复杂度/边界/依赖 + 裁决 req-gate 🔲 项 |
| `/constraints` | 2.1 | 项目约束（标准模式 / 存量适配模式，含工具选型人确认） |
| `/design` | 3.x | 技术方案（3.0 通用骨架 + Controller/Listener/Job 类型模板） |
| `/task-breakdown` | 4.1 | 任务拆解（公共组件入 Phase 0.5） |
| `/contract-tests` | 4.2 | 接口契约测试（先红后绿，验收场景翻译） |
| `/implement` | 5.1 | AI 编码（让测试变绿；编码完成即停） |
| `/check-standards` | 5.2 | **兜底核对入口**（强制独立节点：产物命名矫正 → check-standards skill 逐项扫描 → 证据报告 → 用户确认；5.3 前置硬依赖） |
| `/accept` | 5.3 | 验收报告（前置检查 5.2 报告存在性；含 quickstart 调通证据） |
| `/gen-comments` | 附加 | 存量代码补注释 |
| `/gen-logs` | 附加 | 存量代码补全/完善日志 |

> `/bugfix` 命令位于 **bugfix-workflow** skill 内（`skill/bugfix-workflow/commands/bugfix.md`），不在 ai-dev-workflow 命令表中。

## ai-dev-workflow 完整流程

### 总体：三种使用方式

| 方式 | 触发 | 说明 |
|---|---|---|
| **方式一 分步执行（推荐）** | 依次 `/feature-list` → `/req-gate` → … | 每步产物可独立检查、可随时介入 |
| **方式二 一句话全流程** | `/jee-forge XX 模块` 或 "按流程开发 XX 模块" | 自动做场景判定后按顺序执行 |
| **方式三 轻量模式** | "写个 XX 接口" / "改段代码" | 跳过中间产物直接写码，但注释/日志/兜底核对不打折 |

### 第 0 步：开发场景判定（流程入口，由人确认）

| 场景 | 判定依据 | 走向 |
|---|---|---|
| 从零新项目 | 项目尚不存在 | 0.0 项目初始化 → 1.1 |
| 老项目/既有代码迭代 | 项目已存在、未接入本流程规范 | 0.5 存量扫描（含优化决策闸门）→ 1.1 |
| 已接入规范项目新模块 | 项目级约束文件已按 2.1 固化 | 直接 1.1 |
| 同模块已有产物迭代 | `docs/` 已有该模块历史产物目录 | 0.8 迭代变更影响分析 → 1.1（禁直接改码） |

> 判定不了 → 一律按老项目走 0.5，不自行猜测。

### 整体流程一览

下图来自 ai-dev-workflow 方法论文档（[`skill/ai-dev-workflow/docs/流程总览.md`](skill/ai-dev-workflow/docs/流程总览.md)），与下方"0.x 前置 / 1.1~5.3"两表互为对照。

```text
产品需求
  │
  ▼
【入口确认】和用户确认：当前老项目上迭代需求，还是新项目？
  │
  ├─ 新项目 ──────────────────────┬─ 老项目上迭代 ──────────────────────┬─ 已接入规范项目
  │                               │                                     │
  ▼                               ▼                                     ▼
0.0 项目初始化                    【优化决策】是否按规范                  1.1 需求分析
（脚手架 10 项硬检查：多环境       优化存量代码？                          （直接起）
 配置/HikariCP/JDBC 字符集/       ⚠ 未明确选择 → 不得进入 1.1
 端口/MyBatis-Plus 插件/          ├─ 是（选规范，可多选）──► 先做存量优化 ──► 1.1 需求分析
 MetaObjectHandler/schema         └─ 否（跳过）──────────► 1.1 需求分析（2.1 走存量适配模式）
 一致性/驱动版本/日志配置/         同模块已有历史产物目录？
 接口文档依赖；防"启动即炸"；       ├─ 是 ──► 0.8 迭代变更影响分析 ──► 1.1（继承旧产物同步，禁直接改码）
 模板：0.0-项目初始化.md）         └─ 否 ──►（如上走 0.5 或直接 1.1）
  │
  ▼
1.1 需求分析 ──→ 功能清单总览（需求准入：分档 A/B/C + 验收基线；先过滤非 Java 服务端需求；表格：功能项/类型/优先级/依赖/验收标准）
  │                模板：1.1-功能清单.md
  ▼
1.2 需求质量核对 ──→ 需求质量核对报告（/req-gate：原文回读逐节核对 + 跨节矛盾扫描 + 术语↔码值对齐；强制闸门，未过不得进入 1.3）
  │                模板：1.2-需求质量核对.md
  ▼
1.3 澄清 ────→ 澄清问题清单（歧义/入口复杂度/边界/依赖 + 裁决 1.2 交来的矛盾/术语项，人确认）+ 更新后功能清单
  │                模板：1.3-澄清问题清单.md
  ▼
2.1 技术架构 ──→ 技术架构 + 项目约束（标准模式 / 存量适配模式：对齐老项目约定）
  │                模板：2.1-项目约束.md、2.1-项目约束-存量适配.md
  ▼
3.x 技术方案 ──→ 每功能项一份技术方案 md（3.0 通用骨架 + 类型模板，含验收场景）
  │                模板：3.0 通用骨架 + 3.1-Controller / 3.2-Listener / 3.3-Job（四段式）
  ▼
4.1/4.2 任务拆解 + 契约测试（人主导）──→ 任务拆解.md + 红色测试 + DDL
  │                模板：4.1-任务拆解.md、4.2-接口契约测试.md
  ▼
5.1/5.2/5.3 AI 编码 + 规范核对（强制独立节点）+ 收敛验收（AI 主导）──→ 绿色代码 + 规范核对报告 + 验收报告
  │                模板：5.1-编码指令.md、5.3-验收报告.md（规范核对加载 check-standards skill）
  ▼
人工验收 ──→ 上线
```

> 图中**未单独画出** 0.9 需求入口整形（`/req-intake`）——它是大需求（跨多 Java 模块 / 超大 / 混杂非 Java 内容）时的**可选前置闸门**，命中判据则先于 1.1 执行，详见下方"0.x 前置步骤"小节。

### 0.x 前置步骤

| 步骤 | 触发命令 | 做什么 | 产物 |
|---|---|---|---|
| 0.0 项目初始化 | `/0.0-项目初始化` | 脚手架硬检查（配置四件套/HikariCP/JDBC 字符集/端口/MyBatis-Plus 插件/MetaObjectHandler/schema/驱动/日志/接口文档） | `docs/0.0-脚手架核对.md` |
| 0.5 存量扫描 | `/legacy-scan` | 扫描老项目约定（包/返回体/命名/中间件/约束文件）+ **优化决策闸门** | `docs/0.5-存量代码扫描.md`（项目级） |
| 0.8 变更影响分析 | `/change-impact` | 定位旧产物 → 变更点映射 → 产物同步计划（新增/修改/删除）→ **人确认后从源头 1.1 同步** | `docs/<模块>/0.8-迭代变更影响分析.md` |
| 0.9 需求入口整形 | `/req-intake` | **可选前置**。触发：需求跨多 Java 模块 / 超大 / 混杂非 Java 内容（任一）。**非 Java 服务端需求一律直接忽略**（不拆/不列清单/不产文件）；按 Java 模块生成模块级需求 md（含来源段落追踪/验收基线/跨模块依赖）→ **人确认后才各进 1.1** | `docs/req-intake-<时间戳>/`（清单 + 每模块一份需求 md） |

### 1.1 ~ 5.3 五步主流程

| 步骤 | 命令 | 做什么 | 产物（模板） | 谁主导 |
|---|---|---|---|---|
| 1.1 功能清单 | `/feature-list` | 需求准入（分档 A/B/C + 验收基线）→ 需求点穷尽 → 拆功能项（类型/优先级/依赖/可测试验收标准）→ **需求覆盖核对（无静默消失）** → MVP 切分 | `1.1-功能清单.md` | 人 |
| 1.2 需求质量核对 | `/req-gate` | **强制闸门**：① 原文回读逐节核对（防遗漏/误读）② 跨节矛盾扫描（防静默选边）③ 术语↔码值对齐 | `1.2-需求质量核对.md` | AI + 人验证 |
| 1.3 澄清 | `/clarify` | 盘问歧义/入口复杂度/边界用例/依赖 + 裁决 req-gate 🔲 项 | `1.3-澄清问题清单.md` | 人 + AI |
| 2.1 项目约束 | `/constraints` | 技术架构 + 项目约束（硬规则，可检查；标准/存量适配双模式；工具选型人确认） | `2.1-项目约束.md` | 人 |
| 3.x 技术方案 | `/design` | 每功能项一份方案（3.0 通用骨架 + 类型四段）；含验收场景、公共组件识别；Controller 功能项附带接口清单 | `3.<序号>.1-<功能>-技术方案.md`、`3.<序号>.2-…-接口清单.md` | 人 + AI 辅助 |
| 4.1/4.2 任务拆解 + 契约测试 | `/task-breakdown` `/contract-tests` | 任务拆解（公共组件入 Phase 0.5）+ 契约测试**先红** + DDL | `4.1.<序号>-任务拆解.md`、测试代码 | 人 |
| 5.1 AI 编码 | `/implement` | 让测试变绿，按注释/日志规范同步生成注释与日志；编码完成即停 | 绿色代码 + 测试结果 | AI |
| 5.2 规范核对 | `/check-standards` | **强制独立节点**（编码 Agent 不自评）：先矫正产物命名/路径 → 加载 check-standards skill 用 grep/ast-grep 逐项核对**全部 33 项（含方法级注释/日志全覆盖）**，每项附证据 → 未到位先与用户确认再补齐 → 报告获用户确认 | `5.2.<序号>-<功能>-规范核对报告.md` | AI + 人验证 |
| 5.3 验收 | `/accept` | **前置检查 5.2 报告存在性（无则拒收）**；人工补核 + 重复代码核对 + **quickstart 调通证据**（全新构建 + 真实启动 + 按验收场景实测） | `5.3.<序号>-<功能>-验收报告.md` | 人 |

### 每一步的规范加载（触发矩阵）

| 流程步骤 | 必须加载的规范技能 |
|---|---|
| 0.0 脚手架 | build-standards + java-code-standards（application-config/04-templates）+ database-standards（table-design） |
| 0.5 存量扫描 | templates/0.5 + 2.1-存量适配；选优化才加载对应规范 |
| 3.x 方案 | database-standards（DDL/表）+ java-code-standards（分层接口） |
| 4.1 拆任务 | database-standards（Mapper XML 触发条件） |
| 4.2 契约测试 | test-standards |
| 5.1 编码 | java-code-standards + comment-standards + database-standards + build-standards（按生成物） |
| 5.2 核对 | check-standards skill |
| 5.3 验收 | comment-standards + 各规范自检清单 |

### 中间产物确认闸门（防跑偏的第零道闸门）

**每一步产出后，AI 必须停下等人工确认，禁止连续执行到下一步**。关键闸门：0.5 优化决策、0.8 变更影响、0.9 需求构成清单、1.1 功能清单、1.2 核对报告（未确认不进 1.3）、1.3 澄清、2.1 约束、3.x 方案、4.1/4.2、5.1、5.2 核对报告（未确认不进 5.3）、5.3 验收。

### 轻量模式（写个接口/改个功能）

不强制 1.1~4.2 中间产物，直接：加载规范 skill → 全量注释 + 全量日志写码 → `/check-standards` 兜底。**三条硬要求不打折**；同模块已有历史产物改逻辑仍须先 0.8，禁止拿轻量模式绕过产物同步。

## 规范类技能与核对技能怎么用

除 `ai-dev-workflow` / `bugfix-workflow` 两个流程型技能外，其余 7 个规范/核对技能均为"自动触发"型：Agent 按任务描述匹配 `description` 自动加载对应技能，无需命令。覆盖的触发面：

| 想写什么 | Agent 会自动加载 |
|---|---|
| 任何 Java 代码 | java-code-standards（+ comment-standards） |
| 任何注释/补注释 | comment-standards |
| SQL / DDL / MyBatis XML | database-standards |
| pom / 依赖 / 模块 | build-standards |
| 单元/契约测试 | test-standards |
| 老项目体检/接入 | legacy-onboarding（建议配合 ai-dev-workflow 0.5 使用） |
| 交付前兜底核对 | check-standards（可由 `/check-standards` 或自然语言触发） |
| 修复已有代码 bug | bugfix-workflow（/bugfix：复现→根因→最小修复→防回归→兜底） |

## 安装

技能内容以 `skill/<name>/SKILL.md` 组织。不同 Agent 对技能目录识别规则不同，三选一：

### 方式一：整仓 clone（支持嵌套扫描的工具：opencode / Codex）

```bash
git clone git@github.com:soft6096/jee-forge.git ~/.agents/skills/jee-forge
```

更新 = `git -C ~/.agents/skills/jee-forge pull`。

### 方式二：一键分发脚本（Claude Code / CodeBuddy 等一级目录工具）

```bash
./install.sh                # 自动检测已装技能目录并安装 8 个技能
./install.sh --tool claude  # 只装到 ~/.claude/skills
./install.sh --list         # 先看会装到哪里
./install.sh --force        # 覆盖已存在副本（先自动备份）
```

脚本用**复制**分发（部分工具不跟随 symlink，已踩坑验证）。

### 方式三：手动复制（任意工具）

```bash
cp -r skill/* <你的技能目录>/   # 或只装需要的某几个
```

> 只装其中某几个也完全没问题；装全家桶体验最完整。

### 使用示例

| 你想做什么 | 对 Agent 说 |
|---|---|
| 完整流程（总入口） | `/jee-forge 订单模块`（或 "按流程开发订单模块"；跨多模块/超大自动先 `/req-intake`） |
| 直接写码（轻量） | "写个 XX 接口" / "实现 XX 功能" |
| 写 SQL / 建表 | "写个 SQL" / "建张表" |
| 补注释 / 补日志 | "给 XX 模块补注释" |
| 修 bug | "这个 bug 帮我修"（加载 bugfix-workflow，`/bugfix`；涉及需求/产物变更先走流程 0.8） |
| 老项目接规范 | "把这个老项目接入规范体系" |
| 交付前兜底核对 | "对 src/main/java 跑 check-standards" |

## 仓库由来与维护

- 本仓库由 8 个独立技能仓库聚合而来（ai-dev-workflow / build-standards / java-code-standards / comment-standards / database-standards / test-standards / legacy-onboarding / check-standards），并新增 `bugfix-workflow` 作为家族第 9 技能（缺陷修复纪律）。原仓库内容原样保留为各 `skill/<name>/`，技能名、触发词、内部相对路径均未改动，**用法与单独安装完全一致**。
- 价值：跨技能一致的规范变更（如"同表唯一映射"需同步到 java-code-standards + database-standards + legacy-onboarding + check-standards）从"4 个仓库各提交一次"收敛为**单仓库一次 commit 原子落地**。
- 新增技能：在 `skill/` 下新建 `skill/<新技能名>/SKILL.md`（自包含）即可被扫描识别，无需改动其它技能。
- 发布：本仓库同时是"规范技能集"与"流程技能"的单一事实源；本地以 `docs/<模块名>V<版本>-<时间戳>/` 落盘中间产物。

## License

[MIT](LICENSE)。技能内容与代码示例全部原创（详见 [COPYRIGHT.md](COPYRIGHT.md)）。
