"""
CIO system setting persistence model.
"""

from sqlalchemy import Column, Index, JSON, String

from departments.CIO.models.base import BaseModel


class SystemSettingRecord(BaseModel):
    """Stores CIO-managed system settings."""

    __tablename__ = "system_settings"

    setting_key = Column(String(120), nullable=False, unique=True, comment="Setting key")
    payload = Column(JSON, nullable=False, comment="Setting payload")

    __table_args__ = (
        Index("ix_system_settings_setting_key", "setting_key"),
        {"comment": "CIO system settings"},
    )
