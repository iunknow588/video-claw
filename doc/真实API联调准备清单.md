# 真实 API 联调准备清单

## 1. 目标

这份清单用于在拿到 DeepSeek / GLM / Seedance API Key 之后，快速完成联调准备并验证当前项目是否已经能跑通真实链路。

联调目录：

- `E:\2026OPC大赛\龙虾流程\src`

## 2. 当前代码已经准备好的内容

当前项目已经具备：

- DeepSeek 客户端骨架
- GLM 客户端骨架
- Seedance 客户端骨架
- 统一错误处理和回退逻辑
- Alembic 迁移
- API 层测试
- 存储状态接口

重点文件：

- [src/app/services/ai_clients.py](E:\2026OPC大赛\龙虾流程\src\app\services\ai_clients.py)
- [src/app/services/analysis.py](E:\2026OPC大赛\龙虾流程\src\app\services\analysis.py)
- [src/app/services/script.py](E:\2026OPC大赛\龙虾流程\src\app\services\script.py)
- [src/app/services/video.py](E:\2026OPC大赛\龙虾流程\src\app\services\video.py)
- [src/alembic/versions/20260527_0001_initial_mvp_schema.py](E:\2026OPC大赛\龙虾流程\src\alembic\versions\20260527_0001_initial_mvp_schema.py)

## 3. 拿到 Key 后先做什么

### 第一步：复制环境模板

把：

- [src/.env.example](E:\2026OPC大赛\龙虾流程\src\.env.example)

复制为：

- `E:\2026OPC大赛\龙虾流程\src\.env`

### 第二步：填入真实 Key

至少填写：

```env
DEEPSEEK_API_KEY=你的key
GLM_API_KEY=你的key
SEEDANCE_API_KEY=你的key
```

并把：

```env
AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED=false
```

这样系统才会强制走真实第三方调用，而不是占位回退。

### 第三步：检查数据库和存储配置

推荐先保持：

```env
VIDEO_STORAGE_BACKEND=local
MEDIA_ROOT=runtime/media
MEDIA_URL_PREFIX=/media
```

这样能先把“AI 生成链路”跑通，不额外引入对象存储变量。

## 4. 联调前自检

运行：

```powershell
cd E:\2026OPC大赛\龙虾流程\src
.\.venv\Scripts\python.exe scripts\preflight_check.py
```

用途：

- 检查 key 是否已填
- 检查当前是不是强制真实调用模式
- 检查视频存储后端配置是否完整

## 5. 第一个真实冒烟测试

运行：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_real_ai.py
```

这个脚本会直接走服务层，依次触发：

1. DeepSeek 分析
2. GLM 脚本生成
3. Seedance 视频任务处理

它不会依赖外部 MySQL，内部使用内存 SQLite 做临时验证。

### 正常时你应该看到

- `[analysis] ...`
- `[script] ...`
- `[video] status='completed' ...`

### 如果失败

常见原因通常是：

- API Key 不对
- 模型名和账户权限不匹配
- Seedance 实际返回字段和当前代码假设不一致
- 账户未开通对应模型

## 6. 第二个验证：数据库迁移

运行：

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

正常说明：

- 迁移脚本可执行
- 数据表可创建
- 当前数据库连接参数可用

## 7. 第三个验证：启动服务

先启动依赖：

```powershell
docker-compose up -d db redis
```

启动服务：

```powershell
uvicorn main:app --reload
```

打开：

- `http://127.0.0.1:8000/docs`

## 8. 第四个验证：接口链路联调

按这个顺序调：

1. `POST /api/hotspots/fetch`
2. `POST /api/analysis`
3. `POST /api/scripts`
4. `POST /api/scripts/review/{script_id}`
5. `POST /api/videos`
6. `GET /api/videos/task/{task_id}`
7. `GET /api/operations/summary`
8. `GET /api/operations/storage`

## 9. 哪些步骤会真实调用第三方

当 `AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED=false` 且 key 已配置时：

- `POST /api/analysis` 会真实调用 DeepSeek
- `POST /api/scripts` 会真实调用 GLM
- `POST /api/videos` 后台处理会真实调用 Seedance

## 10. 当前最可能出现的适配点

真正联调时，最可能要微调的是：

1. DeepSeek 响应 JSON 字段解析
2. GLM 返回内容的 JSON 提取
3. Seedance 返回视频地址字段名

尤其是 Seedance，这类平台很容易返回：

- `video_url`
- `url`
- `download_url`
- 或异步任务 id

如果它返回的是任务 id 而不是现成视频地址，下一步就需要再加“轮询任务状态”的实现。

## 11. 当前资料包

你拿到 key 之后，最直接会用到的是：

- [src/.env.example](E:\2026OPC大赛\龙虾流程\src\.env.example)
- [src/scripts/preflight_check.py](E:\2026OPC大赛\龙虾流程\src\scripts\preflight_check.py)
- [src/scripts/smoke_real_ai.py](E:\2026OPC大赛\龙虾流程\src\scripts\smoke_real_ai.py)
- [src/README.md](E:\2026OPC大赛\龙虾流程\src\README.md)

## 12. 一句话建议

拿到 key 后，先不要一上来就跑整套 Swagger 流程。

最稳的顺序是：

1. `preflight_check.py`
2. `smoke_real_ai.py`
3. `alembic upgrade head`
4. `uvicorn main:app --reload`
5. Swagger 主链路联调

