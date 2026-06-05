import ast
import json
import logging
import re
from typing import Dict, Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from backend.config import settings
from backend.tools.action_tools import create_task_tool, update_task_tool, delete_task_tool

logger = logging.getLogger("zoho_chatbot")

def parse_pending_action(text: str) -> Optional[Dict[str, Any]]:
    """
    Parses the PENDING_ACTION block from the agent response.
    Supports both JSON and python dict formatting for maximum LLM resilience.
    """
    # Regex to find PENDING_ACTION: followed by a JSON-like curly brace block
    match = re.search(r"PENDING_ACTION:\s*(\{.*\})", text, re.DOTALL)
    if not match:
        return None
        
    json_str = match.group(1).strip()
    
    # Try parsing as standard JSON
    try:
        return json.loads(json_str)
    except Exception:
        pass
        
    # Fallback to ast.literal_eval if it's formatted as a Python dictionary (single quotes, etc.)
    try:
        return ast.literal_eval(json_str)
    except Exception as e:
        logger.error(f"Failed to parse PENDING_ACTION structure: {e}. String was: {json_str}")
        
    return None


async def action_agent_node(state: dict, config: RunnableConfig = None) -> dict:
    """
    Manages task actions.
    - If user confirmed == True, executes the stored pending_action and lets LLM summarize.
    - If not confirmed, prompts LLM to output a PENDING_ACTION block and pauses.
    """
    messages = state.get("messages", [])
    confirmed = state.get("confirmed")
    pending_action = state.get("pending_action")
    ltm = state.get("long_term_memory", {})

    # Injected runtime dependencies
    zoho_client = config["configurable"]["zoho_client"]
    portal_id = config["configurable"].get("portal_id")

    # --- Scenario 1: Action Confirmed by User ---
    if confirmed is True and pending_action:
        operation = pending_action.get("operation")
        details = pending_action.get("details", {})
        
        logger.info(f"Executing confirmed action: {operation} with args {details}")
        
        tool_config = {
            "configurable": {
                "zoho_client": zoho_client,
                "portal_id": portal_id
            }
        }
        
        # Programmatic execution of the correct tool based on operation
        try:
            if operation == "create_task":
                tool_output = await create_task_tool.ainvoke(details, config=tool_config)
            elif operation == "update_task":
                tool_output = await update_task_tool.ainvoke(details, config=tool_config)
            elif operation == "delete_task":
                tool_output = await delete_task_tool.ainvoke(details, config=tool_config)
            else:
                tool_output = f"Error: Unknown operation request '{operation}'."
        except Exception as e:
            logger.error(f"Error executing action tool: {e}")
            tool_output = f"Error executing action tool: {str(e)}"
            
        # Create a system message detailing the tool outcome
        system_msg = SystemMessage(
            content=f"System: Action was confirmed by the user. Tool output:\n{tool_output}"
        )
        
        # Let LLM summarize the outcome
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2
        )
        
        summary_prompt = (
            "You are a project management assistant. The user just confirmed the action, "
            "and it has been executed. Summarize the result of the operation friendly and concisely to the user."
        )
        
        # Invoke LLM with original messages + execution report
        response = await llm.ainvoke(
            [SystemMessage(content=summary_prompt)] + messages + [system_msg],
            config
        )
        
        return {
            "messages": [system_msg, response],
            "pending_action": None,
            "confirmed": None  # Reset confirmation flag
        }

    # --- Scenario 2: Action Agent Intent proposal (Pre-confirmation) ---
    context_str = (
        f"- Last project you worked on: {ltm.get('last_project_name', 'N/A')}\n"
        f"- Frequently accessed: {ltm.get('frequently_used_projects', [])}\n"
        f"- Recent queries: {ltm.get('past_queries', [])[-3:]}"
    )

    system_prompt = (
        "You are a project management assistant. You can create, update, and delete tasks.\n"
        "IMPORTANT: Before calling any tool, you MUST output a PENDING_ACTION block in this exact format:\n"
        "PENDING_ACTION: {\n"
        "  \"operation\": \"create_task\" | \"update_task\" | \"delete_task\",\n"
        "  \"details\": { ... all parameters you plan to use ... },\n"
        "  \"human_readable\": \"I will create a task called X in project Y assigned to Z\"\n"
        "}\n"
        "Then STOP and wait. Do not call the tool until confirmation is received.\n\n"
        "User context from previous sessions:\n"
        f"{context_str}\n\n"
        "Write your description of what you will do and output the PENDING_ACTION block."
    )
    
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0
        )
        
        full_messages = [SystemMessage(content=system_prompt)] + messages
        response = await llm.ainvoke(full_messages, config)
        
        # Parse for PENDING_ACTION
        parsed_action = parse_pending_action(response.content)
        
        if parsed_action:
            logger.info(f"Action Agent proposed action: {parsed_action}")
            return {
                "messages": [response],
                "pending_action": parsed_action
            }
        else:
            # If no action block found (clarifying question, normal dialogue, etc.)
            logger.info("Action Agent output normal response without pending action.")
            return {
                "messages": [response],
                "pending_action": None
            }
            
    except Exception as e:
        logger.error(f"Error in action_agent_node: {e}")
        return {
            "messages": [AIMessage(content="I encountered an error trying to process your request. Please try again.")]
        }
