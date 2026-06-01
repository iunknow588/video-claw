# 配置目录重构提案

## 当前问题

配置文件命名不够直观，无法一眼看出对应部门：
- `finance.yaml` → 需要思考才知道是 CFO
- `production.yaml` → 需要思考才知道是 COO

## 重构方案

### 方案一：部门前缀（推荐）

```
config/
├── cfo_finance.yaml          # CFO - 财务预算
├── cfo_pricing.yaml          # CFO - API定价
├── coo_production.yaml       # COO - 生产渲染
├── coo_storage.yaml          # COO - 存储配置
├── cqo_quality.yaml          # CQO - 质检阈值
├── cqo_platform.yaml         # CQO - 平台规则
├── cio_infrastructure.yaml   # CIO - 基础设施
├── cio_security.yaml         # CIO - 安全凭证
├── ceo_governance.yaml       # CEO - 治理策略
├── ceo_workflow.yaml         # CEO - 工作流定义
├── cmo_promotion.yaml        # CMO - 推广配置
└── cho_agent.yaml            # CHO - 代理配置
```

**优点**：
- 一眼看出所属部门
- 文件排序自然按部门分组
- 支持一个部门多个配置文件

### 方案二：部门子目录

```
config/
├── CFO/
│   ├── finance.yaml
│   └── pricing.yaml
├── COO/
│   ├── production.yaml
│   └── storage.yaml
├── CQO/
│   ├── quality.yaml
│   └── platform.yaml
├── CIO/
│   ├── infrastructure.yaml
│   └── security.yaml
├── CEO/
│   ├── governance.yaml
│   └── workflow.yaml
├── CMO/
│   └── promotion.yaml
└── CHO/
    └── agent.yaml
```

**优点**：
- 物理隔离，权限控制更直观
- 部门配置文件数量可扩展
- 符合 CxO 目录结构一致性

**缺点**：
- 深度增加一级
- 需要更多路径操作

### 方案三：混合模式（最终推荐）

```
config/
├── departments/              # 部门业务配置
│   ├── CFO/
│   │   ├── finance.yaml
│   │   └── pricing.yaml
│   ├── COO/
│   │   ├── production.yaml
│   │   └── storage.yaml
│   ├── CQO/
│   │   ├── quality.yaml
│   │   └── platform.yaml
│   ├── CMO/
│   │   └── promotion.yaml
│   └── CHO/
│       └── agent.yaml
├── infrastructure/           # CIO 基础设施配置
│   ├── database.yaml
│   ├── redis.yaml
│   ├── api_keys.yaml
│   └── storage_backends.yaml
└── governance/               # CEO 治理配置
    ├── departments.yaml      # 部门拓扑定义
    ├── workflow.yaml         # 工作流编排
    └── permissions.yaml      # 权限策略
```

**设计理由**：

| 目录 | 管理部门 | 内容 | 变更频率 |
|------|----------|------|----------|
| `departments/` | 各部门自治 | 业务规则、阈值、参数 | 高 |
| `infrastructure/` | CIO | 数据库、缓存、API密钥 | 低 |
| `governance/` | CEO | 部门拓扑、工作流、权限 | 中 |

## 代码映射

```python
# 自动发现配置域
from pathlib import Path

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
                dept_name = dept_dir.name  # "CFO", "COO", etc.
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


# 使用示例
domains = ConfigDiscovery.discover()
# 结果：
# {
#     "cfo_finance": Path("config/departments/CFO/finance.yaml"),
#     "cfo_pricing": Path("config/departments/CFO/pricing.yaml"),
#     "coo_production": Path("config/departments/COO/production.yaml"),
#     "cio_database": Path("config/infrastructure/database.yaml"),
#     "ceo_workflow": Path("config/governance/workflow.yaml"),
#     ...
# }
```

## 配置加载示例

```python
# 统一加载入口
class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self._domains: dict[str, ConfigDomain] = {}
        self._discovery = ConfigDiscovery()
    
    async def initialize(self):
        """初始化：自动发现所有配置域"""
        discovered = self._discovery.discover()
        
        for domain_name, path in discovered.items():
            # 根据命名约定推断管理 Agent
            dept = domain_name.split('_')[0].upper()
            agent = self._create_agent(dept)
            
            domain = ConfigDomain(
                name=domain_name,
                path=path,
                agent=agent
            )
            
            await domain.load()
            self._domains[domain_name] = domain
    
    def _create_agent(self, dept: str) -> ConfigAgent:
        """根据部门创建对应 Agent"""
        agents = {
            "CFO": CFOConfigAgent(),
            "COO": COOConfigAgent(),
            "CQO": CQOConfigAgent(),
            "CIO": CIOConfigAgent(),
            "CEO": CEOConfigAgent(),
            "CMO": CMOConfigAgent(),
            "CHO": CHOConfigAgent(),
        }
        return agents.get(dept, DefaultConfigAgent())
    
    def get(self, domain: str, key: str = None):
        """获取配置"""
        if domain not in self._domains:
            raise KeyError(f"Unknown domain: {domain}")
        
        config = self._domains[domain].config
        if key:
            return getattr(config, key, None)
        return config


# 使用示例
manager = ConfigManager()
await manager.initialize()

# 获取 CFO 财务配置
budget = manager.get("cfo_finance", "daily_budget")

# 获取 COO 生产配置
backend = manager.get("coo_production", "storage_backend")

# 获取 CIO 数据库配置
db_url = manager.get("cio_database", "url")

# 获取 CEO 工作流配置
workflow = manager.get("ceo_workflow", "main_route")
```

## 权限映射

```python
# 根据目录结构自动推断权限
class ConfigGovernance:
    """配置治理"""
    
    DOMAIN_PERMISSIONS = {
        # 部门配置：对应部门 + CEO
        "cfo_*": ["CFO", "CEO"],
        "coo_*": ["COO", "CEO"],
        "cqo_*": ["CQO", "CEO"],
        "cmo_*": ["CMO", "CEO"],
        "cho_*": ["CHO", "CEO"],
        
        # 基础设施：CIO + CEO
        "cio_*": ["CIO", "CEO"],
        
        # 治理配置：CEO 专属
        "ceo_*": ["CEO"],
    }
    
    @classmethod
    def can_modify(cls, domain: str, operator: str) -> bool:
        """检查是否有权限修改"""
        for pattern, allowed in cls.DOMAIN_PERMISSIONS.items():
            if cls._match(domain, pattern):
                return operator in allowed
        return False
    
    @staticmethod
    def _match(domain: str, pattern: str) -> bool:
        """通配符匹配"""
        if pattern.endswith('*'):
            return domain.startswith(pattern[:-1])
        return domain == pattern
```

## 总结

| 方案 | 命名示例 | 优点 | 缺点 |
|------|----------|------|------|
| 方案一 | `cfo_finance.yaml` | 简洁、排序分组 | 文件增多后目录混乱 |
| 方案二 | `CFO/finance.yaml` | 物理隔离、权限直观 | 路径深度+1 |
| **方案三（推荐）** | `departments/CFO/finance.yaml` | **语义分层、扩展性强、权限清晰** | 稍复杂 |

**推荐方案三**，因为：
1. **语义清晰**：`departments/`、`infrastructure/`、`governance/` 一看就知道配置类型
2. **权限直观**：不同目录对应不同管理策略
3. **扩展性强**：新增部门或配置类型不影响现有结构
4. **自动化友好**：目录结构即元数据，支持自动发现
