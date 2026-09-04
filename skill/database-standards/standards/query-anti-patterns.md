# 查询反模式 (Query Anti-Patterns)

## 适用范围

生成查询代码、审查 DAO/Mapper/Repository 层、优化慢查询时加载。AI 生成代码最常见的 SQL 性能问题集中于此。

## 强制规则

### 1. N+1 查询（最高频，禁止）

循环内逐条查库，或 ORM 懒加载逐条触发。

```java
// 反例：循环内查库 —— N+1
List<Order> orders = orderMapper.selectByUserId(userId);
for (Order order : orders) {
    User user = userMapper.selectById(order.getUserId());  // N 次查询
}

// 正例：批量查询后内存映射
List<Order> orders = orderMapper.selectByUserId(userId);
Set<Long> userIds = orders.stream().map(Order::getUserId).collect(toSet());
Map<Long, User> userMap = userMapper.selectBatchIds(userIds)
        .stream().collect(toMap(User::getId, u -> u));
```

- 自检：循环体内出现 SQL/ORM 查询调用 = 违规
- ORM 懒加载（延迟加载关联对象）在列表场景默认禁止，显式关闭或改批量

### 2. 超大 IN 列表（禁止）

`WHERE id IN (...)` 列表超过 1000 项：

- 包体过大、解析慢、索引效率骤降
- 分批查询（500~1000 一批）后内存合并
- 批量删除/更新同理，分批 + 控制事务大小

```sql
-- 反例：一万个 id 一次 IN
DELETE FROM t_order WHERE id IN (1, 2, 3, ... 10000);

-- 正例：分批 500 一批
DELETE FROM t_order WHERE id IN (1, 2, ... 500);  -- 循环执行，每批提交
```

### 3. JOIN 膨胀 / 笛卡尔积

- 禁止无关联条件的多表 join（产生笛卡尔积）
- join 超过 3-4 张表：中间结果膨胀，改拆查询内存组装或冗余字段
- join 前先过滤：先 WHERE 缩小左表，再 join，而非 join 后过滤

```sql
-- 反例：先 join 后过滤，大表中间结果
SELECT o.*, u.nickname FROM t_order o
JOIN t_user u ON u.id = o.user_id
JOIN t_product p ON p.id = o.product_id
JOIN t_shop s ON s.id = o.shop_id
WHERE o.create_time > '2026-01-01';

-- 正例：主表先过滤，只 join 必要表
SELECT o.id, o.order_no, u.nickname
FROM (SELECT id, order_no, user_id FROM t_order
      WHERE create_time > '2026-01-01' LIMIT 100) o
JOIN t_user u ON u.id = o.user_id;
```

### 4. 聚合查询陷阱

- `GROUP BY` 严格遵守 ONLY_FULL_GROUP_BY：SELECT 列要么在 GROUP BY，要么是聚合函数
- 禁止对非索引列/高基数列 GROUP BY 大表
- `HAVING` 能转 WHERE 就转 WHERE（HAVING 在聚合后过滤，无法走索引）
- 禁止 `SELECT DISTINCT *`（大表全字段去重，内存爆炸）；按需去重列

```sql
-- 反例：HAVING 过滤本可 WHERE 的
SELECT user_id, COUNT(*) FROM t_order
GROUP BY user_id HAVING status = 1;

-- 正例
SELECT user_id, COUNT(*) FROM t_order
WHERE status = 1 GROUP BY user_id;
```

### 5. 连接/遍历模式（禁止）

| 反模式 | 问题 | 替代 |
|---|---|---|
| `ORDER BY RAND()` | 全表排序取随机 | 应用层随机 id 再查 |
| `LIMIT 1` 取最新后还排序大表 | 无索引排序慢 | 索引支撑 ORDER BY |
| 循环内单条 INSERT/UPDATE | N 次往返 + 事务膨胀 | 批量（500~1000/批） |
| 应用层过滤本可 SQL 过滤 | 全表拉到内存 | WHERE 下推 |
| `SELECT *` 取全字段只用一个 | 网络/内存浪费 | 明确列 |

### 6. 隐式类型转换（高频）

- 列是 varchar，条件传数字 / 列是数字，条件传字符串 → 索引失效
- 字符集不一致的 join 列 → 隐式转换 + 索引失效
- 列被函数包裹 `WHERE DATE(create_time)=...` → 改写范围条件

```sql
-- 反例
WHERE DATE(create_time) = '2026-01-01'   -- 函数包裹，索引失效
-- 正例
WHERE create_time >= '2026-01-01' AND create_time < '2026-01-02'
```

### 7. 大事务内查询/远程调用（禁止）

- 事务内禁止远程调用、循环逐条写
- 事务只包必要写操作，查询放事务外（锁持有时间长 → 死锁/阻塞）
- 批量更新：锁顺序保持一致，避免交叉死锁

## 自检清单

- [ ] 无循环内查库（N+1）
- [ ] 无超大 IN（>1000）
- [ ] join ≤ 3-4 表，无笛卡尔积
- [ ] 无 SELECT DISTINCT *
- [ ] GROUP BY 符合 ONLY_FULL_GROUP_BY
- [ ] 无 ORDER BY RAND()
- [ ] 无隐式类型转换/函数包裹索引列
- [ ] 事务内无远程调用、无逐条写
