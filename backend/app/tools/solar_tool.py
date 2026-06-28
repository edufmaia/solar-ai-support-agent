from ..repositories.geospatial_analysis_repository import GeospatialAnalysisRepository
from ..schemas.geospatial import GeospatialAnalysisRead
from ..schemas.tools import EstimateSolarPotentialInput
from ..solar.base import BaseSolarProvider
from .base import AgentTool


class EstimateSolarPotentialTool(AgentTool[EstimateSolarPotentialInput]):
    name = "estimate_solar_potential"
    description = (
        "Estima o potencial solar preliminar a partir das coordenadas do lead e "
        "da conta de energia, atualizando a análise geoespacial."
    )
    input_model = EstimateSolarPotentialInput

    def __init__(
        self,
        solar_provider: BaseSolarProvider,
        geospatial_repository: GeospatialAnalysisRepository,
    ) -> None:
        self.solar_provider = solar_provider
        self.geospatial_repository = geospatial_repository

    def execute(self, payload: EstimateSolarPotentialInput) -> GeospatialAnalysisRead | None:
        result = self.solar_provider.estimate(
            payload.latitude,
            payload.longitude,
            payload.average_energy_bill,
        )
        return self.geospatial_repository.update_solar_data(payload.analysis_id, result)
