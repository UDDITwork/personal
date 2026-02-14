"""
Authentication Dependencies
JWT token creation/validation and password hashing utilities
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Tuple
import secrets

from database import get_db, User, UserSession
from config import settings

# Security schemes
security = HTTPBearer()

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> Tuple[str, str]:
    """
    Hash password with bcrypt and generate salt

    Args:
        password: Plain text password

    Returns:
        Tuple of (hashed_password, salt)
        Note: bcrypt handles salting internally, so we return empty string for salt
    """
    from loguru import logger
    logger.info(f"Hashing password (length: {len(password)} chars)")

    # Hash using bcrypt (bcrypt generates and stores salt internally)
    hashed = pwd_context.hash(password)

    logger.info("Password hashed successfully")

    # Return empty salt since bcrypt handles it internally
    return hashed, ""


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """
    Verify password against hash

    Args:
        password: Plain text password to verify
        hashed: Stored password hash
        salt: Stored salt (not used, kept for backward compatibility)

    Returns:
        True if password matches, False otherwise
    """
    # Verify using bcrypt (salt parameter ignored since bcrypt handles it)
    return pwd_context.verify(password, hashed)


def create_access_token(user_id: str, email: str) -> Tuple[str, datetime]:
    """
    Create JWT access token

    Args:
        user_id: User's unique identifier
        email: User's email address

    Returns:
        Tuple of (token, expiration_datetime)
    """
    # Calculate expiration time
    expire = datetime.utcnow() + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    # Convert to Unix timestamp (seconds since epoch) for JWT exp claim
    # RFC 7519: exp must be a NumericDate (Unix timestamp)
    exp_timestamp = int(expire.timestamp())

    # Create JWT payload
    payload = {
        "sub": user_id,  # Subject (user ID)
        "email": email,
        "type": "access",
        "exp": exp_timestamp  # FIXED: Unix timestamp instead of datetime object
    }

    # Encode JWT token
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return token, expire


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate user from JWT token

    This is a FastAPI dependency that validates the JWT token
    and returns the authenticated user object

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Define credentials exception
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        # Extract user ID from payload
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        # Verify token is active in database
        session = db.query(UserSession).filter(
            UserSession.access_token == token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired or invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from database
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()

        if user is None:
            raise credentials_exception

        return user

    except JWTError:
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is active

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active user object

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def revoke_token(token: str, db: Session) -> bool:
    """
    Revoke an access token (for logout)

    Args:
        token: JWT access token to revoke
        db: Database session

    Returns:
        True if token was revoked, False if not found
    """
    # Find session with this token
    session = db.query(UserSession).filter(
        UserSession.access_token == token
    ).first()

    if session:
        # Mark as inactive
        session.is_active = False
        db.commit()
        return True

    return False
