# API 文档规范 (API Documentation Standards)

## 适用范围

生成接口文档注解（SpringDoc/OpenAPI/knife4j）、评审接口文档时加载。

## 文档平台（Apifox 兼容）

- 代码侧统一 OpenAPI 注解（本规范），与文档平台**解耦**——**Apifox 支持 OpenAPI 导入**（项目级"导入 OpenAPI"同步接口），注解照常写，与"用 Apifox 不用 Swagger"的团队约定不冲突
- 团队用 Apifox 时：Apifox 为接口文档事实源（在线协作/联调/Mock），OpenAPI 注解随代码维护供同步；knife4j 仅作离线导出备选
- 存量项目已用 Apifox（不用 Swagger/knife4j）→ 以老项目约定为准（见 ai-dev-workflow 存量适配模式，规范仅兜底）

## 依赖与启用配置（项目初始化必配，缺依赖注解不生效）

- **依赖必须引入**（见 build-standards `dependency-standards.md` 接口文档依赖章节）：
  - Spring Boot 3.x → `springdoc-openapi-starter-webmvc-ui`（注解 `@Tag`/`@Operation`/`@Schema` 来自 `io.swagger.v3.oas.annotations.*`）
  - 团队要 knife4j 增强 UI（离线导出/权限/OpenAPI3 聚合）→ 再加 `knife4j-openapi3-jakarta-spring-boot-starter`，版本与 springdoc 对齐
- **开关按环境配置**（`application.yml` + profile 覆盖）：dev/qa 开启，online 关闭（防接口信息泄露）

```yaml
# application.yml
springdoc:
  api-docs:
    enabled: ${SPRINGDOC_ENABLED:true}   # dev/qa 开启
  swagger-ui:
    enabled: ${SPRINGDOC_ENABLED:true}

# application-online.yml
springdoc:
  api-docs:
    enabled: false                       # online 关闭
  swagger-ui:
    enabled: false
```

- 生成 Controller/DTO/VO 时注解必须与依赖配套；依赖未引入 → 先补依赖再写注解，禁止"注解写好但依赖缺失"（编译报错）

## 强制规则

### 1. 注解使用

- 接口文档用 OpenAPI 注解（`@Tag`/`@Operation`/`@Schema`），与 Controller/DTO 同步维护
- 类级 `@Tag(name = "订单管理", description = "...")`，方法级 `@Operation(summary = "创建订单", description = "...")`
- DTO/VO 字段用 `@Schema(description = "...")`，与校验注解并存

```java
@Tag(name = "订单管理", description = "订单查询与操作")
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @Operation(summary = "创建订单", description = "创建订单，返回订单号")
    @PostMapping
    public Response<OrderVO> create(@Validated @RequestBody OrderCreateDTO createInfo) {
        return Response.success(orderService.create(createInfo));
    }
}
```

```java
public class OrderCreateDTO {
    @Schema(description = "用户ID", requiredMode = REQUIRED)
    @NotNull(message = "用户ID不能为空")
    private Long userId;

    @Schema(description = "商品SKU", requiredMode = REQUIRED)
    @NotBlank(message = "商品SKU不能为空")
    private String skuId;
}
```

### 2. 文档与代码一致

- 接口签名变更 → 同步改注解（文档是接口契约一部分，过期文档误导联调）
- 响应结构返回 `Response<T>` 泛型，让文档展示真实响应结构（禁 Map 裸返回，文档不可读）

### 3. 禁止事项

- ❌ 暴露 Entity 作为接口出入参（文档泄露表结构 + 多余字段；用 DTO/VO）
- ❌ 敏感字段进文档示例（示例值用脱敏假数据）
- ❌ 无注解裸接口（文档自动生成但无业务语义）
- ❌ 文档注解与校验逻辑冲突（@Schema required 与 @NotNull 不一致）

### 4. 环境

- 文档开关配置化：dev 环境开启，prod 按需关闭（防接口信息泄露）
- 离线文档导出（knife4j 导出 markdown/openapi json）进版本管理，随接口变更同步

### 5. API 版本化

- 接口演进统一版本策略，禁止破坏性变更直接改老接口

| 方案 | 实现 | 适用 |
|---|---|---|
| URL 版本（推荐） | `/api/v1/orders`、`/api/v2/orders` | 对外 API，简单直观 |
| Header 版本 | `Accept: application/vnd.xx.v2+json` | 内部服务，路径稳定 |

- 团队选一，禁止混用
- 破坏性变更（字段改名/删除、语义变化、响应结构变化）→ 必须升版本，不静默改老接口
- 兼容性变更（加可选字段、加接口）→ 不升版本，老版本继续可用
- 老版本下线：提前公告 + 过渡期（建议 ≥ 6 个月），明确下线时间
- Controller 映射带版本：`@RequestMapping("/api/v1/orders")`，新版复制改 v2，不原地改

## 自检清单

- [ ] springdoc/knife4j 依赖已引入（无依赖注解不生效）
- [ ] 文档开关按环境配置（online 关闭）
- [ ] 类/方法/字段有 OpenAPI 注解
- [ ] 出入参用 DTO/VO，无 Entity 暴露
- [ ] 注解与校验一致
- [ ] 示例无敏感数据
- [ ] 破坏性变更已升版本，无静默改老接口
