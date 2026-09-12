# test-workflow

按需生成"验收测试工具"——真实调用接口、产出独立验收测试报告。**默认不生成、不执行**。

## 解决的问题

主流程（ai-dev-workflow）默认不生成任何测试代码。当开发者需要**行为验证**（接口真的能调通、返回符合预期、事务/并发行为正确）时，本技能按需生成一套可执行的验收工具：从 `3.x 接口清单 + 验收场景` 推导用例，真实调用入口，断言响应并关联服务端日志，产出报告。

- 不生成 Java 测试类（省 token、省编译时间）
- 默认不执行（把"何时验证"交给开发者）
- 失败项分类 + 服务端日志摘录（便于定位与修复）

## 内容结构

```
test-workflow/
├── SKILL.md                       # 入口：定位/触发/输入产出/覆盖边界
├── commands/
│   └── gen-test.md                # /gen-test 命令
├── standards/
│   ├── case-design.md             # 用例设计：验收场景三态、核心场景优先、不穷举
│   └── runner-standards.md        # 执行器：真 HTTP、失败分类、日志关联、数据隔离
├── assets/
│   └── runner/                    # 通用执行器（Python，复制到项目）
│       ├── runner.py
│       └── cases.example.yaml
└── templates/
    └── 验收测试报告.md             # 独立报告模板
```

## 使用

触发方式（显式）：

```
生成验收测试 <功能项>
生成接口测试 <模块>
真实调用接口验证 <接口>
```

或执行命令 `/gen-test <功能项或模块>`。

生成后由开发者运行：

```bash
python3 <模块>/tests/runner/runner.py --cases <模块>/tests/<功能项>.cases.yaml
```

> 本技能**默认不触发**于日常写码；"写测试 / 写单测 / 契约测试"等说法不触发它。

## 与其他 skill 的关系

| skill | 关系 |
|---|---|
| [ai-dev-workflow](https://github.com/soft6096/jee-forge/tree/main/skill/ai-dev-workflow) | 主流程默认不生成测试；本技能按需补充，不阻塞主流程；5.3 需求覆盖报告与本技能报告互不替代 |
| java-code-standards / database-standards | 生成用例/执行器时按需加载 |

## 安装

本技能是 [jee-forge](https://github.com/soft6096/jee-forge) 技能家族成员（单仓库 9 个技能）。安装任选其一：

```bash
# 方式一：整仓 clone（opencode/Codex 支持 skill/<name> 嵌套识别，更新 = git pull）
git clone git@github.com:soft6096/jee-forge.git ~/.agents/skills/jee-forge

# 方式二：只装本技能到你的 agent 技能目录（Claude Code：~/.claude/skills/；opencode：~/.agents/skills/）
git clone git@github.com:soft6096/jee-forge.git /tmp/jee-forge && cp -r /tmp/jee-forge/skill/test-workflow ~/.agents/skills/test-workflow
```

## 维护

- 用例设计准则在 `standards/case-design.md`，执行器准则在 `standards/runner-standards.md`，其他技能引用不复制
- 通用执行器在 `assets/runner/` 维护单一版本
- 改规范后更新 `SKILL.md` 与本 README

## 许可

MIT
