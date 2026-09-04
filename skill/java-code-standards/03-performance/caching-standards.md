# 缓存使用规范 (Caching Standards)

## 适用范围

使用 Redis、本地缓存（Caffeine）缓存数据时加载。定义缓存策略、key 设计、一致性。

## 强制规则

### 1. 缓存适用判断

| 适合缓存 | 不适合缓存 |
|---|---|
| 读多写少、变化不频繁 | 实时性要求高（库存扣减） |
| 热点数据（商品、配置、用户信息） | 强一致性要求（余额） |
| 计算昂贵（复杂查询、远程聚合） | 单次读、无复用价值 |

- 缓存引入前先确认：命中率潜力高、数据可容忍短暂不一致

### 2. Key 设计

- 统一格式：`业务:对象:标识`，如 `order:detail:{orderId}`
- key 前缀集中定义常量类（见 constants 规范），禁止散落拼串
- key 含上下文（租户/用户），防串数据

```java
private static final String ORDER_DETAIL_KEY = "order:detail:";

public OrderVO getOrderDetail(Long orderId) {
    String key = ORDER_DETAIL_KEY + orderId;
    // ...
}
```

### 3. 缓存策略

**Cache-Aside（旁路，推荐默认）**：
- 读：先查缓存 → 未命中查库 → 回填缓存 → 返回
- 写：先写库 → 删缓存（不更新缓存，避免并发写缓存不一致）

```java
public OrderVO getOrderDetail(Long orderId) {
    String key = ORDER_DETAIL_KEY + orderId;
    OrderVO cachedOrderVO = cache.get(key, OrderVO.class);
    if (cachedOrderVO != null) {
        return cachedOrderVO;
    }
    OrderVO dbOrderVO = orderService.getDetailFromDb(orderId);  // 回源
    if (dbOrderVO != null) {
        cache.set(key, dbOrderVO, TTL_SECONDS);
    }
    return dbOrderVO;
}

@Transactional(rollbackFor = Exception.class)
public void updateOrder(Long orderId, OrderUpdateDTO updateInfo) {
    orderMapper.updateById(toEntity(updateInfo));
    cache.delete(ORDER_DETAIL_KEY + orderId);   // 写库后删缓存
}
```

### 4. 一致性策略

- **写库后删缓存** 优于 写库后更新缓存（删可容忍并发重算，更新有竞态窗口）
- 删除失败补偿：延迟双删 / 消息队列重删 / 监听 binlog 删缓存
- 缓存与库强一致场景（少）：串行化写 + 版本校验；绝大多数业务用最终一致

### 5. 缓存问题防治

| 问题 | 方案 |
|---|---|
| 缓存穿透（查不存在） | 空值缓存（TTL 短）或布隆过滤器 |
| 缓存击穿（热点 key 失效） | 互斥锁重建 / 逻辑过期 |
| 缓存雪崩（大批 key 同时失效） | TTL 加随机抖动 / 多级缓存 |

```java
// 互斥锁重建（击穿防护）
public OrderVO getHotOrder(Long orderId) {
    String key = ORDER_DETAIL_KEY + orderId;
    OrderVO orderVO = cache.get(key, OrderVO.class);
    if (orderVO != null) {
        return orderVO;
    }
    String lockKey = "lock:" + key;
    boolean locked = redisLock.tryLock(lockKey, 3, TimeUnit.SECONDS);
    if (!locked) {
        // 未抢到锁，短暂等待后重试（或返回兜底）
        return fallbackGet(orderId);
    }
    try {
        orderVO = cache.get(key, OrderVO.class);   // 双重检查
        if (orderVO == null) {
            orderVO = orderService.getDetailFromDb(orderId);
            cache.set(key, orderVO, TTL_SECONDS);
        }
        return orderVO;
    } finally {
        redisLock.unlock(lockKey);
    }
}
```

- TTL 随机抖动：`TTL + ThreadLocalRandom.current().nextInt(300)`

### 6. 本地缓存（Caffeine）

- 本地缓存用于：进程内高频只读数据（字典、配置、元数据），TTL 短
- 多实例部署注意本地缓存一致性（发布/变更时清或接受短时不一致）
- 容量上限（maximumSize），防内存膨胀

```java
@Bean
public Cache<String, DictVO> dictCache() {
    return Caffeine.newBuilder()
            .maximumSize(10_000)
            .expireAfterWrite(5, TimeUnit.MINUTES)
            .build();
}
```

### 7. 禁止事项

- ❌ 缓存存超大对象（> 1MB 列表）：拆 key 或换存储
- ❌ 缓存敏感数据明文（脱敏后存）
- ❌ 无 TTL 永不过期缓存（除非强一致 + 主动管理）
- ❌ 业务逻辑依赖缓存读取结果做关键判断（缓存可能 miss）

## 反例 / 正例

```java
// 反例：写库后更新缓存（并发窗口不一致）+ 无 TTL + key 散落
orderMapper.updateById(order);
cache.set("order_" + orderId, order);   // 两个请求并发更新，旧值覆盖新值

// 正例
orderMapper.updateById(order);
cache.delete(ORDER_DETAIL_KEY + orderId);
```

## 性能优化建议

- 多级缓存：本地（微秒）→ Redis（毫秒）→ DB（10ms+），逐级回源
- 批量热点查询用 pipeline/MGET，禁循环单次 get（N 次 RTT）
- 大 key 拆分；热点 key 复制分片（读扩散）

## 自检清单

- [ ] 缓存适用性已评估（读多写少）
- [ ] key 统一前缀 + 常量管理
- [ ] Cache-Aside：写库后删缓存
- [ ] 穿透/击穿/雪崩有防护
- [ ] 空值有短 TTL 缓存
- [ ] 本地缓存限容量 + TTL
- [ ] 无敏感明文缓存
- [ ] 批量操作用 pipeline
