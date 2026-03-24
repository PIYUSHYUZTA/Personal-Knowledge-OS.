"""
Security utilities: JWT tokens, password hashing, MPC handshakes.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import hashlib
import hmac
import secrets
from jose import JWTError, jwt
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# PASSWORD HASHING
# ============================================================================

import bcrypt

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, datetime]:
    """
    Create a JWT access token.

    Returns:
        (token, expiration_datetime)
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt, expire

def create_refresh_token(data: dict) -> Tuple[str, datetime]:
    """Create a JWT refresh token with longer expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt, expire

def verify_token(token: str) -> Optional[dict]:
    """
    Verify a JWT token and extract claims.

    Returns:
        Claims dict if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"Invalid token: {e}")
        return None

# ============================================================================
# MPC (MULTI-PARTY COMPUTATION) SECURITY
# ============================================================================

def generate_mpc_handshake() -> str:
    """
    Generate a secure MPC handshake challenge.
    Used for multi-party computation security in distributed systems.
    """
    if not settings.MPC_ENABLED:
        return ""

    # Generate a random 32-byte challenge
    challenge = secrets.token_hex(32)
    return challenge

def compute_mpc_hash(
    challenge: str,
    private_key: Optional[str] = None
) -> str:
    """
    Compute HMAC-SHA256 hash for MPC verification.

    In a real MPC implementation:
    - Client generates challenge
    - Server signs with private key
    - Client verifies signature
    - Exchange is cryptographically secure
    """
    if private_key is None:
        private_key = settings.MPC_PRIVATE_KEY or settings.SECRET_KEY

    signature = hmac.new(
        private_key.encode(),
        challenge.encode(),
        hashlib.sha256
    ).hexdigest()

    return signature

def verify_mpc_handshake(
    challenge: str,
    signature: str,
    private_key: Optional[str] = None
) -> bool:
    """Verify MPC handshake signature."""
    expected_signature = compute_mpc_hash(challenge, private_key)
    return hmac.compare_digest(expected_signature, signature)

# ============================================================================
# SESSION TOKEN GENERATION
# ============================================================================

def generate_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(64)
