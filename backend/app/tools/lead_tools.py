from ..repositories.lead_repository import LeadRepository
from ..schemas.lead import LeadCreate, LeadRead
from ..schemas.lead_scoring import LeadScoringInput, LeadScoringResult
from ..schemas.tools import ClassifyLeadInput, SaveLeadInput, UpdateLeadInput
from ..services.lead_scoring_service import LeadScoringService
from .base import AgentTool


class SaveLeadTool(AgentTool):
    name = "save_lead"
    description = "Cria um novo lead com os dados coletados na conversa."
    input_model = SaveLeadInput

    def __init__(self, lead_repository: LeadRepository) -> None:
        self.lead_repository = lead_repository

    def execute(self, payload: SaveLeadInput) -> LeadRead:
        return self.lead_repository.create(LeadCreate(**payload.model_dump()))


class UpdateLeadTool(AgentTool):
    name = "update_lead"
    description = "Atualiza os dados básicos de um lead existente (campos nulos são ignorados)."
    input_model = UpdateLeadInput

    def __init__(self, lead_repository: LeadRepository) -> None:
        self.lead_repository = lead_repository

    def execute(self, payload: UpdateLeadInput) -> LeadRead | None:
        data = payload.model_dump(exclude={"lead_id"})
        return self.lead_repository.update_basic_info(payload.lead_id, LeadCreate(**data))


class ClassifyLeadTool(AgentTool):
    name = "classify_lead"
    description = "Calcula o score e a temperatura do lead e persiste o resultado."
    input_model = ClassifyLeadInput

    def __init__(
        self,
        scoring_service: LeadScoringService,
        lead_repository: LeadRepository,
    ) -> None:
        self.scoring_service = scoring_service
        self.lead_repository = lead_repository

    def execute(self, payload: ClassifyLeadInput) -> LeadScoringResult:
        scoring_input = LeadScoringInput(
            name=payload.name,
            city=payload.city,
            average_energy_bill=payload.average_energy_bill,
            property_type=payload.property_type,
            intent=payload.intent,
            has_solar_interest=payload.has_solar_interest,
        )
        result = self.scoring_service.score(scoring_input)
        self.lead_repository.update_score(
            payload.lead_id,
            result.lead_score,
            result.lead_temperature,
        )
        return result
