# MyBatis-Plus Mapper 规范 (MyBatis-Plus Mapper Standards)

## 适用范围

生成 MyBatis-Plus Mapper 接口时加载（与 java-code-standards 的 Mapper 接口结构规范配合使用）。本规范专注 MyBatis-Plus 数据访问层的 SQL 相关规则；接口结构/命名/@Param 等 Java 侧规则见 java-code-standards `01-java/mapper-standards.md`。

## 强制规则

### 1. 继承 BaseMapper

- 继承 `BaseMapper<T>` 获得通用 CRUD，接口内只写自定义方法
- 一个 Mapper 对应一个 Entity 类，不跨表混写（跨表查询收敛到主表 Mapper）

```java
@Mapper
public interface OrderMapper extends BaseMapper<Order> {

    Page<Order> selectOrderPage(Page<Order> pageResult, @Param("query") OrderQueryDTO orderQuery);
}
```

### 2. SQL 两种写法选择

| 场景 | 方式 |
|---|---|
| 单表简单条件 | LambdaQueryWrapper / LambdaUpdateWrapper |
| 复杂查询（多表 join、子查询、动态条件多） | XML（见 mybatis-xml-standards.md） |
| 批量插入/更新 | XML `<foreach>` |

- 简单单表查询禁止写死 SQL 字符串，用 Wrapper 避免 SQL 注入与硬编码字段
- **禁止注解 SQL**（`@Select`/`@Insert`/`@Update`/`@Delete`/`<script>`）：需要手写 SQL 一律放 `resources/mapper/XxxMapper.xml`，接口只声明方法签名——注解 SQL 散落 Java 代码无法统一审计/格式化/复用
- 动态 SQL（`<if>`）统一放 XML

### 3. Wrapper 使用规范

- 用 Lambda 版本（`LambdaQueryWrapper` / `LambdaUpdateWrapper`），禁字符串列名版（编译期检查 + 重构安全）
- 条件拼接按「等值在前、范围在后」与索引最左前缀一致（见 index-standards）
- 动态排序字段必须白名单校验，禁止直接拼字符串进 `orderBy`
- 防注入：Wrapper 值参数是安全的，但 `apply()` / `last()` 传用户输入 = 注入，禁止

```java
// 反例：字符串列名 + 用户输入进 last
queryWrapper.orderByAsc("create_time").last("LIMIT " + userInput);

// 正例
new LambdaQueryWrapper<Order>()
        .eq(Order::getUserId, userId)
        .orderByDesc(Order::getId)
        .last("LIMIT " + safeLimit);   // safeLimit 来自校验后的常量/参数
```

### 4. 分页

- 使用 MyBatis-Plus 分页插件 `Page<T>`，不手写 `LIMIT offset, size`
- 分页方法第一参数必须是 `Page`，插件自动生成 count 查询
- 插件配置 `maxLimit` 防止一次性拉全表（见 pagination-example.md）

```java
Page<Order> selectOrderPage(Page<Order> pageResult, @Param("query") OrderQueryDTO orderQuery);
```

- 深分页（offset 大）改键集分页，见 pagination-standards.md

### 5. 逻辑删除

- 逻辑删除列（deleted）在全局配置开启，Entity 注解 `@TableLogic`，查询自动过滤
- 物理删除只用于明确需彻底删除的场景（日志表、关联清理）

### 6. 批量操作

- 批量插入用 `insertBatchSomeColumn` 自定义方法或 XML foreach，不用循环 `insert`
- 批量大小控制 500~1000，超大分批提交

### 7. 字段映射

- 字段映射用驼峰自动转换（`map-underscore-to-camel-case: true`），XML 少写 `resultMap`；有别名/复杂映射才写 resultMap
- 查询列裁剪：列表页只查列表所需列，定义专用 VO 接收

### 8. 禁止事项

- ❌ **注解 SQL**（`@Select`/`@Insert`/`@Update`/`@Delete`/`<script>`）——手写 SQL 一律放 XML，禁止写在接口方法上
- ❌ 返回 `Map<String, Object>` 作为主结果（类型不安全），用 VO/DTO 接收
- ❌ `select *`（XML 内），明确列出列
- ❌ 在 Mapper 里写业务逻辑（if 状态判断等）
- ❌ 返回全部列给不需要的字段（性能 + 序列化冗余）

## 反例 / 正例

```java
// 反例：注解 SQL 写在 Java 方法上（禁）——SQL 散落代码中，无法统一审计/复用
@Select("SELECT * FROM t_order WHERE status = #{0} AND shop_id = #{1}")
List<Order> list(Integer status, Long shopId);

// 正例 1（简单条件用 Wrapper，Service 层组装，无 XML 文件）
List<Order> list = orderMapper.selectList(new LambdaQueryWrapper<Order>()
        .eq(Order::getStatus, status)
        .eq(Order::getShopId, shopId));

// 正例 2（复杂 SQL 进 XML，接口只声明方法签名）
List<OrderVO> selectOrderVOList(@Param("status") Integer status,
                                @Param("shopId") Long shopId);
```

```xml
<!-- resources/mapper/OrderMapper.xml -->
<select id="selectOrderVOList" resultType="com.example.order.vo.OrderVO">
    SELECT id, order_no, status
    FROM t_order
    WHERE status = #{status} AND shop_id = #{shopId}
</select>
```

## 性能优化建议

- 大表查询强制走索引列条件（见 index-standards），Mapper 方法注释标明期望索引
- 深分页（offset 大）改游标/键集分页，见 pagination-standards.md
- 批量操作用 foreach 一次提交，控制 batch 大小（500~1000）

## 自检清单

- [ ] 继承 BaseMapper，无重复通用 CRUD 定义
- [ ] 复杂 SQL 在 XML，简单条件用 Wrapper；无注解 SQL（@Select/@Insert/@Update/@Delete/<script>）
- [ ] Wrapper 用 Lambda 版，无字符串列名
- [ ] 无 apply()/last() 拼接用户输入
- [ ] 分页用 Page 参数，插件配 maxLimit
- [ ] 逻辑删除 @TableLogic 配置
- [ ] 无 select *，列明确
- [ ] 无 Map 返回主结果
- [ ] 批量操作用批量方法，大小受控
