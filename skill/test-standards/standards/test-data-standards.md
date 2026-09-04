# 测试数据规范 (Test Data Standards)

## 适用范围

准备测试数据、使用数据库测试环境（Testcontainers/嵌入式库/数据工厂）时加载。

## 强制规则

### 1. 测试数据原则

- 测试数据在测试内构造（工厂/Builder），**不依赖生产数据、不依赖手工预置的共享库数据**
- 测试用到的数据必须显式声明，禁止隐式依赖"库里恰好有一条 id=1 的记录"
- 每个测试独立准备数据，测试结束清理（或靠事务回滚/容器重建）

### 2. 数据工厂（Factory）

- 实体构造用工厂类（`TestOrderFactory` / Builder），集中默认值，测试只覆盖差异字段

```java
public class TestOrderFactory {
    public static Order pendingOrder(Long id) {
        Order o = new Order();
        o.setId(id);
        o.setUserId(100L);
        o.setStatus(OrderStatus.PENDING);
        o.setAmount(new BigDecimal("99.90"));
        return o;
    }
}
```

- 默认值满足大多数测试，特殊情况显式覆盖

### 3. 数据库集成测试

| 方案 | 适用 | 注意 |
|---|---|---|
| H2 嵌入式 | 快速单测、简单 SQL | 方言差异（MySQL 语法可能不兼容），复杂 SQL 不用 |
| Testcontainers（推荐） | 真实数据库行为 | 启动慢，CI 用 Docker；测试类共享容器实例 |
| 事务回滚 | Service 层集成 | `@Transactional` 测试默认回滚，防污染 |

- 生产用 MySQL 的项目，复杂 SQL 测试**必须 Testcontainers MySQL**（H2 方言坑）
- Testcontainers 容器实例：静态字段 + `@Container` 共享，避免每测试启动

```java
@Testcontainers
class OrderMapperIT {

    @Container
    static MySQLContainer<?> mysql = new MySQLContainer<>("mysql:8.0")
            .withDatabaseName("test")
            .withUsername("test")
            .withPassword("test");

    @Test
    void selectPage_shouldFilterByStatus() {
        // 使用 mysql.getJdbcUrl() 连接
    }
}
```

### 4. 数据隔离

- 并行测试（CI 多线程）避免共享库数据冲突：每个测试类独立数据空间或容器
- 测试库与开发库分离，禁止测试连生产库（数据安全事故）
- 批量清理策略：`@Sql` 前置脚本 / truncate / 容器重建，不在测试里写循环删

### 5. 禁止事项

- ❌ 测试依赖真实线上数据（敏感数据泄露风险 + 不可控）
- ❌ 测试内 `INSERT` 大段 SQL 硬编码（用工厂 + ORM）
- ❌ 测试数据散落各测试类重复构造（抽工厂）
- ❌ 断言依赖数据插入顺序/自增 ID 具体值

## 自检清单

- [ ] 测试数据工厂化，无散落构造
- [ ] 不依赖共享库预置数据
- [ ] 复杂 SQL 用 Testcontainers 真实库
- [ ] 测试库与生产库隔离
- [ ] 测试独立可重复运行
- [ ] 无敏感数据入测试
