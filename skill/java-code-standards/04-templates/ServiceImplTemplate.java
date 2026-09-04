package com.example.module.service.impl;

import com.example.common.PageResult;
import com.example.module.converter.XxxConverter;
import com.example.module.dto.XxxCreateDTO;
import com.example.module.dto.XxxQueryDTO;
import com.example.module.dto.XxxUpdateDTO;
import com.example.module.entity.Xxx;
import com.example.module.mapper.XxxMapper;
import com.example.module.service.XxxService;
import com.example.module.vo.XxxVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

/**
 * Xxx 业务服务实现。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class XxxServiceImpl implements XxxService {

    private final XxxMapper xxxMapper;
    private final XxxConverter xxxConverter;

    @Override
    public XxxVO getById(Long id) {
        Xxx entity = getEntityOrThrow(id);
        return xxxConverter.toVO(entity);
    }

    @Override
    public PageResult<XxxVO> queryPage(XxxQueryDTO xxxQuery) {
        Page<Xxx> page = new Page<>(xxxQuery.getPageNum(), xxxQuery.getPageSize());
        LambdaQueryWrapper<Xxx> wrapper = new LambdaQueryWrapper<Xxx>()
                .eq(xxxQuery.getStatus() != null, Xxx::getStatus, xxxQuery.getStatus())
                .orderByDesc(Xxx::getCreateTime)
                .orderByDesc(Xxx::getId);
        Page<Xxx> result = xxxMapper.selectPage(page, wrapper);
        return PageResult.of(xxxConverter.toVOList(result.getRecords()), result.getTotal());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long create(XxxCreateDTO createInfo) {
        Xxx entity = xxxConverter.toEntity(createInfo);
        xxxMapper.insert(entity);
        log.info("xxx created, id={}", entity.getId());
        return entity.getId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(Long id, XxxUpdateDTO updateInfo) {
        Xxx entity = getEntityOrThrow(id);
        xxxConverter.updateEntity(updateInfo, entity);
        xxxMapper.updateById(entity);
        log.info("xxx updated, id={}", id);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        Xxx entity = getEntityOrThrow(id);
        xxxMapper.deleteById(entity.getId());
        log.info("xxx deleted, id={}", id);
    }

    private Xxx getEntityOrThrow(Long id) {
        Xxx entity = xxxMapper.selectById(id);
        if (entity == null) {
            throw new com.example.common.exception.BusinessException(
                    com.example.common.exception.ErrorCode.XXX_NOT_FOUND, "记录不存在");
        }
        return entity;
    }
}
