# AI视频自动生产线 — 开发计划（完善版v2）

**版本：** v2.0  
**日期：** 2026年5月26日  
**编制依据：** 技术评审报告（修订版v3）  
**项目定位：** AI辅助内容创作工具（半自动模式）

---

## 一、需求分析（完善版）

### 1.1 项目背景与目标

#### 1.1.1 背景
短视频行业进入"AI辅助创作"时代，传统人工创作效率低、成本高。本项目旨在构建一套**半自动化的AI辅助内容创作系统**，在确保合规的前提下，将单条视频制作时间从4-6小时缩短至30-60分钟。

#### 1.1.2 目标
- **效率目标：** 日产5-10条精品视频（原方案50-100条不切实际）
- **成本目标：** 单条成本≤50元，月度总成本≤3万元
- **质量目标：** 平台通过率≥80%，完播率≥15%
- **合规目标：** 100%人工审核后发布，零封号风险

### 1.2 用户画像

| 用户角色 | 职责 | 核心诉求 | 使用频率 |
|----------|------|----------|----------|
| 内容运营 | 热点追踪、内容策划 | 快速发现热点，高效产出内容 | 每日 |
| 内容审核员 | 质量把控、合规审查 | 便捷审核工具，明确审核标准 | 每日 |
| 技术负责人 | 系统维护、故障处理 | 系统稳定，监控完善 | 按需 |
| 数据分析 | 效果追踪、策略优化 | 数据直观，报表自动化 | 每周 |

### 1.3 核心需求（完善版）

#### 1.3.1 功能性需求

| 需求编号 | 需求名称 | 优先级 | 用户故事 | 验收标准 |
|----------|----------|--------|----------|----------|
| R001 | 热点内容采集 | P0 | 作为内容运营，我希望系统自动监控各平台热门内容，以便快速发现创作灵感 | 支持抖音/小红书/B站；每日更新；可配置监控关键词 |
| R002 | AI内容分析 | P0 | 作为内容运营，我希望AI分析爆款内容的框架结构，以便参考创作 | 输出内容结构、情绪曲线、钩子设计；分析时间<30秒 |
| R003 | 脚本生成 | P0 | 作为内容运营，我希望基于爆款框架快速生成原创脚本，以便提高创作效率 | 生成时间<60秒；支持多种内容类型；人工可编辑 |
| R004 | 视频生成 | P0 | 作为内容运营，我希望将脚本自动转化为视频素材，以便减少剪辑时间 | 生成时间<5分钟；支持多种风格；异步回调 |
| R005 | 人工审核 | P0 | 作为审核员，我希望在关键节点审核内容，以便确保合规和质量 | 脚本+视频双重审核；审核界面直观；支持通过/驳回/修改 |
| R006 | 半自动发布 | P1 | 作为内容运营，我希望审核通过后快速发布到各平台，以便减少操作时间 | 支持抖音/小红书/B站；人工确认后发布；支持定时发布 |
| R007 | 数据监控 | P1 | 作为数据分析，我希望追踪已发布内容的效果数据，以便优化策略 | 播放量、点赞、评论、完播率；数据可视化；周报自动生成 |
| R008 | 成本控制 | P0 | 作为技术负责人，我希望实时监控API调用成本，以便控制预算 | 实时成本看板；超预算告警；成本日报 |
| R009 | 内容库管理 | P1 | 作为内容运营，我希望管理历史脚本和视频素材，以便复用和参考 | 支持标签、搜索、分类；支持版本管理 |
| R010 | 用户权限管理 | P2 | 作为技术负责人，我希望不同角色有不同权限，以便保障系统安全 | RBAC权限模型；操作日志记录 |

#### 1.3.2 非功能性需求（完善版）

| 需求编号 | 需求名称 | 指标 | 测试方法 |
|----------|----------|------|----------|
| NFR001 | 日产量 | 5-10条精品视频 | 统计每日审核通过并发布的视频数量 |
| NFR002 | 视频时长 | 5-15秒 | 视频元数据检查 |
| NFR003 | 成本控制 | 单条成本≤50元 | 成本报表统计 |
| NFR004 | 合规性 | 100%人工审核后发布 | 审核日志检查 |
| NFR005 | 系统可用性 | ≥99% | 监控工具统计 |
| NFR006 | API响应时间 | <3秒（分析/生成） | 压力测试 |
| NFR007 | 视频生成时间 | <10分钟 | 实际测试 |
| NFR008 | 数据安全性 | 敏感数据加密存储 | 安全审计 |
| NFR009 | 可扩展性 | 支持未来扩展新平台 | 架构评审 |
| NFR010 | 易用性 | 新用户30分钟上手 | 用户测试 |

### 1.4 业务流程

#### 1.4.1 核心业务流程

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 热点采集 │ → │ AI分析  │ → │ 脚本生成 │ → │ 人工审核 │ → │ 视频生成 │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                                  ↓
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 数据监控 │ ← │ 效果追踪 │ ← │ 内容发布 │ ← │ 人工确认 │ ← │ 视频审核 │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

#### 1.4.2 异常处理流程

| 异常场景 | 处理方式 | 责任人 |
|----------|----------|--------|
| API调用失败 | 自动重试3次，失败后人工介入 | 技术负责人 |
| 生成内容违规 | 自动标记，进入人工审核 | 审核员 |
| 视频生成失败 | 通知运营，支持重新生成 | 内容运营 |
| 成本超预算 | 自动告警，暂停非紧急任务 | 技术负责人 |
| 平台发布失败 | 记录原因，支持手动重试 | 内容运营 |

### 1.5 约束条件（完善版）

- **合规约束：**
  - 禁止全自动爬取和发布，必须通过官方API或人工操作
  - 所有发布内容必须经过人工审核
  - 遵守《网络安全法》《个人信息保护法》

- **成本约束：**
  - 月度总成本控制在3万元以内
  - 单条视频成本≤50元
  - API调用设置日预算上限

- **技术约束：**
  - 视频生成依赖Seedance 2.0 API，需处理异步回调
  - 系统需支持高并发API调用限流
  - 数据存储需符合安全规范

- **人员约束：**
  - 初期团队3-4人，含1名内容审核员
  - 内容运营需具备短视频创作经验
  - 技术负责人需熟悉AI API集成

---

## 二、概要设计（完善版）

### 2.1 系统架构（完善版）

#### 2.1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           接入层                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │   Web管理端  │  │   移动端    │  │      第三方回调              │  │
│  │  (Vue.js)   │  │  (H5/小程序)│  │   (Seedance/平台API)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                          网关层                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │   Nginx     │  │  限流熔断    │  │      认证授权               │  │
│  │  (反向代理)  │  │  (RateLimit)│  │      (JWT/OAuth2)           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                        应用服务层                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 热点采集  │ │ AI分析   │ │ 脚本生成 │ │ 视频生成 │ │ 人工审核 │  │
│  │  服务    │ │  服务    │ │  服务   │ │  服务   │ │  服务   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 发布管理  │ │ 数据监控 │ │ 成本控制 │ │ 内容库  │ │ 用户管理 │  │
│  │  服务    │ │  服务    │ │  服务   │ │  服务   │ │  服务   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                         AI服务层                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │   DeepSeek-V4    │  │     GLM-5.1      │  │   Seedance 2.0   │  │
│  │   (分析引擎)      │  │   (生成引擎)      │  │   (视频引擎)      │  │
│  │  - 内容分析       │  │  - 脚本生成       │  │  - 视频生成       │  │
│  │  - 框架提取       │  │  - 文案优化       │  │  - 风格迁移       │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                        基础设施层                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ OpenClaw │ │  MySQL   │ │  Redis   │ │   OSS    │ │ Prometheus│  │
│  │ (调度)   │ │ (主从)   │ │ (缓存)   │ │ (对象存储)│ │ (监控)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  Celery  │ │  RabbitMQ│ │  Docker  │ │  Nacos   │ │  Grafana │  │
│  │ (任务队列)│ │ (消息)   │ │ (容器)   │ │ (配置中心)│ │ (可视化) │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.1.2 部署架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         生产环境                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Kubernetes集群                            │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │    │
│  │  │  API服务 Pod │  │  任务 Pod   │  │     Web Pod         │  │    │
│  │  │  (3 replicas)│  │  (2 replicas)│  │   (2 replicas)      │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │  MySQL主从   │  │  Redis集群  │  │      OSS存储               │  │
│  │  (RDS)      │  │  (云托管)   │  │    (阿里云/腾讯云)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块划分（完善版）

| 模块 | 职责 | 技术选型 | 部署方式 |
|------|------|----------|----------|
| 热点采集服务 | 监控各平台热门内容 | Python + Playwright + 官方API | 定时任务Pod |
| AI分析服务 | 分析爆款内容框架 | DeepSeek-V4 API + FastAPI | API服务Pod |
| 脚本生成服务 | 生成原创视频脚本 | GLM-5.1 API + FastAPI | API服务Pod |
| 视频生成服务 | 生成视频素材 | Seedance 2.0 API + FastAPI | API服务Pod |
| 人工审核服务 | 内容审核与确认 | FastAPI + Vue.js | Web服务Pod |
| 发布管理服务 | 辅助发布流程 | 各平台官方API + FastAPI | API服务Pod |
| 数据监控服务 | 效果追踪 | Python + ECharts | Web服务Pod |
| 成本控制服务 | API调用成本监控 | Python + Prometheus | 定时任务Pod |
| 内容库服务 | 历史内容管理 | FastAPI + MySQL | API服务Pod |
| 用户管理服务 | 权限与认证 | FastAPI + JWT | API服务Pod |

### 2.3 数据流设计（完善版）

#### 2.3.1 正常流程

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 定时任务 │ → │ 热点采集 │ → │ 数据清洗 │ → │ 热点入库 │ → │ 通知运营 │
│ (OpenClaw)│   │ (Playwright)│  │ (Python) │   │ (MySQL)  │   │ (WebSocket)│
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                                   ↓
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 分析入库 │ ← │ DeepSeek │ ← │ 运营选择 │ ← │ 查看热点 │ ← │ 运营登录 │
│ (MySQL)  │   │ (API)    │   │ 热点     │   │ (Web)    │   │ (Web)    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     ↓
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 脚本入库 │ ← │ GLM-5.1 │ ← │ 审核脚本 │ ← │ 生成脚本 │ ← │ 查看分析 │
│ (MySQL)  │   │ (API)   │   │ (人工)   │   │ (API)    │   │ (Web)    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     ↓
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 视频入库 │ ← │ Seedance│ ← │ 审核视频 │ ← │ 生成视频 │ ← │ 查看脚本 │
│ (OSS)    │   │ (API)   │   │ (人工)   │   │ (API)    │   │ (Web)    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     ↓
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 发布记录 │ ← │ 平台API │ ← │ 人工确认 │ ← │ 查看视频 │ ← │ 运营操作 │
│ (MySQL)  │   │ (官方)  │   │ (Web)    │   │ (Web)    │   │ (Web)    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

#### 2.3.2 异常流程

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│ 生成失败 │ → │ 记录日志 │ → │ 通知运营 │
│ (API)   │   │ (MySQL)  │   │ (钉钉/微信)│
└─────────┘    └─────────┘    └─────────┘
     ↓
┌─────────┐    ┌─────────┐    ┌─────────┐
│ 重新生成 │ ← │ 运营确认 │ ← │ 查看失败原因│
│ (API)   │   │ (Web)    │   │ (Web)    │
└─────────┘    └─────────┘    └─────────┘
```

### 2.4 接口设计（完善版）

#### 2.4.1 RESTful API规范

| 接口 | 方法 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| /api/v1/hotspot/fetch | POST | 手动触发热点采集 | `{platform, category, limit}` | `{task_id, status}` |
| /api/v1/hotspot/list | GET | 获取热点列表 | `Query: platform, date, page` | `{items, total}` |
| /api/v1/analysis/{id} | POST | 执行AI分析 | `{hotspot_id, analysis_type}` | `{task_id, status}` |
| /api/v1/analysis/report/{id} | GET | 获取分析报告 | - | `{report_content, created_at}` |
| /api/v1/script/generate | POST | 生成脚本 | `{analysis_id, content_type, topic}` | `{script_id, content}` |
| /api/v1/script/review | POST | 审核脚本 | `{script_id, status, comment}` | `{next_step}` |
| /api/v1/video/generate | POST | 生成视频 | `{script_id, style, size}` | `{task_id, status}` |
| /api/v1/video/status/{id} | GET | 查询视频状态 | - | `{status, progress, url}` |
| /api/v1/video/review | POST | 审核视频 | `{video_id, status, comment}` | `{next_step}` |
| /api/v1/publish/submit | POST | 提交发布 | `{video_id, platforms, schedule}` | `{publish_task_id}` |
| /api/v1/publish/status/{id} | GET | 查询发布状态 | - | `{status, platform_urls}` |
| /api/v1/cost/realtime | GET | 实时成本 | - | `{today, month, breakdown}` |
| /api/v1/cost/report | GET | 成本报表 | `Query: start_date, end_date` | `{daily_costs, total}` |
| /api/v1/content/library | GET | 内容库 | `Query: type, tag, page` | `{items, total}` |
| /api/v1/dashboard/metrics | GET | 仪表盘数据 | - | `{production, cost, quality}` |

#### 2.4.2 WebSocket接口

| 接口 | 说明 | 消息类型 |
|------|------|----------|
| /ws/notifications | 实时通知 | `task_completed`, `review_required`, `alert` |
| /ws/cost | 实时成本 | `cost_update` |

#### 2.4.3 回调接口

| 接口 | 说明 | 来源 |
|------|------|------|
| /callback/video | 视频生成完成回调 | Seedance 2.0 |
| /callback/publish | 平台发布状态回调 | 各平台官方API |

---

## 三、详细设计（完善版）

### 3.1 热点采集模块（完善版）

#### 3.1.1 功能描述（完善）
- 支持抖音、小红书、B站热门内容监控
- 采用官方API为主，人工补充为辅
- 每日定时采集（00:00、12:00），频率可控
- 支持关键词过滤和分类标签
- 采集数据保存30天，支持历史回溯

#### 3.1.2 技术实现（完善）

```python
# 核心流程
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

class Platform(Enum):
    DOUYIN = "douyin"
    XIAOHONGSHU = "xiaohongshu"
    BILIBILI = "bilibili"

class Category(Enum):
    KNOWLEDGE = "knowledge"
    EMOTION = "emotion"
    PRODUCT = "product"
    ENTERTAINMENT = "entertainment"

@dataclass
class HotspotItem:
    id: str
    platform: Platform
    content_id: str
    title: str
    author: str
    url: str
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    category: Category
    tags: List[str]
    fetched_at: datetime
    cover_image: Optional[str] = None
    duration: Optional[int] = None  # 视频时长（秒）

class HotspotCollector:
    """热点采集器"""
    
    def __init__(self):
        self.collectors = {
            Platform.DOUYIN: DouyinCollector(),
            Platform.XIAOHONGSHU: XiaohongshuCollector(),
            Platform.BILIBILI: BilibiliCollector()
        }
        self.db = Database()
        self.logger = Logger()
    
    async def fetch_hotspots(
        self,
        platform: Platform,
        category: Category,
        limit: int = 10,
        keywords: Optional[List[str]] = None
    ) -> List[HotspotItem]:
        """
        采集热点内容
        
        Args:
            platform: 平台名称
            category: 内容分类
            limit: 采集数量（最大50）
            keywords: 关键词过滤
        
        Returns:
            List[HotspotItem]: 热点内容列表
        """
        try:
            # 1. 调用对应平台的采集器
            collector = self.collectors[platform]
            raw_data = await collector.fetch(category, limit)
            
            # 2. 数据清洗和转换
            items = [self._parse_item(data, platform) for data in raw_data]
            
            # 3. 关键词过滤
            if keywords:
                items = [item for item in items 
                        if any(kw in item.title for kw in keywords)]
            
            # 4. 去重（基于content_id）
            existing_ids = self.db.get_existing_content_ids(platform)
            items = [item for item in items if item.content_id not in existing_ids]
            
            # 5. 存储到数据库
            self.db.save_hotspots(items)
            
            # 6. 记录日志
            self.logger.info(f"Fetched {len(items)} hotspots from {platform.value}")
            
            return items
            
        except Exception as e:
            self.logger.error(f"Failed to fetch hotspots: {e}")
            raise
    
    def _parse_item(self, raw_data: dict, platform: Platform) -> HotspotItem:
        """解析原始数据为HotspotItem"""
        return HotspotItem(
            id=generate_uuid(),
            platform=platform,
            content_id=raw_data.get("id"),
            title=raw_data.get("title", ""),
            author=raw_data.get("author", ""),
            url=raw_data.get("url", ""),
            view_count=raw_data.get("view_count", 0),
            like_count=raw_data.get("like_count", 0),
            comment_count=raw_data.get("comment_count", 0),
            share_count=raw_data.get("share_count", 0),
            category=Category(raw_data.get("category", "entertainment")),
            tags=raw_data.get("tags", []),
            fetched_at=datetime.now(),
            cover_image=raw_data.get("cover_image"),
            duration=raw_data.get("duration")
        )

# 各平台采集器实现
class DouyinCollector:
    """抖音热点采集器"""
    
    async def fetch(self, category: Category, limit: int) -> List[dict]:
        # 1. 优先使用官方API
        # 2. 备选：Playwright模拟浏览器（需处理反爬）
        # 3. 返回原始数据列表
        pass

class XiaohongshuCollector:
    """小红书热点采集器"""
    
    async def fetch(self, category: Category, limit: int) -> List[dict]:
        # 类似实现
        pass

class BilibiliCollector:
    """B站热点采集器"""
    
    async def fetch(self, category: Category, limit: int) -> List[dict]:
        # 类似实现
        pass
```

#### 3.1.3 数据模型（完善）

```sql
-- 热点内容表
CREATE TABLE hotspot_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增ID',
    uuid VARCHAR(36) NOT NULL UNIQUE COMMENT '全局唯一ID',
    platform VARCHAR(50) NOT NULL COMMENT '平台名称',
    content_id VARCHAR(100) NOT NULL COMMENT '平台内容ID',
    title VARCHAR(500) COMMENT '标题',
    author VARCHAR(100) COMMENT '作者',
    author_id VARCHAR(100) COMMENT '作者ID',
    url VARCHAR(500) COMMENT '链接',
    cover_image VARCHAR(500) COMMENT '封面图URL',
    video_url VARCHAR(500) COMMENT '视频URL（如有）',
    view_count INT DEFAULT 0 COMMENT '播放量',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    comment_count INT DEFAULT 0 COMMENT '评论数',
    share_count INT DEFAULT 0 COMMENT '分享数',
    category VARCHAR(50) COMMENT '内容分类',
    tags JSON COMMENT '标签列表',
    duration INT COMMENT '视频时长（秒）',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_platform_content (platform, content_id),
    INDEX idx_platform_fetched (platform, fetched_at),
    INDEX idx_category (category),
    INDEX idx_tags (tags)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='热点内容表';

-- 采集任务日志表
CREATE TABLE collection_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(36) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    category VARCHAR(50),
    status VARCHAR(20) COMMENT 'success/failed',
    item_count INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集任务日志表';
```

#### 3.1.4 配置参数

```yaml
# hotspot_config.yaml
collection:
  schedule:
    - "0 0 * * *"    # 每天00:00
    - "0 12 * * *"   # 每天12:00
  platforms:
    - douyin
    - xiaohongshu
    - bilibili
  categories:
    - knowledge
    - emotion
    - product
    - entertainment
  limits:
    default: 10
    max: 50
  filters:
    min_view_count: 10000
    min_like_count: 1000
  retention_days: 30
```

### 3.2 AI分析模块（完善版）

#### 3.2.1 功能描述（完善）
- 基于DeepSeek-V4分析爆款内容框架
- 提取内容结构、情绪曲线、钩子设计、节奏控制
- 生成《内容框架参考报告》（结构化JSON）
- 支持批量分析
- 分析结果持久化，支持历史对比

#### 3.2.2 技术实现（完善）

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class HookType(Enum):
    SUSPENSE = "suspense"          # 悬念式
    QUESTION = "question"          # 提问式
    CONTRAST = "contrast"          # 对比式
    EMOTION = "emotion"            # 情绪式
    FACT = "fact"                  # 事实式

@dataclass
class ContentStructure:
    opening: str                   # 开头（0-3秒）
    body: List[str]               # 主体（3-12秒）
    climax: str                   # 高潮（12-15秒）
    ending: str                   # 结尾（15秒+）

@dataclass
class EmotionCurve:
    points: List[Dict]            # 情绪曲线点 [{time, emotion, intensity}]
    peak_time: int                # 情绪峰值时间
    valley_time: int              # 情绪谷值时间

@dataclass
class HookDesign:
    type: HookType                # 钩子类型
    content: str                  # 钩子内容
    duration: int                 # 钩子时长（秒）
    effectiveness: float          # 预估效果（0-1）

@dataclass
class AnalysisReport:
    id: str
    hotspot_id: str
    content_structure: ContentStructure
    emotion_curve: EmotionCurve
    hook_design: HookDesign
    framework_summary: str        # 框架摘要
    reusable_elements: List[str]  # 可复用元素
    risk_warnings: List[str]      # 风险提示
    created_at: datetime

class AIAnalyzer:
    """AI分析器"""
    
    def __init__(self):
        self.deepseek = DeepSeekClient(api_key=config.DEEPSEEK_API_KEY)
        self.db = Database()
        self.cost_controller = CostController()
    
    async def analyze_content(
        self,
        hotspot_id: str,
        analysis_type: str = "comprehensive"
    ) -> AnalysisReport:
        """
        分析爆款内容
        
        Args:
            hotspot_id: 热点内容ID
            analysis_type: 分析类型（comprehensive/quick）
        
        Returns:
            AnalysisReport: 分析报告
        """
        # 1. 获取热点内容
        hotspot = self.db.get_hotspot(hotspot_id)
        if not hotspot:
            raise ValueError(f"Hotspot not found: {hotspot_id}")
        
        # 2. 构建分析Prompt
        prompt = self._build_analysis_prompt(hotspot, analysis_type)
        
        # 3. 调用DeepSeek-V4 API
        start_time = time.time()
        response = await self.deepseek.chat.completions.create(
            model="deepseek-v4",
            messages=[
                {"role": "system", "content": "你是一位短视频内容分析专家，擅长分析爆款视频的内容框架和成功要素。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # 4. 记录成本
        cost = response.usage.total_tokens * config.DEEPSEEK_V4_PRICE_PER_TOKEN
        self.cost_controller.record_api_call("deepseek-v4", cost)
        
        # 5. 解析JSON响应
        analysis_data = json.loads(response.choices[0].message.content)
        
        # 6. 构建分析报告
        report = self._build_report(hotspot_id, analysis_data)
        
        # 7. 保存到数据库
        self.db.save_analysis_report(report)
        
        # 8. 记录性能指标
        duration = time.time() - start_time
        self.logger.info(f"Analysis completed in {duration:.2f}s, cost: ¥{cost:.4f}")
        
        return report
    
    def _build_analysis_prompt(self, hotspot: HotspotItem, analysis_type: str) -> str:
        """构建分析Prompt"""
        base_prompt = f"""
        请分析以下爆款视频的内容框架，并以JSON格式返回分析结果：
        
        视频信息：
        - 标题：{hotspot.title}
        - 作者：{hotspot.author}
        - 播放量：{hotspot.view_count}
        - 点赞数：{hotspot.like_count}
        - 评论数：{hotspot.comment_count}
        - 分享数：{hotspot.share_count}
        - 时长：{hotspot.duration}秒
        - 分类：{hotspot.category.value}
        - 标签：{', '.join(hotspot.tags)}
        """
        
        if analysis_type == "comprehensive":
            base_prompt += """
            
            请提供以下分析（JSON格式）：
            {
                "content_structure": {
                    "opening": "开头设计（0-3秒），说明如何吸引注意力",
                    "body": ["主体内容要点1", "主体内容要点2", "主体内容要点3"],
                    "climax": "高潮设计，说明如何制造情绪峰值",
                    "ending": "结尾设计，说明如何引导互动"
                },
                "emotion_curve": {
                    "points": [
                        {"time": 0, "emotion": "好奇", "intensity": 0.8},
                        {"time": 5, "emotion": "兴奋", "intensity": 0.9},
                        {"time": 10, "emotion": "共鸣", "intensity": 0.7}
                    ],
                    "peak_time": 5,
                    "valley_time": 8
                },
                "hook_design": {
                    "type": "悬念式/提问式/对比式/情绪式/事实式",
                    "content": "钩子具体内容",
                    "duration": 3,
                    "effectiveness": 0.85
                },
                "framework_summary": "内容框架摘要（100字以内）",
                "reusable_elements": ["可复用的元素1", "可复用的元素2"],
                "risk_warnings": ["潜在风险1", "潜在风险2"]
            }
            """
        else:
            base_prompt += """
            
            请提供简要分析（JSON格式）：
            {
                "framework_summary": "内容框架摘要（50字以内）",
                "reusable_elements": ["可复用的元素1"],
                "risk_warnings": ["潜在风险1"]
            }
            """
        
        return base_prompt
    
    def _build_report(self, hotspot_id: str, data: dict) -> AnalysisReport:
        """从JSON数据构建报告对象"""
        return AnalysisReport(
            id=generate_uuid(),
            hotspot_id=hotspot_id,
            content_structure=ContentStructure(
                opening=data["content_structure"]["opening"],
                body=data["content_structure"]["body"],
                climax=data["content_structure"]["climax"],
                ending=data["content_structure"]["ending"]
            ),
            emotion_curve=EmotionCurve(
                points=data["emotion_curve"]["points"],
                peak_time=data["emotion_curve"]["peak_time"],
                valley_time=data["emotion_curve"]["valley_time"]
            ),
            hook_design=HookDesign(
                type=HookType(data["hook_design"]["type"]),
                content=data["hook_design"]["content"],
                duration=data["hook_design"]["duration"],
                effectiveness=data["hook_design"]["effectiveness"]
            ),
            framework_summary=data["framework_summary"],
            reusable_elements=data["reusable_elements"],
            risk_warnings=data["risk_warnings"],
            created_at=datetime.now()
        )
```

#### 3.2.3 数据模型（完善）

```sql
-- 分析报告表
CREATE TABLE analysis_reports (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    hotspot_id VARCHAR(36) NOT NULL COMMENT '关联的热点ID',
    analysis_type VARCHAR(20) DEFAULT 'comprehensive' COMMENT '分析类型',
    content_structure JSON COMMENT '内容结构',
    emotion_curve JSON COMMENT '情绪曲线',
    hook_design JSON COMMENT '钩子设计',
    framework_summary TEXT COMMENT '框架摘要',
    reusable_elements JSON COMMENT '可复用元素',
    risk_warnings JSON COMMENT '风险提示',
    api_cost DECIMAL(10, 4) COMMENT 'API调用成本',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_hotspot_id (hotspot_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分析报告表';
```

### 3.3 脚本生成模块（完善版）

#### 3.3.1 功能描述（完善）
- 基于GLM-5.1生成原创视频脚本
- 支持多种内容类型（知识科普、情感故事、产品种草、娱乐搞笑）
- 支持自定义风格（专业、轻松、幽默、严肃）
- 人工审核后进入下一环节
- 脚本版本管理，支持历史回溯

#### 3.3.2 技术实现（完善）

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class ContentType(Enum):
    KNOWLEDGE = "knowledge"        # 知识科普
    EMOTION = "emotion"            # 情感故事
    PRODUCT = "product"            # 产品种草
    ENTERTAINMENT = "entertainment" # 娱乐搞笑

class StyleType(Enum):
    PROFESSIONAL = "professional"  # 专业
    CASUAL = "casual"              # 轻松
    HUMOROUS = "humorous"          # 幽默
    SERIOUS = "serious"            # 严肃

@dataclass
class Scene:
    sequence: int                  # 场景序号
    duration: int                  # 场景时长（秒）
    visual_description: str        # 画面描述
    audio_narration: str          # 旁白文案
    bgm_suggestion: Optional[str] = None  # BGM建议
    transition: Optional[str] = None      # 转场效果

@dataclass
class Script:
    id: str
    analysis_id: str
    content_type: ContentType
    style: StyleType
    topic: str
    title: str
    duration: int                  # 总时长（秒）
    scenes: List[Scene]           # 场景列表
    hook: str                      # 钩子文案
    cta: str                       # 行动号召（Call to Action）
    tags: List[str]
    version: int                   # 版本号
    status: str                    # draft/pending_review/approved/rejected
    created_at: datetime
    updated_at: datetime

class ScriptGenerator:
    """脚本生成器"""
    
    def __init__(self):
        self.glm = GLMClient(api_key=config.GLM_API_KEY)
        self.db = Database()
        self.cost_controller = CostController()
        self.plagiarism_checker = PlagiarismChecker()
    
    async def generate_script(
        self,
        analysis_id: str,
        content_type: ContentType,
        style: StyleType,
        topic: str,
        duration: int = 15
    ) -> Script:
        """
        生成视频脚本
        
        Args:
            analysis_id: 分析报告ID
            content_type: 内容类型
            style: 风格类型
            topic: 主题
            duration: 目标时长（秒）
        
        Returns:
            Script: 视频脚本
        """
        # 1. 获取分析报告
        analysis = self.db.get_analysis_report(analysis_id)
        if not analysis:
            raise ValueError(f"Analysis report not found: {analysis_id}")
        
        # 2. 构建生成Prompt
        prompt = self._build_script_prompt(
            analysis, content_type, style, topic, duration
        )
        
        # 3. 调用GLM-5.1 API
        start_time = time.time()
        response = await self.glm.chat.completions.create(
            model="glm-5.1",
            messages=[
                {"role": "system", "content": "你是一位资深短视频编剧，擅长创作爆款短视频脚本。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        # 4. 记录成本
        cost = response.usage.total_tokens * config.GLM_51_PRICE_PER_TOKEN
        self.cost_controller.record_api_call("glm-5.1", cost)
        
        # 5. 解析JSON响应
        script_data = json.loads(response.choices[0].message.content)
        
        # 6. 构建脚本对象
        script = self._build_script(analysis_id, script_data, content_type, style, topic, duration)
        
        # 7. 查重检测
        similarity = await self.plagiarism_checker.check(script)
        if similarity > 0.3:
            script.risk_warnings.append(f"查重率较高: {similarity:.2%}")
        
        # 8. 保存到数据库
        self.db.save_script(script)
        
        # 9. 记录性能指标
        duration_ms = time.time() - start_time
        self.logger.info(f"Script generated in {duration_ms:.2f}s, cost: ¥{cost:.4f}")
        
        return script
    
    def _build_script_prompt(
        self,
        analysis: AnalysisReport,
        content_type: ContentType,
        style: StyleType,
        topic: str,
        duration: int
    ) -> str:
        """构建脚本生成Prompt"""
        return f"""
        基于以下爆款内容框架，创作一个原创短视频脚本：
        
        【框架参考】
        框架摘要：{analysis.framework_summary}
        内容结构：
        - 开头：{analysis.content_structure.opening}
        - 主体：{', '.join(analysis.content_structure.body)}
        - 高潮：{analysis.content_structure.climax}
        - 结尾：{analysis.content_structure.ending}
        
        钩子设计：
        - 类型：{analysis.hook_design.type.value}
        - 内容：{analysis.hook_design.content}
        - 效果预估：{analysis.hook_design.effectiveness}
        
        【创作要求】
        内容类型：{content_type.value}
        风格：{style.value}
        主题：{topic}
        目标时长：{duration}秒
        
        【输出格式】
        请以JSON格式输出脚本：
        {{
            "title": "脚本标题",
            "duration": {duration},
            "hook": "前3秒钩子文案",
            "scenes": [
                {{
                    "sequence": 1,
                    "duration": 5,
                    "visual_description": "画面描述（详细、可执行）",
                    "audio_narration": "旁白文案（口语化、有节奏感）",
                    "bgm_suggestion": "BGM建议",
                    "transition": "转场效果"
                }}
            ],
            "cta": "结尾行动号召（引导点赞/关注/评论）",
            "tags": ["标签1", "标签2"]
        }}
        
        【注意事项】
        1. 完全原创，不抄袭参考内容
        2. 符合平台内容规范，无违规内容
        3. 口语化表达，适合短视频场景
        4. 画面描述要具体、可执行
        5. 总时长控制在{duration}秒左右
        """
    
    def _build_script(
        self,
        analysis_id: str,
        data: dict,
        content_type: ContentType,
        style: StyleType,
        topic: str,
        duration: int
    ) -> Script:
        """从JSON数据构建脚本对象"""
        scenes = [
            Scene(
                sequence=s["sequence"],
                duration=s["duration"],
                visual_description=s["visual_description"],
                audio_narration=s["audio_narration"],
                bgm_suggestion=s.get("bgm_suggestion"),
                transition=s.get("transition")
            )
            for s in data["scenes"]
        ]
        
        return Script(
            id=generate_uuid(),
            analysis_id=analysis_id,
            content_type=content_type,
            style=style,
            topic=topic,
            title=data["title"],
            duration=data["duration"],
            scenes=scenes,
            hook=data["hook"],
            cta=data["cta"],
            tags=data["tags"],
            version=1,
            status="pending_review",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
```

#### 3.3.3 数据模型（完善）

```sql
-- 脚本表
CREATE TABLE scripts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    analysis_id VARCHAR(36) NOT NULL COMMENT '关联的分析报告ID',
    content_type VARCHAR(50) COMMENT '内容类型',
    style VARCHAR(50) COMMENT '风格类型',
    topic VARCHAR(200) COMMENT '主题',
    title VARCHAR(200) COMMENT '脚本标题',
    duration INT COMMENT '总时长（秒）',
    scenes JSON COMMENT '场景列表',
    hook TEXT COMMENT '钩子文案',
    cta TEXT COMMENT '行动号召',
    tags JSON COMMENT '标签',
    version INT DEFAULT 1 COMMENT '版本号',
    status VARCHAR(20) DEFAULT 'pending_review' COMMENT '状态',
    similarity_score DECIMAL(5, 4) COMMENT '查重率',
    api_cost DECIMAL(10, 4) COMMENT 'API调用成本',
    created_by VARCHAR(100) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_analysis_id (analysis_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脚本表';

-- 脚本审核记录表
CREATE TABLE script_reviews (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    script_id VARCHAR(36) NOT NULL,
    reviewer VARCHAR(100) COMMENT '审核人',
    status VARCHAR(20) COMMENT 'approved/rejected',
    comment TEXT COMMENT '审核意见',
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_script_id (script_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脚本审核记录表';
```

### 3.4 视频生成模块（完善版）

#### 3.4.1 功能描述（完善）
- 基于Seedance 2.0生成视频素材
- 支持文生视频、图生视频、视频续写
- 异步处理，回调通知
- 支持多种风格（写实、动画、3D、水墨）
- 视频质量检测（清晰度、流畅度、一致性）

#### 3.4.2 技术实现（完善）

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class VideoStyle(Enum):
    REALISTIC = "realistic"        # 写实
    ANIMATION = "animation"        # 动画
    THREE_D = "3d"                 # 3D
    INK = "ink"                    # 水墨
    CYBERPUNK = "cyberpunk"        # 赛博朋克

class VideoStatus(Enum):
    PENDING = "pending"            # 等待中
    PROCESSING = "processing"      # 处理中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消

@dataclass
class VideoTask:
    id: str
    script_id: str
    status: VideoStatus
    style: VideoStyle
    size: str                      # 分辨率（如1080x1920）
    duration: int                  # 时长（秒）
    prompt: str                    # 生成提示词
    video_url: Optional[str] = None
    cover_url: Optional[str] = None
    progress: float = 0.0          # 进度（0-1）
    error_message: Optional[str] = None
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None

class VideoGenerator:
    """视频生成器"""
    
    def __init__(self):
        self.seedance = SeedanceClient(api_key=config.SEEDANCE_API_KEY)
        self.db = Database()
        self.oss = OSSClient()
        self.cost_controller = CostController()
        self.quality_checker = VideoQualityChecker()
    
    async def generate_video(
        self,
        script_id: str,
        style: VideoStyle = VideoStyle.REALISTIC,
        size: str = "1080x1920"
    ) -> VideoTask:
        """
        生成视频
        
        Args:
            script_id: 脚本ID
            style: 视频风格
            size: 分辨率
        
        Returns:
            VideoTask: 视频生成任务
        """
        # 1. 获取脚本
        script = self.db.get_script(script_id)
        if not script:
            raise ValueError(f"Script not found: {script_id}")
        
        # 2. 构建视频生成提示词
        prompt = self._build_video_prompt(script, style)
        
        # 3. 创建任务记录
        task = VideoTask(
            id=generate_uuid(),
            script_id=script_id,
            status=VideoStatus.PENDING,
            style=style,
            size=size,
            duration=script.duration,
            prompt=prompt
        )
        self.db.save_video_task(task)
        
        # 4. 调用Seedance 2.0 API（异步）
        try:
            seedance_task = await self.seedance.video.generations.create(
                model="seedance-2.0",
                prompt=prompt,
                size=size,
                duration=script.duration,
                style=style.value,
                callback_url=f"{config.BASE_URL}/callback/video"
            )
            
            # 5. 更新任务状态
            task.status = VideoStatus.PROCESSING
            self.db.update_video_task(task)
            
            # 6. 记录成本（预估）
            estimated_cost = script.duration * config.SEEDANCE_PRICE_PER_SECOND
            self.cost_controller.record_api_call("seedance-2.0", estimated_cost)
            
            self.logger.info(f"Video task created: {task.id}, estimated cost: ¥{estimated_cost:.2f}")
            
        except Exception as e:
            task.status = VideoStatus.FAILED
            task.error_message = str(e)
            self.db.update_video_task(task)
            self.logger.error(f"Failed to create video task: {e}")
            raise
        
        return task
    
    def _build_video_prompt(self, script: Script, style: VideoStyle) -> str:
        """构建视频生成提示词"""
        scenes_desc = "\n".join([
            f"场景{s.sequence}（{s.duration}秒）：{s.visual_description}"
            for s in script.scenes
        ])
        
        return f"""
        创作一个{script.duration}秒的短视频：
        
        主题：{script.topic}
        风格：{style.value}
        
        分镜描述：
        {scenes_desc}
        
        要求：
        - 画面流畅，转场自然
        - 符合{style.value}风格
        - 时长控制在{script.duration}秒左右
        """
    
    async def handle_callback(self, callback_data: dict):
        """处理视频生成回调"""
        task_id = callback_data.get("task_id")
        status = callback_data.get("status")
        
        task = self.db.get_video_task(task_id)
        if not task:
            self.logger.error(f"Video task not found: {task_id}")
            return
        
        if status == "completed":
            # 1. 下载视频
            video_url = callback_data.get("video_url")
            video_path = await self._download_video(video_url, task_id)
            
            # 2. 上传到OSS
            oss_url = await self.oss.upload(video_path, f"videos/{task_id}.mp4")
            
            # 3. 质量检测
            quality_report = await self.quality_checker.check(video_path)
            
            # 4. 更新任务状态
            task.status = VideoStatus.COMPLETED
            task.video_url = oss_url
            task.progress = 1.0
            task.completed_at = datetime.now()
            self.db.update_video_task(task)
            
            # 5. 通知审核员
            await self._notify_reviewer(task, quality_report)
            
            self.logger.info(f"Video completed: {task_id}, quality: {quality_report.score}")
            
        else:
            # 处理失败
            task.status = VideoStatus.FAILED
            task.error_message = callback_data.get("error", "Unknown error")
            self.db.update_video_task(task)
            
            # 通知运营
            await self._notify_operator(task)
            
            self.logger.error(f"Video failed: {task_id}, error: {task.error_message}")
    
    async def _download_video(self, url: str, task_id: str) -> str:
        """下载视频到本地"""
        import aiohttp
        import aiofiles
        
        video_path = f"/tmp/videos/{task_id}.mp4"
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                async with aiofiles.open(video_path, 'wb') as f:
                    await f.write(await response.read())
        
        return video_path
    
    async def _notify_reviewer(self, task: VideoTask, quality_report: dict):
        """通知审核员"""
        message = {
            "type": "video_review_required",
            "task_id": task.id,
            "script_id": task.script_id,
            "video_url": task.video_url,
            "quality_score": quality_report.score,
            "quality_issues": quality_report.issues
        }
        await WebSocketManager.broadcast("reviewers", message)
    
    async def _notify_operator(self, task: VideoTask):
        """通知运营"""
        message = {
            "type": "video_generation_failed",
            "task_id": task.id,
            "script_id": task.script_id,
            "error": task.error_message
        }
        await WebSocketManager.broadcast("operators", message)

class VideoQualityChecker:
    """视频质量检测器"""
    
    async def check(self, video_path: str) -> dict:
        """
        检测视频质量
        
        Returns:
            dict: {score, issues, details}
        """
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        
        # 1. 检测分辨率
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 2. 检测帧率
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 3. 检测时长
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        # 4. 检测清晰度（抽样检测）
        clarity_scores = []
        for i in range(0, frame_count, max(1, frame_count // 10)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                clarity = cv2.Laplacian(gray, cv2.CV_64F).var()
                clarity_scores.append(clarity)
        
        avg_clarity = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0
        
        cap.release()
        
        # 5. 生成质量报告
        issues = []
        if width < 1080 or height < 1920:
            issues.append("分辨率不足")
        if fps < 24:
            issues.append("帧率过低")
        if avg_clarity < 100:
            issues.append("画面模糊")
        
        score = 1.0
        if issues:
            score -= len(issues) * 0.2
        
        return {
            "score": max(0, score),
            "issues": issues,
            "details": {
                "resolution": f"{width}x{height}",
                "fps": fps,
                "duration": duration,
                "clarity": avg_clarity
            }
        }
```

#### 3.4.3 数据模型（完善）

```sql
-- 视频任务表
CREATE TABLE video_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    script_id VARCHAR(36) NOT NULL COMMENT '关联的脚本ID',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
    style VARCHAR(50) COMMENT '视频风格',
    size VARCHAR(20) COMMENT '分辨率',
    duration INT COMMENT '时长（秒）',
    prompt TEXT COMMENT '生成提示词',
    video_url VARCHAR(500) COMMENT '视频URL',
    cover_url VARCHAR(500) COMMENT '封面URL',
    progress DECIMAL(5, 2) DEFAULT 0 COMMENT '进度（0-1）',
    error_message TEXT COMMENT '错误信息',
    quality_score DECIMAL(5, 4) COMMENT '质量评分',
    quality_report JSON COMMENT '质量报告',
    api_cost DECIMAL(10, 4) COMMENT 'API调用成本',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_script_id (script_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频任务表';
```

### 3.5 人工审核模块（完善版）

#### 3.5.1 功能描述（完善）
- 脚本审核：检查内容合规性、原创性、质量
- 视频审核：检查画面质量、品牌一致性、技术问题
- 发布确认：最终人工确认后发布
- 审核历史记录，支持审计追溯
- 审核标准可配置

#### 3.5.2 审核流程（完善）

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 脚本生成 │ → │ 脚本审核 │ → │ 视频生成 │ → │ 视频审核 │ → │ 发布确认 │
│ (AI)    │   │ (人工)   │   │ (AI)    │   │ (人工)   │   │ (人工)   │
└─────────┘    └────┬────┘    └─────────┘    └────┬────┘    └────┬────┘
                    │                               │              │
              ┌─────┴─────┐                  ┌─────┴─────┐   ┌────┴────┐
              │           │                  │           │   │         │
           [通过]      [驳回]             [通过]      [驳回] [确认]   [取消]
              │           │                  │           │   │         │
              ↓           ↓                  ↓           ↓   ↓         ↓
         [视频生成]   [返回修改]         [发布确认]   [重新生成] [发布] [存档]
```

#### 3.5.3 审核标准（完善）

| 审核阶段 | 审核项 | 标准 | 处理方式 | 责任人 |
|----------|--------|------|----------|--------|
| **脚本审核** | 内容合规 | 无违规内容（涉黄、涉暴、政治敏感） | 不通过则驳回 | 审核员 |
| | 原创性 | 查重率<30% | 不通过则重新生成 | 审核员 |
| | 内容质量 | 逻辑通顺，有吸引力 | 不通过则修改建议 | 审核员 |
| | 品牌一致性 | 符合品牌调性 | 不通过则修改 | 审核员 |
| | 时长控制 | 5-15秒 | 不通过则调整 | 审核员 |
| **视频审核** | 画面质量 | 清晰、无瑕疵、无黑屏 | 不通过则重新生成 | 审核员 |
| | 音画同步 | 音频与画面匹配 | 不通过则重新生成 | 审核员 |
| | 风格一致性 | 符合选定风格 | 不通过则重新生成 | 审核员 |
| | 技术合规 | 格式正确，大小合适 | 不通过则转码处理 | 审核员 |
| **发布确认** | 最终检查 | 标题、标签、封面完整 | 不通过则补充 | 运营 |
| | 发布平台 | 确认目标平台 | 不通过则调整 | 运营 |
| | 发布时间 | 确认发布时间 | 不通过则调整 | 运营 |

#### 3.5.4 技术实现（完善）

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class ReviewStatus(Enum):
    PENDING = "pending"            # 待审核
    APPROVED = "approved"          # 已通过
    REJECTED = "rejected"          # 已驳回
    NEEDS_MODIFICATION = "needs_modification"  # 需修改

class ReviewStage(Enum):
    SCRIPT = "script"              # 脚本审核
    VIDEO = "video"                # 视频审核
    PUBLISH = "publish"            # 发布确认

@dataclass
class ReviewRecord:
    id: str
    stage: ReviewStage
    item_id: str                   # 脚本ID或视频ID
    reviewer: str
    status: ReviewStatus
    comment: str
    checklist: dict                # 审核清单
    created_at: datetime

class ReviewManager:
    """审核管理器"""
    
    def __init__(self):
        self.db = Database()
        self.notification = NotificationService()
    
    async def submit_for_review(
        self,
        stage: ReviewStage,
        item_id: str,
        submitter: str
    ):
        """提交审核"""
        # 1. 创建审核记录
        record = ReviewRecord(
            id=generate_uuid(),
            stage=stage,
            item_id=item_id,
            reviewer="",  # 待分配
            status=ReviewStatus.PENDING,
            comment="",
            checklist=self._get_checklist(stage),
            created_at=datetime.now()
        )
        self.db.save_review_record(record)
        
        # 2. 通知审核员
        await self.notification.notify_reviewers(stage, item_id)
        
        self.logger.info(f"Submitted for {stage.value} review: {item_id}")
    
    async def review(
        self,
        record_id: str,
        reviewer: str,
        status: ReviewStatus,
        comment: str,
        checklist: dict
    ):
        """执行审核"""
        # 1. 获取审核记录
        record = self.db.get_review_record(record_id)
        if not record:
            raise ValueError(f"Review record not found: {record_id}")
        
        # 2. 更新审核记录
        record.reviewer = reviewer
        record.status = status
        record.comment = comment
        record.checklist = checklist
        self.db.update_review_record(record)
        
        # 3. 根据审核结果处理
        if status == ReviewStatus.APPROVED:
            await self._handle_approval(record)
        elif status == ReviewStatus.REJECTED:
            await self._handle_rejection(record)
        elif status == ReviewStatus.NEEDS_MODIFICATION:
            await self._handle_modification(record)
        
        # 4. 通知提交人
        await self.notification.notify_submitter(record)
        
        self.logger.info(f"Review completed: {record_id}, status: {status.value}")
    
    async def _handle_approval(self, record: ReviewRecord):
        """处理通过"""
        if record.stage == ReviewStage.SCRIPT:
            # 脚本审核通过，进入视频生成
            await self._trigger_video_generation(record.item_id)
        elif record.stage == ReviewStage.VIDEO:
            # 视频审核通过，进入发布确认
            await self._notify_publish_confirmation(record.item_id)
        elif record.stage == ReviewStage.PUBLISH:
            # 发布确认通过，执行发布
            await self._execute_publish(record.item_id)
    
    async def _handle_rejection(self, record: ReviewRecord):
        """处理驳回"""
        # 更新对应内容状态为rejected
        if record.stage == ReviewStage.SCRIPT:
            self.db.update_script_status(record.item_id, "rejected")
        elif record.stage == ReviewStage.VIDEO:
            self.db.update_video_task_status(record.item_id, "rejected")
    
    async def _handle_modification(self, record: ReviewRecord):
        """处理需修改"""
        # 通知提交人修改
        await self.notification.notify_modification_required(
            record.item_id,
            record.comment
        )
    
    def _get_checklist(self, stage: ReviewStage) -> dict:
        """获取审核清单"""
        checklists = {
            ReviewStage.SCRIPT: {
                "content_compliance": {"label": "内容合规", "checked": False},
                "originality": {"label": "原创性", "checked": False},
                "content_quality": {"label": "内容质量", "checked": False},
                "brand_consistency": {"label": "品牌一致性", "checked": False},
                "duration_control": {"label": "时长控制", "checked": False}
            },
            ReviewStage.VIDEO: {
                "video_quality": {"label": "画面质量", "checked": False},
                "audio_sync": {"label": "音画同步", "checked": False},
                "style_consistency": {"label": "风格一致性", "checked": False},
                "technical_compliance": {"label": "技术合规", "checked": False}
            },
            ReviewStage.PUBLISH: {
                "completeness": {"label": "信息完整", "checked": False},
                "platform_correct": {"label": "平台正确", "checked": False},
                "schedule_correct": {"label": "时间正确", "checked": False}
            }
        }
        return checklists.get(stage, {})
```

### 3.6 成本控制模块（完善版）

#### 3.6.1 功能描述（完善）
- 实时监控API调用成本
- 设置多级告警阈值（预警、告警、熔断）
- 生成成本日报/周报/月报
- 成本预测和预算规划
- 支持按项目、按模块、按人员维度统计

#### 3.6.2 技术实现（完善）

```python
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum
import asyncio

class AlertLevel(Enum):
    WARNING = "warning"            # 预警（80%预算）
    ALERT = "alert"               # 告警（100%预算）
    CRITICAL = "critical"         # 熔断（120%预算）

@dataclass
class CostRecord:
    id: str
    api_name: str
    api_model: str
    request_type: str            # chat/video/image
    tokens_input: int
    tokens_output: int
    cost: float
    task_id: str
    created_at: datetime

class CostController:
    """成本控制器（完善版）"""
    
    # 预算配置
    DAILY_BUDGET = 1000          # 日预算（元）
    WARNING_THRESHOLD = 0.8      # 预警阈值（80%）
    ALERT_THRESHOLD = 1.0        # 告警阈值（100%）
    CRITICAL_THRESHOLD = 1.2     # 熔断阈值（120%）
    
    # API单价配置（元/千token或元/秒）
    API_PRICING = {
        "deepseek-v4": {"input": 0.002, "output": 0.008},
        "glm-5.1": {"input": 0.005, "output": 0.015},
        "seedance-2.0": {"per_second": 0.5}
    }
    
    def __init__(self):
        self.db = Database()
        self.alert = AlertService()
        self.cache = RedisClient()
        self._lock = asyncio.Lock()
    
    async def record_api_call(
        self,
        api_name: str,
        api_model: str,
        request_type: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        duration: int = 0,
        task_id: str = ""
    ):
        """
        记录API调用成本
        
        Args:
            api_name: API名称
            api_model: 模型名称
            request_type: 请求类型
            tokens_input: 输入token数
            tokens_output: 输出token数
            duration: 视频时长（秒）
            task_id: 关联任务ID
        """
        async with self._lock:
            # 1. 计算成本
            cost = self._calculate_cost(
                api_name, tokens_input, tokens_output, duration
            )
            
            # 2. 创建记录
            record = CostRecord(
                id=generate_uuid(),
                api_name=api_name,
                api_model=api_model,
                request_type=request_type,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost=cost,
                task_id=task_id,
                created_at=datetime.now()
            )
            self.db.save_cost_record(record)
            
            # 3. 更新缓存中的日成本
            today_key = f"cost:daily:{datetime.now().strftime('%Y-%m-%d')}"
            await self.cache.incrbyfloat(today_key, cost)
            await self.cache.expire(today_key, 86400 * 7)  # 保留7天
            
            # 4. 检查预算阈值
            await self._check_budget_threshold(today_key)
            
            # 5. 更新任务成本
            if task_id:
                await self._update_task_cost(task_id, cost)
    
    def _calculate_cost(
        self,
        api_name: str,
        tokens_input: int,
        tokens_output: int,
        duration: int
    ) -> float:
        """计算API调用成本"""
        pricing = self.API_PRICING.get(api_name, {})
        
        if "per_second" in pricing:
            # 视频生成按秒计费
            return duration * pricing["per_second"]
        else:
            # 文本按token计费
            input_cost = (tokens_input / 1000) * pricing.get("input", 0)
            output_cost = (tokens_output / 1000) * pricing.get("output", 0)
            return input_cost + output_cost
    
    async def _check_budget_threshold(self, today_key: str):
        """检查预算阈值"""
        daily_cost = float(await self.cache.get(today_key) or 0)
        ratio = daily_cost / self.DAILY_BUDGET
        
        if ratio >= self.CRITICAL_THRESHOLD:
            # 熔断：暂停非紧急任务
            await self.alert.send(
                level=AlertLevel.CRITICAL,
                message=f"日预算严重超支：¥{daily_cost:.2f}（{ratio*100:.1f}%）",
                action="暂停非紧急任务"
            )
            await self._pause_non_urgent_tasks()
        elif ratio >= self.ALERT_THRESHOLD:
            # 告警
            await self.alert.send(
                level=AlertLevel.ALERT,
                message=f"日预算已用完：¥{daily_cost:.2f}（{ratio*100:.1f}%）",
                action="通知负责人"
            )
        elif ratio >= self.WARNING_THRESHOLD:
            # 预警
            await self.alert.send(
                level=AlertLevel.WARNING,
                message=f"日预算即将用完：¥{daily_cost:.2f}（{ratio*100:.1f}%）",
                action="关注成本"
            )
    
    async def get_cost_report(
        self,
        start_date: str,
        end_date: str,
        group_by: str = "day"
    ) -> dict:
        """
        生成成本报表
        
        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            group_by: 分组方式（day/week/month）
        
        Returns:
            dict: 成本报表
        """
        # 1. 查询数据库
        records = self.db.get_cost_records(start_date, end_date)
        
        # 2. 按维度统计
        report = {
            "summary": {
                "total_cost": sum(r.cost for r in records),
                "total_requests": len(records),
                "avg_cost_per_request": sum(r.cost for r in records) / len(records) if records else 0
            },
            "by_api": {},
            "by_day": {},
            "by_task": {}
        }
        
        for record in records:
            # 按API统计
            api_key = f"{record.api_name}/{record.api_model}"
            if api_key not in report["by_api"]:
                report["by_api"][api_key] = {"cost": 0, "requests": 0}
            report["by_api"][api_key]["cost"] += record.cost
            report["by_api"][api_key]["requests"] += 1
            
            # 按天统计
            day = record.created_at.strftime("%Y-%m-%d")
            if day not in report["by_day"]:
                report["by_day"][day] = {"cost": 0, "requests": 0}
            report["by_day"][day]["cost"] += record.cost
            report["by_day"][day]["requests"] += 1
            
            # 按任务统计
            if record.task_id:
                if record.task_id not in report["by_task"]:
                    report["by_task"][record.task_id] = {"cost": 0}
                report["by_task"][record.task_id]["cost"] += record.cost
        
        return report
    
    async def get_realtime_cost(self) -> dict:
        """获取实时成本"""
        today = datetime.now().strftime("%Y-%m-%d")
        today_key = f"cost:daily:{today}"
        
        daily_cost = float(await self.cache.get(today_key) or 0)
        remaining = self.DAILY_BUDGET - daily_cost
        
        return {
            "today": {
                "cost": daily_cost,
                "budget": self.DAILY_BUDGET,
                "remaining": remaining,
                "usage_rate": daily_cost / self.DAILY_BUDGET
            },
            "apis": {
                api: float(await self.cache.get(f"cost:{api}:{today}") or 0)
                for api in self.API_PRICING.keys()
            }
        }
    
    async def _pause_non_urgent_tasks(self):
        """暂停非紧急任务"""
        # 实现暂停逻辑
        pass
    
    async def _update_task_cost(self, task_id: str, cost: float):
        """更新任务成本"""
        task_key = f"task:cost:{task_id}"
        await self.cache.incrbyfloat(task_key, cost)
```

#### 3.6.3 数据模型（完善）

```sql
-- 成本记录表
CREATE TABLE cost_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    api_name VARCHAR(50) NOT NULL COMMENT 'API名称',
    api_model VARCHAR(50) COMMENT '模型名称',
    request_type VARCHAR(20) COMMENT '请求类型',
    tokens_input INT DEFAULT 0 COMMENT '输入token数',
    tokens_output INT DEFAULT 0 COMMENT '输出token数',
    duration INT DEFAULT 0 COMMENT '视频时长（秒）',
    cost DECIMAL(10, 6) NOT NULL COMMENT '成本（元）',
    task_id VARCHAR(36) COMMENT '关联任务ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_api_name (api_name),
    INDEX idx_task_id (task_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成本记录表';

-- 预算配置表
CREATE TABLE budget_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    budget_type VARCHAR(20) COMMENT 'daily/weekly/monthly',
    budget_amount DECIMAL(10, 2) COMMENT '预算金额',
    warning_threshold DECIMAL(5, 2) DEFAULT 0.8 COMMENT '预警阈值',
    alert_threshold DECIMAL(5, 2) DEFAULT 1.0 COMMENT '告警阈值',
    critical_threshold DECIMAL(5, 2) DEFAULT 1.2 COMMENT '熔断阈值',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预算配置表';

-- 告警记录表
CREATE TABLE alert_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    alert_level VARCHAR(20) COMMENT 'warning/alert/critical',
    message TEXT COMMENT '告警内容',
    action VARCHAR(200) COMMENT '执行动作',
    notified_users JSON COMMENT '通知用户',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_level (alert_level),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警记录表';
```

---

## 四、实施计划清单（完善版）

### 4.1 项目里程碑（完善）

| 阶段 | 时间 | 目标 | 交付物 | 验收标准 | 风险点 |
|------|------|------|--------|----------|--------|
| **Phase 0** | 第1-2周 | 技术验证 | 《技术验证报告》 | 所有API连通性测试通过；视频生成质量可接受 | Seedance效果不达预期 |
| **Phase 1** | 第3-6周 | MVP开发 | 最小可行产品 | 核心流程跑通；日产1-2条视频 | 开发进度延迟 |
| **Phase 2** | 第7-14周 | 功能完善 | Beta版本 | 系统稳定运行；日产3-5条视频 | 测试不充分 |
| **Phase 3** | 第15-22周 | 单平台验证 | 《盈利验证报告》 | 单平台盈利；ROI≥1.5 | 平台政策变化 |
| **Phase 4** | 第23周+ | 迭代优化 | 正式版本 | 日产5-10条精品；月度盈利 | 竞争加剧 |

### 4.2 详细任务分解（完善版）

#### Phase 0：技术验证（第1-2周）

| 任务编号 | 任务名称 | 负责人 | 工期 | 依赖 | 输出 | 验收标准 |
|----------|----------|--------|------|------|------|----------|
| T001 | 搭建开发环境 | 技术负责人 | 2天 | - | 环境文档 | Docker Compose可一键启动 |
| T002 | 验证DeepSeek-V4 API | 技术负责人 | 2天 | T001 | 测试脚本 | 响应时间<3秒；JSON格式正确 |
| T003 | 验证GLM-5.1 API | 技术负责人 | 2天 | T001 | 测试脚本 | 脚本生成质量可接受 |
| T004 | 验证Seedance 2.0 API | 技术负责人 | 3天 | T001 | 测试视频 | 视频质量≥60分；生成时间<10分钟 |
| T005 | 验证OpenClaw调度 | 技术负责人 | 2天 | T001 | 测试任务 | 定时任务正常执行 |
| T006 | 编写技术验证报告 | 技术负责人 | 1天 | T002-T005 | 验证报告 | 所有测试通过 |

**交付物：** 《技术验证报告》
**Go/No-Go标准：** Seedance 2.0视频质量≥60分，否则项目终止或更换方案

#### Phase 1：MVP开发（第3-6周）

| 任务编号 | 任务名称 | 负责人 | 工期 | 依赖 | 输出 | 验收标准 |
|----------|----------|--------|------|------|------|----------|
| T007 | 数据库设计 | 技术负责人 | 3天 | T006 | ER图、DDL | 满足所有需求；索引合理 |
| T008 | 热点采集模块开发 | 技术负责人 | 5天 | T007 | 采集服务 | 支持3平台；日采集100条 |
| T009 | AI分析模块开发 | 技术负责人 | 5天 | T007 | 分析服务 | 分析时间<30秒 |
| T010 | 脚本生成模块开发 | 技术负责人 | 5天 | T007 | 生成服务 | 生成时间<60秒 |
| T011 | 视频生成模块开发 | 技术负责人 | 5天 | T007 | 生成服务 | 异步处理正常；回调可用 |
| T012 | 人工审核界面开发 | 技术负责人 | 5天 | T007 | Web界面 | 审核流程完整；操作便捷 |
| T013 | 成本控制模块开发 | 技术负责人 | 3天 | T007 | 监控服务 | 实时成本可见；告警正常 |
| T014 | 系统集成测试 | 技术负责人 | 3天 | T008-T013 | 测试报告 | 核心流程100%通过 |

**交付物：** MVP版本系统
**Go/No-Go标准：** 端到端流程跑通，单条视频制作时间<2小时

#### Phase 2：功能完善（第7-14周）

| 任务编号 | 任务名称 | 负责人 | 工期 | 依赖 | 输出 | 验收标准 |
|----------|----------|--------|------|------|------|----------|
| T015 | 发布管理模块开发 | 技术负责人 | 5天 | T014 | 发布服务 | 支持3平台；人工确认后发布 |
| T016 | 数据监控模块开发 | 技术负责人 | 5天 | T014 | 监控服务 | 数据可视化；周报自动生成 |
| T017 | 用户权限管理 | 技术负责人 | 3天 | T014 | 权限服务 | RBAC模型；操作日志完整 |
| T018 | 日志监控系统 | 技术负责人 | 3天 | T014 | 监控面板 | 日志可检索；告警可配置 |
| T019 | 性能优化 | 技术负责人 | 5天 | T015-T018 | 优化报告 | API响应<2秒；并发支持10 |
| T020 | 安全加固 | 技术负责人 | 3天 | T019 | 安全报告 | 无高危漏洞；数据加密 |
| T021 | Beta测试 | 全员 | 10天 | T020 | 测试报告 | Bug修复率100% |
| T022 | Bug修复 | 技术负责人 | 5天 | T021 | 修复版本 | 无P0/P1 Bug |

**交付物：** Beta版本系统
**Go/No-Go标准：** 系统稳定运行72小时无故障

#### Phase 3：单平台验证（第15-22周）

| 任务编号 | 任务名称 | 负责人 | 工期 | 依赖 | 输出 | 验收标准 |
|----------|----------|--------|------|------|------|----------|
| T023 | 选定验证平台 | 内容运营 | 2天 | T022 | 平台方案 | 平台选择依据充分 |
| T024 | 内容策略制定 | 内容运营 | 3天 | T023 | 内容策略 | 垂直领域明确；差异化清晰 |
| T025 | 每日内容生产 | 内容运营 | 30天 | T024 | 内容库 | 日产3-5条；通过率≥80% |
| T026 | 数据收集分析 | 数据分析 | 30天 | T024 | 数据报表 | 数据完整；指标可追踪 |
| T027 | 成本效益分析 | 数据分析 | 5天 | T026 | 分析报告 | ROI计算准确 |
| T028 | 优化迭代 | 全员 | 10天 | T027 | 优化版本 | 关键指标提升≥20% |

**交付物：** 《单平台盈利验证报告》
**Go/No-Go标准：** 单平台月度盈利≥5000元，ROI≥1.5

#### Phase 4：迭代优化（第23周+）

| 任务编号 | 任务名称 | 负责人 | 工期 | 依赖 | 输出 | 验收标准 |
|----------|----------|--------|------|------|------|----------|
| T029 | 多平台适配 | 技术负责人 | 10天 | T028 | 多平台版本 | 支持3平台发布 |
| T030 | 自动化程度提升 | 技术负责人 | 15天 | T029 | 自动化功能 | 审核效率提升50% |
| T031 | 功能扩展 | 技术负责人 | 15天 | T030 | 扩展功能 | 内容库管理；数据分析增强 |
| T032 | 正式版本发布 | 全员 | 5天 | T031 | 正式版本 | 文档完整；培训完成 |

**交付物：** 正式版本系统

### 4.3 资源计划（完善版）

#### 人力资源（完善）

| 角色 | 人数 | 职责 | 投入时间 | 技能要求 | 成本（月） |
|------|------|------|----------|----------|-----------|
| 技术负责人 | 1 | 系统架构、核心开发、运维 | 全职 | Python/FastAPI/K8s/AI API | 15,000-20,000 |
| 内容运营 | 1 | 热点追踪、内容策划、发布 | 全职 | 短视频创作/平台规则 | 8,000-12,000 |
| 内容审核员 | 1 | 内容审核、质量把控 | 全职 | 内容敏感度/审核经验 | 6,000-8,000 |
| 数据分析 | 1 | 数据监控、效果分析、报表 | 兼职（50%） | 数据分析/可视化 | 4,000-6,000 |
| **合计** | **4人** | | | | **33,000-46,000** |

#### 技术资源（完善）

| 资源 | 规格 | 数量 | 月度成本 | 用途 | 供应商 |
|------|------|------|----------|------|--------|
| 云服务器 | 8核16G | 2台 | 2,000元 | API服务/Web服务 | 阿里云/腾讯云 |
| GPU服务器 | 显存16G | 1台 | 3,000元 | 视频处理（如有本地渲染需求） | 阿里云/腾讯云 |
| 对象存储 | 标准存储 | 1TB | 500元 | 视频/图片存储 | 阿里云OSS |
| 数据库 | MySQL 8.0 | 1实例 | 500元 | 数据存储 | 云托管RDS |
| Redis | 4G内存 | 1实例 | 300元 | 缓存/队列 | 云托管Redis |
| CDN | 按流量 | - | 500元 | 视频加速 | 阿里云CDN |
| 域名/SSL | - | 1个 | 100元 | 域名和证书 | 阿里云 |
| **合计** | | | **6,900元** | | |

#### API资源（完善）

| API | 用途 | 预估月调用量 | 单价 | 月度成本 | 备注 |
|-----|------|-------------|------|----------|------|
| DeepSeek-V4 | 内容分析 | 1,000次 | ¥0.01/千token | 1,000元 | 按token计费 |
| GLM-5.1 | 脚本生成 | 2,000次 | ¥0.02/千token | 2,000元 | 按token计费 |
| Seedance 2.0 | 视频生成 | 300次 | ¥0.5/秒 | 15,000元 | 按秒计费；15秒视频 |
| 平台官方API | 发布/数据 | 500次 | 免费 | 0元 | 目前免费 |
| **合计** | | | | **18,000元** | |

#### 月度成本汇总（完善）

| 成本项 | 月度成本 | 占比 | 说明 |
|--------|----------|------|------|
| 人力成本 | 33,000-46,000 | 55-65% | 4人团队 |
| 技术资源 | 6,900 | 8-10% | 服务器/存储/CDN |
| API成本 | 18,000 | 25-30% | AI服务调用 |
| 其他（办公、测试等） | 2,000 | 3-5% | 杂项 |
| **总计** | **59,900-72,900** | 100% | |

**注：** 此成本为正式运营后的预估，MVP阶段可压缩至20,000-30,000元/月

### 4.4 风险管理（完善版）

#### 4.4.1 风险登记册

| 风险编号 | 风险描述 | 概率 | 影响 | 风险等级 | 应对措施 | 责任人 | 状态 |
|----------|----------|------|------|----------|----------|--------|------|
| R001 | Seedance 2.0效果不达预期 | 中 | 高 | **高** | 1. Phase 0充分PoC验证；2. 准备备选方案（可灵/Runway）；3. 调整预期为"AI素材+人工剪辑" | 技术负责人 | 开放 |
| R002 | 平台政策变化（反爬/封号） | 高 | 高 | **高** | 1. 100%人工审核后发布；2. 使用官方API；3. 控制发布频率；4. 多账号分散风险 | 内容运营 | 开放 |
| R003 | 成本超支 | 中 | 中 | **中** | 1. 实时成本监控；2. 日预算告警；3. 优化Prompt减少token；4. 控制视频时长 | 技术负责人 | 开放 |
| R004 | 内容审核不通过率高 | 高 | 中 | **中** | 1. 建立审核标准库；2. AI预审+人工终审；3. 内容运营培训；4. 预留修改时间 | 审核员 | 开放 |
| R005 | 团队人员变动 | 低 | 中 | **低** | 1. 完善技术文档；2. 代码规范；3. 知识沉淀；4. 交叉培训 | 技术负责人 | 开放 |
| R006 | 竞品挤压（AI内容泛滥） | 高 | 中 | **中** | 1. 垂直领域深耕；2. 差异化内容策略；3. 快速迭代；4. 建立品牌壁垒 | 内容运营 | 开放 |
| R007 | 技术债务累积 | 中 | 中 | **中** | 1. 代码审查；2. 单元测试；3. 定期重构；4. 技术债跟踪 | 技术负责人 | 开放 |
| R008 | 数据安全事件 | 低 | 高 | **中** | 1. 数据加密；2. 访问控制；3. 定期审计；4. 备份策略 | 技术负责人 | 开放 |

#### 4.4.2 风险应对策略

| 策略类型 | 适用风险 | 具体措施 |
|----------|----------|----------|
| **规避** | R002（平台政策） | 完全放弃全自动发布，改为人工确认后发布 |
| **转移** | R008（数据安全） | 购买网络安全保险；使用云服务商的安全服务 |
| **减轻** | R001（Seedance效果） | Phase 0充分验证；准备备选方案；调整预期 |
| **接受** | R005（人员变动） | 建立文档和知识库；接受一定的人员流动风险 |
| **储备** | R003（成本超支） | 预留20%应急预算；设置多级告警阈值 |

### 4.5 质量保证（完善版）

#### 4.5.1 质量门禁

| 阶段 | 门禁检查项 | 通过标准 | 检查人 |
|------|-----------|----------|--------|
| 代码提交 | 代码审查 | 无严重问题；覆盖率>80% | 技术负责人 |
| 模块完成 | 单元测试 | 测试用例通过率100% | 开发工程师 |
| 集成完成 | 集成测试 | 核心流程100%通过 | 测试工程师 |
| 版本发布 | 性能测试 | API响应<2秒；并发支持10 | 技术负责人 |
| 版本发布 | 安全扫描 | 无高危漏洞 | 安全工程师 |
| 上线前 | 用户验收 | 核心需求100%满足 | 产品经理 |

#### 4.5.2 测试策略

| 测试类型 | 测试内容 | 工具 | 执行人 | 频率 |
|----------|----------|------|--------|------|
| 单元测试 | 函数/方法正确性 | pytest | 开发工程师 | 每次提交 |
| 集成测试 | 模块间接口 | pytest + httpx | 测试工程师 | 每日构建 |
| 性能测试 | API响应时间/并发 | locust | 测试工程师 | 每周 |
| 安全测试 | 漏洞扫描 | OWASP ZAP | 安全工程师 | 每月 |
| 用户测试 | 易用性/功能完整性 | 人工 | 内容运营 | 每版本 |
| 回归测试 | 历史功能 | 自动化脚本 | 测试工程师 | 每版本发布前 |

#### 4.5.3 监控指标

| 指标类别 | 指标名称 | 目标值 | 告警阈值 |
|----------|----------|--------|----------|
| **系统性能** | API响应时间 | <2秒 | >3秒 |
| | 系统可用性 | ≥99.5% | <99% |
| | 错误率 | <0.1% | >0.5% |
| **业务指标** | 日产量 | 5-10条 | <3条 |
| | 审核通过率 | ≥80% | <70% |
| | 单条成本 | ≤50元 | >60元 |
| | 视频生成成功率 | ≥95% | <90% |
| **成本指标** | 日API成本 | ≤1000元 | >1200元 |
| | 月度总成本 | ≤30,000元 | >35,000元 |

---

## 五、附录（完善版）

### 5.1 技术栈清单（完善）

| 层级 | 技术 | 版本 | 用途 | 选型理由 |
|------|------|------|------|----------|
| **后端语言** | Python | 3.11+ | 核心业务逻辑 | AI生态丰富；开发效率高 |
| **Web框架** | FastAPI | 0.100+ | Web服务 | 高性能；异步支持；自动生成文档 |
| **数据库** | MySQL | 8.0 | 数据存储 | 成熟稳定；事务支持 |
| **缓存** | Redis | 7.0 | 缓存/队列/实时数据 | 高性能；支持多种数据结构 |
| **消息队列** | RabbitMQ | 3.12+ | 异步任务 | 可靠；支持延迟队列 |
| **任务调度** | Celery | 5.3+ | 定时任务/异步处理 | 与Python生态集成好 |
| **前端框架** | Vue.js | 3.3+ | 管理界面 | 组件化；生态丰富 |
| **UI组件库** | Element Plus | 2.3+ | 界面组件 | 与Vue3兼容；组件丰富 |
| **容器化** | Docker | 24.0+ | 应用容器化 | 环境一致性；易于部署 |
| **编排** | Kubernetes | 1.28+ | 容器编排 | 高可用；弹性伸缩 |
| **网关** | Nginx | 1.24+ | 反向代理/负载均衡 | 高性能；稳定 |
| **监控** | Prometheus | 2.47+ | 指标采集 | 云原生标准 |
| **可视化** | Grafana | 10.0+ | 监控面板 | 美观；插件丰富 |
| **日志** | ELK Stack | 8.x | 日志收集分析 | 功能完整 |
| **配置中心** | Nacos | 2.2+ | 配置管理 | 动态配置；服务发现 |
| **AI服务** | DeepSeek-V4 | API | 内容分析 | 推理能力强 |
| **AI服务** | GLM-5.1 | API | 脚本生成 | 长程任务执行好 |
| **AI服务** | Seedance 2.0 | API | 视频生成 | 即梦AI技术基础 |
| **对象存储** | 阿里云OSS | - | 视频/图片存储 | 国内访问快；成本低 |
| **CDN** | 阿里云CDN | - | 内容分发 | 国内节点多 |

### 5.2 项目文档清单（完善）

| 文档 | 责任人 | 完成时间 | 模板 | 审批人 |
|------|--------|----------|------|--------|
| 《需求规格说明书》 | 技术负责人 | Phase 0 | 公司模板 | 项目经理 |
| 《系统设计文档》 | 技术负责人 | Phase 1 | 公司模板 | 技术总监 |
| 《数据库设计文档》 | 技术负责人 | Phase 1 | 公司模板 | 技术总监 |
| 《接口文档》 | 技术负责人 | Phase 1 | Swagger自动生成 | 技术总监 |
| 《测试计划》 | 测试工程师 | Phase 1 | 公司模板 | 项目经理 |
| 《测试报告》 | 测试工程师 | Phase 2 | 公司模板 | 项目经理 |
| 《部署文档》 | 技术负责人 | Phase 2 | 公司模板 | 运维负责人 |
| 《操作手册》 | 内容运营 | Phase 3 | 公司模板 | 项目经理 |
| 《盈利验证报告》 | 数据分析 | Phase 3 | 公司模板 | 项目经理 |
| 《项目总结报告》 | 项目经理 | Phase 4 | 公司模板 | 技术总监 |

### 5.3 会议计划

| 会议 | 频率 | 参与人 | 时长 | 输出 |
|------|------|--------|------|------|
| 每日站会 | 每日 | 全员 | 15分钟 | 昨日进展/今日计划/阻塞问题 |
| 周会 | 每周 | 全员 | 1小时 | 周总结/下周计划/风险同步 |
| 评审会 | 每阶段末 | 全员+领导 | 2小时 | 阶段评审/Go-NoGo决策 |
| 复盘会 | 每阶段末 | 全员 | 1小时 | 经验教训/改进措施 |

### 5.4 沟通计划

| 沟通方式 | 用途 | 工具 | 响应时间 |
|----------|------|------|----------|
| 即时通讯 | 日常沟通 | 钉钉/飞书 | 工作时间内 |
| 邮件 | 正式通知/报告 | 企业邮箱 | 24小时内 |
| 文档协作 | 需求/设计文档 | 语雀/Notion | 按需 |
| 项目管理 | 任务跟踪 | Jira/禅道 | 每日更新 |
| 代码管理 | 版本控制 | GitLab/GitHub | 及时 |

---

**编制：** 需求分析师  
**审核：** [待填写]  
**批准：** [待填写]  
**日期：** 2026年5月26日
