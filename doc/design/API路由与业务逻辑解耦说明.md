# API 路由与业务逻辑解耦说明

## 1. 调整目标

这次调整的目标不是单纯把端点写薄，而是把“谁对外说话”这件事彻底理顺。

最终规则如下：

- `router` 只做 HTTP 协议层
- `use_cases` 负责入口级用例编排
- `services` 负责业务协作
- `skills` 负责单一动作
- `CEO` 不再作为任何公开接口前缀

## 2. 路由归属结论

当前不新增 COO 或独立“路由部门”。

职责划分如下：

- `CAO`：对外工作流入口、治理入口、公开控制台入口
- `CMO`：对话入口、消息流入口
- `CIO`：内部查询入口、运行态数据入口
- `CEO`：后台治理内核，不直接暴露公开 API

因此公开路由的部门语义是：

- `CAO` 管公开工作流与治理
- `CMO` 管对话
- `CIO` 管内部查询
- `CEO` 只保留后台编排与治理

## 3. 当前必须避免的反模式

以下做法都应禁止：

1. 公开路径使用 `/api/ceo/*`
2. 端点中直接写数据库查询
3. 端点中直接拼复杂业务响应
4. 路由层越级依赖跨部门底层实现
5. 用 `CEO*` 命名公开 DTO

## 4. 目标 API 结构

```text
src/
  app/
    router/
      endpoints/
        cao/
        cmo/
        promotion/
        operations/
        hotspots/
        analysis/
        scripts/
        videos/
        images/

  departments/
    CAO/services/use_cases/
      governance_gateway.py
      workflow_gateway.py
      public_console.py

    CMO/services/use_cases/
      chat_stream.py

    CIO/services/use_cases/
      operations_query.py

    CEO/services/
      control/
      control_plane/
      orchestration/
```

说明：

- `src/app/router/` 是中立装配层，不属于任何部门
- 对外入口的部门语义，以 URL 前缀和对应 use case 所属部门为准

## 5. 路由到用例映射

- `/api/cao/pipeline-status` -> `CAO/services/use_cases/public_console.py`
- `/api/cao/runs/*` -> `CAO/services/use_cases/public_console.py`
- `/api/cao/workflows/*` -> `CAO/services/use_cases/workflow_gateway.py`
- `/api/cao/governance/*` -> `CAO/services/use_cases/governance_gateway.py`
- `/api/cmo/chat` -> `CMO/services/use_cases/chat_stream.py`
- `/api/promotion/chat` -> `CMO/services/use_cases/chat_stream.py`
- `/api/operations/*` -> `CIO/services/use_cases/operations_query.py`
- `/api/hotspots/*` -> `CSO/services/use_cases/hotspot_api.py`
- `/api/analysis/*` -> `CCO/services/use_cases/analysis_api.py`
- `/api/scripts/*`、`/api/videos/*`、`/api/images/*` -> `COO/services/use_cases/*`

## 6. 路由层只允许做什么

端点函数只允许保留下列内容：

- FastAPI 参数声明
- `Depends(...)`
- 调用单个 use case
- 把领域异常映射为 `HTTPException`
- 登记后台任务

端点函数不再直接做：

- `select(...)`
- `session.execute(...)`
- Repository 直调
- 业务状态判断
- 复杂响应拼装
- 事件流编排

补充约束：

- 后台任务如果涉及数据库写入，必须由后台任务自己新建会话
- 路由注入的请求级 `AsyncSession` 不能跨请求传给后台异步任务继续使用
- `use_cases` 可以决定“是否异步”，但不能把已结束的请求事务继续外泄给 `services`

## 7. 用例层职责

### 7.1 CAO

- 接收对外工作流请求
- 暴露治理查询网关
- 暴露公开控制台数据
- 对外统一屏蔽 CEO 内部实现细节

### 7.2 CMO

- 解释用户消息
- 输出回复事件
- 输出进度事件
- 输出结果或报告事件

### 7.3 CIO

- 查询运行数据
- 查询成本与审计信息
- 查询存储状态
- 承接事件、日志、追踪、持久化支撑

### 7.4 CEO

- 维护控制平面
- 管理 Leader
- 组织工作流规则
- 作为后台治理服务被 `CAO/CMO` 委托调用

## 8. 命名规则

公开接口与公开 DTO 不再使用 `CEO*` 前缀，应改为：

- 通用对话请求 -> `ChatMessageRequest`
- 治理请求 -> `Governance*Request`
- 工作流请求 -> `Workflow*Request`

这样可以保证：

- 公开接口语义不再把 CEO 推到前台
- DTO 名称与真实职责一致
- 文档、测试、代码三处表达统一

## 9. 结论

路由层的正确结构不是“CEO 统一对外”，而是：

- 应用装配中立集中
- 对外职责必须分流
- 行政工作流入口归 `CAO`
- 对话入口归 `CMO`
- 内部查询归 `CIO`
- `CEO` 只在后台治理
