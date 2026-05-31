"""
Database Models - Base Class
"""

import uuid
from typing import Any

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

PrimaryKeyType = BigInteger().with_variant(Integer, "sqlite")


class BaseModel(Base):
    """Base model with common fields"""
    __abstract__ = True
    
    id = Column(PrimaryKeyType, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
