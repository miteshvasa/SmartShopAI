from tempfile import SpooledTemporaryFile
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import AgentDeps, answer_with_agent, route_query
from app.config import get_settings
from app.db import get_session, init_db
from app.memory import memory_store
from app.pii import redact_pii
from app.schemas import ChatRequest, ChatResponse, TranscriptionResponse

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["DELETE", "GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatResponse:
    session_id = payload.session_id or memory_store.new_session_id()
    sanitized_query, pii_redacted = redact_pii(payload.query)
    context = memory_store.get_context(session_id)
    deps = AgentDeps(
        session=session,
        conversation_context=context,
        customer_preferences=payload.customer_preferences,
    )
    route = await route_query(sanitized_query, deps)
    specialist_answer = await answer_with_agent(route.agent, sanitized_query, deps)
    answer, answer_redacted = redact_pii(specialist_answer.answer)

    memory_store.append(session_id, "customer", sanitized_query)
    memory_store.append(session_id, "assistant", answer)

    return ChatResponse(
        session_id=session_id,
        agent=route.agent,
        answer=answer,
        sources=specialist_answer.sources,
        pii_redacted=pii_redacted or answer_redacted,
    )


@app.delete("/memory/{session_id}")
async def clear_memory(session_id: str) -> dict[str, bool]:
    return {"cleared": memory_store.clear(session_id)}


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(audio: Annotated[UploadFile, File(...)]) -> TranscriptionResponse:
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is required for transcription.")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    file_obj: SpooledTemporaryFile[bytes] = audio.file
    file_obj.seek(0)
    result = await client.audio.transcriptions.create(
        model=settings.whisper_model,
        file=(audio.filename or "audio.webm", file_obj, audio.content_type or "audio/webm"),
    )
    text, pii_redacted = redact_pii(result.text)
    return TranscriptionResponse(text=text, pii_redacted=pii_redacted)
