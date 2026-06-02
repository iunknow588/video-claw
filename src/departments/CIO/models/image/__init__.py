"""
Image generation task model.
"""

from sqlalchemy import Column, ForeignKey, Index, Integer, JSON, Numeric, String, Text

from departments.CIO.models.base import BaseModel


class ImageTask(BaseModel):
    """Image generation task."""

    __tablename__ = "image_tasks"

    script_id = Column(String(36), ForeignKey("scripts.uuid"), nullable=True, comment="Related script ID")
    status = Column(String(20), default="pending", comment="Status")
    provider_name = Column(String(50), comment="Image provider name")
    provider_task_id = Column(String(100), comment="Provider-side task ID")
    prompt = Column(Text, comment="Generation prompt")
    negative_prompt = Column(Text, comment="Negative prompt")
    aspect_ratio = Column(String(20), comment="Aspect ratio")
    resolution = Column(String(20), comment="Resolution profile")
    image_count = Column(Integer, default=1, comment="Requested image count")
    image_urls = Column(JSON, comment="Generated image URLs")
    primary_image_url = Column(String(500), comment="Primary image URL")
    request_payload = Column(JSON, comment="Provider request payload")
    result_payload = Column(JSON, comment="Provider result payload")
    error_message = Column(Text, comment="Error message")
    api_cost = Column(Numeric(10, 4), comment="API call cost")
    completed_at = Column(String(50), comment="Completion timestamp")

    __table_args__ = (
        Index("ix_image_tasks_script_id", "script_id"),
        Index("ix_image_tasks_status", "status"),
        Index("ix_image_tasks_created_at", "created_at"),
        {"comment": "Image generation tasks"},
    )
