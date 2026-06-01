# Runtime 去平铺化说明

## 目标

前几轮已经把业务层与入口层的大部分 `settings.*` 直读收回到了 runtime 模块。本轮继续向前一步：

1. runtime 模块优先消费部门配置域对象
2. 不再把平铺字段当作一等配置来源

## 问题

虽然 `services / skills / app entry` 已经基本改为只读 runtime，但部分 runtime 自身仍旧直接依赖平铺字段，例如：

1. `CTO/services/ai_clients/`
2. `CIO/services/storage/`
3. `CEO/services/control_plane/defaults/`

这样会留下一个结构性尾巴：

1. domain object 已经存在，但 runtime 还在绕回平铺层
2. 平铺字段变成“事实主源”，不利于后续继续收敛

## 方案

### CTO

AI runtime 直接读取：

- `settings.ai_providers.deepseek`
- `settings.ai_providers.glm`
- `settings.ai_providers.seedance`
- `settings.ai_providers.runtime`

### CIO

Storage runtime 直接读取：

- `settings.storage`

### CEO

控制平面默认值直接读取：

- `settings.leaders`
- `settings.workflow`

## 原则

1. **domain object 是 runtime 主源**
2. **flat settings 只保留给外部兼容测试与少量边缘调用**
3. **runtime 内部不重复解释平铺字段**

## 结果

这样收口后，配置链路会更清楚：

`config files -> config manager -> domain object -> runtime -> services / skills / app entry`

而不是：

`config files -> domain object -> sync flat fields -> runtime -> services`

后续如果继续清理，平铺字段就只剩下外部兼容表面，不再参与内部主路径。
