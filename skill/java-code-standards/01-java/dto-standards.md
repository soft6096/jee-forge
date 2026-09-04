# DTO 规范 (DTO Standards)

## 适用范围

生成数据传输对象（入参/查询条件/内部传输）时加载。

## 强制规则

### 1. 类定位

- DTO 承载**入站**数据：请求参数、查询条件、跨服务传输
- 命名：`XxxDTO`，请求场景可细分 `XxxCreateDTO` / `XxxUpdateDTO` / `XxxQueryDTO`
- ❌ DTO 不承载数据库概念（不引用 Entity、不写 SQL 条件映射细节）

```java
@Data
public class OrderQueryDTO {

    @NotNull(message = "用户ID不能为空")
    private Long userId;

    private Integer status;

    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime startTime;

    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime endTime;

    private Integer pageNum = 1;

    private Integer pageSize = 10;
}
```

### 2. 校验规则

- 入参 DTO 字段加 Bean Validation 注解（见 controller 规范）
- 查询 DTO 校验放宽：可选条件不强制，格式校验（时间格式、枚举值）保留

### 3. 字段规则

- 只放当前场景需要的字段，不整表拷贝
- 字段类型与业务语义一致：金额 BigDecimal、时间 LocalDateTime
- 有默认值的字段显式初始化，避免空指针
- 分页字段继承统一 `PageQuery` 基类（见 controller 规范），不重复声明

### 4. 可变性

- 使用 Lombok `@Data` 简化（团队统一）；内部流转 DTO 可用 `@Value` 不可变
- 不继承 Entity，不实现 Entity 相关接口

## 反例 / 正例

```java
// 反例：DTO 混入出参字段 + 无校验 + 类型含糊
public class OrderDTO {
    private String orderId;      // 应为 Long
    private String amount;       // 应为 BigDecimal
    private String statusText;   // 出参概念混入入参
    private String remark;
    private String remark2;      // 无意义字段
}

// 正例
public class OrderCreateDTO {
    @NotNull(message = "商品ID不能为空")
    private Long skuId;
    @Min(value = 1, message = "数量至少1")
    private Integer quantity;
    @DecimalMin(value = "0.01", message = "金额必须大于0")
    private BigDecimal amount;
}
```

## 最佳实践

- 增/改分离：`CreateDTO` 与 `UpdateDTO` 分开，字段约束不同（update 允许部分字段空）
- 查询 DTO 直接作为 Wrapper 构造条件，字段命名与 Entity 属性对齐便于 Lambda 引用
- 跨服务 DTO 序列化稳定：不轻易改字段名/类型，加字段向后兼容
- 时间范围校验（start ≤ end）在 Service 层做跨字段校验

## 自检清单

- [ ] 命名 XxxDTO / XxxQueryDTO 等，语义明确
- [ ] 入参字段有校验注解
- [ ] 金额 BigDecimal、时间 LocalDateTime
- [ ] 无出参概念（statusText 等）
- [ ] 无冗余无用字段
- [ ] 默认值已初始化
- [ ] 不继承 Entity
