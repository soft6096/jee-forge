package com.example.module.service;

import com.example.common.PageResult;
import com.example.module.dto.XxxCreateDTO;
import com.example.module.dto.XxxQueryDTO;
import com.example.module.dto.XxxUpdateDTO;
import com.example.module.vo.XxxVO;

/**
 * Xxx 业务服务接口。
 *
 * <p>定义 Xxx 的查询、创建、更新、删除业务能力。</p>
 */
public interface XxxService {

    /**
     * 查询单条。
     *
     * @param id Xxx ID
     * @return Xxx 详情，不存在时抛业务异常
     */
    XxxVO getById(Long id);

    /**
     * 分页查询。
     *
     * @param query 查询条件
     * @return 分页结果
     */
    PageResult<XxxVO> queryPage(XxxQueryDTO xxxQuery);

    /**
     * 创建。
     *
     * @param createInfo 创建入参
     * @return 新记录 ID
     */
    Long create(XxxCreateDTO createInfo);

    /**
     * 更新。
     *
     * @param id  Xxx ID
     * @param updateInfo 更新入参
     */
    void update(Long id, XxxUpdateDTO updateInfo);

    /**
     * 删除。
     *
     * @param id Xxx ID
     */
    void delete(Long id);
}
