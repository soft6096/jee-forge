# 自定义异常规范 (Custom Exception Standards)

## 适用范围

生成自定义异常类时加载。定义异常体系扩展、错误码设计。

## 强制规则

### 1. 继承体系

- 业务异常继承项目基础 `BusinessException`，系统异常继承 `SystemException`（见 00-common 异常规范）
- ❌ 自定义异常直接继承 `RuntimeException` 旁路统一体系

```java
// 项目已有基础类，扩展时这样写
public class OrderNotExistException extends BusinessException {
    public OrderNotExistException(String message) {
        super(ErrorCode.ORDER_NOT_FOUND, message);
    }
}
```

### 2. 错误码

- 错误码集中管理（常量类或枚举），异常类内不散落字符串

```java
// 错误码枚举（推荐）
public enum ErrorCode {

    ORDER_NOT_FOUND("ORDER_001", "订单不存在"),
    ORDER_STATUS_ILLEGAL("ORDER_002", "订单状态不允许该操作"),
    STOCK_NOT_ENOUGH("ORDER_003", "库存不足"),
    SYSTEM_ERROR("SYS_001", "系统繁忙，请稍后重试");

    private final String code;
    private final String defaultMessage;

    ErrorCode(String code, String defaultMessage) {
        this.code = code;
        this.defaultMessage = defaultMessage;
    }

    public String getCode() { return code; }
    public String getDefaultMessage() { return defaultMessage; }
}
```

- 错误码命名：模块前缀（ORDER/USER/PAY）+ 递增序号，或语义段
- 编码规范：4-6 位字符串，前 2-3 位模块，后位错误序号

### 3. 构造器设计

- 至少提供：`(ErrorCode)`、`(ErrorCode, message)`、`(ErrorCode, message, Throwable)`
- message 缺省用 ErrorCode 默认文案，可覆盖为动态细节

```java
public class BusinessException extends RuntimeException {
    private final String code;

    public BusinessException(ErrorCode errorCode) {
        super(errorCode.getDefaultMessage());
        this.code = errorCode.getCode();
    }

    public BusinessException(ErrorCode errorCode, String message) {
        super(message);
        this.code = errorCode.getCode();
    }

    public BusinessException(ErrorCode errorCode, String message, Throwable cause) {
        super(message, cause);
        this.code = errorCode.getCode();
    }
}
```

### 4. 使用原则

- 一个异常类可服务一个领域（`OrderNotExistException`），也可统一 `BusinessException` + 错误码
- 异常粒度：调用方需区分处理才细分异常类，否则用错误码区分
- ❌ 为每个失败场景建异常类（爆炸式增长）

## 反例 / 正例

```java
// 反例：异常类爆炸 + 错误码散落
public class OrderNullException extends RuntimeException {}
public class OrderStatusException extends RuntimeException {}
public class OrderAmountException extends RuntimeException {}
public class OrderShopException extends RuntimeException {}
// 每处 throw new XXXException("订单...")

// 正例
throw new BusinessException(ErrorCode.ORDER_STATUS_ILLEGAL, "当前状态为已取消，不可再次取消");
```

## 最佳实践

- 全局异常处理器对 `BusinessException` 取 code+message 返回 `Response`，对未知异常记日志返回通用错误
- 错误码文档化：README 或枚举注释维护错误码表，前端对照提示
- 错误码一经发布不改语义，废弃用新码，避免前端旧逻辑错乱

## 自检清单

- [ ] 继承统一异常体系（Business/SystemException）
- [ ] 错误码集中定义，无散落字符串
- [ ] 构造器含 ErrorCode 与 cause 变体
- [ ] 未爆炸式建异常类
- [ ] 错误码有文档/注释
