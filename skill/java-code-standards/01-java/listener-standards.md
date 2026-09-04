# Listener 规范 (Message Listener Standards)

## 适用范围

生成消息队列消费端（RabbitMQ/Kafka/RocketMQ Listener）代码时加载。与 ai-dev-workflow 3.2 Listener 技术方案模板配合。

## 强制规则

### 1. 类结构

- `@RabbitListener` / `@KafkaListener` 注解，监听方法只做消费编排，业务逻辑进 Service

```java
@Component
@RequiredArgsConstructor
public class OrderCreatedListener {

    private final OrderService orderService;

    @RabbitListener(queues = "order.created.queue", ackMode = "MANUAL")
    public void onOrderCreated(OrderCreatedMsg msg, Channel channel,
                               @Header(AmqpHeaders.DELIVERY_TAG) long tag) throws IOException {
        orderService.handleOrderCreated(msg);
        channel.basicAck(tag, false);   // 处理成功手动 ACK
    }
}
```

### 2. 消费幂等（必须）

- 消息可能重复投递（网络重试/生产者重发），消费必须幂等
- 幂等实现：业务唯一键（消息内业务 ID）+ 去重表/Redis SETNX，或状态位校验

```java
public void handleOrderCreated(OrderCreatedMsg msg) {
    boolean first = orderProcessRecord.saveIfAbsent(msg.getOrderNo());  // 幂等键
    if (!first) {
        log.info("重复消息，跳过: orderNo={}", msg.getOrderNo());
        return;
    }
    // 处理业务
}
```

- 幂等记录与业务处理同事务（防记录成功但处理失败丢消息）

### 3. ACK 与死信

- 手动 ACK：处理成功才 ack；处理失败 requeue 或进死信
- 消费异常重试有上限（3-5 次），超限进死信队列，禁止无限重试堵塞
- 死信队列单独监听 + 告警（业务兜底人工处理）
- 消息格式版本化（字段加版本号），兼容演进

### 4. 消费性能

- 单条消息处理要快：不依赖远程调用阻塞，重活异步化或拆分消息
- 批量消费（Kafka poll 多条）批量处理
- 消费线程池配置：并发数配置化，防消息堆积也防打爆下游

### 5. 错误处理

- 消费方法不吞异常：可重试异常上抛（触发重试），不可重试（业务数据错误）直接进死信
- 关键消费日志：消息 ID、业务键、处理结果
- 禁止 catch 后静默（消息丢失无感知）

## 反例 / 正例

```java
// 反例：自动 ACK + 无幂等 + 吞异常
@RabbitListener(queues = "order.created.queue")
public void onOrderCreated(OrderCreatedMsg msg) {
    try {
        orderService.handle(msg);   // 处理失败也 ack，消息丢失
    } catch (Exception e) {
        log.error("处理失败", e);    // 静默吞掉，不重试不进死信
    }
}
```

```java
// 正例：手动 ACK + 幂等 + 失败抛错重试
@RabbitListener(queues = "order.created.queue", ackMode = "MANUAL")
public void onOrderCreated(OrderCreatedMsg msg, Channel channel,
                           @Header(AmqpHeaders.DELIVERY_TAG) long tag) throws IOException {
    try {
        orderService.handleOrderCreated(msg);   // 内部含幂等
        channel.basicAck(tag, false);
    } catch (BusinessException e) {
        channel.basicReject(tag, false);        // 业务失败进死信
    } catch (Exception e) {
        throw e;                                // 系统异常抛错触发重试
    }
}
```

## 自检清单

- [ ] 消费幂等（唯一键/状态位）
- [ ] 手动 ACK，处理成功才确认
- [ ] 重试有上限，失败进死信
- [ ] 无吞异常静默
- [ ] 无远程调用阻塞消费线程
- [ ] 日志含消息 ID + 业务键
