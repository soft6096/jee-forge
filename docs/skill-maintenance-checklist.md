# 家族规范变更 checklist（改 skill 前必读）

> 用途：**任何新增 / 修改 / 删除技能规范条目的操作**（写新规范、改 SKILL.md、改模板、加/改 check-standards 核对项、把 `docs/experience.md` 经验固化成规则）动手前逐项走一遍，防"改了 A 漏了 B、跨技能不同步"。
> 为什么必须：本仓库 9 个技能互相引用（ai-dev-workflow 编排、java-code-standards 引用 comment/database/test/build、check-standards 核对项覆盖其余技能、legacy-onboarding 按 8 维度聚合加载）。一条规范变更往往要动 3~4 个技能，漏一处 = 交付前核对与规范打架。
> 何时视为"改规范"：不只是改代码规范技能——**任何影响"AI 生成物长什么样 / 怎么被核对"的改动都算**，含中间产物模板（templates/）、命令（commands/）、核对项（check-standards）、触发描述（各 SKILL.md frontmatter description）。

## 0. 变更前：定位与映射（先搜，后动手）

- [ ] **归属定位**：这条规则属于哪个技能？（现有 9 技能无法容纳 → 说明可能该新建技能，先与维护者确认，不随手塞进现有技能）
- [ ] **引用方扫描**：`search_content` 搜新/改规则关键词，找出所有提及处：各 SKILL.md 触发矩阵、README 技能表/命令表、docs/usage-zh.md、skill/ai-dev-workflow/docs/流程总览.md、legacy-onboarding 8 维度清单、experience 固化目标。**未扫完不下结论。**

## 1. 变更中：逐项核对（每一项都要能答"改 / 不改 / 明确不改的原因"）

### A. 规则本身归属与一致性
- [ ] 归属技能是否唯一？是否与相邻技能规则冲突（先搜同名/同义规则，如"唯一索引"同时出现在 java-code-standards / database-standards，改动需同步两处）
- [ ] **rule 可分三态**：硬规则（可 grep/ast-grep 判定）→ 必须配核对项（见 C）；软取向（判不了对错）→ 明确放"软取向/背景约定"层，不写进硬性约束与核对项；原则说明（方法论文档）→ 只改 docs，不进核对
- [ ] 改动是否影响"存量适配模式"（0.5/2.1-存量适配）？老项目对齐场景是否要豁免或需同步表述
- [ ] 若新增/改名模板：产物命名是否符合 ai-dev-workflow 命名规则（带流程编号/功能项序号/禁任务 ID 前缀），是否与 `skill/ai-dev-workflow/docs/流程总览.md` 模板索引一致

### B. 入口与触发
- [ ] 是否涉及流程步骤（0.x/1.x~5.x）？是 → 同步：SKILL.md 命令表 + 步骤小节 + 落盘规则 + 命名规则 + 确认闸门清单 + `templates/通用-模块进度与断点.md` 步骤行 + README 命令表/流程图
- [ ] 触发描述（各 SKILL.md / commands frontmatter `description`）是否要加触发词，让 Agent 在该场景能加载到
- [ ] 规范技能（非命令型）是否要在 ai-dev-workflow"配套规范 skill 触发矩阵"登记加载时机

### C. 核对兜底（check-standards）
- [ ] **硬规则必配核对项**：新硬规则是否同步成 check-standards 核对项（33 项体系内新增/修改）？每项是否有可执行的 grep/ast-grep 判定指令？**无自动核对手段的规则=可能被静默跳过**
- [ ] 核对项是否与 5.2/5.3 报告模板里的"关键规范落地核对表"（templates/5.3-验收报告.md）重复或需同步

### D. 引用方与文档同步
- [ ] java-code-standards 内部引用（comment/database/test/build 的引用路径、00-common 公共规范与 01-java 各规范）是否仍准确
- [ ] legacy-onboarding 8 维度体检是否要同步（新增维度/核对样例）
- [ ] README / docs/usage-zh.md 的技能表、命令表、目录树注释、模板/命令计数是否同步（计数改一个数就要全仓搜一遍）
- [ ] docs/experience.md 中已固化条目是否要移入归档（被本规则接管的条目不再重复驱动）

### E. 示例与模板
- [ ] 示例/模板是否跟着改？**改规则不改示例 = 示例误导人**（如 java-code-standards 05-examples 全量 CRUD 示例、04-templates 类骨架）
- [ ] 正反例是否更新（规则改后旧反例可能不再反）

## 2. 变更后：验收

- [ ] **全仓引用一致性复查**：改后 `search_content` 关键词复查，确认无"漏网"旧表述
- [ ] **frontmatter 机械校验**（改过任何 SKILL.md / commands `description` 时必做）：全部 SKILL.md + commands/*.md 跑一遍 YAML 解析（description 内半角冒号 `: ` 必须用引号包裹或全角冒号；Ruby `YAML.safe_load` / Python yaml 均可），并确认 description 长度 ≤1024 字符——防"改了触发词结果 frontmatter 解析失败 / 触发词被截断"
- [ ] 变更说明：在 commit message 写清"改了哪些技能 / 为什么 / 核对项出处"，便于后人追溯（本仓库靠 commit 原子落地，一次变更一个 commit）
- [ ] 对外发布影响：使用者的已装副本需重新 `./install.sh --force`（或按 docs/usage-zh.md 更新方式）才生效，README/usage-zh 的更新说明若涉及安装方式同步写清

## 3. 快速对照表（改动类型 → 必查位置）

| 改动类型 | 必查位置（除规则自身技能外） |
| :--- | :--- |
| 改代码规范（java/comment/database/build/test） | check-standards 核对项 + 05-examples/04-templates + legacy-onboarding + ai-dev-workflow 触发矩阵 + README |
| 改核对项（check-standards） | 33 项清单 + templates/5.3-验收报告.md 关键规范表 + 各规范技能对应章节 |
| 改流程（ai-dev-workflow） | SKILL.md（命令表/步骤/落盘/命名/闸门）+ 模块进度模板 + README 流程图 + skill/ai-dev-workflow/docs/流程总览.md + commands/* |
| 新增模板/命令 | SKILL.md 命令表 + README 命令表 + 模板索引 + 计数（全仓搜旧数字） |
| 经验固化（experience → 规则） | 归属技能 + check-standards + 引用方 + experience 归档 |
