from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class Source(BaseModel):
    video: int
    title: str
    start: float
    end: float
    text: str
    similarity: float


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[Source]
    timestamp: str


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class HealthResponse(BaseModel):
    status: str
    chunks_loaded: int
    embedding_model: str
    llm_model: str
