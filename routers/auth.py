"""
Authentication Router
Handles user registration, login, and logout
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from loguru import logger

from database import get_db, User, UserSession
from auth.dependencies import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    full_name: str = Field(..., description="User's full name")


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class AuthResponse(BaseModel):
    """Authentication response with token"""
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_at: Optional[datetime] = None
    user: Optional[dict] = None


class UserResponse(BaseModel):
    """User information response"""
    id: str
    email: str
    full_name: str
    created_at: datetime
    is_active: bool


# Endpoints

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account

    Creates a new user with email/password authentication.
    Email must be unique.
    """
    logger.info(f"Registration attempt for email: {request.email}")

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()

    if existing_user:
        logger.warning(f"Registration failed: Email {request.email} already registered")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password
    password_hash, password_salt = hash_password(request.password)

    # Create new user
    new_user = User(
        email=request.email,
        password_hash=password_hash,
        password_salt=password_salt,
        full_name=request.full_name,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.success(f"User registered successfully: {new_user.email} (ID: {new_user.id})")

    return AuthResponse(
        success=True,
        message="User registered successfully",
        user={
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name
        }
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password

    Returns a JWT access token that should be included in
    subsequent requests as: Authorization: Bearer <token>
    """
    logger.info(f"Login attempt for email: {request.email}")

    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        logger.warning(f"Login failed: User not found for email {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.password_hash, user.password_salt):
        logger.warning(f"Login failed: Incorrect password for email {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login failed: User account inactive for email {request.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token, expires_at = create_access_token(user.id, user.email)

    # Store session in database
    session = UserSession(
        user_id=user.id,
        access_token=access_token,
        expires_at=expires_at,
        is_active=True
    )

    db.add(session)
    db.commit()

    logger.success(f"User logged in successfully: {user.email} (ID: {user.id})")

    return AuthResponse(
        success=True,
        message="Login successful",
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user

    Invalidates the current access token
    """
    # Get token from security dependency (it's already validated by get_current_user)
    # We need to extract it from the dependency
    # For simplicity, we'll invalidate all active sessions for this user

    logger.info(f"Logout request for user: {current_user.email}")

    # Invalidate all active sessions for this user
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True
    ).update({"is_active": False})

    db.commit()

    logger.success(f"User logged out successfully: {current_user.email}")

    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's information

    Returns profile information for the currently logged-in user
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at,
        is_active=current_user.is_active
    )
