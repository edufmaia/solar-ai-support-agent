from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..agents.orchestrator import ConversationNotFoundError, MockAgentOrchestrator
from ..config.database import get_db_session
from ..llm import LLMProviderConfigurationError, LLMProviderInvocationError
from ..schemas.chat import ChatRequest, ChatResponse
from ..security.rate_limit import enforce_chat_rate_limit

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(enforce_chat_rate_limit)],
)
def chat(payload: ChatRequest, session: Session = Depends(get_db_session)) -> ChatResponse:
    try:
        orchestrator = MockAgentOrchestrator(session)
        return orchestrator.handle_chat(payload)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found",
        ) from exc
    except LLMProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except LLMProviderInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
