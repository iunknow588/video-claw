"""
Analysis Report Model
"""

from sqlalchemy import Column, String, Text, JSON, Numeric, ForeignKey, Index
from sqlalchemy.dialects.mysql import BIGINT

from departments.CIO.models.base import BaseModel


class AnalysisReport(BaseModel):
    """AI analysis report"""
    __tablename__ = "analysis_reports"
    
    hotspot_id = Column(String(36), ForeignKey("hotspot_items.uuid"), nullable=False, comment="Related hotspot ID")
    analysis_type = Column(String(20), default="comprehensive", comment="Analysis type")
    content_structure = Column(JSON, comment="Content structure")
    emotion_curve = Column(JSON, comment="Emotion curve")
    hook_design = Column(JSON, comment="Hook design")
    framework_summary = Column(Text, comment="Framework summary")
    reusable_elements = Column(JSON, comment="Reusable elements")
    risk_warnings = Column(JSON, comment="Risk warnings")
    api_cost = Column(Numeric(10, 4), comment="API call cost")
    
    __table_args__ = (
        Index("ix_analysis_reports_hotspot_id", "hotspot_id"),
        Index("ix_analysis_reports_created_at", "created_at"),
        {"comment": "AI analysis reports"},
    )

    @property
    def report_title(self) -> str:
        return "爆款DNA报告"

    @property
    def dna_report(self) -> dict:
        return {
            "content_structure": self.content_structure if self.content_structure is not None else {},
            "emotion_curve": self.emotion_curve if self.emotion_curve is not None else {},
            "hook_design": self.hook_design if self.hook_design is not None else {},
            "framework_summary": self.framework_summary or "",
            "reusable_elements": list(self.reusable_elements or []),
            "risk_warnings": list(self.risk_warnings or []),
        }
