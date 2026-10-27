# 核对项完整清单（57 项）

> 归属：`check-standards` 技能的判据字典，从 SKILL.md 移出以降低「每次代码核对都整篇加载」的体量。
>
> **何时读**：① 无 Python 环境、需按「标准检查指令」手工执行时（降级路径）；
> ② 脚本报 `manual/warn` 但输出中的判据摘要不足以判定时；③ 新增/修改核对项需对齐口径时。
>
> **正常流程不用读**：脚本 `check_standards.py` 的每项输出已带判据摘要（`judgment` 字段，`--explain` 可看全量），
> 模型按摘要判 `manual/warn` 项即可。
>
> **单一事实源**：本文件的判定标准是核对口径的唯一来源；`scripts/cs_checks.py` 的机械实现必须与本文件一致，
> 改动任一侧都要同步另一侧（见 `docs/skill-maintenance-checklist.md`）。另两处是**摘要/实现视角**，不另立口径：
> `scripts/cs_checks.py` 的 `CHECK_GUIDE`（每项判据摘要）与 `scripts/README.md` 的「57 项核对（id → 规则）」表——改口径时三处必须同步。
>
> **分组约定**：本文件的分组（一~九）仅作文档组织用途，**引用核对项一律用 `#id`（1~57）**；
> 脚本内部另有分组划分（如 `#44 变量命名` 单列一组），**不要求与本文档组号对齐**。

---

**所有核对项无级别之分**：每项都是硬规则，未执行到位一律 ❌ 进待用户确认清单（与用户确认补齐/跳过），不存在"HIGH 必改 / INFO 可跳过"之分。选型敏感项 ⚠️ 按 2.1 约束/0.5 扫描口径判定（见"模式判定"），其余按规范。**核对范围按上「核对范围界定」执行**（指定目录 / 本轮改动 git diff / 全项目三种）——**下方指令中的 `src/main/java` 等路径均为示例，实际执行时替换为界定后的范围**。

### 一、方法与日志覆盖（新代码必核——注释/日志必须覆盖所有代码，含抽取的 private 方法）

> 痛点根源：ServiceImpl 方法无日志、Controller 抽取的 private 方法大段无注释无日志，旧核对只扫 public 方法所以漏检。**本组按"方法级"机械核对，public + private + 抽取方法全覆盖**。

| # | 核对项 | 标准检查指令（实际执行） | 判定标准（全部满足才 ✅） |
| :---: | :--- | :--- | :--- |
| 1 | **方法级注释全覆盖** | ast-grep 列全部方法节点（`$MOD $RET $NAME($$$) { $$$ }`，含 public/private/protected/静态），逐个核对方法声明上方有 `/** */` Javadoc | **目标类（Controller/ServiceImpl/Service/Listener/Job/Consumer）所有方法（public + private + 抽取方法）有 Javadoc**：功能 + @param/@return 写业务含义；其余类型按静态检查口径核对其**显式 public** 方法与构造器（隐式 public 的接口方法不判），豁免 `@Override`、getter/setter 单行透传、方法体不足 2 行的短方法 |
| 2 | **方法级日志全覆盖** | grep/ast-grep 逐个检查方法体内是否含 `log.info`/`log.warn`/`log.error` 调用（**`log.debug` 不算——线上不输出，视为无日志**）；再对含日志的方法判断是否覆盖关键阶段 | **Controller/Service/ServiceImpl/Job/Listener 的每个业务方法（public + private 抽取方法）方法体内 ≥1 条 INFO/WARN/ERROR 业务日志**（入口入参摘要 / 关键分支 / 结果返回前）；**方法内无任何 INFO/WARN/ERROR（即使有 log.debug）→ ❌**；大段逻辑（≥10 行）无 INFO/WARN/ERROR → ❌；方法含 ≥2 个业务阶段（查库/状态变更/循环组装等）但仅开头 1 条日志、中间关键逻辑无 INFO → ❌（"半覆盖"漏网形态）；纯 getter/setter/单行透传可豁免（注明豁免原因）；异常处 ERROR 带堆栈 |
| 3 | 步骤注释 + WHY | `grep -rn "// 1\." src/main/java` 抽查 + **对脚本报出缺口的方法逐个核对（只读该方法，长方法必须逐段核对，不得只 grep 命中数判 ✅）** | 方法体 ≥2 个逻辑步骤有编号注释（`// 1.` `// 2.`…，覆盖到方法最后一段逻辑）；**方法内每个业务段（查询/校验/循环/状态变更/组装）都有步骤注释，不得前半段有注释后半段裸奔**；复杂逻辑有 `// WHY:`；**无 ≥10 行连续逻辑代码零注释（脚本判定，命中即 ❌）**；长方法（>20 行）逐段核对（含方法后半段）；深层嵌套（≥3 层）分支前有注释（存量模式同样要求） |
| 4 | 禁翻译式注释 | 抽查注释 | 无逐行翻译式注释；注释写业务含义非复述代码 |
| 5 | 全类 @Slf4j + 无 System.out | `grep -rln "@Slf4j" src/main/java`；`grep -rn "System.out" src/main/java` | Controller/Service/ServiceImpl/Job/Listener 全类 @Slf4j，无 System.out、无散落 Logger 混用 |

### 二、框架与产物（选型敏感 ⚠️ 按项目模式判定）

| # | 核对项 | 标准检查指令（实际执行） | 判定标准（全部满足才 ✅） |
| :---: | :--- | :--- | :--- |
| 6 | 接口文档支持 ⚠️ | `grep -n "springdoc\|knife4j\|springfox\|swagger" pom.xml`；`grep -rln "@Tag\|@Operation\|@Api\|@ApiOperation" src/main/java`；`grep -rln "@Schema\|@ApiModelProperty" src/main/java` | 有依赖或有注解 → ✅；**两者都无时**：约束文件（2.1 / 0.5）写明选型 → ❌；未写明选型 / 无约束文件 → ✅（按「不确定当正常」处理，不产候选） |
| 7 | 日志框架支持 ⚠️ | `ls src/main/resources/logback*.xml src/main/resources/log4j2*.xml`；`grep -n "log4j2\|logback" pom.xml` | 有日志配置（logback/log4j2*）→ ✅；仅 pom 声明、无配置文件 → 候选（manual，可能配在 yml 里）；**两者都无时**：约束写明选型 → ❌；未写明 / 无约束 → ✅（「不确定当正常」） |
| 8 | SQL 在 XML ⚠️ | `grep -rn "@Select\|@Insert\|@Update\|@Delete\|<script>" src/main/java`；`ls src/main/resources/mapper/*.xml` | 标准模式：无注解 SQL，手写 SQL 全在 XML，namespace 一致；老项目按 0.5 数据访问约定判定 |
| 9 | JSON 入参/出参产物 | `ls docs/*/3.*.2-接口清单（前后端通用）.md` | 每个 Controller 功能项的接口清单已生成，URL+方法+JSON 入参/出参（成功/失败）与方案一致 |

### 三、SQL 与数据安全

| # | 核对项 | 标准检查指令（实际执行） | 判定标准（全部满足才 ✅） |
| :---: | :--- | :--- | :--- |
| 10 | SQL 注释（方案内） | `grep -rn "CREATE TABLE\|SELECT \|INSERT INTO\|UPDATE " docs/*/3.*.1-技术方案*.md` | 方案《数据模型与 SQL》所有 SQL 带注释：DDL 每字段 COMMENT；查询/DML 每条 `--`（用途+归属 Mapper+关键条件） |
| 11 | DDL 字段注释 | `grep -A 25 "CREATE TABLE" src/main/resources/db/schema.sql docs/*/3.*.1-技术方案*.md` | CREATE TABLE 每个字段带 COMMENT + 表级 COMMENT；无裸字段 |
| 12 | SQL 注入 | `grep -rn '\${' src/main/resources/mapper/*.xml`；`grep -rn '"SELECT \|"INSERT \|"UPDATE \|"DELETE ' src/main/java` | XML 无 `${}` 拼接值；Java 无字符串拼接 SQL；无 apply()/last() 传用户输入 |
| 13 | UPDATE/DELETE 带 WHERE | `grep -rn -i "^[[:space:]]*UPDATE \|^[[:space:]]*DELETE " src/main/resources/mapper/*.xml` | 所有 UPDATE/DELETE 带 WHERE（无 WHERE → ❌） |

### 四、事务与代码质量

| # | 核对项 | 标准检查指令（实际执行） | 判定标准（全部满足才 ✅） |
| :---: | :--- | :--- | :--- |
| 14 | 事务 rollbackFor | `grep -rn "@Transactional" src/main/java` | 每个 @Transactional 均带 rollbackFor = Exception.class |
| 15 | 构造器注入 | `grep -rn "@Autowired" src/main/java`（应为空） | 无字段注入；统一构造器注入（@RequiredArgsConstructor + final）（存量模式按老约定） |
| 16 | 分层边界 | `grep -rn "Mapper" src/main/java/*/controller/*.java`；Controller 方法体抽查 | Controller 不注入 Mapper、不写业务逻辑/SQL/事务 |
| 17 | Entity 不暴露 | `grep -rn "Entity\|@TableName" src/main/java/*/controller/*.java` | 接口出入参用 DTO/VO，不暴露 Entity |
| 18 | 异常处理 | `grep -rn "throw new RuntimeException\|catch (.*) {}" src/main/java` | 无裸 RuntimeException；无空 catch 吞异常 |
| 19 | 命名单字母/泛称 | `grep -rn "catch (.* e)\|throw new.*(.* e)" src/main/java` | 无单字母类名、异常参数非 e、无泛称变量 |
| 20 | 统一返回体 ⚠️ | `grep -rn "Map<" src/main/java/*/controller/*.java`；`grep -rln "class R\b\|class Result\b" src/main/java` | 按 2.1/老约定：Controller 返回 Response<T>/PageResult<T>（存量按老返回体），无 Map 裸返回 |
| 21 | 密码加密 | `grep -rn -i "md5\|sha1\|DigestUtils" src/main/java` | 无 MD5/SHA1 存密码（用 BCrypt 慢哈希） |
| 22 | 分页上限 | `grep -rn "pageSize\|PageQuery" src/main/java/*/dto/*.java` | 分页入参 pageSize 有 @Max/上限校验 |
| 23 | 校验 message 具体性 | `grep -rn 'message = "' src/main/java` 抽查 + 定位 @NotBlank/@NotNull/@Size/@Pattern/@Min/@Max 等校验注解 | **校验注解 message 必须具体**：含业务字段名 + 具体原因（"手机号不能为空"/"数量必须大于0"）；**禁止无字段语义笼统文案**——message 值若仅由笼统词构成（前缀 `参数/数据/输入/请求/字段/内容/信息` × 结论 `不合法/错误/非法/无效/有误/不正确/格式不对`，含标点变体）→ ❌ 附证据（文件:行号 + message 原文） |

### 五、场景化 + 其余项（对应类型文件存在时才核 / 人工项）

| # | 核对项 | 触发条件 / 检查指令 | 判定标准 |
| :---: | :--- | :--- | :--- |
| 24 | Job 防重入 + 批处理 | `grep -rln "@Scheduled" src/main/java` 有命中 | 有分布式锁/状态位防重入；批处理带 LIMIT；无长事务 |
| 25 | Listener 幂等 + 死信 | `grep -rln "@RabbitListener\|@KafkaListener" src/main/java` 有命中 | 消费幂等；重试有上限 + 死信队列；无 catch 静默 |
| 26 | 文件上传安全 | `grep -rln "MultipartFile" src/main/java` 有命中 | 扩展名+MIME 双白名单；UUID 重命名；大小限制 |
| 27 | 写接口幂等（HTTP） | Controller 存在 POST/PUT 写接口 | 写接口有幂等方案（唯一键/令牌/Redis SETNX），幂等键与业务同事务（自动 grep 难查 → 人工抽查标"需人工核对"） |
| 28 | 敏感信息进日志 | `grep -rn "password\|token\|secret" src/main/java` | 日志/异常/响应不含密码/token 明文（命中核对是否脱敏） |
| 29 | 集合命名 | `grep -rn "List<.*> records\|List<.*> codes\|Set<.*> values" src/main/java` | 集合字段用 xxxList/xxxSet/xxxMap 后缀 |
| 30 | 魔法值/缓存 key | 抽查常量类 | 无裸魔法值；缓存 key 集中常量定义 |
| 31 | 公共组件复用 | 扫描 common/util、common/base 与业务重复方法体 | 无 ≥2 处**方法体完全相同**（去空白后逐字符相等 → ❌，应抽公共组件） |
| 32 | 日志参数 NPE（求值安全） | `grep -rn 'log\.\(debug\|info\|warn\|error\)(".*{[^}]*}",' src/main/java` 列出含占位符参数的日志行 → **逐处人工确认**（启发式，命中后需人眼判）：参数是否含 `.getXxx(` / `.getName(` / `.get(0` / 链式 `.getUser().` 等**方法调用**且调用者未先判空 | **日志参数不得写可能 NPE 的调用**：判空前的 `.getId()`、链式取值任一环可能 null、`list.get(0)` 空集合、`map.get(k).xxx()` 值为 null（eager 求值，日志行先炸，判空在后救不了）——见 java-code-standards `00-common/04-logging-standards.md` §6；**脚本判定（fail）**：日志参数含**高危取值链** `.get(...).`（取值可能为 null 再取成员 = 必 NPE）；普通 getter 调用（`obj.getId()`）不报——是否已判空脚本判不了，按「不确定当正常」不产候选 |
| 33 | 同表重复映射 | `grep -rhn '@TableName("[^"]*")' src/main/java` 统计各表名出现次数 → 出现 >1 次的表名列清单 | **全项目一张表只允许一个 Entity 映射**（同表唯一映射，见 java-code-standards `01-java/entity-standards.md` §1）：`@TableName("x")` 出现 >1 次 → ❌ 附证据（重复表名 + 各映射 Entity 类文件:行号）；确认其中 N-1 个无业务引用（grep 引用点）→ 提示删除/收敛 |

### 六、代码格式（#34–#38，对齐 Checkstyle 10.x）

> 本组补齐原 33 项的"格式"空白。**可靠项**（#34~#37）脚本给 `pass/fail`；**#38**（空格）为启发式，标 `manual` 交人工确认；花括号类判定为可靠项，统一归 #57。格式规则通用，标准/存量模式都核。

| # | 核对项 | 判定标准（全部满足才 ✅） |
| :---: | :--- | :--- |
| 34 | 行尾空白与 Tab | 无行尾空白字符；缩进无 Tab（4 空格） |
| 35 | 行宽超限 | 单行 ≤120 字符（`package` / `import` / URL 行豁免） |
| 36 | 连续空行 | 无连续 2 行以上空行 |
| 37 | import 卫生 | 无通配符 import、无 `sun.*` / `com.sun.*`、无未使用 import |
| 38 | 空格 | 运算符/关键字两侧有空格（脚本判定，命中即 ❌）；花括号类判定见 #57（必写 / `{` 位置 / `}` 与 `else`·`catch`·`finally` 同行） |

### 七、命名 / 结构 / 书写卫生（#39–#44，对齐 Checkstyle 10.x）

> 本组补齐命名大小写与书写卫生。可机械判定项给 `pass/fail`；#42 字符串比较为启发式标 `manual`。格式/命名规则通用，标准/存量模式都核。

| # | 核对项 | 判定标准（全部满足才 ✅） |
| :---: | :--- | :--- |
| 39 | 命名规范（大小写/形式） | 包名全小写；类/接口/枚举 UpperCamelCase 非单字母；方法 lowerCamelCase 且非单字母；常量 UPPER_SNAKE（`log`/`logger` 豁免）；泛型参数单个大写字母；缩写连续大写 ≤3（DAO/DTO/VO/SQL/URL/HTTP/JSON/XML/API/ID 等豁免） |
| 40 | 类与文件结构 | 必须声明 `package`；一文件一顶层类；顶层类有 Javadoc（Javadoc 可在注解之上，跨行注解同样识别） |
| 41 | 书写卫生 | 修饰符顺序正确、无冗余修饰符；数组 `int[] a`；`long` 用大写 `L`；无 `printStackTrace()` |
| 42 | 字符串比较（启发式） | 字符串用 `equals`（非 `==`）；`equals` 常量前置（脚本给候选，人工确认）。**枚举/常量比较（`Type.CONST`、裸 `UPPER_SNAKE`）不计入**——枚举用 `==` 是推荐写法 |
| 43 | 遗留标记 | 无 `TODO` / `FIXME`（唯一例外：流程标记 `// TODO(收敛)`） |
| 44 | 变量命名 | 成员/局部/参数/lambda 变量 lowerCamelCase（脚本判定：含 `_` 或首字母大写即 ❌；跳过常量/枚举/类/方法/循环变量） |

### 八、缩进 / import 顺序 / 方法规模 / equals 成对（#45–#49，对齐 Checkstyle 10.x）

> 本组为 B 方案补强项（自研实现、**规则口径**对齐 Checkstyle 10.x，未复制其代码/文档）。可机械判定项给 `pass/fail`：#47 方法长度 / #48 参数个数 / #49 equals-hashCode，以及 **#45 的「语句起始行缩进非 4 倍数」与 #46 import 顺序**（已升级为 fail）；**#45 的续行·注解·数组部分仍标 `manual`** 给候选证据。标准/存量模式都核。

| # | 核对项 | 判定标准（全部满足才 ✅） |
| :---: | :--- | :--- |
| 45 | 缩进一致性 | ① 语句起始行缩进为 4 空格倍数（**续行对齐不计**：以 `.`/`+`/`,`/`)`/`&&`/`\|\|` 开头的行，或上一非空行以 `(`/`,`/`=`/`+`/`.`/`->` 结尾）；② 注解行缩进与其所注解的成员一致（注解与成员同行、注解参数续行不计）；③ **续行缩进不得少于**语句起始行 +8（`lineWrappingIndentation`）——**超出不报**（对齐实测口径：续行只报「不足」）；④ `switch` 的 `case`/`default` 标签相对 `switch` 起始行缩进 +4（`caseIndent`，严格：多/少都报）；⑤ **数组初始化** `{ ... }` 内元素行相对初始化起始行缩进 +4 **或** +8 **均合规**（`arrayInitIndent` 期望为一组）；**枚举常量参数的折行不在判定范围**（与 Checkstyle 实测口径一致：该工具对枚举常量参数折行不做 `lineWrappingIndentation` 判定，与其缩进量无关）；缩进无 Tab（#34 另查）。**判定分两档**：①「语句起始行缩进非 4 倍数」→ **脚本判定 fail**；② 续行 / 注解对齐 / 数组初始化 → 候选（manual）。**续行取高置信形态**；深层续行（嵌套 lambda / 方法链）的精确相位不做还原——**识别不确定时一律不报**，避免制造噪音 |
| 46 | import 顺序（启发式） | 分组顺序 **第三方 → `javax` → `java`/`jdk`/`sun`**，各组内按包名字典序；`static` import 不参与排序校验（脚本判定，相邻逆序即 ❌；可用 IDE「Optimize Imports」一次性收敛） |
| 47 | 方法长度 | 方法体代码行数 ≤100（Checkstyle `MethodLength` 口径；注释/空行/纯大括号行不计） |
| 48 | 方法参数个数 | 形参个数 ≤7（Checkstyle `ParameterNumber` 口径）；枚举常量（`UPPER_SNAKE`）不算方法 |
| 49 | equals/hashCode 成对 | 手写 `equals` 必须同时手写 `hashCode`（反之亦然）；豁免 record（隐式生成）与 Lombok `@Data`/`@EqualsAndHashCode`/`@Value` |

### 九、书写细项（#50~#57，对齐静态检查口径，两种模式均执行）

| # | 检查项 | 判定标准 |
|---|---|---|
| 50 | catch 形参命名 | catch 形参须为 `e`/`t`/`ex`/`_`，或小写开头且长度 ≥3 的纯字母名（如 `exception`、`ioException`） |
| 51 | 静态变量命名 | 非 `final` 的 `static` 字段须为 lowerCamelCase（常量 `static final` 由 #39 按 UPPER_SNAKE 核对，不重复）；`import static` 不算声明 |
| 52 | 逗号分号后空格 | `,` `;` 之后须有空白（行尾除外）；类型转换 `)` 之后须有空白；`if`/`for`/`while`/`switch`/`catch`/`synchronized`/`try`/`do`/`else`/`finally` 之后须有空白 |
| 53 | 成员之间空行 | 方法/构造器之前须有空行；豁免：类型体首个成员、**上一成员是字段**（含带初始化表达式的字段）。紧邻的 Javadoc / 块注释 / 注解**不构成**豁免 |
| 54 | 一行一声明 | 一条声明语句内不得定义多个变量（`int a = 1, b = 2;`）；同一行写多条独立声明属 #55 |
| 55 | 一行一语句 | 同一行不得出现多条语句（`for` 头部的分号、`do{...}while(...);` 除外） |
| 56 | package/import 不换行 | `package` 与 `import` 语句须写在单行内，不得被换行拆断 |
| 57 | 花括号必写与位置 | `if`/`for`/`while`/`do`/`else` 必须带 `{}`；`{` 须位于行尾且其后换行（数组初始化、lambda 体除外）；`}` 与 `else`/`catch`/`finally` 必须同行（`RightCurly` `option=same`） |

> [!WARNING] #1/#2/#3 方法级核对必须逐个方法核对（防"长代码丢焦点"，但不必通读整篇文件）
> grep/ast-grep 只能列出方法与"哪里有注释/日志"，证明不了"哪个方法缺"，所以**哪个方法缺必须真读那个方法**。**#1（方法 Javadoc）、#2（方法日志）、#3（步骤注释）必须对本轮生成/修改的每个 Java 文件逐个方法核对**——脚本已给出缺口方法的行号，**只读报出缺口的那几个方法**（用 Read 的 `offset/limit` 读其起止行），**不要通读整篇文件**（缺口之外的内容与本项判定无关，通读整篇 = 白烧 token）：
> - **抽取方法（private 辅助方法）是漏注释/漏日志高发区**——Controller 里抽出的校验/转换方法、ServiceImpl 里抽出的组装/查询方法，逐个核对有方法 Javadoc、方法体内 ≥1 条 INFO/WARN/ERROR 日志
> - **#2 防"半覆盖"漏网**：方法开头 1 条 `log.debug`（或 1 条 INFO）但中间 10+ 行查库/循环/组装逻辑无 INFO/WARN/ERROR → ❌（debug 不算日志，方法须关键阶段有 INFO）
> - 对每个缺口方法，从方法第一行读到最后一行（**仅在必要时扩读**，如判断方法名表意需看类/接口声明；长方法自然读得多），重点盯方法后半段与深层嵌套分支；长方法（>20 行）逐段确认编号注释覆盖到最后一步、每段业务逻辑都有日志
> - 禁止只数 grep 命中数判 ✅；未核到的方法按"未核对"处理，打回重核

