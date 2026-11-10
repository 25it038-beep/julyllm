"""
HS AI SOLUTIONS - JULY INFERENCE ENGINE
llama.cpp Queue Management, Streaming Token Generation, & Identity Injection
Founder: Harshan Seliyan
"""

import time
import asyncio
from typing import List, Dict, Any, Generator, AsyncGenerator, Optional
from app.config import settings
from app.model_loader import model_manager
from app.monitoring import metrics
from app.security import sanitize_input

# Concurrency lock: CPU inference on server executes sequentially to avoid thrashing
_inference_lock = asyncio.Lock()


class InferenceError(Exception):
    pass


class JulyInferenceEngine:
    """
    High-level inference orchestrator.
    Handles prompt construction, system prompt injection,
    sampling controls, and Server-Sent Event streaming.
    """

    @staticmethod
    def build_messages(
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        custom_system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Constructs full message list with persistent JULY system identity."""
        sys_prompt = custom_system_prompt or settings.DEFAULT_SYSTEM_PROMPT
        messages = [{"role": "system", "content": sys_prompt}]

        if conversation_history:
            for msg in conversation_history:
                # Add only user and assistant past messages
                if msg.get("role") in ("user", "assistant"):
                    messages.append({
                        "role": msg["role"],
                        "content": msg.get("content", "")
                    })

        # Append current user prompt
        messages.append({"role": "user", "content": sanitize_input(user_message)})
        return messages

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        max_tokens: int = 512,
        stop: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Non-streaming chat generation under concurrency lock."""
        if not model_manager.is_loaded:
            raise InferenceError("Model is not loaded. Cannot execute inference.")

        start_time = time.time()
        metrics.request_start()

        # Default stop sequences
        stop_tokens = ["<|eot_id|>", "<|im_end|>", "User:", "\nUser"]
        if stop:
            if isinstance(stop, str):
                stop_tokens.append(stop)
            elif isinstance(stop, list):
                stop_tokens.extend(stop)

        async with _inference_lock:
            try:
                if model_manager.is_mock:
                    await asyncio.sleep(0.4)
                    last_msg = messages[-1]["content"] if messages else "Hello"
                    resp_text = (
                        f"[MOCK MODE: Simulated JULY Output] Hello! I am JULY, developed by HS AI Solutions "
                        f"(Founder: Harshan Seliyan). You said: '{last_msg}'. "
                        "Real inference is disabled because MOCK_INFERENCE=true."
                    )
                    duration = time.time() - start_time
                    tok_count = len(resp_text.split())
                    metrics.request_end(duration, tok_count, is_error=False)
                    return {
                        "content": resp_text,
                        "prompt_tokens": sum(len(m["content"].split()) for m in messages),
                        "completion_tokens": tok_count,
                        "latency_ms": round(duration * 1000, 2),
                        "is_mock": True
                    }

                # Direct llama_cpp execution in threadpool to avoid blocking event loop
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: model_manager.llm.create_chat_completion(
                        messages=messages,
                        temperature=temperature,
                        top_p=top_p,
                        top_k=top_k,
                        repeat_penalty=repeat_penalty,
                        max_tokens=min(max_tokens, settings.MAX_TOKENS_LIMIT),
                        stop=stop_tokens
                    )
                )

                duration = time.time() - start_time
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                completion_tokens = usage.get("completion_tokens", len(content.split()))
                prompt_tokens = usage.get("prompt_tokens", 0)

                metrics.request_end(duration, completion_tokens, is_error=False)

                return {
                    "content": content,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "latency_ms": round(duration * 1000, 2),
                    "is_mock": False
                }

            except Exception as e:
                duration = time.time() - start_time
                metrics.request_end(duration, 0, is_error=True)
                raise InferenceError(f"Inference generation error: {e}")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        max_tokens: int = 512,
        stop: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """Streaming chat generation producing text tokens."""
        if not model_manager.is_loaded:
            raise InferenceError("Model is not loaded. Cannot execute streaming inference.")

        start_time = time.time()
        metrics.request_start()
        token_count = 0

        stop_tokens = ["<|eot_id|>", "<|im_end|>", "User:", "\nUser"]
        if stop:
            if isinstance(stop, str):
                stop_tokens.append(stop)
            elif isinstance(stop, list):
                stop_tokens.extend(stop)

        async with _inference_lock:
            try:
                if model_manager.is_mock:
                    last_msg = messages[-1]["content"] if messages else "Hello"
                    mock_words = (
                        f"[MOCK MODE] Hello! I am JULY, the AI assistant developed by HS AI Solutions "
                        f"(Founder: Harshan Seliyan). Received: '{last_msg}'."
                    ).split()
                    for word in mock_words:
                        await asyncio.sleep(0.04)
                        token_count += 1
                        yield word + " "
                    metrics.request_end(time.time() - start_time, token_count, is_error=False)
                    return

                # Streaming generator with llama-cpp
                loop = asyncio.get_running_loop()

                def sync_stream_gen():
                    return model_manager.llm.create_chat_completion(
                        messages=messages,
                        temperature=temperature,
                        top_p=top_p,
                        top_k=top_k,
                        repeat_penalty=repeat_penalty,
                        max_tokens=min(max_tokens, settings.MAX_TOKENS_LIMIT),
                        stop=stop_tokens,
                        stream=True
                    )

                stream = await loop.run_in_executor(None, sync_stream_gen)

                for chunk in stream:
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content_piece = delta.get("content", "")
                    if content_piece:
                        token_count += 1
                        yield content_piece
                        await asyncio.sleep(0.001)  # allow event loop to flush

                metrics.request_end(time.time() - start_time, token_count, is_error=False)

            except Exception as e:
                metrics.request_end(time.time() - start_time, 0, is_error=True)
                raise InferenceError(f"Streaming inference error: {e}")


inference_engine = JulyInferenceEngine()
