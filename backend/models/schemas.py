from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

class ChatRequest(BaseModel):
    message: str = Field(description="The user's query or instruction.")
    session_id: str = Field(description="UUID string for the conversation session.")
    confirmed: Optional[bool] = Field(default=None, description="Human-in-the-loop approval confirmation result.")

class ChatResponse(BaseModel):
    reply: str = Field(description="The text reply from the agent.")
    pending_action: Optional[Dict[str, Any]] = Field(default=None, description="Action information requesting user confirmation.")
    requires_confirmation: bool = Field(description="True if the action agent is waiting for user approval.")
    agent_type: str = Field(description="Type of the active agent: 'query' or 'action'.")

class UserInfoResponse(BaseModel):
    id: str = Field(description="The internal user database ID (UUID).")
    zoho_user_id: str = Field(description="The user's Zoho account ID.")
    email: str = Field(description="The email address of the user.")
    created_at: datetime = Field(description="Registration time.")

    model_config = ConfigDict(from_attributes=True)
