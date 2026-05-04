"""Conversation CRUD."""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from backend.auth.security import get_current_user
from backend.db.store import (
    list_conversations,
    get_conversation,
    get_messages,
    delete_conversation,
    create_conversation,
    update_conversation_title,
)
from backend.config import MAX_TITLE_LENGTH

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LENGTH)


@router.get("")
async def get_all(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return list_conversations(user["id"], limit=limit, offset=offset)


@router.post("")
async def create(user: dict = Depends(get_current_user)):
    return create_conversation(user["id"])


@router.get("/{conv_id}")
async def get_one(conv_id: str, user: dict = Depends(get_current_user)):
    conv = get_conversation(conv_id, user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.get("/{conv_id}/messages")
async def get_conv_messages(conv_id: str, user: dict = Depends(get_current_user)):
    conv = get_conversation(conv_id, user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return get_messages(conv_id)


@router.patch("/{conv_id}")
async def rename(conv_id: str, body: RenameRequest, user: dict = Depends(get_current_user)):
    conv = get_conversation(conv_id, user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    update_conversation_title(conv_id, body.title.strip())
    return {"ok": True}


@router.delete("/{conv_id}")
async def delete(conv_id: str, user: dict = Depends(get_current_user)):
    if not delete_conversation(conv_id, user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}
