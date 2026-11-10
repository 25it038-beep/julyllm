"""
HS AI SOLUTIONS - JULY CLOUD AI FASTAPI BACKEND
High-Performance Inference Server for Render Cloud
Founder: Harshan Seliyan
"""

import time
import json
import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import (
    ChatCompletionRequest, ChatCompletionResponse, ChatChoice, ChatMessage, UsageInfo,
    CompletionRequest, CompletionResponse, CompletionChoice,
    JulyChatRequest, JulyChatResponse,
    HealthResponse, StatusResponse, ModelInfoResponse,
    ConversationSummary, ConversationDetail
)
from app.security import verify_api_key, verify_admin_key
from app.model_loader import model_manager, ModelLoadError
from app.inference import inference_engine, InferenceError
from app.conversations import conversation_manager
from app.monitoring import metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Service lifecycle: initializes model on startup, cleans up on shutdown."""
    print(f"==================================================")
    print(f"       JULY CLOUD AI - HS AI SOLUTIONS            ")
    print(f"       Founder: {settings.FOUNDER}                ")
    print(f"       Environment: {settings.ENVIRONMENT}        ")
    print(f"==================================================")

    # Initialize model asynchronously so server responds to health checks immediately
    def start_loader():
        try:
            model_manager.load()
        except Exception as e:
            print(f"[HS JULY ERROR] Model startup load failed: {e}")

    # Launch loading task
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, start_loader)

    yield

    # Clean shutdown
    print("[HS JULY SHUTDOWN] Unloading models and reclaiming resources...")
    model_manager.unload()


app = FastAPI(
    title="JULY Cloud AI Infrastructure",
    description="Remote Cloud Inference Engine for JULY 3B GGUF Model by HS AI Solutions",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Enable CORS for web clients & dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Root & Health Endpoints ---
@app.get("/", tags=["General"])
async def root():
    return {
        "service": settings.APP_NAME,
        "organization": settings.ORGANIZATION,
        "founder": settings.FOUNDER,
        "status": "online",
        "documentation": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Liveness & readiness probe for Render and container orchestrators."""
    snap = metrics.get_snapshot()
    is_ready = model_manager.is_loaded
    return HealthResponse(
        status="ready" if is_ready else "initializing",
        model_loaded=is_ready,
        model_name="JULY-3B",
        uptime_seconds=snap["uptime_seconds"],
        memory_available_mb=snap["memory_available_mb"],
        memory_used_mb=snap["memory_used_mb"],
        cpu_percent=snap["cpu_percent"],
        is_mock=model_manager.is_mock,
        version=settings.APP_VERSION
    )


@app.get("/v1/status", response_model=StatusResponse, tags=["Monitoring"])
async def get_system_status(user: str = Depends(verify_api_key)):
    """Detailed runtime metrics, memory allocation, and inference throughput."""
    snap = metrics.get_snapshot()
    meta = model_manager.model_metadata
    return StatusResponse(
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        organization=settings.ORGANIZATION,
        founder=settings.FOUNDER,
        model_status="ready" if model_manager.is_loaded else "loading_or_unloaded",
        model_path=model_manager.model_path,
        model_architecture=meta.get("architecture"),
        quantization=meta.get("quantization"),
        parameters=meta.get("parameter_label", "3B"),
        context_length=meta.get("context_length", settings.N_CTX),
        threads=settings.N_THREADS,
        active_requests=snap["active_requests"],
        total_requests=snap["total_requests"],
        total_tokens_generated=snap["total_tokens_generated"],
        average_latency_ms=snap["average_latency_ms"],
        generation_speed_tps=snap["generation_speed_tps"],
        error_count=snap["error_count"],
        memory_system_mb=snap["memory_total_mb"],
        memory_available_mb=snap["memory_available_mb"],
        is_mock=model_manager.is_mock
    )


@app.get("/v1/models", tags=["OpenAI Compatible"])
async def list_models(user: str = Depends(verify_api_key)):
    """OpenAI-compatible models catalog."""
    return {
        "object": "list",
        "data": [
            {
                "id": "july-3b",
                "object": "model",
                "created": 1730000000,
                "owned_by": "hs-ai-solutions",
                "permission": [],
                "root": "july-3b",
                "parent": None
            }
        ]
    }


@app.get("/v1/model/info", response_model=ModelInfoResponse, tags=["Model"])
async def model_info(user: str = Depends(verify_api_key)):
    """Deep inspection data of active GGUF checkpoint and model identity."""
    meta = model_manager.model_metadata
    return ModelInfoResponse(
        model_name="JULY 3B",
        identity=f"JULY developed by {settings.ORGANIZATION}",
        founder=settings.FOUNDER,
        architecture=meta.get("architecture", "llama"),
        quantization=meta.get("quantization", "Q4_K_M"),
        estimated_parameters=meta.get("parameter_label", "3B"),
        context_length=meta.get("context_length", settings.N_CTX),
        threads_configured=settings.N_THREADS,
        is_loaded=model_manager.is_loaded,
        is_mock=model_manager.is_mock,
        metadata={k: v for k, v in meta.items() if not k.startswith("_") and k != "sample_tensors"}
    )


# --- Native JULY Chat Endpoint with Memory ---
@app.post("/v1/chat", response_model=JulyChatResponse, tags=["JULY Native"])
async def native_chat(req: JulyChatRequest, user: str = Depends(verify_api_key)):
    """
    Simplified chat interface designed for the PowerShell client.
    Handles conversation session retrieval, system prompt formatting, and optional SSE streaming.
    """
    conv_id = req.conversation_id or str(uuid.uuid4())

    # Retrieve prior conversation messages
    history = conversation_manager.get_messages(conv_id, limit=20)
    messages = inference_engine.build_messages(
        user_message=req.message,
        conversation_history=history,
        custom_system_prompt=req.system_prompt
    )

    if req.stream:
        async def stream_generator():
            full_response = []
            try:
                async for token in inference_engine.stream_chat(
                    messages=messages,
                    temperature=req.temperature,
                    top_p=req.top_p,
                    top_k=req.top_k,
                    repeat_penalty=req.repeat_penalty,
                    max_tokens=req.max_tokens
                ):
                    full_response.append(token)
                    payload = json.dumps({"token": token, "conversation_id": conv_id})
                    yield f"data: {payload}\n\n"

                # Persist completed messages to conversation memory
                conversation_manager.add_message(conv_id, "user", req.message)
                conversation_manager.add_message(conv_id, "assistant", "".join(full_response))
                yield "data: [DONE]\n\n"
            except Exception as e:
                err_payload = json.dumps({"error": str(e), "conversation_id": conv_id})
                yield f"data: {err_payload}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Non-streaming response
    try:
        res = await inference_engine.generate_chat(
            messages=messages,
            temperature=req.temperature,
            top_p=req.top_p,
            top_k=req.top_k,
            repeat_penalty=req.repeat_penalty,
            max_tokens=req.max_tokens
        )
        # Store in conversation database
        conversation_manager.add_message(conv_id, "user", req.message)
        conversation_manager.add_message(conv_id, "assistant", res["content"])

        return JulyChatResponse(
            response=res["content"],
            conversation_id=conv_id,
            model="JULY 3B",
            prompt_tokens=res["prompt_tokens"],
            completion_tokens=res["completion_tokens"],
            latency_ms=res["latency_ms"],
            is_mock=res["is_mock"]
        )
    except InferenceError as ie:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(ie))


# --- OpenAI Compatible Chat Completions ---
@app.post("/v1/chat/completions", tags=["OpenAI Compatible"])
async def chat_completions(req: ChatCompletionRequest, user: str = Depends(verify_api_key)):
    """Standard OpenAI-compatible Chat Completion endpoint."""
    # Ensure system prompt is present
    has_system = any(m.role == "system" for m in req.messages)
    messages_payload = []
    if not has_system:
        messages_payload.append({"role": "system", "content": settings.DEFAULT_SYSTEM_PROMPT})
    for m in req.messages:
        messages_payload.append({"role": m.role, "content": m.content})

    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    if req.stream:
        async def event_generator():
            try:
                async for token in inference_engine.stream_chat(
                    messages=messages_payload,
                    temperature=req.temperature,
                    top_p=req.top_p,
                    top_k=req.top_k,
                    repeat_penalty=req.repeat_penalty,
                    max_tokens=req.max_tokens,
                    stop=req.stop if isinstance(req.stop, list) else ([req.stop] if req.stop else None)
                ):
                    chunk = {
                        "id": req_id,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": "july-3b",
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": token},
                                "finish_reason": None
                            }
                        ]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

                # Send final stop chunk
                done_chunk = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": "july-3b",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }
                    ]
                }
                yield f"data: {json.dumps(done_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                err_chunk = {"error": {"message": str(e), "type": "server_error"}}
                yield f"data: {json.dumps(err_chunk)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    try:
        res = await inference_engine.generate_chat(
            messages=messages_payload,
            temperature=req.temperature,
            top_p=req.top_p,
            top_k=req.top_k,
            repeat_penalty=req.repeat_penalty,
            max_tokens=req.max_tokens,
            stop=req.stop if isinstance(req.stop, list) else ([req.stop] if req.stop else None)
        )
        return ChatCompletionResponse(
            id=req_id,
            created=created_ts,
            model="july-3b",
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=res["content"]),
                    finish_reason="stop"
                )
            ],
            usage=UsageInfo(
                prompt_tokens=res["prompt_tokens"],
                completion_tokens=res["completion_tokens"],
                total_tokens=res["prompt_tokens"] + res["completion_tokens"]
            )
        )
    except InferenceError as ie:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(ie))


# --- OpenAI Compatible Text Completions ---
@app.post("/v1/completions", tags=["OpenAI Compatible"])
async def text_completions(req: CompletionRequest, user: str = Depends(verify_api_key)):
    """Standard OpenAI-compatible raw prompt completion endpoint."""
    messages = [
        {"role": "system", "content": settings.DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": req.prompt}
    ]
    req_id = f"cmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    try:
        res = await inference_engine.generate_chat(
            messages=messages,
            temperature=req.temperature,
            top_p=req.top_p,
            top_k=req.top_k,
            repeat_penalty=req.repeat_penalty,
            max_tokens=req.max_tokens,
            stop=req.stop if isinstance(req.stop, list) else ([req.stop] if req.stop else None)
        )
        return CompletionResponse(
            id=req_id,
            created=created_ts,
            model="july-3b",
            choices=[
                CompletionChoice(
                    text=res["content"],
                    index=0,
                    finish_reason="stop"
                )
            ],
            usage=UsageInfo(
                prompt_tokens=res["prompt_tokens"],
                completion_tokens=res["completion_tokens"],
                total_tokens=res["prompt_tokens"] + res["completion_tokens"]
            )
        )
    except InferenceError as ie:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(ie))


# --- Conversation Management Endpoints ---
@app.get("/v1/conversations", tags=["Conversations"])
async def list_conversations(limit: int = 50, user: str = Depends(verify_api_key)):
    """Lists saved conversation sessions."""
    return conversation_manager.list_conversations(limit=limit)


@app.get("/v1/conversations/{conversation_id}", tags=["Conversations"])
async def get_conversation(conversation_id: str, limit: int = 100, user: str = Depends(verify_api_key)):
    """Retrieves full message history of a specific conversation."""
    msgs = conversation_manager.get_messages(conversation_id, limit=limit)
    if not msgs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found or empty.")
    return {"conversation_id": conversation_id, "messages": msgs}


@app.delete("/v1/conversations/{conversation_id}", tags=["Conversations"])
async def delete_conversation(conversation_id: str, user: str = Depends(verify_api_key)):
    """Deletes a conversation session and all its stored messages."""
    deleted = conversation_manager.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return {"status": "success", "deleted_conversation_id": conversation_id}


# --- Administrative Endpoints ---
@app.post("/admin/model/reload", tags=["Administration"])
async def reload_model(admin: str = Depends(verify_admin_key)):
    """Administrative reload of model weights."""
    try:
        model_manager.unload()
        model_manager.load()
        return {"status": "success", "message": "Model reloaded successfully."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Reload failed: {e}")


@app.post("/admin/model/unload", tags=["Administration"])
async def unload_model(admin: str = Depends(verify_admin_key)):
    """Administrative eviction of model weights to free RAM."""
    model_manager.unload()
    return {"status": "success", "message": "Model unloaded and RAM reclaimed."}
