# Java Code Standards Skill

约束 AI 生成 Java 代码质量的规范集合。面向 Spring Boot + Spring + MyBatis-Plus 生态。

## 设计目标

- **按需加载**：按类类型/场景拆分为独立 Markdown，AI 只加载当前任务对应规范，节省 token
- **可执行**：每条规则配正反例 + 自检清单，AI 可直接对照
- **原创**：全部内容独立撰写，参考开源规范风格但不复制原文，无版权风险
- **完整**：覆盖命名、注释、异常、日志、格式 → 各类 Java 类 → 数据库/SQL → 性能/并发/缓存 → 模板 → 完整示例

## 目录结构

```
├── 00-common/          # 通用规范（生成任何代码前加载）
│   ├── 01-naming-standards.md      # 命名规范
│   ├── 03-exception-standards.md   # 异常处理规范
│   ├── 04-logging-standards.md     # 日志规范
│   └── 05-code-format-standards.md # 代码格式规范
│   （注释规范已独立 → comment-standards skill）
│
├── 01-java/            # 各类 Java 类规范（按生成目标加载）
│   ├── controller-standards.md     # Controller
│   ├── service-standards.md        # Service 接口
│   ├── service-impl-standards.md   # Service 实现
│   ├── mapper-standards.md         # Mapper 接口结构（数据访问规则见 database-standards）
│   ├── entity-standards.md         # 实体类
│   ├── dto-standards.md            # DTO
│   ├── vo-standards.md             # VO
│   ├── config-standards.md         # 配置类
│   ├── application-config-standards.md  # 配置文件（application.yml：多环境 profile/逐项注释/连接池/Redis 池/MQ）
│   ├── utils-standards.md          # 工具类
│   ├── exception-standards.md      # 自定义异常
│   ├── enum-standards.md           # 枚举类
│   ├── constants-standards.md      # 常量类
│   ├── converter-standards.md      # MapStruct 转换器
│   ├── validator-standards.md      # 自定义校验器
│   ├── security-standards.md       # 认证鉴权与安全防护
│   ├── listener-standards.md       # MQ 消息消费
│   ├── job-standards.md            # 定时任务
│   ├── api-doc-standards.md        # 接口文档（OpenAPI/knife4j）
│   └── distributed-standards.md    # 分布式（锁/幂等/事务）
│
├── 03-performance/     # 性能优化规范
│   ├── performance-standards.md    # 常见性能问题
│   ├── concurrency-standards.md    # 并发编程
│   └── caching-standards.md        # 缓存使用
│
├── 04-templates/       # 代码模板（按需参考）
│   ├── ControllerTemplate.java
│   ├── ServiceTemplate.java
│   ├── ServiceImplTemplate.java
│   ├── MapperTemplate.java
│   ├── EntityTemplate.java
│   ├── DtoTemplate.java
│   ├── VoTemplate.java
│   ├── ConfigTemplate.java
│   └── ExceptionTemplate.java
│
└── 05-examples/        # 完整示例
    └── crud-example.md             # CRUD 完整示例
```

> **数据库相关规范已迁移至 [database-standards](https://github.com/soft6096/database-standards)**：SQL 编写、表设计、索引、分页、查询反模式、数据安全（通用层）+ MyBatis-Plus Mapper/XML/分页示例（MyBatis-Plus 层）。本 skill 专注 Java 代码规范。

## 使用方式（AI 加载矩阵）

| 任务类型 | 必加载 | 建议加载 |
|---|---|---|
| 任意 Java 代码 | 00-common/* + comment-standards | - |
| 写 Controller | 00-common/* + controller-standards | validator / vo / dto |
| 写 Service/Impl | 00-common/* + service-* | exception / enum |
| 写 Mapper 接口 | 00-common/* + mapper-standards | database-standards mybatis-plus/mapper |
| 写 Entity | 00-common/* + entity | database-standards table-design |
| 认证鉴权/安全 | security-standards | - |
| 写 Listener/Job | listener-standards / job-standards | - |
| 接口文档 | api-doc-standards | - |
| 分布式场景 | distributed-standards | concurrency / caching |
| 写测试代码 | test-standards（全部） | - |
| 写 SQL/表结构/XML/分页 | database-standards（全部） | - |
| 性能敏感代码 | 00-common/* + performance | concurrency / caching |
| 生成完整类 | 00-common/* + 对应类规范 + 对应模板 | 对应示例 |

## 规范文件统一结构

每份规范文件按以下结构组织：

1. **适用范围** — 何时加载此规范
2. **强制规则** — 必须遵守，违反即返工
3. **反例 / 正例** — 对照示例
4. **最佳实践** — 推荐做法
5. **性能优化建议** — 性能相关条目
6. **自检清单** — 生成后逐项核对

## 版权声明

本项目内容为**原创撰写**。所有规则文本与代码示例均独立编写，详细合规说明见 [COPYRIGHT.md](COPYRIGHT.md)。

### 原创性声明

- ✅ 全部规则文本为原创表达，基于 Java 社区**通用工程惯例**撰写（命名、异常、日志、格式等共识性实践，不构成任何单一作品的独特表达）
- ✅ 全部代码示例为原创编写，仅使用公开 API 的功能性调用（Spring / MyBatis-Plus / JDK 标准 API），不包含任何开源项目的整段代码
- ✅ 未复制、未翻译、未改写任何受版权保护的书籍、手册或文档原文
- ✅ 未引用《阿里巴巴 Java 开发手册》纸质书/PDF 及任何第三方整理版本
- ❌ 无「复制自/摘自/来源：xxx」的引用内容（自查确认）

### 参考源处理

仅**借鉴规则思想**（哪些规则存在、业界怎么约束），未复制其文本与代码：

| 参考源 | 许可 | 处理方式 |
|---|---|---|
| alibaba/p3c | Apache 2.0 | 借鉴规则思想，未复制代码/原文 |
| google/styleguide | CC-BY 3.0 | 借鉴风格共识，未复制文本 |
| spring-projects/spring-framework | Apache 2.0 | 借鉴设计思想，未复制代码 |
| baomidou/mybatis-plus | Apache 2.0 | 仅使用其公开 API（功能性使用） |
| mybatis/mybatis-3 | Apache 2.0 | 仅使用其公开 API |
| SonarSource/sonar-java | LGPL 3.0 | 仅参考质量规则思想，未复制代码 |

Apache 2.0 / CC-BY 3.0 / LGPL 均允许参考与再创作；本项目未引入任何 GPL 代码，无传染风险。

### 引入第三方代码时的义务（保持合规）

向本项目贡献代码片段时：

1. 禁止引入未明确开源协议的代码
2. 复制 Apache 2.0 项目代码须保留其版权声明与 NOTICE 文件
3. 复制 GPL/LGPL 代码须评估传染范围，默认禁止
4. 参考某项目实现后重写，仍建议在注释注明思想来源

## License

MIT（覆盖本项目全部原创内容）
