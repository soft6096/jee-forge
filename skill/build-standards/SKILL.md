---
name: build-standards
description: 约束 AI 生成构建配置的规范集（Maven pom/依赖管理/多模块结构）。编写 pom.xml、添加依赖、设计多模块结构、解决依赖冲突时必须加载本 skill。触发场景：写 pom、加依赖、拆模块、依赖版本管理、依赖冲突、Maven 配置、多模块工程结构、接口模块配 springdoc/knife4j、日志框架 Logback/Log4j2 依赖。代码生成完成后的依赖核对见 check-standards skill（HIGH #1 接口文档 / #2 日志框架 选型敏感项）。
---

# Build Standards

约束 AI 生成构建配置的规范集。面向 Maven 多模块 Java 项目。

## 加载矩阵

| 任务类型 | 必读 |
|---|---|
| 写 pom.xml / 构建配置 | `standards/maven-standards.md` |
| 添加/审查依赖、解决冲突 | `standards/dependency-standards.md` |
| 设计多模块结构 / 依赖方向 | `standards/module-standards.md` |

## 核心规则速查

- 版本集中在父 pom（properties / dependencyManagement），子模块不写版本
- 第三方依赖走 BOM；插件版本进 pluginManagement
- 依赖 scope 正确（test 依赖必 test）；禁 LATEST/RELEASE
- 冲突用 dependencyManagement 统一版本解决，禁盲目 exclusion
- 接口项目必配 springdoc/knife4j（OpenAPI 注解依赖）；日志默认 Logback 禁重复引、Log4j2 禁并存
- 依赖单向：admin → service → domain → common，禁循环依赖
- 跨模块复用下沉 common，禁模块间复制代码

## 与其他 skill 的关系

- **java-code-standards**：Java 代码规范引用本 skill（写 pom/依赖/模块时加载）
- **database-standards / comment-standards / test-standards / ai-dev-workflow**：无直接引用

## 使用要求

生成任何构建配置（pom/依赖/模块结构）前，按「任务类型 → 加载矩阵」读取规范；生成后对照对应规范自检清单逐项核对。违反强制规则即返工。
