# Leader 汇报与 CEO 查询机制

## 1. 目标

这套机制解决三件事：

1. 各部门 Leader 能按统一方式提交阶段汇报。
2. CEO 能在内部治理链路中查看最新汇报和历史汇报。
3. 对外查询入口与内部治理入口分层，避免把 CEO 直接暴露成公开 API 前台。

## 2. 当前职责归属

当前系统中，这条链路已经按职责拆开：

- `CEO`：定义汇报治理规则、决定汇报口径、发起内部查询与催报。
- `CIO`：负责汇报数据持久化、历史检索、查询服务。
- `CAO`：承接外部可访问的治理网关与公开查询入口。

也就是说：

- “汇报制度”归 `CEO`
- “汇报数据”归 `CIO`
- “对外接口”归 `CAO`

## 3. 当前代码位置

### 3.1 持久化与查询

- `src/app/CIO/models/leader_report/`
- `src/app/CIO/services/leader_reports/`

### 3.2 CEO 内部治理与控制面

- `src/app/CEO/services/control/`
- `src/app/CEO/services/control_plane/`

### 3.3 CAO 外部治理网关

- `src/app/CAO/services/use_cases/governance_gateway.py`

## 4. 路由归属

对外不再以 `/api/ceo/*` 形式暴露汇报查询接口，而是统一放在 CAO 治理网关下。

当前应以这组入口为准：

- `POST /api/cao/governance/reports/collect`
- `GET /api/cao/governance/reports`
- `GET /api/cao/governance/leaders/{leader_name}/reports`
- `GET /api/cao/governance/leaders/{leader_name}/reports/latest`
- `POST /api/cao/governance/leaders/{leader_name}/request-report`

## 5. 设计含义

这样整理后，系统边界更清楚：

- CEO 仍然掌握治理权，但不直接承担公开 API 门面职责。
- CIO 统一保存汇报记录，避免各部门各自留一份“影子数据”。
- CAO 作为对外治理入口，负责统一呈现和查询。

## 6. 后续完善方向

还可以继续补三类能力：

1. 汇报治理状态：如“已阅”“已确认”“需补充”。
2. 汇报节奏策略：如 `cadence` 配置化。
3. CIO 汇报与真实运行事件联动：把 workflow、质检、发布结果摘要纳入汇报视图。
