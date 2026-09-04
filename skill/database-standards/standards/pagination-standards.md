# 分页查询规范 (Pagination Standards)

## 适用范围

实现列表分页查询时加载。定义分页方式选择、实现与深分页处理。ORM/数据库无关，适用任何技术栈。

## 强制规则

### 1. 分页方式选择

| 数据量 | 推荐方式 |
|---|---|
| < 100 万 | 常规分页（LIMIT offset, size，带索引条件） |
| 100 万 ~ 1000 万 | 常规分页 + 索引条件约束 |
| > 1000 万 / 深分页 | 游标/键集分页 |

- 统一走分页插件/封装，禁止散落手写 `LIMIT offset, size` 且无上限

### 2. 分页参数

- `pageNum` 从 1 开始，`pageSize` 上限校验（默认 10，最大 100）
- 非法页码防御：pageNum ≤ 0 归一为 1，pageSize > 上限钳制
- 分页参数统一封装成基类（PageQuery），前端传参规范化

### 3. 深分页处理（offset 大）

`LIMIT 100000, 20` 慢因：数据库先扫 100020 行再丢前 100000。方案：

**键集分页（推荐）**：记住上一页最后一条的排序键

```sql
-- 按 id 降序翻页：每次带上 lastId
-- 第一页 lastId = null → 不加条件
SELECT id, order_no, amount, status
FROM t_order
WHERE id < #{lastId}
  AND user_id = #{userId}        -- 业务条件照常
ORDER BY id DESC
LIMIT #{size}
```

- 键集分页前提：排序键唯一稳定（id 天然满足）；多列排序时建对应复合索引
- 前端体验差异：无页码跳转，用「加载更多 / 上一页下一页游标」

### 4. 排序稳定性

- `ORDER BY` 加唯一字段（id）兜底，避免同排序值导致翻页重复/遗漏

```sql
-- 反例：create_time 相同的大量行，翻页错乱
ORDER BY create_time DESC
-- 正例
ORDER BY create_time DESC, id DESC
```

- 排序字段走索引：ORDER BY 列顺序与索引一致，避免 filesort
- 动态排序字段必须白名单校验，禁止直接拼接

### 5. count 查询优化

- 常规分页自动 count；条件复杂（join + 多条件）时 count 昂贵
- 无需总数场景（加载更多）用键集分页，天然免 count
- count 结果缓存：列表条件不变时缓存总数（可选）

## 反例 / 正例

```sql
-- 反例：手写 offset 深分页 + 无上限
SELECT * FROM t_order
ORDER BY create_time DESC
LIMIT 100000, 20;

-- 正例：游标
SELECT id, order_no, amount, status
FROM t_order
WHERE id < #{lastId}
ORDER BY id DESC
LIMIT #{size};
```

## 自检清单

- [ ] 分页封装统一，无散落手写 offset
- [ ] pageSize 有上限校验
- [ ] 深分页用键集分页
- [ ] ORDER BY 含唯一字段
- [ ] 排序字段走索引
- [ ] 游标条件绑定参数，无拼接
- [ ] 动态排序白名单校验
