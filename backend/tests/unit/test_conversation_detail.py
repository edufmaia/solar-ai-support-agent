from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.schemas.agent_event import AgentEventRead
from app.schemas.conversation import ConversationRead
from app.schemas.geospatial import GeospatialAnalysisRead
from app.schemas.lead import LeadRead
from app.services.conversation_detail_service import ConversationDetailService


def _now():
    return datetime(2026, 6, 20, tzinfo=UTC)


class _ConvRepo:
    def __init__(self, conv):
        self._conv = conv

    def get_by_id(self, _id):
        return self._conv


class _LeadRepo:
    def __init__(self, lead):
        self._lead = lead
        self.queried = False

    def get_by_id(self, _id):
        self.queried = True
        return self._lead


class _GeoRepo:
    def __init__(self, geo):
        self._geo = geo

    def get_latest_by_lead_id(self, _id):
        return self._geo


class _EventRepo:
    def __init__(self, events):
        self._events = events

    def list_by_conversation_id(self, _id):
        return self._events


def _service(conv, lead=None, geo=None, events=None):
    svc = ConversationDetailService(None)
    svc.conversation_repository = _ConvRepo(conv)
    svc.lead_repository = _LeadRepo(lead)
    svc.geospatial_analysis_repository = _GeoRepo(geo)
    svc.agent_event_repository = _EventRepo(events or [])
    return svc


def _conversation(lead_id):
    return ConversationRead(
        id=uuid4(),
        lead_id=lead_id,
        channel="api",
        status="open",
        current_state="ready_for_pre_analysis",
        assigned_to_human=True,
        started_at=_now(),
        updated_at=_now(),
    )


def test_returns_none_when_conversation_missing():
    assert _service(None).build(uuid4()) is None


def test_builds_full_detail():
    lead_id = uuid4()
    conv = _conversation(lead_id)
    lead = LeadRead(
        id=lead_id,
        name="Ana",
        city="Natal",
        average_energy_bill=Decimal("600"),
        lead_score=80,
        lead_temperature="hot",
        created_at=_now(),
        updated_at=_now(),
    )
    geo = GeospatialAnalysisRead(
        id=uuid4(),
        lead_id=lead_id,
        solar_data_available=True,
        estimated_panel_min=6,
        estimated_panel_max=8,
        estimated_system_kwp=Decimal("3.64"),
        confidence_level="medium",
        requires_technical_review=False,
        created_at=_now(),
    )
    event = AgentEventRead(
        id=uuid4(),
        conversation_id=conv.id,
        event_type="human_handoff_requested",
        event_source="mock_agent_orchestrator",
        payload={"reason": "hot_lead"},
        created_at=_now(),
    )

    detail = _service(conv, lead=lead, geo=geo, events=[event]).build(conv.id)

    assert detail is not None
    assert detail.conversation.assigned_to_human is True
    assert detail.lead.lead_score == 80
    assert detail.lead.lead_temperature == "hot"
    assert detail.geospatial.solar_data_available is True
    assert detail.geospatial.estimated_panel_min == 6
    assert detail.events[0].event_type == "human_handoff_requested"


def test_no_lead_skips_lead_and_geo():
    conv = _conversation(None)
    svc = _service(conv, lead=LeadRead(id=uuid4(), created_at=_now(), updated_at=_now()))
    detail = svc.build(conv.id)
    assert detail is not None
    assert detail.lead is None
    assert detail.geospatial is None
    assert svc.lead_repository.queried is False
