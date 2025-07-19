from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.models import (
    UserSignup,
    UserLogin,
    AuthResponse,
    UserProfile,
    PasswordChange,
    PasswordReset,
    EmailVerification,
)
from app.db import get_supabase_client
from app.auth_dependencies import get_current_user

# from app.rate_limiter import rate_limiter
from supabase.client import Client
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signup", response_model=AuthResponse)
async def signup(user_data: UserSignup, request: Request):
    """Register a new user with email and password"""

    # Rate limiting
    # await rate_limiter.check_rate_limit(request)

    try:
        client: Client = get_supabase_client()

        # Sign up user with Supabase Auth
        response = client.auth.sign_up(
            {
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "full_name": user_data.full_name,
                        "username": user_data.username,
                    }
                },
            }
        )

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed",
            )

        # Check if email confirmation is required
        if response.session is None:
            return AuthResponse(
                message="Please check your email to confirm your account",
                user=None,
                access_token=None,
                refresh_token=None,
                requires_verification=True,
            )

        return AuthResponse(
            message="User registered successfully",
            user={
                "id": response.user.id,
                "email": response.user.email,
                "full_name": user_data.full_name,
                "username": user_data.username,
            },
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            requires_verification=False,
        )

    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), request: Request = None
):
    """Login user with email and password"""

    # Rate limiting
    # await rate_limiter.check_rate_limit(request)

    try:
        client: Client = get_supabase_client()

        # Sign in with Supabase Auth
        response = client.auth.sign_in_with_password(
            {
                "email": form_data.username,  # OAuth2 uses username field for email
                "password": form_data.password,
            }
        )

        if response.user is None or response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        # Get user metadata
        user_metadata = response.user.user_metadata or {}

        return AuthResponse(
            message="Login successful",
            user={
                "id": response.user.id,
                "email": response.user.email,
                "full_name": user_metadata.get("full_name"),
                "username": user_metadata.get("username"),
            },
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            requires_verification=False,
        )

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(refresh_data: Dict[str, str], request: Request):
    """Refresh access token using refresh token"""

    # await rate_limiter.check_rate_limit(request)

    try:
        client: Client = get_supabase_client()
        refresh_token = refresh_data.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token required"
            )

        # Refresh session
        response = client.auth.refresh_session(refresh_token)

        if response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        user_metadata = response.user.user_metadata or {}

        return AuthResponse(
            message="Token refreshed successfully",
            user={
                "id": response.user.id,
                "email": response.user.email,
                "full_name": user_metadata.get("full_name"),
                "username": user_metadata.get("username"),
            },
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            requires_verification=False,
        )

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user), request: Request = None
):
    """Logout current user"""

    try:
        client: Client = get_supabase_client()

        # Sign out user
        client.auth.sign_out()

        return {"message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {"message": "Logout completed"}


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get current user profile"""

    try:
        client: Client = get_supabase_client()

        # Get updated user data
        user_response = client.auth.get_user()

        if user_response.user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        user_metadata = user_response.user.user_metadata or {}

        return UserProfile(
            id=user_response.user.id,
            email=user_response.user.email,
            full_name=user_metadata.get("full_name"),
            username=user_metadata.get("username"),
            created_at=user_response.user.created_at,
            email_verified=user_response.user.email_confirmed_at is not None,
        )

    except Exception as e:
        logger.error(f"Get user profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile",
        )


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    profile_data: Dict[str, str],
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None,
):
    """Update user profile"""

    # await rate_limiter.check_rate_limit(request)

    try:
        client: Client = get_supabase_client()

        # Update user metadata
        response = client.auth.update_user({"data": profile_data})

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Profile update failed"
            )

        user_metadata = response.user.user_metadata or {}

        return UserProfile(
            id=response.user.id,
            email=response.user.email,
            full_name=user_metadata.get("full_name"),
            username=user_metadata.get("username"),
            created_at=response.user.created_at,
            email_verified=response.user.email_confirmed_at is not None,
        )

    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile update failed"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None,
):
    """Change user password"""

    # await rate_limiter.check_rate_limit(request)

    try:
        client: Client = get_supabase_client()

        # Update password
        response = client.auth.update_user({"password": password_data.new_password})

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Password change failed"
            )

        return {"message": "Password changed successfully"}

    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password change failed"
        )


@router.post("/reset-password")
async def reset_password(reset_data: PasswordReset, request: Request):
    """Send password reset email"""

    # await rate_limiter.check_rate_limit(request)

    try:
        client: Client = get_supabase_client()

        # Send reset password email
        client.auth.reset_password_email(reset_data.email)

        return {"message": "Password reset email sent"}

    except Exception as e:
        logger.error(f"Password reset error: {e}")
        # Don't reveal if email exists or not
        return {"message": "Password reset email sent"}


@router.post("/verify-email")
async def verify_email(verification_data: EmailVerification):
    """Verify email with token"""

    try:
        client: Client = get_supabase_client()

        # Verify email
        response = client.auth.verify_otp(
            {
                "email": verification_data.email,
                "token": verification_data.token,
                "type": "email",
            }
        )

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email verification failed",
            )

        return {"message": "Email verified successfully"}

    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email verification failed"
        )
