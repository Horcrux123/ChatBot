import logging
import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig

from backend.agents.router import router_node
from backend.agents.query_agent import query_agent_node, QUERY_TOOLS
from backend.agents.action_agent import action_agent_node
from backend.memory.short_term import memory_saver
from backend.memory.long_term import load_long_term_memory, save_long_term_memory

logger = logging.getLogger("zoho_chatbot")

# --- LangGraph Graph State Definition ---

class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    agent_type: str            # "query" or "action"
    pending_action: Optional[Dict[str, Any]]
    confirmed: Optional[bool]
    user_id: str
    session_id: str
    long_term_memory: Dict[str, Any]


# --- Graph Nodes ---

async def memory_node(state: GraphState, config: RunnableConfig) -> dict:
    """
    Dual-purpose memory node:
    - At start (messages end with HumanMessage): Loads memory from DB
    - At end (messages end with AIMessage/SystemMessage): Saves memory to DB
    """
    db = config["configurable"]["db"]
    user_id = state["user_id"]
    
    # If long_term_memory is not set, we are in the load phase
    if not state.get("long_term_memory"):
        logger.info(f"Loading long-term memory for user: {user_id}")
        ltm = await load_long_term_memory(user_id, db)
        return {"long_term_memory": ltm}
    else:
        # We are in the save phase
        logger.info(f"Saving long-term memory for user: {user_id}")
        zoho_client = config["configurable"]["zoho_client"]
        portal_id = config["configurable"].get("portal_id")
        await save_long_term_memory(
            user_id=user_id,
            db=db,
            messages=state["messages"],
            zoho_client=zoho_client,
            portal_id=portal_id
        )
        return {}


async def hil_node(state: GraphState, config: RunnableConfig) -> dict:
    """
    Human-in-the-loop node.
    If confirmed is False, it appends a cancellation message and clears active actions.
    If confirmed is True, it does nothing and transitions back to execution.
    """
    confirmed = state.get("confirmed")
    if confirmed is False:
        logger.info("User cancelled the proposed task action.")
        cancel_msg = AIMessage(content="Operation cancelled. No changes were made.")
        return {
            "messages": [cancel_msg],
            "pending_action": None,
            "confirmed": None
        }
    return {}


# --- Routing Decisions ---

def route_memory(state: GraphState) -> str:
    """
    Routes from the memory node.
    If the last message is a HumanMessage, it's the start of a turn, so route to intent classification.
    Otherwise, we just finished processing the turn, so route to END.
    """
    messages = state.get("messages", [])
    if messages and messages[-1].type == "human":
        return "router"
    return END


def route_query_agent(state: GraphState) -> str:
    """Routes to tools if tool calls are present, otherwise goes to memory save."""
    messages = state.get("messages", [])
    if messages and messages[-1].tool_calls:
        return "query_tools"
    return "memory"


def route_action(state: GraphState) -> str:
    """Routes to HIL interrupt if action proposed, otherwise goes to memory save."""
    if state.get("pending_action") is not None:
        return "hil"
    return "memory"


def route_hil(state: GraphState) -> str:
    """Routes to tool execution if confirmed, otherwise goes to cancellation/save."""
    confirmed = state.get("confirmed")
    if confirmed is True:
        return "action_agent"
    return "memory"


# --- Graph Construction & Compilation ---

workflow = StateGraph(GraphState)

# Add all execution nodes
workflow.add_node("memory", memory_node)
workflow.add_node("router", router_node)
workflow.add_node("query_agent", query_agent_node)
workflow.add_node("query_tools", ToolNode(QUERY_TOOLS))
workflow.add_node("action_agent", action_agent_node)
workflow.add_node("hil", hil_node)

# Set up transitions
workflow.add_edge(START, "memory")

workflow.add_conditional_edges(
    "memory",
    route_memory,
    {
        "router": "router",
        END: END
    }
)

workflow.add_conditional_edges(
    "router",
    lambda state: state["agent_type"],
    {
        "query": "query_agent",
        "action": "action_agent"
    }
)

workflow.add_conditional_edges(
    "query_agent",
    route_query_agent,
    {
        "query_tools": "query_tools",
        "memory": "memory"
    }
)
workflow.add_edge("query_tools", "query_agent")

workflow.add_conditional_edges(
    "action_agent",
    route_action,
    {
        "hil": "hil",
        "memory": "memory"
    }
)

workflow.add_conditional_edges(
    "hil",
    route_hil,
    {
        "action_agent": "action_agent",
        "memory": "memory"
    }
)

# Compile graph with memory saver thread storage and interrupt BEFORE HIL
app = workflow.compile(
    checkpointer=memory_saver,
    interrupt_before=["hil"]
)
