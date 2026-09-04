package com.example.module.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * Xxx 详情出参。
 */
@Data
public class XxxVO {

    /** 主键 ID */
    @Schema(description = "主键 ID")
    private Long id;

    /** 业务编号 */
    @Schema(description = "业务编号")
    private String bizNo;

    /** 名称 */
    @Schema(description = "名称")
    private String name;

    /** 金额，单位：元 */
    @Schema(description = "金额，单位：元")
    private BigDecimal amount;

    /** 状态编码 */
    @Schema(description = "状态编码")
    private Integer status;

    /** 状态文案 */
    @Schema(description = "状态文案")
    private String statusText;

    /** 创建时间 */
    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
