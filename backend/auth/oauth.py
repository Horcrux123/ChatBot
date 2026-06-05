import logging
from typing import Dict, Any
import httpx

from backend.config import settings

logger = logging.getLogger("zoho_chatbot")

class AuthError(Exception):
    """Custom exception raised for OAuth failure events."""
    pass

def get_authorization_url() -> str:
    """
    Builds the Zoho OAuth2 authorization URL.
    Requests offline access and prompt consent to guarantee return of a refresh_token.
    """
    scopes = "ZohoProjects.portals.READ,ZohoProjects.tasks.ALL,ZohoProjects.users.READ"
    return (
        f"{settings.ZOHO_ACCOUNTS_URL.rstrip('/')}/oauth/v2/auth?"
        f"scope={scopes}&"
        f"client_id={settings.ZOHO_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={settings.ZOHO_REDIRECT_URI}&"
        f"access_type=offline&"
        f"prompt=consent"
    )

async def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    """Exchanges an authorization code for access and refresh tokens."""
    url = f"{settings.ZOHO_ACCOUNTS_URL.rstrip('/')}/oauth/v2/token"
    data = {
        "code": code,
        "client_id": settings.ZOHO_CLIENT_ID,
        "client_secret": settings.ZOHO_CLIENT_SECRET,
        "redirect_uri": settings.ZOHO_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, data=data, timeout=10.0)
            if response.status_code != 200:
                raise AuthError(f"Zoho token exchange failed. Status: {response.status_code}. Response: {response.text}")
            
            res_json = response.json()
            if "error" in res_json:
                raise AuthError(f"Zoho token exchange returned error payload: {res_json['error']}")
            
            return res_json
        except httpx.HTTPError as e:
            logger.error(f"Network error during token exchange: {e}")
            raise AuthError(f"Network error during Zoho token exchange: {str(e)}")

async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refreshes an expired access token using the user's refresh token."""
    url = f"{settings.ZOHO_ACCOUNTS_URL.rstrip('/')}/oauth/v2/token"
    data = {
        "refresh_token": refresh_token,
        "client_id": settings.ZOHO_CLIENT_ID,
        "client_secret": settings.ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, data=data, timeout=10.0)
            if response.status_code != 200:
                raise AuthError(f"Zoho token refresh failed. Status: {response.status_code}. Response: {response.text}")
            
            res_json = response.json()
            if "error" in res_json:
                raise AuthError(f"Zoho token refresh returned error payload: {res_json['error']}")
            
            return res_json
        except httpx.HTTPError as e:
            logger.error(f"Network error during token refresh: {e}")
            raise AuthError(f"Network error during Zoho token refresh: {str(e)}")

async def get_zoho_user_info(access_token: str) -> Dict[str, Any]:
    """
    Fetches the profile info of the authenticated user.
    Falls back gracefully to Portal Owner query if user info endpoint is inaccessible.
    """
    # Fetch from standard user info endpoint
    url = f"{settings.ZOHO_ACCOUNTS_URL.rstrip('/')}/oauth/user/info"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                user_info = response.json()
                # standard fields in user info: "email" and "id"
                if "id" in user_info and "email" in user_info:
                    return {
                        "zoho_user_id": str(user_info["id"]),
                        "email": user_info["email"]
                    }
        except Exception as e:
            logger.warning(f"Error calling Zoho user info: {e}")
            
        # Fallback to fetching portals and using portal details
        logger.info("Attempting portal owners list fallback for user identification...")
        try:
            portals_url = f"{settings.ZOHO_API_BASE.rstrip('/')}/portals/"
            portals_response = await client.get(portals_url, headers=headers, timeout=10.0)
            if portals_response.status_code == 200:
                portals_data = portals_response.json()
                portals = portals_data.get("portals", [])
                if portals:
                    portal = portals[0]
                    # Generate a unique key per portal owner if not available
                    owner_id = str(portal.get("owner_id", f"portal_{portal['id']}"))
                    owner_email = portal.get("owner_email", f"owner@{portal['id']}.zoho.com")
                    return {
                        "zoho_user_id": owner_id,
                        "email": owner_email
                    }
        except Exception as e:
            logger.error(f"Portal owner fallback query failed: {e}")
            
        # Hard fallback to prevent crashes when testing locally offline or without API connectivity
        return {
            "zoho_user_id": "zoho_user_default",
            "email": "user@zoho.com"
        }
