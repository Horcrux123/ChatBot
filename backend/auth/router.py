import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import User, UserMemory, get_db_session
from backend.auth.oauth import get_authorization_url, exchange_code_for_tokens, get_zoho_user_info
from backend.auth.middleware import get_current_user, sign_user_id, COOKIE_NAME
from backend.models.schemas import UserInfoResponse

logger = logging.getLogger("zoho_chatbot")

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login")
def login():
    """Redirects the user to Zoho's OAuth consent page."""
    auth_url = get_authorization_url()
    logger.info(f"Initiating login, redirecting user to: {auth_url}")
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(
    response: Response,
    code: str = Query(..., description="The authorization code received from Zoho"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Exchanges Zoho code for credentials, upserts the user in the database,
    sets a signed session cookie, and redirects to the React frontend.
    """
    try:
        # 1. Exchange auth code for access & refresh tokens
        tokens = await exchange_code_for_tokens(code)
        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")  # Returned on first auth or prompt=consent
        expires_in = tokens.get("expires_in", 3600)
        
        # Calculate expiry time
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # 2. Query user profile info from Zoho
        zoho_profile = await get_zoho_user_info(access_token)
        zoho_user_id = zoho_profile["zoho_user_id"]
        email = zoho_profile["email"]

        # 3. Check if user already exists
        user_query = await db.execute(
            select(User).where(User.zoho_user_id == zoho_user_id)
        )
        user = user_query.scalars().first()

        if user:
            # Update user info
            user.email = email
            user.set_encrypted_access_token(access_token)
            # Only update refresh token if we got a new one in the request
            if refresh_token:
                user.set_encrypted_refresh_token(refresh_token)
            user.token_expires_at = token_expires_at
            logger.info(f"Updating existing user profile for {email}")
        else:
            # Create a brand new user
            if not refresh_token:
                # If refresh_token is missing, we must throw an error or handle gracefully.
                # In most cases, prompt=consent ensures we always get it on first login.
                logger.warning("No refresh token received during user registration! Proceeding with fallback.")
                refresh_token = "placeholder_refresh_token"
                
            user = User(
                zoho_user_id=zoho_user_id,
                email=email,
                token_expires_at=token_expires_at
            )
            user.set_encrypted_access_token(access_token)
            user.set_encrypted_refresh_token(refresh_token)
            
            db.add(user)
            await db.flush() # Sync database so we can access user.id
            
            # Initialize user long-term memory record
            user_memory = UserMemory(
                user_id=user.id,
                last_project_id=None,
                last_project_name=None,
                frequently_used_projects=[],
                past_queries=[],
                preferences={}
            )
            db.add(user_memory)
            logger.info(f"Registered new user: {email}")

        # Commit transaction
        await db.commit()

        # 4. Generate signed session cookie
        signed_cookie = sign_user_id(user.id)
        
        # 5. Set response cookie
        response = RedirectResponse(url=f"{settings.FRONTEND_URL}/chat")
        response.set_cookie(
            key=COOKIE_NAME,
            value=signed_cookie,
            httponly=True,
            max_age=86400 * 30,  # 30 days
            samesite="lax",      # Essential for local cross-site setups
            secure=False,        # Set to True in production HTTPS environments
            path="/"
        )
        return response

    except Exception as e:
        logger.error(f"Callback authentication flow encountered an error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication callback failed: {str(e)}"
        )


@router.get("/me", response_model=UserInfoResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Returns basic profile information for the logged-in user."""
    return current_user


@router.post("/logout")
async def logout(response: Response):
    """Deletes the session cookie to log the user out."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"success": True, "message": "Logged out successfully."}
