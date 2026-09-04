---
name: test-standards
description: 约束 AI 生成测试代码的规范集（单元测试/契约测试/测试数据）。编写单元测试、接口契约测试、测试数据准备、审查测试代码时必须加载；对接 ai-dev-workflow 契约测试流程（4.2 先红后绿）。触发场景：写测试、写单测、写契约测试、测试数据、覆盖率、Testcontainers、Mockito、JUnit、测试规范审查。测试原则适用任何语言，示例以 Java（JUnit5 + Mockito + Spring Boot Test）为主。
---

# Test Standards

约束 AI 生成测试代码的规范集。三层内容：

- **unit-test-standards.md**：单元测试 — AAA 结构/Mock 规则/断言风格/测试隔离
- **contract-test-standards.md**：契约测试 — 验收场景翻译/三态覆盖/先红后绿
- **test-data-standards.md**：测试数据 — 数据工厂/Testcontainers/隔离

## 加载矩阵

| 任务类型 | 必读 |
|---|---|
| 写单元测试 | `standards/unit-test-standards.md` |
| 写接口契约测试（对接 ai-dev-workflow 4.2） | `standards/contract-test-standards.md` + `standards/unit-test-standards.md` |
| 准备测试数据 / 数据库集成测试 | `standards/test-data-standards.md` |
| 审查测试代码 | 全部（按对应类型） |

## 核心规则速查

- 测试是验收标准：禁止改断言/删测试/@Disabled（编码不得迁就测试）
- 一个测试一个行为，AAA 结构；断言用 AssertJ 流式
- **测试方法名英文驼峰**（`createOrderShouldReturn400WhenUserNotExist`），禁止中文/拼音方法名；用例中文写 Javadoc
- 依赖全 mock，不测实现细节；无 Thread.sleep
- 契约测试覆盖三态（合法/非法/边界），先红后绿
- 测试数据工厂化，复杂 SQL 用 Testcontainers 真实库
- 测试隔离：不依赖执行顺序、不共享可变状态

## 与其他 skill 的关系

- **ai-dev-workflow**：4.2 `/contract-tests` 契约测试流程引用本 skill 的 contract-test-standards（流程在流程 skill，代码规范在本 skill）
- **java-code-standards**：Java 代码规范引用本 skill（写测试时加载）
- **database-standards / comment-standards**：无直接引用

## 使用要求

生成任何测试代码前，按「任务类型 → 加载矩阵」读取规范；生成后对照对应规范自检清单逐项核对。契约测试先红后绿，红因必须是"实现不存在"而非"测试写错"。
