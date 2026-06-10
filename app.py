
import io
import re
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Porra Mundial 2026", page_icon="⚽", layout="wide")

SOURCE_URL = "https://docs.google.com/spreadsheets/d/1q4SpZQb7_7UrX-NtReo2XS7jBMvHH0xI/edit?usp=drivesdk&ouid=105950533705571221592&rtpof=true&sd=true"
CACHE_MINUTES = 5
LOGO_PATH = "UG 448X448.png"

# Colores corporativos
C_PRIMARY_DARK = "#004A5F"
C_PRIMARY = "#327D8E"
C_PRIMARY_LIGHT = "#64AEBC"
C_SECONDARY_DARK = "#CC6100"
C_SECONDARY = "#F28E00"
C_SECONDARY_LIGHT = "#F1C831"
C_GRAY_DARK = "#383737"
C_GRAY = "#706F6F"
C_GRAY_LIGHT = "#D9D9D9"


def make_download_url(url: str) -> str:
    url = url.strip().replace("&amp;", "&")
    m = re.search(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if m:
        sheet_id = m.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
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
    ranking = ranking.sort_values(["POS", "PUNTOS_TOTALES", "PARTICIPANTE"], ascending=[True, False, True]).reset_index(drop=True)

    ranking = ranking.merge(ranking_prev[["PARTICIPANTE", "POS_ANTERIOR", "PUNTOS_ANTERIORES"]], on="PARTICIPANTE", how="left")
    ranking["CAMBIO_POSICION"] = ranking["POS_ANTERIOR"] - ranking["POS"]
    ranking["CAMBIO_PUNTOS"] = ranking["PUNTOS_TOTALES"] - ranking["PUNTOS_ANTERIORES"]

    def movimiento(v):
        if pd.isna(v):
            return "🆕"
        if v > 0:
            return f"▲ +{int(v)}"
        if v < 0:
            return f"▼ {int(v)}"
        return "• 0"

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
    return ranking, team_points


st.markdown(f"""
<style>
.stApp {{
  background: linear-gradient(180deg, #ffffff 0%, #f4f8f9 40%, #eef5f6 100%);
}}
.block-container {{
  max-width: 1180px;
  padding-top: 1.15rem;
  padding-bottom: 2rem;
}}
#MainMenu, footer, header {{visibility: hidden;}}

.title-wrap {{
  background: linear-gradient(135deg, {C_PRIMARY_DARK} 0%, {C_PRIMARY} 58%, {C_PRIMARY_LIGHT} 100%);
  border-radius: 24px;
  padding: 1.2rem 1.35rem;
  margin-bottom: 1rem;
  box-shadow: 0 18px 40px rgba(0, 74, 95, .24);
}}
.title-main {{
  color: #ffffff;
  font-size: 2.35rem;
  font-weight: 900;
  line-height: 1.05;
  margin: 0;
}}
.title-sub {{
  color: rgba(255,255,255,.98);
  margin-top: .35rem;
  font-size: 1rem;
  font-weight: 600;
}}
.section-title {{
  color: {C_PRIMARY_DARK};
  font-weight: 900;
  font-size: 1.25rem;
}}

.kpi-card {{
  background: white;
  border: 1px solid rgba(50, 125, 142, .18);
  border-radius: 18px;
  padding: .95rem 1rem .8rem;
  box-shadow: 0 8px 22px rgba(50,125,142,.08);
  min-height: 106px;
}}
.kpi-label {{
  color: {C_GRAY_DARK};
  font-size: .96rem;
  font-weight: 700;
  margin-bottom: .25rem;
}}
.kpi-value {{
  color: {C_PRIMARY_DARK};
  font-size: 1.8rem;
  font-weight: 900;
  line-height: 1.05;
}}

.podium-card {{
  border-radius: 18px;
  padding: 1rem 1rem .9rem;
  min-height: 140px;
  color: white;
  box-shadow: 0 10px 22px rgba(0,0,0,.10);
}}
.podium-gold {{ background: linear-gradient(135deg, {C_SECONDARY_DARK} 0%, {C_SECONDARY} 55%, {C_SECONDARY_LIGHT} 100%); color: #ffffff; }}
.podium-silver {{ background: linear-gradient(135deg, {C_GRAY} 0%, #9C9B9B 60%, {C_GRAY_LIGHT} 100%); color: {C_GRAY_DARK}; }}
.podium-bronze {{ background: linear-gradient(135deg, #a85810 0%, {C_SECONDARY_DARK} 60%, {C_SECONDARY} 100%); color: #ffffff; }}
.podium-rank {{ font-size: 1.85rem; margin-bottom: .35rem; }}
.podium-name {{ font-weight: 900; font-size: 1.08rem; }}
.podium-points {{ margin-top: .35rem; font-size: 1rem; font-weight: 800; }}

.stTabs [data-baseweb="tab-list"] {{
  gap: .45rem;
  border-bottom: 2px solid rgba(0,74,95,.12);
}}
.stTabs [data-baseweb="tab"] {{
  color: {C_PRIMARY_DARK} !important;
  font-weight: 900 !important;
  font-size: 1rem !important;
  background: rgba(255,255,255,.76) !important;
  border-radius: 12px 12px 0 0 !important;
  padding: .45rem .95rem !important;
}}
.stTabs [data-baseweb="tab"]:hover {{
  color: {C_PRIMARY_DARK} !important;
  background: rgba(100,174,188,.12) !important;
}}
.stTabs [aria-selected="true"] {{
  color: {C_PRIMARY_DARK} !important;
  background: rgba(100,174,188,.18) !important;
  border-bottom: 3px solid {C_PRIMARY_DARK} !important;
}}

.rank-row {{
  display: grid;
  grid-template-columns: 78px 1.8fr 130px;
  gap: .75rem;
  align-items: center;
  background: #ffffff;
  border: 1px solid rgba(80,80,80,.10);
  border-left: 6px solid {C_PRIMARY_LIGHT};
  border-radius: 16px;
  padding: .8rem .95rem;
  margin-bottom: .5rem;
  box-shadow: 0 6px 18px rgba(0,0,0,.04);
}}
.rank-row.top1 {{ border-left-color: {C_SECONDARY_LIGHT}; background: linear-gradient(90deg, rgba(241,200,49,.16), white 26%); }}
.rank-row.top2 {{ border-left-color: {C_GRAY}; background: linear-gradient(90deg, rgba(217,217,217,.28), white 26%); }}
.rank-row.top3 {{ border-left-color: {C_SECONDARY}; background: linear-gradient(90deg, rgba(242,142,0,.13), white 26%); }}

.pos-badge {{
  width: 54px;
  height: 54px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  background: {C_PRIMARY_DARK};
  font-weight: 900;
  font-size: 1.2rem;
  box-shadow: inset 0 0 0 4px rgba(255,255,255,.15);
}}
.pos-badge.gold {{ background: linear-gradient(135deg, {C_SECONDARY_DARK}, {C_SECONDARY_LIGHT}); color: #ffffff; }}
.pos-badge.silver {{ background: linear-gradient(135deg, {C_GRAY}, {C_GRAY_LIGHT}); color: {C_GRAY_DARK}; }}
.pos-badge.bronze {{ background: linear-gradient(135deg, {C_SECONDARY_DARK}, {C_SECONDARY}); color: #ffffff; }}

.rank-name {{ font-weight: 900; color: {C_GRAY_DARK}; font-size: 1.03rem; }}
.rank-sub {{ color: {C_GRAY_DARK}; font-size: .84rem; opacity: .88; margin-top: .1rem; }}
.rank-points {{ font-weight: 900; color: {C_PRIMARY_DARK}; font-size: 1.4rem; text-align: center; }}
.rank-label {{ color: {C_PRIMARY_DARK}; font-size: .82rem; text-align: center; font-weight: 800; }}
.tag {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: .35rem .65rem;
  font-size: .82rem;
  font-weight: 800;
  width: fit-content;
}}
.tag-up {{ background: rgba(100,174,188,.2); color: {C_PRIMARY_DARK}; }}
.tag-down {{ background: rgba(242,142,0,.16); color: {C_SECONDARY_DARK}; }}
.tag-flat {{ background: rgba(112,111,111,.14); color: {C_GRAY_DARK}; }}
.tag-new {{ background: rgba(241,200,49,.22); color: {C_SECONDARY_DARK}; }}
.delta-box {{ text-align: center; font-weight: 900; color: {C_GRAY_DARK}; }}
.tab-hint, p, li, label {{ color: {C_GRAY_DARK} !important; }}

@media (max-width: 900px) {{
  .title-main {{ font-size: 1.85rem; }}
  .rank-row {{ grid-template-columns: 64px 1fr; gap: .55rem; }}
  .rank-points, .rank-label, .delta-box, .tag {{ text-align: left; }}
}}
</style>
""", unsafe_allow_html=True)

try:
    ranking, team_points = load_data()
except Exception as e:
    st.error(f"No se pudo cargar la clasificación: {e}")
    st.stop()

leader = ranking.sort_values(["POS", "PARTICIPANTE"]).iloc[0]
last_loaded = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

col_logo, col_title = st.columns([1, 8])
with col_logo:
    if Path(LOGO_PATH).exists():
        st.image(LOGO_PATH, width=96)
with col_title:
    st.markdown(f"""
    <div class='title-wrap'>
      <div class='title-main'>Clasificación Oficial · Porra Mundial 2026</div>
      <div class='title-sub'>Actualización automática · Última carga de datos: <b>{last_loaded}</b></div>
    </div>
    """, unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Participantes</div><div class='kpi-value'>{int(ranking['PARTICIPANTE'].nunique())}</div></div>", unsafe_allow_html=True)
with k2:
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Líder actual</div><div class='kpi-value'>{leader['PARTICIPANTE']}</div></div>", unsafe_allow_html=True)
with k3:
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Puntos del líder</div><div class='kpi-value'>{int(leader['PUNTOS_TOTALES'])}</div></div>", unsafe_allow_html=True)
with k4:
    third_points = int(ranking.nsmallest(min(3, len(ranking)), 'POS').iloc[min(2, len(ranking)-1)]['PUNTOS_TOTALES']) if len(ranking) > 0 else 0
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Puntos del 3º</div><div class='kpi-value'>{third_points}</div></div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>🏅 Podium</div>", unsafe_allow_html=True)
podium = ranking.nsmallest(3, 'POS')[['PARTICIPANTE', 'PUNTOS_TOTALES']].reset_index(drop=True)
medal_classes = ['podium-gold', 'podium-silver', 'podium-bronze']
medals = ['🥇', '🥈', '🥉']
p1, p2, p3 = st.columns(3)
for i, col in enumerate([p1, p2, p3]):
    if i < len(podium):
        row = podium.iloc[i]
        col.markdown(f"""
        <div class='podium-card {medal_classes[i]}'>
            <div class='podium-rank'>{medals[i]}</div>
            <div class='podium-name'>{row['PARTICIPANTE']}</div>
            <div class='podium-points'>{int(row['PUNTOS_TOTALES'])} puntos</div>
        </div>
        """, unsafe_allow_html=True)

rank_tab, teams_tab = st.tabs(['🏆 Ranking', '🌍 Equipos'])

with rank_tab:
    st.markdown("<div class='section-title'>Clasificación general</div>", unsafe_allow_html=True)
    st.markdown("<div class='tab-hint'>Vista pública de la clasificación con estilo deportivo y lectura rápida.</div>", unsafe_allow_html=True)

    for _, row in ranking.iterrows():
        pos = int(row['POS']) if pd.notna(row['POS']) else '-'
        points = int(row['PUNTOS_TOTALES']) if pd.notna(row['PUNTOS_TOTALES']) else 0
        st.markdown(f"""
        <div class='rank-row {row_class}'>
            <div class='pos-badge {badge_class}'>{pos}</div>
            <div>
                <div class='rank-name'>{row['PARTICIPANTE']}</div>
                <div class='rank-sub'>Posición actual{medal}</div>
            </div>
            <div>
                <div class='rank-label'>Puntos</div>
                <div class='rank-points'>{points}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with teams_tab:
    st.markdown("<div class='section-title'>Puntos por equipo</div>", unsafe_allow_html=True)
    st.markdown("<div class='tab-hint'>Selecciones que más están aportando puntos a la porra.</div>", unsafe_allow_html=True)
    st.dataframe(team_points, use_container_width=True, hide_index=True)
