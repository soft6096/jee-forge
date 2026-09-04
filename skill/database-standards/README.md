# database-standards

约束 AI 生成数据库代码质量的规范集。面向 MySQL，两层结构：

- **通用层** `standards/`：ORM 无关，适用任何技术栈（Java/Go/Node/Python）
- **MyBatis-Plus 层** `mybatis-plus/`：Java 生态数据访问（Mapper/Wrapper/XML/分页插件）

## 解决的问题

AI 生成 SQL 常见问题：N+1 查询、SELECT *、索引失效写法、深分页、无 WHERE 的 UPDATE/DELETE、隐式类型转换、超大 IN 列表、时区坑等。本 skill 把这些约束固化为可加载规范，AI 编码前按加载矩阵读取，生成后按自检清单核对。

## 规范文件

| 文件 | 覆盖 |
|---|---|
| [SKILL.md](SKILL.md) | skill 入口 + 加载矩阵 + 规则速查 |
| [standards/sql-standards.md](standards/sql-standards.md) | SQL 编写：WHERE/JOIN/分页/参数化 |
| [standards/table-design-standards.md](standards/table-design-standards.md) | 建表 DDL：命名/类型/必备字段 |
| [standards/index-standards.md](standards/index-standards.md) | 索引：复合索引/失效场景/覆盖索引 |
| [standards/pagination-standards.md](standards/pagination-standards.md) | 分页：深分页/键集分页/排序稳定 |
| [standards/query-anti-patterns.md](standards/query-anti-patterns.md) | 查询反模式：N+1/超大 IN/join 膨胀/聚合 |
| [standards/data-safety.md](standards/data-safety.md) | 数据安全：无 WHERE 写操作/备份/在线 DDL/时区 |
| [mybatis-plus/mapper-standards.md](mybatis-plus/mapper-standards.md) | MyBatis-Plus Mapper：Wrapper/分页/逻辑删除/批量 |
| [mybatis-plus/mybatis-xml-standards.md](mybatis-plus/mybatis-xml-standards.md) | MyBatis XML：resultMap/动态 SQL/foreach |
| [mybatis-plus/pagination-example.md](mybatis-plus/pagination-example.md) | MyBatis 分页完整示例（插件 + 键集分页） |

## 与 java-code-standards 的关系

- **database-standards** = 数据库规范（本仓库，含 MyBatis-Plus 层）
- **java-code-standards** = Java 代码规范（[GitHub](https://github.com/soft6096/java-code-standards)，Controller/Service/Entity 等 Java 类规范）
- 写 MyBatis Mapper 接口：接口结构看 java-code-standards `01-java/mapper-standards.md`，数据访问规则看本仓库 `mybatis-plus/mapper-standards.md`

## 安装

### Claude Code / opencode 等 agent（从 GitHub 安装）

```bash
# 方式一：git clone 到 skills 目录
git clone git@github.com:soft6096/database-standards.git ~/.claude/skills/database-standards

# 或 opencode 用户目录
git clone git@github.com:soft6096/database-standards.git ~/.agents/skills/database-standards
```

### 手动

下载仓库，把 `database-standards` 目录放入你的 agent skills 目录（Claude Code：`~/.claude/skills/`；opencode：`~/.agents/skills/` 或 `~/.config/opencode/skills/`）。

## 使用

触发场景自动加载：写 SQL、建表、设计索引、分页查询、N+1 排查、慢查询优化、DELETE/UPDATE 审查。也可以显式要求：`用 database-standards 规范检查这段 SQL`。

## 维护

- 规范文件按「强制规则 → 反例/正例 → 自检清单」结构编写，新增规则保持此结构
- 写操作类规则进 `data-safety.md`（最高优先级）
- 改规范后更新 SKILL.md 加载矩阵与速查

## 许可

MIT
