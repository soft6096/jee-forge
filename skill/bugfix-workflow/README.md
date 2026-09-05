# bugfix-workflow

缺陷修复纪律工作流（Bugfix）：先复现与定位 → assess 根因（证据，禁止盲试）→ 影响面与产物同步判断 → 最小修复（全量注释/日志）→ 防回归测试 + 功能回归 → `/check-standards` 兜底 → 经验沉淀。

## 安装

随 jee-forge 家族一体安装（见仓库根 README）。也可单独使用本目录。

## 使用

```text
/bugfix <bug 描述或路径>      # 或自然语言"这个 bug 帮我修"
```

## 边界

- 新功能 / 完整模块 → ai-dev-workflow
- 修复涉及需求/范围变更，或该模块 docs/ 已有 ai-dev-workflow 产物 → 先配合 ai-dev-workflow（0.5/0.8，产物同步不豁免）
- 修复完成统一 `/check-standards` 兜底核对

## 目录

```text
bugfix-workflow/
├── SKILL.md                    # 入口 + 工作流 + 边界
├── commands/bugfix.md          # /bugfix 命令执行细则
└── templates/bugfix-修复单.md   # 修复单模板
```
