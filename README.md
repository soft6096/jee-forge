# jee-forge

> Java/AI 工程开发的"规范锻造炉"——把 AI 辅助开发所需的**流程、规范、测试、核对**整合为一套可安装的 Skill 家族，让 AI 生成的代码"规范、不跑偏、可维护"。

> 📘 中文使用指南见 [`docs/usage-zh.md`](docs/usage-zh.md)（含各工具安装细节、生效确认方法与 FAQ）。

**English:** jee-forge is a family of 8 Agent Skills (SKILL.md-based) for Java/Spring backend development powered by AI agents. One repo, eight skills — install once, use in any agent that supports skills (Claude Code / opencode / Codex / Cursor / CodeBuddy …).

---

## 为什么需要这套技能家族

直接丢给 AI 一句提示词让它写代码，结果往往是：代码能跑但没人敢维护、接口悄悄偏离设计、SQL 没有索引、注释稀疏、测试从零开始。这 8 个技能把 AI 编码约束成一条**分工明确、按需加载**的流水线：

- **流程管"怎么走"**：需求 → 方案 → 任务 → 契约测试 → 编码 → 核对 → 验收
- **规范管"长什么样"**：代码 / 注释 / SQL / 构建 / 测试 各自成域，谁写谁加载
- **核对管"交付前兜底"**：写完了逐项 grep/ast-grep 扫描，禁止凭记忆答 ✅

技能间**不冲突**：每个技能目录独立、按任务描述触发、按需加载（单个编码会话只叠加与当前任务匹配的规范，防止规范挤占编码上下文）。

## Skill 家族一览（8 个）

| skill | 职责 | 典型触发说法 | 备注 |
|---|---|---|---|
| [`skill/ai-dev-workflow`](skill/ai-dev-workflow) | 完整开发流程：0.x 前置（0.0/0.5/0.8/0.9 需求入口整形）+ 1.1~5.3 五步，命令 + 产物模板 | "按流程开发 XX 模块" | 流程编排中枢 |
| [`skill/java-code-standards`](skill/java-code-standards) | Java 代码规范引擎：19 类类规范 + 安全/分布式/性能/模板/示例 | "写个接口/Controller/Service" | Spring Boot + MyBatis-Plus 生态 |
| [`skill/comment-standards`](skill/comment-standards) | 全量注释规范 + 存量代码补注释工作流 | "给 XX 模块补注释" | 任何语言通用，Java 示例 |
| [`skill/database-standards`](skill/database-standards) | SQL / 表设计 / 索引 / 分页 / 反模式 / MyBatis-Plus | "写个 SQL/建张表" | MySQL |
| [`skill/build-standards`](skill/build-standards) | Maven pom / 依赖管理 / 多模块结构 | "写 pom/加依赖/拆模块" | 与 api-doc/日志框架选型联动 |
| [`skill/test-standards`](skill/test-standards) | 单元测试 / 契约测试 / 测试数据 | "写单测/写契约测试" | JUnit5 + Mockito |
| [`skill/legacy-onboarding`](skill/legacy-onboarding) | 存量项目体检与规范接入（8 维度 + A/B/C 整改） | "老项目接入规范/扫描这个项目" | 与 ai-dev-workflow 0.5 分工 |
| [`skill/check-standards`](skill/check-standards) | 代码交付前兜底核对（33 项核对 + 证据 + 报告） | "对 xx 跑 check-standards" | grep/ast-grep 实际扫描 |

> 内部引用关系（谁依赖谁）：`ai-dev-workflow` 挂 4 个规范技能；`java-code-standards` 引用 comment/database/test/build；`check-standards` 的核对项覆盖其余全部技能；`legacy-onboarding` 按 8 维度聚合加载各规范。合并为单仓库后**一体安装、引用不悬空**。

## 安装

技能内容以 `skill/<name>/SKILL.md` 组织。不同 Agent 对技能目录的识别规则不同，请按你的工具选择方式：

### 方式一：整仓 clone（支持嵌套扫描的工具：opencode / Codex）

```bash
git clone git@github.com:soft6096/jee-forge.git ~/.agents/skills/jee-forge
```

克隆后保持 `skill/<name>/SKILL.md` 结构即可被递归识别；更新 = `git -C ~/.agents/skills/jee-forge pull`。

### 方式二：一键分发脚本（Claude Code / CodeBuddy 等一级目录工具）

```bash
./install.sh            # 自动检测本机已装的 agent 技能目录并安装
./install.sh --tool claude    # 只装到 ~/.claude/skills
./install.sh --list     # 先看会装到哪里
```

脚本把 `skill/*` 下 8 个技能**复制**（非软链，部分工具不跟随 symlink）到检测到的技能目录。

### 方式三：手动复制（任意工具）

```bash
cp -r skill/ai-dev-workflow ~/.claude/skills/          # Claude Code 示例
cp -r skill/comment-standards ~/.claude/skills/
# ……其余技能同理；或整批：cp -r skill/* 你的技能目录/
```

> 提示：只装其中某几个也完全没问题（技能互相独立、按名引用）；装全家桶则体验最完整。

## 使用示例

| 你想做什么 | 对 Agent 说 |
|---|---|
| 完整走一遍流程 | "按流程开发 XX 模块" |
| 直接写码（轻量） | "写个 XX 接口" / "实现 XX 功能" |
| 写 SQL / 建表 | "写个 SQL" / "建张表" |
| 补注释 / 补日志 | "给 XX 模块补注释" |
| 老项目接规范 | "把这个老项目接入规范体系" |
| 交付前核对 | "写完的代码跑一下 check-standards" |

## 目录结构

```
jee-forge/
├── README.md               # 家族总览 + 安装（本文件）
├── LICENSE                 # MIT
├── COPYRIGHT.md            # 仓库级版权合规说明（第三方参考源对照）
├── install.sh              # 多 Agent 一键分发脚本
└── skill/
    ├── ai-dev-workflow/        # 流程 skill：SKILL.md + commands/ + templates/ + docs/
    ├── java-code-standards/    # 代码规范：SKILL.md + 00-common/ + 01-java/ + 03-performance/ + 04-templates/ + 05-examples/
    ├── comment-standards/      # 注释规范：SKILL.md + standards/
    ├── database-standards/     # SQL 规范：SKILL.md + standards/ + mybatis-plus/
    ├── build-standards/        # 构建规范：SKILL.md + standards/
    ├── test-standards/         # 测试规范：SKILL.md + standards/
    ├── legacy-onboarding/      # 存量接入：SKILL.md + standards/
    └── check-standards/        # 兜底核对：SKILL.md（33 项核对内联）
```

## 仓库由来与维护

- 本仓库由 8 个独立技能仓库聚合而来（ai-dev-workflow / build-standards / java-code-standards / comment-standards / database-standards / test-standards / legacy-onboarding / check-standards），原仓库内容原样保留为各 `skill/<name>/`，技能名、触发词、内部相对路径均未改动，**用法与单独安装完全一致**。
- 价值：跨技能一致的规范变更（如"同表唯一映射"需同步到 java-code-standards + database-standards + legacy-onboarding + check-standards）从"4 个仓库各提交一次"收敛为**单仓库一次 commit 原子落地**。
- 新增技能：在 `skill/` 下新建 `skill/<新技能名>/SKILL.md`（目录内自包含）即可被扫描器识别，无需改动其它技能。

## License

[MIT](LICENSE)。技能内容与代码示例全部原创（详见 [COPYRIGHT.md](COPYRIGHT.md)）。
