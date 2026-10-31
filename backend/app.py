import os
import sys
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()
load_dotenv(os.path.join(backend_dir, ".env"))

# --- Import your agent router ---
from agent.router import route_query
from db import (
    save_thread,
    save_message,
    get_user_threads,
    get_thread_messages,
    delete_thread,
)

# ============================
# 1. FASTAPI INITIALIZATION
# ============================

app = FastAPI(
    title="L.A.R.A. Backend API",
    description="API for the Legal Analysis & Research Assistant",
    version="1.0.0",
)

# ============================
# 2. CORS CONFIGURATION (FIXED)
# ============================

# IMPORTANT:
# - 5174 is your frontend port
# - both localhost and 127.0.0.1 MUST be allowed
# - exact match is required by browser

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================
# 3. PYDANTIC MODELS
# ============================

class QueryRequest(BaseModel):
    user_query: str
    role: str
    thread_id: str


class QueryResponse(BaseModel):
    final_analysis: str
    thread_id: str


class ChatHistoryRequest(BaseModel):
    user_id: str


class ThreadMessagesRequest(BaseModel):
    thread_id: str


class SaveThreadRequest(BaseModel):
    user_id: str
    thread_id: str
    title: str | None = None


# ============================
# 4. API ENDPOINTS
# ============================

@app.get("/")
def read_root():
    return {"message": "LARA backend is running."}


@app.post("/process_query", response_model=QueryResponse)
async def process_legal_query(request: QueryRequest):
    """
    Main endpoint called by frontend
    """
    try:
        result = route_query(
            role=request.role,
            user_query=request.user_query,
            thread_id=request.thread_id,
        )

        final_analysis = result.get(
            "final_analysis",
            "Sorry, no analysis could be generated.",
        )

        # Save chat
        save_message(request.thread_id, "user", request.user_query)
        save_message(request.thread_id, "bot", final_analysis)

        return QueryResponse(
            final_analysis=final_analysis,
            thread_id=request.thread_id,
        )

    except Exception as e:
        print(f"ERROR processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/get_chat_history")
async def get_chat_history(request: ChatHistoryRequest):
    try:
        threads = get_user_threads(request.user_id)
        return {"threads": threads}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_thread_messages")
async def get_thread_messages_endpoint(request: ThreadMessagesRequest):
    try:
        messages = get_thread_messages(request.thread_id)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save_thread")
async def save_thread_endpoint(request: SaveThreadRequest):
    try:
        save_thread(request.user_id, request.thread_id, request.title)
        return {"message": "Thread saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete_thread/{thread_id}")
async def delete_thread_endpoint(thread_id: str):
    try:
        delete_thread(thread_id)
        return {"message": "Thread deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================
# 5. LOCAL SERVER ENTRY POINT
# ============================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
