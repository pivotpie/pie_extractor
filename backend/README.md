# IDP Document Extractor Backend

Backend service for the IDP Document Extractor & Chatbot, built with FastAPI and SQLite.

## Features

- User authentication with JWT tokens
- Social login with GitHub and Google
- Document upload and processing
- Chat interface for document queries
- RESTful API

## Prerequisites

- Python 3.10+
- pip (Python package manager)
- Git

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/pie-extractor.git
   cd pie-extractor/backend
   ```

2. **Create and activate a virtual environment**
   ```bash
   # On Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Run the setup script to configure your environment
   python scripts/setup_env.py
   ```
   
   You'll need to provide:
   - GitHub OAuth credentials (optional)
   - Google OAuth credentials (optional)
   - Other configuration values

5. **Set up the database**
   ```bash
   # Create database tables
   alembic upgrade head
   ```

6. **Run the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`
   - API documentation: `http://localhost:8000/api/docs`
   - Interactive API docs: `http://localhost:8000/api/redoc`

## OAuth Setup

### GitHub OAuth
1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Set the following:
   - Application name: IDP Document Extractor
   - Homepage URL: `http://localhost:3000`
   - Authorization callback URL: `http://localhost:8000/api/v1/auth/oauth/github/callback`
4. Copy the Client ID and generate a Client Secret
5. Update your `.env` file with these values

### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Go to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Configure the consent screen
6. Create an OAuth client ID for a web application
7. Set the following authorized redirect URIs:
   - `http://localhost:8000/api/v1/auth/oauth/google/callback`
8. Copy the Client ID and Client Secret
9. Update your `.env` file with these values

## Project Structure

```
backend/
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── oauth.py         # OAuth endpoints
│   │   ├── documents.py     # Document endpoints
│   │   └── chat.py          # Chat endpoints
│   ├── core/                # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py        # Application settings
│   │   ├── security.py      # Authentication utilities
│   │   └── oauth.py         # OAuth utilities
│   ├── models/              # Database models
│   │   ├── __init__.py
│   │   ├── base.py          # Base model
│   │   ├── user.py          # User model
│   │   └── document.py      # Document models
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   └── auth.py          # Authentication schemas
│   ├── database.py          # Database configuration
│   └── main.py              # FastAPI application
├── data/                    # Data storage
│   ├── db/                  # SQLite databases
│   └── uploads/             # Uploaded files
├── scripts/                 # Utility scripts
│   └── setup_env.py         # Environment setup
├── .env.example             # Example environment variables
├── .gitignore
├── alembic.ini              # Alembic configuration
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## Development

### Running Tests
```bash
# Run tests
pytest

# Run with coverage report
pytest --cov=app tests/
```

### Database Migrations
```bash
# Create a new migration
alembic revision --autogenerate -m "Your migration message"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

## Deployment

For production deployment, consider using:
- Gunicorn with Uvicorn workers
- Nginx as a reverse proxy
- Let's Encrypt for SSL certificates
- Environment variables for configuration

Example Gunicorn command:
```bash
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
