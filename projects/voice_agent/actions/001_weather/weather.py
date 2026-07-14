"""
Souhrn aktuálního počasí a předpovědi z externí služby.

Výchozí lokalita:
- použije se JARVIS_WEATHER_LOCATION, pokud je nastavena,
- jinak se použije Praha.
"""

from __future__ import annotations

import os

import requests

WEATHER_TRANSLATIONS = {
    "sunny": "slunečno",
    "clear": "jasno",
    "partly cloudy": "polojasno",
    "cloudy": "oblačno",
    "overcast": "zataženo",
    "mist": "opar",
    "fog": "mlha",
    "light rain": "slabý déšť",
    "rain": "déšť",
    "heavy rain": "silný déšť",
    "shower in vicinity": "přeháňky v okolí",
    "light rain shower": "slabé dešťové přeháňky",
    "patchy rain nearby": "místy déšť v okolí",
    "moderate rain": "mírný déšť",
    "patchy light rain": "místy slabý déšť",
    "light snow": "slabé sněžení",
    "snow": "sněžení",
    "moderate snow": "mírné sněžení",
    "patchy snow nearby": "místy sněžení v okolí",
    "thunderstorm": "bouřka",
    "thundery outbreaks possible": "možné bouřky",
}


def _default_location(location: str | None) -> str:
    return (location or os.environ.get("JARVIS_WEATHER_LOCATION") or "Praha").strip()


def _translate_weather_description(description: str) -> str:
    normalized = str(description or "").strip().lower()
    return WEATHER_TRANSLATIONS.get(normalized, normalized)


def _load_weather_payload(location: str | None) -> tuple[str, dict]:
    target = _default_location(location)
    response = requests.get(
        f"https://wttr.in/{target}",
        params={"format": "j1", "lang": "cs"},
        timeout=10,
        headers={"User-Agent": "JARVIS Windows"},
    )
    response.raise_for_status()
    return target, response.json()


def _format_current_weather(target: str, payload: dict) -> str:
    current = (payload.get("current_condition") or [{}])[0]
    temp_c = current.get("temp_C")
    feels_like = current.get("FeelsLikeC")
    weather_desc = ((current.get("weatherDesc") or [{}])[0]).get("value", "")
    humidity = current.get("humidity")
    wind_kmph = current.get("windspeedKmph")

    parts = []
    if temp_c:
        parts.append(f"{temp_c} °C")
    if weather_desc:
        parts.append(_translate_weather_description(weather_desc))
    if feels_like and feels_like != temp_c:
        parts.append(f"pocitově {feels_like} °C")
    if humidity:
        parts.append(f"vlhkost {humidity}%")
    if wind_kmph:
        parts.append(f"vítr {wind_kmph} km/h")

    if not parts:
        return "Informace o počasí momentálně nejsou dostupné."

    return f"Počasí pro {target}: " + ", ".join(parts) + "."


def _format_forecast_day(day: dict) -> str:
    date = day.get("date", "neznámé datum")
    avg_temp = day.get("avgtempC")
    min_temp = day.get("mintempC")
    max_temp = day.get("maxtempC")
    chance_rain = day.get("daily_chance_of_rain")
    chance_snow = day.get("daily_chance_of_snow")

    hourly = day.get("hourly") or []
    noon = hourly[min(len(hourly) - 1, 4)] if hourly else {}
    weather_desc = ((noon.get("weatherDesc") or [{}])[0]).get("value", "")

    parts = []
    if weather_desc:
        parts.append(_translate_weather_description(weather_desc))
    if avg_temp:
        parts.append(f"průměr {avg_temp} °C")
    if min_temp and max_temp:
        parts.append(f"min/max {min_temp}/{max_temp} °C")
    if chance_rain:
        parts.append(f"riziko deště {chance_rain}%")
    if chance_snow and chance_snow != "0":
        parts.append(f"riziko sněžení {chance_snow}%")

    if not parts:
        return f"{date}: bez dostupných detailů"

    return f"{date}: " + ", ".join(parts)


def _format_weather_forecast(target: str, payload: dict, days: int = 3) -> str:
    forecast_days = payload.get("weather") or []
    if not forecast_days:
        return "Předpověď počasí momentálně není dostupná."

    safe_days = max(1, min(int(days or 3), len(forecast_days), 3))
    formatted_days = [_format_forecast_day(day) for day in forecast_days[:safe_days]]
    return f"Předpověď počasí pro {target}: " + "; ".join(formatted_days) + "."


def get_weather_summary(
    location: str | None = None,
    mode: str = "current",
    days: int = 3,
) -> str:
    weather_mode = str(mode or "current").strip().lower()
    try:
        target, payload = _load_weather_payload(location)
        if weather_mode in {"forecast", "predpoved", "předpověď"}:
            return _format_weather_forecast(target, payload, days)
        return _format_current_weather(target, payload)
    except Exception:
        return "Informace o počasí momentálně nejsou dostupné."
