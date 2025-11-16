# app.py
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api.geocoding import geocode_location
from api.marine import get_marine_forecast
from api.weather import weather_forecast
from services.forecast import ForecastService
try:
    from config import (
        SPOTS, TIMEZONE,
        DEFAULT_LIMITS, DEFAULT_PESOS,
        WORLDTIDES_API_KEY, WORLDTIDES_DAYS
    )
except Exception:
    # Fallbacks mínimos para rodar com entrada por cidade
    SPOTS = []
    TIMEZONE = "Europe/Lisbon"
    DEFAULT_LIMITS = {"ALTURA_BOA_MIN": 0.6, "ALTURA_BOA_MAX": 2.2, "PERIODO_MIN_BOM": 8.0, "VENTO_MAX_OK": 12.0, "OFFSHORE_TOL": 30.0}
    DEFAULT_PESOS = {"altura": 0.35, "periodo": 0.25, "vento": 0.25, "direcao": 0.15}
    WORLDTIDES_API_KEY = ""
    WORLDTIDES_DAYS = 2
try:
    from scoring import ScoreCalculator
except Exception:
    ScoreCalculator = None

# ===== Tema (Light/Dark) =====
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "light"  # default

def use_theme(mode: str):
    """Aplica CSS e retorna o template do Plotly e cores úteis."""
    mode = (mode or "light").lower()
    is_dark = mode == "dark"

    # CSS global
    if is_dark:
        st.markdown("""
            <style>
              .stApp { background-color:#0f1115 !important; color:#e5e7eb !important; }
              section.main > div { color:#e5e7eb !important; }
              .block-container { padding-top: 1.2rem; }
            </style>
        """, unsafe_allow_html=True)
        plotly_template = "plotly_dark"
        wg_th_bg = "#1f2937"  # cabeçalho da WG table
        text_color = "#e5e7eb"
    else:
        st.markdown("""
            <style>
              .stApp { background-color:#ffffff !important; color:#111827 !important; }
              .block-container { padding-top: 1.2rem; }
            </style>
        """, unsafe_allow_html=True)
        plotly_template = "plotly_white"
        wg_th_bg = "#111"     # igual já usado antes
        text_color = "#111827"

    return plotly_template, wg_th_bg, text_color

# Botão de alternância (na barra superior)
c_theme1, c_theme2 = st.columns([0.82, 0.18])
with c_theme2:
    label = "🌙 Dark" if st.session_state.theme_mode == "light" else "☀️ Light"
    if st.button(label, use_container_width=True):
        st.session_state.theme_mode = "dark" if st.session_state.theme_mode == "light" else "light"

PLOTLY_TEMPLATE, WG_TH_BG, _TEXT = use_theme(st.session_state.theme_mode)

# --------------------------------- SETUP ---------------------------------
st.set_page_config(page_title="Surf Forecast PT", page_icon="🌊", layout="wide")
st.title("🌊 Surf Forecast")
st.caption("Dados: Open-Meteo (Marine + Forecast) + Geocoding (Nominatim)")
fs = None
ts = None
spots_to_show = []

# ---------------------------- SIDEBAR CONTROLS ----------------------------
st.sidebar.header("Localização")
city_query = st.sidebar.text_input("Cidade (ex: Carcavelos, Portugal)", value="", help="Digite e pressione Enter")
if not city_query.strip():
    st.info("Digite uma cidade na barra lateral para ver a previsão.")
    st.stop()
try:
    lat, lon, full_name = geocode_location(city_query.strip())
    st.success(f"Localização: {full_name} ({lat:.4f}, {lon:.4f})")
    marine_data = get_marine_forecast(lat, lon)
    weather_data = weather_forecast(lat, lon)
    forecast = ForecastService.parse_forecast_data(
        marine_data, weather_data, full_name, lat, lon
    )
    st.subheader(full_name)
    st.text(forecast.to_llm_context())
    st.stop()
except Exception as e:
    st.error(f"Erro ao obter previsão: {e}")
    st.stop()
st.sidebar.header("Modelo (vento/temperatura)")
MODEL_LABELS = {"auto":"Auto (Best match)", "icon":"ICON (DWD)", "gfs":"GFS (NOAA)", "ecmwf":"ECMWF"}
model_key = st.sidebar.selectbox(
    "Modelo principal", list(MODEL_LABELS.keys()),
    format_func=lambda k: MODEL_LABELS[k], index=1
)

st.sidebar.header("Limiares padrão")
ALTURA_BOA_MIN = st.sidebar.number_input("Altura mínima boa (m)", 0.0, 5.0, DEFAULT_LIMITS["ALTURA_BOA_MIN"], 0.1)
ALTURA_BOA_MAX = st.sidebar.number_input("Altura máxima boa (m)", 0.1, 8.0, DEFAULT_LIMITS["ALTURA_BOA_MAX"], 0.1)
PERIODO_MIN_BOM = st.sidebar.number_input("Período mínimo bom (s)", 5.0, 20.0, DEFAULT_LIMITS["PERIODO_MIN_BOM"], 0.5)
VENTO_MAX_OK = st.sidebar.number_input("Vento ok até (m/s)", 2.0, 30.0, DEFAULT_LIMITS["VENTO_MAX_OK"], 0.5)
OFFSHORE_TOL = st.sidebar.number_input("Tolerância offshore (°)", 10.0, 90.0, DEFAULT_LIMITS["OFFSHORE_TOL"], 1.0)

st.sidebar.header("Pesos do score")
peso_altura  = st.sidebar.slider("Peso: Altura", 0.0, 1.0, DEFAULT_PESOS["altura"], 0.05)
peso_periodo = st.sidebar.slider("Peso: Período", 0.0, 1.0, DEFAULT_PESOS["periodo"], 0.05)
peso_vento   = st.sidebar.slider("Peso: Vento/Offshore", 0.0, 1.0, DEFAULT_PESOS["vento"], 0.05)
peso_direcao = st.sidebar.slider("Peso: Direção do swell", 0.0, 1.0, DEFAULT_PESOS["direcao"], 0.05)

# janela
day_opt = st.radio("Janela:", ["Hoje e Amanhã", "Somente Hoje", "Próximas 72h"], horizontal=True)
def filter_range(df):
    now = pd.Timestamp.now(tz=TIMEZONE).tz_localize(None)
    if day_opt == "Somente Hoje":
        end = now.normalize() + pd.Timedelta(days=1)
    elif day_opt == "Hoje e Amanhã":
        end = now.normalize() + pd.Timedelta(days=2)
    else:
        end = now + pd.Timedelta(hours=72)
    return df[(df["time"] >= now - pd.Timedelta(hours=1)) & (df["time"] <= end)]

# ----------------------- HELPERS (WG TABLE + MARÉ) ------------------------
def _knots(ms):
    """Converte m/s para nós (suporta Series ou valor único)"""
    if isinstance(ms, (pd.Series, np.ndarray, list)):
        return pd.Series(ms) * 1.94384
    return ms * 1.94384 if pd.notna(ms) else ms

def _arrow(deg: float) -> str:
    dirs = ["↑","↗","→","↘","↓","↙","←","↖"]
    try:
        return dirs[int(((deg % 360) / 45.0) + 0.5) % 8]
    except Exception:
        return "·"

def _cell_color(v, kind):
    BAD  = "#d9d9d9"; OK = "#a7f3a0"; GOOD = "#63e07f"; EPIC = "#36c37e"
    if pd.isna(v): return BAD
    if kind == "wind_kn":
        v=float(v)
        return EPIC if v<=6 else GOOD if v<=12 else OK if v<=18 else BAD
    if kind == "swell_m":
        v=float(v)
        return BAD if v<0.6 else OK if v<0.9 else GOOD if v<2.2 else EPIC
    if kind == "period_s":
        v=float(v)
        return BAD if v<8 else OK if v<10 else GOOD if v<14 else EPIC
    if kind == "temp_c":
        v=float(v)
        return "#93c5fd" if v<16 else GOOD if v<21 else OK if v<26 else "#f59e0b"
    if kind == "score":
        v=float(v)
        return BAD if v<5 else OK if v<7 else GOOD if v<8.5 else EPIC
    return BAD

def build_wg_table_v2(df_scored: pd.DataFrame):
    d = df_scored.copy()
    d["Hora"] = d["time"].dt.strftime("%d/%m %Hh")
    d["Vel (kn)"] = (_knots(d["wind_speed_10m"])).round(0).astype("Int64")
    d["Raj (kn)"] = (_knots(d.get("wind_gusts_10m"))).round(0).astype("Int64") if "wind_gusts_10m" in d else pd.Series([pd.NA]*len(d))
    d["Dir vento"] = [f"{_arrow(x)} {int(round(x))}°" if pd.notna(x) else "–" for x in d["wind_direction_10m"]]
    d["Ond (m)"] = d["swell_wave_height"].round(2)
    d["Per (s)"] = d["swell_wave_period"].round(1)
    d["Dir vaga"] = [f"{_arrow(x)} {int(round(x))}°" if pd.notna(x) else "–" for x in d["swell_wave_direction"]]
    d["Temp (°C)"] = d["temperature_2m"].round(0).astype("Int64")
    # Se tiver temperatura da água no df (depende do fetch)
    if "sea_surface_temperature" in d.columns:
        d["Água (°C)"] = d["sea_surface_temperature"].round(0).astype("Int64")
    else:
        d["Água (°C)"] = pd.Series([pd.NA]*len(d), dtype="Int64")
    d["Score"] = d["score"].round(1)
    d["⭐"] = d["Score"].apply(lambda x: "⭐" if pd.notna(x) and x>=7 else "")

    cols = ["Hora","Vel (kn)","Raj (kn)","Dir vento","Ond (m)","Per (s)","Dir vaga","Temp (°C)","Água (°C)","Score","⭐"]
    d = d[cols]

    def style_by_kind(s, kind):
        return [f"background-color:{_cell_color(v,kind)}; text-align:center;" for v in s]

    styler = (d.style
      .set_table_styles([
        {"selector":"th","props":[("text-align","center"),("background","#111"),("color","white"),("font-weight","600"),("padding","6px")]},
        {"selector":"td","props":[("padding","6px"),("font-size","0.9rem")]}
      ])
      .hide(axis="index")
      .apply(lambda s: ["text-align:center;"]*len(s), subset=cols)
      .apply(style_by_kind, subset=["Vel (kn)"],  kind="wind_kn")
      .apply(style_by_kind, subset=["Ond (m)"],   kind="swell_m")
      .apply(style_by_kind, subset=["Per (s)"],   kind="period_s")
      .apply(style_by_kind, subset=["Temp (°C)"], kind="temp_c")
      .apply(style_by_kind, subset=["Score"],     kind="score")
    )
    return styler

def tide_sparkline(tide_df, df_scored, height=120):
    fig = go.Figure()
    if tide_df is not None and not tide_df.empty:
        fig.add_trace(go.Scatter(
            x=tide_df["time"], y=tide_df["tide_m"], mode="lines",
            line=dict(width=2), fill="tozeroy", name="Maré (m)"
        ))
    good = df_scored[df_scored["score"]>=7]
    if not good.empty:
        # marca estrelas no nível mediano da maré (apenas visual)
        y_star = (tide_df["tide_m"].median() if tide_df is not None and not tide_df.empty else 0)
        fig.add_trace(go.Scatter(
            x=good["time"], y=[y_star]*len(good),
            mode="markers", marker=dict(size=12, symbol="star"),
            name="score ≥ 7"
        ))
    fig.update_layout(height=height, margin=dict(l=10,r=10,t=10,b=10),
                      xaxis=dict(title=""), yaxis=dict(title="Maré (m)"),
                      showlegend=False)
    return fig

def contiguous_windows(df, threshold=7.0):
    """retorna lista de (x0, x1) para blocos consecutivos com score>=threshold"""
    d = df.sort_values("time")
    mask = d["score"] >= threshold
    spans = []
    if mask.any():
        start = None
        prev_t = None
        for t, ok in zip(d["time"], mask):
            if ok and start is None:
                start = t
            if not ok and start is not None:
                spans.append((start, prev_t if prev_t is not None else t))
                start = None
            prev_t = t
        if start is not None:
            spans.append((start, d["time"].iloc[-1]))
    return spans

def plot_combined(df_m, df_f, df_scored, tide_df, spot_name, model_key, shade_threshold=7.0):
    fig = go.Figure()
    # Swell (altura)
    fig.add_trace(go.Scatter(x=df_m["time"], y=df_m["swell_wave_height"], mode="lines+markers",
                             name="Swell (m)", yaxis="y1"))
    # Período
    fig.add_trace(go.Scatter(x=df_m["time"], y=df_m["swell_wave_period"], mode="lines+markers",
                             name="Período (s)", yaxis="y2"))
    # Maré (área)
    if tide_df is not None and not tide_df.empty:
        fig.add_trace(go.Scatter(x=tide_df["time"], y=tide_df["tide_m"], mode="lines",
                                 fill="tozeroy", name="Maré (m)", yaxis="y3"))
    # Vento
    fig.add_trace(go.Scatter(x=df_f["time"], y=df_f["wind_speed_10m"], mode="lines+markers",
                             name=f"Vento 10m (m/s) — {model_key.upper()}", yaxis="y4"))
    # Score
    fig.add_trace(go.Scatter(x=df_scored["time"], y=df_scored["score"], mode="lines+markers",
                             name="Score (0–10)", yaxis="y5", line=dict(dash="dot", width=3)))

    # Sombreamento das janelas boas
    for x0, x1 in contiguous_windows(df_scored, threshold=shade_threshold):
        fig.add_vrect(x0=x0, x1=x1, fillcolor="green", opacity=0.12, line_width=0)

    fig.update_layout(
        title=f"Previsão combinada — {spot_name}",
        xaxis=dict(title="Hora"),
        yaxis=dict(title="Swell (m)", side="left"),
        yaxis2=dict(title="Período (s)", overlaying="y", side="right", position=1.0, showgrid=False),
        yaxis3=dict(title="Maré (m)", overlaying="y", side="left", position=0.04, showgrid=False),
        yaxis4=dict(title="Vento (m/s)", overlaying="y", side="right", position=0.96, showgrid=False),
        yaxis5=dict(title="Score (0–10)", overlaying="y", side="right", position=0.90, range=[0,10], showgrid=False),
        legend=dict(orientation="h"),
        margin=dict(l=40, r=40, t=40, b=30),
    )
    return fig

# ---------------------------------- LOOP ----------------------------------
for spot in spots_to_show:
    st.markdown("---")
    st.subheader(f"🏖️ {spot['nome']}")

    # Calibração por spot
    with st.expander("Calibração deste spot", expanded=False):
        c1, c2, c3 = st.columns(3)
        A_MIN = c1.number_input("Altura mínima boa (m) — spot", 0.0, 5.0, DEFAULT_LIMITS["ALTURA_BOA_MIN"], 0.1, key=f"{spot['nome']}-amin")
        A_MAX = c2.number_input("Altura máxima boa (m) — spot", 0.1, 8.0, DEFAULT_LIMITS["ALTURA_BOA_MAX"], 0.1, key=f"{spot['nome']}-amax")
        P_MIN = c3.number_input("Período mínimo bom (s) — spot", 5.0, 20.0, DEFAULT_LIMITS["PERIODO_MIN_BOM"], 0.5, key=f"{spot['nome']}-pmin")
        c4, c5, c6 = st.columns(3)
        W_OK  = c4.number_input("Vento ok até (m/s) — spot", 2.0, 30.0, VENTO_MAX_OK, 0.5, key=f"{spot['nome']}-wok")
        OFF_T = c5.number_input("Tolerância offshore (°) — spot", 10.0, 90.0, OFFSHORE_TOL, 1.0, key=f"{spot['nome']}-off")
        ORIENT= c6.number_input("Orientação do pico (°)", 0.0, 359.0, float(spot["orientacao"]), 1.0, key=f"{spot['nome']}-orient")

        p1, p2, p3, p4 = st.columns(4)
        w_alt = p1.slider("Peso Altura", 0.0, 1.0, peso_altura, 0.05, key=f"{spot['nome']}-walt")
        w_per = p2.slider("Peso Período", 0.0, 1.0, peso_periodo, 0.05, key=f"{spot['nome']}-wper")
        w_wnd = p3.slider("Peso Vento/Off", 0.0, 1.0, peso_vento, 0.05, key=f"{spot['nome']}-wwnd")
        w_dir = p4.slider("Peso Direção", 0.0, 1.0, peso_direcao, 0.05, key=f"{spot['nome']}-wdir")

    # ---------- Dados: Marine (ondas + água) ----------
    try:
        marine_json, df_marine, marine_url = fs.get_marine(spot["lat"], spot["lon"])
    except Exception as e:
        st.error(f"Erro ao carregar MARINE: {e}")
        continue
    df_m = filter_range(df_marine)

    # ---------- Dados: Forecast (vento/temp) ----------
    try:
        forecast_json, df_fore, forecast_url = fs.get_forecast(spot["lat"], spot["lon"], model=model_key)
    except Exception as e:
        st.error(f"Erro no modelo '{model_key}': {e}")
        continue
    df_f = filter_range(df_fore)

    # ---------- Merge por horário ----------
    df_merged = pd.merge_asof(
        df_m.sort_values("time"),
        df_f.sort_values("time"),
        on="time", direction="nearest", tolerance=pd.Timedelta("30min")
    ).dropna(subset=["swell_wave_height","swell_wave_period","swell_wave_direction"])

    if df_merged.empty:
        st.warning("Sem dados suficientes para este intervalo.")
        continue

    # ---------- Maré (WorldTides) ----------
    tide_df, tide_url = ts.get_tide(
        spot_name=spot["nome"], lat=spot["lat"], lon=spot["lon"], days=WORLDTIDES_DAYS
    )
    tide_df = filter_range(tide_df) if tide_df is not None else tide_df

    # ---------- Score com sliders ----------
    calc = ScoreCalculator(
        orientacao_spot=ORIENT,
        altura_min=A_MIN, altura_max=A_MAX,
        periodo_min=P_MIN, vento_max_ok=W_OK, offshore_tol=OFF_T,
        pesos={"altura": w_alt, "periodo": w_per, "vento": w_wnd, "direcao": w_dir}
    )
    df_scored = calc.apply(df_merged)

    # ---------- Métricas topo ----------
    top_row = df_scored.loc[df_scored["score"].idxmax()]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Melhor hora", top_row["time"].strftime("%d/%m %H:%M"))
    c2.metric("Score", f"{top_row['score']:.1f}/10")
    c3.metric("Swell (m)", f"{top_row['swell_wave_height']:.2f}")
    c4.metric("Período (s)", f"{top_row['swell_wave_period']:.1f}")

    # ------------------ TABS ------------------
    tab_dash, tab_wg = st.tabs(["📈 Dashboard", "🟦 WG+ (tabela + maré)"])

    with tab_dash:
        fig_combined = plot_combined(df_m, df_f, df_scored, tide_df, spot["nome"], model_key)
        st.plotly_chart(fig_combined, use_container_width=True, key=f"{spot['nome']}-combined")

    with tab_wg:
        df_show = df_scored.copy()
        styler = build_wg_table_v2(df_show)
        st.markdown("<style>.stMarkdown table{border-collapse:collapse;width:100%;}</style>", unsafe_allow_html=True)
        st.markdown(styler.to_html(), unsafe_allow_html=True)
        st.caption("Maré (sparkline) com ⭐ quando score ≥ 7")
        if tide_df is None or tide_df.empty:
            st.info("Sem dados de maré carregados (WorldTides).")
        else:
            st.plotly_chart(tide_sparkline(tide_df, df_scored), use_container_width=True, key=f"{spot['nome']}-tide-spark")

    # ------------------ DEBUG ------------------
    with st.expander("🛠️ Debug (URLs e dados)"):
        st.caption("URL Marine (ondas):"); st.code(marine_url, language="text")
        st.caption(f"URL Forecast (vento/temp) — modelo={model_key}:"); st.code(forecast_url, language="text")
        if tide_url:
            st.caption("URL Maré (WorldTides):"); st.code(tide_url, language="text")

        if tide_df is not None and not tide_df.empty:
            st.write("Maré (amostra):")
            st.dataframe(tide_df.head(), use_container_width=True)

        st.write("Processado (score) — primeiras linhas:")
        cols = [
            "time","swell_wave_height","swell_wave_period","swell_wave_direction",
            "sea_surface_temperature",
            "wind_speed_10m","wind_direction_10m","wind_gusts_10m","temperature_2m",
            "score"
        ]
        # Mostra somente colunas existentes
        cols_exist = [c for c in cols if c in df_scored.columns]
        st.dataframe(df_scored[cols_exist].round(3).head(24), use_container_width=True)
