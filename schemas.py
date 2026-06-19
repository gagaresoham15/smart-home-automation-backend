from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
try:
    from .models import UserRole
except (ImportError, ValueError):
    from models import UserRole

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# User Schemas
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    mobile: str
    password: str

class UserLogin(BaseModel):
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    password: str

class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    mobile: str
    role: UserRole
    profile_image: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    class Config:
        from_attributes = True

# Device Schemas
class DeviceCreate(BaseModel):
    chip_id: str

class DeviceOut(BaseModel):
    chip_id: str
    created_at: datetime
    is_assigned: bool
    class Config:
        from_attributes = True

# Equipment Schemas
class EquipmentCreate(BaseModel):
    chip_id: str
    name: str
    room_name: str
    gpio_pin: int

class EquipmentOut(BaseModel):
    id: int
    chip_id: str
    name: str
    room_name: str
    gpio_pin: int
    status: str
    class Config:
        from_attributes = True

# Aggregated Schemas
class AdminDashboardStats(BaseModel):
    total_users: int
    total_devices: int
    unassigned_devices: int
    assigned_devices: int

class MonthStat(BaseModel):
    month: str
    users: int
    devices: int

class AdminReportOut(BaseModel):
    history: List[MonthStat]
