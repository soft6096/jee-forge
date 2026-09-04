---
name: java-code-standards
description: Java 代码生成规范引擎，约束 AI 生成代码质量（Spring Boot + Spring + MyBatis-Plus 生态）。**只要产出/修改 Java 代码就必须加载本 skill——包括不走完整开发流程的零散请求（"写个 XX 接口"/"写个 Controller"/"帮我写这段代码"/"实现这个功能"）：任何 Java 代码产物在返回用户前，本 skill 与 comment-standards 都必须已加载**——命名/分层/异常/日志/事务/注入/SQL/安全是硬性要求，生成物不符合即返工。写 Controller/Service/ServiceImpl/Mapper/Entity/DTO/VO/Config/Utils/Exception/Enum/Constants/Converter/Validator/Security/Listener/Job 等类时按生成目标加载 01-java 对应规范；代码注释规则见 comment-standards skill（**未加注释 = 代码未完成，不得交付**）；涉及 SQL/表设计/索引/MyBatis XML/分页时加载 database-standards skill（通用 SQL + MyBatis-Plus 层）；写测试代码时加载 test-standards skill；构建配置（pom/依赖/模块）时加载 build-standards skill；性能敏感/并发/缓存代码加载 03-performance 规范；生成完整类时参考 04-templates 模板。触发场景：生成 Java 代码、写 Java 类、Spring Boot 接口、MyBatis-Plus Mapper、SQL/建表 DDL、分页查询、认证鉴权、定时任务、消息消费、代码规范审查、**没有需求文档/不走流程的直接写码请求**。WHEN NOT（不要因这些场景触发本 skill）：纯 SQL/DDL/索引任务 → 只加载 database-standards；纯注释补全/审查 → 只加载 comment-standards；纯测试代码 → 只加载 test-standards；纯 pom/依赖/构建配置 → 只加载 build-standards——本 skill 不重复定义这些领域，避免多 skill 规则叠加冲突挤占编码上下文。代码生成完成后的兜底核对见 check-standards skill（全部核对项，含方法级注释/日志全覆盖）。
---

# Java Code Standards

约束 AI 生成 Java 代码质量的规范集。面向 Spring Boot + Spring + MyBatis-Plus 生态，按类类型/场景拆分为独立规范，按需加载。

## 强制使用流程

生成任何 Java 代码前，必须按「任务类型 → 加载矩阵」读取规范，生成后对照「自检清单」逐项核对。违反强制规则即返工。

## 按需加载原则（硬规则：防止规范挤占编码上下文）

- **精确到单文件加载**：按矩阵只读当前任务对应的规范文件（写 Controller 只读 `controller-standards.md` + `api-doc-standards.md`），**禁止把整个 `01-java/`、`04-templates/` 目录读一遍**
- `00-common/*`（4 份）是唯一全量必读组；建议加载顺序：先 01-java 对应类规范（明确写什么），再 00-common（约束怎么写）
- `04-templates/`：只读与当前生成类对应的**那一个**模板文件（如写 Service 实现只读 `ServiceImplTemplate.java`）——模板是骨架参考，不是必读全文
- `05-examples/`（完整 CRUD 示例 321 行）：**仅首次搭建同类功能或不确定代码组织方式时读**，常规开发不加载
- 一次编码会话叠加的规范总量应控制在 ~1500 行内；超出时优先保 `00-common` + 当前类规范，其余按矩阵延后

## 加载矩阵

| 任务类型 | 必读 | 建议读 |
|---|---|---|
| 任意 Java 代码 | `00-common/*`（4 份）+ comment-standards `standards/comment-standards.md` | - |
| 写 Controller | `00-common/*` + `01-java/controller-standards.md` + `01-java/api-doc-standards.md`（OpenAPI 注解强制） | validator / vo / dto |
| 写 Service 接口 | `00-common/*` + `01-java/service-standards.md` | exception / enum |
| 写 Service 实现 | `00-common/*` + `01-java/service-impl-standards.md` | exception / enum |
| 写 Mapper | `00-common/*` + `01-java/mapper-standards.md`（接口结构） | database-standards `mybatis-plus/mapper-standards.md` |
| 写 Entity | `00-common/*` + `01-java/entity-standards.md` | database-standards `table-design-standards.md` |
| 写 DTO / VO | `00-common/*` + 对应类规范 + `01-java/api-doc-standards.md`（字段 @Schema 强制） | converter |
| 写 Config / Utils / Enum / Constants 等 | `00-common/*` + 对应类规范 | - |
| 写 application.yml / 配置文件 / 连接池 | `01-java/application-config-standards.md` | config-standards |
| 生成项目脚手架 / 工程初始化（配置 + 公共组件） | build-standards + `01-java/application-config-standards.md` + `04-templates/`（ConfigTemplate / MyMetaObjectHandler） | database-standards `table-design-standards.md` |
| 认证鉴权 / 安全 | `01-java/security-standards.md` | controller-standards |
| 写 Listener（MQ 消费） | `01-java/listener-standards.md` | database-standards `pagination-standards.md` |
| 写 Job（定时任务） | `01-java/job-standards.md` | concurrency |
| 接口文档（OpenAPI/knife4j） | `01-java/api-doc-standards.md` | controller-standards |
| 分布式（锁/幂等/事务） | `01-java/distributed-standards.md` | concurrency / caching |
| 写 pom / 加依赖 / 模块结构 | build-standards（全部） | - |
| 写测试代码 | test-standards `unit-test-standards.md` + `contract-test-standards.md` | test-standards `test-data-standards.md` |
| 写 SQL / 建表 DDL | database-standards `sql-standards.md` + `table-design-standards.md` + `index-standards.md` | database-standards `pagination-standards.md` |
| 写 MyBatis XML | database-standards `mybatis-plus/mybatis-xml-standards.md` | database-standards `sql-standards.md` / `pagination-standards.md` |
| 分页查询 | database-standards `pagination-standards.md` + `mybatis-plus/pagination-example.md` | database-standards `index-standards.md` |
| 性能敏感代码 | `00-common/*` + `03-performance/performance-standards.md` | concurrency / caching |
| 并发 / 锁 | `03-performance/concurrency-standards.md` | - |
| 缓存 (Redis/Caffeine) | `03-performance/caching-standards.md` | - |
| 生成完整类 | `00-common/*` + 01-java 对应规范 | `04-templates/` 对应**单个**模板文件（如 ServiceImplTemplate.java）、`05-examples/`（仅首次/不确定时） |

## 核心规范速查

### 命名（01-naming-standards.md）
- 类 UpperCamelCase，接口无 `I` 前缀，实现类 `Impl` 后缀；**禁止单字母类名**（`R` 统一返回体类名反例）
- 统一返回体固定为 `Response<T>`（code/message/data），放 `common.web`；分页用 `PageResult<T>`；禁止 `R` / `Result` / `ApiResponse`
- **包结构：每种职责独立分包，同类不混放**——`controller` / `service` / `service.impl` / `mapper` / `domain`（实体）/ `dto`（入参）/ `vo`（出参）各归其包；DTO 与 VO 必须分属 `dto`、`vo` 两个独立包，严禁 VO 放 dto 包或 DTO 放 vo 包
- 方法 lowerCamelCase 动词开头，分层前缀：Controller `get/create/update/delete`、Service `query/save/modify/remove`、Mapper `select/insert/update/delete`
- 变量名 = `[来源/角色限定] + [领域词] + [类型后缀]`，2~3 个词表达业务语义：`LoginVO loginResult`、`SysUser existingUser`、`String accessToken`、`OrderQueryDTO orderQuery`
- 变量命名反模式（命中即改）：单字母（`e`/`p`）、泛称简写（`vo`/`dto`/`data`/`obj`）、类型机械小驼峰（`User user`/`Token token`）、单单词泛指（`user`/`token`/`list`/`map`）、序号命名（`user1`/`data2`）、拼音
- 同类型多变量用语义限定词区分：`cachedOrderVO`/`dbOrderVO`、`sourceOrderVO`/`targetOrderVO`、`accessToken`/`refreshToken`
- 异常处理参数禁单字母 `e`：`@ExceptionHandler(ServiceException.class)` 用 `ServiceException serviceException`；`catch (Exception exception)`
- 分页对象 `IPage<T> pageResult` / `Page<T> pageResult` 语义命名（非裸 `page`）；集合字段 `recordList`（非 `records`），统一 `xxxList`/`xxxSet`/`xxxMap`
- 常量全大写 + 下划线

### 异常（03-exception-standards.md）
- 业务异常抛 `BusinessException(ErrorCode, message)`，错误码集中定义，禁止裸 `RuntimeException`
- 禁止空 catch、吞异常；资源用 try-with-resources
- Controller 不写 try/catch，全局处理器统一转换

### 日志（04-logging-standards.md）
- SLF4J 占位符 `{}`，禁止字符串拼接与 System.out；全类 `@Slf4j`（Controller/Service/Job/Listener 一律带）
- 异常日志带堆栈（最后参数传异常对象）
- 关键日志带业务上下文 ID，禁敏感信息
- **Logback 配置**：项目必须提供 `logback-spring.xml`（控制台 + 滚动文件 + 环境级 level 分离），禁止依赖默认配置裸奔（见 04-templates/logback-spring.xml）

### 注释（见 comment-standards skill）
- 全量注释：所有类（DTO/VO/Config 等，仅示例非穷举）类注释写清职责、所有变量/字段注释写清含义
- 所有方法（含测试方法）注释：功能 + @param/@return 业务含义（禁止只重复参数名）
- 方法体 ≥2 个逻辑步骤编号步骤注释（`// 1. 参数提取…`）；复杂逻辑写 `// WHY:`
- 禁止逐行翻译式注释，注释与代码一致

### Service 实现（service-impl-standards.md）
- 构造器注入（`@RequiredArgsConstructor` + final 字段），禁止字段注入
- `@Transactional(rollbackFor = Exception.class)`，事务内禁止远程调用
- 并发写用乐观锁（`@Version`）或行锁，禁止无锁覆盖

### 数据访问
- SQL/表设计/索引/分页/MyBatis XML 规范见 **database-standards** skill，本 skill 只覆盖 Java 侧（Mapper 接口结构）
- Mapper 接口：继承 `BaseMapper`，方法命名 select/insert/update/delete 前缀，多参数 `@Param`，禁 Map 返回
- **自定义 SQL 一律放 XML**（`resources/mapper/XxxMapper.xml`），**禁止注解 SQL**（`@Select`/`@Insert`/`@Update`/`@Delete`/`<script>`）；接口方法无实现且无 XML/BaseMapper 覆盖 = 运行期炸
- 批量操作 foreach 500~1000 一批，禁止循环单条
- **自动填充**：实体 `@TableField(fill=...)` 必须配套项目级 `MetaObjectHandler`（见 04-templates/MyMetaObjectHandler.java），缺失插入报 `Column 'create_time' cannot be null`

### 工程配置（application-config-standards.md 摘要）
- 多环境四件套：`application.yml` + `-dev` / `-qa` / `-online`，禁止单文件裸奔；profile 激活 `${SPRING_PROFILES_ACTIVE:dev}` 不写死
- HikariCP 显式池参数，禁止 datasource 三件套（url/username/password）裸奔
- JDBC URL：端口与环境实际一致（禁默认 3306 想当然）；**禁写 `characterEncoding=utf8mb4`**（Connector/J 8.x 报 Unsupported character encoding），不写或写 `characterEncoding=UTF-8`

### 安全（security-standards.md）
- 接口权限注解 + 资源归属校验（防 IDOR）；SQL 全参数化
- 密码慢哈希、密钥无硬编码；文件上传白名单 + 大小 + 重命名
- 敏感字段脱敏，不进日志/响应

### 分布式（distributed-standards.md）
- 分布式锁 SETNX + 过期 + 原子释放；写接口幂等（唯一键/状态位）
- 跨服务调用有超时 + 重试退避 + 熔断；分布式事务多数用最终一致

### 测试（见 test-standards skill）
- 测试是验收标准：禁改断言/删测试；契约测试覆盖三态（合法/非法/边界）
- 单测 AAA + 全 mock；数据工厂化；复杂 SQL 用 Testcontainers

### 性能（03-performance/*）
- 禁止 N+1：批量查询后内存映射
- 线程池用 ThreadPoolExecutor 显式参数 + 命名线程工厂，禁止 Executors 快捷方法
- 缓存 Cache-Aside：写库后删缓存；防穿透（空值缓存）、击穿（互斥锁）、雪崩（TTL 抖动）

## 版权

本 skill 内容全部原创，无版权风险。规范详情见 COPYRIGHT.md。

## 自检要求

生成代码后逐项核对对应规范的「自检清单」：命名、异常、日志、事务、SQL、性能是否全部达标。违反强制规则必须修正后再交付。
