"""
Pydantic Schemas for API
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Hotspot Schemas ---
class HotspotCreate(BaseModel):
    platform: str
    content_id: str
    title: Optional[str] = None
    author: Optional[str] = None
    author_id: Optional[str] = None
    url: Optional[str] = None
    cover_image: Optional[str] = None
    video_url: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    duration: Optional[int] = None
    fetched_at: Optional[str] = None


class HotspotFetchRequest(BaseModel):
    platform: str = Field(..., description="douyin / xiaohongshu / bilibili")
    keyword: str = Field(..., min_length=1, max_length=100)
    count: int = Field(default=10, ge=1, le=50)

class HotspotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    platform: str
    content_id: str
    title: Optional[str]
    author: Optional[str]
    view_count: int
    like_count: int
    category: Optional[str]
    created_at: datetime


# --- Analysis Schemas ---
class AnalysisCreate(BaseModel):
    hotspot_id: str
    analysis_type: str = "comprehensive"

class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    hotspot_id: str
    analysis_type: str
    framework_summary: Optional[str]
    api_cost: Optional[float]
    created_at: datetime


# --- Script Schemas ---
class ScriptCreate(BaseModel):
    analysis_id: str
    content_type: str
    style: str
    topic: str
    duration: int = Field(default=60, ge=5, le=180)
    title: Optional[str] = None
    scenes: Optional[List[dict]] = None
    hook: Optional[str] = None
    cta: Optional[str] = None

class ScriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    analysis_id: str
    title: str
    topic: str
    duration: int
    status: str
    version: int
    created_at: datetime


# --- Video Task Schemas ---
class VideoTaskCreate(BaseModel):
    script_id: str
    style: str
    size: str = "1080x1920"
    duration: Optional[int] = None
    prompt: Optional[str] = None


class ScriptReviewRequest(BaseModel):
    approved: bool
    feedback: str = ""


class VideoReviewRequest(BaseModel):
    approved: bool
    feedback: str = ""


class OperationsSummaryResponse(BaseModel):
    counts: Dict[str, int]
    script_status: Dict[str, int]
    video_status: Dict[str, int]
    cost_breakdown: Dict[str, float]
    daily_budget: float
    budget_usage_ratio: float
    generated_at: datetime


class StorageStatusResponse(BaseModel):
    backend: str
    configured: bool
    media_url_prefix: Optional[str] = None
    recommended_for_current_stage: Optional[str] = None
    media_root: Optional[str] = None
    public_base_url: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    release_tag: Optional[str] = None
    ipfs_api_url: Optional[str] = None
    ipfs_gateway_url: Optional[str] = None
    pin_on_add: Optional[bool] = None
    bucket: Optional[str] = None
    endpoint_url: Optional[str] = None
    region: Optional[str] = None
    object_prefix: Optional[str] = None
    note: Optional[str] = None


class VideoTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    script_id: str
    status: str
    progress: float
    video_url: Optional[str]
    api_cost: Optional[float]
    created_at: datetime


class ReviewRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    item_type: str
    item_uuid: str
    stage: str
    approved: bool
    reviewer: Optional[str]
    feedback: Optional[str]
    status_before: Optional[str]
    status_after: Optional[str]
    created_at: datetime


class WorkflowStepLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    trace_id: str
    parent_id: Optional[str] = None
    skill_name: str
    event_type: str
    status: str
    input_json: Optional[Dict[str, Any]] = None
    output_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    cost: int
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class CostRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    uuid: str
    source_type: str
    source_uuid: str
    provider: str
    model_name: str
    amount: float
    currency: str
    usage_type: str
    created_at: datetime


class DomainWorkflowRequest(BaseModel):
    domain: str = Field(..., min_length=1, max_length=100, description="目标内容领域")
    platform: str = Field(..., description="douyin / xiaohongshu / bilibili")
    hotspot_count: int = Field(default=12, ge=3, le=50)
    top_n: int = Field(default=3, ge=1, le=10)
    content_type: str = Field(default="knowledge")
    style: str = Field(default="clean")
    video_style: Optional[str] = Field(default="realistic")
    duration: int = Field(default=30, ge=5, le=180)
    audience: Optional[str] = None
    publish_goal: Optional[str] = None
    auto_approve_script: bool = False
    auto_generate_video: bool = False


class CEOChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class CEOLeaderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    config: Dict[str, Any] = Field(default_factory=dict)


class CEOLeaderUpdateRequest(BaseModel):
    config: Dict[str, Any] = Field(default_factory=dict)


class CEORollbackRequest(BaseModel):
    version: int = Field(..., ge=1)


class CEOWorkflowUpdateRequest(BaseModel):
    graph_definition: Dict[str, Any]


class CEOWorkflowEdgeRequest(BaseModel):
    from_leader: str
    to_leader: str


class CEOConditionalEdgeRequest(BaseModel):
    from_leader: str
    router_func: str
    mapping: Dict[str, str]


class CEOOptimizeCommandRequest(BaseModel):
    target_metric: str
    goal_value: Any
    note: Optional[str] = None


class CEOLeaderProposalRequest(BaseModel):
    proposal: Dict[str, Any]


class CEOBudgetRequest(BaseModel):
    token_limit: int = Field(..., ge=1)


class CEOResourceAdjustRequest(BaseModel):
    resource_type: str
    amount: Any


class CEOReportCollectRequest(BaseModel):
    cadence: str = Field(default="daily", min_length=1, max_length=30)


class SkillDescriptorResponse(BaseModel):
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    tags: List[str]
    default_config: Dict[str, Any]
    retry_policy: Dict[str, Any]
    dependencies: List[str]
    required_tokens: List[str]
    methods: List[str]
    streamable: bool


class DomainWorkflowHotspotResponse(BaseModel):
    uuid: str
    title: Optional[str] = None
    platform: str
    heat_score: int
    view_count: int
    like_count: int


class PromptPackageResponse(BaseModel):
    selected_hotspot_ids: List[str]
    core_keywords: List[str]
    hook_keywords: List[str]
    visual_keywords: List[str]
    title_candidates: List[str]
    prompt_summary: str
    script_topic: str
    video_prompt: str


class DomainWorkflowResponse(BaseModel):
    domain: str
    platform: str
    workflow_run_id: Optional[str] = None
    trace_id: Optional[str] = None
    finance_bundle: Optional[Dict[str, Any]] = None
    expanded_queries: List[str]
    selected_hotspots: List[DomainWorkflowHotspotResponse]
    prompt_package: PromptPackageResponse
    analysis_ids: List[str]
    script_id: str
    script_status: str
    qa_status: Optional[str] = None
    video_task_id: Optional[str] = None
    video_status: Optional[str] = None
    video_url: Optional[str] = None
    workflow_notes: List[str]
    ceo_plan: Optional[Dict[str, Any]] = None
    lead_route_list: Optional[List[str]] = None
    research_bundle: Optional[Dict[str, Any]] = None
    analysis_bundle: Optional[Dict[str, Any]] = None
    prompt_bundle: Optional[Dict[str, Any]] = None
    production_bundle: Optional[Dict[str, Any]] = None
    qa_bundle: Optional[Dict[str, Any]] = None
    publish_bundle: Optional[Dict[str, Any]] = None


class WorkflowRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    trace_id: Optional[str] = None
    workflow_type: str
    domain: str
    platform: str
    status: str
    audience: Optional[str] = None
    publish_goal: Optional[str] = None
    content_type: Optional[str] = None
    style: Optional[str] = None
    video_style: Optional[str] = None
    duration: Optional[int] = None
    expanded_queries: Optional[List[str]] = None
    selected_hotspot_ids: Optional[List[str]] = None
    prompt_package: Optional[Dict[str, Any]] = None
    analysis_ids: Optional[List[str]] = None
    script_id: Optional[str] = None
    video_task_id: Optional[str] = None
    result_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime


class WorkflowTraceResponse(BaseModel):
    run: WorkflowRunResponse
    steps: List[WorkflowStepLogResponse]
    summary: Dict[str, Any]
