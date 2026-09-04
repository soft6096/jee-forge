# Service 规范 (Service Standards)

## 适用范围

生成 Service 接口时加载。定义接口设计原则、方法粒度、命名。

## 强制规则

### 1. 接口定位

- Service 接口描述业务能力，不含实现细节（不引用 Mapper、不声明 SQL 相关概念）
- 一个业务域一个接口：`OrderService`、`UserService`
- 接口名 = 领域名词 + Service

### 2. 方法设计

- 方法名用业务动词：`submitOrder`、`cancelOrder`、`queryPage`，不用 `doXxx`、`handleXxx`
- **接口方法不写访问修饰词**（隐式 public，见命名规范 §8）：`PageResult<RoleVO> queryRoleList(...)`，禁止 `public PageResult<RoleVO> ...`
- **参数名 = 类型小驼峰或角色语义名**：`RoleSaveDTO roleSaveDTO`，禁止 `dto` / `query` / `e` 泛称
- **返回集合的方法名以类型后缀结尾**：`getPermissionTreeList()`（返回 List）、`resolvePermCodeSet()`（返回 Set）
- 参数用 DTO 聚合，避免长参数列表（> 3 个包装为 DTO）

```java
// 反例
OrderVO query(Long userId, String status, Integer pageNum, Integer pageSize,
              String startTime, String endTime, Long shopId);

// 正例（无 public、参数语义名）
PageResult<OrderVO> queryOrderPage(OrderQueryDTO orderQueryDTO);
```

- 返回类型面向调用方：列表返回 `List<VO>` 或 `PageResult<VO>`，不返回 Map
- 方法职责单一：一个方法一个业务动作，禁止「查询 + 更新」混在一个方法

### 3. 事务边界声明

- 事务标注在实现类方法上（见 service-impl 规范），接口不写 `@Transactional`

### 4. 异常声明

- 接口方法不写 `throws`，业务异常运行时抛出，由全局处理器统一处理

## 反例 / 正例

```java
// 反例：接口泄漏实现概念
public interface OrderService {
    PageResult<Order> selectOrderPage(IPage<Order> page, @Param("userId") Long userId);
    void updateOrderStatus(Long id, Integer status);  // 过于底层
}

// 正例
public interface OrderService {
    PageResult<OrderVO> queryOrderPage(OrderQueryDTO orderQueryDTO);
    void submitOrder(Long orderId);
    void cancelOrder(CancelOrderDTO cancelOrderDTO);
}
```

## 最佳实践

- 接口注释写清业务规则（状态流转约束、幂等性），实现类注释写技术细节
- 跨服务调用（Feign/RPC）在接口注释标注超时与重试语义
- 只暴露业务需要的操作，不暴露全量 CRUD（内部批量操作可不下沉接口）
- 领域动词统一：submit/cancel/confirm/refund，避免同义混用（submit/commit/doSubmit）

## 自检清单

- [ ] 接口描述业务能力，无实现细节
- [ ] 方法名业务动词，无 do/handle 泛化命名；返回集合以 xxxList/xxxSet/xxxMap 结尾
- [ ] 接口方法无 public 修饰词
- [ ] 参数语义名（无 dto/query/e 泛称）
- [ ] 参数 > 3 个已包装 DTO
- [ ] 返回类型面向调用方（VO/PageResult）
- [ ] 无事务注解
- [ ] 无 throws 声明
