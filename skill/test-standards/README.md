# test-standards

约束 AI 生成测试代码的规范集。测试原则适用任何语言，示例以 Java（JUnit5 + Mockito + Spring Boot Test）为主。

## 解决的问题

AI 生成测试常见问题：只测合法路径、断言实现细节、测试依赖真实外部服务、测试间数据污染、改断言迁就实现（骗绿）、Thread.sleep 等待、Mock 满天飞。本 skill 把这些约束固化为可加载规范。

## 规范文件

| 文件 | 覆盖 |
|---|---|
| [SKILL.md](SKILL.md) | skill 入口 + 加载矩阵 + 规则速查 |
| [standards/unit-test-standards.md](standards/unit-test-standards.md) | 单元测试：AAA/Mock/断言风格/隔离 |
| [standards/contract-test-standards.md](standards/contract-test-standards.md) | 契约测试：验收场景翻译/三态/先红后绿 |
| [standards/test-data-standards.md](standards/test-data-standards.md) | 测试数据：工厂/Testcontainers/隔离 |

## 与其他 skill 的关系

| skill | 关系 |
|---|---|
| [ai-dev-workflow](https://github.com/soft6096/jee-forge/tree/main/skill/ai-dev-workflow) | 4.2 契约测试流程引用本 skill 的 contract-test-standards |
| [java-code-standards](https://github.com/soft6096/jee-forge/tree/main/skill/java-code-standards) | Java 代码规范引用本 skill |
| [database-standards](https://github.com/soft6096/jee-forge/tree/main/skill/database-standards) | SQL 规范，无直接引用 |
| [comment-standards](https://github.com/soft6096/jee-forge/tree/main/skill/comment-standards) | 注释规范，无直接引用 |

## 安装

本技能是 [jee-forge](https://github.com/soft6096/jee-forge) 技能家族成员（单仓库 8 个技能）。安装任选其一：

```bash
# 方式一：整仓 clone（opencode/Codex 支持 skill/<name> 嵌套识别，更新 = git pull）
git clone git@github.com:soft6096/jee-forge.git ~/.agents/skills/jee-forge

# 方式二：只装本技能到你的 agent 技能目录（Claude Code：~/.claude/skills/；opencode：~/.agents/skills/）
git clone git@github.com:soft6096/jee-forge.git /tmp/jee-forge && cp -r /tmp/jee-forge/skill/test-standards ~/.agents/skills/test-standards
```

## 使用

触发场景自动加载：写测试、写单测、写契约测试、测试数据、Testcontainers、Mockito、JUnit。也可显式要求：`用 test-standards 规范检查测试代码`。

## 维护

- 规范文件按「强制规则 → 反例/正例 → 自检清单」结构编写
- 测试规范本体只在 `standards/` 维护，其他 skill 引用不复制
- 改规范后更新 SKILL.md 加载矩阵与速查

## 许可

MIT
