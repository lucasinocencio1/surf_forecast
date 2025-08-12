
# Surf Forecast (Caparica, Carcavelos, Peniche)

MVP em Python que usa **Open-Meteo Marine** (grátis, sem API key) para prever altura/período/direção do swell e vento,
calcula um **surf score (0–10)** e aponta a **melhor hora** para cada spot.

## Como rodar

```bash
# 1) criar e ativar venv (opcional)
python -m venv .venv
source .venv/bin/activate  # mac/linux
# .venv\Scripts\activate  # windows

# 2) instalar deps
pip install -r requirements.txt

# 3) executar
python surf_forecast.py
```

Os CSVs com histórico horário ficam em `data/`.
