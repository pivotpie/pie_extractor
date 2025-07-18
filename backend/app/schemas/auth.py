from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Token data schema"""
    email: Optional[str] = None

class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8)

class UserUpdate(UserBase):
    """User update schema"""
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None

class UserInDBBase(UserBase):
    """Base user in database schema"""
    id: int
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class User(UserInDBBase):
    """User response schema"""
    pass

class UserInDB(UserInDBBase):
    """User in database schema"""
    hashed_password: str

class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str

class PasswordResetRequest(BaseModel):
    """Password reset request schema"""
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str
    new_password: str = Field(..., min_length=8)
