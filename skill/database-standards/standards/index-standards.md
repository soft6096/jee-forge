# 索引规范 (Index Standards)

## 适用范围

设计索引、评审查询 SQL、生成表结构时加载。

## 强制规则

### 1. 索引设计原则

- 为查询而建：索引服务于实际查询模式，不为「可能用到」建
- 索引命名规范：`idx_列名`（普通）、`uk_列名`（唯一）
- 每个表索引数量控制：一般 ≤ 5 个，冗余索引定期清理

```sql
CREATE INDEX idx_order_user_status ON t_order (user_id, status);
CREATE UNIQUE INDEX uk_order_no ON t_order (order_no);
```

### 2. 复合索引

- 复合索引遵循最左前缀：查询条件按索引列顺序（`user_id` 先于 `status`）
- 等值列放前，范围列（>、<、BETWEEN）放后

```sql
-- 索引 (user_id, status, create_time)
-- 可用：
WHERE user_id = 1 AND status = 2 AND create_time > '2026-01-01'
-- 不可用（跳过最左列）：
WHERE status = 2 AND create_time > '2026-01-01'
```

- 高频查询列组设计针对性复合索引，避免单列索引堆叠（MySQL 8 有 index merge，但复合更优）

### 3. 唯一索引

- 业务唯一性用唯一索引兜底（订单号、手机号、防重幂等键），代码校验不可靠（并发窗口）
- 唯一键冲突处理：捕获重复键异常转业务提示，不预查询再插入

### 4. 索引失效场景（禁止）

| 写法 | 问题 |
|---|---|
| `WHERE func(col) = x` | 列被函数包裹 |
| `WHERE col = '123'`（col 为 varchar） | 隐式类型转换 |
| `LIKE '%xx'` | 前导通配符 |
| `OR` 连接非索引列 | 全表扫描 |
| `col IS NOT NULL` 高频 | 视优化器 |
| 排序与索引顺序不一致 | filesort |

### 5. 覆盖索引

- 高频列表查询用覆盖索引（查询列全部在索引内），避免回表

```sql
-- 索引 (user_id, status, create_time) 覆盖以下查询
SELECT id, status, create_time FROM t_order WHERE user_id = 1;
```

### 6. 其他索引类型

- 长文本前缀索引：`INDEX idx_name (name(20))`，cardinality 足够高时
- 联合唯一：`uk_user_sku (user_id, sku_id)` 防重复下单
- 禁止冗余：`idx_a`、`idx_b`、`idx_a_b` 三个索引并存时，`idx_a` 通常冗余

## 反例 / 正例

```sql
-- 反例：状态区分度低单独建索引（价值低）
CREATE INDEX idx_status ON t_order (status);   -- status 只有 5 个值，区分度低

-- 正例：等高区分度 + 查询组合
CREATE INDEX idx_user_status ON t_order (user_id, status);
```

## 最佳实践

- 区分度低的列（状态、性别）不单独建索引，放复合索引靠后位
- 用 `EXPLAIN` 验证：type 至少 range/ref，避免 ALL；关注 rows 估算
- 索引变更评估：写入开销 vs 查询收益，写多读少表慎加索引
- 大表建索引用在线 DDL（`ALGORITHM=INPLACE`），低峰期执行

## 自检清单

- [ ] 索引服务实际查询，无「保险式」堆叠
- [ ] 复合索引符合最左前缀，等值前范围后
- [ ] 无索引失效写法（函数/隐式转换/前导 %）
- [ ] 唯一约束有唯一索引兜底
- [ ] 索引数 ≤ 5，无冗余索引
- [ ] 高频查询考虑覆盖索引
- [ ] EXPLAIN 验证关键查询
