# 并发编程规范 (Concurrency Standards)

## 适用范围

编写多线程、异步、锁、共享状态代码时加载。

## 强制规则

### 1. 共享状态

- 类字段尽量不可变（`final`）；可变共享状态必须同步保护
- 静态可变字段（`static` 集合、缓存）必须线程安全容器：`ConcurrentHashMap`、`CopyOnWriteArrayList`
- 线程封闭优先：能用局部变量不用共享字段

```java
// 反例：HashMap 共享
public class CacheHolder {
    private static final Map<String, String> CACHE = new HashMap<>();  // 并发写丢数据/死循环(JDK7)
}

// 正例
private static final Map<String, String> CACHE = new ConcurrentHashMap<>();
```

### 2. 原子操作

- 计数/累加用 `AtomicLong`/`LongAdder`（高并发计数 LongAdder 更优）
- 复合操作（check-then-act：先查后改）用锁或原子 CAS，禁用两个独立原子操作拼接

```java
// 反例：非原子 check-then-act
if (counter.get() < MAX) {
    counter.incrementAndGet();   // 两个线程可同时通过检查，超限
}

// 正例：AtomicInteger 原子方法
int cur = counter.get();
while (cur < MAX && !counter.compareAndSet(cur, cur + 1)) {
    cur = counter.get();
}
```

### 3. 锁使用

- 优先 `synchronized`（简单场景），需要超时/可中断/多条件用 `ReentrantLock`
- 锁粒度最小化：只锁共享资源操作，不锁整个方法（读多写少用 `ReadWriteLock`/`StampedLock`）
- 锁顺序一致防死锁；多锁场景按固定顺序获取（A→B，永不 B→A）
- 禁 `synchronized` 内做远程调用/DB 慢查询（持锁过久）

```java
// 正例：细粒度锁
private final ReentrantLock lock = new ReentrantLock();

public void deduct() {
    lock.lock();
    try {
        // 只保护共享计数操作
    } finally {
        lock.unlock();
    }
}
```

### 4. 线程池

- 禁 `Executors.newFixedThreadPool`（无界队列 OOM 风险）；用 `ThreadPoolExecutor` 显式参数

```java
@Bean("orderNotifyExecutor")
public ThreadPoolExecutor orderNotifyExecutor() {
    return new ThreadPoolExecutor(
            4, 8,
            60L, TimeUnit.SECONDS,
            new ArrayBlockingQueue<>(1000),
            new ThreadFactoryBuilder().setNameFormat("order-notify-%d").build(),
            new ThreadPoolExecutor.CallerRunsPolicy());  // 拒绝策略业务化
    );
}
```

- 参数配置化（见 config 规范），命名线程工厂便于排查
- 拒绝策略明确：`CallerRunsPolicy`（降速）或自定义（告警 + 丢弃），禁默认 Abort 静默抛

### 5. 异步正确性

- `@Async` 方法：同类自调用失效（代理）；异常默认静默——配 `AsyncUncaughtExceptionHandler` 记录
- 异步任务上下文（用户、traceId）用 `TaskDecorator` 传递
- Future 等待设超时：`future.get(3, TimeUnit.SECONDS)`，禁无限等待

### 6. 并发容器选择

| 场景 | 容器 |
|---|---|
| 读多写少 | CopyOnWriteArrayList |
| 高并发写 | ConcurrentHashMap |
| 有序队列 | ConcurrentLinkedQueue / 阻塞队列 |
| 延迟任务 | DelayQueue / ScheduledExecutor |

## 反例 / 正例

```java
// 反例
public class TicketService {
    private int stock;   // 无保护

    public void buy() {
        if (stock > 0) {        // check 与 act 分离，超卖
            stock--;            // 非原子
        }
    }
}

// 正例：数据库/原子操作保证，见 service-impl 乐观锁示例
```

## 性能优化建议

- 读多写少用 `LongAdder`/`StampedLock`，减少 CAS 竞争
- 锁竞争热点：分段锁、或改为无锁结构（原子 + 不可变）
- 避免伪共享：高频写字段 padding 或使用 LongAdder 内部实现
- 线程池线程数经验：CPU 密集 = CPU 核数 + 1；IO 密集 = CPU 核数 × (1 + 等待/计算比)

## 自检清单

- [ ] 共享状态线程安全容器
- [ ] 复合操作用原子/锁，无 check-then-act 竞态
- [ ] 锁粒度小，无锁内远程调用
- [ ] 无 Executors 快捷方法创建线程池
- [ ] 线程池命名 + 拒绝策略明确
- [ ] 异步有异常兜底 + 超时
- [ ] 无死锁风险（锁顺序一致）
