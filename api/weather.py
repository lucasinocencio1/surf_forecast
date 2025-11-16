"""
weather forecast api client
"""

import requests
from pydantic import ValidationError
from models import WeatherResponse


def weather_forecast(latitude: float, longitude: float) -> WeatherResponse:
    """
    fetch weather forecast data from open-meteo api with validation
    
    args:
        latitude: latitude coordinate
        longitude: longitude coordinate
    
    returns:
        validated weather response
    
    raises:
        requests.HTTPError: if api request fails
        ValidationError: if api response doesn't match expected schema
    """
    # open-meteo weather api endpoint
    url = "https://api.open-meteo.com/v1/forecast"
    
    # parameters for the api request
    params = {
        "latitude": latitude,
        "longitude": longitude,
        # Use correct parameter names per Open-Meteo and send as comma-separated strings
        "hourly": ",".join([
            "temperature_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ]),
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "wind_speed_10m_max",
            "wind_direction_10m_dominant",
            "wind_gusts_10m_max",
        ]),
        "windspeed_unit": "kn",  # knots for surfing
        "timezone": "auto",
        "forecast_days": 7
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    # validate response
    try:
        data = response.json()
        # Map Open-Meteo keys to our Pydantic model expectations
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})
        key_map_hourly = {
            "wind_speed_10m": "windspeed_10m",
            "wind_direction_10m": "winddirection_10m",
            "wind_gusts_10m": "windgusts_10m",
        }
        key_map_daily = {
            "wind_speed_10m_max": "windspeed_10m_max",
            "wind_direction_10m_dominant": "winddirection_10m_dominant",
            "wind_gusts_10m_max": "windgusts_10m_max",
        }
        # Apply mapping without mutating lists accidentally
        for src, dst in key_map_hourly.items():
            if src in hourly and dst not in hourly:
                hourly[dst] = hourly[src]
        for src, dst in key_map_daily.items():
            if src in daily and dst not in daily:
                daily[dst] = daily[src]
        data["hourly"] = hourly
        data["daily"] = daily
        return WeatherResponse(**data)
    except ValidationError as e:
        raise ValueError(f"invalid weather api response: {e}")


if __name__ == "__main__":
    import sys
    latitude = float(sys.argv[1])
    longitude = float(sys.argv[2])
    weather = weather_forecast(latitude, longitude)
    print(weather)
