from typing import Any

import httpx

from ..config.settings import Settings, get_settings


class OverpassError(Exception):
    """Raised when the Overpass request fails or returns unparseable data."""


class OverpassClient:
    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client

    def _query(self, latitude, longitude) -> str:
        radius = self.settings.footprint_search_radius_m
        timeout = int(self.settings.overpass_timeout_seconds)
        return (
            f"[out:json][timeout:{timeout}];"
            f'(way(around:{radius},{latitude},{longitude})["building"];);'
            f"out geom;"
        )

    def buildings_around(self, latitude, longitude) -> list[list[tuple[float, float]]]:
        query = self._query(latitude, longitude)
        # Overpass is queried via POST (raw query body) with a descriptive
        # User-Agent; the public instance rejects header-less GET requests (406).
        headers = {"User-Agent": self.settings.app_name}
        try:
            if self.client is not None:
                response = self.client.post(
                    self.settings.overpass_base_url, content=query, headers=headers
                )
            else:
                response = httpx.post(
                    self.settings.overpass_base_url,
                    content=query,
                    headers=headers,
                    timeout=self.settings.overpass_timeout_seconds,
                )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OverpassError(str(exc)) from exc

        polygons: list[list[tuple[float, float]]] = []
        for element in data.get("elements", []):
            if element.get("type") != "way":
                continue
            geometry = element.get("geometry") or []
            ring = [(pt["lat"], pt["lon"]) for pt in geometry if "lat" in pt and "lon" in pt]
            if len(ring) >= 3:
                polygons.append(ring)
        return polygons
