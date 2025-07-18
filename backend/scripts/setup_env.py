import os
from pathlib import Path
from dotenv import load_dotenv

# Load existing .env file if it exists
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Get values from environment or prompt user
def get_env(key, default=None, is_secret=False):
    value = os.getenv(key, '').strip()
    if not value and default is not None:
        return default
    if not value:
        prompt = f"Enter {key}"
        if is_secret:
            from getpass import getpass
            value = getpass(prompt + ": ")
        else:
            value = input(prompt + ": ")
    return value

# Collect environment variables
env_vars = {
    # Application
    "APP_NAME": get_env("APP_NAME", "IDP Document Extractor"),
    "DEBUG": get_env("DEBUG", "True"),
    
    # API
    "API_V1_STR": get_env("API_V1_STR", "/api/v1"),
    "SECRET_KEY": get_env("SECRET_KEY", "your-secret-key-here"),
    "ACCESS_TOKEN_EXPIRE_MINUTES": get_env("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"),  # 7 days
    
    # Database
    "SQLITE_DB_DIR": get_env("SQLITE_DB_DIR", "data/db"),
    "SQLITE_DB_NAME": get_env("SQLITE_DB_NAME", "app.db"),
    
    # File Storage
    "UPLOAD_DIR": get_env("UPLOAD_DIR", "data/uploads"),
    "MAX_FILE_SIZE": get_env("MAX_FILE_SIZE", "10485760"),  # 10MB
    
    # OAuth
    "GITHUB_CLIENT_ID": get_env("GITHUB_CLIENT_ID", ""),
    "GITHUB_CLIENT_SECRET": get_env("GITHUB_CLIENT_SECRET", "", is_secret=True),
    "GOOGLE_CLIENT_ID": get_env("GOOGLE_CLIENT_ID", ""),
    "GOOGLE_CLIENT_SECRET": get_env("GOOGLE_CLIENT_SECRET", "", is_secret=True),
    
    # Frontend
    "FRONTEND_URL": get_env("FRONTEND_URL", "http://localhost:3000"),
    
    # CORS
    "BACKEND_CORS_ORIGINS": get_env(
        "BACKEND_CORS_ORIGINS", 
        json.dumps(["http://localhost:3000", "http://localhost:8000"])
    ),
}

# Write to .env file
with open(env_path, 'w') as f:
    for key, value in env_vars.items():
        if isinstance(value, bool):
            value = str(value).lower()
        f.write(f"{key}={value}\n")

print(f"\n✅ Environment configuration saved to {env_path.absolute()}")
print("\nNext steps:")
print("1. Review the .env file and update any values as needed")
print("2. Run database migrations: `alembic upgrade head`")
print("3. Start the application: `uvicorn app.main:app --reload`")
