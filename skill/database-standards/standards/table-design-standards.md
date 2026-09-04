# 表设计规范 (Table Design Standards)

## 适用范围

设计表结构、生成建表 DDL、评审字段时加载。

## 强制规则

### 1. 表命名

- 表名小写 + 下划线，业务前缀统一（如 `t_order`、`t_user`）
- **前缀风格与项目现有表保持一致**：RuoYi 系项目常用 `sys_` 系统表前缀（`sys_user`、`sys_dict_type`），业务表可无前缀；新增表必须沿用项目已有前缀风格，禁止同库混用多套前缀
- 复数/单数团队统一（推荐单数：`t_order` 非 `t_orders`）
- 关联表命名：`t_user_role`（两实体名拼接）

### 2. 必备字段

每张表必备四件套：

```sql
CREATE TABLE `t_order` (
    `id`           BIGINT       NOT NULL COMMENT '主键ID（雪花）',
    `create_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`      TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0-未删 1-已删',
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '订单表';
```

- 主键 BIGINT（雪花分配），不用 INT 自增（容量 + 分库分表兼容）
- `deleted` 与 ORM 逻辑删除注解配合，业务查询自动过滤
- 时间统一 DATETIME，存业务本地时区，注释标注时区约定

### 3. 字段类型规范

| 数据类型 | 使用场景 | 注意 |
|---|---|---|
| BIGINT | 主键、ID、时间戳(可选) | 不用 INT 存 ID |
| VARCHAR(n) | 短文本 | 按实际长度定，不滥用 255 |
| TEXT | 长文本 | 独立字段，不进索引 |
| DECIMAL(p,s) | 金额、精确小数 | 禁止 FLOAT/DOUBLE 存金额 |
| INT/TINYINT | 状态、数量、枚举值 | 状态列注释枚举含义 |
| DATETIME | 时间 | 不用 TIMESTAMP（2038 问题 + 时区坑） |
| JSON | 结构化扩展字段 | 仅查询频率低的场景 |

- 金额统一 `DECIMAL(10,2)` 或更大精度，注释单位（元/分）
- 状态字段用 TINYINT/INT 存编码，注释每个值含义，不存中文

### 3.5 建库/建表字符集：显式 utf8mb4

建库建表**必须显式声明字符集与排序规则**，禁止依赖服务器默认（默认可能不是 utf8mb4）：

```sql
CREATE DATABASE `app` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

CREATE TABLE `t_order` (
    ...
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '订单表';
```

- MySQL 8 服务器默认字符集即 utf8mb4，但显式声明防止部署环境差异（老实例默认 latin1/utf8mb3 时中文/emoji 乱码）
- 排序规则统一 `utf8mb4_general_ci` 或 `utf8mb4_0900_ai_ci`（MySQL 8 默认），全库一致，避免 JOIN 排序规则冲突
- 连接侧字符集（JDBC URL）见 java-code-standards `application-config-standards.md`：**不要在 URL 写 `characterEncoding=utf8mb4`**（Connector/J 8.x 报 Unsupported character encoding）

### 3.6 表结构与代码一致性（schema 与 Entity 强一致）

- **Entity 与 DDL 一一对应**：字段增减必须同时改 Entity + schema/迁移脚本，禁止只改一边——只改 Entity 报 `Unknown column 'xxx'`，只改 DDL 报实体字段不存在
- **一张表只允许一个 Entity 映射**（同表唯一映射）：新建 Entity 前先 `grep '@TableName("表名")'` 全项目查重——同表已有 Entity 则复用/扩展，**禁止再造第二个映射同表的 Entity**（后台/前台/各模块各建一个都是重复映射，双维护必漂移，见 java-code-standards `01-java/entity-standards.md` §1）
- **初始化/重建库必须用当前 schema 全量重建**，禁止沿用旧库旧表：库里遗留旧版表（如旧列 `nickname` 新代码用 `real_name`）时，删除旧库按当前 schema.sql 重建，而不是手工补列
- schema.sql（或迁移脚本全集）与代码同仓维护、随版本演进；存量库表结构与代码不匹配时，先对齐 schema 再谈运行
- 表结构变更走迁移脚本（ALTER 追加），禁止直接改线上库；schema 文件与迁移脚本双轨并存时，以脚本全集为准

### 4. 字段约束

- 所有字段 `NOT NULL` + 默认值；必须可空时显式 DEFAULT NULL 并注释原因
- 字符集 utf8mb4（emoji 支持）；排序规则统一
- 枚举用 CHECK 约束或注释约束（MySQL 8 支持 CHECK），代码枚举同步维护

### 5. 扩展字段规范

- 预留扩展字段禁止 `col1/col2/remark1/remark2`——用 JSON 扩展列或明确命名
- 大字段（TEXT/BLOB）独立表或延迟加载，不混入高频查询主表

### 6. 反范式规范

- 读多写少可冗余展示字段（如订单表冗余商品名），冗余列注释来源（`冗余自 t_product.name`）
- 冗余一致性由写侧维护：更新源表时同步冗余列（事务内）

## 反例 / 正例

```sql
-- 反例
CREATE TABLE `order` (
    id INT AUTO_INCREMENT PRIMARY KEY,          -- 自增 + 未加 t_ 前缀 + 无注释
    money FLOAT,                                -- 金额 float 精度损失
    status VARCHAR(20),                         -- 存中文状态
    create_date DATE,                           -- 精度不够
    col1 VARCHAR(255), col2 VARCHAR(255)        -- 无意义扩展字段
);
```

## 最佳实践

- 每表字段带 COMMENT，建表 DDL 进版本管理（Flyway/Liquibase 或 SQL 脚本目录）
- 表结构变更走迁移脚本，不手工改线上库
- 大表（千万级）加列/索引评估锁表影响，用在线变更
- 归档策略：历史数据按月/年归档表，主表保持体积可控

## 自检清单

- [ ] 表名小写带前缀 + 注释
- [ ] 四件套（id/create_time/update_time/deleted）齐全
- [ ] 主键 BIGINT 非自增
- [ ] 金额 DECIMAL，无 FLOAT/DOUBLE
- [ ] 时间 DATETIME
- [ ] 全字段 NOT NULL + 默认值
- [ ] 建库建表显式 utf8mb4 + 排序规则（不依赖服务器默认）
- [ ] 全字段 COMMENT
- [ ] 无 col1/col2 无意义字段
- [ ] DDL 进版本管理
- [ ] Entity 与 DDL 一一对应（字段增减双同步）
- [ ] 初始化/重建库按当前 schema 全量重建，无旧库旧表遗留
