# 讯飞 MaaS 文本接入说明

## 1. 目标

当前阶段先跑通主流程，不追求一次性统一所有外部模型能力。

本次接入范围只覆盖文本链路：

- `CCO/services/content_creation/`：热点内容分析
- `COO/services/script_management/`：脚本生成

视频生成链路暂不改动，继续保持独立 provider 与占位渲染兜底：

- `COO/services/video_production/`
- `COO/services/composition/`
- `CIO/services/storage/`

## 2. 边界

本次只做三件事：

1. 在 `CTO/services/ai_clients/` 增加 `xfyun_maas` 文本 provider
2. 让分析与脚本服务统一走 `xfyun_maas`
3. 让 `CFO` 的预算与 provider 就绪检查识别 `xfyun_maas`

本次不做：

- 不接入新的真实视频生成服务
- 不改动现有 `Seedance` 视频调用结构
- 不把全部历史 provider 配置一次性删除

## 3. 结构归属

按当前部门划分，职责如下：

- `CTO`
  - 负责 AI provider client 封装
  - 负责 `xfyun_maas` 的请求协议适配
- `CCO`
  - 负责分析用例
  - 只关心“拿到结构化 JSON 分析结果”
- `COO`
  - 负责脚本生成用例
  - 只关心“拿到结构化 JSON 脚本结果”
- `CFO`
  - 负责文本 provider 的预算预检与可用性校验
- `CIO`
  - 继续负责配置装载、存储、日志与运行时资产

`CEO` 不直接承接任何模型接入细节，只保留编排。

## 4. 配置策略

新增 `xfyun_maas` 配置段，最小字段如下：

- `api_key`
- `base_url`
- `model`
- `resource_id`（可选，默认空；当接入微调模型时再传）

推荐默认值：

- `base_url = https://maas-coding-api.cn-huabei-1.xf-yun.com/v2`
- `model = astron-code-latest`

当前代码只使用 OpenAI 兼容入口。

- `openai_url = https://maas-coding-api.cn-huabei-1.xf-yun.com/v2`
- `anthropic_url = https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic`

`anthropic_url` 暂不入配置。等系统真正增加 Anthropic 协议 client 时，再由 `CTO/services/ai_clients/` 单独承接。

## 5. 调用策略

讯飞 MaaS 文本链路采用 OpenAI 兼容的 `chat/completions` 风格接口。

分析与脚本服务统一遵循以下原则：

1. 使用 system prompt 明确要求返回 JSON
2. 不依赖 DeepSeek 专属 `response_format=json_object`
3. 在服务端统一做 JSON 提取与解析
4. 当 `resource_id` 为空或为 `0` 时，不附带微调模型标识

## 6. 流程影响

主流程变化后应满足：

1. 用户从 `CAO` 发起工作流
2. `CFO` 只检查 `xfyun_maas` 与 `seedance`
3. `CCO` 用 `xfyun_maas` 完成分析
4. `COO` 用 `xfyun_maas` 完成脚本生成
5. 视频阶段继续按当前配置决定：
   - 不生成真实视频：走预览/占位渲染
   - 生成真实视频：仍由独立视频 provider 承接

## 7. 后续扩展

等主流程稳定后，再做第二阶段：

1. 为视频生成新增正式 provider
2. 让 `COO/video_production` 支持多视频 provider 切换
3. 再决定是否彻底移除 `deepseek/glm` 旧文本配置
