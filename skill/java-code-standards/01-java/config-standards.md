# Config 规范 (Configuration Class Standards)

## 适用范围

生成 Spring 配置类时加载。定义配置类结构、Bean 注册、条件装配、外部化配置。

## 强制规则

### 1. 类结构

- `@Configuration` + 类注释说明配置职责（负责哪部分能力）
- 配置类按职责拆分，禁止一个大类塞所有 Bean

```java
@Configuration
public class MybatisPlusConfig {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        PaginationInnerInterceptor pagination = new PaginationInnerInterceptor(DbType.MYSQL);
        pagination.setMaxLimit(100L);
        interceptor.addInnerInterceptor(pagination);
        interceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());
        return interceptor;
    }
}
```

### 2. Bean 注册

- 明确类型 + 有含义的 beanName（方法名即 beanName，命名动词 + 名词：`redisTemplate`、`paginationInterceptor`）
- `@Bean` 方法返回具体类型，不返回 Object；带初始化参数优先，少用 `@Value` 注入复杂对象
- 同名 Bean 冲突：`@Qualifier` 显式指定，不靠 `@Primary` 掩盖问题

### 3. 条件装配

- 按环境/存在性装配用 `@ConditionalOnProperty` / `@ConditionalOnMissingBean` / `@Profile`
- 环境差异配置（dev/prod）用 application-{env}.yml，不写 if 分支在代码里

```java
@Configuration
@ConditionalOnProperty(name = "app.feature.xx.enabled", havingValue = "true")
public class XxFeatureConfig {
    // 特性开关关闭时不装配
}
```

### 4. 外部化配置

- 配置值走 `application.yml` + `@ConfigurationProperties` 绑定类，不用散落 `@Value`
- 敏感配置（密码、密钥）走环境变量/配置中心，不硬编码、不提交仓库

```java
@Data
@ConfigurationProperties(prefix = "app.order")
@Component
public class OrderProperties {
    /** 订单超时时间，分钟 */
    private Integer timeoutMinutes = 30;
    /** 单用户最大未支付订单数 */
    private Integer maxPendingOrders = 10;
}
```

### 5. 线程池配置

- 自定义线程池显式命名（`ThreadFactory` 带业务名前缀），便于排查

```java
ThreadFactory factory = new ThreadFactoryBuilder()
        .setNameFormat("order-notify-pool-%d").build();
```

- 线程池参数（核心/最大/队列）走配置，不硬编码

## 反例 / 正例

```java
// 反例：配置散落 + 魔法值 + @Value 满天飞
@Configuration
public class AppConfig {
    @Value("${order.timeout:30}")
    private int timeout;
    @Value("${order.max:10}")
    private int maxPending;

    @Bean
    public ExecutorService executor() {
        return Executors.newFixedThreadPool(10);  // 无命名线程工厂，无配置化
    }
}
```

## 最佳实践

- 拦截器/过滤器/切面注册在独立 `WebConfig`（或 `WebMvcConfigurer` 实现类）
- 异步/定时/缓存各自独立配置类，开启对应 `@Enable*` 注解
- 配置类避免复杂初始化逻辑；需要时用 `InitializingBean` 校验配置合法性（启动即失败，不运行时炸）

## 自检清单

- [ ] 配置类职责单一
- [ ] Bean 方法名有意义，返回具体类型
- [ ] 环境差异用 Profile/Conditional
- [ ] 配置走 @ConfigurationProperties，无散落 @Value
- [ ] 无硬编码密钥/密码
- [ ] 线程池命名 + 参数配置化
