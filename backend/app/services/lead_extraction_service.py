import re
from decimal import Decimal, InvalidOperation
from unicodedata import normalize

from ..schemas.lead_extraction import LeadExtractionResult
from .lead_extractor import LeadExtractor


class LeadExtractionService(LeadExtractor):
    # (pattern, splits_origin): for self-introductions ("sou ...") a trailing
    # " de <lugar>" is treated as an origin city, not part of the name. The
    # explicit name contexts ("me chamo", "meu nome é") keep the full name so
    # surnames like "de Souza" are preserved.
    NAME_PATTERNS = [
        (re.compile(r"\bme\s+chamo\s+([^,.;]+)", re.IGNORECASE), False),
        (re.compile(r"\bmeu\s+nome\s+[ée]\s+([^,.;]+)", re.IGNORECASE), False),
        (re.compile(r"\bsou\s+(?!de\b|do\b|da\b)([^,.;]+)", re.IGNORECASE), True),
    ]

    CITY_PATTERNS = [
        re.compile(r"\bmoro\s+em\s+([^,.;]+)", re.IGNORECASE),
        re.compile(r"\bsou\s+de\s+([^,.;]+)", re.IGNORECASE),
    ]

    # Origin city in a self-introduction: "sou (a) <nome de 1-3 palavras> de <cidade>".
    # Used only as a fallback when the explicit CITY_PATTERNS find nothing.
    ORIGIN_CITY_PATTERN = re.compile(
        r"\bsou\s+(?:(?:o|a|os|as|um|uma)\s+)?(?:[^,.;\s]+\s+){1,3}de\s+([^,.;]+)",
        re.IGNORECASE,
    )

    LEADING_ARTICLE_PATTERN = re.compile(r"^(?:o|a|os|as|um|uma)\s+", re.IGNORECASE)
    ORIGIN_SPLIT_PATTERN = re.compile(r"\s+de\s+", re.IGNORECASE)

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

    HUMAN_REQUEST_KEYWORDS = [
        "atendente",
        "humano",
        "atendimento humano",
        "com uma pessoa",
        "com alguem",
        "com alguém",
        "pessoa real",
    ]

    GEO_CONSENT_KEYWORDS = [
        "autorizo",
        "pode analisar",
        "pode fazer a analise",
        "faca a analise",
        "quero a analise",
        "pode verificar",
    ]

    # Brazilian phone: optional +55, DDD (2 digits, optional parens), then 8-9
    # subscriber digits with optional space/dot/dash separators.
    PHONE_PATTERN = re.compile(
        r"(?:\+?55\s*)?\(?\d{2}\)?[\s.-]*\d{4,5}[\s.-]?\d{4}"
    )

    # Best-effort address: a logradouro keyword through the end of the clause
    # (stops at ';' or newline). Commas/periods inside are kept.
    ADDRESS_PATTERN = re.compile(
        r"\b(?:rua|avenida|av\.?|travessa|alameda|rodovia|estrada)\b[^;\n]*",
        re.IGNORECASE,
    )

    def extract(self, message: str) -> LeadExtractionResult:
        normalized_message = self._normalize_text(message)

        name = self._extract_name(message)
        city = self._extract_city(message)
        average_energy_bill = self._extract_average_energy_bill(message)
        property_type = self._extract_property_type(normalized_message)
        intent = self._extract_intent(normalized_message)
        has_solar_interest = intent in {"solar_quote", "solar_interest"}
        wants_human = self._detect_wants_human(normalized_message)
        phone = self._extract_phone(message)
        address = self._extract_address(message)
        geo_consent = self._detect_geo_consent(normalized_message)

        return LeadExtractionResult(
            name=name,
            city=city,
            average_energy_bill=average_energy_bill,
            property_type=property_type,
            intent=intent,
            has_solar_interest=has_solar_interest,
            wants_human=wants_human,
            phone=phone,
            address=address,
            geo_consent=geo_consent,
        )

    def _extract_name(self, message: str) -> str | None:
        for pattern, splits_origin in self.NAME_PATTERNS:
            match = pattern.search(message)
            if not match:
                continue

            raw_name = self._strip_leading_article(self._clean_fragment(match.group(1)))
            if splits_origin:
                # "Carla de Natal" -> "Carla" (the origin city is handled separately)
                raw_name = self.ORIGIN_SPLIT_PATTERN.split(raw_name, maxsplit=1)[0].strip()

            formatted = self._format_words(raw_name)
            if formatted:
                return formatted

        return None

    def _extract_city(self, message: str) -> str | None:
        for pattern in self.CITY_PATTERNS:
            match = pattern.search(message)
            if not match:
                continue

            formatted = self._format_words(self._strip_leading_article(self._clean_fragment(match.group(1))))
            if formatted:
                return formatted

        origin = self.ORIGIN_CITY_PATTERN.search(message)
        if origin:
            formatted = self._format_words(self._strip_leading_article(self._clean_fragment(origin.group(1))))
            if formatted:
                return formatted

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

    def _detect_wants_human(self, normalized_message: str) -> bool:
        return any(keyword in normalized_message for keyword in self.HUMAN_REQUEST_KEYWORDS)

    def _detect_geo_consent(self, normalized_message: str) -> bool:
        return any(keyword in normalized_message for keyword in self.GEO_CONSENT_KEYWORDS)

    def _extract_phone(self, message: str) -> str | None:
        match = self.PHONE_PATTERN.search(message)
        if not match:
            return None

        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) in (10, 11, 12, 13):
            return digits

        return None

    def _extract_address(self, message: str) -> str | None:
        match = self.ADDRESS_PATTERN.search(message)
        if not match:
            return None

        address = match.group(0).strip(" ,.;:-")
        return address or None

    @staticmethod
    def _normalize_text(text: str) -> str:
        return normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower().strip()

    @staticmethod
    def _clean_fragment(fragment: str) -> str:
        cleaned = fragment.strip(" ,.;:-")
        cleaned = re.split(r"\b(minha|minhas|meu|meus|quero|tenho|para|e)\b", cleaned, maxsplit=1, flags=re.IGNORECASE)[0]
        cleaned = cleaned.strip(" ,.;:-")
        return cleaned

    @classmethod
    def _strip_leading_article(cls, text: str) -> str:
        return cls.LEADING_ARTICLE_PATTERN.sub("", text).strip()

    @staticmethod
    def _format_words(raw: str) -> str | None:
        words = raw.split()
        if 1 <= len(words) <= 4:
            return " ".join(word.capitalize() for word in words)
        return None
