package com.example.module.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * Xxx 实体，对应表 t_xxx。
 */
@Data
@TableName("t_xxx")
public class Xxx {

    /** 主键 ID（雪花） */
    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    /** 业务编号 */
    private String bizNo;

    /** 名称 */
    private String name;

    /** 金额，单位：元，精度 2 位 */
    private BigDecimal amount;

    /** 状态：10-待处理 20-处理中 30-已完成 90-已取消 */
    private Integer status;

    /** 备注 */
    private String remark;

    /** 创建时间 */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /** 更新时间 */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /** 逻辑删除：0-未删 1-已删 */
    @TableLogic
    private Integer deleted;

    /** 乐观锁版本号 */
    @Version
    private Integer version;
}
