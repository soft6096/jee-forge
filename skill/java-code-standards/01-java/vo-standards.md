# VO 规范 (VO Standards)

## 适用范围

生成视图对象（出参）时加载。定义出参组装、字段裁剪、脱敏、与 Entity/DTO 边界。

## 强制规则

### 1. 类定位

- VO 承载**出站**数据：接口响应、页面展示所需字段
- 命名：`XxxVO`；分页出参 `PageResult<XxxVO>`
- ❌ VO 不包含 Entity 全字段，只含前端需要字段
- ❌ VO 不包含敏感数据（密码、token），需脱敏

```java
@Data
public class OrderVO {

    private Long id;

    private String orderNo;

    /** 状态编码，前端映射文案 */
    private Integer status;

    /** 状态文案，服务端填充（或前端按编码映射） */
    private String statusText;

    private BigDecimal amount;

    /** 手机号脱敏：138****1234 */
    private String mobileMasked;

    private LocalDateTime createTime;
}
```

### 2. 组装规则

- Service 层组装 VO，Controller 不拼装
- 转换用 MapStruct（见 converter 规范）或显式构造，禁止手写一堆 get/set 散落各处
- 枚举 → 文案映射统一在枚举/转换器处理，不散落 if

```java
// 正例：枚举集中映射
orderVO.setStatusText(OrderStatusEnum.of(order.getStatus()).getDesc());
```

### 3. 字段规则

- 只放展示字段，列表与详情可拆两个 VO（`OrderListVO` / `OrderDetailVO`），列表不含大字段
- 时间统一格式由序列化配置（`yyyy-MM-dd HH:mm:ss`），VO 不存字符串时间
- 金额保留 BigDecimal 输出，前端统一格式化；单位注释说明

### 4. 序列化

- 不返回 null 大字段；空列表返回空集合，不返回 null（构造时初始化 `new ArrayList<>()`）
- 敏感字段（手机号、身份证）在 VO 层脱敏输出，字段命名 `xxxMasked` 或统一脱敏配置

## 反例 / 正例

```java
// 反例：VO = Entity 全字段 + 密码字段 + 无脱敏
public class UserVO {
    private Long id;
    private String username;
    private String password;    // 敏感，泄漏
    private String mobile;      // 未脱敏
    private String remark;
    private String extra1;      // 冗余
}

// 正例
public class UserVO {
    private Long id;
    private String username;
    private String mobileMasked;   // 138****1234
}
```

## 最佳实践

- 列表 VO 与详情 VO 分离，列表裁剪列减少传输
- 聚合展示字段（如订单含商品数）由 Service 一次性组装，禁止前端循环查询
- 版本兼容：VO 字段只增不改删，前端旧版本兼容
- 命名统一：`amount` 输出元还是分，全项目一致并在字段注释写明

## 性能优化建议

- 大列表响应：VO 只含必需字段（减少序列化与网络传输）
- 大批量组装：批量查字典/关联数据后内存映射，避免 N+1

## 自检清单

- [ ] 只含前端需要字段，无 Entity 全量拷贝
- [ ] 无敏感字段泄漏，敏感字段已脱敏
- [ ] 枚举文案集中映射
- [ ] 列表/详情已按需拆分
- [ ] 空列表返回空集合
- [ ] 组装在 Service 层
