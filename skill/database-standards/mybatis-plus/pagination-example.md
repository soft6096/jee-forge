# 分页查询完整示例

展示两种分页实现：MyBatis-Plus 分页插件（常规）与键集分页（深分页/加载更多）。

## 场景

订单列表，按用户 + 状态 + 时间范围查询，按创建时间倒序。数据量 500 万。

## 1. 分页插件配置

```java
@Configuration
public class MybatisPlusConfig {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        PaginationInnerInterceptor pagination = new PaginationInnerInterceptor(DbType.MYSQL);
        pagination.setMaxLimit(100L);   // 防止一次性拉全表
        interceptor.addInnerInterceptor(pagination);
        return interceptor;
    }
}
```

## 2. 查询 DTO

```java
@Data
public class OrderQueryDTO extends PageQuery {

    @NotNull(message = "用户ID不能为空")
    private Long userId;

    private Integer status;

    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime startTime;

    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime endTime;
}

@Data
public class PageQuery {
    @Min(value = 1, message = "页码从1开始")
    private Integer pageNum = 1;

    @Min(value = 1, message = "每页条数最小为1")
    @Max(value = 100, message = "每页条数最大100")
    private Integer pageSize = 10;
}
```

## 3. Mapper

```java
@Mapper
public interface OrderMapper extends BaseMapper<Order> {

    Page<Order> selectOrderPage(Page<Order> pageResult, @Param("query") OrderQueryDTO orderQuery);
}
```

## 4. XML

```xml
<mapper namespace="com.example.order.mapper.OrderMapper">

    <sql id="orderColumns">
        id, order_no, user_id, amount, status, create_time
    </sql>

    <sql id="queryCondition">
        <if test="query.userId != null">
            AND user_id = #{query.userId}
        </if>
        <if test="query.status != null">
            AND status = #{query.status}
        </if>
        <if test="query.startTime != null">
            AND create_time &gt;= #{query.startTime}
        </if>
        <if test="query.endTime != null">
            AND create_time &lt;= #{query.endTime}
        </if>
    </sql>

    <select id="selectOrderPage" resultType="com.example.order.entity.Order">
        SELECT <include refid="orderColumns"/>
        FROM t_order
        <where>
            <include refid="queryCondition"/>
        </where>
        ORDER BY create_time DESC, id DESC
    </select>
</mapper>
```

> 排序含 `id DESC` 兜底：同 create_time 大量行时分页不重不漏。

## 5. Service

```java
@Service
@RequiredArgsConstructor
public class OrderServiceImpl implements OrderService {

    private final OrderMapper orderMapper;
    private final OrderConverter orderConverter;

    @Override
    public PageResult<OrderVO> queryPage(OrderQueryDTO orderQuery) {
        Page<Order> pageResult = new Page<>(orderQuery.getPageNum(), orderQuery.getPageSize());
        IPage<Order> pageQueryResult = orderMapper.selectOrderPage(pageResult, orderQuery);
        return PageResult.of(orderConverter.toVOList(pageQueryResult.getRecords()), pageQueryResult.getTotal());
    }
}
```

```java
@Data
public class PageResult<T> {
    private List<T> recordList;
    private long total;

    public static <T> PageResult<T> of(List<T> recordList, long total) {
        PageResult<T> pageResult = new PageResult<>();
        pageResult.setRecordList(recordList);
        pageResult.setTotal(total);
        return pageResult;
    }
}
```

## 6. 键集分页（深分页方案）

`LIMIT 100000, 20` 慢：MySQL 先扫 100020 行再丢弃。键集分页直接定位。

```java
public interface OrderMapper extends BaseMapper<Order> {

    Page<Order> selectOrderPage(Page<Order> pageResult, @Param("query") OrderQueryDTO orderQuery);

    /** 键集分页：按 id 倒序，取小于 lastId 的数据 */
    List<Order> selectByCursor(@Param("query") OrderQueryDTO orderQuery,
                               @Param("lastId") Long lastId,
                               @Param("size") Integer size);
}
```

```xml
<select id="selectByCursor" resultType="com.example.order.entity.Order">
    SELECT <include refid="orderColumns"/>
    FROM t_order
    <where>
        <if test="lastId != null">
            AND id &lt; #{lastId}
        </if>
        <include refid="queryCondition"/>
    </where>
    ORDER BY id DESC
    LIMIT #{size}
</select>
```

```java
// Service：加载更多
public List<OrderVO> queryByCursor(OrderQueryDTO orderQuery, Long lastId, int size) {
    List<Order> orderRecordList = orderMapper.selectByCursor(orderQuery, lastId, size);
    return orderConverter.toVOList(orderRecordList);
}
```

前端调用：首屏 `lastId = null`，后续带上一页最后一条的 id。免 count，天然高效。

## 7. 深分页性能对比

| 方案 | 第 10 万页（LIMIT 100000,20） | 说明 |
|---|---|---|
| offset 分页 | 扫 100020 行 + 计数查询 | 越翻越慢，count 大表也贵 |
| 键集分页 | 走 `idx_id` 定位 + LIMIT 20 | 恒定速度，免 count |
| 时间范围收敛 | 条件缩小到索引范围 | 业务可加时间窗约束时优先 |

## 8. 索引

```sql
-- 常规分页：排序走索引
KEY `idx_user_status_create` (`user_id`, `status`, `create_time`),
KEY `idx_create` (`create_time`)

-- 键集分页：id 主键天然支撑
```

## 规范对照

| 规范点 | 落地位置 |
|---|---|
| 分页插件统一 | MybatisPlusConfig 注册 |
| pageSize 上限 | PageQuery @Max(100) + 插件 maxLimit |
| 排序唯一兜底 | ORDER BY create_time DESC, id DESC |
| XML 动态条件 | `<where>` + `<if>` + `<sql>` 片段 |
| 索引设计 | 复合索引 (user_id, status, create_time) |
| 深分页处理 | 键集分页 selectByCursor |
| 转换不散落 | orderConverter.toVOList |
