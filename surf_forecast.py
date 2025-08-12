import requests
import pandas as pd

# --------- CONFIG ---------
# Orientação aproximada do pico (azimute em graus: 0=N, 90=E, 180=S, 270=W)
SPOTS = [
    {"nome": "Costa da Caparica",   "lat": 38.643, "lon": -9.236, "orientacao": 240},
    {"nome": "Carcavelos",          "lat": 38.676, "lon": -9.335, "orientacao": 250},
    {"nome": "Peniche (Supertubos)","lat": 39.343, "lon": -9.361, "orientacao": 210},
]
TIMEZONE = "Europe/Lisbon"

# Pesos e faixas (ajuste ao seu gosto/realidade local)
ALTURA_BOA_MIN = 0.8    # m
ALTURA_BOA_MAX = 2.2    # m
PERIODO_MIN_BOM = 8.0   # s
PERIODO_MAX_REF  = 15.0 # s (cap do score)
VENTO_MAX_OK     = 12.0 # m/s (acima disso começa a estragar)
OFFSHORE_TOL     = 45.0 # graus de tolerância p/ vento offshore

# ------------------- APIS -------------------

def openmeteo_marine(lat, lon, timezone=TIMEZONE):
    """Ondas/swell da Marine API (sem vento 10m)."""
    url = "https://marine-api.open-meteo.com/v1/marine"
    # Use múltiplos &hourly= para evitar o 400
    hourly_vars = [
        "wave_height",
        "swell_wave_height",
        "swell_wave_period",
        "swell_wave_direction",
        # você pode adicionar mais daqui: wave_direction, wind_wave_height, etc. (ver docs)
    ]
    params = [
        ("latitude", lat),
        ("longitude", lon),
        ("timezone", timezone),
    ] + [("hourly", v) for v in hourly_vars]

    r = requests.get(url, params=params, timeout=30)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("Erro HTTP (marine):", r.status_code)
        print("URL:", r.url)
        print("Resposta:", r.text[:500])
        raise

    j = r.json()["hourly"]
    df = pd.DataFrame(j)
    df["time"] = pd.to_datetime(df["time"])
    return df

def openmeteo_wind(lat, lon, timezone=TIMEZONE):
    """Vento 10m do endpoint geral /v1/forecast."""
    url = "https://api.open-meteo.com/v1/forecast"
    hourly_vars = ["wind_speed_10m", "wind_direction_10m"]
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(hourly_vars),
        "timezone": timezone,
    }
    r = requests.get(url, params=params, timeout=30)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("Erro HTTP (forecast):", r.status_code)
        print("URL:", r.url)
        print("Resposta:", r.text[:500])
        raise

    j = r.json()["hourly"]
    df = pd.DataFrame(j)
    df["time"] = pd.to_datetime(df["time"])
    return df

# ------------------- SCORE -------------------

def ang_diff(a, b):
    # diferença angular mínima (0–180)
    return abs((a - b + 180) % 360 - 180)

def clamp01(x):
    return max(0.0, min(1.0, x))

def surf_score(row, orientacao_spot):
    altura = float(row["swell_wave_height"])
    periodo = float(row["swell_wave_period"])
    dir_swell = float(row["swell_wave_direction"])
    vvento = float(row.get("wind_speed_10m", 0.0))
    dvento = float(row.get("wind_direction_10m", 0.0))

    # 1) Alinhamento do swell com a orientação do pico
    alinhamento = 1 - ang_diff(dir_swell, orientacao_spot) / 180.0

    # 2) Janela de altura boa
    altura_score = clamp01((altura - ALTURA_BOA_MIN) / (ALTURA_BOA_MAX - ALTURA_BOA_MIN)) if ALTURA_BOA_MAX > ALTURA_BOA_MIN else 0.0

    # 3) Período
    periodo_score = clamp01((periodo - PERIODO_MIN_BOM) / (PERIODO_MAX_REF - PERIODO_MIN_BOM)) if PERIODO_MAX_REF > PERIODO_MIN_BOM else 0.0

    # 4) Vento offshore (de terra p/ mar)
    offshore_target = (orientacao_spot + 180) % 360
    offshore = clamp01(1 - ang_diff(offshore_target, dvento) / OFFSHORE_TOL)
    vento_penal = clamp01(1 - vvento / VENTO_MAX_OK)

    score = 0.35*altura_score + 0.35*periodo_score + 0.20*alinhamento + 0.10*(offshore*vento_penal)
    return round(10 * clamp01(score), 1)  # escala 0–10

# ------------------- PIPELINE -------------------

def prever_spot(spot):
    # 1) ondas/swell
    df_m = openmeteo_marine(spot["lat"], spot["lon"])
    # 2) vento 10m
    df_w = openmeteo_wind(spot["lat"], spot["lon"])
    # 3) merge por timestamp
    df = pd.merge(df_m, df_w, on="time", how="inner")
    # 4) score
    df["score"] = df.apply(lambda r: surf_score(r, spot["orientacao"]), axis=1)
    # 5) melhor hora
    top = df.loc[df["score"].idxmax()]
    return {
        "spot": spot["nome"],
        "melhor_hora": top["time"],
        "score": float(top["score"]),
        "onda(m)": float(top["swell_wave_height"]),
        "periodo(s)": float(top["swell_wave_period"]),
        "dir_swell(°)": float(top["swell_wave_direction"]),
        "vento(m/s)": float(top["wind_speed_10m"]),
        "dir_vento(°)": float(top["wind_direction_10m"]),
    }, df

if __name__ == "__main__":
    resumos = []
    historicos = {}
    for s in SPOTS:
        resumo, df = prever_spot(s)
        resumos.append(resumo)
        historicos[s["nome"]] = df

    # ranking por score
    print(pd.DataFrame(resumos).sort_values("score", ascending=False).to_string(index=False))

    # salva histórico horário
    for nome, df in historicos.items():
        fn = f"data/historico_{nome.replace(' ','_').lower()}.csv"
        df.to_csv(fn, index=False)