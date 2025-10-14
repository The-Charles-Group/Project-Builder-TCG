"""
Database models for Learning Brain confidence adjustment system
"""
from __future__ import annotations
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class OperatingMode(str, Enum):
    """Operating modes for the Learning Brain system"""
    OFF = "off"
    SHADOW = "shadow"
    ACTIVE = "active"


class ConfidenceAdjustment(BaseModel):
    """Model for confidence adjustment feedback"""
    id: Optional[int] = None
    deliverable_code: str
    deliverable_name: str
    original_confidence: float = Field(ge=0.0, le=1.0)
    adjusted_confidence: float = Field(ge=0.0, le=1.0)
    reason: Optional[str] = None
    notes: Optional[str] = None
    admin_user: Optional[str] = None
    timestamp: Optional[datetime] = None
    episode_id: Optional[int] = None
    applied: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ModeChange(BaseModel):
    """Model for tracking mode changes"""
    id: Optional[int] = None
    from_mode: OperatingMode
    to_mode: OperatingMode
    admin_user: Optional[str] = None
    timestamp: Optional[datetime] = None
    reason: Optional[str] = None


class FeedbackPayload(BaseModel):
    """Payload for submitting confidence adjustments"""
    deliverable_code: str
    deliverable_name: str
    original_confidence: float = Field(ge=0.0, le=1.0)
    adjusted_confidence: float = Field(ge=0.0, le=1.0)
    reason: Optional[str] = None
    notes: Optional[str] = None


class ModeChangePayload(BaseModel):
    """Payload for changing operating mode"""
    mode: OperatingMode
    reason: Optional[str] = None


class BulkFeedbackPayload(BaseModel):
    """Payload for submitting multiple confidence adjustments"""
    adjustments: List[FeedbackPayload]
    apply_immediately: bool = False


class ConfidenceBlendPayload(BaseModel):
    """Payload for blending AI scores with learned adjustments"""
    base_scores: Dict[str, float]
    rfp_text: Optional[str] = None
    use_draft: bool = False


class StatusResponse(BaseModel):
    """Response model for status endpoint"""
    mode: OperatingMode
    total_adjustments: int
    pending_adjustments: int
    published_adjustments: int
    last_mode_change: Optional[datetime] = None
    last_adjustment: Optional[datetime] = None
    statistics: Dict[str, Any] = Field(default_factory=dict)


class AdjustmentHistoryResponse(BaseModel):
    """Response model for adjustment history"""
    adjustments: List[ConfidenceAdjustment]
    total: int
    page: int
    page_size: int


class ResetResponse(BaseModel):
    """Response model for reset operations"""
    success: bool
    message: str
    cleared_adjustments: int
    cleared_episodes: int