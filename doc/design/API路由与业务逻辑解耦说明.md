# API 路由与业务逻辑解耦说明

## 1. 调整目标

本次调整的目标不是单纯把端点变薄，而是把“谁对外说话”这件事彻底理顺。

最终规则如下：

- `router` 只做 HTTP 协议层
- `use_cases` 负责入口级用例编排
- `services` 负责业务协作
- `skills` 负责单一动作
- `CEO` 不再作为任何公开接口前缀

## 2. 路由归属结论

当前不新增 COO、COO-like 或独立“路由部门”。

理由很明确：

- `COO` 是生产执行部门，不负责全局对外接入
- `CIO` 适合内部查询接口，不适合承接用户工作流入口
- `CAO` 最适合承接行政入口、流程入口、治理查询入口
- `CMO` 最适合承接会话式入口

因此最终分层为：

- `CAO`：对外工作流与治理网关
- `CMO`：对话与沟通事件流
- `CIO`：内部运行查询
- `CEO`：后台治理内核，不直接暴露公开 API

## 3. 当前应避免的反模式

以下做法都应该禁止：

1. 公开路径使用 `/api/ceo/*`
2. 端点里直接写数据库查询
3. 端点里直接拼装复杂业务状态
4. 路由模块直接越级依赖跨部门底层实现
5. 用 CEO 命名对外请求对象与接口模型

## 4. 目标 API 结构

```text
src/
  app/
    app.py
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

- `src/app/router/` 是中立装配层，不属于任何部门。
- 端点的语义归属以 URL 前缀和 use case 所在部门为准。

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
- `/api/scripts/*` 与 `/api/videos/*` -> `COO/services/use_cases/*`

## 6. 路由层只允许做什么

端点函数只允许保留下面四类内容：

- FastAPI 参数声明
- `Depends(...)`
- 调用单个 use case
- 把领域异常映射为 `HTTPException`

端点函数不允许再直接做：

- `select(...)`
- `session.execute(...)`
- Repository 直调
- 业务状态判断
- 复杂响应拼装
- 事件流编排

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
- 查询成本与审核信息
- 查询存储状态
- 承接事件、日志、追踪、持久化支撑

### 7.4 CEO

- 维护控制平面
- 管理 Leader
- 组织工作流规则
- 作为后台治理服务被 CAO/CMO 委托调用

## 8. 命名规则

公开接口与公开 DTO 不再使用 `CEO*` 前缀。

应改为：

- 通用对话请求 -> `ChatMessageRequest`
- 治理类请求 -> `Governance*Request`
- 工作流类请求 -> `Workflow*Request`

这样可以保证：

- 公开接口语义不再把 CEO 放在前台
- DTO 名称和真实职责一致
- 文档、测试、代码三处表达统一

## 9. 结论

路由层的正确结构不是“CEO 统一对外”，而是：

- 应用装配中立集中
- 对外职责必须分流
- 行政入口归 `CAO`
- 对话入口归 `CMO`
- 内部查询归 `CIO`
- CEO 只在后台治理

只要还有 `/api/ceo/*` 这样的公开路径，就说明这次解耦还没有完成。
