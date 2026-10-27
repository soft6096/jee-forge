# jee-forge

> Java/AI 工程开发的"规范锻造炉"——把 AI 辅助开发所需的**流程、规范、测试、核对**整合为一套可安装的 Skill 家族，让 AI 生成的代码"规范、不跑偏、可维护"。

**English:** jee-forge is a family of 9 Agent Skills (SKILL.md-based) for AI-driven Java/Spring backend development. One repo, nine skills — install once, use in any agent that supports skills (Claude Code / opencode / Codex / Cursor / CodeBuddy …). The flagship skill `ai-dev-workflow` runs a full SDD/TDD pipeline from requirement to acceptance; the other 8 skills provide code standards, a bug-fix discipline and a final check gate.

> 📘 中文使用指南（含各工具安装细节、生效确认与 FAQ）见 [`docs/usage-zh.md`](docs/usage-zh.md)。

---

## 目录

1. [快速开始](#快速开始)
2. [Skill 家族一览](#skill-家族一览9-个)
3. [技能结构与命令结构](#技能结构与命令结构)
4. [场景分流](#场景分流什么情况走哪条路)
5. [ai-dev-workflow 完整流程](#ai-dev-workflow-完整流程)
6. [规范类技能与核对技能怎么用](#规范类技能与核对技能怎么用)
7. [安装](#安装)
8. [仓库由来与维护](#仓库由来与维护)

---

## 快速开始

```bash
git clone https://github.com/soft6096/jee-forge.git
cd jee-forge
./install.sh          # 自动检测本机 agent 技能目录并安装 9 个技能（也可 --tool claude / --list 先看）
```

安装后新开会话，对你的 Agent 说：

```
/jee-forge 订单模块
```

即可进入完整开发流程（需求 → 方案 → 任务 → 编码 → 规范核对 → 需求覆盖 → 验收）。写码收尾统一用 `/check-standards` 做兜底核对。

> 看不到 `/jee-forge`？直接说"按流程开发 XX 模块"效果等价（斜杠命令是否出现取决于工具的 skill 命令注册）。

---

## 为什么需要这套技能家族

直接丢给 AI 一句提示词让它写代码，结果往往是：代码能跑但没人敢维护、接口悄悄偏离设计、SQL 没索引、注释稀疏、测试从零开始。这套技能把 AI 编码约束成一条**分工明确、按需加载**的流水线：

- **流程管"怎么走"**：需求 → 方案 → 任务 → 编码 → 核对 → 需求覆盖 → 验收（ai-dev-workflow）
- **规范管"长什么样"**：代码 / 注释 / SQL / 构建 / 测试 各自成域，谁写谁加载
- **核对管"交付前兜底"**：写完优先跑 `scripts/check_standards.py` 机械扫描（无 Python 回退 grep/ast-grep），禁止凭记忆答 ✅

技能间**不冲突**：每个技能一个独立目录、靠任务描述自动触发、按需加载——单个编码会话只叠加与当前任务匹配的规范，防止规范挤占编码上下文。

## Skill 家族一览（9 个技能）

| skill | 类型 | 职责 | 典型触发说法 |
|---|---|---|---|
| [`ai-dev-workflow`](skill/ai-dev-workflow) | 流程 | 完整开发流程（0.x 前置 + 1.1~5.3 五步 + 18 命令 + 22 模板） | `/jee-forge XX 模块` / "按流程开发 XX 模块" |
| [`quick-change-workflow`](skill/quick-change-workflow) | 流程 | 小改动非全流程通道（缺陷修复/优化/小需求补充，即 quick change）：判型→产物定位→A/B/C 根因分层→最小改动→功能回归→兜底核对；小改动不走 1.1~5.3 重流程 | `/quick-change` / "这个 bug 帮我修" / "在 XX 模块补个 XX" |
| [`java-code-standards`](skill/java-code-standards) | 代码规范 | Java 代码规范引擎（01-java 20 份类/场景规范 + 03-performance + 04-templates + 05-examples） | "写个接口/写 Controller/写 Service" |
| [`comment-standards`](skill/comment-standards) | 注释规范 | 全量注释规范 + 存量代码补注释工作流 | "给 XX 模块补注释" |
| [`database-standards`](skill/database-standards) | SQL 规范 | SQL / 表设计 / 索引 / 分页 / 反模式 / MyBatis-Plus | "写个 SQL" / "建张表" |
| [`build-standards`](skill/build-standards) | 构建规范 | Maven pom / 依赖管理 / 多模块结构 | "写 pom" / "加个依赖" |
| [`test-workflow`](skill/test-workflow) | 按需验收测试工具 | 按需生成真实调用接口的验收测试工具与独立报告 | 生成验收测试 / 生成接口测试 / 真实调用接口验证 |
| [`legacy-onboarding`](skill/legacy-onboarding) | 存量接入 | 存量项目体检与规范接入（8 维度 + A/B/C 分级整改） | "老项目接入规范" / "扫描这个项目" |
| [`check-standards`](skill/check-standards) | 兜底核对 | 代码交付前核对（57 项 + 证据 + 报告 + 确认闸门） | "/check-standards" / "对 xx 跑 check-standards" |


**依赖关系**：`ai-dev-workflow` 编排流程并挂载各规范技能；`java-code-standards` 引用 comment/database/build；`check-standards` 的核对项覆盖其余全部技能；`legacy-onboarding` 体检时按 8 维度聚合加载各规范；`quick-change-workflow` 处理已有模块上的小增量（缺陷修复/优化/小需求补充）并引用 ai-dev-workflow（产物同步；需升版本/跨模块的大迭代转 0.8）/check-standards（兜底）；`test-workflow` 按需生成真实调用接口的验收测试工具。合并为单仓库后**一体安装、引用不悬空**。

## 技能结构与命令结构

### 技能目录约定

每个技能 = 一个自包含目录（`skill/<name>/`），入口统一为 `SKILL.md`：

- `SKILL.md` 顶部 frontmatter 的 `name` + `description` 决定 Agent 何时加载它（触发）；正文是加载后 AI 遵循的规则/加载矩阵。
- 命令型技能把斜杠命令放在自己的 `commands/`（文件名 = 命令名）；文档型技能把规范拆在 `standards/` 或按主题分子目录；**当前 9 个技能中 `ai-dev-workflow`（18 命令）、`quick-change-workflow`（/quick-change）与 `test-workflow`（/gen-test）带 commands/，其余规范技能靠自动触发，无需命令。**

### 仓库目录树

```
jee-forge/
├── README.md / COPYRIGHT.md / install.sh / global-rules.md / docs/
├── scripts/                      # audit-size.py：技能体积审计与预算校验（改 skill 后跑，见「体积预算」）
└── skill/
    ├── ai-dev-workflow/          # ★ 流程技能（命令型）
    │   ├── SKILL.md              # 入口：场景判定/方式三轻量/硬性约束（触发即加载）
    │   ├── references/完整流程.md   # 完整流程正文：触发矩阵/命令表/落盘规则/闸门/五步流程（轻量场景不加载）
    │   ├── commands/             # 19 个斜杠命令（见下节命令表）
    │   ├── templates/            # 22 份中间产物空白模板（0.0~5.3 + req-intake + 通用-模块进度与断点）
    │   ├── references/           # 按需参考（3.1/3.4 完整示例、样式图表与卡片示例）：不进触发加载，用到才读
    │   ├── scripts/              # export_html.py（纯标准库：md → 带左侧导航 HTML 导出，/export-html 用）
    │   └── docs/                 # 方法论文档（流程总览 / Spec-Coding / Vibe 对比）
    ├── quick-change-workflow/          # 小改动非全流程（quick change：缺陷/优化/小需求）：SKILL.md + commands/quick-change.md + templates/quick-change-交付单.md
    ├── java-code-standards/      # 代码规范引擎
    │   ├── SKILL.md + README.md + COPYRIGHT.md
    │   ├── 00-common/            # 全量必读公共规范（命名/日志/异常/公共组件等）
    │   ├── 01-java/              # 20 份 Java 类/场景规范（controller/service/mapper/entity/dto/vo…）
    │   ├── 03-performance/       # 性能/并发/缓存规范
    │   ├── 04-templates/         # 可复制类骨架模板（ConfigTemplate/ServiceImpl 等）
    │   ├── assets/               # 工具配置（eclipse-formatter.xml，配 Spotless 一键格式化）
    │   └── 05-examples/          # 完整 CRUD 示例（321 行）
    ├── comment-standards/        # 注释规范：SKILL.md + standards/（comment-standards.md、gen-comments-workflow.md）
    ├── database-standards/       # SQL 规范：SKILL.md + standards/（SQL/表设计/索引/分页/反模式/数据安全）+ mybatis-plus/（3 份）
    ├── build-standards/          # 构建规范：SKILL.md + standards/（maven/dependency/module）
    ├── test-workflow/            # 按需验收测试：SKILL.md + commands/（gen-test）+ standards/（case-design/runner-standards）+ assets/（runner）+ templates/（验收测试报告）
    ├── legacy-onboarding/        # 存量接入：SKILL.md + standards/（workflow/report-template）
    └── check-standards/          # 兜底核对：SKILL.md（57 项概览 + 分组要点）+ references/checklist.md（完整判据与手工指令，按需读）+ README.md + scripts/（check_standards.py 机械扫描，纯 stdlib）
```

> 各技能内部结构各不相同（有 `standards/`、按主题子目录、或单文件内联）是刻意保留——每份 `SKILL.md` 的"加载矩阵"写死了自己的规范路径，统一目录反而会破坏引用与按需加载。
>
> **模板命名规则**：`0.x / 1.x` 带小数点 = **流程步骤产物模板**（0.0 项目初始化、0.5 存量扫描、0.9 需求入口整形…5.3 需求覆盖）；`通用-` = **全程通用模板（非步骤）**：`通用-中间产物-MD样式规范.md`（所有产物样式）、`通用-模块进度与断点.md`（模块目录伴随，配合 `/progress`）。

### ai-dev-workflow 命令结构（18 个斜杠命令）

| 命令 | 归属 | 作用 |
|---|---|---|
| `/jee-forge` | 总入口 | 一键完整流程：场景判定 →（大/跨栈需求走 `/req-intake`）→ 五步或轻量模式 |
| `/progress` | 进度/接续 | 读取/更新模块 `通用-模块进度与断点.md`，报告每步状态与断点并从断点续跑（跨会话/换人接手先 `/progress`，禁止从 1.1 重跑） |
| `/0.0-项目初始化` | 0.0 | 脚手架 11 项硬检查（防"启动即炸"，从零建工程必做） |
| `/legacy-scan` | 0.5 | 存量代码扫描与约束适配（老代码迭代必做，含"是否优化存量"决策闸门） |
| `/feasibility` | 0.6 | 需求可行性评估（**可选前置**：命中风险信号——未用过外部系统/选型争议/成本不清新方向——人确认后执行，一页速评 go/需澄清/kill） |
| `/change-impact` | 0.8 | 迭代变更影响分析（同模块已有产物改逻辑/迭代必做：定位旧产物→变更映射→产物同步计划，人确认） |
| `/req-intake` | 0.9 | 需求入口整形（可选前置：需求跨多 Java 模块/超大/混栈时按模块生成需求 md，非 Java 部分直接忽略，人确认后进 1.1） |
| `/feature-list` | 1.1 | 功能清单（需求准入分档/基线 → 需求点穷尽 → 拆功能项 → 覆盖核对 → MVP） |
| `/req-gate` | 1.2 | 需求质量核对（**强制闸门**：原文回读逐节 + 跨节矛盾 + 术语↔码值对齐） |
| `/clarify` | 1.3 | 澄清歧义/入口复杂度/边界/依赖 + 裁决 req-gate 🔲 项 |
| `/constraints` | 2.1 | 项目约束（标准模式 / 存量适配模式，含工具选型人确认） |
| `/design` | 3.x | 技术方案（3.0 通用骨架 + Controller/Listener/Job 类型模板） |
| `/task-breakdown` | 4.1 | 任务拆解（公共组件入 Phase 0.5） |
| `/implement` | 5.1 | AI 编码（编码完成即停） |
| `/check-standards` | 5.2 | **兜底核对入口**（强制独立节点、始终执行：产物命名矫正 → check-standards skill 脚本机械扫描（无 Python 回退 grep/ast-grep）→ 证据报告 → 用户确认；5.3 已改为用户可选，不再作为拒绝 5.3 的硬前置） |
| `/accept` | 5.3 | 需求覆盖报告（**用户可选、默认不执行：开工前先问用户，附【AI 推荐】**；执行时逐需求点核对代码证据/缺口、独立生成；跳过则不落盘） |
| `/gen-comments` | 附加 | 存量代码补注释 |
| `/gen-logs` | 附加 | 存量代码补全/完善日志 |
| `/export-html` | 附加 | 中间产物 md → 带左侧导航 HTML 导出（**阅读/存档旁路，默认不自动跑；md 为真源；3.x.2 接口清单不导出**） |

> `/quick-change` 命令位于 **quick-change-workflow** skill 内（`skill/quick-change-workflow/commands/quick-change.md`），不在 ai-dev-workflow 命令表中。

## 场景分流（什么情况走哪条路）

**先判要不要用流程。这四类不要用**（直接让 AI 做更快）：

| 情形 | 为什么不用 |
|---|---|
| 已指明改哪个文件 / 方法 / 改法 | 定位这步你已经做完了，判档与产物定位是重复劳动；走**短路**：直接改 → 复现验证 → 四行交付（改动/根因/影响面/验证）+ 收尾动作（同类扫描只列不改 / 经验沉淀同根因第 2 次才写），约 +500 token，换下次同类问题直接命中 |
| 照样板、照某模块写新代码 | 模式复制，直接参考样板写即可（走 ai-dev-workflow 轻量模式） |
| 纯日志排查，日志已指出位置 | 读日志 → 改 → 验证，一步到位 |
| 临时试验 / 一次性脚本 | 不产出可复用资产，留痕没有意义 |

**进场信号**（命中任一才进）：说不清改哪 / 要查影响面 / 动接口·出参·字段·口径 / 需留痕交付 / 同一问题已改 2 次未解。

进场之后再分档。分档判据是**产物要不要动**，不是代码改了几行——bug 的本质是"期望已存在、代码没做到"，天然不动产物。完整图：

```
用户输入（报错 / "改一下" / 新需求 / 一句话改动）
        │
        ▼
【入口闸门】判不清就先问一句："小修小补，还是走完整流程？"
        │
        ▼
① 项目状态
   ├─ 新项目 ─────────────────────────► 0.0 项目初始化 → 1.1
   ├─ 老项目/未接入规范 ───────────────► 0.5 存量扫描 + 优化决策闸门 → 1.1
   └─ 已接入规范
        │
        ▼
② 该模块 docs/ 有历史产物吗？
   ├─ 没有 ─┬─ 只是新增一个零散接口 ──► 轻量模式：加载规范 → 写码(注释+日志) → 兜底核对
   │        └─ 完整新功能 ────────────► 完整流程 1.1 → 2.1 → 3.x → 5.1 → 5.2 → 5.3
   └─ 有
        │
        ▼
③ 本次要不要动「期望」本身？（产物里的口径）
   │
   ├─ 产物不动（期望已在产物里，代码没做到）
   │   纯 bug · 优化（行为口径不变）
   │        │
   │        ▼
   │   【A 改码通道】（quick-change-workflow）
   │   对照 1.1 → 3.x.1 → 3.x.2 确认期望 → 改代码（注释+日志）
   │   → 复现验证（改前失败 / 改后通过）
   │   → 交付：改动点 + 根因 + 验证结果（几行的，一句话；多处/公共方法，简短记录）
   │
   └─ 产物要改（口径变了 / 补个小功能）
       小需求补充 · 口径小调整 · 优化改了验收场景
            │
            ▼
       【B 产物同步通道】（quick-change-workflow）
       ① 轻量改 3.x 对应段（小需求：1.1 补功能项 + 3.x 补方案/接口段）
       ② 登记产物同步记录（旧表述 → 新表述 + 原因）
       ③ 改码对齐 → ④ 回归 + 落交付单
       ※ 不升版本目录、不重走 1.1~5.3
        │
        └──────────────┬──────────────────┐
                       ▼                  │
④ 是否升版本目录 / 跨模块 / 重走主链？     │
   ├─ 是 ──► 停，转 0.8 /change-impact     │
   │         （定位旧产物 + 变更映射 → 人确认 → 从源头 1.1 同步 → 再写码）
   └─ 否 ──┐                             │
           ▼                             │
⑤ 收尾（A / B 两条通道共用）◄─────────────┘
   功能回归证据 → /check-standards 兜底 → 交付记录
        │
        ▼
⑥ 收尾动作：同类扫描（各档统一）→ 踩坑沉淀（同根因第 2 次出现才写 docs/experience.md，跨模块通用标 [HARD]）
```

场景速查：

| 场景 | 判定依据 | 通道 | 产物 | 交付 |
|---|---|---|---|---|
| 纯 bug，几行 | 产物里能查到期望 | A 改码 | 不动 | 对话一句话 + 同类扫描 N 处/无 |
| 纯 bug，多处/公共方法 | 同上，影响面大 | A 改码 | 不动 | 简短记录 |
| 优化，口径不变 | 行为不变 | A 改码 | 不动 | 一句话 + 同类扫描 N 处/无 |
| 优化改了验收口径 | 口径动了 | B 同步 | 改 3.x | 交付单 |
| 小需求补充 | 已有模块新增功能点 | B 同步 | 1.1 补项 + 3.x 补段 | 交付单 |
| 大迭代 | 升版本/跨模块/重走主链 | 完整流程 | 全链同步 | 0.8 + 5.3 |
| 完整新功能 | 模块无既有产物 | 完整流程 | 全量 | 5.3 覆盖报告 |
| 零散新接口 | 无产物需同步 | 轻量模式 | 无 | 兜底核对 |

三条硬边界：

- 产物里查不到这条"期望"的，就不是 bug：要么按 B 同步产物，要么走完整流程。
- 需要升版本目录 / 跨模块 / 重走主链的，一律不走 quick-change，直接 0.8。
- 注释与日志在任何通道都不豁免；豁免的只是产物改动、产物定位章节与交付单这类仪式（"期望确实在产物里/与现状一致"的只读查证仍要做）。

交互次数（程序员的真实体感）：A 档 **0 次**（一句话进、一句话出），B 档 **1 次**（确认产物改哪段），转完整流程 **1 次**（确认要升版本）。只有判档不清、产品口径对齐、兜底有项未到位、同一问题改 3 次仍不过，才额外开口；"能否开始改 / 要不要落交付单 / 要不要跑兜底"这类问题文档已禁止问。

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

下图来自 ai-dev-workflow 方法论文档（[`skill/ai-dev-workflow/docs/流程总览.md`](skill/ai-dev-workflow/docs/流程总览.md)，**人读用途；执行以 `SKILL.md` + `references/完整流程.md` 为准**），与下方"0.x 前置 / 1.1~5.3 主流程"两表互为对照。

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
（脚手架 11 项硬检查：多环境       优化存量代码？                          （直接起）
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
4.1 任务拆解（人主导）──→ 任务拆解.md + DDL
  │                模板：4.1-任务拆解.md
  ▼
5.1/5.2/5.3 AI 编码 + 规范核对（强制独立节点）+ 需求覆盖（AI 主导）──→ 绿色代码 + 规范核对报告 + 需求覆盖报告
  │                模板：5.1-编码指令.md、5.3-需求覆盖报告.md（规范核对加载 check-standards skill）
  ▼
人工验收 ──→ 上线
```

> 图中**未单独画出**两个可选前置：**0.6 需求可行性评估**（`/feasibility`，命中风险信号——未用过外部系统/选型争议/成本不清——时一页速评 go/需澄清/kill）与 **0.9 需求入口整形**（`/req-intake`，跨多 Java 模块/超大/混杂非 Java 内容时先按模块整形需求）。命中判据则先于 1.1 执行，详见下方"0.x 前置步骤"小节。

### 0.x 前置步骤

| 步骤 | 触发命令 | 做什么 | 产物 |
|---|---|---|---|
| 0.0 项目初始化 | `/0.0-项目初始化` | 脚手架硬检查（配置四件套/HikariCP/JDBC 字符集/端口/MyBatis-Plus 插件/MetaObjectHandler/schema/驱动/日志/接口文档） | `docs/0.0-项目初始化.md` |
| 0.5 存量扫描 | `/legacy-scan` | 扫描老项目约定（包/返回体/命名/中间件/约束文件）+ **优化决策闸门** | `docs/0.5-存量代码扫描.md`（项目级） |
| 0.6 需求可行性评估 | `/feasibility` | **可选前置**。命中风险信号（未用过外部系统/选型争议/成本不清新方向）时先回答"值不值得做/做不做得动"：读事实 → 自查关键未知 → 一页速评（风险扫描/体量粗估/备选路线）→ 🟢 go / 🟡 需澄清 / 🔴 kill，**人拍板**；普通需求直接跳过 | `docs/0.6-需求可行性评估.md` |
| 0.8 变更影响分析 | `/change-impact` | 定位旧产物 → 变更点映射 → 产物同步计划（新增/修改/删除）→ **人确认后从源头 1.1 同步** | `docs/<模块>/0.8-迭代变更影响分析.md` |
| 0.9 需求入口整形 | `/req-intake` | **可选前置**。触发：需求跨多 Java 模块 / 超大 / 混杂非 Java 内容（任一）。**非 Java 服务端需求一律直接忽略**（不拆/不列清单/不产文件）；按 Java 模块生成模块级需求 md（含来源段落追踪/验收基线/跨模块依赖）→ **人确认后才各进 1.1** | `docs/req-intake-<时间戳>/`（清单 + 每模块一份需求 md） |

### 1.1 ~ 5.3 主流程（功能项级）

| 步骤 | 命令 | 做什么 | 产物（模板） | 谁主导 |
|---|---|---|---|---|
| 1.1 功能清单 | `/feature-list` | 需求准入（分档 A/B/C + 验收基线）→ 需求点穷尽 → 拆功能项（类型/优先级/依赖/可测试验收标准）→ **需求覆盖核对（无静默消失）** → MVP 切分 | `1.1-功能清单.md` | 人 |
| 1.2 需求质量核对 | `/req-gate` | **强制闸门**：① 原文回读逐节核对（防遗漏/误读）② 跨节矛盾扫描（防静默选边）③ 术语↔码值对齐 | `1.2-需求质量核对.md` | AI + 人验证 |
| 1.3 澄清 | `/clarify` | 盘问歧义/入口复杂度/边界用例/依赖 + 裁决 req-gate 🔲 项 | `1.3-澄清问题清单.md` | 人 + AI |
| 2.1 项目约束 | `/constraints` | 技术架构 + 项目约束（硬规则，可检查；标准/存量适配双模式；工具选型人确认） | `2.1-项目约束.md` | 人 |
| 3.x 技术方案 | `/design` | 每功能项一份方案（3.0 通用骨架 + 类型四段）；含验收场景、公共组件识别；Controller 功能项附带接口清单 | `3.<序号>.1-<功能>-技术方案.md`、`3.<序号>.2-…-接口清单.md` | 人 + AI 辅助 |
| 4.1 任务拆解 | `/task-breakdown` | 任务拆解（公共组件入 Phase 0.5）+ DDL | `4.1.<序号>-任务拆解.md` | 人 |
| 5.1 AI 编码 | `/implement` | 按注释/日志规范同步生成注释与日志；编码完成即停 | 代码 + 编码完成报告 | AI |
| 5.2 规范核对 | `/check-standards` | **强制独立节点**（编码 Agent 不自评）：先矫正产物命名/路径 → 加载 check-standards skill **优先跑 `scripts/check_standards.py` 机械扫描（无 Python 回退 grep/ast-grep）**核对**全部 44 项（含方法级注释/日志全覆盖）**，每项附证据 → 未到位先与用户确认再补齐 → 报告获用户确认 | `5.2.<序号>-<功能>-规范核对报告.md` | AI + 人验证 |
| 5.3 需求覆盖 | `/accept` | 逐需求点核对代码证据/缺口，独立生成需求覆盖报告 | `5.3.<序号>-<功能>-需求覆盖报告.md` | AI + 人验证 |

### 每一步的规范加载（触发矩阵）

| 流程步骤 | 必须加载的规范技能 |
|---|---|
| 0.0 脚手架 | build-standards + java-code-standards（application-config/04-templates）+ database-standards（table-design） |
| 0.5 存量扫描 | templates/0.5 + 2.1-存量适配；选优化才加载对应规范 |
| 3.x 方案 | database-standards（DDL/表）+ java-code-standards（分层接口） |
| 4.1 拆任务 | database-standards（Mapper XML 触发条件） |
| 5.1 编码 | java-code-standards + comment-standards + database-standards + build-standards（按生成物） |
| 5.2 核对 | check-standards skill |
| 5.3 需求覆盖 | comment-standards + 各规范自检清单 |

### 中间产物确认闸门（防跑偏的第零道闸门）

**每一步产出后，AI 必须停下等人工确认，禁止连续执行到下一步**。关键闸门：0.5 优化决策、0.6 可行性评估结论（go/需澄清/kill，命中才走）、0.8 变更影响、0.9 需求构成清单、1.1 功能清单、1.2 核对报告（未确认不进 1.3）、1.3 澄清、2.1 约束、3.x 方案、4.1、5.1、5.2 核对报告（未确认不进 5.3）、5.3 需求覆盖报告。

### 轻量模式（写个接口/改个功能）

不强制 1.1~4.1 中间产物，直接：加载规范 skill → 全量注释 + 全量日志写码 → `/check-standards` 兜底。**三条硬要求不打折**；同模块已有历史产物改逻辑仍须先 0.8，禁止拿轻量模式绕过产物同步。

## 规范类技能与核对技能怎么用

除 `ai-dev-workflow` / `quick-change-workflow` / `test-workflow` 三个命令型技能外，其余 6 个规范/核对技能均为"自动触发"型：Agent 按任务描述匹配 `description` 自动加载对应技能，无需命令。覆盖的触发面：

| 想写什么 | Agent 会自动加载 |
|---|---|
| 任何 Java 代码 | java-code-standards（+ comment-standards） |
| 任何注释/补注释 | comment-standards |
| SQL / DDL / MyBatis XML | database-standards |
| pom / 依赖 / 模块 | build-standards |
| 按需生成验收测试 | test-workflow |
| 老项目体检/接入 | legacy-onboarding（建议配合 ai-dev-workflow 0.5 使用） |
| 交付前兜底核对 | check-standards（可由 `/check-standards` 或自然语言触发） |
| 已有模块上的小增量（修 bug / 优化 / 补个小需求） | quick-change-workflow（/quick-change：判型→产物定位→根因分层→最小改动→功能回归→兜底，不走重流程） |

## 安装

> **安装来源约定**：所有安装方式**只认远端仓库**（GitHub / 你指定的 git 地址），
> 不接受本地工作区作为来源。因此本机改完必须**提交并推送**才能被安装到，
> 避免把未提交的半成品装进技能目录。

技能内容以 `skill/<name>/SKILL.md` 组织。不同 Agent 对技能目录识别规则不同，三选一：

### 方式一：整仓 clone（支持嵌套扫描的工具：opencode / Codex）

```bash
git clone https://github.com/soft6096/jee-forge.git ~/.agents/skills/jee-forge
```

更新 = `git -C ~/.agents/skills/jee-forge pull`。

### 方式二：一键分发脚本（Claude Code / CodeBuddy 等一级目录工具）

脚本有两种分发形态：**默认是拷贝**（兼容性最好），**一台机器装多个 Agent 时推荐链接形态**。

#### 形态 A：链接模式 `--link`（一份真身 + 软链共享）

```bash
./install.sh --link                 # 从远端 clone/更新安装副本，并把技能以软链挂到各 Agent 技能目录
./install.sh --link --ref v1.2.0    # 指定分支 / 标签 / 提交号（默认 main）
./install.sh --link --repo <地址>    # 指定其它 git 地址（默认即 GitHub 开源仓库）
./install.sh --link --list          # 只预览，不安装
```

只保留**一份安装副本** `~/.agents/repos/jee-forge`，各 Agent 的技能目录里放软链指向它；
副本根写 `.jee-forge-origin` 安装回执（git 源 / ref / commit / 提交时间 / 安装时间）。

- **更新** = 重跑 `./install.sh --link`（内部 fetch + checkout，零拷贝、无备份残留）
- **前提：你的 Agent 能跟随软链。** 本仓库实测：opencode / CodeBuddy **原生读** `~/.agents/skills`（不依赖软链），Trae / Claude Code / Hermes 可跟随软链；若某个工具装了却看不到技能，说明它不跟随软链 → 改用下面的拷贝形态
- **判定「源 vs 安装产物」**：技能目录里是指向 `~/.agents/repos/jee-forge/skill/<name>` 的软链、且副本根有 `.jee-forge-origin`；开发源目录没有该文件

#### 形态 B：拷贝模式（默认，兼容性最好）

```bash
./install.sh                        # 从 GitHub main 拉取快照并分发 9 个技能（默认）
./install.sh --repo <地址>          # 指定其它 git 地址
./install.sh --repo https://...git  # 直接指定任意 git 地址
./install.sh --ref v1.2.0           # 指定分支 / 标签 / 提交号（默认 main）
./install.sh --tool codebuddy       # 只装到 ~/.codebuddy/skills
./install.sh --list                 # 先看远端来源 + 会装到哪里（不实际安装）
./install.sh --force                # 覆盖已存在副本（先自动备份）
./install.sh --no-prune             # 关闭备份自动清理（默认只保留最近 1 个批次，其余自动删除）
```

每个 Agent 目录各得一份**实体副本**，不依赖软链（部分工具不跟随 symlink，已踩坑验证）；
多 Agent 混用时同一技能会出现多份副本，脚本结束时会提示可改用形态 A。

脚本的行为要点（两种形态通用）：

- **只从远端安装**：拷贝形态内部 `git fetch --depth 1` 拉取指定 ref 的快照后再复制；链接形态 clone / 更新安装副本。
  本地工作区改动一律不影响安装结果；日志会打印实际安装的远端提交（`远端快照：<hash> <日期> <标题>`），便于核对装的是哪一版；
- **分发方式**：拷贝形态用**复制**（不依赖软链，兼容性最好）；链接形态用**软链**（一份副本全机共享，需工具能跟随软链）；
- **分发全局规则**（两种形态均进）：把仓根真源 `global-rules.md`（「需要用户裁决时必须给出【AI 推荐】项」的跨 Agent 行为规则）以受管块（`# BEGIN/END jee-forge::global-rules`）追加到各 Agent 的全局指令文件（`~/.claude/CLAUDE.md`、`~/.agents/AGENTS.md`、`~/.trae/AGENTS.md`、`~/.hermes/AGENTS.md`、`~/.qoder/AGENTS.md` 等）；**仅对配置目录已存在的 Agent 写入、不新建目录**；**幂等**：重跑整块替换不叠加，不改动文件其它内容；`--list` 只预览将写哪些文件；改规则请改 `global-rules.md` 后推送重装；
- **自动清理旧备份**（拷贝形态）：`--force` 覆盖前把旧副本备份为 `<name>.pre-jee-forge-<14 位时间戳>`（同一次运行共用同一时间戳 = 同一批次）；安装完成后每个技能目录**只保留最近 `KEEP_BACKUP_BATCHES`（默认 1）个批次**，其余批次自动清理；`--no-prune` 可关闭自动清理，`--list` 只预览不删除；
- 默认来源与 ref 在 `install.sh` 顶部配置（`REMOTE_GITHUB` / `DEFAULT_REPO` / `DEFAULT_REF`）。

### 方式三：手动分发（任意工具）

先 clone 远端，再从 clone 出来的副本复制——**不要直接复制你正在编辑的工作区**：

```bash
git clone --depth 1 https://github.com/soft6096/jee-forge.git /tmp/jee-forge
cp -r /tmp/jee-forge/skill/* <你的技能目录>/   # 或只装需要的某几个
```

> 只装其中某几个也完全没问题；装全家桶体验最完整。

### 使用示例

| 你想做什么 | 对 Agent 说 |
|---|---|
| 完整流程（总入口） | `/jee-forge 订单模块`（或 "按流程开发订单模块"；跨多模块/超大自动先 `/req-intake`） |
| 直接写码（轻量） | "写个 XX 接口" / "实现 XX 功能" |
| 写 SQL / 建表 | "写个 SQL" / "建张表" |
| 补注释 / 补日志 | "给 XX 模块补注释" |
| 修 bug / 小优化 / 补小需求 | "这个 bug 帮我修" / "在 XX 模块补个 XX"（加载 quick-change-workflow 按增量轻量流程；需升版本/跨模块的大迭代先走流程 0.8） |
| 老项目接规范 | "把这个老项目接入规范体系" |
| 交付前兜底核对 | "对 src/main/java 跑 check-standards" |

## 仓库由来与维护

- 本仓库由 8 个独立技能仓库聚合而来（ai-dev-workflow / build-standards / java-code-standards / comment-standards / database-standards / test-workflow / legacy-onboarding / check-standards），并新增 `quick-change-workflow` 作为家族第 9 技能（小改动非全流程通道：缺陷修复/优化/小需求补充，原名为 `bugfix-workflow`，因覆盖面扩到优化与小需求补充而改名，命令同步为 `/quick-change`）。**原 8 技能之一的 `test-standards` 已废弃，由 `test-workflow`（按需验收测试工具，`/gen-test`）取代**。原仓库内容原样保留为各 `skill/<name>/`，除本次改名外技能名、触发词、内部相对路径均未改动，**用法与单独安装完全一致**。
- 价值：跨技能一致的规范变更（如"同表唯一映射"需同步到 java-code-standards + database-standards + legacy-onboarding + check-standards）从"4 个仓库各提交一次"收敛为**单仓库一次 commit 原子落地**。
- 新增技能：在 `skill/` 下新建 `skill/<新技能名>/SKILL.md`（自包含）即可被扫描识别，无需改动其它技能。
- **变更纪律（改动任何 skill 前必读）**：新增/修改规范条目、模板、命令或核对项前，先过 [`docs/skill-maintenance-checklist.md`](docs/skill-maintenance-checklist.md)——定位归属技能 → 扫描引用方 → 逐项核对（硬规则必配核对项/软取向不混入/示例模板同步/README·usage-zh·流程总览计数与表述同步）→ 变更后全仓复查，防"改了 A 漏了 B"。
- **体积预算（改 skill 后必跑）**：技能是加载进 Agent 上下文的文本，越长每个任务越贵，且膨胀是渐进无声的。改完跑

  ```
  python3 scripts/audit-size.py
  ```

  退出码 0 = 全部在预算线内且无异常回涨（超 +5% 警告 / +20% 失败）。报告里的**「级联路径估算」比单文件大小更重要**——它算的是一次任务实际读进上下文的量（如一次 `/design`、一次 `/implement`），SKILL.md 的常驻成本只在触发时支付，而模板与规范是每个任务都付。优化完成后跑 `--write-baseline` 刷新基线，否则基线停留在旧值、后续增量无法触发报警。**`references/` 存放"用到才读"的示例与判据字典**（不进触发加载），是保持 SKILL.md 精简的主要手段。
- 发布：本仓库同时是"规范技能集"与"流程技能"的单一事实源；本地以 `docs/<模块名>V<版本>-<时间戳>/` 落盘中间产物。
- 经验回流：使用者把项目 `docs/experience.md` 使用总结按 [`docs/experience-contributing.md`](docs/experience-contributing.md) 交回维护者，评审后固化为对应规范/核对项随版本发布（**固化时同样过变更纪律 checklist**，避免同坑多用户反复踩）。
