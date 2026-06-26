import json

from pydantic import ValidationError

from ...schemas.lead_extraction import LeadExtractionResult

LEAD_FIELDS_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "name": {"type": ["string", "null"]},
        "email": {"type": ["string", "null"]},
        "phone": {"type": ["string", "null"]},
        "city": {"type": ["string", "null"]},
        "address": {"type": ["string", "null"]},
        "property_type": {"type": ["string", "null"], "enum": ["residential", "commercial", None]},
        "average_energy_bill": {"type": ["number", "null"]},
        "intent": {"type": "string", "enum": ["solar_quote", "solar_interest", "general_question"]},
        "has_solar_interest": {"type": "boolean"},
        "wants_human": {"type": "boolean"},
        "geo_consent": {"type": "boolean"},
    },
    "required": ["intent", "has_solar_interest", "wants_human", "geo_consent"],
    "additionalProperties": False,
}

LEAD_FIELDS_TOOL: dict = {
    "name": "record_lead_fields",
    "description": "Registra os dados consolidados do lead extraídos da conversa.",
    "input_schema": LEAD_FIELDS_JSON_SCHEMA,
}


def build_extraction_system_prompt() -> str:
    return (
        "Você extrai dados estruturados de um lead a partir de uma conversa em "
        "português do Brasil entre um assistente de energia solar e um cliente.\n"
        "Leia TODO o histórico e o JSON de dados já conhecidos. Devolva o melhor "
        "valor atual de CADA campo, ou null quando desconhecido. Não invente dados.\n"
        "Atenção a respostas curtas: quando o assistente pergunta algo (ex.: o nome "
        "ou o e-mail) e o cliente responde apenas o valor numa linha (ex.: "
        "'Eduardo Freire Maia' ou 'contato@exemplo.com'), associe esse valor ao "
        "campo perguntado. Preserve valores já conhecidos se não houver correção.\n"
        "average_energy_bill é um número em reais (sem 'R$'). property_type é "
        "'residential', 'commercial' ou null."
    )


def render_known_lead(known_lead: dict | None) -> str:
    return json.dumps(known_lead or {}, ensure_ascii=False, default=str)


def result_from_fields(fields: dict) -> LeadExtractionResult:
    try:
        return LeadExtractionResult.model_validate(fields)
    except ValidationError as exc:
        raise ValueError(f"invalid lead fields: {exc}") from exc
