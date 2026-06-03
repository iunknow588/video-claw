# 龙虾流程架构演进路线图（P0-P3）

## 当前状态（P0 已完成）

P0 已实现：
- ✅ `trigger_id` 透传 + 复合索引
- ✅ `TriggerScanner` 基础调度（轮询 + 双重去重）
- ✅ Trigger CRUD API
- ✅ 向后兼容的代码改造
- ✅ 基础测试覆盖

---

## P1 — 生产级调度与观测（2 周）

### 目标
将 P0 的"最小可行调度"升级为生产级调度系统，增加精确触发、分布式支持和基础监控。

### 任务清单

#### Task P1-A：精确 Cron 调度（2 人日）
**问题**：P0 使用轮询（30s 间隔），调度精度低，资源浪费。

**方案**：
```python
# 改造 TriggerScanner 使用 APScheduler CronTrigger
from apscheduler.triggers.cron import CronTrigger

class PreciseTriggerScanner:
    def __init__(self, workflow_engine, job_store=None):
        self.scheduler = AsyncIOScheduler(jobstores=job_store)
        
    async def add_trigger_job(self, trigger: WorkflowTrigger):
        """为每个 trigger 创建独立的 cron job"""
        self.scheduler.add_job(
            func=self._execute_workflow,
            trigger=CronTrigger.from_crontab(trigger.cron),
            id=f"trigger_{trigger.id}",
            replace_existing=True,
            args=[trigger]
        )
```

**验收**：
- Trigger 按 cron 表达式精确触发（误差 < 1s）
- 支持秒级 cron（如 `*/5 * * * * *`）

#### Task P1-B：分布式 Job Store（2 人日）
**问题**：单进程调度器无法水平扩展，存在单点故障。

**方案**：
```python
# 使用 Redis 作为 APScheduler 的 job store
from apscheduler.jobstores.redis import RedisJobStore

jobstores = {
    'default': RedisJobStore(
        host='redis',
        port=6379,
        db=0,
        jobs_key='apscheduler.jobs',
        run_times_key='apscheduler.run_times'
    )
}

scheduler = AsyncIOScheduler(jobstores=jobstores)
```

**验收**：
- 多实例部署时，同一 trigger 只在一个实例上执行
- 实例重启后，trigger 配置不丢失

#### Task P1-C：执行锁与并发控制（1 人日）
**问题**：P0 的去重依赖数据库查询，存在竞态窗口。

**方案**：
```python
import redis.asyncio as redis

class DistributedLock:
    """Redis 分布式锁，防止同一 trigger 多实例并发执行"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def acquire(self, trigger_id: str, ttl_seconds: int = 300) -> bool:
        """获取锁，返回是否成功"""
        key = f"trigger_lock:{trigger_id}"
        # NX = only if Not eXists
        result = await self.redis.set(key, "1", nx=True, ex=ttl_seconds)
        return result is not None
        
    async def release(self, trigger_id: str):
        """释放锁"""
        await self.redis.delete(f"trigger_lock:{trigger_id}")
```

**验收**：
- 同一 trigger 在 5 分钟内只能有一个运行实例
- 锁自动过期，防止死锁

#### Task P1-D：基础监控与告警（2 人日）
**问题**：无 trigger 执行状态的可观测性。

**方案**：
```python
# 在 TriggerScanner 中增加指标收集
from prometheus_client import Counter, Histogram, Gauge

trigger_fired_total = Counter('trigger_fired_total', 'Total triggers fired', ['trigger_id', 'status'])
trigger_execution_duration = Histogram('trigger_execution_duration_seconds', 'Trigger execution time')
active_runs_gauge = Gauge('active_workflow_runs', 'Currently running workflows', ['trigger_id'])

class MonitoredTriggerScanner(TriggerScanner):
    async def _execute_workflow(self, trigger):
        with trigger_execution_duration.time():
            try:
                result = await super()._execute_workflow(trigger)
                trigger_fired_total.labels(trigger_id=trigger.id, status='success').inc()
            except Exception as e:
                trigger_fired_total.labels(trigger_id=trigger.id, status='failed').inc()
                # 告警：连续失败 3 次触发告警
                await self._check_alert(trigger)
                raise
```

**验收**：
- Prometheus 指标：`trigger_fired_total`、`trigger_execution_duration`、`active_runs`
- 告警规则：连续 3 次失败触发钉钉/飞书告警

#### Task P1-E：灰度与 A/B 测试支持（1 人日）
**问题**：新 trigger 无法小流量验证。

**方案**：
```python
class WorkflowTrigger(Base):
    # 新增字段
    canary_percentage = Column(Float, default=100.0)  # 灰度百分比
    canary_namespace = Column(String(64), nullable=True)  # 灰度隔离空间
    
# 调度时根据灰度比例决定是否触发
async def should_fire_trigger(trigger: WorkflowTrigger) -> bool:
    if trigger.canary_percentage >= 100:
        return True
    # 使用 trigger_id + 当前小时作为随机种子，保证同一小时内结果一致
    import hashlib
    seed = f"{trigger.id}:{datetime.utcnow().hour}"
    hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return (hash_val % 100) < trigger.canary_percentage
```

**验收**：
- 可设置 trigger 只触发 10% 的时间
- 灰度运行与正式运行数据隔离

---

## P2 — 事件驱动与插件化（3-4 周）

### 目标
从"轮询/定时"模型演进为"事件驱动"模型，支持外部系统触发和插件化扩展。

### 任务清单

#### Task P2-A：事件总线接入（3 人日）
**问题**：当前只有定时触发，无法响应外部事件（如热点爆发、用户操作）。

**方案**：
```python
from enum import Enum

class WorkflowEventType(Enum):
    SCHEDULED = "scheduled"      # 定时触发
    WEBHOOK = "webhook"          # 外部 webhook
    MANUAL = "manual"            # 手动触发
    HOTSPOT_DETECTED = "hotspot" # 热点发现
    USER_ACTION = "user_action"  # 用户行为

class WorkflowEvent:
    def __init__(self, event_type: WorkflowEventType, payload: dict, source: str):
        self.event_type = event_type
        self.payload = payload
        self.source = source
        self.timestamp = datetime.utcnow()

class EventDrivenEngine:
    """支持多种触发源的工作流引擎"""
    
    async def handle_event(self, event: WorkflowEvent):
        """处理外部事件，查找匹配的 trigger 并执行"""
        # 查找监听该事件类型的 trigger
        triggers = await self.find_triggers_by_event(event.event_type)
        
        for trigger in triggers:
            # 合并事件 payload 与 trigger 默认参数
            merged_input = {**trigger.input_params, **event.payload}
            
            await self.workflow_engine.run_domain_workflow(
                domain=trigger.domain,
                platform=trigger.platform,
                input_params=merged_input,
                trigger_id=trigger.id,
                event_context={
                    'event_type': event.event_type.value,
                    'event_source': event.source,
                    'event_timestamp': event.timestamp.isoformat()
                }
            )
```

**验收**：
- 支持通过 Webhook 接收外部事件并触发工作流
- 事件 payload 可与 trigger 默认参数合并

#### Task P2-B：插件化 Trigger 源（3 人日）
**问题**：新增触发源需要修改核心代码。

**方案**：
```python
from abc import ABC, abstractmethod
from typing import Type

class TriggerSource(ABC):
    """触发源插件基类"""
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        pass
        
    @abstractmethod
    async def start(self, callback: Callable[[WorkflowEvent], Awaitable[None]]):
        """启动监听，当事件发生时调用 callback"""
        pass
        
    @abstractmethod
    async def stop(self):
        """停止监听"""
        pass

class WebhookTriggerSource(TriggerSource):
    """Webhook 触发源"""
    source_type = "webhook"
    
    async def start(self, callback):
        # 启动 HTTP server 接收 webhook
        from aiohttp import web
        app = web.Application()
        app.router.add_post('/webhook/{trigger_id}', self._handle_webhook)
        self._callback = callback
        
    async def _handle_webhook(self, request):
        trigger_id = request.match_info['trigger_id']
        payload = await request.json()
        
        event = WorkflowEvent(
            event_type=WorkflowEventType.WEBHOOK,
            payload=payload,
            source=f"webhook:{trigger_id}"
        )
        await self._callback(event)
        return web.Response(status=200)

class TriggerSourceRegistry:
    """触发源插件注册表"""
    _sources: Dict[str, Type[TriggerSource]] = {}
    
    @classmethod
    def register(cls, source_class: Type[TriggerSource]):
        cls._sources[source_class.source_type] = source_class
        
    @classmethod
    def create(cls, source_type: str) -> TriggerSource:
        return cls._sources[source_type]()

# 注册插件
TriggerSourceRegistry.register(WebhookTriggerSource)
TriggerSourceRegistry.register(KafkaTriggerSource)  # 未来扩展
TriggerSourceRegistry.register(RabbitMQTriggerSource)  # 未来扩展
```

**验收**：
- 新增触发源只需实现 `TriggerSource` 接口并注册
- 核心代码无需修改即可支持新触发源

#### Task P2-C：工作流编排可视化（2 人日）
**问题**：无法直观查看工作流执行状态和依赖关系。

**方案**：
```python
class WorkflowVisualizer:
    """生成工作流执行 DAG 图"""
    
    def generate_trace_dag(self, run_id: str) -> dict:
        """生成 trace 的有向无环图"""
        run = await self.run_service.get_run_by_id(run_id)
        
        nodes = []
        edges = []
        
        stages = ['CFO', 'Research', 'Analysis', 'Planning', 'Production', 'QA', 'Publish']
        for i, stage in enumerate(stages):
            nodes.append({
                'id': stage,
                'status': self._get_stage_status(run, stage),
                'duration': self._get_stage_duration(run, stage)
            })
            if i > 0:
                edges.append({'from': stages[i-1], 'to': stage})
                
        # QA 重做循环的回流边
        if self._has_qa_rework(run):
            edges.append({'from': 'QA', 'to': 'Planning', 'label': 'rework'})
            
        return {'nodes': nodes, 'edges': edges}
```

**验收**：
- API 返回工作流执行的 DAG JSON
- 前端可渲染为可视化流程图（支持 Mermaid/Graphviz）

#### Task P2-D：动态参数与上下文传递（2 人日）
**问题**：Stage 间参数传递硬编码，不够灵活。

**方案**：
```python
class ContextManager:
    """工作流执行上下文，支持动态参数传递"""
    
    def __init__(self):
        self._context = {}
        
    def set(self, key: str, value: Any, scope: str = "global"):
        """设置上下文变量
        scope: global | stage | run
        """
        self._context[f"{scope}:{key}"] = value
        
    def get(self, key: str, scope: str = "global", default=None):
        """获取上下文变量，支持变量引用"""
        value = self._context.get(f"{scope}:{key}", default)
        
        # 支持模板语法："{{stage:Planning.plan_id}}"
        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            ref = value[2:-2].strip()
            return self._resolve_ref(ref)
            
        return value
        
    def _resolve_ref(self, ref: str):
        """解析变量引用"""
        scope, key = ref.split(".", 1)
        return self._context.get(f"{scope}:{key}")

# 在引擎中使用
async def run_domain_workflow(self, ...):
    ctx = ContextManager()
    ctx.set("trigger_id", trigger_id)
    ctx.set("domain", domain)
    
    # CFO 阶段设置预算
    cfo_result = await self._run_stage('lead.cfo', context=ctx)
    ctx.set("budget", cfo_result["budget"], scope="CFO")
    
    # Research 阶段引用预算
    research_result = await self._run_stage(
        'lead.research',
        context=ctx,
        budget=ctx.get("budget", scope="CFO")  # 或直接使用模板
    )
```

**验收**：
- Stage 间可通过上下文传递任意参数
- 支持模板语法引用其他 stage 的输出

---

## P3 — 智能化与自治（滚动迭代）

### 目标
引入 AI 驱动的决策，实现工作流的自我优化和故障自愈。

### 任务清单（初步）

#### Task P3-A：智能重试策略
**问题**：当前 QA 重做是固定次数，未考虑失败原因。

**方案**：
```python
class IntelligentRetryPolicy:
    """基于失败原因智能决定重试策略"""
    
    async def determine_retry(self, failure_context: dict) -> RetryDecision:
        # 使用 LLM 分析失败原因
        analysis = await self.llm.analyze_failure(failure_context)
        
        if analysis["type"] == "transient":
            # 临时错误（如网络），立即重试
            return RetryDecision(retry_now=True, delay=0)
            
        elif analysis["type"] == "content_quality":
            # 内容质量问题，调整参数后重试
            return RetryDecision(
                retry_now=True,
                delay=0,
                param_adjustments={"temperature": 0.8, "max_tokens": 2000}
            )
            
        elif analysis["type"] == "fundamental":
            # 根本性错误（如策略冲突），终止并告警
            return RetryDecision(retry_now=False, alert_severity="critical")
```

#### Task P3-B：预测性调度
**问题**：定时触发无法适应流量波动。

**方案**：
```python
class PredictiveScheduler:
    """基于历史数据预测最佳触发时间"""
    
    async def optimize_schedule(self, trigger_id: str):
        # 分析历史执行数据
        history = await self.get_execution_history(trigger_id, days=30)
        
        # 使用简单时序模型预测最佳时间
        optimal_time = self._predict_optimal_time(history)
        
        # 动态调整 cron 表达式
        await self.update_trigger_cron(trigger_id, optimal_time)
```

#### Task P3-C：自治故障恢复
**问题**：工作流失败后需要人工介入。

**方案**：
```python
class AutonomousRecovery:
    """自治故障检测与恢复"""
    
    async def handle_failure(self, run_id: str, failure: dict):
        # 1. 自动诊断
        diagnosis = await self.diagnose_failure(failure)
        
        # 2. 尝试自动修复
        if diagnosis["recoverable"]:
            recovery_action = await self.plan_recovery(diagnosis)
            await self.execute_recovery(run_id, recovery_action)
            
        # 3. 无法自动修复时，生成详细报告并升级
        else:
            await self.escalate_to_human(run_id, diagnosis)
```

---

## 实施优先级矩阵

| 任务 | 业务价值 | 技术难度 | 风险 | 建议优先级 |
|------|---------|---------|------|-----------|
| P1-A 精确 Cron | 高 | 低 | 低 | P1 首项 |
| P1-B 分布式 Job Store | 高 | 中 | 中 | P1 第二 |
| P1-C 分布式锁 | 高 | 低 | 低 | P1 并行 |
| P1-D 监控告警 | 高 | 低 | 低 | P1 并行 |
| P1-E 灰度支持 | 中 | 低 | 低 | P1 末尾 |
| P2-A 事件总线 | 高 | 中 | 中 | P2 首项 |
| P2-B 插件化 | 高 | 中 | 中 | P2 第二 |
| P2-C 可视化 | 中 | 中 | 低 | P2 可选 |
| P2-D 动态参数 | 中 | 中 | 低 | P2 并行 |
| P3-A 智能重试 | 高 | 高 | 高 | 长期 |
| P3-B 预测调度 | 中 | 高 | 高 | 长期 |
| P3-C 自治恢复 | 高 | 高 | 高 | 长期 |

---

## 技术债务跟踪

| 债务项 | 产生阶段 | 影响 | 偿还计划 |
|--------|---------|------|---------|
| P0 轮询调度精度低 | P0 | 资源浪费 | P1-A |
| P0 单点调度器 | P0 | 无法扩展 | P1-B |
| P0 数据库去重竞态 | P0 | 可能重复触发 | P1-C |
| P0 缺少监控 | P0 | 故障发现慢 | P1-D |
| 硬编码 stage 顺序 | 原始架构 | 扩展性差 | P2-D |
| 缺少事件驱动 | 原始架构 | 响应延迟 | P2-A |

---

## 里程碑与验收

| 阶段 | 时间 | 验收标准 |
|------|------|---------|
| P0 | 已完成 | trigger_id 透传 + 基础调度 + 测试覆盖 |
| P1 | +2 周 | 精确 cron + 分布式 + 监控 + 灰度 |
| P2 | +3-4 周 | 事件驱动 + 插件化 + 可视化 + 动态参数 |
| P3 | 滚动 | 智能重试 + 预测调度 + 自治恢复 |

---

## 附录：参考架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        P3 自治层                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ 智能重试策略 │  │ 预测性调度   │  │ 自治故障恢复         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        P2 事件驱动层                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ 事件总线     │  │ 插件化 Trigger│  │ 可视化编排          │ │
│  │ (Webhook/   │  │ 源 (Kafka/   │  │ (DAG 渲染)          │ │
│  │  Kafka/     │  │ RabbitMQ)    │  │                     │ │
│  │  RabbitMQ)  │  │              │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        P1 生产级调度层                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ 精确 Cron    │  │ 分布式 Job   │  │ 监控告警 + 灰度     │ │
│  │ 调度         │  │ Store (Redis)│  │ 支持               │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        P0 基础层（已完成）                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ trigger_id  │  │ TriggerScanner│  │ Trigger CRUD API   │ │
│  │ 透传 + 索引  │  │ (轮询 + 去重) │  │ + Trace 查询        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```
