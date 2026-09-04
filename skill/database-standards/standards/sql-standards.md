# SQL 编写规范 (SQL Standards)

## 适用范围

编写 SQL、审查 Mapper 内 SQL、生成查询代码时加载。面向 MySQL，其他数据库参照调整。

## 强制规则

### 1. 基本要求

- 关键字大写：`SELECT` / `FROM` / `WHERE` / `JOIN`，表名列名小写下划线
- 每个 SQL 明确写出列，禁止 `SELECT *`（ORM 动态查询场景除外，其已自动裁剪）
- 表名与列名显式 `t_alias.column` 限定，多表 join 必带别名

```sql
-- 用途：按用户+状态查订单列表（列表页）；归属：OrderMapper.selectOrderList
-- 参数：userId 用户ID、status 订单状态；条件：join 用户表取昵称
SELECT o.id, o.order_no, o.amount, u.nickname
FROM t_order o
JOIN t_user u ON u.id = o.user_id
WHERE o.user_id = #{userId}
  AND o.status = #{status}
ORDER BY o.create_time DESC
LIMIT #{limit}
```

### 1.5 SQL 注释（强制，一条不漏）

- **所有 SQL 语句必须带注释**：建表 DDL、DML、查询 SQL 全覆盖，禁止无注释裸 SQL
- **建表 DDL**：每个字段 `COMMENT '...'`（含义 + 枚举取值/单位/时区约定）+ 表级 `COMMENT='...'`（见 table-design-standards）
- **查询/DML SQL**：语句上方 `--` 注释，必含 ① 用途 ② 归属 Mapper 函数（如 `OrderMapper.selectTimeoutOrders`）③ 关键条件/参数说明；多行语句每段条件可再行内注释

```sql
-- 用途：筛选超时未支付订单（Job 超时关闭）；归属：OrderMapper.selectTimeoutOrders
-- 参数：minutes 超时分钟、limit 批处理上限；条件：PENDING + 超时 + 未删除
SELECT order_id FROM sys_order
WHERE status = 'PENDING'
  AND create_time < DATE_SUB(NOW(), INTERVAL #{minutes} MINUTE)
  AND del_flag = '0'
ORDER BY create_time ASC
LIMIT #{limit}

-- 用途：初始化订单状态字典（幂等：同 dict_type 跳过）
INSERT INTO sys_dict_type (dict_name, dict_type, status) VALUES ('订单状态', 'order_status', '0');
```

- SQL 注释与代码注释同源（见 comment-standards）：注释写业务含义，禁止只翻译 SQL 关键字；技术方案中的 SQL 同样适用（见 ai-dev-workflow 3.0 模板"SQL 全量注释"）

### 2. WHERE 条件规范

- 等值条件在前，范围条件在后
- 复合索引条件：按索引列顺序书写（最左前缀），字段类型与列一致
- 禁用条件隐式转换：`WHERE mobile = 123`（mobile 是 varchar）——索引失效

```sql
-- 反例：函数/隐式转换导致索引失效
WHERE DATE(create_time) = '2026-01-01'
WHERE phone = 13800001234
WHERE name LIKE '%张'

-- 正例
WHERE create_time >= '2026-01-01' AND create_time < '2026-01-02'
WHERE phone = '13800001234'
WHERE name LIKE '张%'
```

- 前导模糊 `LIKE '%xx'` 无法走索引，高频场景换全文检索/前缀索引
- `NOT IN` / `OR` 慎用，可走索引时用 `NOT EXISTS` / `UNION` 等价改写（EXPLAIN 验证）

### 3. JOIN 规范

- 小表驱动大表：JOIN 顺序从数据量小到大
- 关联字段两边都有索引（关联列类型一致，否则隐式转换 + 索引失效）
- 避免多表 join 超过 3-4 张；超过时拆查询内存组装或冗余字段
- JOIN 条件显式 ON，禁止 WHERE 隐式连接（可读性 + 误删风险）

### 4. 分页与排序

- 深分页禁止 `LIMIT 100000, 20`——改游标/键集分页（见分页规范）
- 排序字段尽量走索引（ORDER BY 与索引列顺序一致）
- 排序加唯一字段（id）兜底，避免相同排序值分页重复/漏数据

### 5. 事务与锁

- 写 SQL 明确影响行数：`UPDATE` 必带 WHERE，无 WHERE 的 UPDATE/DELETE 需显式审查
- 行锁：`SELECT ... FOR UPDATE` 只在事务内且需要锁时使用，锁条件必走索引
- 批量更新逐条或批量，禁止循环内单条提交大事务

### 6. 参数化

- 所有值用预编译占位（`#{}` / `?` / 命名参数），禁止字符串拼接（SQL 注入）
- 动态表名/排序字段仅限白名单场景，且必须白名单校验

## 反例 / 正例

```sql
-- 反例
SELECT * FROM t_order WHERE user_id = 1 AND status LIKE '%1%' ORDER BY RAND();

-- 正例
SELECT id, order_no, amount, status
FROM t_order
WHERE user_id = #{userId}
  AND status = #{status}
ORDER BY id DESC
LIMIT #{pageSize}
```

## 最佳实践

- 每个慢 SQL 用 EXPLAIN 验证走索引（type 不为 ALL，rows 可控）
- 大表修改（加列/加索引）用在线 DDL 工具，避免锁表
- 数据量 > 1000 万表：拆分查询粒度，避免全表扫描兜底逻辑
- 不查不用的列：列表页 join 只取展示列

## 性能优化建议

| 场景 | 问题 | 建议 |
|---|---|---|
| `WHERE func(col) = x` | 索引失效 | 改写范围条件 |
| `LIKE '%x%'` | 索引失效 | 前缀匹配/全文检索 |
| `LIMIT 100000,20` | 深度翻页慢 | 键集分页 |
| 3+ 表 join 大表 | 中间结果膨胀 | 拆查询 |
| `OR` 跨列 | 索引失效 | UNION 或拆条件 |

## 自检清单

- [ ] 无 SELECT *
- [ ] 无索引失效写法（函数、隐式转换、前导 %）
- [ ] 值全部参数化，无拼接
- [ ] JOIN 有索引 + 类型一致
- [ ] UPDATE/DELETE 有 WHERE
- [ ] EXPLAIN 验证关键查询
- [ ] 无深分页
- [ ] 所有 SQL 带注释（查询/DML 每条 `--` 用途+归属+条件；DDL 每列 COMMENT）
