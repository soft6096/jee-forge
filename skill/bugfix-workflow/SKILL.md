---
name: bugfix-workflow
description: 缺陷修复纪律工作流（Bugfix）。当用户报告已交付/已有代码有 bug（修复缺陷/XX 坏了/功能不对/报错排查/这段代码出问题）时加载本 skill：先复现与定位 → assess 根因（带证据，禁止盲试）→ 影响面与产物同步判断 → 最小修复（全量注释/日志）→ 防回归测试 + 相关功能回归 → 兜底核对 → 经验沉淀。触发场景：修 bug、修复缺陷、修一下 XX、功能异常、Bugfix、bug 排查。WHEN NOT（不要因这些场景触发本 skill）：新功能/完整模块开发 → ai-dev-workflow；纯生成/修改业务代码（非缺陷修复）→ java-code-standards + comment-standards；写测试 → test-standards。边界：涉及需求/范围变更，或该模块在 docs/ 已有 ai-dev-workflow 历史产物 → 先配合 ai-dev-workflow（0.5/0.8，产物同步不豁免），本 skill 不替代流程的产物同步。
---

# Bugfix Workflow（缺陷修复纪律）

**定位**：修 bug 也要有纪律——先复现、找根因、最小修复、防回归，禁止"盲试 N 次看运气"。本 skill 独立可触发，也可被 ai-dev-workflow 在 Bugfix 场景引用。

## 为什么必须有这一步

没有纪律的 bug 修复常见翻车：凭印象猜着改 → 改错位置 → 连带破坏其它功能 → 修好一个冒出一个。本流程把修复收敛为 **assess → fix → verify** 三段，每一步都要有证据。

## 与家族其它 skill 的边界

| skill | 边界 |
|---|---|
| ai-dev-workflow | 新功能/完整模块走主流程；**本 skill 只处理"已有代码的缺陷修复"**。修复涉及需求/范围变更，或该模块 docs/ 已有历史产物 → 先配合 ai-dev-workflow（0.5 存量约束 / 0.8 产物同步），产物同步不豁免 |
| check-standards | 修复完成后加载做兜底核对（注释/日志/规范逐项，附证据） |
| java-code-standards / comment-standards / test-standards | 写修复代码时按其规范执行（注释/日志不豁免）；补防回归测试按 test-standards |

## 工作流（命令 `/bugfix`，详见 `commands/bugfix.md`）

```
bug 报告
  ▼
1. 定位与复现：确认涉及模块、能否稳定复现（步骤/输入/报错原文/日志）
  ▼
2. assess 根因：定位根因（读代码 + grep/日志证据），产出根因假设并验证；
   禁止"猜测→盲改→看运气"
  ▼
3. 影响面与产物同步判断：
   · 该模块 docs/ 有 ai-dev-workflow 产物？→ 按 ai-dev-workflow 0.8 处理产物同步
   · 是否只改代码、不碰需求/契约/验收口径？→ 保持，禁止顺手改需求
  ▼
4. fix：最小修复（只改根因相关代码，禁止"顺手优化"无关代码）；
   全量注释 + 方法级日志（不豁免）
  ▼
5. verify：补 1 条防回归测试（先红→修复→绿）+ 相关功能回归 + 受影响验收场景抽查；
   附证据（文件:行号 / 测试结果 / 运行日志）
  ▼
6. 兜底与沉淀：`/check-standards` 核对 → 修复单落盘
   docs/<模块>/bugfix-<YYYYMMDDHHMMSS>.md → 可选记入 docs/experience.md（标 [HARD] 表示建议固化）
```

## 硬性要求

- 先复现、先根因，后动手；根因不清禁止改码
- 最小修复：只改根因相关，禁止"顺手优化"/重构/无关清理
- 不改需求口径：验收标准/契约变更不属于 bugfix，回 ai-dev-workflow（0.8/修整）处理
- 同模块已有 docs 产物 → 产物同步不豁免（先 0.8）
- 注释与日志不豁免：本次修改/新增的代码全量注释 + 方法级日志
- 修复后必须补防回归测试 + 证据，`/check-standards` 兜底后才算完成
- 修复失败 ≥3 次自动修复循环 → 停下向用户求助（禁止无限盲试）

## 产物

- 修复单：`docs/<模块>/bugfix-<YYYYMMDDHHMMSS>.md`（模板 `templates/bugfix-修复单.md`）
- 代码改动 + 防回归测试 + 核对结论（引用 check-standards 报告或本地执行）

## 完成标准

- [ ] bug 已复现（步骤/输入/报错原文/日志证据）
- [ ] 根因已定位并验证（证据，非猜测）
- [ ] 影响面与产物同步已判断（有 docs 产物 → 已走 0.8 或明确无需同步）
- [ ] 修复为最小改动；本次代码全量注释 + 方法级日志
- [ ] 防回归测试 1 条（先红→绿）+ 相关功能回归证据
- [ ] `/check-standards` 兜底核对完成（未到位项已确认/补齐）
- [ ] 修复单已落盘 `docs/<模块>/bugfix-<时间戳>.md`，经验已按需记入 `docs/experience.md`
