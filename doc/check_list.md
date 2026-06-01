# AI视频自动生产线任务清单（历史归档）

> 说明：这份文档形成于早期方案讨论阶段，包含旧的 skill 分层、旧路径和旧里程碑拆分。
> 当前系统结构请以 `src/README.md`、`doc/README.md`、`doc/design/README.md` 和实际源码目录为准。

## 当前阅读方式

这份清单建议仅作为历史参考使用，主要可参考：

- 当时如何拆分 CEO / LOG / LEAD / SKILL 的职责想法
- 历史阶段里程碑如何规划
- 哪些 backlog 至今仍有追踪价值

以下内容不要再直接视为当前实现事实：

- `src/app/services/*` 一类平铺结构
- 旧版 workflow 归属
- 旧版发布链路目录
- 未更新过的阶段性完成状态

## 当前正式结构速记

当前系统以 `src/app/` 下 11 个部门目录为准：

- `CEO`
- `CIO`
- `CFO`
- `CHO`
- `CMO`
- `CAO`
- `COO`
- `CQO`
- `CTO`
- `CSO`
- `CCO`

当前运行时资产统一放在：

- `runtime/logs/`
- `runtime/media/`

当前启动与基础设施入口统一放在仓库根目录：

- `Dockerfile`
- `docker-compose.yml`
- `alembic.ini`
- `pytest.ini`

## 归档说明

如需继续整理这份清单，建议后续将其中仍有价值的 backlog 迁移到单独的 `doc/design/` 专题文档中，而不是继续把它当作当前执行清单维护。
