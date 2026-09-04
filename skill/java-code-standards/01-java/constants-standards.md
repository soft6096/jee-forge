# 常量规范 (Constants Standards)

## 适用范围

生成常量类时加载。定义常量组织、命名、作用域。

## 强制规则

### 1. 常量组织

- 按业务域分组常量类：`OrderConstants`、`UserConstants`、`CacheConstants`
- 大类再细分内部静态类或按前缀分组
- ❌ 一个 `Constants` 类塞所有模块常量（维护灾难）

```java
public final class OrderConstants {

    private OrderConstants() {
    }

    /** 默认订单超时时间，分钟 */
    public static final int DEFAULT_TIMEOUT_MINUTES = 30;

    /** 单用户最大未支付订单数 */
    public static final int MAX_PENDING_ORDERS = 10;

    /** 订单号前缀 */
    public static final String ORDER_NO_PREFIX = "ORD";

    public static final class Cache {
        public static final String ORDER_KEY_PREFIX = "order:";
        public static final long ORDER_CACHE_TTL_SECONDS = 1800L;
        private Cache() {
        }
    }
}
```

- 常量类 `final` + `private` 构造器（防实例化/继承）

### 2. 命名

- 全大写 + 下划线：`MAX_PENDING_ORDERS`
- 含单位的常量名或注释标注单位：`TIMEOUT_MINUTES`、`TTL_SECONDS`
- 前缀命名用于缓存 key：`ORDER_KEY_PREFIX = "order:"`

### 3. 作用域

- 常量尽量就近定义：仅类内使用放 `private static final` 于该类；跨类才提公共常量类
- ❌ 全局常量类堆一切

```java
// 仅本类使用 → 不建常量类
public class OrderService {
    private static final int MAX_RETRY_TIMES = 3;
}
```

- 配置值优先 `application.yml` + `@ConfigurationProperties`（可调），业务不可调规则才用代码常量

### 4. 禁止事项

- ❌ 魔法值直接出现（`if (x > 30)`）——提常量并注释含义
- ❌ 常量类内放可变静态字段
- ❌ 重复定义相同常量（如两处 `"order:"` 前缀）

## 反例 / 正例

```java
// 反例
public class Constants {            // 万金油类
    public static final String A = "a";
    public static final String B = "b";
    // 500 行...
}

// 业务代码
if (user.getAge() > 18) { }         // 魔法值
redis.set("order:" + orderId, ...); // 前缀散落

// 正例
public final class OrderConstants {
    private OrderConstants() {
    }
    public static final int ADULT_AGE = 18;
    public static final String CACHE_KEY_PREFIX = "order:";
}
```

## 最佳实践

- 缓存 key 常量集中，避免多处拼串导致 key 不一致
- 跨模块共享常量放 common 模块，模块私有常量放模块内
- 常量变更走配置中心时，代码常量 → 配置属性迁移，注释保留默认值

## 自检清单

- [ ] 按业务域分组，无万金油 Constants 类
- [ ] 常量类 final + 私有构造器
- [ ] 全大写 + 下划线，单位明确
- [ ] 无魔法值散落
- [ ] 仅本类用常量未外提
- [ ] 无重复常量定义
