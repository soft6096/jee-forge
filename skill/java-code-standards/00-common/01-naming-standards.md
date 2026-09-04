# 命名规范 (Naming Standards)

## 适用范围

生成任意 Java 代码前必读。适用于类、方法、变量、常量、包名、枚举、泛型等全部标识符。

## 强制规则

### 1. 包名

- 全部小写，单词间无分隔符
- 反例：`com.Company.Order` / `com.company_name`
- 正例：`com.example.hotel.order`
- **每种职责对象独立分包，同类放同一包，禁止混放**。DTO 与 VO 必须分属 `dto` / `vo` 两个独立包，严禁混在同一包：

| 层 | 包 | 说明 |
|---|---|---|
| Controller | `com.example.order.controller` | 接口层 |
| Service 接口/实现 | `com.example.order.service` / `com.example.order.service.impl` | 业务层 |
| Mapper | `com.example.order.mapper` | 持久层接口 |
| 实体 | `com.example.order.domain` | 数据库实体 |
| 请求对象 | `com.example.order.dto` | 入参（DTO） |
| 出参对象 | `com.example.order.vo` | 出参（VO），**与 dto 分属两个包** |
| 通用组件 | `com.example.order.common.*` | 工具/异常/统一返回体等 |
| 配置 | `com.example.order.config` | 配置类 |

- **同类对象不混放**：`dto` 包只放请求入参类，`vo` 包只放出参类，`domain` 只放实体——VO 放进 dto 包、DTO 放进 vo 包均属违规
- 反例：
  - `com.example.order.controller.vo.MeVO`、`com.example.order.controller.dto.LoginDTO`（挂 controller 下）
  - `com.example.order.dto.UserVO`、`com.example.order.vo.LoginDTO`（DTO/VO 混包）
  - `com.example.order.dto` 同时放 `LoginDTO` 和 `MenuVO`（同类不纯）
- 正例：`com.example.order.vo.CurrentUserInfoVO`、`com.example.order.dto.LoginDTO`、`com.example.order.domain.Order`

### 2. 类名 / 接口名

- UpperCamelCase（帕斯卡命名）
- 名词或名词短语，避免动词开头
- 接口不加 `I` 前缀（除历史遗留），实现类加 `Impl` 后缀
- 反例：`userService`、`getUserData`、`IUserService`、`class A`、`class XxxUtil` 中的 `Util`（无业务含义，用 `XxxSupport`/`XxxHelper` 或并入领域类）
- 正例：`UserService`（接口）、`UserServiceImpl`（实现）、`OrderController`、`RoleService`
- **禁止单字母类名**（`class A` / `class B` / `class R` / `interface I` 均反例）
- **统一返回体类名固定为 `Response<T>`**，禁止 `R` / `Result` / `ResponseResult` 等其他命名；分页用 `PageResult<T>`（独立分页结构，非返回体）
- **类名表达业务语义，禁止中文直译/无领域含义缩写**：

```java
// 反例：中文直译（Me = 我）→ 无业务语义
public class MeVO { ... }
public class GetInfoDTO { ... }

// 正例：业务语义命名（当前用户信息）
public class CurrentUserInfoVO { ... }
```

- DTO/VO 类名 = 「领域概念 + 后缀」：`CurrentUserInfoVO`、`OrderQueryDTO`、`RoleAssignDTO`
- 禁止：`MeVO`（Me 无领域概念）、`InfoDTO`（Info 无领域概念）、`UserInfoDTO`（Info 冗余，若语义就是用户信息则 `UserDTO` 或 `UserVO`）
- 判据：类名去掉后缀（VO/DTO）后，剩余部分必须是**领域术语**（CurrentUserInfo / OrderQuery / RoleAssign），能独立表达业务概念

### 3. 方法名

- lowerCamelCase（驼峰命名）
- 动词或动词短语，语义清晰
- 分层约定：
  - Controller：`get/create/update/delete` 前缀，如 `getOrderById`
  - Service：`query/save/modify/remove` 或领域动词，如 `queryPage`、`submitOrder`
  - Mapper：`select/insert/update/delete` 前缀，如 `selectList`、`insertBatch`
- 布尔返回方法：`is/has/can/should` 前缀，如 `isValid`、`hasPermission`
- **禁止单字母方法名**（`void a()` / `int b()` 反例）
- 反例：`handleData`、`doStuff`、`getOrderInfoByIdAndStatus`、`void run()`（无业务语义）

### 4. 变量名

#### 核心原则

- lowerCamelCase，表达**语义角色**（这个变量是谁、从哪来、干什么用），见名知意，不依赖注释
- 命名模板：**`[来源/角色限定] + [领域词] + [类型/角色后缀]`**，如 `existingUser` / `loginResult` / `accessToken`
- 变量名 2~3 个词最佳；单个单词仅限领域原子概念（`id` / `name` / `status` / `quantity`）
- **一票判定**：删掉类型声明后，名字能否独立回答「它是谁、从哪来、干什么用」——答不出即反例

#### 反模式分类（对号入座，命中即改）

| # | 反模式 | 特征 | ❌ 反例 | ✅ 正例 |
|---|--------|------|---------|---------|
| 1 | 单字母 | 变量只有一个字母 | `e` `p` `s` `d` | `exception` `sysPermission`（循环索引 `i/j/k` 豁免） |
| 2 | 无意义简写 | 泛称后缀，无业务信息 | `vo` `dto` `query` `result` `info` `data` `obj` `req` `resp` `param` `item` `entity` | `loginResult` `orderQuery` `saveInfo` `userItem` → 具体到 `roleItem` |
| 3 | 类型机械小驼峰 | 变量名 = 类型名改小写，无角色信息 | `User user` `Token token` `LoginVO vo` `OrderCreateDTO dto` | `existingUser` `accessToken` `loginResult` `orderCreateInfo` |
| 4 | 单单词泛指 | 有领域词但缺来源/角色，上下文有歧义 | `user`（查出的还是入参？）`token`（哪种？）`name`（谁的？）`list` `map` `config` | `existingUser` `accessToken` `userName` `orderList` `roleMap` `mybatisConfig` |
| 5 | 同类不区分 | 同方法多个同类变量同名或不可辨 | 两个 `OrderVO orderVO`、两个 `String token` | `sourceOrderVO` / `targetOrderVO`、`accessToken` / `refreshToken` |
| 6 | 序号命名 | 数字后缀无语义 | `user1` `user2` `data1` `data2` `token2` | `sourceUser` `targetUser` `primaryData` `fallbackData` `newToken` |
| 7 | 拼音 | 拼音当变量名 | `shuliang` `yonghu` `zhunbei` | `quantity` `user` `prepared` |

#### 来源 / 角色限定词（给单单词补身份）

- 来源：`existing`（库中已存在）/ `current`（当前）/ `cached`（缓存）/ `db`（库里）/ `input` / `output` / `new` / `old`
- 关系：`source` / `target`（转换源目标）、`first` / `second`（次序）、`primary` / `fallback`（主备）
- 类型后缀：DTO → `CreateInfo` / `Query` / `UpdateInfo`；VO → `Result` / `Detail` 或领域语义；Token → `AccessToken` / `RefreshToken` / `AuthToken`

```java
// 反例：覆盖反模式 1/2/3/4/5/6
OrderVO vo;                  // #2
SysUser user;                // #3/#4
String token;                // #3/#4
OrderVO orderVO, orderVO2;   // #5/#6
for (SysPermission p : permissionList) { ... }   // #1
catch (Exception e) { ... }  // #1

// 正例
LoginVO loginResult;         // 登录结果
SysUser existingUser;        // 库中已存在用户
String accessToken;          // 访问令牌
OrderVO sourceOrderVO;       // 源订单（转换）
OrderVO targetOrderVO;       // 目标订单
for (SysPermission sysPermission : sysPermissionList) { ... }
catch (Exception exception) { ... }
```

- **同类型多变量并存，用语义限定词区分**（来源/关系/用途），禁止同名或序号

```java
OrderVO cachedOrderVO = cache.get(key, OrderVO.class);   // 缓存中的
OrderVO dbOrderVO = orderService.getDetailFromDb(id);    // 库里的
String accessToken;                                       // 访问令牌
String refreshToken;                                      // 刷新令牌
```

- 基础类型直接语义命名：`String name`、`Map<Long, Order> orderMap`

#### 方法参数

- **参数名按角色命名（领域词 + 角色词，不机械重复完整类型名）**：

```java
public PageResult<OrderVO> queryPage(OrderQueryDTO orderQuery) { ... }   // 查询条件
public Long create(OrderCreateDTO createInfo) { ... }                    // 创建参数
public void update(Long id, OrderUpdateDTO updateInfo) { ... }           // 更新参数
public void cancelOrder(CancelOrderDTO cancelInfo) { ... }               // 取消参数
```

- **禁止泛称参数名**：`e` / `dto` / `query` / `response` / `req`（反例）→ `exception` / `roleQueryDTO` / `httpServletResponse`；有多个同类参数用角色前缀（`sourceOrderVO` / `targetOrderVO`）
- **异常处理参数禁止单字母 `e`**（覆盖 `catch` 与 `@ExceptionHandler` 方法参数）：参数名 = 类型名小驼峰

```java
@ExceptionHandler(ServiceException.class)
public Response<Void> handleServiceException(ServiceException serviceException) { ... }

@ExceptionHandler(MethodArgumentNotValidException.class)
public Response<Void> handleValidationException(MethodArgumentNotValidException methodArgumentNotValidException) { ... }

@ExceptionHandler(BindException.class)
public Response<Void> handleBindException(BindException bindException) { ... }

@ExceptionHandler(Exception.class)
public Response<Void> handleException(Exception exception) { ... }

// catch 同理
catch (ServiceException serviceException) { ... }
catch (Exception exception) { ... }
```

- **分页参数对象用语义名 `pageResult` / `pageQuery`**（禁止裸 `page` 单单词泛指）：`IPage<SysUser> pageResult`（MyBatis-Plus 分页对象，承载结果）；入参分页条件用 `PageQuery pageQuery`

#### 集合命名

- **集合字段/局部变量命名：统一 `xxxList` / `xxxSet` / `xxxMap` 后缀（按元素类型），禁止复数命名**：

```java
List<Long> permissionIdList;          // ✅ List → xxxList
Set<String> codeSet;                  // ✅ Set → xxxSet
Map<Long, Order> orderMap;            // ✅ Map → xxxMap
List<OrderVO> orderVOList;            // ✅ 统一 xxxList
List<Long> permissionIds;             // ❌ 复数命名（与团队约定冲突）
Set<String> codes;                    // ❌ 应 codeSet
List<T> records;                      // ❌ records 无语义 → recordList
List<T> recordList;                   // ✅ 当前页记录列表
```

- **返回集合的方法名以类型后缀结尾**：

```java
List<RoleVO> queryRoleList(RoleQueryDTO roleQueryDTO);   // ✅ 返回 List → 方法名 xxxList 结尾
Set<String> resolvePermCodeSet(Long userId);             // ✅ 返回 Set → xxxSet 结尾
List<RoleVO> queryRole(RoleQueryDTO roleQueryDTO);       // ❌ 未带 List 后缀
```

- **树/层级结构豁免（与字段豁免同一判据）**：返回树结构的方法保持语义名，`List<PermissionTreeVO> getPermissionTree()`（树不是平级列表，不加 List 后缀）
- **语义名豁免**：非"列表"语义的集合用业务名，`List<PermissionTreeVO> menuTree`（树结构不是列表集合，保持语义名）；判定：元素关系是「平级列表」→ xxxList；是「树/图/层级结构」→ 语义名
- 避免拼音、单字母（循环变量 `i/j/k` 除外）

### 5. 常量名

- 全大写 + 下划线分隔（`static final`）
- 反例：`static final int maxCount = 5`
- 正例：`static final int MAX_COUNT = 5`
- 枚举值同理：`DAY_STATUS_SUBMITTED`

### 6. 分层 DTO 命名后缀

| 类型 | 后缀 | 示例 |
|---|---|---|
| 请求入参 | DTO / Req | `OrderCreateDTO`、`OrderQueryDTO` |
| 出参 | VO | `OrderVO` |
| 数据库实体 | 无后缀 | `Order` |
| 业务接口 | Service | `OrderService` |
| 实现 | ServiceImpl | `OrderServiceImpl` |

### 8. 接口方法修饰词（Service/Mapper 接口）

- **接口方法不写访问修饰词**（隐式 `public abstract`，Java 惯例，写 `public` 是冗余）
- 反例：`public Response<Void> updateRole(...)`（接口内）
- 正例：

```java
public interface RoleService {
    PageResult<RoleVO> queryRoleList(RoleQueryDTO roleQueryDTO);   // 无 public
    void updateRole(RoleEditDTO roleEditDTO);
}
```

- 实现类方法写 `public`（类方法必须有访问修饰词）
- `default` 仅接口默认方法使用；`private` 仅 Java 9+ 接口私有方法使用

### 9. 缩写规则

- 缩写视为单词：`getUserId` 而非 `getUserID`
- 类名中：`UserIdDTO` 而非 `UserIDDTO`

## 反例 / 正例

```java
// 反例：命名混乱
public class userInfoController {
    private String USERNAME;
    public void handleData(String id, String status) {
        String s = USERNAME + id;
    }
}

// 正例
public class UserInfoController {
    private static final int MAX_PAGE_SIZE = 100;

    public UserVO getUserById(Long userId) {
        return userService.getUserById(userId);
    }
}
```

## 最佳实践

- 命名自文档化：读名字即知含义，不依赖注释
- 领域术语优先：业务词用团队统一词汇（见领域模型），如 `order` 不用 `transaction`
- 布尔字段命名避免 `is` 前缀（Lombok 生成歧义）：用 `submitted` 而非 `isSubmitted`
- 方法名避免 2 个以上动词叠加：`queryAndValidateAndSubmit` → 拆多个方法

## 自检清单

- [ ] 包名全小写；每种职责独立包，同类不混放；DTO/VO 分属 `dto` / `vo` 两包，不在 controller 包下
- [ ] 类 UpperCamelCase，接口无 `I` 前缀，实现带 `Impl`；无单字母类名（`R` 类反例）
- [ ] 类名业务语义（去后缀后是领域术语），无中文直译（MeVO 类反例）；统一返回体为 `Response<T>`
- [ ] 方法 lowerCamelCase，动词开头，分层前缀正确
- [ ] 变量名符合「来源/角色 + 领域词 + 类型后缀」模板，2~3 个词表达业务语义；无单字母、无泛称简写（vo/dto/data/obj）、无类型机械小驼峰（User user）、无单单词泛指（user/token/list）、无序号命名（user1）
- [ ] 同类型多变量已用实义限定词区分（existing/db/cached、source/target、accessToken/refreshToken）
- [ ] 参数名 = 角色语义名（无 e/dto/query/response 泛称）
- [ ] 集合命名统一 `xxxList` / `xxxSet` / `xxxMap` 后缀（树/层级结构豁免语义名）
- [ ] 返回集合的方法名以 xxxList/xxxSet/xxxMap 结尾（树/层级豁免）
- [ ] 接口方法无 public 修饰词
- [ ] 常量全大写 + 下划线
- [ ] DTO/VO/Entity 后缀正确
- [ ] 无拼音命名
