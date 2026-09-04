# ServiceImpl 规范 (Service Implementation Standards)

## 适用范围

生成 Service 实现类时加载。定义事务使用、业务逻辑组织、依赖注入、并发控制。

## 强制规则

### 1. 类结构

- `@Service` 注解，实现接口，类注释说明实现要点
- 依赖注入用构造器注入（`@RequiredArgsConstructor` + final 字段），禁止字段注入 `@Autowired`

```java
@Service
@RequiredArgsConstructor
public class OrderServiceImpl implements OrderService {

    private final OrderMapper orderMapper;
    private final OrderItemService orderItemService;
    private final RedisTemplate<String, String> redisTemplate;

    @Override
    public void submitOrder(Long orderId) {
        // 业务逻辑
    }
}
```

- 只注入本类需要的依赖，不层层透传

### 2. 事务管理

- 事务加在实现类方法上，写清 `rollbackFor`

```java
@Override
@Transactional(rollbackFor = Exception.class)
public void createOrder(OrderCreateDTO createInfo) {
    Order order = new Order();
    // 主表插入
    orderMapper.insert(order);
    // 明细插入，任一失败整体回滚
    orderItemService.insertBatch(order.getId(), createInfo.getItems());
}
```

- `@Transactional` 默认只回滚 RuntimeException，必须显式 `rollbackFor = Exception.class`
- 只读查询不加事务；一个事务内不做远程调用（第三方 HTTP/RPC），锁库时间过长
- 事务内异常上抛，不 catch 后吞掉（否则无法回滚）
- 自调用陷阱：同类内方法调用不经过代理，`@Transactional` 失效——事务方法放接口/外部调用

### 3. 业务逻辑组织

- 方法遵循：校验 → 取数 → 计算 → 落库 → 通知/清理，顺序清晰
- 复杂度高时拆分私有方法，每方法一个意图
- 状态流转用枚举 + 状态机校验，不散落 if 判断

```java
// 正例：状态流转校验
public void cancelOrder(Long orderId) {
    Order order = getOrderWithCheck(orderId);
    orderStatusMachine.validate(order.getStatus(), OrderAction.CANCEL);
    // ...
}

private Order getOrderWithCheck(Long orderId) {
    Order order = orderMapper.selectById(orderId);
    if (order == null) {
        throw new BusinessException(ErrorCode.ORDER_NOT_FOUND, "订单不存在");
    }
    return order;
}
```

### 4. 数据操作边界

- 通过 Mapper/其他 Service 访问数据，不直接 new 其他实现类
- 跨实体事务：调用其他 Service 的 `@Transactional` 方法，事务传播默认 REQUIRED 合并
- 循环依赖：构造器注入下编译即报错，发现即重构（抽中间层）

### 5. 并发控制

- 库存/余额类写操作加乐观锁（版本号）或行锁，禁止无锁覆盖

```java
// 正例：MyBatis-Plus 乐观锁（SQL 在 XML，接口只声明；禁注解 SQL）
int deductStock(@Param("id") Long id, @Param("delta") Integer delta,
                @Param("version") Integer version);

// 调用处
int rows = stockMapper.deductStock(stockId, delta, stock.getVersion());
if (rows == 0) {
    throw new BusinessException(ErrorCode.STOCK_LOCKED, "库存不足或已变更，请重试");
}
```

```xml
<!-- resources/mapper/StockMapper.xml -->
<update id="deductStock">
    UPDATE stock
    SET quantity = quantity - #{delta}, version = version + 1
    WHERE id = #{id} AND version = #{version} AND quantity >= #{delta}
</update>
```

## 反例 / 正例

```java
// 反例：字段注入 + 吞异常 + 事务无效
@Service
public class OrderServiceImpl implements OrderService {
    @Autowired
    private OrderMapper orderMapper;

    @Transactional
    public void create(OrderCreateDTO createInfo) {
        try {
            orderMapper.insert(toEntity(createInfo));
        } catch (Exception e) {
            log.error("create order error", e);
            // 异常被吞，事务提交脏数据
        }
    }
}

// 正例
@Override
@Transactional(rollbackFor = Exception.class)
public void create(OrderCreateDTO createInfo) {
    orderMapper.insert(toEntity(createInfo));
}
```

## 最佳实践

- 复杂领域逻辑（价格计算、状态机）抽独立领域类，ServiceImpl 只做编排
- 批量操作（> 100 条）用批量插入/更新（见 sql 规范），不循环单条
- 幂等：重复提交场景用唯一键或幂等表防重
- 日志（**方法级全覆盖，见 `00-common/04-logging-standards.md` §1.6**）：每个业务方法（含抽取的 private 辅助方法）方法体内 ≥1 条 INFO/WARN/ERROR 日志（**debug 不算**）——入口记入参摘要（方法名 + 关键入参）、关键状态变更记 INFO、返回前记结果；大段逻辑（≥10 行）无 INFO/WARN/ERROR = 不合格

## 性能优化建议

- 事务内禁止远程调用与长循环；事务范围尽量小
- 查询结果缓存于方法内局部变量，不重复查库
- N+1 查询：批量取数后内存组装，不循环逐条查（见 mybatis-xml / sql 规范）

## 自检清单

- [ ] 构造器注入，无 @Autowired 字段注入
- [ ] 事务方法显式 rollbackFor，无吞异常
- [ ] 无循环依赖
- [ ] 事务内无远程调用
- [ ] 并发写有乐观锁/行锁
- [ ] 校验 → 业务 → 落库顺序清晰
- [ ] 无 N+1 查询
