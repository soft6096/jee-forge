package com.example.module.config;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * MyBatis-Plus 字段自动填充处理器。
 *
 * <p>配套实体类上的 {@code @TableField(fill = FieldFill.INSERT / INSERT_UPDATE)} 注解：
 * 实体标注自动填充但项目未实现本类时，插入/更新会因字段为 NULL 违反 NOT NULL 约束，
 * 报错如 {@code Column 'create_time' cannot be null}。本组件属项目级基础设施，
 * 项目初始化/脚手架阶段创建，新建项目默认包含。</p>
 */
@Component
public class MyMetaObjectHandler implements MetaObjectHandler {

    /**
     * 插入时自动填充 createTime / updateTime。
     *
     * @param metaObject MyBatis 元对象
     */
    @Override
    public void insertFill(MetaObject metaObject) {
        LocalDateTime now = LocalDateTime.now();
        this.strictInsertFill(metaObject, "createTime", LocalDateTime.class, now);
        this.strictInsertFill(metaObject, "updateTime", LocalDateTime.class, now);
    }

    /**
     * 更新时自动填充 updateTime。
     *
     * @param metaObject MyBatis 元对象
     */
    @Override
    public void updateFill(MetaObject metaObject) {
        this.strictUpdateFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
    }
}
