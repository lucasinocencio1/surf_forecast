# forecast_service.py
import requests
import pandas as pd
import streamlit as st

FORECAST_ENDPOINTS = {
    "auto": "https://api.open-meteo.com/v1/forecast",   # Best match
    "gfs":  "https://api.open-meteo.com/v1/gfs",
    "icon": "https://api.open-meteo.com/v1/dwd-icon",
    "ecmwf":"https://api.open-meteo.com/v1/ecmwf",
}

class ForecastService:
    """Serviço de dados da Open-Meteo: Marine (ondas + temp. da água) e Forecast (vento/temp do ar)."""

    def __init__(self, timezone: str = "Europe/Lisbon"):
        self.timezone = timezone

    # ------------------------- MARINE -------------------------
    @st.cache_data(ttl=30*60, show_spinner=False)
    def get_marine(_self, lat: float, lon: float):
        """
        Retorna (json, df, url) do Marine API com:
          wave_height, swell_wave_height, swell_wave_period,
          swell_wave_direction, sea_surface_temperature
        """
        url = "https://marine-api.open-meteo.com/v1/marine"
        hourly_vars = [
            "wave_height",
            "swell_wave_height",
            "swell_wave_period",
            "swell_wave_direction",
            "sea_surface_temperature",
        ]
        params = [("latitude", lat), ("longitude", lon), ("timezone", _self.timezone)]
        params += [("hourly", v) for v in hourly_vars]

        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()

        df = pd.DataFrame(j["hourly"])
        df["time"] = pd.to_datetime(df["time"])

        called_url = requests.Request("GET", url, params=params).prepare().url
        return j, df, called_url

    # ------------------------ FORECAST ------------------------
    @st.cache_data(ttl=30*60, show_spinner=False)
    def get_forecast(_self, lat: float, lon: float, model: str = "auto"):
        """
        Retorna (json, df, url) do Forecast com:
          wind_speed_10m, wind_direction_10m, wind_gusts_10m, temperature_2m
        """
        endpoint = FORECAST_ENDPOINTS.get(model.lower(), FORECAST_ENDPOINTS["auto"])
        hourly_vars = ["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "temperature_2m"]
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(hourly_vars),
            "timezone": _self.timezone
        }

        r = requests.get(endpoint, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()

        df = pd.DataFrame(j["hourly"])
        df["time"] = pd.to_datetime(df["time"])

        called_url = requests.Request("GET", endpoint, params=params).prepare().url
        return j, df, called_url