---
name: database-standards
description: 约束 AI 生成数据库代码质量的规范集（SQL/表设计/索引/分页/查询反模式/数据安全/MyBatis-Plus）。**只要产出/修改 SQL、DDL、索引或数据访问代码就必须加载本 skill——包括不走完整开发流程的零散请求（"写个 SQL"/"建张表"/"这个查询怎么优化"）：任何 SQL/建表/数据访问产物在返回用户前，本 skill 都必须已加载**；生成 SQL、建表 DDL、索引、分页查询、查询优化代码前必须加载；写 Mapper/DAO/Repository 层、MyBatis XML、审查慢查询时加载。触发场景：写 SQL、建表、设计索引、分页查询、N+1 排查、SQL 优化、DELETE/UPDATE 审查、写 MyBatis-Plus Mapper/XML、**没有需求文档/不走流程的直接 SQL 请求**。WHEN NOT（不要因这些场景触发本 skill）：Java 类结构/命名/分层/日志/事务规则 → java-code-standards；Java 代码注释（非 SQL 语句内的注释）→ comment-standards；纯 Java 代码生成（不含 SQL/表/数据访问）→ 只加载 java-code-standards，本 skill 不重复定义。代码生成完成后的 SQL 兜底核对见 check-standards skill（SQL 在 XML / SQL 注释 / DDL 注释 / SQL 注入 / UPDATE-DELETE 带 WHERE 等核对项）。
---

# Database Standards

约束 AI 生成数据库代码（SQL / 表设计 / 索引 / 分页 / 查询 / MyBatis-Plus）的规范集。面向 MySQL，两层结构：

- **通用层**（`standards/`）：SQL/表设计/索引/分页/反模式/数据安全，ORM 无关，适用任何技术栈
- **MyBatis-Plus 层**（`mybatis-plus/`）：Java 生态数据访问（Mapper/Wrapper/XML/分页插件），配合 java-code-standards 使用

## 加载矩阵

| 任务类型 | 必读 | 建议读 |
|---|---|---|
| 写查询 SQL | `standards/sql-standards.md` | `standards/index-standards.md` / `standards/query-anti-patterns.md` |
| 建表 / 表结构 DDL | `standards/table-design-standards.md` | `standards/index-standards.md` |
| 设计索引 | `standards/index-standards.md` | `standards/sql-standards.md` |
| 分页查询 | `standards/pagination-standards.md` | `standards/index-standards.md` |
| 写 DAO / Mapper / Repository | `standards/query-anti-patterns.md` + `standards/sql-standards.md` | `standards/pagination-standards.md` |
| 写 UPDATE / DELETE / DDL 变更 | `standards/data-safety.md`（最高优先） | `standards/table-design-standards.md` |
| 优化慢查询 | `standards/query-anti-patterns.md` + `standards/index-standards.md` | `standards/sql-standards.md` |
| 写 MyBatis-Plus Mapper | `mybatis-plus/mapper-standards.md` | `mybatis-plus/mybatis-xml-standards.md` |
| 写 MyBatis XML | `mybatis-plus/mybatis-xml-standards.md` | `standards/sql-standards.md` / `standards/pagination-standards.md` |
| MyBatis 分页实现 | `mybatis-plus/pagination-example.md` | `standards/pagination-standards.md` |

## 核心规则速查

### 安全（最高优先，写操作必过）
- UPDATE/DELETE 必带 WHERE；大范围写先备份 + SELECT 预验证
- 大表 DDL 用在线变更，进版本管理；时间统一 DATETIME，左闭右开边界

### 查询
- 禁止 SELECT *、禁止 N+1（循环查库）、禁止超大 IN（>1000）
- 禁止函数包裹索引列 / 隐式类型转换（索引失效）
- join ≤ 3-4 表，小表驱动大表，ON 显式关联

### 索引
- 复合索引最左前缀，等值前范围后；索引数 ≤ 5；唯一约束有唯一索引兜底
- 区分度低列不单独建索引；EXPLAIN 验证 type 不为 ALL

### 分页
- 深分页用键集分页（id < lastId）；ORDER BY 加唯一字段兜底；pageSize 有上限

### MyBatis-Plus
- 简单条件用 LambdaWrapper，复杂 SQL 进 XML；**禁止注解 SQL**（`@Select`/`@Insert`/`@Update`/`@Delete`/`<script>`，手写 SQL 一律 XML）；禁止 `${}` 拼接值、禁止 apply()/last() 传用户输入
- 分页用 `Page` + 插件（配 maxLimit），深分页改键集分页
- 逻辑删除 `@TableLogic`；批量 500~1000 一批；禁 Map 返回主结果

## 使用要求

生成任何 SQL/数据库代码前，按「任务类型 → 加载矩阵」读取规范；生成后对照对应规范「自检清单」逐项核对。违反强制规则即返工。写操作类 SQL（UPDATE/DELETE/DDL）必须过 `standards/data-safety.md` 自检。
