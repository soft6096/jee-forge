package com.example.common.exception;

/**
 * 错误码定义。
 *
 * <p>统一管理业务错误码，禁止在业务代码中散落字符串错误码。</p>
 */
public enum ErrorCode {

    /** 记录不存在 */
    XXX_NOT_FOUND("XXX_001", "记录不存在"),

    /** 状态不允许该操作 */
    XXX_STATUS_ILLEGAL("XXX_002", "状态不允许该操作"),

    /** 系统繁忙 */
    SYSTEM_ERROR("SYS_001", "系统繁忙，请稍后重试");

    private final String code;
    private final String defaultMessage;

    ErrorCode(String code, String defaultMessage) {
        this.code = code;
        this.defaultMessage = defaultMessage;
    }

    public String getCode() {
        return code;
    }

    public String getDefaultMessage() {
        return defaultMessage;
    }
}
