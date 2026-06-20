from typing import Any


def geospatial_prompt_section(geospatial: dict[str, Any] | None) -> str:
    """Format the geospatial/solar pre-analysis for the LLM prompt.

    Returns an empty string when there is nothing useful to report, so the
    prompt stays clean before any analysis has run.
    """
    if not geospatial:
        return ""

    solar = geospatial.get("solar") or {}
    lines: list[str] = []

    if geospatial.get("formatted_address"):
        lines.append(f"  - Endereço analisado: {geospatial['formatted_address']}")

    if solar.get("solar_data_available"):
        panel_min = solar.get("estimated_panel_min")
        panel_max = solar.get("estimated_panel_max")
        if panel_min and panel_max:
            lines.append(
                f"  - Estimativa preliminar de placas: entre {panel_min} e {panel_max}"
            )
        if solar.get("estimated_system_kwp"):
            lines.append(
                f"  - Potência estimada do sistema: aproximadamente {solar['estimated_system_kwp']} kWp"
            )
        if solar.get("confidence_level"):
            lines.append(f"  - Confiança da estimativa: {solar['confidence_level']}")
        if solar.get("requires_technical_review"):
            lines.append("  - Requer revisão técnica de um especialista")

    if not lines:
        return ""

    return "- Pré-análise geoespacial/solar (preliminar):\n" + "\n".join(lines) + "\n"
