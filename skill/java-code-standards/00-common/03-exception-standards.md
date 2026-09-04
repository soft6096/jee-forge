# 异常处理规范 (Exception Handling Standards)

## 适用范围

生成任意 Java 代码前必读。定义异常体系、抛出与捕获原则。

## 强制规则

### 1. 异常体系

项目统一两级结构：

```java
// 基础异常：携带错误码 + 错误信息
public class BaseException extends RuntimeException {
    private final String code;

    public BaseException(String code, String message) {
        super(message);
        this.code = code;
    }

    public String getCode() {
        return code;
    }
}

// 业务异常：业务规则不满足时抛出
public class BusinessException extends BaseException {
    public BusinessException(String code, String message) {
        super(code, message);
    }
}

// 系统异常：基础设施/未知错误
public class SystemException extends BaseException {
    public SystemException(String message) {
        super("SYS_ERROR", message);
    }
}
```

- 所有自定义异常继承 `RuntimeException`，避免强制 checked 异常污染业务层
- 错误码统一字符串常量，放常量类或枚举（见 constants/enum 规范）

### 2. 抛出原则

- 业务规则不满足 → 抛 `BusinessException`，信息对用户可读
- 基础设施失败（DB/Redis/第三方）→ 抛 `SystemException`，信息含技术细节
- 参数校验失败 → 由框架校验（Bean Validation）或抛参数异常，不抛 `BusinessException`
- ❌ 不抛裸 `RuntimeException` / `Exception`（丢失错误码）
- ❌ 不抛异常做流程控制（用 `if` 判断状态）

```java
// 反例
throw new RuntimeException("订单不存在");

// 正例
throw new BusinessException(ErrorCode.ORDER_NOT_FOUND, "订单不存在或已删除");
```

### 3. 捕获原则

- 捕获后必须处理：记录日志、包装抛出、或恢复默认值，三选一
- ❌ 空 catch：`catch (Exception e) { }`
- ❌ 捕获后不记录直接返回 null（吞异常）
- 跨层边界（Controller 入口）不 catch，交给全局异常处理器
- 精确捕获优先：`catch (DuplicateKeyException e)` 优于 `catch (Exception e)`

```java
// 反例
try {
    orderService.submit(orderId);
} catch (Exception e) {
    return;  // 异常被吞，无日志
}

// 正例
try {
    orderService.submit(orderId);
} catch (BusinessException e) {
    throw e;  // 业务异常原样上抛，全局处理器统一响应
} catch (Exception e) {
    log.error("submit order failed, orderId={}", orderId, e);
    throw new SystemException("订单提交失败，请稍后重试");
}
```

### 4. 资源关闭

- 使用 try-with-resources 自动关闭
- 手写 finally 关闭必须判空且再次捕获异常

```java
// 正例
try (InputStream in = new FileInputStream(path);
     BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
    return reader.readLine();
}
```

### 5. 异常信息

- 日志与异常信息禁止拼接敏感数据（密码、token）
- 异常信息带上下文参数：`"order submit failed, orderId=" + orderId`（或占位符）
- 用户可见信息与技术信息分离：`BusinessException` 信息给用户，堆栈进日志

## 反例 / 正例

```java
// 反例：层层 catch 又抛出，堆栈被切断
try {
    return userMapper.selectById(id);
} catch (Exception e) {
    throw new BusinessException("查询失败");  // 丢失原始异常与堆栈
}

// 正例
try {
    return userMapper.selectById(id);
} catch (DataAccessException e) {
    log.error("select user failed, id={}", id, e);
    throw new SystemException("数据库访问异常");
}
```

## 最佳实践

- 全局异常处理器（`@RestControllerAdvice`）统一转换异常为响应体，Controller 层不写 try/catch
- 事务内异常：运行时异常自动回滚，检查 `@Transactional` 的 rollbackFor 设置
- 批量任务（定时 Job）逐条 catch，单条失败不中断整批
- 异步线程内异常必须捕获记录，否则静默丢失
- 第三方调用失败区分「可重试」与「不可重试」，可重试错误带重试策略

### 错误码分段管理

错误码统一字符串编码，分段设计，防撞号 + 快速定位：

| 段位 | 格式 | 示例 | 归属 |
|---|---|---|---|
| 通用段 | `COMMON_xxx` | `COMMON_PARAM_ERROR`、`COMMON_SYSTEM_ERROR` | 全局（参数/鉴权/系统） |
| 模块段 | `模块_xxx` | `ORDER_NOT_FOUND`、`ORDER_STATUS_INVALID`、`PAY_BALANCE_INSUFFICIENT` | 各业务模块 |

- 错误码集中定义：通用段在全局常量/枚举类，模块段在模块内枚举类（`OrderErrorCode`、`PayErrorCode`）
- 编码规则：模块前缀 + 语义（`ORDER_` + `NOT_FOUND`），禁止裸数字（`10001` 不可读）
- 错误码唯一性：新码先查重，禁止不同异常共用同码
- 错误码进文档（接口文档错误码表），前端按码处理（不解析 message）

```java
// 正例：模块内枚举
public enum OrderErrorCode {
    ORDER_NOT_FOUND("ORDER_NOT_FOUND", "订单不存在或已删除"),
    ORDER_STATUS_INVALID("ORDER_STATUS_INVALID", "订单状态不允许该操作");
    ...
}
```

## 性能优化建议

- 异常对象构造昂贵（堆栈填充）。高频路径禁止用异常做控制流
- 已知可预期条件（如空集合、状态未达）用条件判断，不抛异常

## 自检清单

- [ ] 所有抛出使用自定义异常，带错误码
- [ ] 错误码分段（COMMON_/模块_），无裸数字
- [ ] 错误码集中定义 + 查重，无同码复用
- [ ] 无裸 `RuntimeException` 抛业务错误
- [ ] 无空 catch
- [ ] 资源使用 try-with-resources
- [ ] Controller 无 try/catch 堆积
- [ ] 异常日志含上下文参数
- [ ] 无敏感信息入异常/日志
