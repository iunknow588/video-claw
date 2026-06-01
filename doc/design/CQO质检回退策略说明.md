# CQO质检回退策略说明

## 目标

将 QA 失败后的回退判断从 `engine.py` 中抽离，避免：

- 在 CEO engine 中硬编码字符串匹配
- 由 `CQO` 直接决定“打回哪个部门”
- 回退策略无法配置、无法演进

调整后，职责改为：

- `CQO` 只输出质检事实与失败维度
- `CEO` 根据配置化策略决定回退目标
- `control_plane` 提供 QA 回退策略配置

## 职责边界

- `CQO/skills/qa_report`
  - 输出 `qa_status`
  - 输出 `failed_dimensions`
  - 输出 `recommendation`
  - 不直接写死 `reroute_target`

- `CEO/services/control_plane`
  - 维护 QA conditional edge 的 `strategy` 与 `mapping`
  - 作为回退配置的唯一来源

- `CEO/services/orchestration`
  - 根据 QA 报告和策略决策 reroute
  - 执行返工链路

## 策略模型

统一接口：

```python
class QARerouteStrategy(ABC):
    def determine_route_key(self, qa_report: dict[str, Any]) -> str:
        ...
```

当前内置三种策略：

- `balanced`
  - 若失败维度涉及策划一致性、内容合规，则回退 `lead.research_development`
  - 否则回退 `lead.production`

- `conservative`
  - 失败后总是尽早回退到 `lead.research_development`

- `aggressive`
  - 失败后总是优先回退到 `lead.production`

## 配置来源

QA 的 conditional edge 增加 `strategy` 字段：

```python
{
    "from": "lead.qa",
    "router_func": "qa_gate",
    "strategy": "balanced",
    "mapping": {
        "passed": "lead.publish",
        "retry_production": "lead.production",
        "retry_research_development": "lead.research_development",
    },
}
```

`control_plane` 通过 `get_qa_reroute_policy()` 暴露：

- `strategy`
- `mapping`

## 执行链路

当 `qa_status != passed` 时：

1. CEO 读取 QA policy
2. 策略决定 route key
3. mapping 将 route key 转为 leader
4. engine 执行返工

当前支持：

- 回退 `lead.production`
  - 重新制作
  - 重新质检

- 回退 `lead.research_development`
  - 重新策划
  - 重新制作
  - 重新质检

## 收益

- CEO 编排不再硬编码 QA 回退字符串
- CQO 保持“质检部门”定位，不越权管理路由
- 回退策略可通过 control plane 配置演进
- 未来可以继续扩展更细的策略而不污染主流程
