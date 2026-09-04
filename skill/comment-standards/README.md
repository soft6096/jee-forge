# comment-standards

约束 AI 生成代码注释的规范集。通用原则适用任何语言，示例以 Java（Javadoc）为主。

## 解决的问题

AI 生成注释常见问题：类/字段/方法注释漏写、@param 只重复参数名、逐行翻译式注释、编造业务意图、注释与代码不一致、方法体无步骤说明。本 skill 把这些约束固化为可加载规范，AI 写注释前加载，写后按自检清单核对。

核心要求（全量注释）：**所有类**（DTO/VO/Config 等，仅示例非穷举）有类注释写清职责；**所有变量/字段**有注释写清含义；**所有方法**（含测试方法）有功能 + @param + @return 注释；**方法体 ≥2 个逻辑步骤**有编号步骤注释（`// 1. 参数提取…` `// 2. 基础校验…`）。

## 规范文件

| 文件 | 覆盖 |
|---|---|
| [SKILL.md](SKILL.md) | skill 入口 + 加载矩阵 + 规则速查 |
| [standards/comment-standards.md](standards/comment-standards.md) | 注释规范本体：覆盖范围/格式/@param/@return/行内注释/自检清单 |
| [standards/gen-comments-workflow.md](standards/gen-comments-workflow.md) | 存量注释补全工作流：有 spec 派生 / 无 spec 事实注释 |

## 与其他 skill 的关系

| skill | 关系 |
|---|---|
| [java-code-standards](https://github.com/soft6096/java-code-standards) | Java 代码规范引用本 skill 的注释规范 |
| [ai-dev-workflow](https://github.com/soft6096/ai-dev-workflow) | 开发流程引用本 skill 注释规范，gen-comments 命令 = 本 skill 存量补注释工作流 |
| [database-standards](https://github.com/soft6096/database-standards) | SQL 规范，无注释内容 |

## 安装

```bash
git clone git@github.com:soft6096/comment-standards.git ~/.agents/skills/comment-standards
# 或 opencode 用户目录
git clone git@github.com:soft6096/comment-standards.git ~/.agents/skills/comment-standards
```

## 使用

触发场景自动加载：写注释、补注释、生成注释、注释规范审查。也可显式要求：`用 comment-standards 检查这段注释`。

## 维护

- 规范文件按「强制规则 → 反例/正例 → 自检清单」结构编写，新增规则保持此结构
- 注释规范本体只在 `standards/comment-standards.md` 维护，其他 skill 引用不复制
- 改规范后更新 SKILL.md 加载矩阵与速查

## 许可

MIT
