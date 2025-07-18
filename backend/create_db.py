import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine
from app.core.config import settings

def create_database():
    """Create the database file and initialize tables."""
    # Ensure the database directory exists
    db_path = Path(settings.SQLITE_DB_DIR) / settings.SQLITE_DB_NAME
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating database at: {db_path.absolute()}")
    
    # Import all available models to ensure they are registered with SQLAlchemy
    from app.models.user import User
    from app.models.document import Document, DocumentChunk
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    
    # Verify the file was created
    if db_path.exists():
        print(f"Database file created successfully at: {db_path.absolute()}")
    else:
        print(f"Warning: Database file was not created at: {db_path.absolute()}")

if __name__ == "__main__":
    create_database()
