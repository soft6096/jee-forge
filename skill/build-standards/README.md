# build-standards

约束 AI 生成构建配置的规范集。面向 Maven 多模块 Java 项目。

## 解决的问题

AI 生成构建配置常见问题：版本散落子模块、依赖 scope 乱用、LATEST 版本不可复现、依赖冲突盲目 exclusion、模块循环依赖、公共代码复制不下沉。本 skill 把这些约束固化为可加载规范。

## 规范文件

| 文件 | 覆盖 |
|---|---|
| [SKILL.md](SKILL.md) | skill 入口 + 加载矩阵 + 规则速查 |
| [standards/maven-standards.md](standards/maven-standards.md) | Maven：pom 结构/版本管理/插件/profile |
| [standards/dependency-standards.md](standards/dependency-standards.md) | 依赖：引入原则/scope/冲突处理 |
| [standards/module-standards.md](standards/module-standards.md) | 多模块：划分/依赖方向/公共代码下沉 |

## 与其他 skill 的关系

| skill | 关系 |
|---|---|
| [java-code-standards](https://github.com/soft6096/jee-forge/tree/main/skill/java-code-standards) | Java 代码规范引用本 skill |
| [ai-dev-workflow](https://github.com/soft6096/jee-forge/tree/main/skill/ai-dev-workflow) | 项目流程，技术方案阶段含工程结构设计 |
| [database-standards](https://github.com/soft6096/jee-forge/tree/main/skill/database-standards) | SQL 规范，无直接引用 |
| [comment-standards](https://github.com/soft6096/jee-forge/tree/main/skill/comment-standards) | 注释规范，无直接引用 |
| [test-standards](https://github.com/soft6096/jee-forge/tree/main/skill/test-standards) | 测试规范，无直接引用 |

## 安装

本技能是 [jee-forge](https://github.com/soft6096/jee-forge) 技能家族成员（单仓库 9 个技能）。安装任选其一：

```bash
# 方式一：整仓 clone（opencode/Codex 支持 skill/<name> 嵌套识别，更新 = git pull）
git clone git@github.com:soft6096/jee-forge.git ~/.agents/skills/jee-forge

# 方式二：只装本技能到你的 agent 技能目录（Claude Code：~/.claude/skills/；opencode：~/.agents/skills/）
git clone git@github.com:soft6096/jee-forge.git /tmp/jee-forge && cp -r /tmp/jee-forge/skill/build-standards ~/.agents/skills/build-standards
```

## 使用

触发场景自动加载：写 pom、加依赖、拆模块、依赖冲突、多模块工程结构。也可显式要求：`用 build-standards 检查 pom.xml`。

## 维护

- 规范文件按「强制规则 → 反例/正例 → 自检清单」结构编写
- 构建规范本体只在 `standards/` 维护，其他 skill 引用不复制
- 改规范后更新 SKILL.md 加载矩阵与速查

## 许可

MIT
