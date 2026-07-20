from fastapi import FastAPI

from app.config import settings
from app.schemas import ChatRequest, ChatResponse, HealthResponse


app = FastAPI(title=settings.app_name)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        conversation_id=request.conversation_id,
        answer="Chat model is not connected yet.",
    )
