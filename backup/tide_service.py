# tide_service.py
import requests
import pandas as pd
import streamlit as st

class TideService:
    """
    Cliente da API WorldTides (https://www.worldtides.info).
    Usa o endpoint v3 com a opção `heights` para série contínua de altura da maré.
    Retorna DataFrame com colunas:
      - time (datetime naive no timezone informado)
      - tide_m (float, metros)
    """

    BASE_URL = "https://www.worldtides.info/api/v3"

    def __init__(self, api_key: str, timezone: str = "Europe/Lisbon"):
        self.api_key = api_key
        self.timezone = timezone

    @st.cache_data(ttl=21600)  # 6 horas
    def get_tide(_self, spot_name: str, lat: float, lon: float, days: int = 3):
        """
        :param spot_name: apenas informativo (não usado na API)
        :param lat, lon: coordenadas do spot
        :param days: 1–7 no free tier
        :return: (df, url_chamada)
        """
        params = {
            "heights": "",          # série contínua (height vs tempo)
            "datums": "MSL",        # nível médio do mar
            "lat": lat,
            "lon": lon,
            "days": days,
            "key": _self.api_key,
        }
        r = requests.get(_self.BASE_URL, params=params, timeout=30)
        url_called = r.url
        r.raise_for_status()
        j = r.json()

        if "heights" not in j or not j["heights"]:
            return pd.DataFrame(columns=["time", "tide_m"]), url_called

        df = pd.DataFrame(j["heights"])
        # dt (epoch s, UTC) -> timezone local -> volta a naive (sem tz) p/ casar com o resto do app
        df["time"] = (
            pd.to_datetime(df["dt"], unit="s")
              .dt.tz_localize("UTC")
              .dt.tz_convert(_self.timezone)
              .dt.tz_localize(None)
        )
        df = df.rename(columns={"height": "tide_m"}).drop(columns=["dt"])[["time", "tide_m"]]
        df = df.sort_values("time").reset_index(drop=True)
        return df, url_called