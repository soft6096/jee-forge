# 注释规范 (Comment Standards)

## 适用范围

生成任意代码前必读（代码注释）。规范 Javadoc 与行内注释的覆盖范围、格式与写法。面向所有语言：**通用原则适用任何语言**，示例以 Java（Javadoc）为主；Go/Python/JS 等对照语言习惯套用。

## 强制规则

### 1. 覆盖范围（全量强制，无豁免）

以下**全部必须写注释**（Java=Javadoc，其他语言对应 doc 注释）：

| 目标 | 注释要求 | 说明 |
|------|----------|------|
| 所有类 / 接口 | 类注释 | 一切类皆需，DTO/VO/Config/Entity 等仅示例非穷举，**一个都不能漏** |
| 所有变量 / 字段 | 字段注释 | 一切变量皆需：DTO/VO/Config 字段、private 字段、static 常量、测试数据变量（仅示例非穷举） |
| 所有方法 / 函数 | 方法注释 | 含 Controller/Service/Mapper 方法、private 方法、**测试方法** |
| 方法体 | 步骤注释 | 方法内按业务步骤编号注释（见 §5） |

**无豁免场景**：DTO/VO 的每个字段都要注释；Config 的每个配置项都要注释；测试方法也要方法注释；一个类即使只有一个字段也要类注释 + 字段注释。

### 2. 类注释：写清楚「这个类是做什么的」

所有类/接口必须类注释，第一句概述该类职责（做什么、服务谁），禁止只写类名复述。

```java
/**
 * 登录认证 Controller：负责登录、登出、当前用户信息查询与自助改密。
 */
@RestController
@RequestMapping("/auth")
public class AuthController {
```

✅ 正例：
```java
/**
 * 用户管理服务：用户分页查询、新增、编辑、分配角色、启禁用、重置密码、删除。
 */
```
❌ 反例（只复述类名，无职责说明）：
```java
/**
 * UserService。
 */
```

### 3. 变量/字段注释：写清楚「这个变量的意义」

所有变量/字段必须注释，写清业务含义、取值约束（枚举范围、单位、空值语义）。

```java
public class UserSaveDTO {
    /** 用户名，唯一，1-50 字符。 */
    private String username;

    /** 初始密码，BCrypt 加密存储，首登强制改密。 */
    private String password;

    /** 状态：0 启用 1 禁用。 */
    private Integer status;
}
```

- 枚举取值写清每个值的含义（如「0 启用 1 禁用」）
- 单位写清（如「金额单位分」「时间戳毫秒」）
- 可空性写清（如「可空，空表示全部」）
- 反例：`/** 状态。 */ private Integer status;`（没写意义）

### 4. 方法注释：功能 + 入参 + 出参

所有方法（含测试方法）必须方法注释：
- 第一句：这个方法做什么（动词开头，说明职责与结果）
- `@param`：每个参数的业务含义 + 约束（禁止只重复参数名）
- `@return`：返回值的业务含义（禁止只写类型名）
- `@throws`：异常条件（抛出业务异常时写清触发场景）

```java
/**
 * 分页查询订单列表。
 *
 * @param userId   用户 ID，不可为空
 * @param status   订单状态，可空（空表示全部）
 * @param pageNum  页码，从 1 开始
 * @param pageSize 每页条数，最大 100
 * @return 订单分页结果，不含已删除订单
 * @throws BusinessException 用户不存在时抛出
 */
PageResult<OrderVO> queryPage(Long userId, String status, int pageNum, int pageSize);
```

测试方法同样需要：
```java
/**
 * 用例：登录成功（admin）应返回 token 与完整菜单树。
 */
@Test
void loginShouldReturnTokenAndMenuTreeForAdmin() {
```

✅ 正例（写明业务含义 + 约束）：
```java
/**
 * 计算订单实付金额。
 * @param order 订单，含商品明细与优惠信息，不得为 null
 * @return 实付金额，单位分；整单免单时返回 0
 * @throws IllegalArgumentException order.status 非 PAID 状态
 */
```
❌ 反例（只重复参数名，无业务含义）：
```java
/**
 * @param order 订单
 * @return 金额
 */
```

### 5. 方法内步骤注释：编号 + 说明该步做什么

**所有方法体按业务逻辑步骤编号注释**，格式：`// N. 步骤名：该步做什么`。粒度到「业务步骤」而非「逐行翻译」。

- 编号从 1 开始连续递增
- 每步用动词短语概括（参数提取 / 校验 / 查库 / 构建 / 返回）
- 步骤注释说明「该步的业务目的」，不是代码复述

示例（排课方法，9 步）：
```java
/**
 * 排课：校验老师/课程/时间/教室/当日课量后插入排课记录。
 *
 * @param request 排课请求（老师 ID、课程 ID、教室、开始/结束时间）
 * @return true 排课成功
 * @throws BusinessException 校验失败或插入失败
 */
public boolean scheduleClass(ScheduleRequest request) {
    // 1. 参数提取：从请求对象中取出老师ID、课程ID、教室、开始时间、结束时间
    Long teacherId = request.getTeacherId();
    Long courseId = request.getCourseId();
    String classroom = request.getClassroom();
    LocalDateTime startTime = request.getStartTime();
    LocalDateTime endTime = request.getEndTime();

    // 2. 基础校验：检查参数是否为空、时间是否合法（开始时间必须早于结束时间）
    if (teacherId == null || courseId == null || startTime == null || endTime == null
            || !startTime.isBefore(endTime)) {
        throw new BusinessException("参数非法");
    }

    // 3. 检查老师是否存在：根据老师ID查数据库，不存在则抛异常
    Teacher teacher = teacherMapper.selectById(teacherId);
    if (teacher == null) {
        throw new BusinessException("老师不存在");
    }

    // 4. 检查课程是否存在：根据课程ID查数据库，不存在则抛异常
    Course course = courseMapper.selectById(courseId);
    if (course == null) {
        throw new BusinessException("课程不存在");
    }

    // 5. 检查老师该时段是否已有课（时间冲突检测）
    if (scheduleMapper.existsConflict(teacherId, startTime, endTime)) {
        throw new BusinessException("老师该时段已有课");
    }

    // 6. 检查教室该时段是否被占用
    if (scheduleMapper.existsRoomOccupied(classroom, startTime, endTime)) {
        throw new BusinessException("教室该时段被占用");
    }

    // 7. 检查老师当日排课数量是否超标（如一天最多6节）
    if (scheduleMapper.countByTeacherAndDate(teacherId, startTime.toLocalDate()) >= 6) {
        throw new BusinessException("当日排课已满");
    }

    // 8. 构建排课实体对象并插入数据库
    Schedule schedule = Schedule.builder()
            .teacherId(teacherId).courseId(courseId)
            .classroom(classroom).startTime(startTime).endTime(endTime)
            .build();
    scheduleMapper.insert(schedule);

    // 9. 返回结果：插入成功返回true，失败抛异常或返回false
    return schedule.getId() != null;
}
```

规则细则：
- 方法体含 **≥2 个逻辑步骤** → 必须编号注释
- 方法体为单行/纯转发（如 `return mapper.selectById(id);`）→ 可省略步骤注释，但**方法注释仍必须**
- 已有 `// WHY:` 解释动机的地方，步骤注释与 WHY 注释并存，不冲突
- **步骤注释聚焦「业务阶段 + 该步做什么」，禁止复述代码实现细节**（区别见下）：
  - ✅ 业务视角：`// 5. 检查老师该时段是否已有课（时间冲突检测）`、`// 8. 构建排课实体对象并插入数据库`（该步的业务操作）
  - ❌ 代码视角（= 翻译式，触碰 §7 红线）：`// 8. 调用 scheduleMapper.insert 插入`（复述方法调用）、`// 2. 用 isBefore 比较开始结束时间`（复述 API 调用）
  - 判据：步骤注释用**业务词汇**（老师/课程/时段/落库），不用**代码词汇**（调用 xxx 方法 / 执行 insert / 遍历 list）
- **改代码必须同步步骤注释（含重新编号）**：增删/调整步骤后，编号连续重排，注释描述与代码事实一致
- 步骤注释粒度到「业务阶段」；一个阶段内多行代码只写一条注释，禁止每行一条

### 6. 行内注释：解释「为什么」，不解释「是什么」

- 复杂逻辑写 `// WHY:` 注释解释"为什么这么做"
- 反例：`int total = price * count; // 价格乘以数量`（逐行翻译式，禁止）
- 反例：`int i = 0; // 将 i 设为 0`
- 正例：`// WHY: 先扣库存再创建订单，避免超卖窗口`
- 魔法值必须注释或提取常量

> 区分「步骤注释」与「翻译式注释」：步骤注释描述业务阶段（`// 5. 检查老师该时段是否已有课`），翻译式注释复述代码（`// 价格乘以数量`）。前者强制，后者禁止。

### 7. 禁止事项

- ❌ 注释掉的代码（用 git 历史管理）
- ❌ 一整块代码全行注释（改为提取方法）
- ❌ 无意义注释：`// TODO 优化`（无具体事项）、`// 处理中` 等
- ❌ 与代码不一致的过时注释（改代码必改注释）
- ❌ 逐行翻译代码式注释（`// 价格乘以数量`）
- ❌ 描述代码中不存在的行为（注释必须与代码事实一致）

## 反例 / 正例

```java
// 反例：类无注释、字段无注释、方法无注释、方法体无步骤
public class OrderService {
    private OrderMapper mapper;
    public List<Order> getOrders(Long id) {
        List<Order> list = mapper.selectList(
            new LambdaQueryWrapper<Order>().eq(Order::getUserId, id));
        return list;
    }
}

// 正例：类注释 + 字段注释 + 方法注释 + 步骤注释
/**
 * 订单查询服务：按用户查询订单列表。
 */
public class OrderService {
    /** 订单表 Mapper。 */
    private final OrderMapper mapper;

    /**
     * 查询用户的全部订单。
     *
     * @param userId 用户 ID，不可为空
     * @return 该用户的订单列表，按创建时间倒序，不含已删除订单
     */
    public List<Order> getOrders(Long userId) {
        // 1. 参数校验：userId 不可为空
        if (userId == null) {
            throw new IllegalArgumentException("userId 不可为空");
        }
        // 2. 查询：按用户过滤 + 软删除过滤 + 时间倒序
        return mapper.selectList(new LambdaQueryWrapper<Order>()
                .eq(Order::getUserId, userId)
                .eq(Order::getDeleted, 0)
                .orderByDesc(Order::getCreateTime));
    }
}
```

## 最佳实践

- 注释解释意图与约束，代码本身表达实现
- 复杂算法（如分库分表路由、状态机）必须注释设计思路
- 特殊业务规则（如「金额单位为分」「时间存 UTC」）注释在字段/常量处
- 团队约定写入统一文档注释头模板（版权、作者、日期按团队要求）
- 与 Lombok 配合：优先用 `@Data`/`@Getter` 生成 getter/setter（免手写注释）；手写 getter/setter 时同样加注释

## 自检清单

- [ ] 每个类（一切类皆需，DTO/VO/Config 等仅示例非穷举）有类注释，写清「这个类做什么」
- [ ] 每个变量/字段（一切字段皆需，含 DTO/VO/Config 字段、常量）有注释，写清业务含义与约束
- [ ] 每个方法（含 private、测试方法）有方法注释：功能 + @param + @return（测试方法写用例目的）
- [ ] 方法体 ≥2 个逻辑步骤时，步骤注释编号连续、每步说明做什么
- [ ] 步骤注释是业务视角（阶段+该步做什么），无代码实现复述（无「调用 xxx 方法」类翻译）
- [ ] 步骤注释与代码同步（增删步骤后编号已重排）
- [ ] @param/@return 有业务含义，不重复参数名，写明约束（如"不得为 null"）
- [ ] 无逐行翻译代码式注释（无 `// 价格乘以数量` 类注释）
- [ ] 复杂逻辑有 `// WHY:`（非显而易见逻辑有"为什么"注释）
- [ ] 注释与代码一致（抽查：注释描述的行为代码真实存在，无编造意图）
- [ ] 无注释掉的代码
- [ ] 无 TODO 无实义注释
