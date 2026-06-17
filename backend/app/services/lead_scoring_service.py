from decimal import Decimal

from ..schemas.lead_scoring import LeadScoringInput, LeadScoringResult


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

        if score >= 70:
            temperature = "hot"
        elif score >= 40:
            temperature = "warm"
        else:
            temperature = "cold"

        return LeadScoringResult(
            lead_score=score,
            lead_temperature=temperature,
            score_reasons=reasons,
        )
