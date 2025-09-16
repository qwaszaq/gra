"""
Database models for Admin Service.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

Base = declarative_base()


class AdminLog(Base):
    """Admin log entry model."""
    __tablename__ = "admin_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(20), nullable=False, index=True)  # info, warning, error
    service = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    session_id = Column(String(100), nullable=True, index=True)
    turn_id = Column(String(50), nullable=True, index=True)
    player = Column(String(100), nullable=True, index=True)
    action = Column(String(50), nullable=True, index=True)
    extra_data = Column(JSON, nullable=True)  # Additional structured data


class GameSession(Base):
    """Game session tracking model."""
    __tablename__ = "game_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(20), default="active", index=True)  # active, completed, abandoned
    player_count = Column(Integer, default=0)
    scenario = Column(String(50), nullable=True, index=True)
    extra_data = Column(JSON, nullable=True)


class GameTurn(Base):
    """Game turn tracking model."""
    __tablename__ = "game_turns"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    turn_id = Column(String(50), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    status = Column(String(20), default="active", index=True)  # active, completed, timeout
    actions_count = Column(Integer, default=0)
    narrative_generated = Column(String(10), default="false", index=True)  # true/false
    extra_data = Column(JSON, nullable=True)


# Pydantic models for API requests/responses
class LogEntryRequest(BaseModel):
    """Request model for logging entries."""
    level: str
    message: str
    service: str
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    player: Optional[str] = None
    action: Optional[str] = None
    extra_data: Optional[dict] = None


class LogEntryResponse(BaseModel):
    """Response model for log entries."""
    id: int
    timestamp: datetime
    level: str
    service: str
    message: str
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    player: Optional[str] = None
    action: Optional[str] = None
    extra_data: Optional[dict] = None


class SessionSummary(BaseModel):
    """Session summary for dashboard."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    status: str
    player_count: int
    scenario: Optional[str] = None
    turn_count: int = 0
    total_actions: int = 0


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_sessions: int
    active_sessions: int
    total_turns: int
    total_actions: int
    recent_logs: list[LogEntryResponse]
