from __future__ import annotations

import asyncio
import urllib.parse
from typing import Dict

import requests

from apps.compack.modules.tools import Tool


class WeatherTool(Tool):
    """Keyless weather fetcher using wttr.in."""

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "指定された地域の天気を取得します。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {"location": {"type": "string", "description": "地域名（例: 東京/奈良市）"}},
            "required": ["location"],
        }

    async def execute(self, location: str) -> Dict[str, object]:
        if not location:
            raise ValueError("location is required")

        encoded = urllib.parse.quote(location)
        url = f"https://wttr.in/{encoded}?format=j1"
        
        # Retry logic with increased timeout
        max_retries = 2
        timeout = 12
        
        for attempt in range(max_retries + 1):
            try:
                resp = await asyncio.to_thread(requests.get, url, timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
                
                # Validate response structure
                if not isinstance(data, dict) or not data.get("current_condition"):
                    raise ValueError("Invalid weather data structure")
                
                summary = self._summarize(data)
                return summary
                
            except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                if attempt < max_retries:
                    # Wait before retry
                    await asyncio.sleep(1)
                    continue
                else:
                    # Final attempt failed - return error info instead of false data
                    return {
                        "summary": f"天気情報の取得に失敗しました: {str(e)}",
                        "current": {"tempC": None, "feelsLikeC": None, "description": "取得失敗"},
                        "today": {"date": None, "maxtempC": None, "mintempC": None, "chanceOfRain": None},
                        "tomorrow": {},
                        "source": "wttr.in (error)",
                        "error": str(e)
                    }

    def _summarize(self, payload: Dict) -> Dict[str, object]:
        current = (payload.get("current_condition") or [{}])[0]
        weather = payload.get("weather") or []
        today = weather[0] if weather else {}
        tomorrow = weather[1] if len(weather) > 1 else {}

        def extract_day(day: Dict) -> Dict[str, object]:
            hourly = day.get("hourly") or []
            rain = max(int(h.get("chanceofrain", 0)) for h in hourly) if hourly else 0
            return {
                "date": day.get("date"),
                "maxtempC": day.get("maxtempC"),
                "mintempC": day.get("mintempC"),
                "chanceOfRain": rain,
            }

        summary_text = current.get("weatherDesc", [{"value": ""}])[0].get("value", "")
        today_info = extract_day(today)
        tomorrow_info = extract_day(tomorrow) if tomorrow else {}

        text = f"{summary_text} / 最高{today_info.get('maxtempC')}℃ 最低{today_info.get('mintempC')}℃ 降水確率{today_info.get('chanceOfRain')}%"

        return {
            "summary": text,
            "current": {
                "tempC": current.get("temp_C"),
                "feelsLikeC": current.get("FeelsLikeC"),
                "description": summary_text,
            },
            "today": today_info,
            "tomorrow": tomorrow_info,
            "source": "wttr.in",
        }
