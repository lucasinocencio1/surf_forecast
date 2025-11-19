# config.py
SPOTS = [
    {"nome": "Costa da Caparica",   "lat": 38.643, "lon": -9.236, "orientacao": 240},
    {"nome": "Carcavelos",          "lat": 38.676, "lon": -9.335, "orientacao": 250},
    {"nome": "Peniche (Supertubos)","lat": 39.343, "lon": -9.361, "orientacao": 210},
]
TIMEZONE = "Europe/Lisbon"

# URLs oficiais IH Portugal para previsão de maré
TIDE_URLS = {
    "Costa da Caparica": "https://www.hidrografico.pt/previsao-mares?spot=1182",
    "Carcavelos": "https://www.hidrografico.pt/previsao-mares?spot=1176",
    "Peniche (Supertubos)": "https://www.hidrografico.pt/previsao-mares?spot=1193"
}

# Defaults de pesos/limiares (usados nos sliders como ponto de partida)
DEFAULT_LIMITS = dict(
    ALTURA_BOA_MIN=0.8, ALTURA_BOA_MAX=2.2,
    PERIODO_MIN_BOM=8.0, VENTO_MAX_OK=12.0, OFFSHORE_TOL=45.0
)
DEFAULT_PESOS = dict(altura=0.35, periodo=0.35, vento=0.10, direcao=0.20)

# WorldTides API
WORLDTIDES_API_KEY = "b2d79182-e551-4cbe-a56c-3f6849829d35"
WORLDTIDES_DAYS = 3  # dias de previsão de maré (1–7 no free tier) (BACKUP OLD CODE)
