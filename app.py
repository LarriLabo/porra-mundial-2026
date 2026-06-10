
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
C_BG = "#F7F9FA"


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
:root {{
  --c-primary-dark: {C_PRIMARY_DARK};
  --c-primary: {C_PRIMARY};
  --c-primary-light: {C_PRIMARY_LIGHT};
  --c-secondary-dark: {C_SECONDARY_DARK};
  --c-secondary: {C_SECONDARY};
  --c-secondary-light: {C_SECONDARY_LIGHT};
  --c-gray-dark: {C_GRAY_DARK};
  --c-gray: {C_GRAY};
  --c-gray-light: {C_GRAY_LIGHT};
  --c-bg: {C_BG};
}}

.stApp {{
  background: linear-gradient(180deg, #ffffff 0%, #f7f9fa 35%, #eef5f6 100%);
}}

.block-container {{
  max-width: 1180px;
  padding-top: 1.2rem;
  padding-bottom: 2rem;
}}

#MainMenu, footer, header {{visibility: hidden;}}

.title-wrap {{
  background: linear-gradient(135deg, var(--c-primary-dark) 0%, var(--c-primary) 58%, var(--c-primary-light) 100%);
  border-radius: 24px;
  padding: 1.25rem 1.35rem;
  margin-bottom: 1rem;
  box-shadow: 0 18px 40px rgba(0, 74, 95, .22);
}}

.title-grid {{
  display: grid;
  grid-template-columns: 92px 1fr;
  gap: 1rem;
  align-items: center;
}}

.logo-box {{
  background: rgba(255,255,255,.92);
  border-radius: 18px;
  padding: .55rem;
  display: flex;
  align-items: center;
  justify-content: center;
}}

.title-main {{
  color: white;
  font-size: 2.35rem;
  font-weight: 800;
  line-height: 1.05;
  margin: 0;
}}

.title-sub {{
  color: rgba(255,255,255,.92);
  margin-top: .35rem;
  font-size: 1rem;
}}

.section-title {{
  color: var(--c-primary-dark);
  font-weight: 800;
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
  color: var(--c-gray);
  font-size: .9rem;
  margin-bottom: .25rem;
}}

.kpi-value {{
  color: var(--c-primary-dark);
  font-size: 1.8rem;
  font-weight: 800;
  line-height: 1.05;
}}

.podium-card {{
  border-radius: 18px;
  padding: 1rem 1rem .9rem;
  min-height: 140px;
  color: white;
  box-shadow: 0 10px 22px rgba(0,0,0,.10);
}}

.podium-gold {{ background: linear-gradient(135deg, #CC6100 0%, #F28E00 55%, #F1C831 100%); }}
.podium-silver {{ background: linear-gradient(135deg, #706F6F 0%, #9C9B9B 60%, #D9D9D9 100%); color: #383737; }}
.podium-bronze {{ background: linear-gradient(135deg, #8C5425 0%, #CC6100 65%, #F28E00 100%); }}
.podium-rank {{ font-size: 1.85rem; margin-bottom: .35rem; }}
.podium-name {{ font-weight: 800; font-size: 1.08rem; }}
.podium-points {{ margin-top: .35rem; font-size: 1rem; font-weight: 700; }}

.rank-row {{
  display: grid;
  grid-template-columns: 78px 1.6fr 130px 120px 110px;
  gap: .75rem;
  align-items: center;
  background: white;
  border: 1px solid rgba(80,80,80,.10);
  border-left: 6px solid var(--c-primary-light);
  border-radius: 16px;
  padding: .8rem .95rem;
  margin-bottom: .5rem;
  box-shadow: 0 6px 18px rgba(0,0,0,.04);
}}

.rank-row.top1 {{ border-left-color: var(--c-secondary-light); background: linear-gradient(90deg, rgba(241,200,49,.16), white 26%); }}
.rank-row.top2 {{ border-left-color: var(--c-gray); background: linear-gradient(90deg, rgba(217,217,217,.26), white 26%); }}
.rank-row.top3 {{ border-left-color: var(--c-secondary); background: linear-gradient(90deg, rgba(242,142,0,.13), white 26%); }}

.pos-badge {{
  width: 54px;
  height: 54px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  background: var(--c-primary-dark);
  font-weight: 900;
  font-size: 1.2rem;
  box-shadow: inset 0 0 0 4px rgba(255,255,255,.15);
}}

.pos-badge.gold {{ background: linear-gradient(135deg, #CC6100, #F1C831); color: #383737; }}
.pos-badge.silver {{ background: linear-gradient(135deg, #706F6F, #D9D9D9); color: #383737; }}
.pos-badge.bronze {{ background: linear-gradient(135deg, #CC6100, #F28E00); }}

.rank-name {{ font-weight: 800; color: var(--c-gray-dark); font-size: 1.02rem; }}
.rank-sub {{ color: var(--c-gray); font-size: .83rem; margin-top: .1rem; }}
.rank-points {{ font-weight: 900; color: var(--c-primary-dark); font-size: 1.4rem; text-align: center; }}
.rank-label {{ color: var(--c-gray); font-size: .8rem; text-align: center; }}

.tag {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: .35rem .65rem;
  font-size: .82rem;
  font-weight: 700;
  width: fit-content;
}}
.tag-up {{ background: rgba(100,174,188,.16); color: var(--c-primary-dark); }}
.tag-down {{ background: rgba(242,142,0,.14); color: var(--c-secondary-dark); }}
.tag-flat {{ background: rgba(112,111,111,.12); color: var(--c-gray-dark); }}
.tag-new {{ background: rgba(241,200,49,.18); color: var(--c-secondary-dark); }}

.delta-box {{ text-align: center; font-weight: 800; color: var(--c-gray-dark); }}

.tab-hint {{ color: var(--c-gray); font-size: .92rem; margin-top: -.15rem; margin-bottom: .75rem; }}

@media (max-width: 900px) {{
  .title-grid {{ grid-template-columns: 72px 1fr; }}
  .title-main {{ font-size: 1.8rem; }}
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
    max_delta = int(ranking['CAMBIO_PUNTOS'].fillna(0).max())
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Mayor subida</div><div class='kpi-value'>+{max_delta}</div></div>", unsafe_allow_html=True)

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
    st.markdown("<div class='tab-hint'>Vista pública de la clasificación con estilo deportivo.</div>", unsafe_allow_html=True)

    top_chart = ranking.nsmallest(min(10, len(ranking)), 'POS').sort_values(['PUNTOS_TOTALES', 'PARTICIPANTE'], ascending=[False, True]).set_index('PARTICIPANTE')
    st.bar_chart(top_chart['PUNTOS_TOTALES'])

    for _, row in ranking.iterrows():
        pos = int(row['POS']) if pd.notna(row['POS']) else '-'
        points = int(row['PUNTOS_TOTALES']) if pd.notna(row['PUNTOS_TOTALES']) else 0
        mov = str(row['MOVIMIENTO'])
        if mov.startswith('▲'):
            tag_class = 'tag-up'
        elif mov.startswith('▼'):
            tag_class = 'tag-down'
        elif mov.startswith('🆕'):
            tag_class = 'tag-new'
        else:
            tag_class = 'tag-flat'

        badge_class = ''
        row_class = ''
        medal = ''
        if pos == 1:
            badge_class = 'gold'
            row_class = 'top1'
            medal = ' · Campeón provisional'
        elif pos == 2:
            badge_class = 'silver'
            row_class = 'top2'
            medal = ' · 2º puesto'
        elif pos == 3:
            badge_class = 'bronze'
            row_class = 'top3'
            medal = ' · 3º puesto'

        delta_points = int(row['CAMBIO_PUNTOS']) if pd.notna(row['CAMBIO_PUNTOS']) else 0
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
            <div style='text-align:center;'>
                <div class='rank-label'>Movimiento</div>
                <div class='tag {tag_class}'>{mov}</div>
            </div>
            <div class='delta-box'>
                <div class='rank-label'>Δ puntos</div>
                <div>{delta_points:+d}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with teams_tab:
    st.markdown("<div class='section-title'>Puntos por equipo</div>", unsafe_allow_html=True)
    st.markdown("<div class='tab-hint'>Selecciones que más están aportando puntos a la porra.</div>", unsafe_allow_html=True)
    st.bar_chart(team_points.set_index('Equipo')['TOTAL'].head(15))
    st.dataframe(team_points, use_container_width=True, hide_index=True)
