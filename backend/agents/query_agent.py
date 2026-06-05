import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage

from backend.config import settings
from backend.tools.query_tools import (
    list_projects_tool,
    list_tasks_tool,
    get_task_details_tool,
    list_project_members_tool,
    get_task_utilisation_tool
)

logger = logging.getLogger("zoho_chatbot")

# Define the set of query-only tools
QUERY_TOOLS = [
    list_projects_tool,
    list_tasks_tool,
    get_task_details_tool,
    list_project_members_tool,
    get_task_utilisation_tool
]

async def query_agent_node(state: dict, config: dict = None) -> dict:
    """
    Executes the query agent. Injects the long-term memory context
    into the system prompt, binds read tools, and invokes the model.
    """
    messages = state.get("messages", [])
    ltm = state.get("long_term_memory", {})
    
    # Build current user context for the prompt
    context_str = (
        f"- Last project you worked on: {ltm.get('last_project_name', 'N/A')}\n"
        f"- Frequently accessed: {ltm.get('frequently_used_projects', [])}\n"
        f"- Recent queries: {ltm.get('past_queries', [])[-3:]}"
    )

    system_prompt = (
        "You are a helpful project management assistant with access to Zoho Projects.\n"
        "You can only READ data — never create, update, or delete anything.\n\n"
        "User context from previous sessions:\n"
        f"{context_str}\n\n"
        "Use tools to answer the user's question accurately."
    )
    
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0
        )
        
        # Bind tools to the model
        llm_with_tools = llm.bind_tools(QUERY_TOOLS)
        
        # Inject system prompt at start of message list
        full_messages = [SystemMessage(content=system_prompt)] + messages
        
        response = await llm_with_tools.ainvoke(full_messages, config)
        
        return {"messages": [response]}
        
    except Exception as e:
        logger.error(f"Error in query_agent_node: {e}")
        # Return fallback message to prevent crash
        from langchain_core.messages import AIMessage
        return {
            "messages": [AIMessage(content="I encountered an error querying project data. Please try again.")]
        }
