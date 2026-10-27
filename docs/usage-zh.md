# jee-forge 使用指南（中文）

面向所有想把 **AI 生成的 Java 代码"约束在规范内"** 的开发者。本仓库是一个 **Agent Skill 家族**：安装一次，你常用的编程 Agent（Claude Code / opencode / Codex / Cursor / CodeBuddy 等）就能自动按任务加载对应的规范，让 AI 写出**规范、不跑偏、可维护**的代码。

---

## 一、它解决什么问题

直接丢给 AI 一句提示词让它写代码，常见翻车：代码能跑但没人敢维护、接口悄悄偏离设计、SQL 没索引、注释稀疏、测试从零写起。

jee-forge 把约束拆成 10 个**按需加载**的技能（Skill），各管一段：

- **流程**：AI 怎么走（需求 → 方案 → 任务 → 编码 → 核对 → 需求覆盖 → 验收）
- **规范**：产物长什么样（代码 / 注释 / SQL / 构建 / 测试）
- **核对**：交付前兜底（优先跑 `scripts/check_standards.py` 机械扫描，无 Python 回退 grep/ast-grep，附「文件:行号」证据；**脚本默认只扫本次 git 改动文件，全量体检才加 `--all`**）

## 二、技能与触发说法

| skill | 管什么 | 你这样说就会触发 |
|---|---|---|
| `ai-dev-workflow` | 完整开发流程（0.x 前置 + 1.1~5.3 五步） | `/jee-forge XX 模块` 或 "按流程开发 XX 模块" |
| `quick-change-workflow` | 小改动非全流程通道（缺陷修复/优化/小需求补充，即 quick change：判型→产物定位→根因分层→最小改动→功能回归→兜底） | `/quick-change` 或 "这个 bug 帮我修" / "在 XX 模块补个 XX" |
| `java-code-standards` | Java 代码规范（01-java 20 份类/场景规范 + 性能/模板/示例） | "写个接口 / 写个 Controller / 帮我写段代码" |
| `comment-standards` | 注释规范 + 存量补注释 | "给 XX 模块补注释" |
| `database-standards` | SQL / 建表 / 索引 / 分页 / MyBatis-Plus | "写个 SQL / 建张表" |
| `build-standards` | pom / 依赖 / 多模块 | "写 pom / 加个依赖" |
| `test-workflow` | 按需生成真实调用接口的验收测试工具与独立报告 | "生成验收测试 / 生成接口测试 / 真实调用接口验证" |
| `legacy-onboarding` | 老项目体检接入规范 | "把这个老项目接入规范" |
| `check-standards` | 代码交付前兜底核对（57 项） | "代码跑一下 check-standards" |

## 三、安装

### 方式 A：一键脚本（推荐，支持所有工具）

```bash
git clone https://github.com/soft6096/jee-forge.git
cd jee-forge
./install.sh          # 拷贝形态（默认）：自动检测本机已装的 agent 技能目录并复制 9 个技能
./install.sh --list   # 先看会装到哪
```

**一台机器装了多个 Agent 时，推荐改用链接形态**（一份真身 + 软链共享，更新即重跑）：

```bash
./install.sh --link   # 从远端 clone/更新安装副本 ~/.agents/repos/jee-forge，并把技能以软链挂到各 Agent 目录
```

- 前提：你的 Agent 能跟随软链。实测 opencode / CodeBuddy 原生读 `~/.agents/skills`（不依赖软链），Trae / Claude Code / Hermes 可跟随软链；若某个工具装了却看不到技能，就用默认的拷贝形态
- 判定「源 vs 安装产物」：技能目录里是指向 `~/.agents/repos/jee-forge/skill/<name>` 的软链、且副本根有 `.jee-forge-origin`

### 方式 B：整仓 clone（仅支持嵌套扫描的工具）

opencode / Codex 支持识别 `skill/<name>` 嵌套，直接：

```bash
git clone https://github.com/soft6096/jee-forge.git ~/.agents/skills/jee-forge
# 更新 = git -C ~/.agents/skills/jee-forge pull
```

### 方式 C：手动复制（任何工具）

```bash
# 例：装到 Claude Code 用户级技能目录
cp -r skill/ai-dev-workflow ~/.claude/skills/
cp -r skill/comment-standards ~/.claude/skills/
# ……其它技能同理；整批用：cp -r skill/* <你的技能目录>/
```

> 技能互相独立，**只装其中几个也行**；装全家桶体验最完整。

## 四、怎么确认技能已生效

1. 安装后新开一个会话（不要沿用旧会话）；
2. 对你的 Agent 说一句触发话术，例如"写个订单模块的 Service 接口，按 Java 规范来"；
3. 观察 Agent 是否引用本家族规范中的说法（如"按 java-code-standards 分层/命名规则"、"按 comment-standards 全量注释"）；
4. 或直接要求："加载 comment-standards 的加载矩阵"——能答出规范内容即已生效。

## 五、常见问题（FAQ）

**Q1：装好了但 Agent 好像没触发技能？**
先确认：技能目录结构对不对（SKILL.md 必须存在）；会话是否新开；工具是否支持该技能目录位置（opencode 用 `~/.agents/skills/`，Claude Code 用 `~/.claude/skills/`，别放错）；部分工具不跟随 symlink——若用 `--link` 链接形态装的技能看不到，改用默认拷贝形态（`./install.sh`）即可。

**Q2：这么多技能会互相冲突吗？会不会一次全加载、挤爆上下文？**
不会。每个技能一个独立目录、由任务的 description 触发，**只加载与当前任务匹配的规范**。写 SQL 只触发 database-standards，不会把 java/comment 全拉进来；修 bug 触发 quick-change-workflow、新功能触发 ai-dev-workflow。各技能内部还写了 WHEN NOT 边界，避免多 skill 规则叠加。

**Q3：技能里的路径引用（如 `standards/sql-standards.md`）合仓后还有效吗？**
有效。这类引用是"技能内部相对路径"，随整个技能目录搬移保持不变；技能间引用按**技能名**（如"加载 check-standards"），与仓库形态无关。合仓后技能一体安装，引用更不会悬空。

**Q4：以后规范更新怎么更？**
```bash
./install.sh --link                            # 链接形态（推荐）：更新安装副本 + 刷新回执 + 重建软链
./install.sh --force                           # 拷贝形态：覆盖旧副本（会先自动备份）
git -C <你的 jee-forge 副本路径> pull           # 整仓 clone 方式
```

> 一键脚本会**自动清理旧备份**：每个技能目录只保留最近 1 个备份批次，其余批次自动删除；`--no-prune` 可关闭自动清理，`--list` 只预览不删除。

**Q5：这套规范和 Spring Boot 强绑定吗？**
核心面向 Spring Boot + Spring + MyBatis-Plus 生态；SQL/注释/测试/流程等原则可推广到其它语言与技术栈（示例以 Java 为主）。

**Q6：为什么叫"规范"而不是"规则"？**
每个技能 = 规范文本 + 反例/正例 + 自检清单，设计成"AI 能逐条对照检查"的形式，而不是模棱两可的建议。

**Q7：斜杠命令（`/jee-forge`、`/feature-list`）敲不出来 / 没补全，是没装好吗？**
不是。触发方式有两种，**跨工具通用的是自然语言**：
- **自然语言触发（所有工具通用，推荐）**：直接说"按流程开发 XX 模块"、"用 jee-forge 开发 XX 模块"、"按 ai-dev-workflow 流程开发 XX 模块"、"写个 XX 接口"、"继续 XX 模块"等，即可触发对应技能——Claude Code / CodeBuddy / Codex / opencode 全部支持；
- **斜杠命令触发（取决于工具）**：Claude Code / CodeBuddy 会把技能内 `commands/*.md` 注册为 `/命令`；opencode 目前只识别 `SKILL.md`，`commands/` 内文件不注册为斜杠命令——此时敲 `/feature-list` 无补全属正常，AI 会自动读取命令文件按同样流程执行，效果等价。

在 opencode 下请用自然语言触发，不要据此判断安装失败——生效确认见第四节。

## 六、技能家族关系图

```
legacy-onboarding ──体检存量项目──────┐
ai-dev-workflow ──流程编排───────────┤   → 8 维度扫描 / 产物模板 / 场景判定
quick-change-workflow ──小改动非全流程───┘   → /quick-change：判型→产物定位→根因分层→最小改动→功能回归
  │  0.5 / 5.1 编码
  ▼
java-code-standards  ←→ comment-standards（注释）
  │        ←→ database-standards（SQL/建表）
  │        ←→ build-standards（pom/依赖）
  │        ←→ test-workflow（按需验收测试）
  ▼
check-standards ──交付前兜底核对（44 项 + 证据 + 报告）──→ 验收
```

## 七、版权与贡献

- 代码与规范文本全部原创（详见 COPYRIGHT.md）。
- 想新增技能：在 `skill/` 下新建 `skill/<新技能名>/SKILL.md`，目录内自包含即可被扫描识别，无需改动其它技能。
