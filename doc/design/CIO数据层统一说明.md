# CIO数据层统一说明

## 目标

将分散在多个部门服务中的数据库访问逻辑，统一收口到 `CIO/services/data_access/`。

本次调整后：

- `CIO` 负责数据访问层
- 其他部门服务通过 repository 访问 `CIO/models`
- `knowledge`、`workflow_runs`、`workflow_steps` 成为基于 repository 的服务层

## 调整后结构

```text
CIO/services/
  data_access/
    hotspot_repository.py
    analysis_repository.py
    workflow_repository.py
    artifact_repository.py
    knowledge_repository.py
  storage/
  observability/
  knowledge/
  workflow_runs/
  workflow_steps/
```

## 责任边界

- `data_access`
  - 唯一负责 `CIO/models` 的持久化与查询
  - 不承担业务编排

- `workflow_runs`
  - 基于 `WorkflowRepository`
  - 负责工作流运行记录服务接口

- `workflow_steps`
  - 基于 `WorkflowRepository`
  - 负责步骤日志接口与 trace 汇总

- `knowledge`
  - 基于 `ArtifactRepository` 与 `KnowledgeRepository`
  - 负责知识资产、信息事件、产物索引

## repository 划分

- `HotspotRepository`
  - 热点内容创建、查询、搜索

- `AnalysisRepository`
  - 分析报告创建、按热点或 ID 查询

- `WorkflowRepository`
  - 工作流运行记录
  - 步骤日志写入与查询

- `ArtifactRepository`
  - 产物记录
  - 信息事件

- `KnowledgeRepository`
  - 知识资产查询与更新

## 收益

- `CIO/models` 不再被多个服务层直接随意访问
- `CSO`、`CCO`、`CEO` 等部门对 CIO 数据模型的访问入口统一
- 后续替换查询策略、增加缓存、加审计字段时，只需改 repository 层
- 数据层与业务层职责更清晰
