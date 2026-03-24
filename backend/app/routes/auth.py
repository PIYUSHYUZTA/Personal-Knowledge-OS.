"""
Authentication API routes: /auth/register, /auth/login, /auth/verify
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.database.connection import get_db
from app.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.services.auth_service import AuthService
from app.core.security import verify_token
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ============================================================================
# HELPER FUNCTION
# ============================================================================

def get_current_user(token: str = None, db: Session = Depends(get_db)) -> User:
    """
    Dependency to extract and verify current authenticated user from JWT.
    Can be used in any protected route.
    """
    # Token can be extracted from Authorization header in actual implementation
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user = AuthService.verify_session(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new PKOS user account"
)
def register(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    **Request Body:**
    - email: valid email address
    - username: 3-150 characters
    - password: minimum 8 characters
    - full_name: optional

    **Returns:**
    - User details and verification token
    """
    try:
        user_response, verification_token = AuthService.register_user(db, user_create)
        return {
            "user": user_response,
            "verification_token": verification_token,
            "message": "User registered successfully. Check email for verification."
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post(
    "/login",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Login to PKOS",
    description="Authenticate with email and password"
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    **Request Body:**
    - email: registered email
    - password: account password

    **Returns:**
    - access_token: JWT for authenticated requests
    - refresh_token: JWT for token refresh
    - user: logged-in user details
    """
    try:
        user, token_response = AuthService.login(db, credentials.email, credentials.password)
        return {
            "user": UserResponse.model_validate(user),
            "tokens": token_response,
            "message": "Login successful"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Get a new access token using refresh token"
)
def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh an expired access token.

    **Query Parameters:**
    - refresh_token: valid refresh token

    **Returns:**
    - new access_token
    """
    try:
        return AuthService.refresh_access_token(db, refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get(
    "/verify",
    response_model=UserResponse,
    summary="Verify current session",
    description="Get current user info from token"
)
def verify_session(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verify that the provided token is valid and get user info.

    **Query Parameters:**
    - token: JWT access token

    **Returns:**
    - Current user details
    """
    user = AuthService.verify_session(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return UserResponse.model_validate(user)

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Invalidate current session"
)
def logout(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Logout the current user by invalidating their session.

    **Query Parameters:**
    - token: JWT access token

    **Returns:**
    - Logout confirmation message
    """
    user = AuthService.verify_session(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    success = AuthService.logout(db, user.id)
    if success:
        return {"message": "Logout successful"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )
