"""
HS AI SOLUTIONS - JULY CLOUD AI SCHEMAS
OpenAI-Compatible & Native JULY Pydantic Data Contracts
Founder: Harshan Seliyan
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


# --- Chat Message Models ---
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the author: system, user, assistant")
    content: str = Field(..., description="Content of the message")


# --- OpenAI Compatible Chat Completion ---
class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field("july-3b", description="Model ID")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(40, ge=1)
    repeat_penalty: Optional[float] = Field(1.1, ge=0.5, le=2.0)
    max_tokens: Optional[int] = Field(512, ge=1, le=4096)
    stream: Optional[bool] = Field(False, description="Whether to stream response tokens")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequence(s)")
    conversation_id: Optional[str] = Field(None, description="Optional conversation session ID")


class ChatChoice(BaseModel):
    index: int
    message: Optional[ChatMessage] = None
    delta: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Optional[UsageInfo] = None


# --- Text Completion Models ---
class CompletionRequest(BaseModel):
    model: Optional[str] = "july-3b"
    prompt: str = Field(..., description="The prompt string")
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    top_k: Optional[int] = 40
    repeat_penalty: Optional[float] = 1.1
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None


class CompletionChoice(BaseModel):
    text: str
    index: int
    finish_reason: Optional[str] = "stop"


class CompletionResponse(BaseModel):
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: Optional[UsageInfo] = None


# --- Native JULY Chat Models ---
class JulyChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32768, description="User prompt text")
    conversation_id: Optional[str] = Field(None, description="Session ID for multi-turn history")
    system_prompt: Optional[str] = Field(None, description="Custom system instruction override")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(40, ge=1)
    repeat_penalty: Optional[float] = Field(1.1, ge=0.5, le=2.0)
    max_tokens: Optional[int] = Field(512, ge=1, le=4096)
    stream: Optional[bool] = Field(False, description="Stream Server-Sent Events")


class JulyChatResponse(BaseModel):
    response: str
    conversation_id: str
    model: str = "JULY 3B"
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    is_mock: bool = False


# --- Monitoring & Status Models ---
class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    uptime_seconds: float
    memory_available_mb: float
    memory_used_mb: float
    cpu_percent: float
    is_mock: bool
    version: str


class StatusResponse(BaseModel):
    app: str
    version: str
    organization: str
    founder: str
    model_status: str
    model_path: str
    model_architecture: Optional[str] = None
    quantization: Optional[str] = None
    parameters: Optional[str] = None
    context_length: Optional[int] = None
    threads: int
    active_requests: int
    total_requests: int
    total_tokens_generated: int
    average_latency_ms: float
    generation_speed_tps: float
    error_count: int
    memory_system_mb: float
    memory_available_mb: float
    is_mock: bool


class ModelInfoResponse(BaseModel):
    model_name: str
    identity: str
    founder: str
    architecture: str
    quantization: str
    estimated_parameters: str
    context_length: int
    threads_configured: int
    is_loaded: bool
    is_mock: bool
    metadata: Dict[str, Any] = {}


# --- Conversation Storage Models ---
class ConversationSummary(BaseModel):
    conversation_id: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationDetail(BaseModel):
    conversation_id: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str
