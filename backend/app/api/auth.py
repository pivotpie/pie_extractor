import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .. import models, schemas
from ..core import security
from ..core.config import settings
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

from fastapi import Body

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(None),
    db: Session = Depends(get_db),
    body: dict = Body(None)
):
    """OAuth2 compatible token login, get an access token and user for future requests. Accepts form or JSON."""
    if body:
        email = body.get("email") or body.get("username")
        password = body.get("password")
    elif form_data:
        email = form_data.username
        password = form_data.password
    else:
        raise HTTPException(status_code=422, detail="Missing credentials")
    user = security.authenticate_user(db, email=email, password=password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": schemas.User.from_orm(user)}

@router.post("/register")
async def register(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create new user and return token and user object for auto-login.
    
    Args:
        user_in: User creation data
        db: Database session
        
    Returns:
        dict: Access token and user data
        
    Raises:
        HTTPException: If user registration fails
    """
    logger.info(f"Starting registration for user: {user_in.email}")
    logger.debug(f"User data: {user_in.dict()}")
    
    try:
        # Check if user already exists
        logger.debug("Checking if user already exists in database")
        db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
        if db_user:
            logger.warning(f"Registration failed - email already registered: {user_in.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        logger.debug("Creating new user object")
        # Create new user with all required fields
        user_data = {
            "email": user_in.email,
            "full_name": user_in.full_name,
            "is_active": True,
            "is_superuser": False  # Explicitly set default value
        }
        
        # Log the user data being used for creation
        logger.debug(f"User data for creation: {user_data}")
        
        user = models.User(**user_data)
        
        # Set password (this should handle hashing)
        logger.debug("Setting user password")
        user.set_password(user_in.password)
        
        # Save to database
        try:
            logger.debug("Adding user to database session")
            db.add(user)
            logger.debug("Committing transaction")
            db.commit()
            logger.debug("Refreshing user object")
            db.refresh(user)
            logger.info(f"User registered successfully: {user.email}")
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error during registration: {str(db_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save user to database"
            )
        
        # Generate access token
        logger.debug("Generating access token")
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            data={"sub": user.email}, 
            expires_delta=access_token_expires
        )
        
        # Prepare response data
        response_data = {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": schemas.User.from_orm(user)
        }
        
        logger.info(f"Registration completed successfully for user: {user.email}")
        return response_data
        
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error during user registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during registration"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during user registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration"
        )

@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(security.get_current_active_user)
):
    """Get current user"""
    return current_user

@router.post("/password-reset-request")
async def password_reset_request(
    password_reset: schemas.PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset"""
    # In a real app, you would send an email with a reset link
    # For now, we'll just return a success message
    return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/password-reset-confirm")
async def password_reset_confirm(
    password_reset: schemas.PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset"""
    # In a real app, you would validate the reset token
    # For now, we'll just return a success message
    return {"message": "Password has been reset successfully"}
