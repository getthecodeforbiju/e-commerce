from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.database.models import UserRole


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(min_length=8, max_length=100)
    role: UserRole = UserRole.BUYER


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user"""
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse