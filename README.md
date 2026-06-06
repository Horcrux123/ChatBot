# Zoho Projects AI Chatbot

An AI-powered assistant designed to manage your Zoho Projects tasks and coordinate team activities using natural language. Built with a robust, modern stack leveraging **FastAPI**, **React (Vite)**, **LangGraph**, and **SQLite**.

---

## 🛠️ Architecture Overview

The system utilizes a multi-agent workflow powered by LangGraph, routing read operations and write operations to specialized agent nodes. A Human-in-the-Loop (HIL) mechanism secures write operations, prompting the user for confirmation before executing changes in Zoho.

```
       +---------------------------------------------+
       |               React Frontend                |
       +----------------------|----------------------+
                              | HTTP (CORS) / Session Cookie
       +----------------------v----------------------+
       |               FastAPI Backend               |
       |  +---------------------------------------+  |
       |  |           LangGraph Engine            |  |
       |  |  START -> load_memory -> router_node  |  |
       |  |              /                  \     |  |
       |  |   [Query Agent]             [Action   |  |
       |  |         |                    Agent]   |  |
       |  |    (Query Tools)                |     |  |
       |  |         |                   (HIL Pause|  |
       |  |         |                    Confirm) |  |
       |  |         |                       |     |  |
       |  |         |                 (Action Tool|  |
       |  |         |                     Run)    |  |
       |  |         \                       /     |  |
       |  |          +---> save_memory ----+      |  |
       |  +-------------------|-------------------+  |
       +----------------------|----------------------+
                              | Async (SQLAlchemy)
       +----------------------v----------------------+
       |             SQLite Database                 |
       +---------------------------------------------+
```

---

## 📋 Prerequisites

Before starting, ensure your local environment satisfies:
- **Python**: v3.11 or higher
- **NodeJS**: v18 or higher (with npm)
- **Zoho Account**: Developer or standard Zoho account with Projects subscription access

---

## ⚙️ Zoho API Console Setup

To sync the chatbot with your Zoho Projects instance, you must register the application:

1. Visit the [Zoho API Console](https://api-console.zoho.com/).
2. Click **Add Client** and select **Web Server** client type.
3. Configure the client parameters:
   - **Client Name**: `Zoho Projects AI Chatbot`
   - **Homepage URL**: `http://localhost:5173`
   - **Authorized Redirect URIs**: `http://localhost:8000/auth/callback`
4. Click **Create** to generate your unique **Client ID** and **Client Secret**.
5. Keep this console page open; you will paste these keys into your local `.env` configuration file.

### Required API Scopes
Your application will automatically request the following scopes during the consent flow:
- `ZohoProjects.portals.READ`: Permits listing portals.
- `ZohoProjects.tasks.ALL`: Permits querying, creating, editing, and deleting tasks.
- `ZohoProjects.users.READ`: Permits listing project members.

---

## 🗂️ Environment Configuration

1. Locate `.env` in the root folder.
2. Fill in the missing values as follows:

| Environment Variable | Example Value | Description |
| :--- | :--- | :--- |
| `ZOHO_CLIENT_ID` | `1000.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` | Zoho client ID from API Console. |
| `ZOHO_CLIENT_SECRET` | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | Zoho client secret from API Console. |
| `ZOHO_REDIRECT_URI` | `http://localhost:8000/auth/callback` | Redirect route pointing to local FastAPI server. |
| `ZOHO_ACCOUNTS_URL` | `https://accounts.zoho.com` | Base Accounts domain (use `.eu`, `.in` or `.com.cn` depending on your region). |
| `ZOHO_API_BASE` | `https://projectsapi.zoho.com/restapi` | API Base endpoint of Zoho Projects. |
| `GEMINI_API_KEY` | `AIzaSy...` | Your Google Gemini developer API Key. |
| `SECRET_KEY` | `32_character_random_string_for_security` | Key used to sign session cookies and encrypt stored Zoho tokens. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./zoho_chatbot.db` | Target SQLite database URI. |
| `FRONTEND_URL` | `http://localhost:5173` | Home URL of Vite React server. |

---

## 🚀 Local Installation & Execution

### 1. Backend Setup (FastAPI)

Open your terminal, navigate to the `backend/` directory, and follow these steps:

```bash
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install required dependencies
pip install fastapi uvicorn sqlalchemy aiosqlite httpx langgraph langchain langchain-google-genai cryptography itsdangerous pydantic-settings pydantic

# Run the FastAPI server in development mode
uvicorn main:app --reload --port 8000
```

The FastAPI backend will spin up and initialize tables in the `zoho_chatbot.db` SQLite database automatically on startup.

### 2. Frontend Setup (React + Vite)

Open a new terminal window, navigate to the `frontend/` directory, and perform:

```bash
# Navigate to frontend folder
cd frontend

# Install package dependencies
npm install

# Start Vite React server
npm run dev
```

The React frontend application will launch at `http://localhost:5173/`.

---

## 🧪 Verifying the Chatbot

1. Open your browser and navigate to `http://localhost:5173/`.
2. Click **Login with Zoho**. Authenticate and grant the requested permissions.
3. Once redirected to the `/chat` workspace, test these prompts:
   - *"What projects do I have?"* -> The **Query Agent** should list your projects.
   - *"Show tasks for the first project"* -> The **Query Agent** retrieves tasks, remembering the project from the last message.
   - *"Create a task called API Integration in that project"* -> The **Action Agent** generates a proposed change. A confirmation modal will appear.
   - Click **Cancel** to abort task creation. Re-issue and click **Confirm** to witness actual task insertion.
   - *"Who has the most tasks this month?"* -> Aggregates project logs and returns a member utilization report.
   - **Log out** and log back in to verify that your **long-term memory** (e.g. last accessed project) was successfully restored.

---

## ⚠️ Known Limitations

- **Rate Limits**: The Zoho Projects API enforces rate limiting (typically 100 requests per minute per portal). High-frequency querying will trigger rate limits.
- **Offline Tokens**: If you do not see a `refresh_token` generated during the first login callback, navigate to your Zoho Accounts page and revoke permissions for the app, then log in again. This forces Zoho to show the consent dialog and yield a new refresh token.
- **Portals**: If a user is associated with multiple Zoho Project portals, this implementation defaults to using the very first portal returned by the API.
