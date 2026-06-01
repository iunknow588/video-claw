# CEO 服务收敛与部门归属调整说明

## 1. 调整目标

本次调整的目标不是简单搬目录，而是把 `app/CEO/services` 恢复到“只做治理与编排”的清晰边界。

收敛后的原则如下：

- `CEO` 只保留公司级治理、控制平面、主流程编排
- `CMO` 负责所有用户沟通与对话入口
- `CIO` 负责内部运行数据、报告持久化、运营汇总与查询
- `COO` 作为上游部门调用主流程时的生产入口

## 2. 调整前的问题

`app/CEO/services` 之前包含：

- `chat`
- `control`
- `control_plane`
- `leader_reports`
- `operations`
- `orchestration`
- `workflow`

其中有四类问题：

1. `chat` 实际只是把消息转发给 `CMO`
2. `leader_reports` 承担的是报告持久化，不是 CEO 独有业务
3. `operations` 本质是内部运行指标聚合，更接近 CIO 的信息中枢
4. `workflow` 只是工作流入口 facade，与 `orchestration` 分开后形成重复层次

## 3. 调整后的归属

### 3.1 CEO 保留

`app/CEO/services` 现在只保留三块：

- `control`
- `control_plane`
- `orchestration`

说明：

- `control` 负责 CEO 的治理查询、状态汇总、命令下发
- `control_plane` 负责组织结构、Leader 配置、治理规则
- `orchestration` 负责主流程装配、执行、记录，以及工作流 facade

### 3.2 CMO 承接 chat

对话服务的规范入口调整为：

- `app/CMO/services/chat`

说明：

- 用户消息解释
- 进度事件包装
- 报告格式化
- CEO 聊天路由只是调用 CMO，不再在 CEO 下保留对话服务壳层

### 3.3 CIO 承接 leader_reports 与 operations

内部汇总与记录服务统一归入：

- `app/CIO/services/leader_reports`
- `app/CIO/services/operations`

说明：

- `leader_reports` 负责 Leader 报告的持久化与查询
- 报告内容的生成仍然属于各个 Leader 自身
- `operations` 负责热点、分析、脚本、视频、评审、成本等跨流程统计
- CEO 只消费这些结果，不再拥有这些数据聚合实现

### 3.4 orchestration 吸收 workflow facade

工作流入口 facade 合并到：

- `app/CEO/services/orchestration/domain_workflow.py`

说明：

- 不再单独保留 `app/CEO/services/workflow`
- 工作流入口与装配、执行、记录放在同一编排域中，结构更一致

## 4. 当前结构结论

当前结构更符合下面这条判断规则：

- 看到 `CEO/services`，就知道这里是治理与编排
- 看到 `CMO/services/chat`，就知道这里是用户沟通入口
- 看到 `CIO/services/operations`，就知道这里是内部运行指标中心
- 看到 `CIO/services/leader_reports`，就知道这里是治理报告的记录与查询中心

这比“所有公司级能力都塞进 CEO”更容易理解，也更方便后续扩展。

## 5. 本次顺手修正

在迁移 `operations` 时，一并修正了一个指标计算问题：

- `budget_usage_ratio` 之前会把 `cost_breakdown.total` 重复累计一次
- 现在改为直接使用 `cost_breakdown.total`

这样 CFO 与 CEO 看到的预算占用比例与实际总成本保持一致。
