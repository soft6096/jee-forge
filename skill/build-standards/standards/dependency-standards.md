# 依赖管理规范 (Dependency Standards)

## 适用范围

添加/审查项目依赖、解决依赖冲突、设计依赖层级时加载。

## 强制规则

### 1. 依赖引入原则

- 加依赖前问：项目真需要吗？（一个方法可用 JDK 实现就不引库）
- 优先官方/主流库（Apache/Google/Spring 生态），小众库评估维护活跃度
- 同职责只选一个：JSON 库（Jackson/Gson 选一）、工具库（Guava/Hutool 选一），禁并存
- 新增依赖记到 README/依赖说明，注明用途

### 2. 版本策略

- 版本号统一在父 pom `dependencyManagement` 声明，子模块只写 groupId/artifactId（见 maven 规范）
- 优先使用 BOM 管理版本（Spring Boot BOM 已覆盖大部分）
- 重大升级（跨大版本）评估兼容性 + 回归测试，不盲目升
- 安全漏洞（CVE）依赖：及时升补丁版本，记录升级原因

### 3. scope 规范

| scope | 用途 | 注意 |
|---|---|---|
| compile（默认） | 运行时需要 | 主流依赖 |
| provided | 容器提供（servlet-api、lombok） | 不打包进产物 |
| runtime | 仅运行需要（JDBC 驱动） | 编译不需要 |
| test | 仅测试（JUnit/Mockito/Testcontainers） | 禁 compile 误用 |
| optional | 可选特性依赖 | 传递依赖不传播 |

- 测试依赖必须 `test` scope，禁止 `compile` 引入 JUnit/Mockito 等
- Lombok 用 `provided` + `optional`（编译期注解处理，不打进产物）

```xml
<!-- 正例 -->
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <optional>true</optional>   <!-- 不传递给下游 -->
</dependency>

<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <scope>test</scope>
</dependency>
```

### 4. 依赖冲突处理

- 冲突排查：`mvn dependency:tree` 定位重复版本，禁盲加 exclusion
- 处理顺序：统一版本（dependencyManagement 强制）→ 升级兼容 → 最后才 exclusion
- 多个传递依赖引同一库不同版本 → 父 pom 统一版本，禁散落 exclusion

```bash
mvn dependency:tree -Dincludes=com.google.guava
```

- 冲突修复后验证：构建 + 相关测试通过

### 4.5 数据库驱动版本（MySQL 实战红线）

- **MySQL 8 服务器必须配 Connector/J 8.x**（Spring Boot 3.x 已通过 BOM 管理版本，无需手写），**禁止 5.1.x 旧驱动**：旧驱动配 MySQL 8 有一串兼容问题——`characterEncoding=utf8mb4` 报 `Unsupported character encoding`、时区/加密协议（caching_sha2_password）不兼容、emoji 乱码
- 驱动版本统一由 Spring Boot BOM 管理，不手写版本号；确需覆盖时在父 pom `dependencyManagement` 声明

```xml
<!-- ✅ 正确：由 Spring Boot BOM 管理版本，不写版本号 -->
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <scope>runtime</scope>
</dependency>

<!-- ❌ 错误：手写 5.1.x 旧驱动版本（配 MySQL 8 会踩字符集/时区/加密协议坑） -->
<dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
    <version>5.1.49</version>
</dependency>
```

### 4.6 接口文档依赖（springdoc / knife4j，接口项目必配）

- **Controller 接口项目必须引入 springdoc-openapi**（OpenAPI 注解 `@Tag`/`@Operation`/`@Schema` 依赖它才生效，见 java-code-standards `01-java/api-doc-standards.md`）；版本由 Spring Boot BOM 管理，不手写版本号

```xml
<!-- ✅ Spring Boot 3.x：官方 starter（含 swagger-ui），版本由 BOM 管理 -->
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
</dependency>

<!-- Spring Boot 2.x 用：springdoc-openapi-ui -->
```

- 团队要 knife4j 增强 UI（离线导出/权限控制/OpenAPI3 聚合）→ 再加 knife4j starter，版本必须与 springdoc 兼容对齐（knife4j 依赖 springdoc 实现，配错版本注解不生效）

```xml
<dependency>
    <groupId>com.github.xiaoymin</groupId>
    <artifactId>knife4j-openapi3-jakarta-spring-boot-starter</artifactId>
    <version>4.x.x</version>   <!-- 版本与 springdoc-openapi 兼容对齐 -->
</dependency>
```

- 文档开关按环境配置：`springdoc.api-docs.enabled` dev/qa 开、online 关（见 java-code-standards `01-java/api-doc-standards.md`）
- 纯内部/无 HTTP 接口的模块（如仅 Job/Listener 的 service 模块）不需要该依赖

### 4.7 日志依赖（logback，默认即有，禁重复引）

- **Spring Boot 默认 Logback**（`spring-boot-starter-logging` 随 `spring-boot-starter-web` 传递引入），**无需也不应额外加 logback 依赖**——重复显式引 logback-classic 可能版本冲突
- 项目必须提供 `resources/logback-spring.xml` 自定义配置（控制台 + 滚动文件 + 环境级 level，见 java-code-standards `00-common/04-logging-standards.md` 与 `04-templates/logback-spring.xml`）
- 仅当团队明确改用 **Log4j2**：`spring-boot-starter-web`（或 `spring-boot-starter`）排除 `spring-boot-starter-logging`，再显式引 `spring-boot-starter-log4j2`；**Logback 与 Log4j2 禁止并存**（ClassLoader 里两个日志实现，输出混乱）

```xml
<!-- ✅ 改用 Log4j2：排除默认 logback -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-logging</artifactId>
        </exclusion>
    </exclusions>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-log4j2</artifactId>
</dependency>
```

### 5. 禁止事项

- ❌ 传递依赖带进来的多余库不清理（体积 + 安全面）
- ❌ 依赖版本写 `LATEST`/`RELEASE`（构建不可复现）
- ❌ 同一库多版本共存（类加载混乱，运行时诡异 bug）
- ❌ 无脑 exclusion 压冲突（掩盖问题，不解决）
- ❌ 测试框架进 compile scope

## 自检清单

- [ ] 版本统一在父 pom 管理
- [ ] scope 正确（test 依赖不进 compile）
- [ ] 无 LATEST/RELEASE 版本
- [ ] 无同一库多版本
- [ ] 冲突已通过 dependencyManagement 解决，非盲目 exclusion
- [ ] 新依赖有用途说明
- [ ] MySQL 8 → Connector/J 8.x（BOM 管理），无 5.1 旧驱动
- [ ] 接口项目已引 springdoc/knife4j（无接口模块除外），文档开关按环境配置
- [ ] 日志：默认 Logback 无重复引；Log4j2 已排除 logback，未并存
