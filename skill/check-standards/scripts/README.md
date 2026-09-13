# check-standards 机械核对工具

用 Python 标准库**机械执行** `SKILL.md` 定义的 33 项 Java 后端代码规范核对，输出结构化报告（Markdown + JSON）。
它**替代人工/模型逐条跑 grep/ast-grep 并整篇读 Java 文件**，但**不替代人的判断**：可机械判定的项给出 `pass/fail`；
语义类项（步骤注释质量、翻译式注释、幂等、防重入、NPE 等）一律标 `manual`/`warn` 并附证据，**绝不假装通过**。

## 环境要求

- Python **3.8+**，仅标准库（无 pip 依赖、无网络调用）。
- `rg`（ripgrep）**不需要**，未使用也能跑；`ast-grep` 完全不依赖。
- 兼容 UTF-8（含中文注释）与 CRLF；解析失败只记录 warning 并继续，绝不中断。

## 快速开始

```bash
# 1) 自检（内置 Java/XML 夹具，验证 33 项判定逻辑）
python3 scripts/check_standards.py --self-test

# 2) 对某项目跑全量核对，输出 Markdown
python3 scripts/check_standards.py --project /path/to/project

# 3) 输出 JSON（机读）
python3 scripts/check_standards.py --project /path/to/project --format json --output report.json

# 4) 只扫本次 git 改动文件
python3 scripts/check_standards.py --changed

# 5) 只扫某目录 / 只跑部分核对项
python3 scripts/check_standards.py --path src/main/java/com/x/order --only 1,2,14,18
```

## 参数

| 参数 | 说明 |
|---|---|
| `--project DIR` | 项目根目录（默认当前目录） |
| `--path PATH` | 代码扫描范围：目录或单个文件（默认自动探测 Maven `src/main/java`） |
| `--changed` | 只扫 git 改动文件（优先 `git status`，回退 `git diff HEAD~1`；无 git 时降级为空范围，不报错） |
| `--mode {auto,standard,legacy}` | 模式（默认 `auto`：读 2.1 约束 / 0.5 扫描决定，缺失则按规范默认 standard 并注明） |
| `--constraints PATH` | 显式指定 2.1 约束文件（覆盖自动探测） |
| `--format {md,json}` | 输出格式（默认 md） |
| `--output FILE` | 写入文件而非 stdout |
| `--only 1,2,3` | 只跑这些核对 id |
| `--skip 27,32` | 跳过这些核对 id |
| `--max-findings N` | 每项证据条数上限（默认 20，超出记 `...(+N more)`） |
| `--fix-renames` | 实际执行第 0 步 docs/ 重命名（默认**只检测不落盘**） |
| `-q, --quiet` | 不输出进度到 stderr |
| `--self-test` | 运行内置夹具自检后退出 |

**退出码**：`0` 无失败；`1` 至少一项 `fail`；`2` 用法/内部错误。

## 核对范围（scope）

- 传 `--path` → 扫该路径，报告 `scope=path`。
- 传 `--changed` → 用 git 取改动的 `.java`，报告 `scope=changed`；命中证据标注 `[本次改动]` / `[存量]`。
- 都不传 → 全项目（自动探测 Maven 多模块 `src/main/java`），报告 `scope=project`。
- 报告头会写明最终范围。

## 模式（standard / legacy）

选型敏感项 **#6 接口文档 / #7 日志框架 / #8 SQL 在 XML / #20 统一返回体** 按模式判定：

- 找到 `docs/**/2.1-项目约束*.md` → standard；找到 `0.5-存量代码扫描.md` 或 `2.1-项目约束-存量适配.md` → legacy。
- 都没有 → 回退 standard，并在报告 `模式说明` 注明「按规范默认值判定（未找到 2.1 约束）」。
- 判定不了选型的（如无依赖、无注解、无约束文件）→ 记 `manual`，**不猜**。

## 33 项核对（id → 规则）

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

## 第 0 步：产物命名矫正（默认只检测）

扫描 `docs/**/*.md`，检测：技术方案漏 `.1`、任务 ID 前缀 `T\d+-`、接口清单/任务拆解/5.2/5.3 报告命名、
路径不在 `docs/<模块名>V<版本>-<时间戳>/` 下。结果进报告的 `renames`。**默认只列出不改**；
加 `--fix-renames` 才会对 docs/ 下 `.md` 执行重命名并打印所做操作（非 docs/ 内容一律不碰）。

## 输出格式

Markdown 头：

```
=== 关键规范核对报告 ===
项目: <path>    时间: <ts>    模式: standard/legacy    核对范围: 全项目 / <dir> / 本轮改动
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
请先运行并读取结果，不要逐条 grep：
  python3 scripts/check_standards.py --project <项目> --format json --output /tmp/cs.json
然后：只读 pending_confirmation 里 fail 的项，按证据定位修复；
manual 项再按需人读判断；修复后重跑同一命令确认 fail 归零。
```

## 跨平台 / Windows 兼容

- 所有读写均显式指定编码（读 `utf-8-sig`/`utf-8`，回退 `gb18030`/`latin-1`；写 UTF-8），不依赖系统 locale。
- 启动时把 stdout/stderr 切到 UTF-8，Windows GBK 控制台不会因中文乱码/编码错误崩溃。
- 路径全部走 `os.path`，并把 `\`/`/` 归一化后比较；兼容 CRLF。未使用 `fcntl`/`os.fork`/信号等 POSIX-only API，无绝对 `/tmp` 依赖（临时文件用 `tempfile`）。
- `--changed` 在无 git 时降级为空范围并给出说明，不抛 traceback。

## 已知局限（诚实清单）

- #1/#2/#3 的方法识别基于轻量括号扫描（非 AST），极少数语法形态（记录类紧凑构造器、注解数组内花括号等）可能识别不全；未识别的方法不计入证据，但也不会误判为 pass。
- #3/#4/#24/#25/#26/#27/#30/#31/#32 为**启发式 + 人工**项，输出候选证据供人判断，**不自动 pass**。
- #6/#7/#8/#20 依赖项目模式的选型；无 2.1/0.5 约束文件时按规范默认并在报告注明。
- `--changed` 的「本次改动/存量」标注需要该目录是 git 仓库。
- 工具**只读**源码；只有显式 `--fix-renames` 才会重命名 `docs/` 下的 `.md`。
