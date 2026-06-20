from decimal import Decimal

from sqlalchemy.orm import Session

from ..geocoding import BaseGeocodingProvider, GeocodingProviderError, build_geocoding_provider
from ..llm import BaseLLMProvider, build_llm_provider
from ..repositories import AgentEventRepository, ConversationRepository, GeospatialAnalysisRepository, LeadRepository, MessageRepository
from ..schemas.agent_event import AgentEventCreate
from ..schemas.chat import ChatRequest, ChatResponse
from ..schemas.conversation import ConversationCreate, ConversationRead
from ..schemas.geospatial import GeospatialAnalysisRead
from ..schemas.lead import LeadCreate, LeadRead
from ..schemas.lead_extraction import LeadExtractionResult
from ..schemas.lead_scoring import LeadScoringResult
from ..schemas.tools import (
    ClassifyLeadInput,
    EstimateSolarPotentialInput,
    GeocodeAddressInput,
    RequestHumanHandoffInput,
    SaveLeadInput,
    UpdateLeadInput,
)
from ..solar import BaseSolarProvider, SolarProviderError, build_solar_provider
from ..tools import ClassifyLeadTool, EstimateSolarPotentialTool, GeocodeAddressTool, RequestHumanHandoffTool, SaveLeadTool, UpdateLeadTool
from ..schemas.llm import LLMRequest
from ..schemas.message import MessageCreate
from ..services.lead_extraction_service import LeadExtractionService
from ..services.lead_extractor import LeadExtractor
from ..services.lead_scoring_service import LeadScoringService


class ConversationNotFoundError(Exception):
    """Raised when the requested conversation does not exist."""


class MockAgentOrchestrator:
    EVENT_SOURCE = "mock_agent_orchestrator"

    def __init__(
        self,
        session: Session,
        llm_provider: BaseLLMProvider | None = None,
        lead_extractor: LeadExtractor | None = None,
        geocoding_provider: BaseGeocodingProvider | None = None,
        solar_provider: BaseSolarProvider | None = None,
    ) -> None:
        self.session = session
        self.agent_event_repository = AgentEventRepository(session)
        self.conversation_repository = ConversationRepository(session)
        self.lead_repository = LeadRepository(session)
        self.message_repository = MessageRepository(session)
        self.lead_extraction_service = lead_extractor or LeadExtractionService()
        self.lead_scoring_service = LeadScoringService()
        self.llm_provider = llm_provider or build_llm_provider()
        self.save_lead_tool = SaveLeadTool(self.lead_repository)
        self.update_lead_tool = UpdateLeadTool(self.lead_repository)
        self.classify_lead_tool = ClassifyLeadTool(self.lead_scoring_service, self.lead_repository)
        self.handoff_tool = RequestHumanHandoffTool(
            self.conversation_repository,
            self.lead_repository,
        )
        self.geocoding_provider = geocoding_provider or build_geocoding_provider()
        self.geospatial_analysis_repository = GeospatialAnalysisRepository(session)
        self.geocode_address_tool = GeocodeAddressTool(
            self.geocoding_provider,
            self.geospatial_analysis_repository,
        )
        self.solar_provider = solar_provider or build_solar_provider()
        self.estimate_solar_tool = EstimateSolarPotentialTool(
            self.solar_provider,
            self.geospatial_analysis_repository,
        )

    def handle_chat(self, payload: ChatRequest) -> ChatResponse:
        conversation = self._get_or_create_conversation(payload)

        user_message = self.message_repository.create(
            MessageCreate(
                conversation_id=conversation.id,
                role="user",
                content=payload.message,
                model_provider=None,
                model_name=None,
                input_tokens=0,
                output_tokens=0,
                estimated_cost=Decimal("0"),
            )
        )
        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=conversation.lead_id,
                event_type="user_message_received",
                event_source=self.EVENT_SOURCE,
                payload={
                    "message_id": str(user_message.id),
                    "message_length": len(payload.message),
                },
            )
        )

        extraction = self.lead_extraction_service.extract(payload.message)
        conversation = self._persist_extracted_lead_data(conversation, payload, extraction)
        lead = self.lead_repository.get_by_id(conversation.lead_id) if conversation.lead_id is not None else None
        scoring = self._score_lead(conversation, extraction, lead)
        if scoring is not None and lead is not None:
            updated_lead = self.lead_repository.get_by_id(lead.id)
            if updated_lead is not None:
                lead = updated_lead

        geospatial = self._maybe_run_geocoding(conversation, lead, extraction)

        scoring = self._maybe_apply_geospatial_score(conversation, lead, scoring, geospatial)
        if scoring is not None and lead is not None:
            updated_lead = self.lead_repository.get_by_id(lead.id)
            if updated_lead is not None:
                lead = updated_lead

        conversation = self._maybe_request_handoff(conversation, extraction, scoring, geospatial)

        llm_request = self._build_llm_request(
            conversation=conversation,
            user_message=payload.message,
            extraction=extraction,
            lead=lead,
            scoring=scoring,
            geospatial=geospatial,
        )
        llm_response = self.llm_provider.generate_response(llm_request)

        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=conversation.lead_id,
                event_type=self.llm_provider.event_type,
                event_source=self.llm_provider.event_source,
                payload={
                    "provider": llm_response.provider,
                    "model_name": llm_response.model_name,
                    "input_tokens": llm_response.input_tokens,
                    "output_tokens": llm_response.output_tokens,
                    "estimated_cost": float(llm_response.estimated_cost),
                },
            )
        )

        if llm_response.next_state is not None:
            updated_conversation = self.conversation_repository.update_state(
                conversation.id,
                llm_response.next_state,
            )
            if updated_conversation is not None:
                conversation = updated_conversation

        assistant_message = self.message_repository.create(
            MessageCreate(
                conversation_id=conversation.id,
                role="assistant",
                content=llm_response.content,
                model_provider=llm_response.provider,
                model_name=llm_response.model_name,
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                estimated_cost=llm_response.estimated_cost,
            )
        )
        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=conversation.lead_id,
                event_type="assistant_mock_response_created",
                event_source=self.EVENT_SOURCE,
                payload={
                    "message_id": str(assistant_message.id),
                    "model_provider": llm_response.provider,
                    "model_name": llm_response.model_name,
                },
            )
        )

        return ChatResponse(
            conversation_id=conversation.id,
            response=llm_response.content,
            mode=llm_response.provider,
        )

    def _get_or_create_conversation(self, payload: ChatRequest) -> ConversationRead:
        if payload.conversation_id is None:
            conversation = self.conversation_repository.create(
                ConversationCreate(
                    lead_id=None,
                    channel=payload.channel or "api",
                    status="open",
                    current_state="new_lead",
                    assigned_to_human=False,
                )
            )
            self.agent_event_repository.create(
                AgentEventCreate(
                    conversation_id=conversation.id,
                    lead_id=conversation.lead_id,
                    event_type="conversation_started",
                    event_source=self.EVENT_SOURCE,
                    payload={
                        "channel": conversation.channel,
                        "current_state": conversation.current_state,
                    },
                )
            )
            return conversation

        conversation = self.conversation_repository.get_by_id(payload.conversation_id)
        if conversation is None:
            # Limitation: agent_events.conversation_id is NOT NULL and has a FK to
            # conversations(id), so invalid conversation IDs cannot be persisted
            # in agent_events without changing the schema.
            raise ConversationNotFoundError(str(payload.conversation_id))

        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=conversation.lead_id,
                event_type="conversation_reused",
                event_source=self.EVENT_SOURCE,
                payload={
                    "conversation_id": str(conversation.id),
                    "current_state": conversation.current_state,
                },
            )
        )
        return conversation

    def _persist_extracted_lead_data(
        self,
        conversation: ConversationRead,
        payload: ChatRequest,
        extraction: LeadExtractionResult,
    ) -> ConversationRead:
        if not extraction.has_relevant_data():
            return conversation

        lead_payload = LeadCreate(
            name=extraction.name,
            phone=extraction.phone,
            email=None,
            city=extraction.city,
            state=None,
            address=extraction.address,
            property_type=extraction.property_type,
            average_energy_bill=extraction.average_energy_bill,
            intent=(
                extraction.intent
                if conversation.lead_id is None or extraction.intent != "general_question"
                else None
            ),
            source_channel=payload.channel or conversation.channel or "api",
        )

        lead: LeadRead | None
        event_payload = extraction.to_event_payload()

        if conversation.lead_id is None:
            lead = self.save_lead_tool.execute(SaveLeadInput(**lead_payload.model_dump()))
            linked_conversation = self.conversation_repository.assign_lead(conversation.id, lead.id)
            if linked_conversation is not None:
                conversation = linked_conversation

            self.agent_event_repository.create(
                AgentEventCreate(
                    conversation_id=conversation.id,
                    lead_id=lead.id,
                    event_type="lead_data_extracted",
                    event_source=self.EVENT_SOURCE,
                    payload=event_payload,
                )
            )
            self.agent_event_repository.create(
                AgentEventCreate(
                    conversation_id=conversation.id,
                    lead_id=lead.id,
                    event_type="lead_created",
                    event_source=self.EVENT_SOURCE,
                    payload={
                        "lead_id": str(lead.id),
                        "extracted_fields": event_payload,
                    },
                )
            )
            return conversation

        lead = self.update_lead_tool.execute(
            UpdateLeadInput(lead_id=conversation.lead_id, **lead_payload.model_dump())
        )
        lead_id = lead.id if lead is not None else conversation.lead_id

        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=lead_id,
                event_type="lead_data_extracted",
                event_source=self.EVENT_SOURCE,
                payload=event_payload,
            )
        )
        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=lead_id,
                event_type="lead_updated",
                event_source=self.EVENT_SOURCE,
                payload={
                    "lead_id": str(lead_id),
                    "extracted_fields": event_payload,
                },
            )
        )

        return conversation

    def _score_lead(
        self,
        conversation: ConversationRead,
        extraction: LeadExtractionResult,
        lead: LeadRead | None,
    ) -> LeadScoringResult | None:
        if lead is None:
            return None

        scoring = self.classify_lead_tool.execute(
            ClassifyLeadInput(
                lead_id=lead.id,
                name=lead.name,
                city=lead.city,
                average_energy_bill=lead.average_energy_bill,
                property_type=lead.property_type,
                intent=lead.intent,
                has_solar_interest=(
                    extraction.has_solar_interest
                    or lead.intent in {"solar_interest", "solar_quote"}
                ),
            )
        )
        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=lead.id,
                event_type="lead_scored",
                event_source=self.EVENT_SOURCE,
                payload={
                    "lead_score": scoring.lead_score,
                    "lead_temperature": scoring.lead_temperature,
                    "score_reasons": scoring.score_reasons,
                },
            )
        )
        return scoring

    def _maybe_apply_geospatial_score(
        self,
        conversation: ConversationRead,
        lead: LeadRead | None,
        scoring: LeadScoringResult | None,
        geospatial: dict | None,
    ) -> LeadScoringResult | None:
        if scoring is None or lead is None or geospatial is None:
            return scoring

        new_scoring = self.lead_scoring_service.apply_geospatial(scoring, geospatial)
        if (
            new_scoring.lead_score == scoring.lead_score
            and new_scoring.lead_temperature == scoring.lead_temperature
        ):
            return scoring

        self.lead_repository.update_score(
            lead.id, new_scoring.lead_score, new_scoring.lead_temperature
        )
        geo_reasons = new_scoring.score_reasons[len(scoring.score_reasons):]
        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=lead.id,
                event_type="lead_score_updated",
                event_source=self.EVENT_SOURCE,
                payload={
                    "previous_score": scoring.lead_score,
                    "lead_score": new_scoring.lead_score,
                    "lead_temperature": new_scoring.lead_temperature,
                    "delta": new_scoring.lead_score - scoring.lead_score,
                    "score_reasons": geo_reasons,
                },
            )
        )
        return new_scoring

    def _maybe_request_handoff(
        self,
        conversation: ConversationRead,
        extraction: LeadExtractionResult,
        scoring: LeadScoringResult | None,
        geospatial: dict | None = None,
    ) -> ConversationRead:
        if conversation.assigned_to_human:
            return conversation

        if extraction.wants_human:
            reason = "user_requested"
        elif scoring is not None and scoring.lead_temperature == "hot":
            reason = "hot_lead"
        elif ((geospatial or {}).get("solar") or {}).get("requires_technical_review"):
            reason = "technical_review"
        else:
            return conversation

        updated = self.handoff_tool.execute(
            RequestHumanHandoffInput(
                conversation_id=conversation.id,
                lead_id=conversation.lead_id,
                reason=reason,
            )
        )
        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=conversation.lead_id,
                event_type="human_handoff_requested",
                event_source=self.EVENT_SOURCE,
                payload={
                    "reason": reason,
                    "lead_id": str(conversation.lead_id) if conversation.lead_id else None,
                },
            )
        )
        return updated if updated is not None else conversation

    def _maybe_run_geocoding(
        self,
        conversation: ConversationRead,
        lead: LeadRead | None,
        extraction: LeadExtractionResult,
    ) -> dict | None:
        if not extraction.geo_consent:
            return None
        if lead is None or not lead.address:
            return None
        if self.geospatial_analysis_repository.exists_for_lead(lead.id):
            return None

        try:
            analysis = self.geocode_address_tool.execute(
                GeocodeAddressInput(
                    lead_id=lead.id,
                    conversation_id=conversation.id,
                    address=lead.address,
                )
            )
        except GeocodingProviderError as exc:
            self.agent_event_repository.create(
                AgentEventCreate(
                    conversation_id=conversation.id,
                    lead_id=lead.id,
                    event_type="geospatial_analysis_failed",
                    event_source=self.EVENT_SOURCE,
                    payload={"error": str(exc)},
                )
            )
            return None

        found = analysis.latitude is not None and analysis.longitude is not None
        summary = {
            "found": found,
            "address_confidence": analysis.address_confidence,
            "latitude": float(analysis.latitude) if analysis.latitude is not None else None,
            "longitude": float(analysis.longitude) if analysis.longitude is not None else None,
            "formatted_address": analysis.formatted_address,
        }
        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=lead.id,
                event_type="geospatial_analysis_completed",
                event_source=self.EVENT_SOURCE,
                payload=summary,
            )
        )
        solar = self._maybe_run_solar(conversation, lead, analysis)
        if solar is not None:
            summary["solar"] = solar
        return summary

    def _maybe_run_solar(
        self,
        conversation: ConversationRead,
        lead: LeadRead,
        analysis: GeospatialAnalysisRead,
    ) -> dict | None:
        if analysis.latitude is None or analysis.longitude is None:
            return None

        try:
            updated = self.estimate_solar_tool.execute(
                EstimateSolarPotentialInput(
                    analysis_id=analysis.id,
                    latitude=analysis.latitude,
                    longitude=analysis.longitude,
                    average_energy_bill=lead.average_energy_bill,
                )
            )
        except SolarProviderError as exc:
            self.agent_event_repository.create(
                AgentEventCreate(
                    conversation_id=conversation.id,
                    lead_id=lead.id,
                    event_type="solar_potential_failed",
                    event_source=self.EVENT_SOURCE,
                    payload={"error": str(exc)},
                )
            )
            return None

        if updated is None:
            return None

        summary = {
            "solar_data_available": updated.solar_data_available,
            "estimated_panel_min": updated.estimated_panel_min,
            "estimated_panel_max": updated.estimated_panel_max,
            "estimated_system_kwp": (
                float(updated.estimated_system_kwp)
                if updated.estimated_system_kwp is not None
                else None
            ),
            "confidence_level": updated.confidence_level,
            "requires_technical_review": updated.requires_technical_review,
        }
        self.agent_event_repository.create(
            AgentEventCreate(
                conversation_id=conversation.id,
                lead_id=lead.id,
                event_type="solar_potential_completed",
                event_source=self.EVENT_SOURCE,
                payload=summary,
            )
        )
        return summary

    def _build_llm_request(
        self,
        conversation: ConversationRead,
        user_message: str,
        extraction: LeadExtractionResult,
        lead: LeadRead | None,
        scoring: LeadScoringResult | None,
        geospatial: dict | None = None,
    ) -> LLMRequest:
        return LLMRequest(
            conversation_id=conversation.id,
            user_message=user_message,
            current_state=conversation.current_state,
            lead_data=lead.model_dump(mode="json") if lead is not None else None,
            lead_score=scoring.lead_score if scoring is not None else None,
            lead_temperature=scoring.lead_temperature if scoring is not None else None,
            extracted_data=extraction.to_event_payload(),
            geospatial=geospatial,
        )
