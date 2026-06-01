# CIO 持久化初始化说明

## 1. 目标

`CIO` 现在已经不是简单的“内存态信息缓存层”，而是整个系统的数据与持久化中台。  
这份文档说明当前持久化初始化由谁负责、初始化到什么程度、哪些能力已经归 `CIO` 管理。

## 2. 当前持久化职责

当前持久化相关职责主要集中在：

- `src/app/CIO/db/session/`
- `src/app/CIO/models/`
- `src/app/CIO/services/data_access/`
- `src/app/CIO/services/workflow_runs/`
- `src/app/CIO/services/workflow_steps/`
- `src/app/CIO/services/leader_reports/`

其中核心模型包括但不限于：

- `analysis`
- `artifact`
- `cost`
- `hotspot`
- `information_event`
- `knowledge_asset`
- `leader_report`
- `review`
- `script`
- `step_log`
- `video`
- `workflow`

## 3. 启动时会做什么

应用启动时，`CEO/app.py` 会进入 lifespan，并调用：

- `src/app/CIO/db/session/__init__.py` 中的 `ensure_database_ready()`

当前行为是：

1. 构造数据库 engine
2. 检查数据库连通性
3. 确认运行期可以正常访问数据库

注意：

- 应用启动不会自动建表
- 应用启动不会自动执行 Alembic 迁移
- schema 变更统一通过 `alembic.ini + src/alembic/` 管理

## 4. 迁移入口

当前迁移入口位于仓库根目录：

- `alembic.ini`
- `src/alembic/env.py`
- `src/alembic/versions/`

标准执行方式：

```powershell
python -m alembic -c alembic.ini upgrade head
```

这意味着当前的持久化初始化是“两阶段”的：

1. 先跑 Alembic，确保结构到位
2. 再启动应用，确保连接可用

## 5. CIO 持久化边界

### 5.1 CIO 自己直接拥有

- 数据库 session
- SQLAlchemy 模型
- repository 层
- workflow run / step log 记录
- leader report 记录与查询
- 知识资产、分析结果、热点、脚本、视频等核心数据访问

### 5.2 其他部门如何使用

其他部门不应直接把持久化逻辑散落在自己的 API 或 skill 中，而是：

- 通过 `CIO/models`
- 通过 `CIO/services/data_access`
- 或通过 `CIO/services/*` 中的聚合服务

这也是当前“CIO 统一数据层”的落地方式。

## 6. 与工作流的关系

工作流相关持久化已经分成两层：

- `workflow_runs`
  负责工作流整体运行记录

- `workflow_steps`
  负责步骤日志、阶段性 trace 和明细事件

这样 `CEO` 可以专注编排，`CIO` 专注记录与查询。

## 7. 与报告机制的关系

Leader 周期性报告和 CEO 主动查询结果也已经进入 `CIO` 的持久化边界，主要通过：

- `src/app/CIO/models/leader_report/`
- `src/app/CIO/services/leader_reports/`

这说明报告中心虽然服务于 `CEO` 治理，但记录和查询能力仍由 `CIO` 承接。

## 8. 结论

当前持久化初始化的正确理解是：

- 结构初始化：Alembic 负责
- 连接检查：应用启动时负责
- 数据边界：CIO 统一承接

也就是说，`CIO` 已经是系统真正的数据底座，而不是临时性的信息缓存层。
