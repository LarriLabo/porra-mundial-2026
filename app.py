import io
import re
import urllib.request
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Porra Mundial 2026", page_icon="⚽", layout="wide")

# Fuente fija para que los visitantes solo vean la web y no tengan que tocar nada.
SOURCE_URL = "https://docs.google.com/spreadsheets/d/1q4SpZQb7_7UrX-NtReo2XS7jBMvHH0xI/edit?usp=drivesdk&ouid=105950533705571221592&rtpof=true&sd=true"
CACHE_MINUTES = 5


def make_download_url(url: str) -> str:
    url = url.strip().replace("&amp;", "&")

    # Google Sheets -> exportación a Excel
    m = re.search(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if m:
        sheet_id = m.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

    # Google Drive file -> descarga directa
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    if "drive.google.com/uc?" in url and "id=" in url:
        return url

    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    return url


@st.cache_data(ttl=CACHE_MINUTES * 60)
def download_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


@st.cache_data(ttl=CACHE_MINUTES * 60)
def read_workbook(file_bytes: bytes):
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, header=None, engine="openpyxl")


def _find_table_start(row_values, labels, occurrence="first"):
    norm = [str(x).strip().upper() if pd.notna(x) else "" for x in row_values]
    labels_norm = [x.strip().upper() for x in labels]
    matches = []
    for i in range(len(norm) - len(labels_norm) + 1):
        if norm[i:i+len(labels_norm)] == labels_norm:
            matches.append(i)
    if not matches:
        return None
    return matches[-1] if occurrence == "last" else matches[0]


def parse_puntos(raw: pd.DataFrame):
    if raw.shape[0] < 3:
        raise ValueError("La hoja 'Puntos' no tiene suficientes filas.")

    header_row = raw.iloc[1].tolist()

    prev_start = _find_table_start(header_row, ["POS", "PARTICIPANTE", "PUNTOS TOTALES"], occurrence="first")
    curr_start = _find_table_start(header_row, ["POS", "PARTICIPANTE", "PUNTOS TOTALES"], occurrence="last")
    team_start = _find_table_start(
        header_row,
        ["Equipo", "Fase Grupos", "1/16 (5pts)", "1/8 (5pts)", "1/4 (5pts)", "Semis (10pts)", "Final (25pts)", "Campeón (35pts)", "TOTAL"],
        occurrence="first",
    )

    if prev_start is None or curr_start is None:
        raise ValueError("No encuentro las columnas del ranking en la hoja 'Puntos'.")
    if team_start is None:
        raise ValueError("No encuentro la tabla de puntos por equipo en la hoja 'Puntos'.")

    ranking_prev = raw.iloc[2:, prev_start:prev_start+3].copy()
    ranking_prev.columns = ["POS_ANTERIOR", "PARTICIPANTE", "PUNTOS_ANTERIORES"]
    ranking_prev = ranking_prev.dropna(subset=["PARTICIPANTE"]).copy()
    ranking_prev["PARTICIPANTE"] = ranking_prev["PARTICIPANTE"].astype(str).str.strip()
    ranking_prev["POS_ANTERIOR"] = pd.to_numeric(ranking_prev["POS_ANTERIOR"], errors="coerce")
    ranking_prev["PUNTOS_ANTERIORES"] = pd.to_numeric(ranking_prev["PUNTOS_ANTERIORES"], errors="coerce")

    ranking = raw.iloc[2:, curr_start:curr_start+3].copy()
    ranking.columns = ["POS", "PARTICIPANTE", "PUNTOS_TOTALES"]
    ranking = ranking.dropna(subset=["PARTICIPANTE"]).copy()
    ranking["PARTICIPANTE"] = ranking["PARTICIPANTE"].astype(str).str.strip()
    ranking["POS"] = pd.to_numeric(ranking["POS"], errors="coerce")
    ranking["PUNTOS_TOTALES"] = pd.to_numeric(ranking["PUNTOS_TOTALES"], errors="coerce")
    ranking = ranking.sort_values(["POS", "PARTICIPANTE"], ascending=[True, True]).reset_index(drop=True)

    ranking = ranking.merge(
        ranking_prev[["PARTICIPANTE", "POS_ANTERIOR", "PUNTOS_ANTERIORES"]],
        on="PARTICIPANTE",
        how="left",
    )
    ranking["CAMBIO_POSICION"] = ranking["POS_ANTERIOR"] - ranking["POS"]
    ranking["CAMBIO_PUNTOS"] = ranking["PUNTOS_TOTALES"] - ranking["PUNTOS_ANTERIORES"]

    def movimiento(v):
        if pd.isna(v):
            return "🆕"
        if v > 0:
            return f"⬆️ +{int(v)}"
        if v < 0:
            return f"⬇️ {int(v)}"
        return "➡️ 0"

    ranking["MOVIMIENTO"] = ranking["CAMBIO_POSICION"].apply(movimiento)

    team_points = raw.iloc[2:, team_start:team_start+9].copy()
    team_points.columns = ["Equipo", "Fase_Grupos", "Dieciseisavos", "Octavos", "Cuartos", "Semis", "Final", "Campeon", "TOTAL"]
    team_points = team_points.dropna(subset=["Equipo"]).copy()
    team_points["Equipo"] = team_points["Equipo"].astype(str).str.strip()
    for col in [c for c in team_points.columns if c != "Equipo"]:
        team_points[col] = pd.to_numeric(team_points[col], errors="coerce").fillna(0)
    team_points = team_points.sort_values(["TOTAL", "Equipo"], ascending=[False, True]).reset_index(drop=True)

    return ranking, team_points


def load_data():
    download_url = make_download_url(SOURCE_URL)
    file_bytes = download_bytes(download_url)
    sheets = read_workbook(file_bytes)
    if "Puntos" not in sheets:
        raise ValueError(f"El Excel exportado no contiene una hoja llamada 'Puntos'. Hojas detectadas: {list(sheets.keys())}")
    ranking, team_points = parse_puntos(sheets["Puntos"])
    return ranking, team_points, download_url


# ===== Diseño visual =====
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1180px;
    }
    .title-wrap {
        background: linear-gradient(135deg, #0f172a, #111827 60%, #0b1220);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 1.35rem 1.4rem 1.1rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 10px 30px rgba(0,0,0,.18);
    }
    .title-main {
        font-size: 2.3rem;
        font-weight: 800;
        margin: 0;
        line-height: 1.1;
    }
    .title-sub {
        margin-top: .35rem;
        color: #cbd5e1;
        font-size: 1rem;
    }
    .kpi-card {
        border: 1px solid rgba(255,255,255,.08);
        background: rgba(255,255,255,.03);
        border-radius: 16px;
        padding: 1rem 1rem .7rem 1rem;
        min-height: 105px;
    }
    .small-label {
        color: #94a3b8;
        font-size: .9rem;
        margin-bottom: .2rem;
    }
    .big-number {
        font-size: 1.8rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .podium-card {
        border-radius: 18px;
        padding: 1rem 1rem .85rem 1rem;
        border: 1px solid rgba(255,255,255,.08);
        background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
        min-height: 135px;
    }
    .podium-rank {
        font-size: 1.8rem;
        margin-bottom: .4rem;
    }
    .podium-name {
        font-size: 1.1rem;
        font-weight: 700;
    }
    .podium-points {
        color: #93c5fd;
        font-weight: 700;
        margin-top: .35rem;
        font-size: 1rem;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    ranking, team_points, resolved_url = load_data()
except Exception as e:
    st.error(f"No se pudo cargar la clasificación: {e}")
    st.stop()

leader = ranking.sort_values(["POS", "PARTICIPANTE"]).iloc[0]
last_loaded = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

st.markdown(
    f"""
    <div class="title-wrap">
        <div class="title-main">⚽ Porra Mundial 2026</div>
        <div class="title-sub">Clasificación pública de la porra · Solo lectura · Última carga de datos: <b>{last_loaded}</b></div>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f'<div class="kpi-card"><div class="small-label">Participantes</div><div class="big-number">{int(ranking["PARTICIPANTE"].nunique())}</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-card"><div class="small-label">Líder actual</div><div class="big-number">{leader["PARTICIPANTE"]}</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="kpi-card"><div class="small-label">Puntos del líder</div><div class="big-number">{int(leader["PUNTOS_TOTALES"])}</div></div>', unsafe_allow_html=True)
with k4:
    max_delta = int(ranking["CAMBIO_PUNTOS"].fillna(0).max())
    st.markdown(f'<div class="kpi-card"><div class="small-label">Mayor subida</div><div class="big-number">+{max_delta}</div></div>', unsafe_allow_html=True)

st.markdown("### 🏅 Podium")
podium = ranking.nsmallest(3, "POS")[["PARTICIPANTE", "PUNTOS_TOTALES"]].reset_index(drop=True)
p1, p2, p3 = st.columns(3)
medals = ["🥇", "🥈", "🥉"]
for i, col in enumerate([p1, p2, p3]):
    if i < len(podium):
        row = podium.iloc[i]
        col.markdown(
            f"""
            <div class="podium-card">
                <div class="podium-rank">{medals[i]}</div>
                <div class="podium-name">{row['PARTICIPANTE']}</div>
                <div class="podium-points">{int(row['PUNTOS_TOTALES'])} puntos</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

rank_tab, teams_tab, info_tab = st.tabs(["🏆 Ranking", "🌍 Equipos", "ℹ️ Información"])

with rank_tab:
    st.subheader("Clasificación general")
    top_chart = ranking.nsmallest(min(10, len(ranking)), "POS").sort_values(["PUNTOS_TOTALES", "PARTICIPANTE"], ascending=[False, True]).set_index("PARTICIPANTE")
    st.bar_chart(top_chart["PUNTOS_TOTALES"])

    table = ranking[["POS", "PARTICIPANTE", "PUNTOS_TOTALES", "MOVIMIENTO", "CAMBIO_PUNTOS"]].copy()
    table.columns = ["Posición", "Participante", "Puntos", "Movimiento", "Δ puntos"]
    st.dataframe(table, use_container_width=True, hide_index=True)

with teams_tab:
    st.subheader("Puntos por equipo")
    st.bar_chart(team_points.set_index("Equipo")["TOTAL"].head(15))
    st.dataframe(team_points, use_container_width=True, hide_index=True)

with info_tab:
    st.subheader("Información de la web")
    st.success("Esta versión es pública y de solo lectura. Quien entre puede consultar la clasificación, pero no modificar los datos ni la fuente.")
    st.write("- Los datos se leen automáticamente desde una fuente fija compartida.")
    st.write("- La web refresca la lectura cada 5 minutos de caché aproximadamente.")
    st.write("- Si acabas de actualizar la hoja, puedes esperar unos minutos o recargar la página del navegador.")
    with st.expander("Detalles técnicos"):
        st.code(resolved_url)
