# 性能优化规范 (Performance Standards)

## 适用范围

生成性能敏感代码（高频接口、批量任务、大数据量处理）时加载。

## 强制规则

### 1. 循环内禁做重操作

| 禁止 | 替代 |
|---|---|
| 循环内查库（N+1） | 批量查询后内存映射 |
| 循环内调远程接口 | 批量接口或并发聚合 |
| 循环内 new 大对象/序列化 | 复用或循环外准备 |
| 循环内打日志（INFO） | 聚合统计一次输出 |

```java
// 反例：N+1
for (Long orderId : orderIdList) {
    Order order = orderMapper.selectById(orderId);   // 100 次查询
}

// 正例：批量 + 内存映射
List<Order> orders = orderMapper.selectBatchIds(orderIdList);
Map<Long, Order> orderMap = orders.stream()
        .collect(Collectors.toMap(Order::getId, Function.identity()));
for (Long orderId : orderIdList) {
    Order order = orderMap.get(orderId);
}
```

### 2. 集合与字符串

- 已知容量初始化：`new ArrayList<>(expectedSize)`、`new HashMap<>(capacity)`，避免扩容
- 循环拼接字符串用 `StringBuilder`（或预分配），禁 `+` 拼接

```java
// 反例
String s = "";
for (String item : items) {
    s = s + item + ",";   // O(n²)
}

// 正例
StringBuilder sb = new StringBuilder(items.size() * 8);
for (String item : items) {
    sb.append(item).append(',');
}
```

- 频繁 contains 用 HashSet（O(1)）不用 List（O(n)）
- 大列表去重/统计用流 + 收集器，避免手写双重循环

### 3. 对象与资源

- 大对象池化：连接池、线程池复用（见 concurrency 规范），禁每请求 new
- 正则 Pattern 编译为 static final，禁方法内重复 `Pattern.compile`
- 流式处理大文件/大响应：`InputStream`/`Reader` 边读边处理，不整体 load 内存
- 序列化（JSON）对象复用 `ObjectMapper` 单例（Spring 注入），禁每次 new

### 4. 数据库交互

- 批量写：`insertBatch`（foreach 500~1000 一批），禁循环单条
- 只取需要的列与行：分页/limit 兜底，禁无界查询
- 大事务拆小：万级批量处理分批提交（每批 commit），禁一个事务吞全部
- 长事务内禁远程调用（锁资源持有过久，见 service-impl 规范）

### 5. 异步与并行

- 独立无依赖的耗时操作（通知、日志、非关键同步）走异步（`@Async` 或消息队列）
- 并行聚合多数据源用 CompletableFuture + 自定义线程池（禁默认 ForkJoinPool 阻塞场景）

```java
CompletableFuture<List<A>> fa = CompletableFuture.supplyAsync(() -> serviceA.query(), executor);
CompletableFuture<List<B>> fb = CompletableFuture.supplyAsync(() -> serviceB.query(), executor);
CompletableFuture.allOf(fa, fb).join();
```

- 异步任务必须有异常兜底（记录日志），防静默失败

### 6. 性能基线

- 高频接口（QPS 高）先定基线：单接口 P99 延迟、DB 慢查询数
- 优化前先测量（Arthas/JFR/APM），不凭感觉优化
- 每轮优化一个点，压测验证再动下一处

### 7. 监控指标（Micrometer/Prometheus）

- 关键业务埋点：接口请求量/延迟（内置自动）、核心业务流程计数（订单创建数）、错误率
- 自定义指标用 Micrometer（`@Timed` / `Counter` / `Gauge`），统一命名规范

```java
// 正例：业务指标 + tag
@Timed(name = "order.create", description = "订单创建耗时")
public OrderVO create(OrderCreateDTO dto) { ... }

// 计数器
private final Counter orderCreateCounter = Metrics.counter("order.create.count",
        "biz", "order");
orderCreateCounter.increment();
```

- 指标命名：`模块.操作.类型`（`order.create.count`、`payment.timeout.total`），小写点分
- tag 有界：用固定枚举值（状态/类型），禁高基数 tag（用户 ID、订单号 → 指标爆炸）
- 指标只埋业务关键点，不每个方法都埋（采集成本 + 噪音）
- 告警阈值配置化（Prometheus rule），不硬编码在代码

## 反例 / 正例

```java
// 反例：循环内查库 + 拼接 + 大对象
List<OrderVO> result = new ArrayList<>();
for (Long id : ids) {
    Order o = orderMapper.selectById(id);
    result.add(buildVO(o));   // buildVO 内部又查商品表
}

// 正例：批量 + 内存组装（一次查订单、一次查商品、内存 join）
```

## 自检清单

- [ ] 无 N+1 查询
- [ ] 无循环内远程调用/日志/大对象
- [ ] 集合指定容量，字符串 StringBuilder
- [ ] 正则/序列化对象复用
- [ ] 批量写分批，事务大小受控
- [ ] 耗时独立操作异步化
- [ ] 优化前有测量基线
- [ ] 业务关键点有指标埋点，命名规范
- [ ] 无高基数 tag（用户 ID/订单号）
- [ ] 告警阈值配置化
