from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from .database import Base
import datetime
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    mobile = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.USER)
    profile_image = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    assignments = relationship("DeviceAssignment", back_populates="owner")

class Device(Base):
    __tablename__ = "devices"

    chip_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_assigned = Column(Boolean, default=False)
    
    assignment = relationship("DeviceAssignment", back_populates="device", uselist=False)
    equipments = relationship("Equipment", back_populates="device")

class DeviceAssignment(Base):
    __tablename__ = "device_assignments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    chip_id = Column(String, ForeignKey("devices.chip_id"))
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="assignments")
    device = relationship("Device", back_populates="assignment")

class Equipment(Base):
    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, index=True)
    chip_id = Column(String, ForeignKey("devices.chip_id"))
    name = Column(String)
    room_name = Column(String)
    gpio_pin = Column(Integer)
    status = Column(String, default="OFF") # ON/OFF

    device = relationship("Device", back_populates="equipments")
