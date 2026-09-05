# 中间产物 Markdown 样式规范

> 使用说明：**生成任何中间产物 md（功能清单 / 澄清清单 / 项目约束 / 技术方案 / 任务拆解 / 验收报告）时必须遵守本文档**，保证文档精美、专业、可读。
> 目标观感：像开源项目技术文档（GitHub README 级）——速览框、对齐表格、配色时序图/流程图、状态徽标、完成自检。

---

## 一、通用样式规则

### 1.1 文档头部：速览框（所有产物必有）

用 GitHub 官方 callout（`> [!IMPORTANT]`）放关键信息速览表，一屏看懂文档主题。

```markdown
> [!IMPORTANT] 文档速览
>
> | 项目 | 内容 |
> | :--- | :--- |
> | **模块** | 订单管理 |
> | **功能项** | #1 订单创建 · #2 订单查询 |
> | **类型** | Controller |
> | **优先级** | P1 |
> | **依赖** | #3 权限初始化 |
```

- 固定用 `> [!IMPORTANT]` + 标题「文档速览」
- 速览表 2 列：`项目` / `内容`，右列关键值用 `**加粗**`
- 表头列宽不强制，Markdown 渲染自动对齐；分隔行统一 `:---`

### 1.2 分区：用 `---` 分隔大章节

每个 `##` 大章节之间插入 `---` 水平线，增强视觉层次：

```markdown
## 一、入口定义 → 接口清单

...

---

## 二、数据契约 → 校验规则
```

### 1.3 表格：统一对齐 + 表头加粗 + 序号列居中

| 场景 | 对齐方式 | 分隔行写法 |
| :--- | :--- | :--- |
| 文本列（名称/路径/说明） | 左对齐 | `:---` |
| 编号列（# / 序号） | 居中 | `:---:` |
| 数值列（错误码/数量） | 居中 | `:---:` |
| 短状态列（✅/❌/P1） | 居中 | `:---:` |

```markdown
| # | 接口 | 错误码 | 说明 |
| :---: | :--- | :---: | :--- |
| 1 | POST /order | 400 / 500 | 创建订单 |
```

- **表格必须有分隔行对齐标记**，禁止裸 `---|---`（渲染会左对齐难看）
- 表头用普通文本即可，Markdown 表头自动加粗
- 表格内容超过一屏的，拆成多张语义子表（按场景/按模块），避免超长表

### 1.4 callout 提示框（区分信息级别）

| 语法 | 用途 | 视觉 |
| :--- | :--- | :--- |
| `> [!NOTE]` | 补充说明 / 覆盖口径 | 蓝 |
| `> [!TIP]` | 复用建议 / 优化建议 | 绿 |
| `> [!IMPORTANT]` | 必须注意 / 关键约束 | 紫 |
| `> [!WARNING]` | 高风险 / 易错点 | 黄 |
| `> [!CAUTION]` | 不可违背 / 危险操作 | 红 |

```markdown
> [!WARNING] 强制改密拦截
> forceChange = 1 的用户访问受保护接口返回 1007。
```

- 仅内容重要才用，滥用会稀释信息密度
- 短内容直接 callout 单行 + 标题；长内容标题 + 列表/表格

### 1.5 状态徽标（进度 / 状态列）

| 状态 | 标记 |
| :--- | :--- |
| 已确认 / 通过 / 已处理 | `✅` |
| 未确认 / 失败 / 待处理 | `❌` |
| 待确认 / 进行中 | `🔲` / `🟡` |
| 不适用 / 跳过 | `—` |

统一用 emoji，不用文字「已完成/未完成」混搭。

### 1.6 完成标准自检（每个产物末尾）

```markdown
## 完成标准自检

- [x] 接口清单完整，无"待定"
- [ ] 验收场景三态覆盖（合法 / 非法 / 边界）
```

- 完成的 `[x]`，未完成 `[ ]`
- 逐条对照，禁止整段复制不核对

---

## 二、技术方案专属样式（调用骨架 + mermaid 图）

### 2.1 调用骨架（分层调用）——核心逻辑必配

核心逻辑用 **text 代码块**展示「入口 → Service → Mapper」分层调用，函数体用中文编号步骤，**禁止写实现代码**。

```text
# ============ Controller（纯转发：无业务逻辑、不 try/catch）============
AuthController
├─ login(LoginDTO) → Response<LoginVO>                   # 登录 → AuthService.login(dto)
├─ logout() → Response<Void>                             # 登出 → AuthService.logout()
└─ changePassword(ChangePasswordDTO) → Response<Void>    # 自助改密 → AuthService.changePassword(dto)

# ============ Service（业务编排）============
AuthServiceImpl
├─ login(LoginDTO) → LoginVO
│   # 1. 查用户 → sysUserMapper.selectByUsername(username)；不存在或密码不匹配 → 4001「用户名或密码错误」
│   # 2. 校验用户状态；已禁用 → 4002「账号已被禁用」
│   # 3. 签发 JWT → jwtTokenProvider.generate(userId, username)
│   # 4. 组装返回 LoginVO
└─ changePassword(ChangePasswordDTO) → void
    # 1. 取当前 userId（防 IDOR）
    # 2. 查用户 → sysUserMapper.selectById(userId)；校验旧密码；不匹配 → 4004「原密码错误」
    # 3. 新密码加密 → sysUserMapper.updateById(user)，下次登录生效

# ============ Mapper（数据访问，函数下附对应 SQL）============
SysUserMapper
├─ selectByUsername(String username) → SysUser           # 登录：按用户名查用户
│   └─ SQL: SELECT * FROM sys_user WHERE username = #{username} AND deleted = 0
└─ updateById(SysUser user) → int                        # 改密：更新密码
    └─ SQL: UPDATE sys_user SET password = #{password}, update_time = NOW()
            WHERE id = #{id} AND deleted = 0
```

**调用骨架规则**：

- 用 `# ============ 层名（职责）============` 分块：入口层（Controller/Listener/Job）→ Service → Mapper
- 函数行：`├─ 方法签名 → 返回类型`，行尾注释写**用途 + `→` 调用标注**（调用了下层的哪个方法）
- **简单函数**：行尾注释说明做什么即可；**复杂函数**：函数体用 `│   # 1.` 中文编号步骤描述，调用关系用 `→ service.xxx()` / `→ mapper.xxx()` 标注
- **Mapper 函数**：函数下缩进 `└─ SQL: ...` 内联对应 SQL（与"数据模型与 SQL"章节一一对应）
- 纯中文业务描述，禁止写语句级实现代码；图后不需要另附"处理步骤"（骨架已含步骤）

### 2.2 时序图（sequenceDiagram）——可选增强（复杂跨系统交互）

> [!NOTE] 与调用骨架的关系
> 调用骨架是核心逻辑的**必配主体**（分层 + 中文步骤已覆盖）；mermaid 时序图仅在**复杂跨系统交互**（多服务协作 / 外部依赖 / 时序敏感场景）时作为增强补充，不强制。若使用，配色走统一主题变量，图后步骤见调用骨架，不重复写。

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'actorBkg': '#EFF6FF', 'actorBorder': '#3B82F6', 'actorTextColor': '#1E3A8A', 'noteBkgColor': '#FEF9C3', 'noteBorderColor': '#EAB308', 'noteTextColor': '#713F12', 'signalColor': '#334155', 'signalTextColor': '#334155', 'labelBoxBkgColor': '#F1F5F9', 'labelBoxBorderColor': '#CBD5E1', 'labelTextColor': '#334155', 'loopTextColor': '#334155', 'lineColor': '#64748B'}}}%%
sequenceDiagram
    autonumber
    participant C as 客户端
    participant A as AuthController
    participant S as AuthService
    participant DB as MySQL
    participant R as Redis

    C->>A: POST /auth/login { username, password }
    A->>S: login(username, password)
    S->>DB: 按用户名查询 sys_user
    alt 用户不存在
        S-->>C: 1001 用户名或密码错误
    else 校验通过
        S-->>C: 200 { token, forceChange, menus }
    end
```

**时序图规则**：
- 第一行 init 主题变量**逐字使用上方配置**（统一配色，禁止自创颜色）
- `autonumber` 自动编号；参与者别名用**中文业务名**（`C as 客户端`）
- 用 `alt / else / end` 表达分支；`rect` 表达并行区（如需）
- 关键消息写清路径与入参；响应消息标注状态码与关键字段
- 图仅作增强，中文步骤以调用骨架为准

### 2.3 流程图（flowchart）——可选增强（复杂决策 / 状态流转）

> 复杂决策/状态流转可用流程图增强；简单流程不必画图（调用骨架已覆盖步骤）。

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#DBEAFE', 'primaryTextColor': '#1E3A8A', 'primaryBorderColor': '#3B82F6', 'lineColor': '#64748B', 'secondaryColor': '#FEF9C3', 'secondaryTextColor': '#713F12', 'secondaryBorderColor': '#EAB308', 'tertiaryColor': '#D1FAE5', 'tertiaryTextColor': '#065F46', 'tertiaryBorderColor': '#10B981', 'edgeLabelBackground': '#F8FAFC', 'fontFamily': '"Helvetica Neue", Arial, sans-serif'}}}%%
flowchart TD
    A["① 查该用户全部角色"]
    B{"② 角色列表是否为空？"}
    C["返回空数组 []"]
    D{"③ 是否包含 admin 角色？"}
    E["加载全部权限"]
    F["按角色查权限（并集去重）"]
    G["⑤ 构建树：parentId 递归组装"]

    A --> B
    B -->|"是"| C
    B -->|"否"| D
    D -->|"是（admin）"| E
    D -->|"否"| F
    E --> G
    F --> G
```

**流程图规则**：
- 第一行 init 主题变量**逐字使用上方配置**
- 节点文字带 `① ② ③` 序号 + 中文描述，与「处理步骤」编号对应
- 决策节点（菱形）用 `{"..."}`；分支标签写明判定条件（`|"是"|`）
- 复杂分支图放「业务规则」小节；简单流程不必画图（避免过度）

### 2.4 mermaid 渲染注意

- **渲染器要求**：GitHub / GitLab / Obsidian / VSCode 均原生支持 mermaid，直接写代码块即可
- **调用骨架是主体**：mermaid 图是可选增强；即使目标平台不支持 mermaid 渲染，方案也完整可读（中文步骤全在调用骨架里）
- 图内禁止超长句子（一行 ≤ 40 字符），长描述放调用骨架步骤

---

## 三、各产物速览表模板（直接套用）

### 3.1 功能清单速览

```markdown
> [!IMPORTANT] 文档速览
>
> | 项目 | 内容 |
> | :--- | :--- |
> | **模块** | 订单管理 |
> | **功能项数** | 8（Controller 5 · Listener 1 · Job 2） |
> | **优先级分布** | P1×6 · P2×2 |
> | **依赖** | 见功能清单依赖列 |
```

### 3.2 澄清清单速览

```markdown
> [!IMPORTANT] 文档速览
>
> | 项目 | 内容 |
> | :--- | :--- |
> | **澄清对象** | 订单管理功能清单 |
> | **问题总数** | 8（已确认 5 · 待确认 3） |
> | **阻塞项** | 2（见下方 🔲 项） |
```

### 3.3 需求质量核对速览（1.2 /req-gate）

```markdown
> [!IMPORTANT] 文档速览
>
> | 项目 | 内容 |
> | :--- | :--- |
> | **模块** | 商品管理 |
> | **需求分档** | B（有模糊，1.3 澄清补齐） |
> | **验收基线** | 商品模块需求文档 V2.1（2026-08-20 版） |
> | **回读核对** | 12 节（✅ 承接 10 · ⚠️ 遗漏 1 · 🔧 修正 1） |
> | **矛盾项** | 2（全部 🔲 待 1.3 澄清） |
> | **术语对齐** | 5 个（✅ 3 · 🔲 1 · 🔧 1） |
```

### 3.4 任务拆解速览

```markdown
> [!IMPORTANT] 文档速览
>
> | 项目 | 内容 |
> | :--- | :--- |
> | **任务总数** | 10 |
> | **Phase 分布** | 0×2 · 0.5×2 · 1×1 · 2×2 · 3×1 · 4×1 · 5×1 |
> | **契约测试** | T005（先红后绿） |
> | **公共组件** | T003 XxxUtil / T004 AbstractXxx |
```

### 3.5 验收报告速览

```markdown
> [!IMPORTANT] 文档速览
>
> | 项目 | 内容 |
> | :--- | :--- |
> | **功能** | 订单创建（US-001） |
> | **测试** | 12 通过 / 0 失败 |
> | **差异数** | 3（已处理 2 · 待处理 1） |
> | **结论** | 待处理差异 → 追加任务 |
```

---

## 四、风格红线（禁止）

| 红线 | 反例 | 正例 |
| :--- | :--- | :--- |
| 裸表格无对齐标记 | `\|--\|--\|` | `\| :---: \| :--- \|` |
| 长表格不拆 | 一张 30 行表格 | 按语义拆 3 张 |
| 无速览框 | 直接 `## 功能清单` | 先 `> [!IMPORTANT]` 速览 |
| 核心逻辑无调用骨架 | 只写"调 service.xxx"没有分层 | 调用骨架（分层 + `→` 标注 + 中文步骤 + Mapper 内联 SQL） |
| 调用骨架写实现代码 | 函数体写 Java/SQL 实现细节 | 中文编号步骤 + 简单函数一行注释 |
| 自创配色 | `themeVariables` 乱改 | 逐字使用上方配置 |
| callout 滥用 | 每段都套 IMPORTANT | 仅重要内容 |
| 状态用文字 | 「已完成」 | `✅` |

## 自检清单

- [ ] 文档开头有 `> [!IMPORTANT]` 速览框
- [ ] 大章节之间用 `---` 分隔
- [ ] 所有表格分隔行带对齐标记（`:---` / `:---:`）
- [ ] 技术方案核心逻辑含**调用骨架**：分层（入口 → Service → Mapper）+ `→` 调用标注 + 中文编号步骤 + Mapper 内联 SQL；不写实现代码
- [ ] （可选）复杂跨系统交互 / 复杂决策含 mermaid 图（配色用统一主题变量，仅作增强）
- [ ] 状态列用 emoji（✅ / ❌ / 🔲），不用文字混搭
- [ ] 末尾完成标准自检逐条核对
- [ ] 无超长表格 / 无自创配色 / 无 callout 滥用
