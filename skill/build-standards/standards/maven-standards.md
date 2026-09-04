# Maven 构建规范 (Maven Standards)

## 适用范围

编写/审查 pom.xml、构建配置、插件管理时加载。面向 Maven 多模块 Java 项目。

## 强制规则

### 1. pom 结构

- 继承统一父 pom（项目父或公司级 parent），版本集中在父 pom `dependencyManagement` 管理
- 子模块 pom 不写版本号（从父 pom 继承），避免版本散落
- 坐标规范：`groupId` 公司域名反写 + 项目名，`artifactId` 模块名，`version` 由父 pom 统一

```xml
<!-- 父 pom：统一版本 -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-dependencies</artifactId>
            <version>3.2.5</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>common-core</artifactId>
            <version>${revision}</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### 2. 版本管理

- 版本号不硬编码散落各模块 — 集中在父 pom `<properties>`（`${spring-boot.version}`）或 `dependencyManagement`
- 第三方依赖版本用 BOM 导入（Spring Boot BOM、MyBatis-Plus starter BOM），不逐个写版本
- 版本升级：父 pom 单点改，禁止子模块各自升
- 插件版本同样集中在 `pluginManagement`，子模块不重复写版本

### 3. 插件管理

- 常用插件进父 pom `pluginManagement`：`maven-compiler-plugin`、`spring-boot-maven-plugin`、`maven-surefire-plugin`
- 统一 Java 版本：`maven.compiler.source/target` 或 `<release>`，全模块一致

```xml
<properties>
    <java.version>17</java.version>
    <maven.compiler.release>17</maven.compiler.release>
</properties>
```

- 资源过滤/打包插件按需启用，不装无用插件（构建提速 + 维护面小）

### 4. profile 环境

- 环境差异（dev/test/prod）用 `<profile>` + `application-{env}.yml`，不写死构建参数
- profile 内配置：构建资源目录、过滤属性、环境特定依赖
- 默认 profile 为 dev，生产构建显式 `-P prod`

### 5. 禁止事项

- ❌ 子模块各自写版本号（版本散落，升级漏改）
- ❌ 依赖不声明 scope 或默认 compile 乱用
- ❌ 版本冲突不处理直接 `mvn dependency:tree` 排查
- ❌ 重复引入同一依赖不同版本（依赖收敛，见 dependency 规范）
- ❌ 构建产物（target/）提交 git

## 反例 / 正例

```xml
<!-- 反例：子模块硬编码版本 + 无版本管理 -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
    <version>33.0.0-jre</version>   <!-- 版本散落 -->
</dependency>
```

```xml
<!-- 正例：版本在父 pom 管理，子模块省略 version -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
</dependency>
```

## 自检清单

- [ ] 版本集中在父 pom（properties / dependencyManagement）
- [ ] 第三方版本走 BOM
- [ ] 插件版本统一管理
- [ ] Java 版本全模块一致
- [ ] 环境差异用 profile
- [ ] target/ 未提交 git
