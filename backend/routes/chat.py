"""Chat endpoint — WebSocket (primary) + SSE (fallback) streaming."""

import json
import logging
import time
import threading

from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import JWTError, jwt

from backend.config import MAX_MESSAGE_LENGTH, RATE_LIMIT_ENABLED, JWT_SECRET
from backend.auth.security import get_current_user, ALGORITHM
from backend.rag.graph import run_graph
from backend.rag.generator import stream_tokens, generate_title
from backend.db.store import (
    create_conversation,
    add_message,
    get_messages,
    get_conversation,
    update_conversation_title,
)

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, enabled=RATE_LIMIT_ENABLED)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    conversation_id: str | None = None


def _generate_title_async(conv_id: str, question: str):
    """Generate and save conversation title in a background thread."""
    try:
        title = generate_title(question)
        if title:
            update_conversation_title(conv_id, title)
    except Exception as e:
        logger.warning(f"Title generation failed: {e}")


@router.post("")
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest, user: dict = Depends(get_current_user)):
    query = req.message.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Empty message")

    try:
        conv_id = req.conversation_id

        if conv_id:
            conv = get_conversation(conv_id, user["id"])
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conv = create_conversation(user["id"])
            conv_id = conv["id"]

        add_message(conv_id, "user", query)

        history = get_messages(conv_id)
        # Exclude the current user message (just added above) from context
        history_for_context = [
            {"role": m["role"], "content": m["content"]}
            for m in history[:-1]  # skip last message (current query)
        ][-6:]

        # Only classify + retrieve (no LLM call yet)
        graph_result = run_graph(query, history_for_context)

        sources = graph_result.get("sources", [])
        query_type = graph_result.get("query_type", "course_related")
        is_first_message = len(history) <= 1

        logger.info(
            "chat user=%s conv=%s type=%s sources=%d query=%r",
            user["username"], conv_id[:8], query_type, len(sources), query[:60],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat pre-processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")

    def event_stream():
        stream_start = time.time()
        try:
            yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"
            yield f"data: {json.dumps({'node': 'classify', 'query_type': query_type})}\n\n"

            if sources:
                yield f"data: {json.dumps({'node': 'retrieve', 'sources': sources})}\n\n"

            yield f"data: {json.dumps({'node': 'generate', 'streaming': True})}\n\n"

            if query_type == "off_topic":
                response = (
                    "I appreciate your question, but I'm designed to help with "
                    "**course content** only. I can answer questions about topics "
                    "covered in the course videos. Feel free to ask about those!"
                )
                yield f"data: {json.dumps({'token': response})}\n\n"
                add_message(conv_id, "assistant", response, [])
            else:
                if is_first_message:
                    threading.Thread(
                        target=_generate_title_async,
                        args=(conv_id, query),
                        daemon=True,
                    ).start()

                full_response = []
                token_count = 0
                for token in stream_tokens(query, sources, history_for_context):
                    full_response.append(token)
                    token_count += 1
                    yield f"data: {json.dumps({'token': token})}\n\n"

                response = "".join(full_response)
                add_message(conv_id, "assistant", response, sources)

                elapsed = round(time.time() - stream_start, 2)
                logger.info(
                    "generate conv=%s tokens=%d chars=%d time=%ss",
                    conv_id[:8], token_count, len(response), elapsed,
                )

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'error': 'Response generation failed. Is Ollama running?'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ─── WebSocket Chat ────────────────────────────────────────────

def _authenticate_ws(token: str) -> dict | None:
    """Validate JWT token for WebSocket connections."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        username = payload.get("username")
        if user_id and username:
            return {"id": user_id, "username": username}
    except JWTError:
        pass
    return None


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()

    # First message must be auth token
    try:
        auth_msg = await websocket.receive_json()
        token = auth_msg.get("token", "")
        user = _authenticate_ws(token)
        if not user:
            await websocket.send_json({"error": "Authentication failed"})
            await websocket.close(code=4001)
            return
        await websocket.send_json({"authenticated": True})
    except Exception:
        await websocket.close(code=4001)
        return

    # Message loop
    try:
        while True:
            data = await websocket.receive_json()
            query = (data.get("message", "") or "").strip()
            if not query or len(query) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({"error": "Invalid message"})
                continue

            conv_id = data.get("conversation_id")

            try:
                if conv_id:
                    conv = get_conversation(conv_id, user["id"])
                    if not conv:
                        await websocket.send_json({"error": "Conversation not found"})
                        continue
                else:
                    conv = create_conversation(user["id"])
                    conv_id = conv["id"]

                add_message(conv_id, "user", query)

                history = get_messages(conv_id)
                history_for_context = [
                    {"role": m["role"], "content": m["content"]}
                    for m in history[:-1]
                ][-6:]

                graph_result = run_graph(query, history_for_context)
                sources = graph_result.get("sources", [])
                query_type = graph_result.get("query_type", "course_related")
                is_first_message = len(history) <= 1

                logger.info(
                    "ws_chat user=%s conv=%s type=%s sources=%d query=%r",
                    user["username"], conv_id[:8], query_type, len(sources), query[:60],
                )

                # Send pipeline events
                await websocket.send_json({"conversation_id": conv_id})
                await websocket.send_json({"node": "classify", "query_type": query_type})

                if sources:
                    await websocket.send_json({"node": "retrieve", "sources": sources})

                await websocket.send_json({"node": "generate", "streaming": True})

                if query_type == "off_topic":
                    response = (
                        "I appreciate your question, but I'm designed to help with "
                        "**course content** only. I can answer questions about topics "
                        "covered in the course videos. Feel free to ask about those!"
                    )
                    await websocket.send_json({"token": response})
                    add_message(conv_id, "assistant", response, [])
                else:
                    if is_first_message:
                        threading.Thread(
                            target=_generate_title_async,
                            args=(conv_id, query),
                            daemon=True,
                        ).start()

                    stream_start = time.time()
                    full_response = []
                    token_count = 0
                    for token in stream_tokens(query, sources, history_for_context):
                        full_response.append(token)
                        token_count += 1
                        await websocket.send_json({"token": token})

                    response = "".join(full_response)
                    add_message(conv_id, "assistant", response, sources)

                    elapsed = round(time.time() - stream_start, 2)
                    logger.info(
                        "ws_generate conv=%s tokens=%d chars=%d time=%ss",
                        conv_id[:8], token_count, len(response), elapsed,
                    )

                await websocket.send_json({"done": True})

            except Exception as e:
                logger.error(f"WebSocket chat failed: {e}")
                await websocket.send_json({"error": "Response generation failed. Is Ollama running?"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected user=%s", user["username"])
