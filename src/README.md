# AI Video Auto Production Line - MVP Backend

## 1. 项目定位

当前代码库已经不是单纯的接口骨架，而是一个可联调、可测试的 MVP 后端原型，覆盖了以下主流程：

1. 热点采集
2. AI 分析
3. 脚本生成
4. 脚本审核
5. 视频任务创建
6. 视频结果存储
7. 视频审核
8. 运营统计、审核记录、成本记录查询

当前仍属于 MVP 阶段，DeepSeek / GLM / Seedance 真实接口还没有完全接通，部分实现仍为占位逻辑。

## 2. 技术栈

- FastAPI
- SQLAlchemy Async
- MySQL 8.0
- Redis / Celery
- pytest / pytest-asyncio / aiosqlite

## 3. 本地启动

进入目录：

```powershell
cd E:\2026OPC大赛\龙虾流程
```

创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r src/requirements.txt
```

准备 `.env`：

```env
DEBUG=true
DATABASE_URL=mysql+aiomysql://root:password@127.0.0.1:3306/ai_video_prod?charset=utf8mb4
DEEPSEEK_API_KEY=
GLM_API_KEY=
SEEDANCE_API_KEY=
AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED=true

VIDEO_STORAGE_BACKEND=local
MEDIA_ROOT=runtime/media
MEDIA_URL_PREFIX=/media
MEDIA_BASE_URL=
```

启动基础服务：

```powershell
docker-compose up -d db redis
```

启动应用：

```powershell
python -m uvicorn main:app --app-dir src --reload
```

调试入口：

- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## 4. 视频存储后端

当前支持四类视频存储：

- `local`
- `github_release`
- `ipfs`
- `s3_compatible`

### 4.1 推荐顺序

开发 / 比赛演示阶段推荐：

1. `local`
2. 如需公网外链小样片，可选 `github_release`

正式部署推荐：

1. `s3_compatible`
2. 配合 CDN

不建议把 `ipfs` 或 `github_release` 当成主视频库。

### 4.2 local

```env
VIDEO_STORAGE_BACKEND=local
MEDIA_ROOT=runtime/media
MEDIA_URL_PREFIX=/media
MEDIA_BASE_URL=
```

说明：

- 文件保存在仓库根目录的 `runtime/media/videos`
- FastAPI 已自动挂载 `/media/...`
- 最适合本地调试和比赛演示

### 4.3 GitHub Release

```env
VIDEO_STORAGE_BACKEND=github_release
GITHUB_STORAGE_OWNER=
GITHUB_STORAGE_REPO=
GITHUB_STORAGE_TOKEN=
GITHUB_STORAGE_RELEASE_TAG=video-assets
```

说明：

- 适合少量演示素材
- 不适合高频写入、批量审核视频、生命周期管理

### 4.4 IPFS

```env
VIDEO_STORAGE_BACKEND=ipfs
IPFS_API_URL=http://127.0.0.1:5001
IPFS_GATEWAY_URL=https://ipfs.io/ipfs
IPFS_PIN_ON_ADD=true
```

说明：

- 技术上可接入
- 想稳定访问，需要 pinning 或自建节点
- 更适合展示型或分发型场景，不适合当前项目作为主存储

### 4.5 S3 兼容对象存储

适用于 MinIO、AWS S3、Cloudflare R2、阿里云 OSS 的 S3 兼容模式、腾讯云 COS 的 S3 兼容模式等。

```env
VIDEO_STORAGE_BACKEND=s3_compatible
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET=
S3_REGION=
S3_OBJECT_PREFIX=videos
S3_PUBLIC_BASE_URL=
```

说明：

- `S3_ENDPOINT_URL` 可为空，留给 AWS S3 默认地址
- `S3_PUBLIC_BASE_URL` 建议配置成 CDN 或公开访问域名
- 未配置 `S3_PUBLIC_BASE_URL` 时，代码会按常见 S3 URL 规则回填访问地址

## 5. AI 接口接入骨架

当前已经接入真实 AI 客户端骨架：

- DeepSeek: `/chat/completions`
- GLM: `/chat/completions`
- Seedance: `/videos/generations`

说明：

- 已支持超时、基础重试、错误捕获
- 如果未配置 API Key，默认自动回退到占位结果，方便本地联调
- 如需强制真实调用，可将 `AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED=false`

建议环境变量：

```env
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-v4

GLM_API_KEY=
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-5.1

SEEDANCE_API_KEY=
SEEDANCE_BASE_URL=https://api.seedance.ai/v1
SEEDANCE_MODEL=seedance-2.0

AI_HTTP_TIMEOUT=60
AI_MAX_RETRIES=2
AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED=true
```

## 6. Alembic 数据迁移

已初始化：

- `alembic.ini`
- `src/alembic/env.py`
- `src/alembic/versions/20260527_0001_initial_mvp_schema.py`
- `src/alembic/versions/20260529_0002_workflow_runs.py`
- `src/alembic/versions/20260529_0003_step_logs.py`

执行迁移：

```powershell
python -m alembic -c alembic.ini upgrade head
```

应用启动不会自动建表；请先执行迁移，再启动服务。

生成新迁移：

```powershell
python -m alembic -c alembic.ini revision -m "your change"
```

## 7. 主要接口

### 热点

- `POST /api/hotspots`
- `GET /api/hotspots`
- `GET /api/hotspots/search`
- `POST /api/hotspots/fetch`

### 分析

- `POST /api/analysis`
- `GET /api/analysis/hotspot/{hotspot_id}`

### 脚本

- `POST /api/scripts`
- `GET /api/scripts`
- `POST /api/scripts/review/{script_id}`

### 视频

- `POST /api/videos`
- `GET /api/videos`
- `GET /api/videos/task/{task_id}`
- `POST /api/videos/review/{task_id}`

### 运营与存储

- `GET /api/operations/summary`
- `GET /api/operations/reviews`
- `GET /api/operations/costs`
- `GET /api/operations/storage`

其中 `GET /api/operations/storage` 用于查看当前启用的存储后端和脱敏后的配置状态。

### 工作流

- `POST /api/workflows/domain-auto-run`
- `GET /api/workflows/runs`

## 8. 推荐演示顺序

1. 调用 `POST /api/hotspots/fetch`
2. 调用 `POST /api/analysis`
3. 调用 `POST /api/scripts`
4. 调用 `POST /api/scripts/review/{script_id}`
5. 调用 `POST /api/videos`
6. 调用 `POST /api/videos/review/{task_id}`
7. 调用 `GET /api/operations/summary`
8. 调用 `GET /api/operations/reviews`
9. 调用 `GET /api/operations/costs`
10. 调用 `GET /api/operations/storage`

如需走领域驱动自动链路，可直接调用：

11. `POST /api/workflows/domain-auto-run`
12. `GET /api/workflows/runs`

## 9. 测试

运行测试：

```powershell
python -m pytest -c pytest.ini src/tests -q
```

当前补充的测试重点包括：

- 热点搜索与占位采集
- 分析 -> 脚本 -> 视频主流程
- 审核记录与成本记录
- 本地视频存储
- S3 兼容存储工厂选择与配置描述
- API 层主流程联调
- 存储状态接口
- 领域工作流与运行记录查询

## 10. 当前仍未完成的部分

- 真实 AI 平台 API 接入
- Celery 异步任务真正落地
- 发布模块
- RBAC 权限控制
- 前端审核台
- Alembic 迁移脚本

## 11. 目录结构

```text
repo/
|-- Dockerfile
|-- docker-compose.yml
|-- alembic.ini
|-- pytest.ini
|-- runtime/
|   |-- logs/          # 运行日志
|   `-- media/         # 运行期媒体资产
`-- src/
    |-- app/
    |-- config/
    |-- tests/
    `-- main.py
```

