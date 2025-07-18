from typing import Optional, Dict, Any, Tuple
import httpx
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from authlib.integrations.starlette_client import OAuth, OAuthError
from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

class OAuthException(Exception):
    """Custom exception for OAuth related errors"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

# Initialize OAuth
oauth = OAuth()

def configure_oauth():
    """Configure OAuth providers with error handling"""
    try:
        # GitHub OAuth configuration
        oauth.register(
            name='github',
            client_id=settings.GITHUB_CLIENT_ID,
            client_secret=settings.GITHUB_CLIENT_SECRET,
            authorize_url='https://github.com/login/oauth/authorize',
            authorize_params=None,
            access_token_url='https://github.com/login/oauth/access_token',
            access_token_params=None,
            refresh_token_url=None,
            client_kwargs={
                'scope': 'user:email',
                'token_endpoint_auth_method': 'client_secret_post'
            },
            server_metadata_url=None
        )

        # Google OAuth configuration
        oauth.register(
            name='google',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            authorize_params=None,
            access_token_url='https://oauth2.googleapis.com/token',
            access_token_params=None,
            refresh_token_url=None,
            client_kwargs={
                'scope': 'openid email profile',
                'prompt': 'select_account',
            },
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
        )
        
        logger.info("OAuth providers configured successfully")
        
    except Exception as e:
        logger.error(f"Failed to configure OAuth providers: {str(e)}")
        raise OAuthException("OAuth configuration failed")

async def get_github_user_info(access_token: str) -> Dict[str, Any]:
    """
    Get GitHub user info using access token
    
    Args:
        access_token: OAuth access token from GitHub
        
    Returns:
        Dict containing user information
        
    Raises:
        OAuthException: If there's an error fetching user info
    """
    try:
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        async with httpx.AsyncClient() as client:
            # Get user emails
            email_response = await client.get(
                'https://api.github.com/user/emails',
                headers=headers,
                timeout=10.0
            )
            
            if email_response.status_code != 200:
                error_msg = f"GitHub API error: {email_response.text}"
                logger.error(error_msg)
                raise OAuthException("Failed to fetch user emails from GitHub")
                
            emails = email_response.json()
            if not isinstance(emails, list):
                raise OAuthException("Invalid response format from GitHub API")
                
            # Find primary email
            primary_email = next(
                (e['email'] for e in emails if isinstance(e, dict) and e.get('primary')),
                None
            )
            
            # Get user profile
            profile_response = await client.get(
                'https://api.github.com/user',
                headers=headers,
                timeout=10.0
            )
            
            if profile_response.status_code != 200:
                error_msg = f"GitHub API error: {profile_response.text}"
                logger.error(error_msg)
                raise OAuthException("Failed to fetch user profile from GitHub")
                
            profile = profile_response.json()
            
            # Verify required fields
            if not all(key in profile for key in ['id', 'login']):
                raise OAuthException("Incomplete user profile data from GitHub")
            
            return {
                'email': primary_email or profile.get('email', ''),
                'name': profile.get('name') or profile.get('login', ''),
                'avatar_url': profile.get('avatar_url', ''),
                'provider': 'github',
                'provider_id': str(profile.get('id')),
                'email_verified': any(
                    isinstance(e, dict) and e.get('verified', False) 
                    for e in emails
                ),
                'username': profile.get('login', '')
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching GitHub user info: {str(e)}")
        raise OAuthException("Failed to communicate with GitHub API")
    except Exception as e:
        logger.error(f"Unexpected error fetching GitHub user info: {str(e)}")
        raise OAuthException("An unexpected error occurred")

async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """
    Get Google user info using access token
    
    Args:
        access_token: OAuth access token from Google
        
    Returns:
        Dict containing user information
        
    Raises:
        OAuthException: If there's an error fetching user info
    """
    try:
        async with httpx.AsyncClient() as client:
            # Get user info
            response = await client.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10.0
            )
            
            if response.status_code != 200:
                error_msg = f"Google API error: {response.text}"
                logger.error(error_msg)
                raise OAuthException("Failed to fetch user info from Google")
                
            user_info = response.json()
            
            # Verify required fields
            if not all(key in user_info for key in ['sub', 'email']):
                raise OAuthException("Incomplete user profile data from Google")
            
            return {
                'email': user_info['email'],
                'name': user_info.get('name', user_info.get('email', '').split('@')[0]),
                'avatar_url': user_info.get('picture', ''),
                'provider': 'google',
                'provider_id': user_info['sub'],
                'email_verified': user_info.get('email_verified', False),
                'username': user_info.get('email', '').split('@')[0]
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching Google user info: {str(e)}")
        raise OAuthException("Failed to communicate with Google API")
    except Exception as e:
        logger.error(f"Unexpected error fetching Google user info: {str(e)}")
        raise OAuthException("An unexpected error occurred")

def generate_oauth_state(request: Request) -> str:
    """
    Generate a secure state parameter for OAuth flow and store it in the session
    
    Args:
        request: The FastAPI request object
        
    Returns:
        str: The generated state token
    """
    import secrets
    state = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes expiry
    
    # Store state in the session
    if not hasattr(request.state, 'session'):
        request.state.session = {}
    
    request.state.session['oauth_state'] = {
        'state': state,
        'expires_at': expires_at.isoformat(),
        'created_at': datetime.utcnow().isoformat()
    }
    
    logger.debug(f"Generated OAuth state: {state}, expires at: {expires_at}")
    return state

def verify_oauth_state(request: Request, state: str) -> bool:
    """
    Verify the OAuth state parameter from the session
    
    Args:
        request: The FastAPI request object
        state: The state parameter from the OAuth callback
        
    Returns:
        bool: True if the state is valid, False otherwise
    """
    if not state:
        logger.error("No state parameter provided for verification")
        return False
        
    # Get state from session
    session = getattr(request.state, 'session', {})
    if 'oauth_state' not in session:
        logger.error("No OAuth state found in session")
        return False
        
    stored_state = session['oauth_state']
    expires_at = datetime.fromisoformat(stored_state['expires_at'])
    
    # Clean up the state from session after verification
    if 'oauth_state' in session:
        del session['oauth_state']
    
    # Verify state and expiration
    is_valid = (
        state == stored_state['state'] and 
        datetime.utcnow() < expires_at
    )
    
    logger.debug(f"OAuth state verification: {'valid' if is_valid else 'invalid'}")
    return is_valid

# Configure OAuth providers when module is imported
try:
    configure_oauth()
except Exception as e:
    logger.critical(f"Failed to initialize OAuth: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(e)
    )
