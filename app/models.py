"""
Pydantic models for NAV Scoring system.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


# ===== Enums =====
class SecretType(str, Enum):
    CHECKPOINT = "checkpoint"
    ENROUTE = "enroute"


class CheckpointMethod(str, Enum):
    CTP = "CTP"
    RADIUS_ENTRY = "Radius Entry"
    PCA = "PCA"


# ===== Auth Models =====
class MemberCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: Optional[str] = None  # Set on first login if None


class MemberLogin(BaseModel):
    username: str
    password: str


class CoachLogin(BaseModel):
    username: str
    password: str


class MemberResponse(BaseModel):
    id: int
    username: str
    email: str
    name: str
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class SessionData(BaseModel):
    user_id: int
    username: str
    user_type: str  # "member" or "coach"
    name: Optional[str] = None


# ===== Pairing Models =====
class PairingCreate(BaseModel):
    pilot_id: int
    safety_observer_id: int


class PairingResponse(BaseModel):
    id: int
    pilot_id: int
    safety_observer_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PairingDetailResponse(BaseModel):
    id: int
    pilot: MemberResponse
    safety_observer: MemberResponse
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ===== NAV Models =====
class AirportCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=10)


class AirportResponse(BaseModel):
    id: int
    code: str

    class Config:
        from_attributes = True


class StartGateCreate(BaseModel):
    airport_id: int
    name: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class StartGateResponse(BaseModel):
    id: int
    airport_id: int
    name: str
    lat: float
    lon: float

    class Config:
        from_attributes = True


class CheckpointCreate(BaseModel):
    name: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class CheckpointResponse(BaseModel):
    id: int
    nav_id: int
    sequence: int
    name: str
    lat: float
    lon: float

    class Config:
        from_attributes = True


class SecretCreate(BaseModel):
    name: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    type: SecretType = SecretType.CHECKPOINT


class SecretResponse(BaseModel):
    id: int
    nav_id: int
    name: str
    lat: float
    lon: float
    type: SecretType
    created_at: datetime

    class Config:
        from_attributes = True


class NavCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    airport_id: int
    checkpoints: List[CheckpointCreate]


class NavResponse(BaseModel):
    id: int
    name: str
    airport_id: int
    checkpoints: List[CheckpointResponse]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Pre-NAV Submission Models =====
class PreNavCreate(BaseModel):
    pairing_id: int
    nav_id: int
    leg_times: List[float] = Field(..., min_items=1)  # in seconds
    total_time: float = Field(..., gt=0)  # in seconds
    fuel_estimate: float = Field(..., gt=0)  # in gallons


class PreNavResponse(BaseModel):
    id: int
    pairing_id: int
    pilot_id: int
    nav_id: int
    leg_times: List[float]
    total_time: float
    fuel_estimate: float
    token: str
    submitted_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


# ===== Flight Result Models =====
class CheckpointResultDetail(BaseModel):
    name: str
    distance_nm: float
    within_0_25_nm: bool
    method: CheckpointMethod
    estimated_time: float  # seconds
    actual_time: float  # seconds
    deviation: float  # seconds
    leg_score: float  # points
    off_course_penalty: float  # points


class FlightResultsMetrics(BaseModel):
    planned_total_time: float
    actual_total_time: float
    total_deviation: float
    total_time_score: float
    estimated_fuel_burn: float
    actual_fuel_burn: float
    fuel_penalty: float
    missed_checkpoint_secrets: int
    missed_enroute_secrets: int
    checkpoint_secrets_penalty: float
    enroute_secrets_penalty: float
    overall_score: float


class FlightCreate(BaseModel):
    prenav_token: str
    actual_fuel: float = Field(..., gt=0)
    secrets_missed_checkpoint: int = Field(..., ge=0)
    secrets_missed_enroute: int = Field(..., ge=0)
    start_gate_id: int
    # GPX file uploaded separately via multipart


class FlightResultResponse(BaseModel):
    id: int
    pairing_id: int
    nav_id: int
    prenav_id: int
    actual_fuel: float
    secrets_missed_checkpoint: int
    secrets_missed_enroute: int
    start_gate_id: Optional[int]
    overall_score: float
    checkpoint_results: List[CheckpointResultDetail]
    total_metrics: FlightResultsMetrics
    pdf_filename: Optional[str]
    scored_at: datetime

    class Config:
        from_attributes = True


# ===== API Response Wrappers =====
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None
