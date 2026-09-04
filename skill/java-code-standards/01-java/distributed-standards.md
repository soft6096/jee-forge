# 分布式规范 (Distributed Systems Standards)

## 适用范围

生成分布式场景代码时加载：分布式锁、幂等、分布式事务取舍、跨服务调用。

## 强制规则

### 1. 分布式锁

- 用 Redis SETNX + 过期时间（Redisson 封装优先），禁止裸 SETNX 无过期（死锁风险）

```java
// 正例：Redisson 锁（自动续期 + 原子释放）
RLock lock = redissonClient.getLock("lock:order:" + orderId);
boolean locked = lock.tryLock(3, 30, TimeUnit.SECONDS);   // 等待3s，持锁30s自动续期
if (!locked) {
    throw new BusinessException(ErrorCode.LOCKED, "操作太频繁，请重试");
}
try {
    // 临界区
} finally {
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();   // 原子释放，防误删他人锁
    }
}
```

- 锁粒度最小化：按业务资源加锁（订单维度），不全局一把锁
- 锁内不做远程调用/长耗时（持锁过久，锁竞争雪崩）
- 锁 key 与业务资源一致：`lock:业务:资源ID`

### 2. 幂等设计

- 写接口必须幂等（重试/重复提交安全）：下单、支付回调、MQ 消费
- 幂等方案选择：

| 方案 | 适用 | 实现 |
|---|---|---|
| 唯一键约束 | 防重复插入 | 业务唯一键 + 唯一索引，冲突转幂等返回 |
| 状态位 | 状态流转 | 处理前校验状态，已处理跳过 |
| 幂等表/记录 | 通用 | 请求唯一键（客户端生成 token）+ 去重表 |
| Redis SETNX | 短窗口幂等 | 请求 ID + 过期时间 |

```java
// 幂等：请求唯一键 + 数据库唯一约束兜底
public void handlePaymentCallback(PaymentCallbackDTO callback) {
    boolean first = paymentRecord.saveIfAbsent(callback.getTransactionId());  // 唯一键
    if (!first) {
        log.info("重复回调，跳过: {}", callback.getTransactionId());
        return;
    }
    // 更新订单支付状态
}
```

- 幂等键持久化与业务处理同事务（防记录成功业务失败丢单）
- 幂等键要有过期策略（防表无限膨胀）

### 3. 分布式事务取舍

- 默认不用分布式事务（2PC/XA 慎用，性能差 + 复杂度高）
- 取舍：

| 场景 | 方案 |
|---|---|
| 跨库强一致（少） | 本地消息表 + 可靠消息（最终一致） |
| 跨服务最终一致（多） | MQ 事件驱动 + 幂等消费 + 对账补偿 |
| 单服务多表 | 本地事务（@Transactional），不需要分布式 |

- 用 Saga/事务消息前评估：业务真需要强一致吗？多数场景最终一致 + 对账可接受
- 补偿必须有：正向操作配反向操作（冲正/退款），补偿幂等

### 4. 跨服务调用

- 同步调用设超时（连接 + 读超时），禁无限等待
- 重试有上限 + 退避（指数退避），禁无脑重试
- 下游不可用熔断降级（Sentinel/Resilience4j），禁线程阻塞堆积
- 调用链传 traceId（MDC），跨服务日志串联
- 结果校验：下游返回失败/超时按业务语义处理，不吞

### 5. 禁止事项

- ❌ 裸 SETNX 无过期做分布式锁
- ❌ 全局一把锁（热点竞争）
- ❌ 写接口无幂等（重试双写）
- ❌ 跨服务强一致硬上 2PC
- ❌ 同步调用无超时无熔断

## 自检清单

- [ ] 分布式锁：SETNX + 过期 + 原子释放，锁粒度资源级
- [ ] 锁内无远程调用
- [ ] 写接口幂等（唯一键/状态位）
- [ ] 分布式事务方案已评估（多数用最终一致）
- [ ] 补偿操作存在且幂等
- [ ] 同步调用有超时 + 重试退避 + 熔断
- [ ] traceId 跨服务传递
