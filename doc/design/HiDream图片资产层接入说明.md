# HiDream 图片资产层接入说明

## 1. 目标

在不打断当前文本主链路与视频主链路的前提下，为系统增加独立的图片资产能力。

当前阶段的目标不是把图片生成强行塞进主流程，而是先建立清晰、可扩展的图片资产层，用来承接：

- 封面图
- 分镜参考图
- 关键帧图
- 海报图

## 2. 结构归属

- `src/departments/CTO/services/ai_clients/`
  - 负责 HiDream 协议封装
  - 负责签名鉴权、任务创建、任务查询
- `src/departments/COO/services/asset_management/image_generation/`
  - 负责图片任务创建、轮询、结果整理、占位图生成
- `src/departments/COO/services/use_cases/image_api.py`
  - 负责对外图片任务用例
- `src/app/router/endpoints/images/`
  - 负责图片任务公开路由
- `src/departments/CIO/models/image/`
  - 负责图片任务持久化

## 3. 与主视频链路的关系

当前主视频链路保持不变：

1. 文本分析
2. 脚本生成
3. 视频生成或预览合成

HiDream 图片层当前不是硬前置条件。

后续可按两种方式接入：

1. 作为独立图片资产任务，由人工或运营选择使用
2. 作为图生视频、封面图、关键帧预生成环节，插入 `COO` 的生产流程前段

## 4. 接口契约

根据讯飞官方 HiDream 文档，图片生成属于异步任务模式：

1. 先调用 `create`
2. 再轮询 `query`
3. 使用签名 URL 进行鉴权

系统内统一定义为：

- `create_task(...) -> ImageTask`
- `process_task(task_id) -> ImageTask`
- `get_task_status(task_id) -> ImageTask`

## 5. 后台任务事务边界

图片任务创建接口只负责：

- 校验请求
- 写入 `ImageTask`
- 返回任务 ID

真正的图片生成处理必须在独立数据库会话中执行，不能复用 HTTP 请求注入的 `AsyncSession`。

原因：

- 请求返回后，请求级事务会结束
- 背景任务若继续持有原会话，状态更新和结果落盘可能失效
- 占位图模式虽然很快，也仍然属于异步处理，不应依赖路由生命周期

因此这里的固定规则是：

- `router` / `use_case` 只登记后台任务
- 后台任务内部自行创建新会话
- 后台任务内部自行 `commit/rollback`

## 6. 配置边界

HiDream 不复用当前文本模型的 OpenAI 兼容调用方式，而是单独配置：

- `HIDREAM_APP_ID`
- `HIDREAM_API_KEY`
- `HIDREAM_API_SECRET`
- `HIDREAM_CREATE_URL`
- `HIDREAM_QUERY_URL`

默认值应指向讯飞官方文档给出的 `create/query` 地址。

## 7. 占位策略

当 HiDream 未配置时：

- 仍允许创建图片任务
- 生成本地 placeholder PNG
- 让前台、测试、流程编排先可用

这样可以保证：

1. 当前系统先跑通
2. 未来只需补齐 HiDream 凭证即可切到真实调用

## 8. 后续演进

后续可继续增加：

1. `lead.production.image_generate` skill
2. 图像审核与选优
3. 图生视频前置环节
4. `prompt_package.image_prompt_variants` 与图片任务直接联动
