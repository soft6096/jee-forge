# Entity 规范 (Entity Standards)

## 适用范围

生成数据库实体类时加载。定义实体与表映射、字段注解、与 DTO/VO 的边界。

## 强制规则

### 1. 类定位

- Entity 与数据库表一一对应，字段名 = 列名下划线转驼峰
- ❌ Entity 内放业务逻辑、校验注解、转换方法
- ❌ Entity 直接返回给前端（接口出参用 VO）
- **同表唯一映射（强制）**：**全项目一张表只允许一个 Entity 映射**（一个 `@TableName("x")`）。**新建 Entity 前先 `grep -rn '@TableName("该表名")' src/main/java` 全项目查重**——同表已有 Entity：
  - 字段够用 → **直接复用/扩展已有 Entity**，禁止再造一个映射同表的新 Entity
  - 字段不够/命名不符 → 扩展已有 Entity（同步 DDL），或在**确认旧 Entity 无业务引用后删除旧类**，再造新类；**禁止两 Entity 并存映射同表**（后台/前台各建一个、不同模块各建一个都是重复映射，字段增减双维护必漂移）
  - 历史已存在的重复映射（存量项目）→ 列 `docs/0.5-存量代码扫描.md`（表→Entity 清单标注重复）→ 无引用类删除、双引用类收敛合并，见 legacy-onboarding 体检「数据基线」

> [!CAUTION] 重复表映射的后果
> 两个 Entity 映射同一张表（如 `MallProduct` 与 `MallServiceProduct` 都 `@TableName("mall_product")`），字段各自演化 → 双维护必漂移（一边加列另一边不知道）；同表两套 Mapper 查询口径不一；改表结构时漏改一个即运行期炸。**根因：建 Entity 前没查该表是否已有映射**——本规则把"先查重"设为强制动作。

```java
// ❌ 反例：两 Entity 映射同一张表（禁）
@TableName("mall_product") public class MallProduct { ... }                    // 后台建
@TableName("mall_product") public class MallServiceProduct { ... }             // 前台/Service 改造又建一个 → 重复映射

// ✅ 正例：先查重，同表只留一个
@TableName("mall_product") public class MallProduct { ... }                    // 唯一映射，前后台共用
// 业务命名差异（spec_code vs combinationCode）→ 字段统一命名或经 @TableField("列名") 映射，不另建 Entity
```

```java
@TableName("t_order")
public class Order {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private Long userId;

    private String orderNo;

    /** 订单状态：见 OrderStatusEnum */
    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;

    @Version
    private Integer version;
}
```

### 2. 字段注解

| 场景 | 注解 |
|---|---|
| 主键策略 | `@TableId(type = IdType.ASSIGN_ID)` 雪花 ID，或 ASSIGN_UUID |
| 非主表字段 | `@TableField(exist = false)` |
| 逻辑删除 | `@TableLogic` + 全局配置逻辑值 |
| 乐观锁 | `@Version` + 乐观锁插件 |
| 自动填充 | `@TableField(fill = FieldFill.INSERT)` **必须**配合 MetaObjectHandler |
| 字段名非驼峰 | `@TableField("column_name")` |

- 主键：分布式环境用 `ASSIGN_ID`（雪花），不自增 `AUTO`（分库分表不兼容）
- 数据库默认值由 MetaObjectHandler 或 DB 默认处理，业务代码不重复赋值

**自动填充强制规则（createTime/updateTime 报 NOT NULL 的根因防线）**：

实体标注 `@TableField(fill = FieldFill.INSERT / INSERT_UPDATE)` 后，**项目必须存在一个 MetaObjectHandler 实现类**（如 `MyMetaObjectHandler`，`@Component`，自动填充 createTime/updateTime）：

- 有 fill 注解但无 MetaObjectHandler → 插入时字段为 NULL，违反 NOT NULL 约束，报 `Column 'create_time' cannot be null`（启动不报错，一插就炸，最坑）
- 该组件属**项目级基础设施**，在项目初始化/脚手架阶段创建（见 `04-templates/MyMetaObjectHandler.java` 模板），新建项目默认包含
- 数据库表 `create_time/update_time` 也要配默认值 `DEFAULT CURRENT_TIMESTAMP` 兜底（双保险，见 database-standards 表设计规范）

### 3. 类型规范

| 数据库 | Java 类型 |
|---|---|
| bigint | Long（主键不用 Integer） |
| varchar/text | String |
| decimal | BigDecimal（金额禁用 double/float） |
| datetime | LocalDateTime（不用 Date） |
| date | LocalDate |
| tinyint | Integer（枚举存数值）或 String（少量） |
| json | String 或 JSON 字段处理器 |

- 时间统一 `LocalDateTime`，时区统一，不存本地字符串
- 金额统一 `BigDecimal`，精度 scale 与 DB 一致（如 2 位）
- 状态字段存数值/编码，不存中文

### 4. 字段规则

- 必备字段：`id`、`createTime`、`updateTime`、`deleted`（逻辑删团队统一）
- 大字段（text/blob）单独拆表或独立字段，不混入高频查询表
- 字段注释（Javadoc）说明业务含义、取值枚举、单位（如金额单位分）

### 5. 序列化控制

- 大字段不参与序列化时用 `@JsonIgnore`（如内部日志字段）
- 敏感字段（手机号等）出参脱敏在 VO 层，Entity 不处理

## 反例 / 正例

```java
// 反例：Entity 塞校验 + 返回前端 + 自增主键
public class Order {
    @TableId(type = IdType.AUTO)
    private Long id;
    @NotBlank(message = "订单号不能为空")   // 校验应放 DTO
    private String orderNo;
    private String userId;                  // 类型错：应为 Long
    private double amount;                  // 金额用 double，精度风险
    private String createTime;              // 时间用字符串
}
```

```java
// 反例 2：@TableField(fill=...) 标注自动填充，但项目没有 MetaObjectHandler 实现
// → 插入报 Column 'create_time' cannot be null
@TableField(fill = FieldFill.INSERT)
private LocalDateTime createTime;
```

```java
// 正例：fill 注解 + 项目级 MyMetaObjectHandler（见 04-templates/MyMetaObjectHandler.java）
@TableField(fill = FieldFill.INSERT)
private LocalDateTime createTime;

@TableField(fill = FieldFill.INSERT_UPDATE)
private LocalDateTime updateTime;
```

## 最佳实践

- 主键/时间/逻辑删除字段由插件与 MetaObjectHandler 统一处理，业务代码不手动 set
- 表名前缀统一（如 t_），`@TableName` 显式声明，不依赖默认命名
- 字段增减同步改表结构，Entity 与 DDL 保持一一对应
- 大项目按模块分包：`entity.order`、`entity.user`，不堆一个包

## 自检清单

- [ ] 与表一一对应，字段类型正确
- [ ] **同表唯一映射：建 Entity 前已 `grep @TableName("表名")` 全项目查重，无第二 Entity 映射同表**
- [ ] 主键 ASSIGN_ID，非自增
- [ ] 金额 BigDecimal，时间 LocalDateTime
- [ ] 逻辑删除 @TableLogic，乐观锁 @Version（需要时）
- [ ] 无校验注解、无业务逻辑
- [ ] 必备字段齐（id/createTime/updateTime/deleted）
- [ ] 字段有注释
- [ ] 有 `@TableField(fill=...)` → 项目已实现 MetaObjectHandler（MyMetaObjectHandler），否则插入报 NOT NULL
