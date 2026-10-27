# check-standards 机械核对工具

用 Python 标准库**机械执行** `SKILL.md` 定义的 57 项 Java 后端代码规范核对，输出结构化报告（Markdown + JSON）。
它**替代人工/模型逐条跑 grep/ast-grep 并整篇读 Java 文件**，但**不替代人的判断**：可机械判定的项给出 `pass/fail`；
语义类项（步骤注释质量、翻译式注释、幂等、防重入、NPE 等）一律标 `manual`/`warn` 并附证据，**绝不假装通过**。

## 环境要求

- Python **3.8+**，仅标准库（无 pip 依赖、无网络调用）。
- `rg`（ripgrep）**不需要**，未使用也能跑；`ast-grep` 完全不依赖。
- 兼容 UTF-8（含中文注释）与 CRLF；解析失败只记录 warning 并继续，绝不中断。

## 快速开始

```bash
# 1) 自检（内置 Java/XML 夹具，验证 57 项判定逻辑 + 默认扫描范围行为）
python3 scripts/check_standards.py --self-test

# 2) 默认：只扫本次 git 改动文件（AI 刚写完代码的兜底自检主场景）
#    取不到改动（无 git / 无改动）→ 自动回退全项目扫描，并在报告与 stderr 写明原因
python3 scripts/check_standards.py --project /path/to/project

# 3) 强制全项目扫描（全量体检/看存量问题才用）
python3 scripts/check_standards.py --project /path/to/project --all

# 4) 输出 JSON（机读）
python3 scripts/check_standards.py --project /path/to/project --format json --output report.json

# 5) 显式只扫本次改动 / 只扫某目录 / 只跑部分核对项
python3 scripts/check_standards.py --changed
python3 scripts/check_standards.py --path src/main/java/com/x/order --only 1,2,14,18
```

## 参数

| 参数 | 说明 |
|---|---|
| `--project DIR` | 项目根目录（默认当前目录） |
| `--path PATH` | 代码扫描范围：目录或单个文件。**相对路径按当前工作目录解析**；解析不到时**回退按 `--project` 再解析一次**（CWD 与 `--project` 不同目录时建议直接给绝对路径）；若最终仍扫到 **0 个 `.java`** → 按用法错误退出（**exit 2**），不产出核对结论。**AI 流程中不要传整模块/项目根的 `--path`**（会扫出几百上千个存量文件，又慢又污染本次核对结论） |
| `--changed` | 只扫 git 改动文件（优先 `git status`，回退 `git diff HEAD~1`；无 git 时降级为空范围，不报错）。**与「不传范围参数」的默认行为同口径** |
| `--all` | **强制全项目扫描**（自动探测 Maven `src/main/java`，多模块亦可）。默认只扫本次改动，需要全量体检时才加 |
| `--mode {auto,standard,legacy}` | 模式（默认 `auto`：读 2.1 约束 / 0.5 扫描决定，缺失则按规范默认 standard 并注明） |
| `--constraints PATH` | 显式指定 2.1 约束文件（覆盖自动探测） |
| `--format {md,json}` | 输出格式（默认 md） |
| `--output FILE` | 写入文件而非 stdout |
| `--only 1,2,3` | 只跑这些核对 id |
| `--skip 27,32` | 跳过这些核对 id |
| `--max-findings N` | 每项证据条数上限（默认 20，超出记 `...(+N more)`） |
| `--resources-scope {auto,path,project}` | 资源类文件（pom / 日志配置 / Mapper XML / SQL / 文档）的收敛范围，默认 `auto`：`--path` 子树 ∪ 集中目录（`sql/`、`db/`、`docs/` …）下**文件名含模块关键词**的文件（如扫 `xwd-mall-center` 会纳入 `sql/0930/0831-mall-center-init.sql`）；`path`=仅子树；`project`=全项目（旧行为） |
| `--verify --before A.json --after B.json` | 对比两次报告：断言原未通过项**已修（红→绿）**且**无任何项回退**（防"改 A 坏 B"）；只读、不写文件；`manual` 项单列「无机器验证」 |
| `--fix-renames` | 实际执行第 0 步 docs/ 重命名（默认**只检测不落盘**） |
| `-q, --quiet` | 不输出进度到 stderr |
| `--self-test` | 运行内置夹具自检后退出 |

**退出码**：`0` 无失败；`1` 至少一项 `fail`（`--verify` 模式下表示"存在未修好或回退"）；`2` 用法/内部错误（含 **`--path` 扫到 0 个 `.java`**、**范围 > 2000 个文件且未显式 `--all`** —— 前者空范围会被当成「无违规」产出假绿，后者曾导致单次扫 4874 文件跑 55 分钟才被中止；此类路径**不产出核对结论**）。

### 成本护栏（防"启动了不知道有多重"）

- 每次运行先在 stderr 打印：`本次范围 N 个 java 文件，预计约 X 秒`
- 范围 **> 1000 个文件** → 打印 ⚠️ 警告，建议改用默认范围（只扫本次改动）
- 范围 **> 2000 个文件且未显式 `--all`** → **直接拒绝（exit 2）**；确认要做全量体检再显式加 `--all`
- 范围 **≥ 200 个文件**时，每完成 10 项打一行 `[进度] 已完成 N/57 项`（`-q` 时静默）

> 默认 `project` 范围扫到 0 个 `.java` 时**不改退出码**（保持既有用法），但报告「范围说明」会打出 `⚠️ 未扫到任何 .java 文件…结果不可信` 的显式告警。

## 核对范围（scope）

**优先级（高 → 低）**：`--path` / `--changed`（显式） → `--all` → 默认。

- 传 `--path` → 扫该路径，报告 `scope=path`。相对路径先按 CWD、再回退按 `--project` 解析；
  两条都不是有效路径 → 扫到 0 个 `.java` → **exit 2**（防「空范围全项 PASS」的假绿）。
- 传 `--changed` → 用 git 取改动的 `.java`，报告 `scope=changed`；命中证据标注 `[本次改动]` / `[存量]`。无 git 改动时降级为空范围并在 note 说明（显式指定时的既有语义不变）。
- **都不传（默认）→ 只扫本次 git 改动文件**（与显式 `--changed` 同口径），报告 `scope=changed`，`scope_note` 与 stderr 都会写明「默认只扫本次改动文件；如需全量请加 `--all`」；
  取不到 git 改动（无 git / 无改动 / 工作区干净）→ **回退全项目扫描**（`scope=project`），并在报告写明「未检测到 git 改动，已回退全项目扫描」。
  > WHY: 「AI 刚生成完代码 → 兜底自检」才是主场景，默认扫全仓既慢又没必要（曾发生调用方传整模块 `--path` 扫 849~4874 个文件的极慢事故）。但**绝不能**因「无改动」返回 0 文件全项 PASS——那是本工具踩过的「静默假通过」坑，故必须回退全项目。
- 传 `--all` → 强制全项目（自动探测 Maven 多模块 `src/main/java`），报告 `scope=project`，note 为「全项目扫描（--all 显式指定）」。
- 报告头会写明最终范围；范围解析结果同时打到 stderr（`[check-standards] 范围=…` + `范围说明：…` 两行）。

## 模式（standard / legacy）

选型敏感项 **#6 接口文档 / #7 日志框架 / #8 SQL 在 XML / #20 统一返回体** 按模式判定：

- 找到 `docs/**/2.1-项目约束*.md` → standard；找到 `0.5-存量代码扫描.md` 或 `2.1-项目约束-存量适配.md` → legacy。
- 都没有 → 回退 standard，并在报告 `模式说明` 注明「按规范默认值判定（未找到 2.1 约束）」。
- 判定不了选型的（如无依赖、无注解、无约束文件）→ 记 `manual`，**不猜**。

## 57 项核对（id → 规则）

> 本表是**脚本实现视角**的摘要（含 manual 判定条件），供维护者对照代码。
> **判定口径的单一事实源是 `../references/checklist.md`**；模型侧要判据不必读任何表格，直接

      python3 check_standards.py --explain

> 或看报告 JSON 的 `judgment` 字段（`../scripts/cs_checks.py` 的 `CHECK_GUIDE`）。改口径时三处需同步：checklist.md / CHECK_GUIDE / 本表。

| 组 | id | 规则（摘要） |
|---|---|---|
| 方法/日志 | 1 | Controller/Service/ServiceImpl/Listener/Job 的每个方法（含私有/构造器）有 Javadoc |
| | 2 | 每个业务方法体内 ≥1 条 INFO/WARN/ERROR（debug 不算）；纯 getter/setter/单行透传豁免；`≥20 行仅开头 1 条` → manual 半覆盖 |
| | 3 | 编号步骤注释覆盖（≥6 行无注释 / ≥10 行连续裸逻辑 / 长方法后半段无注释）→ manual |
| | 4 | 禁翻译式注释 → manual |
| | 5 | 目标类全有 `@Slf4j`；无 `System.out/err` |
| 框架/产物 | 6 | 接口文档依赖 + `@Tag/@Operation/@Api/@Schema`（选型敏感） |
| | 7 | logback/log4j2 配置文件 + pom 依赖（选型敏感） |
| | 8 | 无注解 SQL（`@Select` 等）/`<script>`；手写 SQL 在 XML（选型敏感） |
| | 9 | 存在符合 `3.<n>[.<m>]-*接口清单（前后端通用）.md` 命名的产物；仅有 `xx-接口清单…` 等不规范命名 → `manual`（提示先做第 0 步矫正），不再误判 pass |
| SQL 安全 | 10 | 技术方案内 SQL 代码块带注释 |
| | 11 | `CREATE TABLE` 每字段 `COMMENT` + 表级 `COMMENT` |
| | 12 | Mapper XML 无 `${}` 拼接（MyBatis-Plus `ew.` 包装器降级 manual）；Java 无字符串拼接 SQL |
| | 13 | Mapper XML 中 UPDATE/DELETE 均带 WHERE |
| 事务/质量 | 14 | `@Transactional` 必带 `rollbackFor` |
| | 15 | 无 `@Autowired` 字段注入（legacy 记 manual） |
| | 16 | Controller 不引用 Mapper、不含 `@Transactional` |
| | 17 | Controller 不暴露 Entity（`@TableName`/`*Entity`） |
| | 18 | 无裸 `RuntimeException`、无空 `catch` |
| | 19 | 无单字母异常参数/类型名 |
| | 20 | Controller 不裸返回 `Map`；使用统一返回体（选型敏感） |
| | 21 | 密码不用 MD5/SHA1（要求实际调用，排除字段名/注释） |
| | 22 | `pageSize` 字段声明有 `@Max` 等上限校验；无任何 `pageSize` 字段声明（走基类/框架分页）→ `skip` |
| | 23 | 校验 `message` 不笼统（`参数/数据/输入/请求/字段/内容/信息` × `不合法/错误/非法/无效/有误/不正确/格式不对`） |
| 场景/其余 | 24 | @Scheduled/Quartz Job → 防重入 + LIMIT（manual） |
| | 25 | @RabbitListener/@KafkaListener → 幂等 + 死信（manual） |
| | 26 | MultipartFile → 白名单/UUID/大小（manual） |
| | 27 | POST/PUT 写接口 → 幂等（manual） |
| | 28 | 日志不含明文 password/token/secret |
| | 29 | 集合命名 `xxxList/xxxSet/xxxMap` |
| | 30 | 魔法值/缓存 key 集中定义（manual） |
| | 31 | 重复方法体 → 抽公共（manual） |
| | 32 | 日志占位符参数含方法调用 → NPE 风险（manual） |
| | 33 | 一张表只允许一个 `@TableName` 映射 |
| 格式/卫生 | 34 | 每行无行尾空白（`[ \t]+$`）、缩进无 Tab（`^\t` / `^[ ]*\t`） |
| | 35 | 行长 ≤ 120 字符（`package `/`import ` 开头或含 `http://`/`https://` 的行豁免） |
| | 36 | 无连续空行（原文匹配 `\n[ \t]*\n[ \t]*\n`） |
| | 37 | import 卫生：无通配符 `import ...*;`、无 `sun.`/`com.sun.` 内部 API、无疑未使用（非 static import 的简单名在文件体不再出现；字面启发式） |
| | 38 | 空格（启发式）→ manual：运算符缺两侧空格；花括号类判定归 #57，本项不再重复给候选 |
| 命名/结构/卫生 | 39 | 命名规范（大小写/形式）：package 段全小写；顶层类型 UpperCamelCase 且非单字母；方法 lowerCamelCase 且非单字母（跳过构造器）；`static final` 常量 UPPER_SNAKE_CASE（豁免 log/logger/serialVersionUID）；泛型形参单个大写字母；>3 连续大写缩写（排除 DAO/ID/DTO/VO/PO/BO/SQL/URL/URI/HTTP/JSON/XML/API）→ manual |
| | 40 | 类与文件结构：有 `package` 声明；仅一个顶层类型声明；顶层类型上方有 `/** */` Javadoc（允许 Javadoc 之上还有**跨多行注解**；`module-info.java` 豁免） |
| | 41 | 书写卫生：修饰符顺序非 JLS 建议顺序 / **接口自身成员**的冗余修饰符（方法显式 `public`、字段显式 `static final`·`public`；接口内嵌套类/匿名类的 `public` 是必需修饰符，不计）/ C 风格数组 `Type name[]`（`String[] a`、`new String[]{…}` 标准写法不计）/ 小写 `l` 长整型后缀 / `printStackTrace()` |
| | 42 | 字符串比较：字符串字面量用 `==`/`!=` → fail；`y.equals("CONST")` 常量未前置、疑似字符串 `==`（名字含 Str/String/Name/Code/Type/Status/Msg/Text）→ manual；**枚举与常量比较已排除**（`Type.CONST`、裸 `UPPER_SNAKE`、声明类型为项目内枚举的变量） |
| | 43 | 遗留标记：`TODO`/`FIXME` 注释（豁免流程收敛标记 `// TODO(收敛)`） |
| | 44 | 变量命名（启发式）：成员/局部/参数/lambda 变量 lowerCamelCase（含 `_` 或首字母大写 → manual 候选；跳过常量/枚举/类/方法/循环变量） |
| 缩进/import/规模/成对 | 45 | 缩进一致性（启发式）→ manual：语句起始行缩进须为 4 空格倍数；续行（以 `.`/`+`/`,`/`)`/`&&`/`\|\|` 开头，或上一非空行以 `(`/`,`/`=`/`+`/`.`/`->` 结尾）对齐不计；**续行缩进不得少于**语句起始行 +8（`lineWrappingIndentation`，**超出不报**——实测只报不足）；`case`/`default` 相对 `switch` +4（`caseIndent`，严格：多/少都报）；数组初始化元素相对初始化起始行 +4 **或** +8 均合规（`arrayInitIndent` 期望为一组）；**枚举常量参数的折行不在判定范围**（实测该工具对枚举常量参数折行不做 `lineWrappingIndentation` 判定，与缩进量无关）；以上续行类只覆盖高置信形态，识别不确定不报 |
| | 46 | import 顺序（启发式）→ manual：分组 **第三方 → `javax` → `java`/`jdk`/`sun`**，各组内按包名字典序；`static` import 不参与；以「相邻逆序」为证据 |
| | 47 | 方法长度：方法体代码行数 > 100 → fail（注释/空行/纯大括号行不计） |
| | 48 | 方法参数个数：形参个数 > 7 → fail（枚举常量 `UPPER_SNAKE` 视为常量而非方法，不计） |
| | 49 | equals/hashCode 成对：手写其一未写另一个 → fail；豁免 record 与 Lombok `@Data`/`@EqualsAndHashCode`/`@Value` |
| | 50 | catch 形参命名：须为 `e`/`t`/`ex`/`_`，或小写开头且长度 ≥3 的纯字母名 → fail |
| | 51 | 静态变量命名：非 `final` 的 `static` 字段须 lowerCamelCase → fail（常量归 #39） |
| | 52 | 逗号/分号后空格：`,` `;` 后、类型转换 `)` 后、控制关键字后须有空白 → fail |
| | 53 | 成员之间空行：方法/构造器前须有空行 → fail；豁免首个成员与「上一成员是字段」 |
| | 54 | 一行一声明：一条声明内定义多个变量（`int a = 1, b = 2;`）→ fail |
| | 55 | 一行一语句：同一行多条语句 → fail（`for` 头分号与 `do{}while()` 除外） |
| | 56 | package/import 不换行：语句被换行拆断 → fail |
| | 57 | 花括号必写与位置：`if`/`for`/`while`/`do`/`else` 缺 `{}`、`{` 不在行尾或其后同行跟代码、`}` 与 `else`/`catch`/`finally` 未同行（`RightCurly` `option=same`）→ fail |

## 第 0 步：产物命名矫正（默认只检测）

扫描 `docs/**/*.md`，检测：技术方案漏 `.1`、任务 ID 前缀 `T\d+-`、接口清单/任务拆解/5.2/5.3 报告命名、
路径不在 `docs/<模块名>V<版本>-<时间戳>/` 下。结果进报告的 `renames`。**默认只列出不改**；
加 `--fix-renames` 才会对 docs/ 下 `.md` 执行重命名并打印所做操作（非 docs/ 内容一律不碰）。

## 输出格式

Markdown 头：

```
=== 关键规范核对报告 ===
项目: <path>    时间: <ts>    模式: standard/legacy    核对范围: 本轮改动（默认）/ <dir> / 全项目（--all）
范围说明: 默认只扫本次改动文件；如需全量请加 --all（git status（未提交改动））
```

逐项行：`[✅]/[❌]/[⚠️ 需人工]/[⏭ 跳过] <id> <name>   说明: ...   证据: file:line ...`，
末尾「结论」与「待用户确认清单（未执行到位项）」。

JSON 稳定结构：

```json
{"project":"...","scope":"project|path|changed","scope_path":"...","mode":"standard|legacy",
 "generated_at":"ISO8601","tool_version":"1.0.0",
 "renames":[{"old":"...","new":"...","reason":"..."}],
 "items":[{"id":1,"name":"...","status":"pass|fail|warn|manual|skip","note":"...",
           "evidence":[{"file":"...","line":12,"detail":"..."}]}],
 "summary":{"pass":0,"fail":0,"warn":0,"manual":0,"skip":0},
 "pending_confirmation":[1,2,14]}
```

## AI 如何调用（省上下文）

```
请先运行并读取结果，不要逐条 grep（默认只扫本次 git 改动；全量体检才加 --all）：
  python3 scripts/check_standards.py --project <项目> --format json --output /tmp/cs.json
然后：只读 pending_confirmation 里 fail 的项，按证据定位修复；
先看报告 scope / scope_note 确认范围（是否只扫了改动 / 是否回退全项目）；
manual 项再按需人读判断；修复后重跑同一命令确认 fail 归零。
```

## 跨平台 / Windows 兼容

- 所有读写均显式指定编码（读 `utf-8-sig`/`utf-8`，回退 `gb18030`/`latin-1`；写 UTF-8），不依赖系统 locale。
- 启动时把 stdout/stderr 切到 UTF-8，Windows GBK 控制台不会因中文乱码/编码错误崩溃。
- 路径全部走 `os.path`，并把 `\`/`/` 归一化后比较；兼容 CRLF。未使用 `fcntl`/`os.fork`/信号等 POSIX-only API，无绝对 `/tmp` 依赖（临时文件用 `tempfile`）。
- `--changed` 在无 git 时降级为空范围并给出说明，不抛 traceback。

## 已知局限（诚实清单）

- #1/#2/#3 的方法识别基于轻量括号扫描（非 AST），极少数语法形态（记录类紧凑构造器、注解数组内花括号等）可能识别不全；未识别的方法不计入证据，但也不会误判为 pass。
- **决策项（不判 fail，交人决策）**：#24 Job 防重入 / #25 Listener 幂等 / #26 文件上传安全 / #27 写接口幂等 —— 这些问的是"业务上要不要做、怎么做"，脚本只输出「方法/类 + 行号 + 已发现的防护痕迹 + 一行提示」供人拍板，**不判 pass/fail**。
- **人工判定（质量类，无法机械化）**：#4 翻译式注释 / #30 魔法值 / #39 缩写连写 / #42 常量未前置的 equals·疑似字符串 `==` / #45 的续行·注解·数组部分 —— 输出候选证据供人判断，**不自动 pass**。
- **已升级为机器判定（fail）**：#3（连续 ≥10 行代码无任何注释）/ #31（≥2 处方法体完全相同）/ #32（日志参数含高危取值链 `.get(...).`）/ #38（运算符·关键字两侧缺空格）/ #44（变量命名含 `_` 或首字母大写）/ #45（语句起始行缩进非 4 倍数）/ #46（import 分组·字典序逆序）。
- #39/#40/#41/#43 为格式/命名类**硬规则**，标准与存量两模式均执行（不按模式豁免）。
- #6/#7/#8/#20 依赖项目模式的选型；无 2.1/0.5 约束文件时按规范默认并在报告注明。
- `--changed` 的「本次改动/存量」标注需要该目录是 git 仓库。
- **默认范围的取改动口径沿用 `git status` / `git diff HEAD~1`**：若新增的 `.java` 落在**全新的未跟踪目录**里，
  `git status` 默认会把整个目录折叠成 `?? dir/`（不逐文件列出）→ 取不到 `.java` → 默认范围**回退全项目扫描**
  （安全但慢，不会假绿）。新增文件落在**已跟踪目录**内可正常识别；也可显式 `--path <该目录>` 精确限定。
- **默认范围下「全项目」是回退结果，不是默认意图**：报告 `scope=project` 时先看 `scope_note`——
  写「--all 显式指定」= 你要求全量；写「已回退全项目扫描」= 工具没取到改动。
- **资源类文件同样受 `--path` 收敛**（默认 `--resources-scope auto`）：若 DDL / 日志配置集中放在
  项目级目录且**文件名不含模块关键词**，扫某模块时不会被纳入（避免带出同仓库其它子项目、
  参考 SQL 的大量无关问题）。需要全项目资源视图时不传 `--path`，或显式 `--resources-scope project`。
- `#11 DDL 注释` 同时支持 MySQL 字段内联 `COMMENT` 与 PostgreSQL `COMMENT ON COLUMN/TABLE`，
  并按括号配对跳过跨行 `CHECK (...)` 约束体；`#26 文件上传` 的「白名单」判定在**去注释**后的
  文本上匹配（注释或 Javadoc 里提到 `.xlsx` 不算证据），且不报纯接口声明。
- 工具**只读**源码；只有显式 `--fix-renames` 才会重命名 `docs/` 下的 `.md`。
- **#45 的续行缩进已作为候选覆盖**（`lineWrappingIndentation=8`），但只覆盖高置信形态
  （运算符前置折行、语句起始行有未配对左括号等）；**深层续行的相位推进**（嵌套 lambda、
  长方法链的多级折行）不做精确还原——识别不确定时一律不报，剩余差异由交付前的静态检查终验兜底。
- **#35 行宽按 120 判定**（比多数静态检查默认的 160 更严）：更严必然通过更宽的口径，
  代价是个别 121~160 字符的行会被要求折行。
- #50~#57 与 #1/#37/#38/#39/#40/#41/#43/#45 的**规则口径**以真实静态检查工具在本项目代码上的
  实测结果逐条校准（含边界写法探针），实现为原创 Python。本仓**不打包、不依赖**该工具及其 jar
  （符合仓库根 `COPYRIGHT.md` §4 第 5 条「GPL/LGPL 拒绝」）；仅以指名方式引用其规则名。

### 抑制注释（与静态检查对齐）

报告生成前会按下列写法过滤证据，即静态检查会抑制的写法本工具同样不再报出：

```java
// CHECKSTYLE:OFF TodoComment
... 被抑制的代码 ...
// CHECKSTYLE:ON TodoComment

// checkstyle:ignore LineLength      ← 抑制本行与下一行
```

> 说明：按规则名匹配，`ALL` 表示匹配全部规则；为简化实现，报告侧过滤按「该行被任一规则抑制」
> 处理，可能略宽于逐规则精确匹配。
