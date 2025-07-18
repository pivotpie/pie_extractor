from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from pathlib import Path
from .models.base import Base
from .core.config import settings

# Create database directory if it doesn't exist
Path(settings.SQLITE_DB_DIR).mkdir(parents=True, exist_ok=True)

# Database URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(settings.SQLITE_DB_DIR, settings.SQLITE_DB_NAME)}"

# Create engine and session
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database and create tables"""
    from .models.user import User
    from .models.document import Document, DocumentChunk
    
    Base.metadata.create_all(bind=engine)
