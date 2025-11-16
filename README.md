
# Surf Forecast

A Python-based MVP that uses the Open-Meteo Marine API (free, no API key required) to forecast swell height, swell period, swell direction, and wind conditions. Search for any city name and the system will automatically convert it to latitude and longitude coordinates to retrieve weather data and wave forecasts. Includes a surf forecast MCP server that provides wave and surf conditions for any location worldwide.

## How to start

```bash
# 1) criar e ativar venv (opcional)
python -m venv .venv
source .venv/bin/activate  # mac/linux
# .venv\Scripts\activate  # windows

# 2) instalar deps
pip install -r requirements.txt

#3) to check backend CRUD
uvicorn backend.main:app --reload

# to check the frontend use  (here you can check the informations from the spot)

python -m streamlit run frontend/app.py
