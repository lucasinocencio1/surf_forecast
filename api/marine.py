"""
marine weather api client
"""

import requests
from pydantic import ValidationError
from models import MarineResponse


def get_marine_forecast(latitude: float, longitude: float) -> MarineResponse:
    """
    fetch marine forecast data from open-meteo api with validation
    
    args:
        latitude: latitude coordinate
        longitude: longitude coordinate
    
    returns:
        validated marine response
    
    raises:
        requests.HTTPError: if api request fails
        ValidationError: if api response doesn't match expected schema
    """
    # open-meteo marine api endpoint
    url = "https://marine-api.open-meteo.com/v1/marine"
    
    # parameters for the api request
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": [
            "wave_height",
            "wave_direction",
            "wave_period",
            "wind_wave_height",
            "wind_wave_direction",
            "wind_wave_period",
            "swell_wave_height",
            "swell_wave_direction",
            "swell_wave_period"
        ],
        "daily": [
            "wave_height_max",
            "wave_direction_dominant",
            "wave_period_max",
            "wind_wave_height_max",
            "wind_wave_direction_dominant",
            "wind_wave_period_max",
            "swell_wave_height_max",
            "swell_wave_direction_dominant",
            "swell_wave_period_max"
        ],
        "timezone": "auto",
        "forecast_days": 7
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    # validate response
    try:
        return MarineResponse(**response.json())
    except ValidationError as e:
        raise ValueError(f"invalid marine api response: {e}")
