
import io
import re
import urllib.request
import unicodedata
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


def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text).strip().lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'[^a-z0-9]+', '', text)
    return text


def make_download_url(url: str) -> str:
    url = url.strip().replace("&amp;", "&")
    m = re.search(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if m:
        sid = m.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=xlsx"
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        fid = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={fid}"
    if "drive.google.com/uc?" in url and "id=" in url:
        return url
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        fid = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={fid}"
    return url


@st.cache_data(ttl=CACHE_MINUTES * 60)
def download_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


def read_excel_all(file_bytes: bytes):
    xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    sheets = {}
    for name in xls.sheet_names:
        header = None if name == 'Puntos' else 0
        sheets[name] = pd.read_excel(io.BytesIO(file_bytes), sheet_name=name, header=header, engine='openpyxl')
    return sheets


def _find_table_start(row_values, labels, occurrence="first"):
    norm = [str(x).strip().upper() if pd.notna(x) else "" for x in row_values]
    labels_norm = [x.strip().upper() for x in labels]
    matches = []
    for i in range(len(norm) - len(labels_norm) + 1):
        if norm[i:i + len(labels_norm)] == labels_norm:
            matches.append(i)
    if not matches:
        return None
    return matches[-1] if occurrence == "last" else matches[0]


def parse_puntos(raw: pd.DataFrame):
    header_row = raw.iloc[1].tolist()
    curr_start = _find_table_start(header_row, ["POS", "PARTICIPANTE", "PUNTOS TOTALES"], occurrence="last")
    team_start = _find_table_start(
        header_row,
        ["Equipo", "Fase Grupos", "1/16 (5pts)", "1/8 (5pts)", "1/4 (5pts)", "Semis (10pts)", "Final (25pts)", "Campeón (35pts)", "TOTAL"],
        occurrence="first",
    )
    if curr_start is None:
        raise ValueError("No encuentro las columnas del ranking en la hoja 'Puntos'.")
    if team_start is None:
        raise ValueError("No encuentro la tabla de puntos por equipo en la hoja 'Puntos'.")

    ranking = raw.iloc[2:, curr_start:curr_start + 3].copy()
    ranking.columns = ["POS", "PARTICIPANTE", "PUNTOS_TOTALES"]
    ranking = ranking.dropna(subset=["PARTICIPANTE"]).copy()
    ranking["PARTICIPANTE"] = ranking["PARTICIPANTE"].astype(str).str.strip()
    ranking["SIGLA"] = ranking["PARTICIPANTE"].apply(normalize_text)
    ranking["POS"] = pd.to_numeric(ranking["POS"], errors="coerce")
    ranking["PUNTOS_TOTALES"] = pd.to_numeric(ranking["PUNTOS_TOTALES"], errors="coerce")
    ranking = ranking.sort_values(["POS", "PUNTOS_TOTALES", "PARTICIPANTE"], ascending=[True, False, True]).reset_index(drop=True)

    team_points = raw.iloc[2:, team_start:team_start + 9].copy()
    team_points.columns = ["Equipo", "Fase_Grupos", "Dieciseisavos", "Octavos", "Cuartos", "Semis", "Final", "Campeon", "TOTAL"]
    team_points = team_points.dropna(subset=["Equipo"]).copy()
    team_points["Equipo"] = team_points["Equipo"].astype(str).str.strip()
    for col in [c for c in team_points.columns if c != "Equipo"]:
        team_points[col] = pd.to_numeric(team_points[col], errors="coerce").fillna(0)
    team_points = team_points.sort_values(["TOTAL", "Equipo"], ascending=[False, True]).reset_index(drop=True)
    team_points["TEAM_KEY"] = team_points["Equipo"].apply(normalize_text)
    return ranking, team_points


def build_participant_details(resumen_df: pd.DataFrame, team_points: pd.DataFrame):
    pts_by_team = dict(zip(team_points['TEAM_KEY'], team_points['TOTAL']))
    levels = [c for c in resumen_df.columns if str(c).strip().lower().startswith('nivel')]

    by_exact = {}
    normalized_names = []
    for _, row in resumen_df.iterrows():
        participant = str(row['PARTICIPANTE']).strip()
        pkey = normalize_text(participant)
        picks = []
        total = 0
        chosen_keys = []
        for lvl in levels:
            team = row[lvl]
            if pd.isna(team):
                continue
            team = str(team).strip()
            tkey = normalize_text(team)
            points = int(pts_by_team.get(tkey, 0))
            total += points
            chosen_keys.append(tkey)
            picks.append({
                'Nivel': lvl,
                'Equipo': team,
                'Puntos acumulados': points,
                'TEAM_KEY': tkey,
            })
        info = {
            'participante': participant,
            'pkey': pkey,
            'total_selecciones': total,
            'equipos': picks,
            'team_keys': chosen_keys,
        }
        by_exact[pkey] = info
        normalized_names.append((pkey, participant, info))

    def resolve(participant_name: str):
        key = normalize_text(participant_name)
        if key in by_exact:
            return by_exact[key]
        # fallback 1: unique contains match
        candidates = [info for pkey, _, info in normalized_names if key in pkey or pkey in key]
        if len(candidates) == 1:
            return candidates[0]
        # fallback 2: prefix match unique
        candidates = [info for pkey, _, info in normalized_names if pkey.startswith(key) or key.startswith(pkey)]
        if len(candidates) == 1:
            return candidates[0]
        return None

    return resolve


@st.cache_data(ttl=CACHE_MINUTES * 60)
def load_data():
    url = make_download_url(SOURCE_URL)
    file_bytes = download_bytes(url)
    sheets = read_excel_all(file_bytes)
    if 'Puntos' not in sheets or 'Resumen de Apuestas' not in sheets:
        raise ValueError(f"Faltan hojas requeridas. Hojas detectadas: {list(sheets.keys())}")
    ranking, team_points = parse_puntos(sheets['Puntos'])
    resolver = build_participant_details(sheets['Resumen de Apuestas'], team_points)
    return ranking, team_points, resolver


def team_card_html(team: str, level: str, points: int, highlight: bool = False):
    border = C_SECONDARY if highlight else C_PRIMARY_LIGHT
    shadow = '0 10px 22px rgba(0,0,0,.10)' if highlight else '0 6px 18px rgba(0,0,0,.05)'
    accent = C_SECONDARY if points > 0 else C_GRAY
    return f"""
    <div style="background:white;border:1px solid {border};border-left:6px solid {accent};border-radius:16px;padding:.9rem 1rem;box-shadow:{shadow};min-height:120px;">
      <div style="color:{C_PRIMARY_DARK};font-weight:800;font-size:.88rem;">{level}</div>
      <div style="color:{C_GRAY_DARK};font-weight:900;font-size:1.12rem;margin-top:.3rem;line-height:1.2;">{team}</div>
      <div style="color:{accent};font-weight:900;font-size:1.55rem;margin-top:.55rem;">{points}</div>
      <div style="color:{C_GRAY};font-size:.86rem;">puntos acumulados</div>
    </div>
    """


st.markdown(f"""
<style>
.stApp {{ background: linear-gradient(180deg, #ffffff 0%, #f4f8f9 40%, #eef5f6 100%); }}
.block-container {{ max-width: 1180px; padding-top: 1.15rem; padding-bottom: 2rem; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.title-wrap {{ background: linear-gradient(135deg, {C_PRIMARY_DARK} 0%, {C_PRIMARY} 58%, {C_PRIMARY_LIGHT} 100%); border-radius: 24px; padding: 1.2rem 1.35rem; margin-bottom: 1rem; box-shadow: 0 18px 40px rgba(0,74,95,.24); }}
.title-main {{ color:#fff; font-size:2.35rem; font-weight:900; line-height:1.05; margin:0; }}
.title-sub {{ color:rgba(255,255,255,.98); margin-top:.35rem; font-size:1rem; font-weight:600; }}
.section-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.25rem; }}
.kpi-card {{ background:white; border:1px solid rgba(50,125,142,.18); border-radius:18px; padding:.95rem 1rem .8rem; box-shadow:0 8px 22px rgba(50,125,142,.08); min-height:106px; }}
.kpi-label {{ color:{C_GRAY_DARK}; font-size:.96rem; font-weight:700; margin-bottom:.25rem; }}
.kpi-value {{ color:{C_PRIMARY_DARK}; font-size:1.8rem; font-weight:900; line-height:1.05; }}
.podium-card {{ border-radius:18px; padding:1rem 1rem .9rem; min-height:140px; color:white; box-shadow:0 10px 22px rgba(0,0,0,.10); }}
.podium-gold {{ background: linear-gradient(135deg, {C_SECONDARY_DARK} 0%, {C_SECONDARY} 55%, {C_SECONDARY_LIGHT} 100%); }}
.podium-silver {{ background: linear-gradient(135deg, {C_GRAY} 0%, #9C9B9B 60%, {C_GRAY_LIGHT} 100%); color:{C_GRAY_DARK}; }}
.podium-bronze {{ background: linear-gradient(135deg, #a85810 0%, {C_SECONDARY_DARK} 60%, {C_SECONDARY} 100%); }}
.podium-rank {{ font-size:1.85rem; margin-bottom:.35rem; }}
.podium-name {{ font-weight:900; font-size:1.08rem; }}
.podium-points {{ margin-top:.35rem; font-size:1rem; font-weight:800; }}
.stTabs [data-baseweb="tab-list"] {{ gap:.45rem; border-bottom:2px solid rgba(0,74,95,.12); }}
.stTabs [data-baseweb="tab"] {{ color:{C_PRIMARY_DARK} !important; font-weight:900 !important; font-size:1rem !important; background:rgba(255,255,255,.76) !important; border-radius:12px 12px 0 0 !important; padding:.45rem .95rem !important; }}
.stTabs [aria-selected="true"] {{ color:{C_PRIMARY_DARK} !important; background:rgba(100,174,188,.18) !important; border-bottom:3px solid {C_PRIMARY_DARK} !important; }}
.rank-shell {{ background:#fff; border:1px solid rgba(80,80,80,.10); border-left:6px solid {C_PRIMARY_LIGHT}; border-radius:16px; padding:.8rem .95rem; margin-bottom:.5rem; box-shadow:0 6px 18px rgba(0,0,0,.04); }}
.rank-shell.top1 {{ border-left-color:{C_SECONDARY_LIGHT}; background:linear-gradient(90deg, rgba(241,200,49,.16), white 26%); }}
.rank-shell.top2 {{ border-left-color:{C_GRAY}; background:linear-gradient(90deg, rgba(217,217,217,.28), white 26%); }}
.rank-shell.top3 {{ border-left-color:{C_SECONDARY}; background:linear-gradient(90deg, rgba(242,142,0,.13), white 26%); }}
.rank-grid {{ display:grid; grid-template-columns:70px 1.7fr 125px 140px; gap:.8rem; align-items:center; }}
.pos-badge {{ width:54px; height:54px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; background:{C_PRIMARY_DARK}; font-weight:900; font-size:1.2rem; box-shadow: inset 0 0 0 4px rgba(255,255,255,.15); }}
.pos-badge.gold {{ background: linear-gradient(135deg, {C_SECONDARY_DARK}, {C_SECONDARY_LIGHT}); }}
.pos-badge.silver {{ background: linear-gradient(135deg, {C_GRAY}, {C_GRAY_LIGHT}); color:{C_GRAY_DARK}; }}
.pos-badge.bronze {{ background: linear-gradient(135deg, {C_SECONDARY_DARK}, {C_SECONDARY}); }}
.rank-name {{ font-weight:900; color:{C_GRAY_DARK}; font-size:1.03rem; }}
.rank-sub {{ color:{C_GRAY_DARK}; font-size:.84rem; opacity:.88; margin-top:.1rem; }}
.rank-points {{ font-weight:900; color:{C_PRIMARY_DARK}; font-size:1.4rem; text-align:center; }}
.rank-label {{ color:{C_PRIMARY_DARK}; font-size:.82rem; text-align:center; font-weight:800; }}
.rank-btn button {{ width:100%; border-radius:12px !important; font-weight:800 !important; border:1px solid rgba(50,125,142,.2) !important; }}
.rank-btn button[kind="primary"] {{ background:{C_PRIMARY_DARK} !important; color:white !important; }}
.tab-hint, p, li, label {{ color:{C_GRAY_DARK} !important; }}
.detail-wrap {{ background:rgba(255,255,255,.86); border:1px solid rgba(50,125,142,.16); border-radius:18px; padding:1rem 1rem .9rem; margin:.35rem 0 1rem; }}
.detail-header {{ display:flex; justify-content:space-between; align-items:flex-end; gap:1rem; flex-wrap:wrap; }}
.detail-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.08rem; }}
.detail-total {{ color:{C_SECONDARY_DARK}; font-weight:900; font-size:1rem; }}
.highlight-note {{ background:rgba(241,200,49,.18); border-left:6px solid {C_SECONDARY}; border-radius:14px; padding:.75rem .9rem; color:{C_GRAY_DARK}; font-weight:700; margin:.25rem 0 1rem; }}
[data-testid="stDataFrame"] div[role="table"] {{ color:{C_GRAY_DARK} !important; }}
@media (max-width: 900px) {{
  .title-main {{ font-size:1.85rem; }}
  .rank-grid {{ grid-template-columns:64px 1fr; }}
}}
</style>
""", unsafe_allow_html=True)

try:
    ranking, team_points, resolve_participant = load_data()
except Exception as e:
    st.error(f"No se pudo cargar la clasificación: {e}")
    st.stop()

if 'selected_participant_key' not in st.session_state:
    st.session_state.selected_participant_key = None
if 'selected_participant_name' not in st.session_state:
    st.session_state.selected_participant_name = None

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
    st.markdown("<div class='tab-hint'>Pulsa el botón del participante para ver sus selecciones como tarjetas. La selección también se resalta en la pestaña Equipos.</div>", unsafe_allow_html=True)

    for _, row in ranking.iterrows():
        pos = int(row['POS']) if pd.notna(row['POS']) else '-'
        points = int(row['PUNTOS_TOTALES']) if pd.notna(row['PUNTOS_TOTALES']) else 0
        participant = str(row['PARTICIPANTE']).strip()

        badge_class = ''
        row_class = ''
        medal = ''
        if pos == 1:
            badge_class = 'gold'; row_class = 'top1'; medal = ' · Campeón provisional'
        elif pos == 2:
            badge_class = 'silver'; row_class = 'top2'; medal = ' · 2º puesto'
        elif pos == 3:
            badge_class = 'bronze'; row_class = 'top3'; medal = ' · 3º puesto'

        st.markdown(f"<div class='rank-shell {row_class}'>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([0.7, 3.3, 1.2, 1.35])
        with c1:
            st.markdown(f"<div class='pos-badge {badge_class}'>{pos}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='rank-name'>{participant}</div><div class='rank-sub'>Posición actual{medal}</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='rank-label'>Puntos</div><div class='rank-points'>{points}</div>", unsafe_allow_html=True)
        with c4:
            st.markdown("<div class='rank-btn'>", unsafe_allow_html=True)
            if st.button("Ver selecciones", key=f"pick_{normalize_text(participant)}"):
                st.session_state.selected_participant_name = participant
                st.session_state.selected_participant_key = normalize_text(participant)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    selected_name = st.session_state.get('selected_participant_name')
    if selected_name:
        detail = resolve_participant(selected_name)
        if detail is None:
            st.warning(f"No he podido relacionar automáticamente a '{selected_name}' con la hoja 'Resumen de Apuestas'.")
        else:
            st.markdown(f"""
            <div class='detail-wrap'>
              <div class='detail-header'>
                <div class='detail-title'>Selecciones de {detail['participante']}</div>
                <div class='detail-total'>Puntos acumulados de sus equipos: {int(detail['total_selecciones'])}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            picks = detail['equipos']
            cols_per_row = 4
            for i in range(0, len(picks), cols_per_row):
                cols = st.columns(cols_per_row)
                for col, pick in zip(cols, picks[i:i+cols_per_row]):
                    with col:
                        st.markdown(team_card_html(pick['Equipo'], pick['Nivel'], int(pick['Puntos acumulados']), highlight=int(pick['Puntos acumulados']) > 0), unsafe_allow_html=True)

with teams_tab:
    st.markdown("<div class='section-title'>Puntos por equipo</div>", unsafe_allow_html=True)
    selected_name = st.session_state.get('selected_participant_name')
    detail = resolve_participant(selected_name) if selected_name else None

    if detail is not None:
        st.markdown(f"<div class='highlight-note'>Equipos resaltados para <b>{detail['participante']}</b>. Los equipos elegidos por este participante aparecen destacados dentro de la tabla.</div>", unsafe_allow_html=True)
        selected_team_keys = set(detail['team_keys'])

        show_df = team_points.drop(columns=['TEAM_KEY']).copy()
        style_df = show_df.style
        def highlight_rows(row):
            team_key = normalize_text(row['Equipo'])
            if team_key in selected_team_keys:
                return ['background-color: rgba(241,200,49,.22); border-left: 4px solid ' + C_SECONDARY + '; font-weight: 800'] * len(row)
            return [''] * len(row)
        style_df = style_df.apply(highlight_rows, axis=1)
        st.dataframe(style_df, use_container_width=True, hide_index=True)

        st.markdown("<div class='tab-hint'>Equipos seleccionados por el participante:</div>", unsafe_allow_html=True)
        cols_per_row = 4
        cards = detail['equipos']
        for i in range(0, len(cards), cols_per_row):
            cols = st.columns(cols_per_row)
            for col, card in zip(cols, cards[i:i+cols_per_row]):
                with col:
                    st.markdown(team_card_html(card['Equipo'], card['Nivel'], int(card['Puntos acumulados']), highlight=True), unsafe_allow_html=True)
    else:
        st.markdown("<div class='tab-hint'>Selecciones que más están aportando puntos a la porra. Selecciona un participante en Ranking para resaltar sus equipos aquí.</div>", unsafe_allow_html=True)
        st.dataframe(team_points.drop(columns=['TEAM_KEY']), use_container_width=True, hide_index=True)
