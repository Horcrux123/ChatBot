import logging
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import init_db, get_db_session
from backend.auth.middleware import get_current_user
from backend.auth.router import router as auth_router
from backend.models.schemas import ChatRequest, ChatResponse
from backend.graph.graph import app as graph_app

# --- Setup Structured Logging ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("zoho_chatbot")

# --- App Lifespan (Startup / Shutdown) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SQLite database tables...")
    try:
        await init_db()
        logger.info("SQLite database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
    yield
    logger.info("Shutting down Zoho Projects AI Chatbot server...")


# --- FastAPI Initialization ---

app = FastAPI(
    title="Zoho Projects AI Chatbot API",
    description="Backend API for interacting with Zoho Projects via a multi-agent LangGraph system.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware config (allows frontend cookie transmission)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register Sub-routers
app.include_router(auth_router)


# --- API Routes ---

@app.get("/")
def read_root():
    return {"message": "Zoho Projects AI Chatbot API is running."}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Main chat orchestration endpoint.
    Manages LangGraph sessions, resumes on user confirmation/cancellation,
    injects runtime configurations, and processes agent results.
    """
    session_id = payload.session_id
    zoho_client = request.state.zoho_client

    # 1. Resolve portal_id (load dynamically if not stored)
    portal_id = None
    try:
        portals = await zoho_client.get_portals()
        if portals:
            portal_id = portals[0]["id"]
    except Exception as e:
        logger.warning(f"Failed to fetch portals on chat load for user {current_user.email}: {e}")

    # 2. Setup runtime configurations to inject into agent nodes and tools
    config = {
        "configurable": {
            "thread_id": session_id,
            "user_id": current_user.id,
            "zoho_client": zoho_client,
            "portal_id": portal_id,
            "db": db
        }
    }

    try:
        # 3. Resume from HIL Interrupt if user sent a confirmation/cancellation decision
        if payload.confirmed is not None:
            logger.info(f"Resuming thread {session_id} from HIL interrupt. Confirmed status: {payload.confirmed}")
            
            # Write confirmation result to state prior to resuming the hil node
            await graph_app.aupdate_state(
                config,
                {"confirmed": payload.confirmed},
                as_node="hil"
            )
            
            # Execute graph remainder (resume from pause)
            async for _ in graph_app.astream(None, config):
                pass
                
        # 4. Standard Message Ingestion
        else:
            logger.info(f"Ingesting new message on thread {session_id} from user {current_user.email}")
            
            initial_state = {
                "messages": [HumanMessage(content=payload.message)],
                "user_id": current_user.id,
                "session_id": session_id,
                "confirmed": None,
                "pending_action": None,
                "long_term_memory": {}
            }
            
            # Run graph workflow
            async for _ in graph_app.astream(initial_state, config):
                pass

        # 5. Extract output state to package backend response
        graph_state = await graph_app.aget_state(config)
        state_values = graph_state.values
        
        messages = state_values.get("messages", [])
        
        # Walk back to retrieve last AIMessage response text
        reply = "I couldn't generate a response. Please try again."
        for msg in reversed(messages):
            if msg.type == "ai":
                reply = msg.content
                # Strip out raw PENDING_ACTION code blocks so they are not rendered as text to the user
                reply = re.sub(r"PENDING_ACTION:\s*(\{.*\})", "", reply, flags=re.DOTALL).strip()
                break
                
        pending_action = state_values.get("pending_action")
        requires_confirmation = pending_action is not None
        agent_type = state_values.get("agent_type", "query")

        return ChatResponse(
            reply=reply or "Action details stored. Please approve to proceed.",
            pending_action=pending_action,
            requires_confirmation=requires_confirmation,
            agent_type=agent_type
        )

    except Exception as e:
        logger.error(f"Error executing chat workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your message: {str(e)}"
        )
