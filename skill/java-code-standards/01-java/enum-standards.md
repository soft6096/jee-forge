# 枚举规范 (Enum Standards)

## 适用范围

生成枚举类时加载。定义枚举用途、结构、状态机与数据库映射。

## 强制规则

### 1. 枚举定位

- 固定有限集合用枚举：状态、类型、渠道、角色
- ❌ 不把可配置数据（会变、走配置中心的字典）写死为枚举
- ❌ 不用字符串散落比较业务状态

### 2. 结构规范

- 枚举字段：编码（int/String）+ 描述（desc）+ 需要的业务属性
- 统一提供：`of(code)` 按编码查找、`contains/isValid` 校验方法

```java
public enum OrderStatusEnum {

    PENDING_PAY(10, "待支付"),
    PAID(20, "已支付"),
    SHIPPED(30, "已发货"),
    COMPLETED(40, "已完成"),
    CANCELED(90, "已取消");

    private final Integer code;
    private final String desc;

    OrderStatusEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public Integer getCode() { return code; }
    public String getDesc() { return desc; }

    public static OrderStatusEnum of(Integer code) {
        if (code == null) {
            return null;
        }
        for (OrderStatusEnum status : values()) {
            if (status.code.equals(code)) {
                return status;
            }
        }
        throw new IllegalArgumentException("unknown order status: " + code);
    }
}
```

- `of` 对未知编码抛异常（快速失败）或返回 null 团队统一；未知编码提示明确
- 枚举值命名全大写 + 下划线，语义完整：`PENDING_PAY` 非 `P1`

### 3. 状态机

- 状态流转定义在枚举内（允许的下一状态），禁止散落 if 判断

```java
public enum OrderStatusEnum {
    // 前置声明略
    private final Set<OrderStatusEnum> allowedNext;

    static {
        PENDING_PAY.allowedNext = Set.of(PAID, CANCELED);
        PAID.allowedNext = Set.of(SHIPPED, CANCELED);
        SHIPPED.allowedNext = Set.of(COMPLETED);
        COMPLETED.allowedNext = Set.of();
        CANCELED.allowedNext = Set.of();
    }

    public boolean canTransitionTo(OrderStatusEnum target) {
        return allowedNext.contains(target);
    }
}

// 使用
if (!current.canTransitionTo(target)) {
    throw new BusinessException(ErrorCode.ORDER_STATUS_ILLEGAL,
            "订单状态不允许从" + current.getDesc() + "流转到" + target.getDesc());
}
```

### 4. 数据库映射

- 数据库存枚举 `code`（int），不存 name（重命名枚举即破坏历史数据）、不存 desc
- MyBatis-Plus 枚举处理器：`@EnumValue` 注解映射 code

```java
public enum OrderStatusEnum {
    @EnumValue
    PENDING_PAY(10, "待支付"),
    // ...
}
```

## 反例 / 正例

```java
// 反例：魔法值散落 + 状态流转不可控
if (order.getStatus() == 10 && action.equals("pay")) {
    order.setStatus(20);
} else if (order.getStatus() == 20 && action.equals("ship")) {
    order.setStatus(30);
}
// 另一处又写一遍，遗漏 CANCELED 场景

// 正例
OrderStatusEnum current = OrderStatusEnum.of(order.getStatus());
OrderStatusEnum target = OrderStatusEnum.of(OrderActionEnum.of(action).getTargetCode());
if (!current.canTransitionTo(target)) {
    throw new BusinessException(ErrorCode.ORDER_STATUS_ILLEGAL, "状态流转不允许");
}
```

## 最佳实践

- 枚举内放与自身强相关的方法（转换、校验），不放通用逻辑
- 描述文案变更不重建枚举，文案统一走字典/国际化时枚举只存 code
- 序列化：VO 出参可带 code+desc，前端按需展示

## 自检清单

- [ ] 固定集合用枚举，可变配置不用枚举
- [ ] 字段含 code + desc
- [ ] of/isValid 统一提供
- [ ] 状态流转收敛在枚举，无散落 if
- [ ] DB 存 code，@EnumValue 映射
- [ ] 值命名全大写语义完整
