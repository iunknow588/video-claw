# 豆包视频模型接入记录

## 1. 用途

本文件用于记录当前项目的视频模型接入口径，避免 `.env`、Ark 控制台和历史示例文档三者不一致。

当前项目的视频生成调用链为：

`POST /api/videos`
-> `departments.COO.services.use_cases.video_api.VideoApiUseCase`
-> `departments.COO.services.video_production.VideoService`
-> `departments.CTO.services.ai_clients.SeedanceClient`
-> `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`

## 2. 当前运行时配置

项目当前从根目录 `.env` 读取以下配置：

```env
SEEDANCE_API_KEY=已配置
SEEDANCE_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
SEEDANCE_MODEL=doubao-seedance-2-0-260128
```

说明：

- `SEEDANCE_API_KEY` 已由系统实际读取并参与真实请求。
- `SEEDANCE_BASE_URL` 当前口径是 Ark OpenAI 风格接口。
- `SEEDANCE_MODEL` 必须与当前 Key 所属账号已开通的视频模型完全一致。

## 3. 历史示例与当前差异

历史示例里曾出现如下模型名：

```text
doubao-seaweed-241128
```

该模型名在 2026-06-02 的实测结果为：

- HTTP `404`
- 错误码：`InvalidEndpointOrModel.NotFound`

这说明它对当前账号而言，要么模型名已失效，要么账号无权限访问，不能直接作为项目现行配置。

## 4. 当前实测结果

测试日期：`2026-06-02`

### 4.1 按当前 `.env` 模型测试

当前模型：

```text
doubao-seedance-2-0-260128
```

实测返回：

- HTTP `404`
- 错误码：`ModelNotOpen`
- 错误含义：当前账号 `2102867909` 未开通该模型

### 4.2 按历史示例模型测试

历史示例模型：

```text
doubao-seaweed-241128
```

实测返回：

- HTTP `404`
- 错误码：`InvalidEndpointOrModel.NotFound`
- 错误含义：模型不存在，或者当前账号无权访问

## 5. 结论

当前问题不是代码链路未接通，而是“模型名 / 账号权限 / 控制台开通状态”三者仍未完全对齐。

也就是说：

- Key 已生效
- 接口地址已生效
- 本地 API 流程已走通到外部视频生成
- 当前阻塞点仍然在 Ark 模型权限侧

## 6. 推荐排查顺序

1. 在 Ark 控制台确认当前 Key 对应的账号是否就是 `2102867909`
2. 在该账号下确认真实已开通的视频模型名称
3. 将 `.env` 中的 `SEEDANCE_MODEL` 改为控制台中实际可用的模型名
4. 运行以下检查脚本再次验证

```powershell
python src\scripts\check_seedance_access.py
```

如果需要测试其他模型名：

```powershell
python src\scripts\check_seedance_access.py --model <实际模型名>
```

## 7. 备注

- 本文件保留“历史示例模型名”仅用于排错记录，不代表当前应继续使用。
- 不建议把完整 Key 再重复写入文档，统一以根目录 `.env` 作为实际运行配置源。
