# MyBatis XML 规范 (MyBatis XML Standards)

## 适用范围

编写 Mapper XML 映射文件、动态 SQL 时加载。

## 触发条件（何时用 XML / 何时禁 XML，决策在前）

**先判定，再决定是否建 XML。XML 是自定义 SQL 的唯一载体（禁注解 SQL），但不是每个 Mapper 必备：**

| 查询类型 | 实现方式 | 是否建 XML |
|---|---|---|
| 单表简单查询（等值/范围/排序/分页） | `BaseMapper` + `LambdaQueryWrapper` | ❌ **禁止建 XML**（无谓维护成本） |
| 单表复杂动态 SQL（多条件拼装） | `LambdaQueryWrapper` 条件拼接 | ❌ 优先 Wrapper，不建 XML |
| 多表 join / 复杂子查询 / 聚合分组 | **XML** | ✅ 建 XML |
| 复杂动态 SQL（`<foreach>`/`<choose>`/`<if>` 复杂拼装） | XML | ✅ 建 XML |
| 批量操作（批量插入/更新优化） | XML `<foreach>` | ✅ 建 XML |
| 特殊分页（分页 + join） | XML | ✅ 建 XML |

- **禁止**：简单查询硬写 XML（`selectById` 自己写 SQL）；Controller/Service 不用 SQL，一律走 Mapper
- **禁止注解 SQL**（`@Select`/`@Insert`/`@Update`/`@Delete`/`<script>`）：需要手写 SQL 的场景一律建 XML——注解 SQL 散落 Java 代码，无法统一审计/格式化/复用，长脚本可读性差
- **判定口诀**：`BaseMapper` 或 `LambdaQueryWrapper` 能表达的查询 → 不建 XML；需要手写 SQL 且带 join/动态/批量 → 建 XML
- Mapper 接口可以不建 XML（无自定义复杂 SQL 时，接口只继承 `BaseMapper`，零文件）

## 强制规则

### 1. XML 结构

- 一个 XML 对应一个 Mapper 接口，namespace 与接口全限定名一致

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
        "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.example.order.mapper.OrderMapper">
</mapper>
```

- resultMap 与接口方法对应，id 与方法名一致
- XML 与接口方法一一对应：接口有方法 XML 无实现（或反之）编译不报错但运行期炸——自查

### 2. resultMap 规范

- 驼峰自动映射开启时，简单查询不写 resultMap
- 必须 resultMap 场景：列别名复杂、多表关联、typeHandler 特殊类型

```xml
<resultMap id="OrderVOMap" type="com.example.order.vo.OrderVO">
    <id property="id" column="id"/>
    <result property="orderNo" column="order_no"/>
    <result property="amount" column="amount" jdbcType="DECIMAL"/>
    <result property="statusText" column="status_text"/>
</resultMap>
```

### 3. SQL 片段

- 公共列/条件抽 `<sql>` 片段复用，片段命名语义化

```xml
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
</sql>
```

- 片段仅限真正复用场景，一次使用不抽

### 4. 动态 SQL

- `<if>` 条件用 OGNL 判空：`test="query.userId != null"`，字符串追加判空 `!= null and != ''`
- `<foreach>` 必带 `collection`、`item`、`separator`；批量参数集合命名 `@Param("ids")`
- 动态排序列必须白名单校验（防注入），不直接 `order by ${orderBy}`

```xml
<select id="selectOrderPage" resultType="com.example.order.entity.Order">
    SELECT <include refid="orderColumns"/>
    FROM t_order
    <where>
        <include refid="queryCondition"/>
    </where>
    ORDER BY ${safeOrderBy}   <!-- safeOrderBy 来自白名单校验后的字段 -->
</select>
```

- `<where>` 自动处理首条 AND；不用 `WHERE 1=1`（可读性 + 老版本优化器问题）

### 5. 批量操作

```xml
<insert id="insertBatch">
    INSERT INTO t_order (order_no, user_id, amount, status)
    VALUES
    <foreach collection="list" item="item" separator=",">
        (#{item.orderNo}, #{item.userId}, #{item.amount}, #{item.status})
    </foreach>
</insert>

<update id="updateBatchStatus">
    UPDATE t_order
    SET status = #{targetStatus}
    WHERE id IN
    <foreach collection="ids" item="id" open="(" separator="," close=")">
        #{id}
    </foreach>
</update>
```

- 批量大小控制 500~1000，超大分批提交

### 6. 禁止事项

- ❌ **注解 SQL**（`@Select`/`@Insert`/`@Update`/`@Delete`/`<script>`）——需要手写 SQL 一律放 XML，禁止写在 Mapper 接口方法上（见 mapper-standards.md）
- ❌ `${}` 拼接值（SQL 注入）——仅限白名单排序/表名
- ❌ `SELECT *`（明确列）
- ❌ 复杂业务逻辑写在 XML（join 后状态判断）

## 反例 / 正例

```xml
<!-- 反例 -->
<select id="selectList" resultType="java.util.Map">
    SELECT * FROM t_order WHERE 1=1
    <if test="status != null">
        AND status = '${status}'      <!-- 拼接注入 + 单引号 -->
    </if>
</select>

<!-- 正例 -->
<select id="selectList" resultType="com.example.order.entity.Order">
    SELECT <include refid="orderColumns"/>
    FROM t_order
    <where>
        <if test="status != null">
            AND status = #{status}
        </if>
    </where>
</select>
```

## 最佳实践

- XML 内只写 SQL 与映射，复杂组装在 Service
- 大 XML 按模块拆分；公共片段集中在 base XML 复用
- XML 与接口、Entity 字段三方一致：改字段同步改 XML（编译期无法发现，靠测试）

## 自检清单

- [ ] 已判定触发条件：简单查询未建 XML（Wrapper 覆盖），复杂 SQL 已建 XML
- [ ] 无注解 SQL（@Select/@Insert/@Update/@Delete/<script>），手写 SQL 全部在 XML
- [ ] namespace 与接口一致
- [ ] XML 方法与接口方法一一对应
- [ ] 无 SELECT *，列明确
- [ ] 无 ${} 拼接值
- [ ] 动态条件用 <where>，无 1=1
- [ ] foreach 参数齐备
- [ ] 排序字段白名单校验
- [ ] 批量大小受控
