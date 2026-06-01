# API 路由与业务逻辑解耦说明

## 1. 调整目标

本次调整的目标，是把 `app/CEO/router` 明确收敛为 API 入口层，而不是继续承担业务编排、查库、状态拼装等职责。

调整后遵循三条硬规则：

- 路由只负责参数接收、异常映射、响应返回
- 业务用例放入责任部门的 `services/use_cases`
- Repository、领域服务、Skill、Pipeline 不允许直接散落在端点函数里

## 2. 组织归属判断

当前不新增专门的“路由部门”。

原因如下：

- API 路由本质是系统入口，不是独立业务部门
- `COO` 负责生产执行，不适合承担全局 API 入口管理
- `CAO` 负责对外交付与发布，不适合接管全量内部 API 路由
- `CIO` 可以承接内部数据与内部结构治理，但当前对外 API 总入口仍应保留在 `CEO`

因此，本阶段的清晰划分是：

- `CEO/router` 负责统一 API 暴露
- 各部门 `services/use_cases` 负责本部门业务用例
- `CIO` 继续承接数据访问、存储、运营统计、观测与日志

这意味着“入口统一归 CEO，业务实现归各责任部门”，而不是“所有逻辑都塞回 CEO”。

## 3. 调整前的问题

当前路由层主要存在四类问题：

1. `workflows` 端点直接实例化 `WorkflowRunService`、`WorkflowStepLogService`
2. `operations` 端点直接写 `select(...)` 查询
3. `analysis`、`scripts`、`videos`、`hotspots` 端点中存在查库、去重、状态校验
4. `ceo`、`cmo` 端点中混入流式事件组装逻辑

这些问题会导致：

- 路由层职责膨胀
- 业务规则散落在多个端点
- 查询策略难以复用
- 测试只能从 API 级别覆盖，单测颗粒度过粗

## 4. 目标结构

```text
app/
  CEO/
    router/
      endpoints/
        hotspots/
        analysis/
        scripts/
        videos/
        workflows/
        operations/
        cmo/
        cao/
        ceo/

  CEO/services/use_cases/
    workflow_api.py
    ceo_control_api.py

  CMO/services/use_cases/
    chat_stream.py

  CAO/services/use_cases/
    public_console.py

  CIO/services/use_cases/
    operations_query.py

  CSO/services/use_cases/
    hotspot_api.py

  CCO/services/use_cases/
    analysis_api.py

  COO/services/use_cases/
    script_api.py
    video_api.py
```

## 5. 路由到用例映射

- `/api/workflows/*` -> `CEO/services/use_cases/workflow_api.py`
- `/api/ceo/*` -> `CEO/services/use_cases/ceo_control_api.py`
- `/api/cmo/chat` 与 `/api/promotion/chat` -> `CMO/services/use_cases/chat_stream.py`
- `/api/cao/*` -> `CAO/services/use_cases/public_console.py`
- `/api/operations/*` -> `CIO/services/use_cases/operations_query.py`
- `/api/hotspots/*` -> `CSO/services/use_cases/hotspot_api.py`
- `/api/analysis/*` -> `CCO/services/use_cases/analysis_api.py`
- `/api/scripts/*` 与 `/api/videos/*` -> `COO/services/use_cases/*`

## 6. 端点层约束

端点函数允许保留的内容只有：

- FastAPI 参数声明
- `Depends(get_db)`
- 调用单个 use case
- 把 `ValueError` 等业务异常映射为 `HTTPException`

端点函数不再直接做以下事情：

- `select(...)`
- `session.execute(...)`
- Repository 直调
- 领域对象存在性判断
- 业务状态校验
- 事件流拼装细节

## 7. 用例层职责

### 7.1 CEO

- 工作流发起
- 工作流历史与 trace 查询
- CEO 管理面查询与命令下发

### 7.2 CMO

- 会话事件流
- 回复事件、进度事件、结果事件的统一输出

### 7.3 CIO

- 运营汇总
- 评审记录查询
- 成本记录查询
- 存储状态查询

### 7.4 CSO / CCO / COO / CAO

- 各自负责本部门 API 对应的用例编排
- 复用本部门已有 service、repository、skill、pipeline

## 8. 结构收益

完成后将得到更稳定的分层关系：

- `router` 薄
- `use_case` 清晰
- `service` 复用明确
- `repository` 不再泄漏到接口层

同时也更符合当前部门化架构：

- `CEO` 统一入口与治理
- `CIO` 统一数据与观测
- `CMO` 统一沟通事件
- `COO / CSO / CCO / CAO / CQO / CTO / CFO / CHO` 各守本职

## 9. 本次落地范围

本次代码修改按下面顺序推进：

1. 为各端点补齐 use case
2. 将路由中的查库与状态判断迁移到 use case
3. 保持 API 路径不变
4. 不引入兼容层，不保留双实现

这样改完以后，`CEO/router` 终于能像一个真正的入口层，而不是半个控制器、半个服务层。
