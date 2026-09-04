# 单元测试规范 (Unit Test Standards)

## 适用范围

编写单元测试、审查测试代码时加载。面向 Java（JUnit5 + Mockito + Spring Boot Test），测试原则适用任何语言。

## 强制规则

### 1. 测试结构（AAA）

每个测试方法遵循 **Arrange-Act-Assert** 三段，空行分隔：

```java
/**
 * 用例：合法入参创建订单，应返回订单号。
 */
@Test
void createOrderShouldReturnOrderIdWhenValid() {
    // Arrange
    OrderCreateDTO dto = new OrderCreateDTO();
    dto.setUserId(100L);
    dto.setSkuId("SKU001");

    // Act
    Long orderId = orderService.create(dto);

    // Assert
    assertThat(orderId).isNotNull();
}
```

- 禁止测试方法内串多个独立场景（一个测试一个行为）
- **测试方法命名：英文驼峰**，格式 `被测行为 + 条件 + 期望`（`createOrderShouldThrowWhenUserNotExist`）
  - 禁止中文方法名、禁止拼音方法名（`创建订单_合法入参_返回订单号` / `chuangjian` 均为反例）
  - 用例场景用中文写在方法 Javadoc（`/** 用例：非法入参（商品不存在）应返回 400 + 错误码。 */`）
  - 断言失败时的可读性靠英文方法名 + 中文注释保证（方法名可读、注释可追溯）

### 2. Mock 规则

- 单测只测当前类，依赖全部 mock（Mapper、其他 Service、外部客户端）
- 只 mock 被测类直接依赖，不 mock 被测类本身（禁 spy 被测类）
- `when` 给必要返回值；验证交互用 `verify`（次数/顺序）

```java
/**
 * 用例：取消待支付订单，应更新状态为已取消。
 */
@Test
void cancelOrderShouldUpdateStatusWhenPending() {
    // Arrange
    when(orderMapper.selectById(1L)).thenReturn(pendingOrder);

    // Act
    orderService.cancel(1L);

    // Assert
    verify(orderMapper).updateById(argThat(o -> o.getStatus() == CANCELED));
    verify(orderMapper, never()).deleteById(any());
}
```

- 禁止 mock 值对象/DTO/Entity（用真实对象，构造填充字段）
- mock 无返回值方法：`doNothing().when(...)` 显式声明，或依赖默认行为

### 3. 断言风格

- 用 AssertJ（`assertThat`）或 Hamcrest 流式断言，禁止裸 JUnit `assertEquals` 满天飞（可读性）
- 集合断言：`assertThat(list).hasSize(2).containsExactly(o1, o2)`
- 异常断言：`assertThatThrownBy(() -> service.create(dto)).isInstanceOf(BusinessException.class).hasMessageContaining("订单不存在")`
- 禁止断言实现细节（内部调用顺序、日志输出）；断言行为结果

### 4. Spring 上下文测试（@SpringBootTest）

- 尽量少用 `@SpringBootTest`（启动慢）；能用纯单测不用 Spring
- Service 层集成测试：`@SpringBootTest` + mock 外部依赖（`@MockBean`），或 `@DataJpaTest`/切片测试
- `@MockBean` 用完即弃：每个测试类独立声明，不共享

### 5. 测试隔离

- 每个测试独立：不依赖执行顺序、不共享可变状态（测试间数据污染 = 最坑）
- 共享静态状态在 `@BeforeEach` 重置
- 并行测试注意共享资源（DB、Redis）隔离

### 6. 禁止事项

- ❌ 测试依赖真实外部服务（DB/Redis/MQ/HTTP）——用 mock 或 Testcontainers（见 test-data 规范）
- ❌ `Thread.sleep` 等待（用 awaitility 轮询或 mock 固定返回值）
- ❌ 测实现细节（private 方法、内部字段）——测行为
- ❌ 测试内 if 分支/循环做断言（测试要线性）
- ❌ 为了过测试删断言、改逻辑迁就实现（测试是验收标准）

## 反例 / 正例

```java
// 反例：多场景一个测试 + 裸断言 + 依赖执行顺序
@Test
void testCreate() {
    Order o = new Order();
    orderService.create(o);
    assertEquals(1, orderMapper.count());
    orderService.create(o);
    assertEquals(2, orderMapper.count());   // 依赖前一个测试的残留数据
}
```

```java
// 正例：单场景 + 行为断言
/**
 * 用例：合法入参创建订单，应只落库一次。
 */
@Test
void createOrderShouldPersistOnceWhenValid() {
    OrderCreateDTO dto = new OrderCreateDTO();
    dto.setUserId(100L);

    orderService.create(dto);

    verify(orderMapper, times(1)).insert(any(Order.class));
}
```

## 最佳实践

- 测试金字塔：底层单测多、集成少、E2E 更少
- 每个 bug 修复先写复现测试（红）→ 修复 → 绿（防回归）
- 测试命名表达业务语义（英文驼峰），中文用例说明写 Javadoc，不写测试的人也能看懂

## 自检清单

- [ ] AAA 结构，一个测试一个行为
- [ ] 方法名英文驼峰（禁止中文/拼音方法名），用例中文写 Javadoc
- [ ] 依赖全 mock，无真实外部服务
- [ ] AssertJ 流式断言，无裸 assertEquals
- [ ] 无 Thread.sleep
- [ ] 测试隔离，无顺序依赖
- [ ] 无改逻辑迁就测试
