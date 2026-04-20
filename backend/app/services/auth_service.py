"""
Authentication service: user registration, login, token management.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.models import User, Session as SessionModel
from app.schemas import UserCreate, UserResponse, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_mpc_handshake,
    compute_mpc_hash,
)
from app.config import settings

logger = logging.getLogger(__name__)

class AuthService:
    """Handles all authentication operations."""

    @staticmethod
    def register_user(db: Session, user_create: UserCreate) -> Tuple[UserResponse, str]:
        """
        Register a new user account.

        Returns:
            (UserResponse, email_verification_token)
        """
        # Check if email already exists
        existing = db.query(User).filter(User.email == user_create.email).first()
        if existing:
            raise ValueError("Email already registered")

        # Check if username already exists
        existing = db.query(User).filter(User.username == user_create.username).first()
        if existing:
            raise ValueError("Username already taken")

        # Create new user
        user = User(
            email=user_create.email,
            username=user_create.username,
            password_hash=hash_password(user_create.password),
            full_name=user_create.full_name,
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"User registered: {user.email}")

        # Generate email verification token (for future use)
        verification_token, _ = create_access_token(
            {"sub": str(user.id), "type": "email_verify"},
            expires_delta=timedelta(hours=24)
        )

        return UserResponse.model_validate(user), verification_token

    @staticmethod
    def login(db: Session, email: str, password: str) -> Tuple[User, TokenResponse]:
        """
        Authenticate user and create session.

        Returns:
            (User object, TokenResponse with JWT tokens)
        """
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("User account is disabled")

        # Create access token
        access_token, access_expires = create_access_token(
            {"sub": str(user.id), "type": "access"}
        )

        # Create refresh token
        refresh_token, refresh_expires = create_refresh_token(
            {"sub": str(user.id), "type": "refresh"}
        )

        # Create session record with MPC handshake
        mpc_challenge = generate_mpc_handshake()
        mpc_hash = compute_mpc_hash(mpc_challenge) if settings.MPC_ENABLED else None

        session = SessionModel(
            user_id=user.id,
            token=access_token,
            mpc_handshake_hash=mpc_hash,
            expires_at=access_expires,
        )

        db.add(session)
        db.commit()

        logger.info(f"User logged in: {user.email}")

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int((access_expires - datetime.now(timezone.utc)).total_seconds()),
        )

        return user, token_response

    @staticmethod
    def verify_session(db: Session, token: str) -> Optional[User]:
        """
        Verify a session token and return the associated user.

        Returns:
            User object if valid, None if invalid
        """
        payload = verify_token(token)
        if not payload or payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user if user and user.is_active else None
        except Exception as e:
            logger.error(f"Error verifying session: {e}")
            return None

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
        """
        Create a new access token from a refresh token.

        Returns:
            TokenResponse with new access token
        """
        payload = verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid refresh token")

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Create new access token
        access_token, access_expires = create_access_token(
            {"sub": str(user.id), "type": "access"}
        )

        return TokenResponse(
            access_token=access_token,
            expires_in=int((access_expires - datetime.now(timezone.utc)).total_seconds()),
        )

    @staticmethod
    def logout(db: Session, user_id: UUID) -> bool:
        """
        Logout user by revoking sessions.

        Returns:
            True if successful
        """
        try:
            sessions = db.query(SessionModel).filter(SessionModel.user_id == user_id).all()
            for session in sessions:
                session.revoked = True
            db.commit()
            logger.info(f"User logged out: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
