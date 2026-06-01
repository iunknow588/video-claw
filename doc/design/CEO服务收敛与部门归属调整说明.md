# CEO 服务收敛与部门归属调整说明

## 1. 调整目标

本次调整要把 CEO 恢复成真正的治理内核，而不是“既治理、又接 API、又对外展示”的混合角色。

收敛后的总原则只有一句话：

`CEO 负责决策，其他部门负责对外执行。`

## 2. CEO 应该保留什么

`departments/CEO/services/` 只保留三类核心能力：

- `control/`
- `control_plane/`
- `orchestration/`

对应含义：

- `control`
  公司级治理查询、Leader 管理、演进命令、报告治理

- `control_plane`
  组织结构、治理规则、Leader 注册表、主链路定义

- `orchestration`
  工作流装配、Pipeline 编排、执行记录协同

这些能力都属于“后台治理内核”，可以被别的部门调用，但不应该直接暴露给用户。

## 3. CEO 不应该再保留什么

下面这些能力不应再由 CEO 直接对外承接：

- 对话入口
- 公开控制台
- 工作流提交入口
- 公开治理查询路径
- 面向用户的页面别名

也就是说，下面这些表达都是错误结构：

- `/api/ceo/chat`
- `/api/ceo/company-status`
- `/api/ceo/workflow`
- `/api/ceo/leaders/*`
- `/api/ceo/reports/*`
- `/ceo`

它们会让 CEO 从“治理者”退化成“前台接待员”。

## 4. 正确的承接方式

### 4.1 CMO 承接对话入口

对话、进度播报、结果汇报统一由 `CMO` 暴露：

- `/api/cmo/chat`
- `/api/promotion/chat`

### 4.2 CAO 承接公开流程与治理入口

工作流提交、公开控制台、治理查询统一由 `CAO` 暴露：

- `/api/cao/pipeline-status`
- `/api/cao/runs/*`
- `/api/cao/workflows/*`
- `/api/cao/governance/*`
- `/cao`

### 4.3 CIO 承接内部运行查询

运行摘要、成本、审核、存储、日志、事件、追踪统一由 `CIO` 承接。

## 5. 服务调用关系

正确调用链路如下：

```text
用户 -> CAO / CMO / CIO -> use_case -> CEO internal service -> control_plane / orchestration
```

这条链路说明：

- CEO 仍然是核心大脑
- 但 CEO 不直接出现在用户视角
- 前台部门只做代理与呈现，不篡改治理职责

## 6. 为什么不新增 COO 或其他部门承接公开入口

不新增的原因如下：

- `COO` 的职责是生产执行，不是行政入口
- `CIO` 的职责是内部数据与基础设施，不是用户接入
- `CAO` 天然适合做行政网关与公开控制台
- `CMO` 天然适合做人机沟通入口

因此不需要再新增 `COO`、`CSO`、`CCO` 之外的平级新部门。

## 7. 对当前代码结构的约束

今后看到下面的目录时，应该有固定预期：

- `CEO/services/control`
  后台治理查询与命令

- `CEO/services/control_plane`
  规则、组织、配置

- `CEO/services/orchestration`
  主流程编排与运行协作

- `CAO/services/use_cases`
  对外流程和治理网关

- `CMO/services/use_cases`
  对话式入口

- `CIO/services/use_cases`
  内部运行查询

只要某个“用户能直接访问的接口”又回到了 `CEO` 的公开路由前缀下，就说明边界被破坏了。

## 8. 结论

CEO 的正确定位不是“站在第一线”，而是“躲在队列后方做治理与演进”。

本次收敛的判断标准很简单：

- CEO 是否仍在公开 URL 中出现
- CEO 是否仍在直接服务用户页面
- CEO 是否仍在承接聊天或公开入口

如果答案是“是”，就还没有收敛完成。
