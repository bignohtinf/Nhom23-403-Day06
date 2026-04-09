"""
VinFast AI — FastAPI Web Demo
Run: uvicorn web_app:app --reload --port 8000
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from agent_v2 import graph
from langchain_core.messages import HumanMessage

# ── App setup ─────────────────────────────────────────────────────────────
app = FastAPI(title="VinFast AI Demo", version="1.0.0")
TEMPLATES_DIR = Path(__file__).parent / "templates"

# In-memory session store: session_id → LangGraph State
sessions: Dict[str, dict] = {}
_pool = ThreadPoolExecutor(max_workers=4)


# ── Schemas ────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class ResetRequest(BaseModel):
    session_id: str = ""


# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    sid = req.session_id.strip() or str(uuid.uuid4())
    prev_state = sessions.get(sid, {"messages": []})

    # Append user message
    new_state = {
        "messages": list(prev_state["messages"]) + [HumanMessage(content=req.message)]
    }

    # Run LangGraph in thread pool (blocking call)
    loop = asyncio.get_event_loop()
    try:
        result_state = await loop.run_in_executor(_pool, graph.invoke, new_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    sessions[sid] = result_state

    # Last message is the AI reply
    reply = result_state["messages"][-1].content

    # Build session preview from first human message
    all_msgs = result_state["messages"]
    preview = next(
        (m.content[:60] for m in all_msgs if hasattr(m, "type") and m.type == "human"),
        "Cuộc trò chuyện mới",
    )

    return JSONResponse({
        "reply":      reply,
        "session_id": sid,
        "preview":    preview,
    })


@app.post("/api/reset")
async def reset(req: ResetRequest):
    sid = req.session_id.strip()
    sessions.pop(sid, None)
    return {"ok": True, "session_id": sid}


@app.get("/api/sessions")
async def list_sessions():
    result = []
    for sid, state in sessions.items():
        msgs = state.get("messages", [])
        preview = next(
            (m.content[:60] for m in msgs if hasattr(m, "type") and m.type == "human"),
            "Cuộc trò chuyện",
        )
        msg_count = len([m for m in msgs if hasattr(m, "type") and m.type == "human"])
        result.append({
            "session_id": sid,
            "preview":    preview,
            "msg_count":  msg_count,
        })
    return result


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    sessions.pop(session_id, None)
    return {"ok": True}
