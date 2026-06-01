# 代码分层优化方案

## 当前问题诊断

### 1. CEO.services.orchestration 过度膨胀
- WorkflowExecutionEngine.run_domain_workflow() 包含 ~400 行硬编码流程
- 直接调用 40+ 个 skill，形成"上帝类"
- 职责：编排 + 业务逻辑 + 错误处理 + 事件发射，全部混在一起

### 2. CEO.skills.executive 越权代理
- 包含 9 个子目录（analysis_center, finance_office 等）
- 实际只是其他部门 skill 的"重导出"，无自身逻辑
- 违反"skills 最小可复用"原则

### 3. services vs skills 边界模糊
- CEO.services.workflow_steps 记录步骤日志 → 应属 CIO
- CEO.services.leader_reports 生成报告 → 应属各 leader 自身
- CEO.services.chat 处理对话 → 应属 CMO

### 4. 跨部门 skill 直接调用
- engine.py 直接实例化所有部门的 skill
- 形成网状依赖，难以单元测试

## 优化方案

### Phase 1: 拆解 CEO.services.orchestration

**目标**: 将 monolithic engine 拆分为 domain-specific services

`
CEO/services/orchestration/
  ├── __init__.py          # 仅导出 facade
  ├── facade.py            # 向后兼容的薄封装
  └── domains/             # 各业务域编排服务
      ├── finance_gate.py      # CFO 财务闸门编排
      ├── research_pipeline.py # CSO 调研流水线
      ├── analysis_pipeline.py # CCO 分析流水线
      ├── rd_pipeline.py       # CTO 策划流水线
      ├── production_pipeline.py # COO 制作流水线
      ├── qa_pipeline.py       # CQO 质检流水线
      └── publish_pipeline.py  # CAO 发布流水线
`

**每个 pipeline 职责**:
- 接收上游输出，调用本域 skills
- 返回标准化 bundle
- 不直接操作其他域

### Phase 2: 删除 CEO.skills.executive

**操作**:
1. 删除 CEO/skills/executive/ 目录
2. 更新所有引用到实际 skill 位置
3. 如需要聚合入口，在 CEO/services/ 下创建 domain service

### Phase 3: 迁移越界服务

| 当前位置 | 目标位置 | 理由 |
|---------|---------|------|
| CEO/services/workflow_steps | CIO/services/workflow_log | 步骤日志属于信息持久化 |
| CEO/services/workflow_runs | CIO/services/workflow_run | 工作流运行记录 |
| CEO/services/leader_reports | 各 leader 自身 | 报告生成是 leader 职责 |
| CEO/services/chat | CMO/services/chat | 对话交互属市场/用户 |

### Phase 4: 建立 Skill 调用契约

**当前问题**: engine 直接实例化 skill
**优化后**:
`python
# 通过 registry 解耦
skill = skill_registry.get("lead.cfo.estimate")
result = await skill.execute(input_bundle)
`

**好处**:
- 调用方不依赖具体类
- 便于 mock 测试
- 支持动态替换

### Phase 5: services 内部编排标准化

**每个部门的 services 结构**:
`
CXO/services/
  ├── __init__.py
  ├── use_cases/           # 用例编排（新增）
  │   ├── __init__.py
  │   └── xxx_pipeline.py  # 聚合多个 skill 的用例
  └── xxx/                 # 原有服务
      ├── __init__.py
      └── ...
`

**示例**: COO/services/use_cases/
`python
# video_production_use_case.py
class VideoProductionUseCase:
    async def execute(self, script, materials, config):
        subtitle = await self.subtitle_skill.compose(...)
        voiceover = await self.voiceover_skill.generate(...)
        video = await self.video_skill.process(...)
        return CompositionResult(subtitle, voiceover, video)
`

## 实施优先级

| 优先级 | 任务 | 影响 | 工作量 |
|--------|------|------|--------|
| P0 | 删除 executive skill | 清理技术债务 | 2h |
| P0 | 拆解 engine.py | 核心架构优化 | 1d |
| P1 | 迁移越界服务 | 职责清晰 | 4h |
| P1 | 建立 skill registry | 解耦依赖 | 4h |
| P2 | 标准化 use_cases | 长期规范 | 2d |

## 预期收益

1. **测试性**: 每个 pipeline 可独立单元测试
2. **可维护性**: 修改制作流程不影响调研流程
3. **可扩展性**: 新增业务域只需添加新 pipeline
4. **清晰度**: 新人可快速定位代码位置
