# Skill Registry 去中心化说明

## 1. 目标

本次调整的目标是解决三个结构问题：

1. `WorkflowAssembly` 硬编码实例化 40+ 个 skill
2. 各部门 skill 通过 CEO 集中 import，形成反向依赖
3. `catalog.py` 集中维护全量 skill 元数据，违背“各部门各自负责”的结构原则

调整后，CEO 不再知道每个 skill 的具体构造细节，只负责消费统一的 Skill Registry。

## 2. 调整原则

### 2.1 部门拥有自己的 skill 定义

每个部门在自己的 `app/<Department>/skills/__init__.py` 中导出 skill 类。

这表示：

- CFO 只声明自己的财务 skill
- CIO 只声明自己的信息 skill
- CHO 只声明自己的公共 Agent 管理 skill
- CEO 不再集中维护所有 skill 的定义清单

### 2.2 Registry 管工厂，不管全局实例

新的 Skill Registry 不再保存一堆全局 skill 实例，而是保存：

- skill class
- descriptor
- session 绑定后的实例化能力

因此 skill 的真实实例是按运行上下文创建的，而不是在中心位置提前全部 new 出来。

### 2.3 Assembly 只绑定 scope

`WorkflowAssembly` 现在只做两件事：

- 让 Registry 完成内建 skill 注册
- 为当前 `session` 绑定一个 `skill_scope`

之后通过 `get_skill(name)` 按名称取用 skill。

## 3. 新结构

```text
departments/CEO/skills/registry/
  └── SkillRegistry

app/<Department>/skills/
  └── __all__
```

关键变化：

- `SkillRegistry` 从各部门 `skills` 模块读取导出的 skill class
- 通过构造签名自动判断是否需要注入 `session`
- `WorkflowAssembly` 不再 import 40+ 个具体 skill class

## 4. 当前效果

### 4.1 解耦

`WorkflowAssembly` 不再直接依赖：

- CFO 全部 skill class
- CIO 全部 skill class
- CHO 全部 skill class
- CMO 全部 skill class
- CSO / CCO / CTO / COO / CQO / CAO 全部 skill class

它只依赖：

- `registry`
- `registry.bind(session=...)`

### 4.2 去中心化

原来集中在 `catalog.py` 的元数据定义已被移除。

现在 skill 的核心元数据直接归属于 skill class 本身，例如：

- `skill_name`
- `description`
- `tags`
- `parameters_schema`
- `dependencies`

### 4.3 支持 session 绑定

像 `lead.cio.store`、`lead.cio.log`、`lead.cfo.charge` 这类需要数据库上下文的 skill，
现在由 Registry 在实例化时自动注入 `session`。

## 5. 结构收益

这次调整之后，skill 体系变成了下面这种关系：

- 部门定义自己的 skill
- Registry 负责发现与实例化
- CEO 编排层只按名称取用

这比“CEO 集中 import 全部 skill 并集中改 metadata”更清晰，也更适合后续继续拆分 use case 和部门职责。
