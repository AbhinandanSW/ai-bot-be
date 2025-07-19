from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import settings
from app.db import get_supabase_client
from supabase.client import Client
import jwt
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Security scheme for bearer token
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token.
    This validates the Supabase JWT token and returns user information.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Validate JWT token using Supabase JWT secret
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )

        # Extract user information from JWT payload
        user_id = payload.get("sub")
        email = payload.get("email")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Optional: Validate token with Supabase (for extra security)
        # This makes a request to Supabase to verify the token is still valid
        client: Client = get_supabase_client()

        try:
            # Set the JWT token for the client
            client.postgrest.auth(token)
            user_response = client.auth.get_user(token)

            if user_response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or token invalid",
                )

            # Return user information
            return {
                "id": user_id,
                "email": email,
                "user": user_response.user,
                "token": token,
            }

        except Exception as supabase_error:
            # If Supabase validation fails, still trust JWT if it's valid
            logger.warning(f"Supabase token validation failed: {supabase_error}")

            return {"id": user_id, "email": email, "token": token}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Dependency to get current active user (additional checks can be added here)
    """

    # Add any additional checks here (e.g., user is active, not banned, etc.)
    # For now, just return the current user

    return current_user


# Optional: Admin user dependency
async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Dependency to ensure current user is an admin
    """

    # Check if user has admin role
    user_metadata = current_user.get("user", {}).user_metadata or {}
    user_role = user_metadata.get("role", "user")

    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    return current_user


# Optional: Rate limit per user
async def get_current_user_with_rate_limit(
    current_user: Dict[str, Any] = Depends(get_current_user), request: Request = None
) -> Dict[str, Any]:
    """
    Dependency that combines user authentication with rate limiting
    """

    # from app.rate_limiter import rate_limiter

    # Use user ID for rate limiting instead of IP
    user_id = current_user.get("id")
    # await rate_limiter.check_rate_limit(request, identifier=user_id)

    return current_user
