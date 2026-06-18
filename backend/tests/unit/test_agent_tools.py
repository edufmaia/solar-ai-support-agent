from decimal import Decimal
from uuid import uuid4

from app.schemas.lead import LeadCreate
from app.schemas.lead_scoring import LeadScoringInput, LeadScoringResult
from app.schemas.tools import (
    ClassifyLeadInput,
    RequestHumanHandoffInput,
    SaveLeadInput,
    UpdateLeadInput,
)
from app.tools import (
    ClassifyLeadTool,
    RequestHumanHandoffTool,
    SaveLeadTool,
    UpdateLeadTool,
)


class _FakeLeadRepository:
    def __init__(self):
        self.created = None
        self.updated_basic = None
        self.scored = None
        self.status_updated = None

    def create(self, data: LeadCreate):
        self.created = data
        return "created-lead"

    def update_basic_info(self, lead_id, data: LeadCreate):
        self.updated_basic = (lead_id, data)
        return "updated-lead"

    def update_score(self, lead_id, lead_score, lead_temperature):
        self.scored = (lead_id, lead_score, lead_temperature)
        return "scored-lead"

    def update_status(self, lead_id, status):
        self.status_updated = (lead_id, status)
        return "status-lead"


class _FakeConversationRepository:
    def __init__(self):
        self.handoff_id = None

    def mark_handoff(self, conversation_id):
        self.handoff_id = conversation_id
        return "handed-off-conversation"


class _FakeScoringService:
    def __init__(self, result: LeadScoringResult):
        self.result = result
        self.captured = None

    def score(self, scoring_input: LeadScoringInput) -> LeadScoringResult:
        self.captured = scoring_input
        return self.result


def test_save_lead_tool_creates_lead_from_input():
    repo = _FakeLeadRepository()
    tool = SaveLeadTool(repo)

    out = tool.execute(SaveLeadInput(name="Maria", city="Natal", average_energy_bill=Decimal("650")))

    assert out == "created-lead"
    assert isinstance(repo.created, LeadCreate)
    assert repo.created.name == "Maria"
    assert repo.created.city == "Natal"
    assert repo.created.average_energy_bill == Decimal("650")


def test_update_lead_tool_passes_lead_id_and_fields():
    repo = _FakeLeadRepository()
    tool = UpdateLeadTool(repo)
    lead_id = uuid4()

    out = tool.execute(UpdateLeadInput(lead_id=lead_id, city="Mossoró"))

    assert out == "updated-lead"
    passed_id, passed_data = repo.updated_basic
    assert passed_id == lead_id
    assert isinstance(passed_data, LeadCreate)
    assert passed_data.city == "Mossoró"
    # lead_id is consumed by the tool, not forwarded into the LeadCreate payload;
    # only the provided field is set, the rest default to None
    assert passed_data.name is None
    assert "lead_id" not in passed_data.model_dump()


def test_classify_lead_tool_scores_and_persists():
    repo = _FakeLeadRepository()
    scoring = _FakeScoringService(
        LeadScoringResult(lead_score=82, lead_temperature="hot", score_reasons=["x"])
    )
    tool = ClassifyLeadTool(scoring, repo)
    lead_id = uuid4()

    out = tool.execute(
        ClassifyLeadInput(
            lead_id=lead_id,
            city="Natal",
            average_energy_bill=Decimal("1200"),
            property_type="commercial",
            intent="solar_quote",
            has_solar_interest=True,
        )
    )

    assert out.lead_score == 82
    assert out.lead_temperature == "hot"
    assert scoring.captured.average_energy_bill == Decimal("1200")
    assert repo.scored == (lead_id, 82, "hot")


def test_request_human_handoff_marks_conversation_and_lead():
    lead_repo = _FakeLeadRepository()
    conv_repo = _FakeConversationRepository()
    tool = RequestHumanHandoffTool(conv_repo, lead_repo)
    conversation_id = uuid4()
    lead_id = uuid4()

    out = tool.execute(
        RequestHumanHandoffInput(
            conversation_id=conversation_id,
            lead_id=lead_id,
            reason="user_requested",
        )
    )

    assert out == "handed-off-conversation"
    assert conv_repo.handoff_id == conversation_id
    assert lead_repo.status_updated == (lead_id, "handoff_requested")


def test_request_human_handoff_without_lead_skips_lead_update():
    lead_repo = _FakeLeadRepository()
    conv_repo = _FakeConversationRepository()
    tool = RequestHumanHandoffTool(conv_repo, lead_repo)

    tool.execute(
        RequestHumanHandoffInput(
            conversation_id=uuid4(),
            lead_id=None,
            reason="hot_lead",
        )
    )

    assert lead_repo.status_updated is None


def test_tool_schema_exposes_name_description_and_input_schema():
    tool = SaveLeadTool(_FakeLeadRepository())

    schema = tool.tool_schema()

    assert schema["name"] == "save_lead"
    assert isinstance(schema["description"], str) and schema["description"]
    assert schema["input_schema"]["type"] == "object"
    assert "city" in schema["input_schema"]["properties"]
