# 契约测试规范 (Contract Test Standards)

## 适用范围

编写接口契约测试、对接 ai-dev-workflow 4.2 契约测试流程时加载。契约测试 = 把技术方案里的验收场景翻译成可执行测试，先红后绿，作为 AI 编码的验收标准。

## 强制规则

### 1. 测试是验收标准

- 契约测试直接翻译技术方案的「验收场景」（合法 + 非法 + 边界 三态）
- 测试文件是验收标准：**禁止修改断言、禁止删除测试、禁止 @Disabled**（AI 编码不得改测试迁就实现）
- 每个验收场景至少一个测试用例，一一对应可追溯

### 2. 覆盖三态

| 场景态 | 说明 | 例 |
|---|---|---|
| 合法 | 正常路径，断言成功结果 | 创建订单 → 返回订单号 |
| 非法 | 参数/权限/状态非法，断言拒绝 | 商品不存在 → 400 + 错误码 |
| 边界 | 临界值/并发/重复/空值 | 库存=0、超时、重复提交幂等 |

- 禁止只测合法路径（非法/边界缺失 = 测试有洞）

### 3. 接口契约测试

- HTTP 接口：`@SpringBootTest + MockMvc`（WebMvc）或 `@WebMvcTest` 切片 + MockMvc，断言状态码 + 响应体结构 + 错误码
- 契约关注：入参校验、响应结构（`Response` code/message/data）、错误码映射、权限
- 不测业务细节（那是单测职责），只测接口边界

```java
/**
 * 用例：非法入参（用户不存在）应返回 400 + 错误码。
 */
@WebMvcTest(OrderController.class)
class OrderControllerContractTest {

    @Autowired
    MockMvc mockMvc;

    @MockBean
    OrderService orderService;

    @Test
    void createOrderShouldReturn400WhenUserNotExist() throws Exception {
        when(orderService.create(any())).thenThrow(new BusinessException(ErrorCode.USER_NOT_FOUND, "用户不存在"));

        mockMvc.perform(post("/api/orders")
                        .contentType(APPLICATION_JSON)
                        .content("{\"userId\":999,\"skuId\":\"SKU001\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(ErrorCode.USER_NOT_FOUND.getCode()))
                .andExpect(jsonPath("$.message").value("用户不存在"));
    }
}
```

### 4. 先红后绿

- 新功能契约测试**先写先跑一遍确认是红的**（红 = 测试正确捕获了未实现行为）
- 红的原因必须是「实现不存在」，不是「测试写错」
- 编码后测试变绿 = 功能达标

### 5. 归属与维护

- 契约测试放 `src/test/java/<对应包>/`，按接口分组命名 `XxxContractTest`
- **测试方法名英文驼峰**：`被测行为 + 条件 + 期望`（`createOrderShouldReturn400WhenUserNotExist`），禁止中文/拼音方法名；用例场景中文写方法 Javadoc
- 技术方案变更 → 同步改契约测试（方案是契约，测试是落地）
- 契约测试与实现解耦：不依赖实现细节，只依赖接口契约

## 反例 / 正例

```java
// 反例：只测合法路径 + 断言实现细节
/**
 * 用例：创建订单（反例——不关心内部调用）。
 */
@Test
void createOrderShouldWork() {
    // 断言内部 mapper 调用次数 —— 契约测试不应关心
    verify(orderMapper).insert(any());
}
```

```java
// 正例：三态覆盖
/**
 * 用例：合法入参创建订单应返回 200。
 */
@Test
void createOrderShouldReturn200WhenValid() { /* 合法 */ }
/**
 * 用例：非法入参（商品不存在）应返回 400。
 */
@Test
void createOrderShouldReturn400WhenSkuNotExist() { /* 非法 */ }
/**
 * 用例：重复提交应返回 409（幂等）。
 */
@Test
void createOrderShouldReturn409WhenDuplicateSubmit() { /* 边界：幂等 */ }
```

## 自检清单

- [ ] 三态（合法/非法/边界）全部覆盖
- [ ] 断言状态码 + 错误码 + 响应结构
- [ ] 方法名英文驼峰，用例中文写 Javadoc
- [ ] 与验收场景一一对应
- [ ] 先红后绿流程执行
- [ ] 无修改断言/删除测试/Disabled
- [ ] 不依赖实现细节
