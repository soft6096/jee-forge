# Utils 规范 (Utility Class Standards)

## 适用范围

生成工具类时加载。定义静态工具类的结构、命名、与实例服务的边界。

## 强制规则

### 1. 类结构

- 工具类 = `final` 类 + `private` 构造器 + 全 `static` 方法

```java
public final class MaskUtil {

    private MaskUtil() {
    }

    /** 手机号脱敏：138****1234 */
    public static String maskMobile(String mobile) {
        if (StringUtils.isBlank(mobile) || mobile.length() < 7) {
            return mobile;
        }
        return mobile.substring(0, 3) + "****" + mobile.substring(mobile.length() - 4);
    }
}
```

- ❌ 无 final、无私有构造器（可被实例化/继承）
- ❌ 工具类持有状态（static 可变字段）

### 2. 命名

- `XxxUtil` / `XxxUtils` / `XxxHelper`，团队统一一种
- 方法名动词：`mask`、`convert`、`buildOrderNo`、`isValidIdCard`

### 3. 边界

- 工具类只做**无状态纯函数**：输入 → 输出，无 IO、无 Spring 依赖
- ❌ 工具类里 new 业务对象、调 Mapper、读配置
- 有依赖的服务逻辑（Redis、DB）放 Service，不放工具类
- 优先复用成熟工具（Spring `StringUtils`、Hutool），不重复造轮子；团队统一依赖库

### 4. 输入防御

- 入参判空（null/blank）返回安全默认值或抛 `IllegalArgumentException`
- 参数校验失败异常信息明确

```java
public static String buildOrderNo(Long userId) {
    if (userId == null) {
        throw new IllegalArgumentException("userId must not be null");
    }
    return "ORD" + DateUtil.format(LocalDateTime.now(), "yyyyMMddHHmmss")
            + String.format("%06d", userId % 1000000);
}
```

## 反例 / 正例

```java
// 反例：有状态 + 可实例化 + 混入服务逻辑
public class DateUtil {
    public static String pattern = "yyyy-MM-dd";  // 静态可变状态
    private RedisTemplate<String, String> redis;  // 工具类依赖注入

    public String format(LocalDateTime t) { ... }
}
```

## 最佳实践

- 工具方法幂等、无副作用，便于单测
- 高频工具（脱敏、金额、时间格式）集中管理，避免各写各的
- 与业务强相关（如订单号规则）放领域服务，不放通用工具
- 每个工具类配单元测试（边界输入：null、空串、超长）

## 自检清单

- [ ] final 类 + private 构造器
- [ ] 无状态，无 Spring 依赖
- [ ] 入参判空
- [ ] 无重复造轮子（复用团队工具库）
- [ ] 纯函数，可单测
