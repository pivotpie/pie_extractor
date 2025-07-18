import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from fastapi.responses import RedirectResponse, JSONResponse, Response
from sqlalchemy.orm import Session
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse, quote_plus
from fastapi.middleware.cors import CORSMiddleware

from .. import models, schemas
from ..core import security, oauth as oauth_utils
from ..core.config import settings
from ..core.oauth import OAuthException, generate_oauth_state, verify_oauth_state, oauth
from ..database import get_db
from ..core.security import create_access_token

router = APIRouter()
logger = logging.getLogger(__name__)

# Add CORS preflight handler for OAuth endpoints
@router.options("/github", status_code=status.HTTP_200_OK)
@router.options("/github/callback", status_code=status.HTTP_200_OK)
@router.options("/google", status_code=status.HTTP_200_OK)
@router.options("/google/callback", status_code=status.HTTP_200_OK)
async def options_handler():
    # Explicit CORS headers for preflight
    response = Response(status_code=200)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@router.get("/github")
async def github_login(
    request: Request,
    redirect_uri: Optional[str] = None
):
    """
    Initiate GitHub OAuth login flow
    
    Args:
        request: The FastAPI request object
        redirect_uri: Optional URI to redirect to after successful authentication
    """
    try:
        logger.info("Initiating GitHub OAuth login")
        
        # Generate and store state in session
        state = generate_oauth_state(request)
        logger.info(f"Generated OAuth state: {state}")
        
        # Get the base redirect URI for GitHub
        base_redirect_uri = get_oauth_redirect_uri('github')
        
        # If a custom redirect_uri was provided, store it in the session
        if redirect_uri:
            # Validate the redirect_uri to prevent open redirects
            try:
                parsed_redirect = urlparse(redirect_uri)
                if not parsed_redirect.netloc:
                    # Ensure it's a path starting with /
                    if not redirect_uri.startswith('/'):
                        redirect_uri = f'/{redirect_uri}'
                    # Prepend the frontend URL
                    redirect_uri = f"{settings.FRONTEND_URL.rstrip('/')}{redirect_uri}"
                request.session['oauth_redirect_uri'] = redirect_uri
                logger.info(f"Stored custom redirect_uri in session: {redirect_uri}")
            except Exception as e:
                logger.warning(f"Invalid redirect_uri: {redirect_uri}, using default. Error: {str(e)}")
                redirect_uri = None

        logger.info(f"Using base redirect_uri: {base_redirect_uri}")

        # Ensure the redirect_uri is properly encoded for the GitHub OAuth flow
        encoded_redirect_uri = quote_plus(base_redirect_uri)

        # Create the authorization URL with all required parameters
        auth_params = {
            'client_id': settings.GITHUB_CLIENT_ID,
            'redirect_uri': base_redirect_uri,  # Use the full URL here, not encoded
            'state': state,
            'scope': 'user:email',
            'response_type': 'code'
        }

        # Build the full authorization URL
        auth_url = f"https://github.com/login/oauth/authorize?{urlencode(auth_params, safe=':')}"

        logger.info(f"Generated GitHub OAuth URL: {auth_url}")

        # Return a JSON response with the URL for the frontend to handle the redirect
        # This helps avoid any potential issues with the redirect
        response = JSONResponse(content={
            "auth_url": auth_url,
            "redirect_uri": base_redirect_uri,
            "state": state
        })
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
        
    except Exception as e:
        logger.error(f"Error initiating GitHub OAuth: {str(e)}", exc_info=True)
        # Return a JSON error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate GitHub login: {str(e)}"
        )

@router.get("/google")
async def google_login(request: Request):
    """
    Initiate Google OAuth login flow
    """
    try:
        # Generate and store state in session
        state = generate_oauth_state(request)
        
        # Get the redirect URI for Google
        redirect_uri = get_oauth_redirect_uri('google')
        
        # Generate the authorization URL
        auth_url = await oauth.google.authorize_redirect(
            request,
            redirect_uri,
            state=state,
            access_type='offline',
            prompt='select_account'
        )
        
        return auth_url
        
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google login"
        )

def get_oauth_redirect_uri(provider: str) -> str:
    """
    Get the OAuth redirect URI for a provider
    
    Args:
        provider: OAuth provider name (e.g., 'github', 'google')
        
    Returns:
        str: The full, properly encoded redirect URI for the provider
    """
    try:
        # Ensure API_BASE_URL has a scheme
        if not settings.API_BASE_URL.startswith(('http://', 'https://')):
            raise ValueError(f"API_BASE_URL must start with http:// or https://, got {settings.API_BASE_URL}")
        
        # Build the callback path
        callback_path = f"{settings.API_V1_STR}/auth/oauth/{provider}/callback".lstrip('/')
        
        # Construct the full URL
        base_url = settings.API_BASE_URL.rstrip('/')
        redirect_uri = f"{base_url}/{callback_path}"
        
        # Parse and normalize the URL
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(redirect_uri)
        
        # Ensure the URL is properly constructed
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid redirect_uri constructed: {redirect_uri}")
            
        # Rebuild the URL to ensure proper encoding
        redirect_uri = urlunparse(parsed)
        
        # For GitHub, we need to ensure the redirect_uri matches exactly what's registered
        if provider == 'github':
            # GitHub is case-sensitive with redirect_uris, so we need to ensure the path is exactly as registered
            # This ensures the path doesn't have any double slashes or missing slashes
            path_parts = [p for p in parsed.path.split('/') if p]
            normalized_path = '/' + '/'.join(path_parts)
            redirect_uri = f"{parsed.scheme}://{parsed.netloc}{normalized_path}"
        
        # Debug logging
        logger.info(f"OAuth {provider} - Final redirect_uri: {redirect_uri}")
        logger.info(f"OAuth {provider} - Using API_BASE_URL: {settings.API_BASE_URL}")
        logger.info(f"OAuth {provider} - Using API_V1_STR: {settings.API_V1_STR}")
        
        return redirect_uri
        
    except Exception as e:
        logger.error(f"Error constructing OAuth redirect_uri for {provider}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to construct OAuth redirect URL: {str(e)}"
        )

@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle GitHub OAuth callback with session-based state verification
    """
    try:
        # Check for OAuth errors
        if error:
            raise OAuthException(
                f"GitHub OAuth error: {error_description or 'Unknown error'}"
            )
        # Verify state using session
        if not verify_oauth_state(request, state):
            logger.error(f"Invalid or expired OAuth state: {state}")
            raise OAuthException("Invalid or expired OAuth state. Please try logging in again.")
        logger.info("OAuth state verified successfully")
        # Get access token
        token = await oauth_utils.oauth.github.authorize_access_token(
            request,
            state=state
        )
        if not token or 'access_token' not in token:
            raise OAuthException("Failed to get access token from GitHub")
        # Get user info
        user_info = await oauth_utils.get_github_user_info(token["access_token"])
        # Get or create user
        user = await get_or_create_user(db, user_info, 'github')
        # Create access token
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        # Get the stored redirect_uri from session or use default
        redirect_uri = request.session.pop('oauth_redirect_uri', None)
        if redirect_uri:
            logger.info(f"Redirecting to custom URI: {redirect_uri}")
            # Add token to the redirect URI
            parsed = urlparse(redirect_uri)
            query = parse_qs(parsed.query)
            query['token'] = [access_token]  # Wrap in list as parse_qs returns lists
            new_query = urlencode(query, doseq=True)
            redirect_url = urlunparse(parsed._replace(query=new_query))
        else:
            logger.info("No custom redirect_uri found, using default")
            redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
        logger.info(f"Redirecting to: {redirect_url}")
        response = RedirectResponse(url=redirect_url)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    except OAuthException as e:
        logger.error(f"GitHub OAuth error: {str(e)}")
        frontend_url = f"{settings.FRONTEND_URL}/auth/error?message={str(e)}"
        response = RedirectResponse(url=frontend_url)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    except Exception as e:
        logger.error(f"Unexpected error in GitHub callback: {str(e)}")
        frontend_url = f"{settings.FRONTEND_URL}/auth/error?message=An unexpected error occurred"
        response = RedirectResponse(url=frontend_url)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback with session-based state verification
    """
    try:
        # Check for OAuth errors
        if error:
            raise OAuthException(
                f"Google OAuth error: {error_description or 'Unknown error'}"
            )
        
        # Verify state using session
        if not verify_oauth_state(request, state):
            logger.error(f"Invalid or expired OAuth state: {state}")
            raise OAuthException("Invalid or expired OAuth state. Please try logging in again.")
        
        # Get access token
        token = await oauth_utils.oauth.google.authorize_access_token(
            request,
            state=state
        )
        
        if not token or 'access_token' not in token:
            raise OAuthException("Failed to get access token from Google")
        
        # Get user info
        user_info = await oauth_utils.get_google_user_info(token["access_token"])
        
        # Get or create user
        user = await get_or_create_user(db, user_info, 'google')
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        # Get the stored redirect_uri from session or use default
        redirect_uri = request.session.pop('oauth_redirect_uri', None)
        if redirect_uri:
            logger.info(f"Redirecting to custom URI: {redirect_uri}")
            # Add token to the redirect URI
            parsed = urlparse(redirect_uri)
            query = parse_qs(parsed.query)
            query['token'] = [access_token]  # Wrap in list as parse_qs returns lists
            new_query = urlencode(query, doseq=True)
            redirect_url = urlunparse(parsed._replace(query=new_query))
        else:
            logger.info("No custom redirect_uri found, using default")
            redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
            
        logger.info(f"Redirecting to: {redirect_url}")
        response = RedirectResponse(url=redirect_url)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    except OAuthException as e:
        logger.error(f"Google OAuth error: {str(e)}")
        frontend_url = f"{settings.FRONTEND_URL}/auth/error?message={str(e)}"
        response = RedirectResponse(url=frontend_url)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    except Exception as e:
        logger.error(f"Unexpected error in Google callback: {str(e)}")
        frontend_url = f"{settings.FRONTEND_URL}/auth/error?message=An unexpected error occurred"
        response = RedirectResponse(url=frontend_url)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

async def get_or_create_user(db: Session, user_info: Dict[str, Any], provider: str) -> models.User:
    """
    Get or create a user based on OAuth provider info
    """
    email = user_info.get('email')
    if not email:
        raise OAuthException(f"No email provided by {provider}")
    
    # Try to find existing user by email
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        # Create new user
        user_data = {
            'email': email,
            'full_name': user_info.get('name', ''),
            'hashed_password': security.get_password_hash(security.generate_random_password()),
            'is_active': True,
            'is_superuser': False,
            'provider': provider
        }
        user = models.User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user: {user.email}")
    
    return user
