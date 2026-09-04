# Converter 规范 (MapStruct Converter Standards)

## 适用范围

生成对象转换器时加载。定义 Entity/DTO/VO 转换规范、MapStruct 使用。

## 强制规则

### 1. 转换器定位

- 统一用 MapStruct 生成转换器，禁止手写 get/set 转换散落业务代码
- 转换方向明确：Entity ↔ DTO、Entity ↔ VO、DTO → Entity

```java
@Mapper(componentModel = "spring")
public interface OrderConverter {

    OrderVO toVO(Order order);

    Order toEntity(OrderCreateDTO createInfo);

    List<OrderVO> toVOList(List<Order> orders);
}
```

- 注入方式：`componentModel = "spring"` 注入 Spring 容器，业务类构造注入

### 2. 映射规则

- 字段名相同自动映射；不同名用 `@Mapping` 显式声明

```java
@Mapper(componentModel = "spring")
public interface OrderConverter {

    @Mapping(target = "statusText", expression = "java(OrderStatusEnum.of(order.getStatus()).getDesc())")
    @Mapping(target = "userId", source = "user.id")
    OrderVO toVO(Order order, User user);
}
```

- 集合转换自动生成循环，禁止手写 for 循环转换
- `null` 处理：`@Mapping(target = "x", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.SET_TO_NULL)` 按需配置；默认跳过 null 可配 `NullValueCheckStrategy`

### 3. 类型转换

- 枚举 ↔ Integer：MapStruct 自动支持 name 映射，需 code 映射用 `@ValueMapping` 或 default expression
- 金额/时间类型一致则免配置，不一致显式表达式转换

```java
@Mapping(target = "amount", expression = "java(createInfo.getAmount().setScale(2, RoundingMode.HALF_UP))")
Order toEntity(OrderCreateDTO createInfo);
```

### 4. 边界

- 转换器只做**字段搬运与简单计算**，不读库、不调 Service
- 复杂组装（查关联数据填充）在 Service 完成后再转 VO
- ❌ 在 Converter 里写业务判断（状态流转、权限）——违反职责

## 反例 / 正例

```java
// 反例：手写转换 + 业务逻辑混入
OrderVO orderVO = new OrderVO();
orderVO.setId(order.getId());
orderVO.setOrderNo(order.getOrderNo());
orderVO.setAmount(order.getAmount());
if (order.getStatus() == 10) {
    orderVO.setStatusText("待支付");
} else if (order.getStatus() == 20) {
    orderVO.setStatusText("已支付");
}
// 200 行...

// 正例
OrderVO orderVO = orderConverter.toVO(order);
```

## 最佳实践

- 编译期生成实现，调试友好；不要忽略 MapStruct 编译告警（字段未映射）
- 转换器单测：覆盖字段映射完整性（`unmappedTargetPolicy` 可设 ERROR 强制不漏字段）

```java
@Mapper(componentModel = "spring",
        unmappedTargetPolicy = ReportingPolicy.ERROR)
public interface OrderConverter {
```

- 大量同结构转换用 List 转换方法，避免循环
- DTO → Entity 更新场景：`updateEntity(OrderUpdateDTO updateInfo, @MappingTarget Order order)` 原地更新

## 自检清单

- [ ] 转换用 MapStruct，无手写 get/set 散落
- [ ] 不同名字段 @Mapping 显式声明
- [ ] 枚举/金额等特殊类型已处理
- [ ] 无业务逻辑在转换器
- [ ] 编译无未映射告警（或已处理）
- [ ] 集合转换用 List 方法
