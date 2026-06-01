# 优化目标 10：配置与依赖管理集中化（重构版）

## 一、问题诊断（基于讨论深化）

### 1.1 当前现状

```
config.yaml                          # 结构化配置（良好）
app/CEO/core/config/__init__.py      # Pydantic Settings（良好）
├── 但：所有配置在一个大 Settings 类中
├── 但：环境变量与代码耦合
└── 但：无统一验证机制
```

### 1.2 核心问题

| 问题 | 表现 | 影响 |
|------|------|------|
| **配置分散** | `config.yaml` 和 `Settings` 类双轨并存 | 维护困难，容易不一致 |
| **环境变量耦合** | `Settings` 类直接读取环境变量 | 无法动态更新，测试困难 |
| **缺乏部门隔离** | 所有配置在一个大 `Settings` 类中 | 违反 CxO 架构，职责不清 |
| **无配置验证** | 仅基础类型校验，无业务规则验证 | 错误配置导致运行时故障 |
| **无热更新** | 配置加载后不可变 | 修改需重启服务 |
| **Agent vs Skill 混淆** | 配置读取逻辑散落在各处 | 无法复用，难以测试 |

---

## 二、重构方案：四层架构

基于讨论结论，采用 **"Skill 原子化 + Agent 协调化 + 联邦治理"** 模式：

```
┌─────────────────────────────────────────┐
│  CEO/services/config_governance/        │
│  - 治理策略（谁可以改什么）              │
│  - 部门拓扑（配置域划分）                │
│  - 全局常量（APP_NAME, VERSION）         │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  CIO/services/config_platform/          │
│                                         │
│  Skills（原子操作，无状态）：             │
│  ├── ConfigReadSkill      读取文件      │
│  ├── ConfigValidateSkill  验证数据      │
│  └── ConfigTransformSkill 转换模型      │
│                                         │
│  Agents（协调者，有状态）：               │
│  ├── ConfigManager        缓存管理      │
│  └── ConfigDiscovery      自动发现      │
└─────────────────────────────────────────┘
                    │
        ┌─────────┼─────────┬────────────┐
        ▼         ▼         ▼            ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │CFO/    │ │COO/    │ │CQO/    │ │CTO/    │
   │config/ │ │config/ │ │config/ │ │config/ │
   │- agent │ │- agent │ │- agent │ │- agent │
   │- schema│ │- schema│ │- schema│ │- schema│
   └────────┘ └────────┘ └────────┘ └────────┘
```

---

## 三、详细设计

### 3.1 CIO 配置平台（基础设施层）

#### Skills（原子操作）

```python
# CIO/skills/config_read/__init__.py
class ConfigReadSkill(BaseSkill):
    """配置读取 Skill - 无状态、原子操作"""
    
    skill_name = "cio.config.read"
    description = "Read configuration from file system"
    
    def execute(self, input_data: dict) -> dict:
        path = Path(input_data["path"])
        format_type = input_data.get("format", "yaml")
        
        with open(path, 'r', encoding='utf-8') as f:
            if format_type == "yaml":
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        return {"data": data, "path": str(path)}


# CIO/skills/config_validate/__init__.py
class ConfigValidateSkill(BaseSkill):
    """配置验证 Skill - 无状态、原子操作"""
    
    skill_name = "cio.config.validate"
    description = "Validate configuration against schema"
    
    def execute(self, input_data: dict) -> dict:
        data = input_data["data"]
        schema_type = input_data["schema_type"]
        
        validator = self._get_validator(schema_type)
        errors = validator.validate(data)
        
        return {"valid": len(errors) == 0, "errors": errors}


# CIO/skills/config_transform/__init__.py
class ConfigTransformSkill(BaseSkill):
    """配置转换 Skill - 无状态、原子操作"""
    
    skill_name = "cio.config.transform"
    description = "Transform raw config to typed model"
    
    def execute(self, input_data: dict) -> dict:
        data = input_data["data"]
        model_class = input_data["model_class"]
        
        model = self._import_model(model_class)
        instance = model(**data)
        
        return {"instance": instance}
```

#### Agents（协调者）

```python
# CIO/services/config_platform/manager.py
class ConfigManager:
    """
    配置管理 Agent
    - 有状态：维护配置缓存
    - 协调：组合多个 Skill 完成配置加载
    """
    
    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._read_skill = ConfigReadSkill()
        self._validate_skill = ConfigValidateSkill()
        self._transform_skill = ConfigTransformSkill()
    
    async def load_config(self, path: Path, schema_type: str, model_class: str) -> T:
        """加载配置 - 协调多个 Skill"""
        cache_key = f"{path}:{schema_type}:{model_class}"
        
        # 1. 检查缓存（Agent 决策）
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 2. 读取文件（调用 Skill）
        read_result = self._read_skill.execute({"path": str(path)})
        
        # 3. 验证数据（调用 Skill）
        validate_result = self._validate_skill.execute({
            "data": read_result["data"],
            "schema_type": schema_type
        })
        
        if not validate_result["valid"]:
            raise ConfigValidationError(validate_result["errors"])
        
        # 4. 转换模型（调用 Skill）
        transform_result = self._transform_skill.execute({
            "data": read_result["data"],
            "model_class": model_class
        })
        
        config = transform_result["instance"]
        
        # 5. 更新缓存（Agent 决策）
        self._cache[cache_key] = config
        
        return config
    
    def invalidate_cache(self, domain: str = None):
        """使缓存失效"""
        if domain:
            self._cache.pop(domain, None)
        else:
            self._cache.clear()


# CIO/services/config_platform/discovery.py
class ConfigDiscovery:
    """自动发现配置域"""
    
    BASE_PATH = Path("config")
    
    @classmethod
    def discover(cls) -> dict[str, Path]:
        """发现所有配置域"""
        domains = {}
        
        # 1. 发现部门配置
        dept_dir = cls.BASE_PATH / "departments"
        for dept_dir in dept_dir.iterdir():
            if dept_dir.is_dir():
                dept_name = dept_dir.name
                for config_file in dept_dir.glob("*.yaml"):
                    domain_name = f"{dept_name.lower()}_{config_file.stem}"
                    domains[domain_name] = config_file
        
        # 2. 发现基础设施配置
        infra_dir = cls.BASE_PATH / "infrastructure"
        for config_file in infra_dir.glob("*.yaml"):
            domain_name = f"cio_{config_file.stem}"
            domains[domain_name] = config_file
        
        # 3. 发现治理配置
        gov_dir = cls.BASE_PATH / "governance"
        for config_file in gov_dir.glob("*.yaml"):
            domain_name = f"ceo_{config_file.stem}"
            domains[domain_name] = config_file
        
        return domains
```

### 3.2 各部门配置定义（业务层）

```python
# CFO/config/schema.py
class FinanceConfig(BaseModel):
    """财务部门配置 Schema"""
    
    daily_budget: Decimal = Field(default=1000.0, gt=0)
    warning_threshold: float = Field(default=0.8, ge=0, le=1)
    alert_threshold: float = Field(default=1.0, ge=0)
    critical_threshold: float = Field(default=1.2, ge=0)
    api_pricing: dict[str, dict[str, Decimal]] = Field(default_factory=dict)
    default_provider: str = "deepseek"
    provider_mix: dict[str, float] = Field(default_factory=lambda: {
        "deepseek": 0.7,
        "glm": 0.3
    })


# CFO/config/agent.py
class CFOConfigAgent:
    """
    CFO 配置 Agent
    - 协调 CFO 相关的配置加载
    - 维护 CFO 配置缓存
    - 处理 CFO 特定的业务逻辑
    """
    
    def __init__(self, manager: ConfigManager):
        self.manager = manager
        self.domain = "finance"
        self.config_path = Path("config/departments/CFO/finance.yaml")
    
    async def load(self) -> FinanceConfig:
        """加载 CFO 配置"""
        return await self.manager.load_config(
            path=self.config_path,
            schema_type="finance",
            model_class="departments.CFO.config.schema.FinanceConfig"
        )
    
    async def update_budget(self, new_budget: Decimal, operator: str):
        """更新预算 - Agent 协调完整流程"""
        # 1. 加载当前配置
        config = await self.load()
        
        # 2. 业务规则验证（Agent 决策）
        if new_budget < 0:
            raise ValueError("Budget cannot be negative")
        
        if new_budget > 5000 and operator != "CFO":
            raise PermissionError("Large budget changes require CFO approval")
        
        # 3. 更新配置（调用 Skill）
        # ... 写入逻辑
        
        # 4. 使缓存失效（Agent 决策）
        self.manager.invalidate_cache(self.domain)


# COO/config/schema.py
class ProductionConfig(BaseModel):
    """生产部门配置 Schema"""
    
    default_resolution: str = "1080p"
    default_fps: int = 30
    max_video_duration: int = 300
    ffmpeg_preset: str = "medium"
    audio_bitrate: str = "192k"
    video_bitrate: str = "5000k"
    storage_backend: str = "local"
    max_file_size: int = 500 * 1024 * 1024


# COO/config/agent.py
class COOConfigAgent:
    """COO 配置 Agent"""
    
    def __init__(self, manager: ConfigManager):
        self.manager = manager
        self.domain = "production"
        self.config_path = Path("config/departments/COO/production.yaml")
    
    async def load(self) -> ProductionConfig:
        """加载 COO 配置"""
        return await self.manager.load_config(
            path=self.config_path,
            schema_type="production",
            model_class="departments.COO.config.schema.ProductionConfig"
        )
```

### 3.3 CEO 治理策略（控制层）

```python
# CEO/services/config_governance/policy.py
class ConfigGovernancePolicy:
    """CEO 配置治理策略"""
    
    def __init__(self):
        self._permissions = {
            "cfo_finance": ["CFO", "CEO"],
            "coo_production": ["COO", "CTO", "CEO"],
            "cqo_quality": ["CQO", "CEO"],
            "cio_infrastructure": ["CIO", "CEO"],
            "ceo_governance": ["CEO"],
        }
        
        self._dynamic_keys = {
            "cfo_finance.daily_budget",
            "cfo_finance.warning_threshold",
            "cqo_quality.min_video_quality_score",
            "coo_production.default_resolution",
        }
    
    def can_modify(self, domain: str, key: str, operator: str) -> bool:
        """检查是否有权限修改"""
        allowed = self._permissions.get(domain, [])
        return operator in allowed or operator == "CEO"
    
    def is_dynamic(self, key: str) -> bool:
        """检查是否支持热更新"""
        return key in self._dynamic_keys
```

### 3.4 配置目录结构

```
config/
├── departments/              # 部门业务配置（高变更频率）
│   ├── CFO/
│   │   ├── finance.yaml      # 预算、阈值
│   │   └── pricing.yaml      # API定价
│   ├── COO/
│   │   ├── production.yaml   # 渲染、合成
│   │   └── storage.yaml      # 存储配置
│   ├── CQO/
│   │   ├── quality.yaml      # 质检阈值
│   │   └── platform.yaml     # 平台规则
│   ├── CMO/
│   │   └── promotion.yaml    # 推广配置
│   └── CHO/
│       └── agent.yaml        # 代理配置
│
├── infrastructure/           # CIO基础设施（低变更频率）
│   ├── database.yaml
│   ├── redis.yaml
│   ├── api_keys.yaml
│   └── storage_backends.yaml
│
└── governance/               # CEO治理配置（中变更频率）
    ├── departments.yaml      # 部门拓扑
    ├── workflow.yaml         # 工作流编排
    └── permissions.yaml      # 权限策略
```

---

## 四、关键改进点

| 改进项 | 原方案 | 新方案 |
|--------|--------|--------|
| **配置位置** | 单一 `Settings` 类 | 分布式 `departments/`、`infrastructure/`、`governance/` |
| **读取逻辑** | 散落在各处 | **Skill 原子化**：`ConfigReadSkill`、`ConfigValidateSkill`、`ConfigTransformSkill` |
| **协调逻辑** | 无 | **Agent 协调化**：`ConfigManager` 组合 Skill |
| **验证机制** | Pydantic 基础校验 | `ConfigValidateSkill` + 各部门 Schema |
| **权限控制** | 无 | CEO `ConfigGovernancePolicy` |
| **热更新** | 不支持 | `ConfigManager.invalidate_cache()` |
| **自动发现** | 手动注册 | `ConfigDiscovery` 自动扫描目录 |
| **环境变量** | 直接读取 | 通过 `ConfigReadSkill` 统一加载 |

---

## 五、实施路径

### 第一阶段：基础设施（1 周）

1. 创建 `CIO/services/config_platform/`
2. 实现 `ConfigReadSkill`、`ConfigValidateSkill`、`ConfigTransformSkill`
3. 实现 `ConfigManager`、`ConfigDiscovery`
4. 保留现有 `Settings` 类作为兼容层

### 第二阶段：目录重构（1 周）

1. 创建 `config/departments/`、`config/infrastructure/`、`config/governance/`
2. 将现有配置按部门拆分
3. 命名规范：`{部门}_{功能}.yaml`

### 第三阶段：部门迁移（2 周）

1. CFO 提取 `FinanceConfig` + `CFOConfigAgent`
2. COO 提取 `ProductionConfig` + `COOConfigAgent`
3. CQO 提取 `QualityConfig` + `CQOConfigAgent`
4. 其他部门按需提取

### 第四阶段：治理完善（1 周）

1. CEO 实现 `ConfigGovernancePolicy`
2. 配置热更新机制
3. 审计日志集成

### 第五阶段：清理遗留（1 周）

1. 移除旧 `Settings` 类
2. 统一使用新配置系统
3. 更新文档

---

## 六、与原方案对比

| 维度 | 原方案（P3 简单集中化） | 新方案（Skill + Agent 联邦制） |
|------|------------------------|------------------------------|
| **架构契合度** | ❌ 违反 CxO 分权 | ✅ 符合联邦治理 |
| **部门自治** | ❌ CIO 全权管理 | ✅ 各部门自主定义 Schema |
| **Skill 复用** | ❌ 无 | ✅ ConfigReadSkill 等可复用 |
| **测试性** | ❌ 难以单元测试 | ✅ Skill 原子操作可独立测试 |
| **扩展性** | ❌ 修改中心类 | ✅ 新增部门只需新增 Schema |
| **长期可维护性** | 中 | 高 |

---

## 七、核心设计原则

1. **Skill = 原子操作**：读取、验证、转换都是无状态的 Skill
2. **Agent = 协调者**：ConfigManager 组合 Skill，管理缓存
3. **联邦治理**：CIO 提供平台，各部门自治，CEO 定规则
4. **目录即元数据**：`config/departments/CFO/` 一看就知道归属
5. **自动发现**：新增配置文件自动识别，无需注册代码

---

*基于讨论结论重构，强调 Skill/Agent 分层、联邦治理、自动发现*
