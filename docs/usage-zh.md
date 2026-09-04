# jee-forge 使用指南（中文）

面向所有想把 **AI 生成的 Java 代码"约束在规范内"** 的开发者。本仓库是一个 **Agent Skill 家族**：安装一次，你常用的编程 Agent（Claude Code / opencode / Codex / Cursor / CodeBuddy 等）就能自动按任务加载对应的规范，让 AI 写出**规范、不跑偏、可维护**的代码。

---

## 一、它解决什么问题

直接丢给 AI 一句提示词让它写代码，常见翻车：代码能跑但没人敢维护、接口悄悄偏离设计、SQL 没索引、注释稀疏、测试从零写起。

jee-forge 把约束拆成 8 个**按需加载**的技能（Skill），各管一段：

- **流程**：AI 怎么走（需求 → 方案 → 任务 → 测试 → 编码 → 核对 → 验收）
- **规范**：产物长什么样（代码 / 注释 / SQL / 构建 / 测试）
- **核对**：交付前兜底（逐项 grep/ast-grep 扫描，附「文件:行号」证据）

## 二、8 个技能与触发说法

| skill | 管什么 | 你这样说就会触发 |
|---|---|---|
| `ai-dev-workflow` | 完整开发流程（0.x 前置 + 1.1~5.3 五步） | "按流程开发 XX 模块" |
| `java-code-standards` | Java 代码规范（19 类类规范 + 安全/分布式/性能） | "写个接口 / 写个 Controller / 帮我写段代码" |
| `comment-standards` | 注释规范 + 存量补注释 | "给 XX 模块补注释" |
| `database-standards` | SQL / 建表 / 索引 / 分页 / MyBatis-Plus | "写个 SQL / 建张表" |
| `build-standards` | pom / 依赖 / 多模块 | "写 pom / 加个依赖" |
| `test-standards` | 单测 / 契约测试 / 测试数据 | "写单测 / 写契约测试" |
| `legacy-onboarding` | 老项目体检接入规范 | "把这个老项目接入规范" |
| `check-standards` | 代码交付前兜底核对（33 项） | "代码跑一下 check-standards" |

## 三、安装

### 方式 A：一键脚本（推荐，支持所有工具）

```bash
git clone git@github.com:soft6096/jee-forge.git
cd jee-forge
./install.sh          # 自动检测本机已装的 agent 技能目录并复制 8 个技能
./install.sh --list   # 先看会装到哪
```

### 方式 B：整仓 clone（仅支持嵌套扫描的工具）

opencode / Codex 支持识别 `skill/<name>` 嵌套，直接：

```bash
git clone git@github.com:soft6096/jee-forge.git ~/.agents/skills/jee-forge
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
先确认：技能目录结构对不对（SKILL.md 必须存在）；会话是否新开；工具是否支持该技能目录位置（opencode 用 `~/.agents/skills/`，Claude Code 用 `~/.claude/skills/`，别放错）；部分工具不跟随 symlink——本仓库安装一律用**复制**不用软链。

**Q2：8 个技能会互相冲突吗？会不会一次全加载、挤爆上下文？**
不会。每个技能一个独立目录、由任务的 description 触发，**只加载与当前任务匹配的规范**。写 SQL 只触发 database-standards，不会把 java/comment 全拉进来。各技能内部还写了 WHEN NOT 边界，避免多 skill 规则叠加。

**Q3：技能里的路径引用（如 `standards/sql-standards.md`）合仓后还有效吗？**
有效。这类引用是"技能内部相对路径"，随整个技能目录搬移保持不变；技能间引用按**技能名**（如"加载 check-standards"），与仓库形态无关。合仓后 8 个技能一体安装，引用更不会悬空。

**Q4：以后规范更新怎么更？**
```bash
git -C <你的 jee-forge 副本路径> pull          # 整仓 clone 方式
# 或一键脚本方式：重新 ./install.sh --force     # 覆盖旧副本（会先自动备份）
```

**Q5：这套规范和 Spring Boot 强绑定吗？**
核心面向 Spring Boot + Spring + MyBatis-Plus 生态；SQL/注释/测试/流程等原则可推广到其它语言与技术栈（示例以 Java 为主）。

**Q6：为什么叫"规范"而不是"规则"？**
每个技能 = 规范文本 + 反例/正例 + 自检清单，设计成"AI 能逐条对照检查"的形式，而不是模棱两可的建议。

## 六、技能家族关系图

```
legacy-onboarding ──体检存量项目────┐
ai-dev-workflow ──流程编排─────────┤   → 8 维度扫描 / 产物模板 / 场景判定
  │  0.5 / 4.2 契约测试 / 5.1 编码
  ▼
java-code-standards  ←→ comment-standards（注释）
  │        ←→ database-standards（SQL/建表）
  │        ←→ build-standards（pom/依赖）
  │        ←→ test-standards（测试）
  ▼
check-standards ──交付前兜底核对（33 项 + 证据 + 报告）──→ 验收
```

## 七、版权与贡献

- 代码与规范文本全部原创，MIT 许可（见根 LICENSE / COPYRIGHT.md）。
- 想新增技能：在 `skill/` 下新建 `skill/<新技能名>/SKILL.md`，目录内自包含即可被扫描识别，无需改动其它技能。
