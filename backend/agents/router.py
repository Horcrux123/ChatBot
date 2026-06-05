import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage

from backend.config import settings

logger = logging.getLogger("zoho_chatbot")

async def router_node(state: dict, config: dict = None) -> dict:
    """
    Classifies the user's query into 'query' or 'action' depending on whether
    they want to read information or perform a write/mutation action.
    """
    messages = state.get("messages", [])
    user_message = ""
    
    # Find the last human message
    for msg in reversed(messages):
        if msg.type == "human":
            user_message = msg.content
            break
            
    if not user_message:
        logger.warning("No user message found in state for routing. Defaulting to 'query'.")
        return {"agent_type": "query"}
        
    system_prompt = (
        "You are a router. Given the user message, respond with exactly one word:\n"
        "'query' if the user wants to READ information (list, show, get, who, how many),\n"
        "'action' if the user wants to WRITE data (create, update, delete, assign, change).\n"
        f"User message: {user_message}"
    )
    
    try:
        # Initialize LLM with low temperature for routing consistency
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0
        )
        
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])
        decision = response.content.strip().lower()
        logger.info(f"Router classified message: '{user_message}' -> '{decision}'")
        
        if "action" in decision:
            return {"agent_type": "action"}
        else:
            return {"agent_type": "query"}
            
    except Exception as e:
        logger.error(f"Error in router_node: {e}. Defaulting to 'query'.")
        return {"agent_type": "query"}
