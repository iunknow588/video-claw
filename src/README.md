# AI Video Auto Production Line

## 1. 项目定位

当前仓库已经不是早期的单体 MVP 骨架，而是一个按部门职责拆分的多角色视频生产系统。  
系统以 `CEO` 为统一治理与编排入口，通过 `CFO -> CSO -> CCO -> CTO -> COO -> CQO -> CAO` 的主链路完成从选题到交付的流程，并由 `CIO / CHO / CMO` 提供运行支撑、公共能力和展示入口。

当前代码的核心特征：

- API 统一从中立装配层 `app/router` 暴露
- 业务实现按部门落在各自的 `services/use_cases`、`services`、`skills`
- 配置已拆分为 `departments / infrastructure / governance`
- 运行期产物统一收敛到仓库根目录 `runtime/`
- 数据访问、运行日志、媒体资产、工作流记录等基础能力集中到 `CIO`

## 2. 当前系统结构

### 2.1 主流程

默认主流程可以理解为：

```text
CFO -> CSO -> CCO -> CTO -> COO -> CQO -> CAO
```

各环节职责：

- `CFO`：预算闸门、成本估算、余额校验、扣费
- `CSO`：热点采集、检索、候选整理
- `CCO`：内容分析、热点拆解、分析结果沉淀
- `CTO`：提示词体系、标题候选、生产前技术校验
- `COO`：脚本生成、视频生产、字幕/配音/渲染编排
- `CQO`：质检、交付前检查、返工建议
- `CAO`：发布交付、平台适配、回调与交付记录

### 2.2 治理与支撑

- `CEO`：统一 API 入口、工作流编排、控制平面、Leader 治理、报告收集
- `CIO`：数据库、Redis、存储、运行期资产、观测、报告持久化、运营查询
- `CHO`：公共 Agent 注册、能力目录、健康状态
- `CMO`：对话入口、进度/报告展示、对外沟通界面

## 3. 仓库目录

当前仓库按“源码 / 配置 / 运行期资产 / 设计文档”分区：

```text
repo/
|-- Dockerfile
|-- docker-compose.yml
|-- alembic.ini
|-- pytest.ini
|-- runtime/                   # 运行期产物
|   |-- logs/
|   `-- media/
|-- doc/
|   `-- design/                # 设计说明与重构文档
`-- src/
    |-- app/                   # 业务源码
    |-- config/                # 分域配置
    |-- alembic/               # 数据迁移脚本
    |-- scripts/               # 联调/预检脚本
    |-- tests/                 # 测试
    |-- main.py                # 启动入口
    `-- requirements.txt
```

### 3.1 `src/app` 当前顶层模块

```text
app/
|-- CEO/
|-- CIO/
|-- CFO/
|-- CHO/
|-- CMO/
|-- CAO/
|-- COO/
|-- CQO/
|-- CTO/
|-- CSO/
`-- CCO/
```

这 11 个目录就是当前系统真实使用的部门边界。

## 4. 源码分层

### 4.1 API 入口层

- 统一入口：`src/app/router/`
- 已暴露的主要路由分组：
  - `hotspots`
  - `analysis`
  - `scripts`
  - `videos`
  - `operations`
  - `workflows`
  - `cmo`
  - `promotion`
  - `cao`
  - `ceo`

这里负责参数接收、响应返回和路由挂载，不承担底层持久化与复杂业务编排。

### 4.2 用例层

当前主要 use case 已按部门归位：

- `CEO/services/use_cases/`
  - `workflow_api.py`
  - `ceo_control_api.py`
- `CIO/services/use_cases/`
  - `operations_query.py`
- `CAO/services/use_cases/`
  - `public_console.py`
  - `publish_delivery.py`
- `CCO/services/use_cases/`
  - `analysis_api.py`
  - `content_analysis.py`
- `COO/services/use_cases/`
  - `script_api.py`
  - `video_api.py`
  - `script_to_publish.py`
  - `video_production.py`
- `CQO/services/use_cases/`
  - `quality_gate.py`
- `CFO/services/use_cases/`
  - `finance_gate.py`

### 4.3 编排层

工作流编排归 `CEO/services/orchestration/`，其中：

- `domain_workflow.py`：工作流 facade
- `assembly/`：装配部门能力
- `engine/`：执行引擎
- `recorder/`：执行记录
- `domains/`：按阶段拆分的 pipeline
- `pipeline.py`：统一 pipeline 输入输出协议

### 4.4 数据与基础设施层

`CIO` 是基础设施与数据中台，主要目录包括：

- `src/departments/CIO/db/`：数据库 session
- `src/departments/CIO/models/`：核心数据模型
- `src/departments/CIO/services/data_access/`：Repository
- `src/departments/CIO/services/database_runtime/`：数据库运行时
- `src/departments/CIO/services/redis_runtime/`：Redis 运行时
- `src/departments/CIO/services/storage/`：媒体资产与视频存储
- `src/departments/CIO/services/runtime_assets/`：仓库根目录 `runtime/` 路径解析
- `src/departments/CIO/services/observability/`：日志、指标、追踪聚合
- `src/departments/CIO/services/leader_reports/`：Leader 报告记录与查询

## 5. 配置结构

配置目录不再是单一大文件，而是三类分域：

```text
src/config/
|-- departments/
|   |-- CFO/finance.yaml
|   |-- COO/production.yaml
|   `-- CSO/hotspot.yaml
|-- infrastructure/
|   |-- ai_providers.yaml
|   |-- database.yaml
|   |-- redis.yaml
|   `-- storage.yaml
`-- governance/
    |-- application.yaml
    |-- departments.yaml
    |-- leaders.yaml
    |-- permissions.yaml
    `-- workflow.yaml
```

职责划分：

- `departments/`：部门业务配置
- `infrastructure/`：CIO 基础设施配置
- `governance/`：CEO 治理与编排配置

## 6. 运行期资产

运行期文件统一放在仓库根目录 `runtime/`，不再混在 `src/` 中：

```text
runtime/
|-- logs/
`-- media/
    |-- audio/
    |-- subtitles/
    |-- renders/
    `-- videos/
```

当前默认路径：

- 日志文件：`runtime/logs/app.log`
- 本地媒体根目录：`runtime/media`
- 本地视频访问前缀：`/media/videos/...`

## 7. 本地启动

从仓库根目录执行：

```powershell
cd E:\2026OPC大赛\龙虾流程
python -m venv .venv
.\.venv\Scripts\activate
pip install -r src/requirements.txt
```

准备环境变量时，至少确认：

```env
DATABASE_URL=mysql+aiomysql://root:YOUR_PASSWORD@127.0.0.1:3306/ai_video_prod?charset=utf8mb4
VIDEO_STORAGE_BACKEND=local
MEDIA_ROOT=runtime/media
MEDIA_URL_PREFIX=/media
AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED=true
XFYUN_MAAS_API_KEY=
SEEDANCE_API_KEY=
SEEDANCE_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
SEEDANCE_MODEL=
```

如果直接从 Ark 控制台或示例复制参数，也支持以下别名：

```env
ARK_API_KEY=
ARK_BASE_URL=
ARK_VIDEO_MODEL=
ARK_MODEL=
ARK_RESOURCE_ID=
```

启动依赖服务：

```powershell
docker-compose up -d db redis
```

执行迁移：

```powershell
python -m alembic -c alembic.ini upgrade head
```

启动应用：

```powershell
python -m uvicorn main:app --app-dir src --reload
```

访问入口：

- Swagger：`http://127.0.0.1:8000/docs`
- Health：`http://127.0.0.1:8000/health`
- CAO 控制台：`http://127.0.0.1:8000/cao`

说明：

- 应用启动时会检查数据库连通性
- 应用不会自动执行 Alembic 迁移
- 本地媒体文件会自动挂载到 `/media`

## 8. 测试与脚本

运行测试：

```powershell
python -m pytest -c pytest.ini src/tests -q
```

辅助脚本目录：

- `src/scripts/preflight_check.py`：启动前配置检查
- `src/scripts/check_seedance_access.py`：Ark 视频模型直连检查
- `src/scripts/front_flow_smoke.py`：前三段内容流程冒烟
- `src/scripts/api_workflow_smoke.py`：API 工作流冒烟
- `src/scripts/smoke_real_ai.py`：真实 AI 接口联调冒烟

推荐顺序：

1. `python src\scripts\preflight_check.py`
2. `python src\scripts\front_flow_smoke.py`
3. `python src\scripts\check_seedance_access.py`
4. `python src\scripts\api_workflow_smoke.py`

## 9. 设计文档索引

设计文档已经沉淀在 `doc/design/`，建议按下面顺序阅读：

### 总体结构

- `doc/design/README.md`
- `doc/design/体系结构与流程划分总说明.md`
- `doc/design/系统模块与技能结构说明.md`
- `doc/design/代码重构落地清单.md`

### 入口、编排与治理

- `doc/design/API路由与业务逻辑解耦说明.md`
- `doc/design/CEO服务收敛与部门归属调整说明.md`
- `doc/design/Pipeline接口标准化说明.md`
- `doc/design/CQO质检回退策略说明.md`
- `doc/design/Leader汇报与CEO查询机制.md`
- `doc/design/前三段内容流程联调说明.md`

### CIO 与基础设施

- `doc/design/基础设施运行时说明.md`
- `doc/design/Ark视频模型联调说明.md`
- `doc/design/运行期资产目录说明.md`
- `doc/design/CIO数据层统一说明.md`
- `doc/design/统一事件与日志体系说明.md`
- `doc/design/Runtime去平铺化说明.md`
- `doc/design/配置与依赖管理集中化说明.md`
- `doc/design/依赖构建集中化说明.md`

### 专项文档

- `doc/design/COO服务职责拆分说明.md`
- `doc/design/CHO公共Agent管理服务说明.md`
- `doc/design/财务预算运行时说明.md`

## 10. 当前 README 的边界

这份 README 负责回答三个问题：

1. 仓库现在长什么样
2. 系统按什么职责划分
3. 从哪里启动、配置、测试

更细的重构动机、部门边界推导、历史方案对比，统一留在 `doc/design/` 与 `doc/design/references/` 中维护。
