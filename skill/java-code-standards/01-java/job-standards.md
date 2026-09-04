# Job 规范 (Scheduled Job Standards)

## 适用范围

生成定时任务（Quartz/Spring @Scheduled）代码时加载。与 ai-dev-workflow 3.3 Job 技术方案模板配合。

## 强制规则

### 1. 类结构

- 定时任务类只做调度入口，业务逻辑进 Service（任务类可测性差）
- 调度配置外部化（cron 表达式走配置），不硬编码

```java
@Component
@RequiredArgsConstructor
public class OrderTimeoutJob {

    private final OrderService orderService;

    @Scheduled(cron = "${job.order-timeout.cron:0 0/5 * * * ?}")
    public void handleTimeoutOrders() {
        orderService.closeTimeoutOrders();
    }
}
```

### 2. 防重入（必须，多实例部署）

- 定时任务可能多实例同时触发（集群部署），必须防重入
- 方案：Redis 分布式锁（SETNX + 过期时间）或 Quartz 集群模式

```java
public void closeTimeoutOrders() {
    String lockKey = "job:lock:order-timeout";
    boolean locked = redisLock.tryLock(lockKey, 60, TimeUnit.SECONDS);  // 锁时长 > 任务预计时长
    if (!locked) {
        log.info("任务已在其他实例执行，跳过: {}", lockKey);
        return;
    }
    try {
        orderService.closeTimeoutOrders();
    } finally {
        redisLock.unlock(lockKey);
    }
}
```

- 锁过期时间 > 任务最大执行时长（防锁提前释放导致并发执行）
- 执行完释放锁，不靠 TTL 兜底（TTL 是兜底不是主路径）

### 3. 批处理控制

- 批处理单次不超过 500 条，分批处理 + 每批提交（防大事务）
- 全量扫描任务（扫全表）必须：时间范围约束 + 分批游标（id > lastId），禁止一次性全表
- 处理进度记录（游标/已处理位置），任务中断可续跑

```java
// 分批游标处理
public void processBatch() {
    Long lastId = 0L;
    while (true) {
        List<Order> batch = orderMapper.selectByCursor(lastId, 500);
        if (batch.isEmpty()) break;
        for (Order order : batch) {
            handleOrder(order);
        }
        lastId = batch.get(batch.size() - 1).getId();
        // 每批可独立提交或定期 checkpoint
    }
}
```

### 4. 执行记录与监控

- 任务执行记录日志：任务名、开始/结束时间、处理数量、耗时
- 异常不静默：失败告警（钉钉/邮件/日志平台）
- 长任务支持手动触发（管理接口），方便补跑

### 5. 禁止事项

- ❌ 任务内无锁无防重入（多实例重复执行）
- ❌ 任务处理量无上限（内存/DB 压力）
- ❌ 任务内长事务 + 远程调用
- ❌ cron 硬编码不配置化
- ❌ 任务失败静默无告警

## 反例 / 正例

```java
// 反例：无锁 + 全表 + 大事务
@Scheduled(cron = "0 0 2 * * ?")
public void cleanup() {
    List<Order> all = orderMapper.selectList(null);   // 全表拉内存
    for (Order o : all) {
        orderMapper.deleteById(o.getId());             // 循环单条 + 隐含大事务
    }
}
```

```java
// 正例：锁 + 分批游标
@Scheduled(cron = "${job.cleanup.cron}")
public void cleanup() {
    if (!redisLock.tryLock("job:lock:cleanup", 120, TimeUnit.SECONDS)) return;
    try {
        processBatch();   // 分批 500 游标处理
    } finally {
        redisLock.unlock("job:lock:cleanup");
    }
}
```

## 自检清单

- [ ] 分布式锁防重入（多实例安全）
- [ ] 批处理分批 + 游标，无全表一次拉
- [ ] 事务大小受控
- [ ] cron 配置化
- [ ] 执行日志 + 失败告警
- [ ] 支持手动触发补跑
