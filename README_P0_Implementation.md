# 龙虾流程 P0 改造实施文档

## 实施概览

本次实施按照评审建议，完成了以下 5 个任务的代码改造：

| 任务 | 内容 | 状态 | 文件 |
|------|------|------|------|
| Task A | 数据库模型 + Alembic 迁移 | ✅ 完成 | `migrations/versions/20260603_add_trigger_id.py` |
| Task B | WorkflowRunService 接口扩展 | ✅ 完成 | `src/departments/CIO/services/workflow_runs/__init__.py` |
| Task C | WorkflowExecutionEngine 透传 trigger_id | ✅ 完成 | `src/departments/CEO/services/orchestration/engine/__init__.py` |
| Task D | API 端点与文档 | ✅ 完成 | `src/app/router/endpoints/cao/workflows.py` |
| Task E | TriggerScanner 调度器（缩减版） | ✅ 完成 | `src/departments/CIO/services/scheduler/__init__.py` |

## 关键设计决策

### 1. 复合索引策略

按照评审建议，增加了两个复合索引：

```sql
-- 按 trigger_id + created_at 查询（最常见场景）
CREATE INDEX ix_workflow_runs_trigger_id_created_at 
ON workflow_runs (trigger_id, created_at) 
WHERE trigger_id IS NOT NULL;

-- 按 trigger_id + status 查询（去重场景）
CREATE INDEX ix_workflow_runs_trigger_id_status 
ON workflow_runs (trigger_id, status) 
WHERE trigger_id IS NOT NULL;
```

### 2. 并发控制（去重机制）

TriggerScanner 实现了双重去重：

1. **Cooldown 检查**：`last_fired_at + cooldown_seconds` 内不重复触发
2. **Active Run 检查**：查询 `pending`/`running` 状态的运行，防止并发重复

```python
# 检查 cooldown
if trigger.last_fired_at:
    cooldown_end = trigger.last_fired_at + timedelta(seconds=self.cooldown_seconds)
    if now < cooldown_end:
        return  # 跳过

# 检查 active runs
duplicate_query = select(WorkflowRun).where(
    and_(
        WorkflowRun.trigger_id == trigger.id,
        WorkflowRun.status.in_(['pending', 'running'])
    )
)
```

### 3. 错误隔离

一个 trigger 的失败不影响其他 trigger：

```python
for trigger in triggers:
    try:
        await self._fire_trigger(trigger, session)
    except Exception as e:
        logger.error(f"Failed to fire trigger {trigger.id}: {e}")
        continue  # 继续处理其他 trigger
```

### 4. 向后兼容

所有新增字段均为 `nullable=True`，现有代码无需修改：

```python
trigger_id = Column(String(36), nullable=True, comment='Trigger ID')
```

## API 示例

### 创建 Trigger

```bash
POST /workflows/triggers
Content-Type: application/json

{
  "name": "daily-hotspots",
  "cron": "0 3 * * *",
  "domain": "科技",
  "platform": "douyin",
  "input": {"audience": "年轻人", "publish_goal": "吸引关注"},
  "enabled": true
}
```

### 手动触发工作流（携带 trigger_id）

```bash
POST /workflows/runs
Content-Type: application/json

{
  "domain": "科技",
  "platform": "douyin",
  "input_params": {"audience": "年轻人"},
  "trigger_id": "trigger-daily-hotspots"
}
```

### 查询 Trigger 的所有运行

```bash
GET /workflows/runs?trigger_id=trigger-daily-hotspots&status=completed&limit=10
```

### 查询 Trace（包含 trigger 上下文）

```bash
GET /workflows/runs/{run_id}/trace
```

响应：

```json
{
  "workflow_run_id": "run-...",
  "trace_id": "abcd1234",
  "trigger_id": "trigger-daily-hotspots",
  "domain": "科技",
  "platform": "douyin",
  "status": "completed",
  "stages": [...]
}
```

## 测试覆盖

测试文件：`tests/test_trigger_integration.py`

覆盖场景：

1. **WorkflowRunService**
   - 创建 run 时携带 trigger_id
   - 创建 run 时不携带 trigger_id（向后兼容）
   - 按 trigger_id 查询 runs

2. **WorkflowExecutionEngine**
   - 执行时透传 trigger_id
   - 执行时不传 trigger_id（向后兼容）

3. **TriggerScanner**
   - Cooldown 期间不重复触发
   - 有 active run 时不重复触发
   - 正常触发流程

4. **TriggerService**
   - CRUD 操作

5. **Alembic Migration**
   - 迁移文件结构验证

## 部署步骤

1. **执行迁移**
   ```bash
   alembic upgrade 20260603_add_trigger_id
   ```

2. **启动调度器**
   ```python
   from src.departments.CIO.services.scheduler import TriggerScanner
   
   scanner = TriggerScanner(
       workflow_engine=engine,
       cooldown_seconds=60,
       check_interval_seconds=30
   )
   await scanner.start()
   ```

3. **验证**
   - 创建 trigger
   - 等待调度或手动触发
   - 检查 `GET /workflows/runs/{id}/trace` 返回包含 `trigger_id`

## 回滚

```bash
alembic downgrade <previous_rev>
```

代码回滚前确保：
- 没有写入依赖 `trigger_id` 的新代码路径
- TriggerScanner 已停止

## 性能预期

- **查询性能**：`GET /workflows/runs?trigger_id=xxx` 在 10k 数据量下 < 100ms
- **调度精度**：取决于 `check_interval_seconds`（默认 30s），非精确 cron
- **内存占用**：TriggerScanner 保持 trigger 表在内存中的最小缓存

## 后续建议（P1）

1. **精确调度**：使用 APScheduler 的 CronTrigger 替代轮询
2. **分布式支持**：使用 Redis 作为 APScheduler 的 job store
3. **事件驱动**：将 TriggerScanner 改为监听 PostgreSQL NOTIFY
4. **监控告警**：增加 trigger 失败次数统计和告警
