package com.example.module.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.*;
import lombok.Data;

import java.math.BigDecimal;

/**
 * Xxx 创建入参。
 */
@Data
public class XxxCreateDTO {

    /** 名称 */
    @Schema(description = "名称")
    @NotBlank(message = "名称不能为空")
    @Size(max = 64, message = "名称长度不能超过64")
    private String name;

    /** 金额，单位：元 */
    @Schema(description = "金额，单位：元")
    @NotNull(message = "金额不能为空")
    @DecimalMin(value = "0.01", message = "金额必须大于0")
    @Digits(integer = 10, fraction = 2, message = "金额最多2位小数")
    private BigDecimal amount;

    /** 状态：见 XxxStatusEnum */
    @Schema(description = "状态：见 XxxStatusEnum")
    @NotNull(message = "状态不能为空")
    private Integer status;

    /** 备注 */
    @Schema(description = "备注")
    @Size(max = 255, message = "备注长度不能超过255")
    private String remark;
}
