"""Data models for ChameleonNet."""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time

class ServiceType(str, Enum):
    SSH = "ssh"
    WEB = "web"

class FidelityMode(str, Enum):
    LOW = "low"          # Static fast responses, minimal synthetic depth
    MEDIUM = "medium"    # Profile-conditioned templates, standard Linux VFS
    HIGH = "high"        # LLM generated, deep context, proactive decoy breadcrumbs

class Event(BaseModel):
    id: Optional[int] = None
    session_id: str
    timestamp: float = Field(default_factory=time.time)
    source_ip: str
    service: ServiceType
    raw_input: str
    response_summary: str = ""
    latency_ms: float = 0.0
    technique_tags: List[str] = Field(default_factory=list)
    fidelity_mode: FidelityMode = FidelityMode.MEDIUM
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Session(BaseModel):
    session_id: str
    service: ServiceType
    source_ip: str
    start_time: float = Field(default_factory=time.time)
    last_activity: float = Field(default_factory=time.time)
    dwell_seconds: float = 0.0
    command_count: int = 0
    skill_score: float = 1.0  # 1.0 - 10.0 scale
    current_profile: str = "ubuntu_web_server"
    current_fidelity: FidelityMode = FidelityMode.MEDIUM
    decoys_revealed: List[str] = Field(default_factory=list)
    technique_counts: Dict[str, int] = Field(default_factory=dict)
    is_active: bool = True

class DecoyItem(BaseModel):
    path: str
    content: str
    category: str
    description: str

class AdaptationAction(BaseModel):
    upgrade_fidelity: Optional[FidelityMode] = None
    inject_decoys: List[DecoyItem] = Field(default_factory=list)
    rotate_profile: Optional[str] = None
    apply_delay_ms: int = 0
    rate_limited: bool = False
    reasons: List[str] = Field(default_factory=list)

class TelemetryStats(BaseModel):
    total_sessions: int = 0
    active_sessions: int = 0
    total_events: int = 0
    avg_dwell_seconds: float = 0.0
    technique_distribution: Dict[str, int] = Field(default_factory=dict)
    skill_distribution: Dict[str, int] = Field(default_factory=dict)
    fidelity_distribution: Dict[str, int] = Field(default_factory=dict)
