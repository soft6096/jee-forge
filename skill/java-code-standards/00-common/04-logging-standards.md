# 日志规范 (Logging Standards)

## 适用范围

生成任意 Java 代码前必读。规范日志框架使用、级别选择、格式与内容。

## 强制规则

### 1. 框架与声明

- 统一 SLF4J API，具体实现默认 **Logback**（`spring-boot-starter-logging` 自带，随 `spring-boot-starter-web` 传递引入，无需额外加依赖）
- **全类使用 `@Slf4j`**（Lombok）：Controller / Service / ServiceImpl / Job / Listener / MQ 消费类一律声明，禁止类内散落 `private static final Logger` 混用
- 禁止直接使用 `System.out.println`、`System.err.println` 输出日志
- 若改用 Log4j2：`spring-boot-starter` 需排除 `spring-boot-starter-logging` 并显式引入 Log4j2（见 build-standards 依赖规范），团队统一选一，禁止 Logback/Log4j2 并存

```java
// 正例：Lombok 或手动声明
@Slf4j
public class OrderService {
    // 直接使用 log 对象
}
```

### 1.5 Logback 配置（logback-spring.xml，强制）

- **项目必须提供 `resources/logback-spring.xml`**，禁止依赖 Spring Boot 默认日志配置裸奔（默认只打控制台、无滚动、级别不可按环境区分）
- 模板见 `04-templates/logback-spring.xml`，必含三件套：

| 组件 | 要求 |
|---|---|
| 控制台 Appender（CONSOLE） | dev 环境全量输出（含 DEBUG），格式化含时间/级别/线程/logger/消息 |
| 滚动文件 Appender（FILE） | 按天滚动 + 大小触发 + 保留天数（如 30 天）+ 单文件上限（如 100MB），生产日志必须落盘 |
| 级别按环境分离 | `<springProfile name="dev">` 开 DEBUG，online 只 INFO/WARN/ERROR；错误单独滚到 error 文件可选 |

```xml
<!-- 最小骨架：控制台 + 滚动文件 + 环境级 level（完整模板见 04-templates/logback-spring.xml） -->
<configuration>
    <springProfile name="dev">
        <logger name="com.example" level="DEBUG"/>
    </springProfile>
    <springProfile name="online">
        <logger name="com.example" level="INFO"/>
    </springProfile>
    <!-- CONSOLE / FILE appender ... -->
</configuration>
```

- `application.yml` 只配 `logging.level.*` 覆盖与 `logging.file` 无关项；Appender 结构一律在 logback-spring.xml（见 application-config-standards.md）
- 文件名用 `logback-spring.xml` 而非 `logback.xml`（`-spring` 后缀才支持 `<springProfile>` 环境切换）

### 1.6 方法级日志覆盖（强制——每个业务方法必须有日志，无豁免分层）

> **为什么**：日志是"证据"——线上出问题要靠日志定位"这个请求发生了什么、走到哪一步、为什么失败"。方法体零日志 = 该方法的执行轨迹完全不可追踪。**日志必须覆盖到方法级，不是只打"关键节点"**：Controller/Service/ServiceImpl/Job/Listener 的每个业务方法（含抽取出来的 private 辅助方法）方法体内部必须有日志。

**覆盖规则（无豁免分层，层层都要有）**：

| 层 | 强制要求 | 示例 |
| :--- | :--- | :--- |
| 类 | 全类 `@Slf4j` | `@Slf4j public class XxxServiceImpl` |
| **每个业务方法（public + private 抽取方法）** | **方法体内 ≥1 条 INFO/WARN/ERROR 业务日志**（`log.debug` **不算覆盖**——线上默认不输出，打 debug = 线上看不到，仅可作补充）：入口记入参摘要（方法名 + 关键入参字段）/ 关键分支 / 结果返回前 | `log.info("queryOrderList start, userId={}, status={}", userId, status);` ... `log.info("queryOrderList done, size={}", list.size());` |
| 方法内 ≥2 个业务阶段 | 每个阶段关键点有 INFO 日志 | 校验后 / 调用外部前 / 状态变更后 |
| 大段逻辑（≥10 行无 INFO/WARN/ERROR） | **❌ 违规**——大段代码执行到哪一步不可知 | — |
| 异常处 | ERROR 带堆栈 | `log.error("createOrder failed, orderId={}", orderId, e);` |

> [!IMPORTANT] debug 不算业务日志（防"打条 debug 冒充覆盖"）
> **方法级日志的"≥1 条"指的是 INFO/WARN/ERROR**——`log.debug` 在 online 环境默认不输出，打 debug 等于线上零日志。判定规则：**方法体内无任何 INFO/WARN/ERROR 日志（即使有 debug）→ 视为零日志 ❌**。debug 仅允许作为 INFO 之外的补充（如循环内明细），不能替代业务日志。

**豁免（只限以下，须注明原因，不静默跳过）**：
- 纯 getter / setter / 单行透传（`return mapper.selectById(id);`）→ 可无日志（但方法 Javadoc 仍必须有）
- 基类/公共组件的模板方法内已被子类日志覆盖的关键路径 → 可不重复打

**反例（两种都要抓）**：

```java
// ❌ 反例 1：方法体一堆逻辑，一条日志都没有
public PageResult<OrderVO> queryOrderList(OrderQueryDTO query) {
    SysUser user = userMapper.selectById(query.getUserId());
    if (user == null) { throw new BusinessException(...); }  // 异常没打日志？
    List<Order> list = orderMapper.selectByCondition(...);    // 查了啥？
    List<OrderVO> voList = list.stream().map(this::buildVO).toList();
    return PageResult.of(voList);                              // 返回了啥？
}

// ❌ 反例 2：开头一条 debug 敷衍，中间 20+ 行关键逻辑零 INFO/WARN/ERROR——"半覆盖"漏网形态
private List<OrderVO> buildBuyNowItems(AppOrderConfirmReqDTO reqDTO) {
    log.debug("读取立即购买商品项，itemCount={}", ...);   // debug 线上不输出，不算覆盖
    if (reqDTO.getBuyNowItemList() == null || ...) { throw new BusinessException(...); }
    List<String> spuCodes = reqDTO.getBuyNowItemList().stream()...collect(...);  // 大量查库/组装逻辑
    Map<...> productMap = mapper.selectList(...)...;                             // 中间全程无 INFO
    for (...) { ... items.add(item); }                                           // 执行到哪一步不可知
    return items;
}

// ✅ 正例：入口 + 关键分支 + 结果 都有 INFO/WARN/ERROR
public PageResult<OrderVO> queryOrderList(OrderQueryDTO query) {
    log.info("queryOrderList start, userId={}, status={}", query.getUserId(), query.getStatus());
    SysUser user = userMapper.selectById(query.getUserId());
    if (user == null) {
        log.warn("queryOrderList user not found, userId={}", query.getUserId());
        throw new BusinessException(...);
    }
    List<Order> list = orderMapper.selectByCondition(query);
    log.info("queryOrderList found, userId={}, count={}", query.getUserId(), list.size());
    List<OrderVO> voList = list.stream().map(this::buildVO).toList();
    log.info("queryOrderList done, userId={}, voCount={}", query.getUserId(), voList.size());
    return PageResult.of(voList);
}
```

> 抽取出来的 private 辅助方法（buildXxx / convertXxx / validateXxx 等）**同样要方法内 ≥1 条 INFO/WARN/ERROR 日志**（debug 不算）——它们是 Controller/ServiceImpl 大方法被抽出来的执行块，零 INFO = 这一段执行过程线上不可见。与代码注释同规则：**注释/日志都要求覆盖到所有代码，包括抽取方法**（见 comment-standards 全量注释 + 本规范方法级日志）。

### 2. 日志级别选择

| 级别 | 用途 | 示例 |
|---|---|---|
| ERROR | 系统无法继续/业务失败需告警 | 数据库异常、第三方调用失败、业务处理失败 |
| WARN | 可继续但需关注 | 参数异常被降级处理、重试成功、缓存穿透回源 |
| INFO | 关键业务节点 | 请求入口、订单创建/状态变更、定时任务完成 |
| DEBUG | 调试细节 | 中间结果、循环内数据 |
| TRACE | 极细追踪 | 少见，默认关闭 |

- 线上默认 INFO，DEBUG/TRACE 不输出业务关键信息（丢失不可恢复）
- 业务关键节点用 INFO，不用 DEBUG

### 3. 格式规范

- 使用占位符 `{}`，禁止字符串拼接

```java
// 反例
log.info("order created, orderId=" + orderId + ", userId=" + userId);

// 正例
log.info("order created, orderId={}, userId={}", orderId, userId);
```

- 占位符避免字符串**拼接**开销（不拼成字符串）；但**参数表达式仍会先求值**（Java 方法参数 eager 求值）——`log.info("...{}", obj.getId())` 中 `obj.getId()` 在调用前必然执行，与日志级别是否输出无关。**禁止把可能 NPE 的调用写进日志参数**（见 §6「日志参数求值安全」）
- 占位符参数传**已判空/安全取值**的变量或字面量；方法调用、链式取值先算到局部变量再传入

### 4. 异常日志

- 异常对象作为最后一个参数传入，保留堆栈

```java
// 反例：只记 message，丢堆栈
log.error("order submit failed: {}", e.getMessage());

// 正例
log.error("order submit failed, orderId={}", orderId, e);
```

- 捕获异常必须记录堆栈；向上抛出时可只在上抛点记录一次，避免重复打
- 日志信息写业务含义，不写框架堆栈复制

### 5. 日志内容要求

- 关键日志带上下文 ID：订单号、用户 ID、traceId
- ❌ 不记录敏感信息：密码、token、身份证、手机号明文（脱敏后记）
- 日志长度限制：大对象（如整表数据）只记关键字段

```java
// 正例：脱敏
log.info("user login, userId={}, mobile={}", userId, MaskUtil.mask(mobile));
```

### 6. 日志参数求值安全（防 NPE，强制）

> **为什么**：Java 方法参数 **eager 求值**——`log.debug("...{}", obj.getId())` 无论 debug 是否开启输出，`obj.getId()` 在调用前已执行。若调用者为 null、链式取值中间环为 null、集合空/越界 → **日志语句本身先 NPE**，判空写在其后也救不了（日志行先炸，代码走不到判空）。

**禁止在日志参数中写可能 NPE 的表达式**（5 类高危形态）：

| # | 高危形态 | ❌ 反例 | ✅ 正例 |
| :---: | :--- | :--- | :--- |
| 1 | **判空之前取值** | `log.debug("...parentId={}", parentCategory.getId()); if (parentCategory == null) return;` —— 日志行先 NPE，走不到判空 | 先判空再打，或判空后把值取到局部变量：`if (parentCategory == null) { log.warn("parentCategory is null, categoryId={}", categoryId); return; } log.debug("...parentId={}", parentCategory.getId());` |
| 2 | **链式取值**（任一环可能 null） | `log.info("...{}", order.getUser().getName())`（order 或 getUser() 为 null → NPE） | 拆开判空：`User u = order == null ? null : order.getUser(); log.info("...userId={}", u == null ? null : u.getId());` 或只打已判空的首层：`log.info("...orderId={}", order == null ? null : order.getId())` |
| 3 | **集合空/越界** | `log.info("...size={}, first={}", list.size(), list.get(0))`（空 list → get(0) 越界） | 先判非空再取：`log.info("...size={}", list == null ? 0 : list.size()); if (list != null && !list.isEmpty()) { log.info("...firstId={}", list.get(0).getId()); }` |
| 4 | **Map 取值后调用** | `log.info("...{}", map.get(key).getName())`（value 为 null → NPE） | 先取再判：`User u = map.get(key); log.info("...{}", u == null ? null : u.getName());` |
| 5 | **debug 昂贵参数**无开关 | `log.debug("...{}", JsonUtil.toJson(order))`（级别关也白白序列化；含 null 链同样炸） | `if (log.isDebugEnabled()) { log.debug("...{}", JsonUtil.toJson(order)); }`（开关内参数仅在开启时求值） |

> [!IMPORTANT] 对象本身 null 是安全的，危险的是"调用" 
> `log.info("user={}", user)`（user 为 null → 打 "null"，**安全**）；`log.info("userId={}", user.getId())`（user 为 null → **NPE**）。规则红线：**日志参数里不写方法调用/链式取值/集合索引**；要打就传**已判空后取到的局部变量**，或先判空、判空分支先打/return 再打。

**通用写法模板**：

```java
// ✅ 安全模式 A：先判空，判空分支先记录并退出，再打正常日志
if (parentCategory == null) {
    log.warn("validateCategory skip, parentCategory is null, categoryId={}", categoryId);  // 只打已判空的参数
    return;
}
log.debug("validateCategory path, categoryId={}, parentId={}", existingCategory.getId(), parentCategory.getId());  // 此刻调用者已确认非 null

// ✅ 安全模式 B：null 安全取值到局部变量后再打（避免三目污染日志行）
Long parentId = parentCategory == null ? null : parentCategory.getId();
log.debug("validateCategory path, categoryId={}, parentId={}", existingCategory.getId(), parentId);
```

## 反例 / 正例

```java
// 反例
System.out.println("创建订单：" + order);
log.info("查询订单");  // 无上下文，无法定位

// 正例
log.info("order create start, orderId={}, userId={}", orderId, userId);
```

## 最佳实践

- 请求入口（Controller/网关）记录入参摘要 + 耗时，出口记录结果
- 定时任务开始/结束/失败各记一条，含批次信息
- 日志上下文：MDC 放入 traceId，链路追踪贯通调用链
- 高频循环内避免 INFO（改 DEBUG 或聚合统计）
- 日志内容与异常体系一致：ERROR 日志与 `SystemException` 抛出点一一对应

## 性能优化建议

- 使用占位符而非拼接（已列强制）
- 判断 `log.isDebugEnabled()`：DEBUG 参数构造昂贵时（如序列化对象）

```java
// 正例
if (log.isDebugEnabled()) {
    log.debug("order detail: {}", JsonUtil.toJson(order));
}
```

- 异步日志（AsyncAppender）降低 I/O 阻塞，注意丢日志风险与背压
- 避免循环内打日志：10 万次循环打 10 万条

## 自检清单

- [ ] 使用 SLF4J，无 System.out 日志
- [ ] 全类 @Slf4j（Controller/Service/Job/Listener 一律带），无散落 Logger 声明
- [ ] logback-spring.xml 已提供：控制台 + 滚动文件 + 环境级 level（非默认配置裸奔）
- [ ] **每个业务方法（public + private 抽取方法）方法体内 ≥1 条 INFO/WARN/ERROR 日志**（debug 不算覆盖）——大段逻辑（≥10 行）无 INFO/WARN/ERROR = ❌
- [ ] 级别选择正确（业务节点 INFO、异常 ERROR）
- [ ] 占位符替代字符串拼接
- [ ] **日志参数求值安全（§6）**：日志参数不写未判空对象的方法调用/链式取值/集合空索引（先判空或先取安全局部变量再打）；判空写日志行之前
- [ ] 异常日志带堆栈
- [ ] 关键日志含业务上下文 ID
- [ ] 无敏感信息
- [ ] 高频路径无逐条日志
