"""
DataMind AI — FastAPI Backend
Real-time WebSocket + REST API
"""

import json
import uuid
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import aiofiles

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import UPLOAD_DIR
from core.state import AgentState
from agents.orchestrator import analysis_graph, chat_graph

app = FastAPI(title="DataMind AI Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections keyed by session_id
_ws_connections: dict[str, WebSocket] = {}
# Session results cache
_session_results: dict[str, dict] = {}


# ── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _ws_connections[session_id] = websocket
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        _ws_connections.pop(session_id, None)


async def _broadcast(session_id: str, data: dict):
    ws = _ws_connections.get(session_id)
    if ws:
        try:
            await ws.send_json(data)
        except Exception:
            pass


# ── File Upload ───────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    save_path = Path(UPLOAD_DIR) / f"{session_id}{ext}"

    async with aiofiles.open(save_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    return {"session_id": session_id, "filename": file.filename, "path": str(save_path)}


# ── Analysis Pipeline ─────────────────────────────────────────────────────────

@app.post("/api/analyze/{session_id}")
async def run_analysis(session_id: str):
    """Trigger the full multi-agent analysis pipeline."""
    # Find uploaded file
    upload_path = None
    for f in Path(UPLOAD_DIR).glob(f"{session_id}*"):
        upload_path = str(f)
        break

    if not upload_path:
        raise HTTPException(status_code=404, detail="Session file not found. Upload a file first.")

    # Run in background thread (LangGraph is sync)
    loop = asyncio.get_event_loop()

    async def _run_and_stream():
        initial_state = AgentState(
            session_id=session_id,
            file_path=upload_path,
        ).model_dump()

        await _broadcast(session_id, {"type": "status", "message": "🚀 Analysis pipeline started..."})

        def _run_sync():
            return analysis_graph.invoke(initial_state)

        result = await loop.run_in_executor(None, _run_sync)

        # Stream activity log events
        for event in result.get("activity_log", []):
            await _broadcast(session_id, {"type": "agent_activity", "data": event})
            await asyncio.sleep(0.05)

        # Send final result
        serializable = _make_serializable(result)
        _session_results[session_id] = serializable
        await _broadcast(session_id, {"type": "analysis_complete", "data": serializable})

    asyncio.create_task(_run_and_stream())
    return {"message": "Analysis started", "session_id": session_id}


@app.get("/api/results/{session_id}")
async def get_results(session_id: str):
    if session_id not in _session_results:
        raise HTTPException(status_code=404, detail="Results not ready yet")
    return _session_results[session_id]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    question: str


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if req.session_id not in _session_results:
        raise HTTPException(status_code=400, detail="Run analysis first before chatting")

    prev = _session_results[req.session_id]
    state = AgentState(
        session_id=req.session_id,
        user_query=req.question,
        cleaned_df_json=prev.get("cleaned_df_json"),
        schema_info=prev.get("schema_info"),
        chat_history=prev.get("chat_history", []),
    ).model_dump()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: chat_graph.invoke(state))

    # Persist updated chat history
    _session_results[req.session_id]["chat_history"] = result.get("chat_history", [])

    query_result = json.loads(result.get("query_result", "{}"))
    return query_result


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "DataMind AI"}


@app.get("/api/sessions")
async def list_sessions():
    return {"sessions": list(_session_results.keys())}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_serializable(obj):
    """Recursively make object JSON-serializable."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_serializable(i) for i in obj]
    elif hasattr(obj, "isoformat"):
        return obj.isoformat()
    elif isinstance(obj, float) and (obj != obj):  # NaN
        return None
    else:
        try:
            json.dumps(obj)
            return obj
        except Exception:
            return str(obj)
