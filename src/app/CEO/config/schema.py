from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AppIdentityConfig(BaseModel):
    name: str = "AI Video Auto Production Line"
    version: str = "1.0.0"
    debug: bool = False
    env: str = "development"


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: Literal["json", "console"] = "json"
    file: str = "runtime/logs/app.log"
    max_bytes: int = Field(default=10485760, ge=1)
    backup_count: int = Field(default=5, ge=0)


class MonitoringConfig(BaseModel):
    prometheus_enabled: bool = True
    metrics_port: int = Field(default=9090, ge=1, le=65535)
    health_check_interval: int = Field(default=30, ge=1)


class ApplicationGovernanceConfig(BaseModel):
    app: AppIdentityConfig
    server: ServerConfig
    logging: LoggingConfig
    monitoring: MonitoringConfig


class PermissionMatrixConfig(BaseModel):
    domain_permissions: dict[str, list[str]] = Field(default_factory=dict)
    dynamic_keys: list[str] = Field(default_factory=list)


class DepartmentsGovernanceConfig(BaseModel):
    owners: dict[str, str] = Field(default_factory=dict)


class LeaderResourceAllocationConfig(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_quota: str = "standard"
    parallelism: int = Field(default=1, ge=1)


class LeaderDefaultsConfig(BaseModel):
    display_name: str
    description: str
    model: str
    bound_tools: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    token_limit: int = Field(ge=1)
    resource_allocations: LeaderResourceAllocationConfig = Field(default_factory=LeaderResourceAllocationConfig)


class ControlPlaneLeadersConfig(BaseModel):
    mission: str
    scope: str
    leaders: dict[str, LeaderDefaultsConfig] = Field(default_factory=dict)


class WorkflowEdgeConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_leader: str = Field(alias="from")
    to_leader: str = Field(alias="to")


class WorkflowConditionalEdgeConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_leader: str = Field(alias="from")
    router_func: str
    strategy: str = "balanced"
    mapping: dict[str, str] = Field(default_factory=dict)


class WorkflowQAReworkConfig(BaseModel):
    max_attempts: int = Field(default=1, ge=0)


class WorkflowGovernanceConfig(BaseModel):
    version: int = Field(default=1, ge=1)
    dispatch_mode: str = "graph"
    main_route: list[str] = Field(default_factory=list)
    edges: list[WorkflowEdgeConfig] = Field(default_factory=list)
    conditional_edges: list[WorkflowConditionalEdgeConfig] = Field(default_factory=list)
    parallel_groups: list[Any] = Field(default_factory=list)
    qa_rework: WorkflowQAReworkConfig = Field(default_factory=WorkflowQAReworkConfig)
