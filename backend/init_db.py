import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine
from app.core.config import settings

def init_db():
    """Initialize the database by creating all tables."""
    # Ensure the database directory exists
    db_dir = Path(settings.SQLITE_DB_DIR)
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Create all tables
    print(f"Creating database at: {settings.SQLALCHEMY_DATABASE_URI}")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()
