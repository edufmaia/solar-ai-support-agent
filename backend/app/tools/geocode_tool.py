from ..geocoding.base import BaseGeocodingProvider
from ..repositories.geospatial_analysis_repository import GeospatialAnalysisRepository
from ..schemas.geospatial import GeospatialAnalysisCreate, GeospatialAnalysisRead
from ..schemas.tools import GeocodeAddressInput
from .base import AgentTool


class GeocodeAddressTool(AgentTool[GeocodeAddressInput]):
    name = "geocode_address"
    description = "Converte o endereço do lead em coordenadas e registra a análise geoespacial."
    input_model = GeocodeAddressInput

    def __init__(
        self,
        geocoding_provider: BaseGeocodingProvider,
        geospatial_repository: GeospatialAnalysisRepository,
    ) -> None:
        self.geocoding_provider = geocoding_provider
        self.geospatial_repository = geospatial_repository

    def execute(self, payload: GeocodeAddressInput) -> GeospatialAnalysisRead:
        result = self.geocoding_provider.geocode(payload.address)
        return self.geospatial_repository.create(
            GeospatialAnalysisCreate(
                lead_id=payload.lead_id,
                conversation_id=payload.conversation_id,
                raw_address=payload.address,
                formatted_address=result.formatted_address,
                latitude=result.latitude,
                longitude=result.longitude,
                address_confidence=result.address_confidence,
                raw_response=result.raw_response,
            )
        )
