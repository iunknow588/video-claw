# COO服务职责拆分说明

## 目标

将 `COO/services` 从按技术实现命名的散点目录，调整为按 COO 职责边界命名的结构：

- `script_management`
- `video_production`
- `asset_management`
- `composition`
- `use_cases`

这样目录即语义，后续扩展时不需要先读源码再猜归属。

## 调整前问题

- `script/` 与 `video/` 是生命周期服务，但命名过于短平
- `subtitle_composer/`、`voiceover/` 实际都属于素材资产
- `video_composition/`、`render_execution/` 实际都属于合成渲染
- `operation_pipeline/` 实际是端到端工作流入口，不是 COO 内部技术流水线

## 调整后结构

```text
COO/services/
  script_management/      # 脚本生命周期
  video_production/       # 视频任务生命周期
  asset_management/       # 字幕、配音等素材资产
  composition/            # 合成计划与渲染执行
  use_cases/              # COO 用例编排
```

## 职责划分

- `script_management`
  - `ScriptService`
  - 管理脚本生成、审核、状态流转

- `video_production`
  - `VideoService`
  - 管理视频任务创建、处理、审核

- `asset_management`
  - `SubtitleComposerService`
  - `VoiceoverService`
  - 负责脚本衍生资产生成

- `composition`
  - `VideoCompositionService`
  - `RenderExecutionService`
  - 负责合成方案与交付渲染

- `use_cases`
  - `VideoProductionUseCase`
  - `ScriptToPublishUseCase`
  - 负责 COO 级流程编排

## 收益

- 路径命名与 COO 责任结构一致
- 视频制作、脚本管理、素材管理、合成渲染分层更清楚
- 新增素材类能力时统一归入 `asset_management`
- 新增合成与导出能力时统一归入 `composition`
