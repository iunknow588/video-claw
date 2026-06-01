# CHO 公共 Agent 管理服务说明

## 1. 目标

CHO 的职责不是单个 skill 的集合，而是“公共 Agent 管理部门”。

因此，CHO 需要补齐 `services` 层，把下面三类职责落成明确的用例编排：

- `agent_management`
- `capability_registry`
- `health_monitoring`

这样 `skills` 只负责单一动作入口，真正的 Agent 管理逻辑放在 `services`。

## 2. 分层原则

### 2.1 skills 层

CHO skills 只负责单次调用：

- 查询公共 Agent 名录
- 查询 Agent 能力画像
- 查询 Agent 健康状态

skills 不直接维护内部 roster，不直接堆放业务规则。

### 2.2 services 层

CHO services 承担实际的部门编排职责：

- Agent 生命周期管理
- 能力目录维护
- 健康状态计算

### 2.3 agent 层

`CHOAgent` 对外暴露：

- `leader_class`
- `service_class`
- `managed_skill_classes`

这样 CHO 就不再只是“带三个 skill 的壳”，而是完整的部门单元。

## 3. 目录结构

```text
app/CHO/
  agent/
  leader/
  skills/
  services/
    agent_management/
    capability_registry/
    health_monitoring/
```

## 4. 职责划分

### 4.1 agent_management

负责公共 Agent 生命周期：

- `list_public_agents()`
- `get_public_agent(agent_name)`
- `provision_agent(spec)`
- `decommission_agent(agent_name)`
- `update_agent(agent_name, updates)`

### 4.2 capability_registry

负责能力目录：

- `list_capabilities()`
- `describe_agent(agent_name)`
- `update_capabilities(agent_name, capabilities)`

### 4.3 health_monitoring

负责健康状态聚合：

- `check_health()`

健康视图来自两部分：

- Agent 生命周期状态
- 能力画像是否齐备

## 5. 结构收益

补齐后，CHO 会从“只有 skill，没有部门服务”的状态，变成结构完整的管理部门：

- `leader` 负责组织身份
- `services` 负责部门编排
- `skills` 负责单动作入口
- `agent` 负责统一暴露部门能力

这比让其他部门绕过 CHO、直接拼 skill 更清晰，也更符合“CXO 管理、skills 执行动作”的体系。
