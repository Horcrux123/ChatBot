import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import UserMemory, User
from backend.zoho_client import ZohoClient

logger = logging.getLogger("zoho_chatbot")

async def load_long_term_memory(user_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Loads long-term user memory from the SQLite database.
    If no memory record exists, initializes a default record.
    """
    try:
        result = await db.execute(
            select(UserMemory).where(UserMemory.user_id == user_id)
        )
        memory = result.scalars().first()
        
        if not memory:
            # Create a default memory record
            memory = UserMemory(
                user_id=user_id,
                last_project_id=None,
                last_project_name=None,
                frequently_used_projects=[],
                past_queries=[],
                preferences={}
            )
            db.add(memory)
            await db.commit()
            
        return {
            "last_project_id": memory.last_project_id,
            "last_project_name": memory.last_project_name,
            "frequently_used_projects": memory.frequently_used_projects or [],
            "past_queries": memory.past_queries or [],
            "preferences": memory.preferences or {}
        }
    except Exception as e:
        logger.error(f"Error loading long-term memory for user {user_id}: {e}")
        return {
            "last_project_id": None,
            "last_project_name": None,
            "frequently_used_projects": [],
            "past_queries": [],
            "preferences": {}
        }


async def save_long_term_memory(
    user_id: str,
    db: AsyncSession,
    messages: list,
    zoho_client: ZohoClient,
    portal_id: Optional[str] = None
) -> None:
    """
    Saves and updates long-term memory in the database.
    - Appends the last user human query to past_queries (caps at 20)
    - Auto-detects project ID mentions from conversation/tool logs
    - Resolves project names using the Zoho API client
    - Updates project access frequencies and highlights top 5
    """
    try:
        # 1. Fetch memory record
        result = await db.execute(
            select(UserMemory).where(UserMemory.user_id == user_id)
        )
        memory = result.scalars().first()
        if not memory:
            logger.warning(f"No memory record found to save for user {user_id}. Skipping.")
            return

        # 2. Append last human query
        last_human_msg = ""
        for msg in reversed(messages):
            if msg.type == "human" and msg.content.strip():
                last_human_msg = msg.content.strip()
                break

        if last_human_msg:
            past_queries = list(memory.past_queries or [])
            # Avoid duplicate consecutive inputs
            if not past_queries or past_queries[-1] != last_human_msg:
                past_queries.append(last_human_msg)
                # Keep last 20
                memory.past_queries = past_queries[-20:]

        # 3. Detect project context from tool calls/messages
        detected_project_id = None
        
        # Scan through AIMessages with tool calls in history
        for msg in reversed(messages):
            if msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    args = tc.get("args", {})
                    if "project_id" in args and args["project_id"]:
                        detected_project_id = str(args["project_id"])
                        break
            if detected_project_id:
                break
                
        # If we detected a project_id, resolve its name
        if detected_project_id:
            resolved_project_name = None
            try:
                if not portal_id:
                    portals = await zoho_client.get_portals()
                    if portals:
                        portal_id = portals[0]["id"]
                        
                if portal_id:
                    projects = await zoho_client.list_projects(portal_id)
                    for p in projects:
                        if str(p.get("id")) == detected_project_id:
                            resolved_project_name = p.get("name")
                            break
            except Exception as pe:
                logger.warning(f"Could not resolve project name for ID {detected_project_id}: {pe}")
                
            if resolved_project_name:
                memory.last_project_id = detected_project_id
                memory.last_project_name = resolved_project_name
                
                # 4. Update frequently accessed projects (list of dicts)
                freq_list = list(memory.frequently_used_projects or [])
                found = False
                for item in freq_list:
                    if str(item.get("project_id")) == detected_project_id:
                        item["count"] = item.get("count", 0) + 1
                        item["project_name"] = resolved_project_name  # Keep name fresh
                        found = True
                        break
                if not found:
                    freq_list.append({
                        "project_id": detected_project_id,
                        "project_name": resolved_project_name,
                        "count": 1
                    })
                
                # Sort descending by count, slice top 5
                freq_list.sort(key=lambda x: x.get("count", 0), reverse=True)
                memory.frequently_used_projects = freq_list[:5]

        memory.updated_at = datetime.now(timezone.utc)
        db.add(memory)
        await db.commit()
        logger.info(f"Long-term memory updated successfully for user {user_id}.")
        
    except Exception as e:
        logger.error(f"Error saving long-term memory for user {user_id}: {e}", exc_info=True)
        await db.rollback()
