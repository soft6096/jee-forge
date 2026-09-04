# Validator 规范 (Custom Validator Standards)

## 适用范围

生成自定义 Bean Validation 校验器时加载。定义校验器结构、注册、与 DTO 校验注解配合。**本文件同时是「校验 message 写法」的总规则源**（DTO/Controller 校验注解的 message 规则见下方「0. message 规则（总则，所有校验注解适用）」）。

## 强制规则

### 0. message 规则（总则，所有校验注解适用——@NotBlank/@NotNull/@Size/@Pattern/自定义注解 message 一律遵守）

**message 必须可读、且能指到具体字段与具体原因**，禁止"参数不合法"式**无字段语义的笼统文案**。

**① 禁止（黑名单，check-standards 可 grep 机械核对）**——message 不得为以下"笼统前缀 + 笼统结论"组合（含标点变体"参数不合法！"等；黑名单以**通用形态**判定：message 不含任何业务字段语义、仅由笼统词构成即违规，不限于穷举词表）：

```java
// ❌ 笼统文案（无字段语义，禁）
@NotBlank(message = "参数不合法")
@NotNull(message = "参数错误")
@NotBlank(message = "参数非法")
@NotBlank(message = "数据不合法")
@NotBlank(message = "输入有误")
@Pattern(regexp = "...", message = "参数无效")
```

**通用判定形态**（grep 可查）：`message = "…"` 的值若**不含业务字段名/业务语义词**，仅由 `参数/数据/输入/请求/字段/内容/信息` × `不合法/错误/非法/无效/有误/不正确/格式不对` 等笼统词构成 → ❌ 不合规。

**② 正向要求（编写指引）**——message 含**两要素**：
- **要素一：业务字段名**（中文业务名，如"手机号/订单号/数量/金额"，非英文变量名）
- **要素二：具体校验原因**（如"不能为空 / 格式不正确 / 必须大于0 / 长度不能超过64"）

```java
// ✅ 具体（字段语义 + 具体原因）
@NotBlank(message = "手机号不能为空")            // 谁（手机号）+ 错哪（不能为空）
@Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
@NotNull(message = "订单号不能为空")
@Min(value = 1, message = "数量必须大于0")
@Max(value = 999, message = "数量不能超过999")
@Size(max = 64, message = "商品名称长度不能超过64")
@DecimalMin(value = "0.01", message = "金额必须大于0")
@Digits(integer = 10, fraction = 2, message = "金额最多2位小数")
```

> [!IMPORTANT] 为什么 message 必须具体
> 校验失败信息会**原样返回给前端/用户**。"参数不合法"让用户无法定位改哪里，也让联调排查困难。message 具体化（"手机号格式不正确"）让用户一眼知道哪个字段错、错在哪——这是接口可用性的一部分，不是可省略的细节。

### 1. 校验器定位

- 自定义校验器处理框架校验覆盖不了的场景：跨字段、正则、业务字典、数值范围规则
- 结构：注解（`@Constraint`）+ 实现（`ConstraintValidator`）

```java
@Target({ElementType.FIELD, ElementType.PARAMETER})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = MobileValidator.class)
public @interface Mobile {

    String message() default "手机号格式不正确";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};
}
```

```java
public class MobileValidator implements ConstraintValidator<Mobile, String> {

    private static final Pattern MOBILE_PATTERN =
            Pattern.compile("^1[3-9]\\d{9}$");

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        if (value == null || value.isBlank()) {
            return true;  // 空值由 @NotBlank 负责，校验器不重复报错
        }
        return MOBILE_PATTERN.matcher(value).matches();
    }
}
```

### 2. 空值约定

- 校验器内 null 返回 true（null 合法性由 `@NotNull` 声明），避免重复校验职责
- 正则 Pattern 编译为 static final，禁止方法内重复编译

### 3. 注解设计

- `message` 提供默认文案，使用处可覆盖
- `groups` / `payload` 必须声明（Bean Validation 规范要求）
- 校验器尽量无状态（可复用实例），不持有线程不安全字段

### 4. 跨字段校验

- 跨字段校验用类级注解（`ElementType.TYPE`），如时间段 start ≤ end

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = TimeRangeValidator.class)
public @interface TimeRange {
    String message() default "开始时间不能晚于结束时间";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}

// 使用
@TimeRange
@Data
public class OrderQueryDTO {
    private LocalDateTime startTime;
    private LocalDateTime endTime;
}
```

## 反例 / 正例

```java
// 反例：校验逻辑散落 Service + 空值重复报错
// Service 里：
if (!mobile.matches("^1[3-9]\\d{9}$")) {
    throw new BusinessException("手机号格式不正确");
}
// 每个接口重复一遍

// 正例
// DTO 字段：
@Mobile
private String mobile;
// 框架统一校验，Service 不感知
```

## 最佳实践

- 先查框架自带注解能否覆盖（@Pattern、@Size、@Email），不够再自定义
- 常用校验（手机号、身份证、金额范围）沉淀团队公共校验注解，避免各处重复写
- 校验失败信息面向用户：`"手机号格式不正确"`，不抛内部技术描述
- 批量校验失败：分组校验（group）控制更新/新增不同约束

## 自检清单

- [ ] **校验 message 具体（总则 0）**：每个校验注解 message 含"业务字段名 + 具体原因"（如"手机号格式不正确"）；无"参数不合法/参数错误/数据不合法/输入有误"式无字段语义笼统文案
- [ ] 注解含 @Constraint + message/groups/payload
- [ ] null 返回 true，不重复 @NotNull 职责
- [ ] Pattern 为 static final
- [ ] 校验器无状态
- [ ] 跨字段校验用类级注解
- [ ] 团队公共校验器优先复用
