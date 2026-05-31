# Leader 汇报与 CEO 查询机制

## 1. 机制目标

当前系统已经形成一套比较完整的治理汇报机制，核心目标有三点：

1. 所有受 CEO 直辖的一级 Leader 都要定期向 CEO 报告
2. CEO 可以主动向任意 Leader 查询最新报告或历史报告
3. CIO 的职责已经扩展到测试与系统稳定性治理，因此其报告不仅包含数据资产，也包含稳定性视角

## 2. 当前实现状态

### 2.1 报告持久化

当前已落地的持久化表：

- `leader_reports`

对应实现：

- 模型：`src/app/models/leader_report.py`
- 服务：`src/app/services/leader_reports.py`

该表用于保存周期报告、CEO 主动拉取的报告，以及后续可能扩展的快照型报告。

### 2.2 Leader 抽象已具备报告接口

当前 `BaseLeader` / `ManagedLeader` 已统一提供以下能力：

- `build_report()`
- `build_periodic_report(context)`
- `accept_command()`
- `propose_change()`
- `get_status()`

具体的部门化实现位于：

- `src/app/leaders/departments.py`

### 2.3 CIO 报告已纳入测试与稳定性内容

当前 CIO 的周期性报告不只看仓库和日志，还会报告：

- `workflow_success_rate`
- `qa_pass_rate`
- `render_success_rate`
- `ffmpeg_preview_runs`
- `preview_placeholder_runs`
- `artifact_count`
- `log_record_count`

这说明“测试工作属于 CIO 职责的一部分”已经在报告结构中落地，不只是口头约定。

## 3. CEO 侧可用能力

### 3.1 主动收集所有 Leader 的周期性报告

- `POST /api/v1/ceo/reports/collect`

作用：按 cadence 批量生成并保存当前所有直辖 Leader 的周期报告。

### 3.2 查询报告列表

- `GET /api/v1/ceo/reports`

支持按 Leader、报告类型和数量限制查询。

### 3.3 查询某个 Leader 的历史报告

- `GET /api/v1/ceo/leaders/{leader_name}/reports`

### 3.4 查询某个 Leader 的最新报告

- `GET /api/v1/ceo/leaders/{leader_name}/reports/latest`

### 3.5 主动要求某个 Leader 提交报告

- `POST /api/v1/ceo/leaders/{leader_name}/request-report`

当前实现会同步创建一份 `requested` 类型报告，并落库保存。

## 4. 机制含义

这套机制已经让 CEO 具备了两种治理姿态。

### 4.1 被动接收

Leader 按周期提交报告，CEO 通过报告中心观察整体趋势。

### 4.2 主动巡检

当 CEO 发现某个部门指标异常时，可以直接点名查询该 Leader 的状态与报告，而不是只能等待定期汇报。

这使 CEO 从“只会编排流程”进一步进化成“会持续治理部门表现”的角色。

## 5. 当前准确性说明

结合当前代码，下面这些判断是准确的：

1. CFO、CIO 以及各业务 Leader 都已经在 CEO 的报告治理范围内。
2. CIO 确实已经承担测试与稳定性报告职责。
3. CEO 确实可以主动查询，而不只是定期收取报告。

但也有两点仍可继续完善：

1. 报告状态目前主要是 `submitted`，`reviewed / acknowledged` 还没有形成完整闭环。
2. `cadence` 目前可用，但还没有做成特别强的策略化调度体系。

## 6. 下一步建议

最值得继续补的三件事：

1. 为 `leader_reports` 增加已审阅、已确认状态
2. 把报告频率做成更明确的策略配置
3. 让 CIO 报告进一步接入真实测试执行结果，而不只是汇总指标
