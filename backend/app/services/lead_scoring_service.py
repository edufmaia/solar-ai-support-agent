from decimal import Decimal

from ..schemas.lead_scoring import LeadScoringInput, LeadScoringResult, LeadTemperature


class LeadScoringService:
    def score(self, data: LeadScoringInput) -> LeadScoringResult:
        score = 0
        reasons: list[str] = []

        if data.has_solar_interest:
            score += 20
            reasons.append("Interesse explícito em energia solar")

        if data.intent == "solar_quote":
            score += 25
            reasons.append("Pedido de orçamento ou simulação identificado")
        elif data.intent == "solar_interest":
            score += 15
            reasons.append("Intenção comercial inicial identificada")

        if data.average_energy_bill is not None:
            bill = Decimal(data.average_energy_bill)
            if bill >= Decimal("1000"):
                score += 35
                reasons.append("Conta de energia acima de R$ 1.000")
            elif bill >= Decimal("700"):
                score += 30
                reasons.append("Conta de energia entre R$ 700 e R$ 999")
            elif bill >= Decimal("500"):
                score += 25
                reasons.append("Conta de energia acima de R$ 500")
            elif bill >= Decimal("300"):
                score += 15
                reasons.append("Conta de energia entre R$ 300 e R$ 499")
            else:
                score += 5
                reasons.append("Conta de energia abaixo de R$ 300")

        if data.property_type == "commercial":
            score += 15
            reasons.append("Imóvel comercial identificado")
        elif data.property_type == "residential":
            score += 10
            reasons.append("Imóvel residencial identificado")

        if data.city:
            score += 10
            reasons.append("Cidade informada")

        if data.name:
            score += 5
            reasons.append("Nome do lead informado")

        score = max(0, min(100, score))

        temperature = self._temperature_for(score)

        return LeadScoringResult(
            lead_score=score,
            lead_temperature=temperature,
            score_reasons=reasons,
        )

    def _temperature_for(self, score: int) -> LeadTemperature:
        if score >= 70:
            return "hot"
        if score >= 40:
            return "warm"
        return "cold"

    def apply_geospatial(
        self, base: LeadScoringResult, geospatial: dict | None
    ) -> LeadScoringResult:
        solar = (geospatial or {}).get("solar")
        if not solar or not solar.get("solar_data_available"):
            return base

        delta = 10
        reasons: list[str] = ["Análise solar confirmada para o endereço"]

        kwp_raw = solar.get("estimated_system_kwp")
        kwp = Decimal(str(kwp_raw)) if kwp_raw is not None else None
        if kwp is not None and kwp >= Decimal("10"):
            delta += 15
            reasons.append("Potencial solar alto (>= 10 kWp)")
        elif kwp is not None and kwp >= Decimal("5"):
            delta += 10
            reasons.append("Potencial solar médio (>= 5 kWp)")
        elif kwp is not None and kwp > Decimal("0"):
            delta += 5
            reasons.append("Potencial solar estimado")

        confidence = solar.get("confidence_level")
        if confidence == "high":
            delta += 5
            reasons.append("Alta confiança na análise geoespacial")
        elif confidence == "medium":
            delta += 3
            reasons.append("Confiança média na análise geoespacial")

        if solar.get("requires_technical_review"):
            reasons.append("Requer revisão técnica (consultor humano)")

        new_score = max(0, min(100, base.lead_score + delta))
        return LeadScoringResult(
            lead_score=new_score,
            lead_temperature=self._temperature_for(new_score),
            score_reasons=base.score_reasons + reasons,
        )
