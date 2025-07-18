from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from passlib.context import CryptContext
from .base import Base

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    # User information
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    
    # Relationships
    documents = relationship("Document", back_populates="owner")
    api_keys = relationship("APIKey", back_populates="user")
    
    def set_password(self, password: str):
        """Hash and set the user's password"""
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash"""
        return pwd_context.verify(password, self.hashed_password)

class APIKey(Base):
    """API key model for external API access"""
    __tablename__ = "api_keys"
    
    # Key information
    key = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean(), default=True)
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    rate_limit = Column(Integer, default=50)  # Default 50 requests per day
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="api_keys")
