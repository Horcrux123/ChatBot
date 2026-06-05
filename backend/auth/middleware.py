import logging
from datetime import datetime, timezone, timedelta
from fastapi import Request, Depends, HTTPException, status
from itsdangerous import Signer, BadSignature
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import User, get_db_session
from backend.auth.oauth import refresh_access_token
from backend.zoho_client import ZohoClient

logger = logging.getLogger("zoho_chatbot")

COOKIE_NAME = "user_session"

# --- Signed Cookie Signing Helpers ---

def sign_user_id(user_id: str) -> str:
    """Signs a user ID using the application SECRET_KEY to store in cookie."""
    s = Signer(settings.SECRET_KEY)
    return s.sign(user_id.encode("utf-8")).decode("utf-8")

def unsign_user_id(signed_value: str) -> str:
    """Unsigns the session cookie to extract user_id. Raises BadSignature if invalid."""
    s = Signer(settings.SECRET_KEY)
    return s.unsign(signed_value.encode("utf-8")).decode("utf-8")


# --- Authentication Dependency ---

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependency that decodes the user session cookie, loads the user from DB,
    checks if their Zoho access token is about to expire (< 5 minutes),
    auto-refreshes it, and injects user/client details into request state.
    """
    signed_session = request.cookies.get(COOKIE_NAME)
    if not signed_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session cookie missing. Please log in."
        )

    try:
        user_id = unsign_user_id(signed_session)
    except BadSignature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session. Please log in again."
        )

    # Load user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session invalid. Account not found."
        )

    # Check and refresh Zoho token if needed (< 5 mins remaining)
    now = datetime.now(timezone.utc)
    token_expiry = user.token_expires_at
    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(tzinfo=timezone.utc)

    # If expired or close to expiry (less than 5 mins)
    if (token_expiry - now).total_seconds() < 300:
        logger.info(f"Zoho token for user {user.email} is expiring soon. Refreshing...")
        try:
            decrypted_refresh_token = user.get_decrypted_refresh_token()
            token_payload = await refresh_access_token(decrypted_refresh_token)
            
            # Update user tokens in database
            new_access_token = token_payload["access_token"]
            user.set_encrypted_access_token(new_access_token)
            
            # Refresh token may also be updated
            if "refresh_token" in token_payload:
                user.set_encrypted_refresh_token(token_payload["refresh_token"])
                
            expires_in = token_payload.get("expires_in", 3600)
            user.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            db.add(user)
            await db.flush() # Sync state with current transaction
            logger.info(f"Successfully refreshed access token for user {user.email}")
        except Exception as e:
            logger.error(f"Failed to refresh Zoho token for user {user.email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Zoho authentication session expired. Please log in again."
            )

    # Create Zoho Client instance with current token
    # We can fetch the portal_id from the user memory table later, or initialize dynamically.
    zoho_client = ZohoClient(access_token=user.get_decrypted_access_token())
    
    # Store user and client in request state for downstream routes
    request.state.user = user
    request.state.zoho_client = zoho_client

    return user
