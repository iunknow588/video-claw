# Pipeline接口标准化说明

## 目标

CEO 编排层只负责调度，不再理解各部门 pipeline 的私有函数签名。  
所有部门 pipeline 统一实现同一契约：

```python
@dataclass
class PipelineContext:
    trace_id: str
    workflow_run_id: str
    request: DomainWorkflowRequest


@dataclass
class PipelineResult:
    status: Literal["success", "failed", "rework"]
    bundle: dict[str, Any]
    notes: list[str]
```

```python
class Pipeline(Protocol):
    async def run(self, context: PipelineContext, input_bundle: dict[str, Any]) -> PipelineResult:
        ...
```

## 责任边界

- `CEO/services/orchestration/`
  - 持有 pipeline 契约
  - 组装跨部门上下文
  - 按顺序调度各部门 pipeline
- 各部门 `services/use_cases/`
  - 编排本部门 skill
  - 产出本部门业务结果
- 各部门 `skills/`
  - 只负责单一动作，不承担跨步骤流程

这意味着 pipeline 是 CEO 的编排适配层，不需要新增部门承接。  
`CAO` 继续负责对外交付，`CIO` 继续负责内部事件、日志、追踪，二者都不接管 CEO 主流程调度。

## 七条标准化链路

- `FinanceGate` -> `CFO`
- `ResearchPipeline` -> `CSO`
- `AnalysisPipeline` -> `CCO`
- `RDPipeline` -> `CTO`
- `ProductionPipeline` -> `COO`
- `QAPipeline` -> `CQO`
- `PublishPipeline` -> `CAO`

统一之后，CEO 只向每条链路传入：

- `context`
- `input_bundle`

统一拿回：

- `status`
- `bundle`
- `notes`

## 状态约定

- `success`: 本阶段完成，可继续进入下一阶段
- `failed`: 由异常体现，交给 CEO 统一失败处理
- `rework`: 本阶段已完成检查，但要求返工；当前主要用于 `CQO`

`CQO` 的返工要求继续由 CEO 决策是否回退到 `COO` 重做，避免质检部门直接反向驱动生产部门。

## 收益

- CEO engine 不再硬编码 7 套不同方法签名
- pipeline 切换或新增实现时，只需遵守同一契约
- 测试可以直接校验“部门 pipeline 是否遵守 contract”
- 后续若扩展并行执行、补偿、重试、审计，也只需围绕统一结果结构增强
