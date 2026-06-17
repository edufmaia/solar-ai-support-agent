import re
from decimal import Decimal, InvalidOperation
from unicodedata import normalize

from ..schemas.lead_extraction import LeadExtractionResult


class LeadExtractionService:
    NAME_PATTERNS = [
        re.compile(r"\bme\s+chamo\s+([^,.;]+)", re.IGNORECASE),
        re.compile(r"\bmeu\s+nome\s+[ée]\s+([^,.;]+)", re.IGNORECASE),
        re.compile(r"\bsou\s+(?!de\b|do\b|da\b)([^,.;]+)", re.IGNORECASE),
    ]

    CITY_PATTERNS = [
        re.compile(r"\bmoro\s+em\s+([^,.;]+)", re.IGNORECASE),
        re.compile(r"\bsou\s+de\s+([^,.;]+)", re.IGNORECASE),
    ]

    MONEY_PATTERNS = [
        re.compile(r"r\$\s*(\d+(?:[.,]\d{1,2})?)", re.IGNORECASE),
        re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*reais\b", re.IGNORECASE),
        re.compile(
            r"conta(?:\s+de\s+energia)?(?:\s+\w+){0,4}\s+(\d+(?:[.,]\d{1,2})?)",
            re.IGNORECASE,
        ),
    ]

    SOLAR_QUOTE_KEYWORDS = [
        "orcamento",
        "orçamento",
        "proposta",
        "simulacao",
        "simulação",
        "cotacao",
        "cotação",
    ]

    SOLAR_INTEREST_KEYWORDS = [
        "energia solar",
        "placa solar",
        "placas solares",
        "painel solar",
        "painel",
        "placa",
        "solar",
    ]

    RESIDENTIAL_KEYWORDS = ["casa", "residencia", "residência", "apartamento", "apto"]
    COMMERCIAL_KEYWORDS = ["comercio", "comércio", "empresa", "loja", "galpao", "galpão", "escritorio", "escritório"]

    def extract(self, message: str) -> LeadExtractionResult:
        normalized_message = self._normalize_text(message)

        name = self._extract_name(message)
        city = self._extract_city(message)
        average_energy_bill = self._extract_average_energy_bill(message)
        property_type = self._extract_property_type(normalized_message)
        intent = self._extract_intent(normalized_message)
        has_solar_interest = intent in {"solar_quote", "solar_interest"}

        return LeadExtractionResult(
            name=name,
            city=city,
            average_energy_bill=average_energy_bill,
            property_type=property_type,
            intent=intent,
            has_solar_interest=has_solar_interest,
        )

    def _extract_name(self, message: str) -> str | None:
        for pattern in self.NAME_PATTERNS:
            match = pattern.search(message)
            if not match:
                continue

            raw_name = self._clean_fragment(match.group(1))
            if not raw_name:
                continue

            words = raw_name.split()
            if 1 <= len(words) <= 4:
                return " ".join(word.capitalize() for word in words)

        return None

    def _extract_city(self, message: str) -> str | None:
        for pattern in self.CITY_PATTERNS:
            match = pattern.search(message)
            if not match:
                continue

            raw_city = self._clean_fragment(match.group(1))
            if not raw_city:
                continue

            words = raw_city.split()
            if 1 <= len(words) <= 4:
                return " ".join(word.capitalize() for word in words)

        return None

    def _extract_average_energy_bill(self, message: str) -> Decimal | None:
        for pattern in self.MONEY_PATTERNS:
            match = pattern.search(message)
            if not match:
                continue

            raw_value = match.group(1).replace(".", "").replace(",", ".")
            try:
                value = Decimal(raw_value)
            except InvalidOperation:
                continue

            if value > 0:
                return value

        return None

    def _extract_property_type(self, normalized_message: str) -> str | None:
        if any(keyword in normalized_message for keyword in self.COMMERCIAL_KEYWORDS):
            return "commercial"

        if any(keyword in normalized_message for keyword in self.RESIDENTIAL_KEYWORDS):
            return "residential"

        return None

    def _extract_intent(self, normalized_message: str) -> str:
        if any(keyword in normalized_message for keyword in self.SOLAR_QUOTE_KEYWORDS):
            return "solar_quote"

        if any(keyword in normalized_message for keyword in self.SOLAR_INTEREST_KEYWORDS):
            return "solar_interest"

        return "general_question"

    @staticmethod
    def _normalize_text(text: str) -> str:
        return normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower().strip()

    @staticmethod
    def _clean_fragment(fragment: str) -> str:
        cleaned = fragment.strip(" ,.;:-")
        cleaned = re.split(r"\b(minha|minhas|meu|meus|quero|tenho|para|e)\b", cleaned, maxsplit=1, flags=re.IGNORECASE)[0]
        cleaned = cleaned.strip(" ,.;:-")
        return cleaned
