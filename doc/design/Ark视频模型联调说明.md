# Ark视频模型联调说明

## 1. 目标

这份说明用于统一 Ark 控制台、`.env` 配置和项目视频调用链三者的口径，避免出现：

- Key 已配置，但模型名不一致；
- 文档示例模型名已经失效；
- 接口地址正确，但账号权限未开通；
- 系统误以为是本地代码问题。

## 2. 当前调用链

项目当前的视频生成链路如下：

```text
POST /api/videos
-> COO/services/use_cases/video_api.py
-> COO/services/video_production/__init__.py
-> CTO/services/ai_clients/__init__.py
-> Ark /contents/generations/tasks
```

职责分层：

- `app/router/endpoints/videos/`：纯路由入口
- `COO/services/use_cases/video_api.py`：创建任务、调度后台执行
- `COO/services/video_production/`：视频生产业务服务
- `CTO/services/ai_clients/`：外部模型 HTTP 客户端

## 3. 配置口径

项目正式使用以下运行时变量：

```env
SEEDANCE_API_KEY=
SEEDANCE_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
SEEDANCE_MODEL=
SEEDANCE_RESOURCE_ID=
```

为兼容 Ark 文档或控制台复制口径，运行时还支持以下别名：

```env
ARK_API_KEY=
ARK_BASE_URL=
ARK_MODEL=
ARK_VIDEO_MODEL=
ARK_RESOURCE_ID=
```

别名映射规则：

- 当 `SEEDANCE_API_KEY` 为空时，回退到 `ARK_API_KEY`
- 当 `SEEDANCE_BASE_URL` 为空时，回退到 `ARK_BASE_URL`
- 当 `SEEDANCE_MODEL` 为空时，优先回退到 `ARK_VIDEO_MODEL`，其次回退到 `ARK_MODEL`
- 当 `SEEDANCE_RESOURCE_ID` 为空时，回退到 `ARK_RESOURCE_ID`

因此，后续如果直接从 Ark 控制台拷贝参数，至少不会再因为变量名不同而失效。

## 4. 推荐联调步骤

### 4.1 先做静态预检

```powershell
python src\scripts\preflight_check.py
```

用于确认：

- `.env` 是否被系统读取；
- `SEEDANCE_*` 或 Ark 别名是否已生效；
- 文本模型、图片模型、视频模型的基础配置是否齐全。

### 4.2 再做视频模型直连检查

```powershell
python src\scripts\check_seedance_access.py
```

如果要临时测试控制台里的候选模型名：

```powershell
python src\scripts\check_seedance_access.py --model <候选模型名>
```

该脚本会直接请求：

```text
POST https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks
```

并输出：

- HTTP 状态码
- Ark 原始错误体
- 当前使用的模型名

### 4.3 最后做本地 API 全链路测试

```powershell
python src\scripts\api_workflow_smoke.py
```

只有在 `check_seedance_access.py` 已经成功的前提下，才值得继续跑完整工作流。

## 5. 常见错误与含义

### `ModelNotOpen`

含义：

- 当前 Key 对应账号尚未开通该模型

处理：

- 去 Ark 控制台核对当前 Key 所属账号
- 确认该账号下的视频模型是否真的开通

### `InvalidEndpointOrModel.NotFound`

含义：

- 模型名不存在，或者当前账号无权限访问该模型

处理：

- 不要继续猜模型名
- 直接从 Ark 控制台复制可用模型名后重新验证

## 6. 当前原则

- 视频模型连通性校验属于 `CTO` 外部能力接入职责
- 视频生成业务编排属于 `COO`
- 路由层只负责暴露接口，不负责拼接供应商细节
- CEO 不直接承接这类一线外部接口工作
