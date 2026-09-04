# 安全规范 (Security Standards)

## 适用范围

生成涉及认证鉴权、用户输入处理、文件上传、数据脱敏的代码时加载。Java 服务端安全基线，AI 生成代码必须满足。

## 强制规则

### 1. 认证鉴权

- 登录态统一走 Spring Security（或团队选定框架），禁止自研 Session 管理
- Token 方案统一：JWT（无状态）或 Session（有状态），团队选一，禁止混用
- JWT 密钥走环境变量/配置中心，禁止硬编码在代码或提交仓库
- 接口权限统一 `@PreAuthorize` / `@RequiresPermissions` 注解，权限码格式 `模块:资源:操作`

```java
@GetMapping("/{id}")
@PreAuthorize("hasAuthority('order:query')")
public Response<OrderVO> getById(@PathVariable Long id) {
    return Response.success(orderService.getById(id));
}
```

- 登录接口限流（防爆破）：验证码/失败次数锁定/速率限制
- 密码存储：BCrypt 等慢哈希 + 盐，禁止 MD5/SHA1 裸存

### 2. 越权防护（IDOR）

- 资源访问必须校验归属：查当前登录用户，禁止仅凭前端传参可信

```java
// 反例：任何登录用户可查他人订单
public OrderVO getById(Long orderId) {
    return orderService.getById(orderId);
}

// 正例：校验订单归属当前用户
public OrderVO getById(Long orderId) {
    Long userId = SecurityUtils.getUserId();
    OrderVO orderVO = orderService.getById(orderId);
    if (!orderVO.getUserId().equals(userId)) {
        throw new BusinessException(ErrorCode.FORBIDDEN, "无权访问该订单");
    }
    return orderVO;
}
```

- 水平越权（他人数据）与垂直越权（低权限调高权限接口）都须防护

### 3. SQL 注入

- 所有 SQL 值参数化（`#{}`/PreparedStatement），禁止字符串拼接 SQL
- 动态排序/表名白名单校验，禁止用户输入直入 `${}` / `order by`
- MyBatis-Plus：禁止 `apply()`/`last()` 传用户输入

### 4. XSS 与输出编码

- 用户输入回显处转义（前端框架默认转义 + 后端过滤富文本白名单）
- 禁止 `innerHTML` 直接插入用户输入（前端）
- 存储用户输入前做长度/格式校验，不信任任何输入

### 5. 文件上传

- 类型白名单（扩展名 + MIME 双重校验），禁止仅校验扩展名
- 大小上限（如 10MB），超限拒绝
- 文件名重命名（UUID），禁止使用用户原始文件名（路径穿越 + 覆盖攻击）
- 存储路径不可执行（独立静态目录/对象存储，非应用 webroot）

```java
// 正例：白名单 + 重命名
private static final Set<String> ALLOWED_TYPES = Set.of("jpg", "png", "pdf");

public String upload(MultipartFile file) {
    String ext = StringUtils.getFilenameExtension(file.getOriginalFilename());
    if (!ALLOWED_TYPES.contains(ext.toLowerCase())) {
        throw new BusinessException(ErrorCode.BAD_REQUEST, "不支持的文件类型");
    }
    if (file.getSize() > 10 * 1024 * 1024) {
        throw new BusinessException(ErrorCode.BAD_REQUEST, "文件超过10MB");
    }
    String filename = UUID.randomUUID() + "." + ext;   // 重命名，非用户原文件名
    // 存到独立存储目录
}
```

### 6. 敏感数据

- 手机号/身份证/银行卡存储加密或脱敏，日志/接口输出脱敏（`138****1234`）
- 密码/密钥/Token 禁止进日志、异常消息、接口响应
- 接口返回不暴露内部字段（IDOR 利用面）：VO 只含必要字段
- 日志脱敏：统一日志切面处理敏感字段

### 7. 安全头（Web 层）

- 响应加安全头：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`（防点击劫持）、`Content-Security-Policy`
- CSRF：无状态 JWT 方案天然免疫，Session 方案启用 CSRF 防护
- CORS 白名单配置，禁止 `*` 全放开（含凭据请求禁止 `*`）

## 反例 / 正例

```java
// 反例：未校验归属 + 拼接 SQL + 敏感信息进日志
public List<Map<String, Object>> search(String keyword) {
    log.info("search: {}", keyword);                    // 无业务上下文
    return mapper.query("SELECT * FROM t_order WHERE title LIKE '%" + keyword + "%'");  // 注入
}

// 正例
public PageResult<OrderVO> search(OrderQueryDTO query) {
    SecurityUtils.checkPermission("order:query");
    return orderService.search(query);                  // Service 层参数化查询
}
```

## 自检清单

- [ ] 接口有权限注解，资源访问校验归属（无 IDOR）
- [ ] SQL 全参数化，无拼接注入
- [ ] 密码慢哈希存储，密钥无硬编码
- [ ] 文件上传白名单 + 大小限制 + 重命名
- [ ] 敏感字段脱敏，不进日志/响应
- [ ] 登录有限流/防爆破
- [ ] 安全头 + CORS 白名单
