# 数据安全规范 (Data Safety)

## 适用范围

生成写 SQL（INSERT/UPDATE/DELETE）、DDL 变更、处理时间/编码时加载。AI 生成破坏性 SQL 是最高风险场景，本规范优先于一切性能考虑。

## 强制规则

### 1. UPDATE / DELETE 必须带 WHERE（最高优先级）

- 无 WHERE 的 UPDATE/DELETE = 全表变更，禁止直接生成
- AI 生成的写 SQL 必须人工复核 WHERE 条件与预期范围一致
- 习惯性生成 `WHERE 1=1` 或空条件 = 全表更新，禁止

```sql
-- 禁止生成（除非显式要求清表）
DELETE FROM t_order;
UPDATE t_order SET status = 2;

-- 必须带条件
DELETE FROM t_order WHERE order_no = #{orderNo};
UPDATE t_order SET status = 2
WHERE id = #{id} AND status = 1;   -- 条件带上原状态，防并发覆盖
```

### 2. 破坏性操作保护

- 大范围 DELETE/UPDATE 前置：备份受影响数据（`CREATE TABLE t_x_bak_20260101 AS SELECT * FROM t_x WHERE ...`）
- 先 SELECT 验证影响行数，再执行变更
- 软删除优先：能逻辑删除不物理删除（deleted 标记）
- 清表/TRUNCATE 只在显式确认后生成

### 3. DDL 变更安全（在线变更）

- 大表（千万级）加列/加索引：评估锁表影响，用在线 DDL（`ALGORITHM=INPLACE`），低峰期执行
- 禁止直接 DROP 列/表——先标记废弃，确认无引用再删
- DDL 进版本管理（Flyway/Liquibase/迁移脚本），不手工执行线上库
- 变更前检查依赖：外键、存储过程、应用代码引用

### 4. 时区与时间类型（高频坑）

- 统一 DATETIME，不用 TIMESTAMP（2038 年问题 + 时区转换坑）
- 存业务本地时区，应用层转换展示；明确注释时区约定
- 禁止 `NOW()` 与代码侧时间混用（应用服务器时区不一致 → 数据错乱）
- 日期边界用 `>= start AND < end`（左闭右开），避免漏 `23:59:59` 数据

```sql
-- 反例：漏当天最后一秒数据
WHERE create_time <= '2026-01-01 23:59:59'   -- 依赖毫秒精度，易漏
-- 正例
WHERE create_time >= '2026-01-01' AND create_time < '2026-01-02'
```

### 5. 字符集与编码

- 统一 utf8mb4（emoji/生僻字），禁止 utf8（MySQL 的 utf8 不是真 UTF-8）
- 排序规则统一（utf8mb4_general_ci / utf8mb4_0900_ai_ci 团队选一）
- join/比对列字符集一致，否则隐式转换 + 乱码/索引失效
- 存储用户输入前：长度校验 + 转义（防超长/注入）

### 6. 事务边界与并发写

- 写操作显式声明事务边界；禁止跨请求长事务
- 并发写：乐观锁（版本号）或条件更新（`WHERE status = 1`），禁止无锁覆盖
- 批量更新锁顺序一致，避免死锁
- 唯一约束兜底并发防重（订单号、幂等键），代码校验有并发窗口

### 7. 敏感数据

- 禁止明文存密码（哈希+盐）、手机号/身份证加密或脱敏
- 日志/SQL 输出不打印敏感列值
- 生成环境查询禁止导出全量敏感数据

## 自检清单

- [ ] UPDATE/DELETE 必带 WHERE 且条件精确
- [ ] 大范围写操作已备份 + SELECT 预验证
- [ ] 大表 DDL 用在线变更，进版本管理
- [ ] 时间统一 DATETIME + 左闭右开边界
- [ ] 字符集 utf8mb4 统一
- [ ] 写操作有事务边界，并发有锁/版本控制
- [ ] 无明文敏感数据
