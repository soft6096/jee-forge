# 版权合规说明 (Copyright Compliance Statement)

本文件为 **jee-forge** 仓库级版权合规声明。

> 本文档源自 java-code-standards 技能的《版权合规说明》，在仓库聚合（原 8 个独立技能仓库 → jee-forge 单仓库）时提升为仓库级，**适用于 `skill/` 下全部技能**（ai-dev-workflow / quick-change-workflow / java-code-standards / comment-standards / database-standards / build-standards / test-workflow / legacy-onboarding / check-standards）。各技能内的规范文本与代码示例均为原创，未携带任何开源再分发义务。

## 1. 内容原创性声明

本仓库全部内容（规范文本、代码示例、模板、示例文档、流程文档）均为**原创撰写**，由项目作者独立创作。

### 1.1 规则文本

- 规范规则基于 Java 社区**通用工程惯例**（naming、exception handling、logging、code style 等行业共识）
- 通用惯例与事实性知识不受版权保护，任何团队规范文档天然高度相似，不构成侵权
- 所有中文表述为作者原创撰写，未复制、未翻译、未改写任何受版权保护的原文

### 1.2 代码示例

- 全部代码示例为原创编写，仅使用公开框架 API 的**功能性调用**：
  - Spring Framework / Spring Boot 注解与 API
  - MyBatis-Plus 公开 API（`LambdaQueryWrapper`、`@TableLogic`、`@Version` 等）
  - JDK 标准库（`ThreadPoolExecutor`、`try-with-resources` 等）
- API 调用、标准语法、功能性表达式属必要表达，不受版权保护
- 未包含任何开源项目的整段代码复制

## 2. 参考源与许可对照

| 参考源 | 许可 | 本项目使用方式 | 许可义务履行 |
|---|---|---|---|
| alibaba/p3c | Apache 2.0 | 借鉴规则思想 | 未复制代码/文本，无 Apache 2.0 保留义务触发 |
| google/styleguide | CC-BY 3.0 | 借鉴风格共识 | 未引用文本；若引用需署名，本项目未引用 |
| spring-projects/spring-framework | Apache 2.0 | 设计思想 + API 使用 | API 功能性使用不受限 |
| baomidou/mybatis-plus | Apache 2.0 | 公开 API 使用 | API 功能性使用不受限 |
| mybatis/mybatis-3 | Apache 2.0 | 公开 API 使用 | API 功能性使用不受限 |
| SonarSource/sonar-java | LGPL 3.0 | 质量规则思想 | 未复制代码，无 LGPL 传染 |
| checkstyle/checkstyle | LGPL 2.1 | 参考规则思想（编码规范的规则名与判定口径） | 未复制其代码/文档/发行物；本仓规则文本为原创中文表述 |
| diffplug/spotless | Apache 2.0 | 构建期格式化工具（用户项目侧引入，本仓不打包） | 未随仓分发其代码，无保留义务 |
| eclipse-jdt formatter | EPL | 格式化引擎（经 Spotless 构建期拉取，本仓不打包） | 未随仓分发其引擎代码 |

> **指名性使用声明**：本文及本仓库内容中提及的第三方项目 / 工具名称（如 Checkstyle、Spotless、Eclipse、SpotBugs、Sonar、Spring、MyBatis 等）**仅用于指名性说明与许可署名**，**不代表任何赞助、背书或关联**；相关名称与商标归其各自所有者。

**关键结论**：
- 未复制任何开源项目的代码或受保护文本 → 未触发任何开源许可的再分发义务
- 未引入 GPL 代码 → 无 copyleft 传染风险
- **本仓不含任何外部工具的可执行文件/二进制**（Checkstyle / SpotBugs / Eclipse 引擎等 jar 均不打包）：对这些工具仅以文字引用规则名称与工具名；格式化配置 `java-code-standards/assets/eclipse-formatter.xml` 与对齐用的规则文本均为**原创整理**
- 本仓库以 MIT 许可发布（见 `LICENSE`），覆盖其全部原创内容

## 3. 受限源清单（禁止引用）

以下内容**禁止**引入本仓库：

- 《阿里巴巴 Java 开发手册》纸质书 / PDF / 电子版 — 受版权保护
- 第三方整理的阿里手册（如 Sxuan-Coder/alibaba-java-development-guide）— 侵权风险
- 任何未明确开源协议的博客、书籍、课程资料 — 版权不明
- 需付费/订阅获取的资料内容

## 4. 维护义务（贡献者必读）

向本仓库提交代码或内容时：

1. **只写原创**：用自己的话重写规则，自己写代码示例
2. **API 可用**：引用公开 API 是安全的，复制实现代码需要授权
3. **标注来源**：若参考了某开源实现后重写，在代码注释注明「参考自 xxx 项目（许可）」
4. **保留声明**：复制 Apache 2.0 代码必须保留版权声明 + NOTICE 文件，并记录来源
5. **GPL 拒绝**：默认禁止引入 GPL/LGPL 代码，除非明确评估并记录
6. **自查流程**：提交前检查有无整段粘贴、无来源代码、无手册原文

## 5. 自查记录

| 检查项 | 结果 | 日期 |
|---|---|---|
| 受限源引用扫描（阿里/手册/第三方整理） | 无 | 2026-08-16 |
| 翻译痕迹检查（大段英文文本） | 无（仅 SQL/DDL 上下文） | 2026-08-16 |
| 「复制自/摘自/来源」引用标记扫描 | 无 | 2026-08-16 |
| 开源代码整段复制检查 | 无（全部原创示例） | 2026-08-16 |
| 仓库聚合（8 技能并入 jee-forge）后重复检查 | 无新增引用 | 2026-09-04 |
| 格式规则（对齐 Checkstyle 10.x）与 Eclipse formatter 配置原创性核查 | 无引用受版权文本；配置为原创手写；未打包任何工具 jar | 2026-09-13 |
| 脚本衍生作品核查（`check-standards/scripts/*.py`、`test-workflow/assets/runner/runner.py`） | 独立实现（无上游许可证头/标识符/结构，无逐字翻译） | 2026-09-13 |
| check-standards 规则口径来源署名补充 + runner.py 复核 | `cs_checks.py` 头部补来源署名（#34~#43 仅对齐 Checkstyle 10.x 规则口径，未复制代码/文档/发行物）；`runner.py` 复核仍为独立实现，无新增引用 | 2026-09-14 |
| check-standards 扩展至 49 项（新增 #45~#49）+ 4 类误报修复 | 新增项（缩进一致性 / import 顺序 / 方法长度 / 方法参数个数 / equals-hashCode 成对）为**原创 Python 实现**，仅「规则口径」参考 Checkstyle 10.x（Indentation、ImportOrder、MethodLength、ParameterNumber、EqualsHashCode）；**未引入 Checkstyle 工具或其任何 jar**（符合 §4 第 5 条「GPL/LGPL 拒绝」），未复制其源码、配置、文档或发行物；规则名以自拟中文名呈现，英文规则名仅在来源说明中以**指名性方式**引用（见上文括注），未复制其规则文档描述文本 | 2026-09-16 |
| check-standards 扩展至 57 项（新增 #50~#57）+ #1/#37/#38/#39/#40/#41/#43/#45 口径升级 + 抑制注释过滤 | 新增项（catch 形参命名 / 静态变量命名 / 逗号分号后空格 / 成员之间空行 / 一行一声明 / 一行一语句 / package-import 不换行 / 花括号必写与位置）与升级项均为**原创 Python 实现**；仅「规则口径」参考 Checkstyle 10.x（CatchParameterName、StaticVariableName、WhitespaceAfter、WhitespaceAround、EmptyLineSeparator、MultipleVariableDeclarations、OneStatementPerLine、NoLineWrap、NeedBraces、LeftCurly、MissingJavadocMethod、UnusedImports、RedundantImport、RedundantModifier、JavadocType、TodoComment 等），口径经真实检查工具在本项目代码上的实测逐条校准（含边界写法探针），实现代码、注释文案、规则中文名均为自拟原创；**未引入 Checkstyle 工具或其任何 jar/配置/文档**（符合 §4 第 5 条「GPL/LGPL 拒绝」）；英文规则名仅在来源说明中以**指名性方式**引用 | 2026-09-16 |
| check-standards 误报治理（作用域收敛 / 语法自适应 / 命名与空格修正） | 全部为**原创实现**：① 资源类文件按 `--path` 收敛（新增 `--resources-scope auto/path/project`），避免扫某模块时带出同仓库其它子项目与参考 SQL；② `#11` 增加 PostgreSQL `COMMENT ON COLUMN/TABLE` 支持并按括号配对跳过跨行 `CHECK` 约束体；③ `#26` 白名单判定改为去注释后匹配（新增自研 `cs_java.strip_comments`）且不报纯接口声明；④ `#38` 排除自增自减与关键字后的单目符号；⑤ `#44` 声明正则要求类型与变量名之间有空白；⑥ `#10/#42` 同步上述口径。未引入、未复制任何受版权内容或第三方工具 | 2026-09-16 |
| check-standards 子项补强（`#39` 方法名禁单字母 / `#38` 花括号子项归并至 `#57` / `#57` 补 `}` 与 `else`·`catch`·`finally` 同行 / `#45` 补续行·case·数组初始化缩进候选） | 新增子项均为**原创 Python 实现**，仅「规则口径」参考 Checkstyle 10.x（`MethodName`、`Indentation` 的 `lineWrappingIndentation`/`caseIndent`/`arrayInitIndent`、`RightCurly` `option=same` 的规则名与判定口径）；其中 `#45` 的**缩进方向与期望值**（续行只报「不足」、`case` 严格多/少都报、数组初始化期望为一组 +4/+8）另经**外部真实 Checkstyle 10.20.2 + 外部 `rules/checkstyle.xml` 探针实测校准**（其中「枚举常量参数折行不参与续行缩进判定」同一并实测确认）；**未引入 Checkstyle 工具或其任何 jar/配置/文档**（符合 §4 第 5 条「GPL/LGPL 拒绝」），未复制其代码或文档文本；核对项编号与「57 项」计数均未变更 | 2026-09-16 |

> 后续内容变更后，重新执行上表自查并更新记录。
