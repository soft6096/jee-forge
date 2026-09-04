# 多模块规范 (Multi-Module Standards)

## 适用范围

设计/维护 Maven 多模块项目结构、模块划分、依赖方向时加载。

## 强制规则

### 1. 模块划分原则

- 按**分层/职责**拆模块，不按业务零散拆（业务模块内部再分包）
- 典型分层：

```
parent
├── common/          # 通用工具、常量、异常、基础类（无业务依赖）
├── common-xxx/      # 特定技术公共层（按需：redis/mq/security 封装）
├── domain/          # 领域模型：Entity/DTO/VO/枚举（可选，视规模）
├── service/         # 业务服务（核心逻辑）
├── admin/           # 管理端应用入口（Controller + 启动类）
└── api/             # 对外接口定义/Feign 客户端（跨服务契约）
```

- 模块数量适度：小项目单模块 + 分包即可，不强行多模块（过度拆分 = 构建复杂 + 依赖地狱）

### 2. 依赖方向（核心规则）

- **依赖单向**：上层依赖下层，禁反向
  - `admin → service → domain/common`
  - `api → domain`（契约只依赖模型）
- **禁循环依赖**：模块 A 依赖 B、B 依赖 A（Maven 构建报错，必须重构）
- 分层依赖树维护：common 底层零依赖业务，service 不依赖 admin

```text
admin ──> service ──> domain ──> common
  │          │
  └──> api ──┘
（api 只依赖 domain，service 可实现 api 接口）
```

### 3. 公共代码归属

- 跨模块复用 → 下沉 common（或 common-xxx），禁模块间直接引用对方内部类
- 下沉判断：第 2 个使用点出现才抽（过早抽象 = 过度设计）
- common 模块职责纯净：工具/常量/异常/基础注解，不塞业务

### 4. 模块间通信

- 模块间通过**接口**协作，不直接操作对方实现
- 跨模块实体传递用 DTO/VO，不直接传 Entity（耦合表结构）
- 依赖尽量窄：service 接口放独立模块（api）时，下游依赖接口不依赖实现

### 5. 禁止事项

- ❌ 循环依赖（构建必炸）
- ❌ 上层模块被下层依赖（方向反转）
- ❌ 模块间复制代码（应下沉 common）
- ❌ 业务代码放 common（common 污染）
- ❌ 无意义模块拆分（单类一模块）

## 反例 / 正例

```text
// 反例：service 依赖 admin（方向反转）+ 循环
admin ──> service ──> admin（循环）
```

```text
// 正例
admin ──> service ──> domain ──> common
```

## 自检清单

- [ ] 模块按分层职责划分，无零散拆分
- [ ] 依赖单向（admin → service → domain → common）
- [ ] 无循环依赖
- [ ] 跨模块复用已下沉 common
- [ ] 模块间通过接口 + DTO 协作
- [ ] common 无业务代码
