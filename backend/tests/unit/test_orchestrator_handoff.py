"""Unit tests for MockAgentOrchestrator._maybe_request_handoff.

The orchestrator's __init__ wires up repositories, providers and Redis, so we
bypass it with object.__new__ and stub only the two collaborators this method
touches: the handoff tool and the agent-event repository.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from app.agents.orchestrator import MockAgentOrchestrator
from app.schemas.conversation import ConversationRead
from app.schemas.lead import LeadRead
from app.schemas.lead_extraction import LeadExtractionResult
from app.schemas.lead_scoring import LeadScoringResult


class _StubHandoffTool:
    def __init__(self) -> None:
        self.calls: list = []

    def execute(self, payload):
        self.calls.append(payload)
        return None  # method falls back to the passed-in conversation


class _StubEventRepo:
    def __init__(self) -> None:
        self.events: list = []

    def create(self, event):
        self.events.append(event)
        return event


def _make_orchestrator() -> MockAgentOrchestrator:
    orch = object.__new__(MockAgentOrchestrator)
    orch._turn_event_count = 0
    orch.handoff_tool = _StubHandoffTool()
    orch.agent_event_repository = _StubEventRepo()
    return orch


def _conversation(*, assigned_to_human: bool = False) -> ConversationRead:
    now = datetime(2026, 1, 1, 12, 0, 0)
    return ConversationRead(
        id=uuid4(),
        lead_id=uuid4(),
        channel="api",
        status="open",
        current_state="new_lead",
        assigned_to_human=assigned_to_human,
        started_at=now,
        updated_at=now,
    )


def _lead(*, phone: str | None = None) -> LeadRead:
    now = datetime(2026, 1, 1, 12, 0, 0)
    return LeadRead(id=uuid4(), phone=phone, created_at=now, updated_at=now)


def _hot_scoring() -> LeadScoringResult:
    return LeadScoringResult(lead_score=90, lead_temperature="hot", score_reasons=["hot"])


def test_already_assigned_to_human_does_not_request_handoff():
    orch = _make_orchestrator()
    conversation = _conversation(assigned_to_human=True)

    result = orch._maybe_request_handoff(conversation, LeadExtractionResult(), None)

    assert result is conversation
    assert orch.handoff_tool.calls == []


def test_user_requested_handoff_uses_user_requested_reason():
    orch = _make_orchestrator()
    conversation = _conversation()

    orch._maybe_request_handoff(conversation, LeadExtractionResult(wants_human=True), None)

    assert orch.handoff_tool.calls[0].reason == "user_requested"


def test_hot_lead_requests_handoff():
    orch = _make_orchestrator()
    conversation = _conversation()

    orch._maybe_request_handoff(conversation, LeadExtractionResult(), _hot_scoring())

    assert orch.handoff_tool.calls[0].reason == "hot_lead"


def test_requires_technical_review_requests_handoff():
    orch = _make_orchestrator()
    conversation = _conversation()
    geospatial = {"solar": {"requires_technical_review": True}}

    orch._maybe_request_handoff(conversation, LeadExtractionResult(), None, geospatial=geospatial)

    assert orch.handoff_tool.calls[0].reason == "technical_review"


def test_analysis_complete_with_contact_does_not_crash():
    """Regression: this branch set reason='analysis_complete_with_contact',
    a value absent from the HandoffReason literal, which made
    RequestHumanHandoffInput raise a ValidationError (HTTP 500)."""
    orch = _make_orchestrator()
    conversation = _conversation()
    # geospatial done (not None) without requiring technical review, lead reachable.
    geospatial: dict = {"solar": {}}

    result = orch._maybe_request_handoff(
        conversation,
        LeadExtractionResult(phone="11999999999"),
        None,
        geospatial=geospatial,
        lead=_lead(phone="11999999999"),
    )

    assert result is conversation
    assert orch.handoff_tool.calls[0].reason == "analysis_complete_with_contact"
    assert orch.agent_event_repository.events[0].event_type == "human_handoff_requested"


def test_no_trigger_returns_conversation_without_handoff():
    orch = _make_orchestrator()
    conversation = _conversation()

    result = orch._maybe_request_handoff(conversation, LeadExtractionResult(), None)

    assert result is conversation
    assert orch.handoff_tool.calls == []


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
