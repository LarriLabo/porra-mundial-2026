
import io
import re
import urllib.request
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Porra Mundial 2026", page_icon="⚽", layout="wide")

SOURCE_URL = "https://docs.google.com/spreadsheets/d/1q4SpZQb7_7UrX-NtReo2XS7jBMvHH0xI/edit?usp=drivesdk&ouid=105950533705571221592&rtpof=true&sd=true"
CACHE_MINUTES = 5

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
C_BG = "#F4F8F9"


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


@st.cache_data(ttl=CACHE_MINUTES * 60)
def load_raw_data():
    url = make_download_url(SOURCE_URL)
    file_bytes = download_bytes(url)
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
        candidates = [info for pkey, _, info in normalized_names if key in pkey or pkey in key]
        if len(candidates) == 1:
            return candidates[0]
        candidates = [info for pkey, _, info in normalized_names if pkey.startswith(key) or key.startswith(pkey)]
        if len(candidates) == 1:
            return candidates[0]
        return None

    return resolve


def team_card_html(team: str, points: int, highlight: bool = False, subtitle: str = ""):
    border = C_SECONDARY if highlight else C_PRIMARY_LIGHT
    shadow = '0 10px 22px rgba(0,0,0,.10)' if highlight else '0 6px 18px rgba(0,0,0,.05)'
    accent = C_SECONDARY if highlight else C_PRIMARY_DARK
    subtitle_html = f"<div style='color:{C_GRAY};font-size:.82rem;margin-top:.15rem'>{subtitle}</div>" if subtitle else ""
    return f"""
    <div style="background:white;border:1px solid {border};border-left:6px solid {accent};border-radius:16px;padding:.9rem 1rem;box-shadow:{shadow};min-height:120px;">
      <div style="color:{C_GRAY_DARK};font-weight:900;font-size:1.08rem;line-height:1.2;">{team}</div>
      {subtitle_html}
      <div style="color:{accent};font-weight:900;font-size:1.55rem;margin-top:.55rem;">{points}</div>
      <div style="color:{C_GRAY};font-size:.86rem;">puntos acumulados</div>
    </div>
    """


style = f"""
<style>
.stApp {{ background: linear-gradient(180deg, #ffffff 0%, {C_BG} 45%, #eef5f6 100%); }}
.block-container {{ max-width: 1180px; padding-top: 1.1rem; padding-bottom: 2rem; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.title-wrap {{ background: linear-gradient(135deg, {C_PRIMARY_DARK} 0%, {C_PRIMARY} 58%, {C_PRIMARY_LIGHT} 100%); border-radius: 24px; padding: 1.25rem 1.4rem; margin-bottom: 1rem; box-shadow: 0 18px 40px rgba(0,74,95,.24); }}
.title-main {{ color:#fff; font-size:2.35rem; font-weight:900; line-height:1.05; margin:0; }}
.title-sub {{ color:rgba(255,255,255,.98); margin-top:.35rem; font-size:1rem; font-weight:600; }}
.section-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.28rem; margin-bottom:.65rem; }}
.podium-wrap {{ margin-top:.15rem; margin-bottom:.4rem; }}
.podium-slot {{ display:flex; align-items:flex-end; justify-content:center; height:220px; }}
.podium-box {{ width:100%; border-radius:18px 18px 14px 14px; padding:1rem 1rem .9rem; color:white; box-shadow:0 12px 26px rgba(0,0,0,.12); }}
.podium-1 {{ background: linear-gradient(135deg, {C_SECONDARY_DARK} 0%, {C_SECONDARY} 55%, {C_SECONDARY_LIGHT} 100%); min-height:210px; }}
.podium-2 {{ background: linear-gradient(135deg, {C_GRAY} 0%, #9C9B9B 60%, {C_GRAY_LIGHT} 100%); color:{C_GRAY_DARK}; min-height:165px; }}
.podium-3 {{ background: linear-gradient(135deg, #a85810 0%, {C_SECONDARY_DARK} 60%, {C_SECONDARY} 100%); min-height:145px; }}
.podium-step-label {{ font-size:2rem; font-weight:900; margin-bottom:.2rem; }}
.podium-name {{ font-weight:900; font-size:1.08rem; margin-top:.4rem; }}
.podium-points {{ margin-top:.45rem; font-size:1rem; font-weight:800; }}
.stTabs [data-baseweb="tab-list"] {{ gap:.45rem; border-bottom:2px solid rgba(0,74,95,.12); }}
.stTabs [data-baseweb="tab"] {{ color:{C_PRIMARY_DARK} !important; font-weight:900 !important; font-size:1rem !important; background:rgba(255,255,255,.76) !important; border-radius:12px 12px 0 0 !important; padding:.45rem .95rem !important; }}
.stTabs [aria-selected="true"] {{ color:{C_PRIMARY_DARK} !important; background:rgba(100,174,188,.18) !important; border-bottom:3px solid {C_PRIMARY_DARK} !important; }}
.rank-row-bg {{ background: rgba(255,255,255,.82); border-radius: 18px; padding: .55rem .75rem; margin-bottom: .45rem; box-shadow: 0 6px 18px rgba(0,0,0,.04); }}
.pos-badge {{ width:54px; height:54px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; background:{C_PRIMARY_DARK}; font-weight:900; font-size:1.2rem; box-shadow: inset 0 0 0 4px rgba(255,255,255,.15); }}
.pos-badge.gold {{ background: linear-gradient(135deg, {C_SECONDARY_DARK}, {C_SECONDARY_LIGHT}); }}
.pos-badge.silver {{ background: linear-gradient(135deg, {C_GRAY}, {C_GRAY_LIGHT}); color:{C_GRAY_DARK}; }}
.pos-badge.bronze {{ background: linear-gradient(135deg, {C_SECONDARY_DARK}, {C_SECONDARY}); }}
.rank-name {{ font-weight:900; color:{C_GRAY_DARK}; font-size:1.1rem; }}
.rank-points {{ font-weight:900; color:{C_PRIMARY_DARK}; font-size:1.4rem; text-align:center; }}
.rank-label {{ color:{C_PRIMARY_DARK}; font-size:.82rem; text-align:center; font-weight:800; }}
.tab-hint, p, li, label {{ color:{C_GRAY_DARK} !important; font-size:1rem; }}
.stButton > button {{ background: linear-gradient(135deg, {C_SECONDARY} 0%, {C_SECONDARY_LIGHT} 100%) !important; color: #FFFFFF !important; border: 1px solid {C_SECONDARY_DARK} !important; font-weight: 900 !important; border-radius: 12px !important; box-shadow: 0 10px 22px rgba(204,97,0,.28) !important; padding: .6rem .95rem !important; }}
.stButton > button:hover {{ filter: brightness(1.03); border-color: {C_SECONDARY_DARK} !important; }}
.stButton > button p {{ color: #FFFFFF !important; font-weight: 900 !important; }}
.detail-wrap {{ background:rgba(255,255,255,.95); border:1px solid rgba(50,125,142,.16); border-radius:18px; padding:1rem 1rem .9rem; margin:.2rem 0 1rem; box-shadow:0 10px 24px rgba(0,0,0,.05); }}
.detail-header {{ display:flex; justify-content:space-between; align-items:flex-end; gap:1rem; flex-wrap:wrap; }}
.detail-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.08rem; }}
.detail-total {{ color:{C_SECONDARY_DARK}; font-weight:900; font-size:1rem; }}
.highlight-note {{ background:rgba(241,200,49,.18); border-left:6px solid {C_SECONDARY}; border-radius:14px; padding:.75rem .9rem; color:{C_GRAY_DARK}; font-weight:700; margin:.25rem 0 1rem; }}
@media (max-width: 900px) {{ .title-main {{ font-size:1.85rem; }} .podium-slot {{ height:auto; }} .podium-1, .podium-2, .podium-3 {{ min-height:unset; }} }}
</style>
"""
st.markdown(style, unsafe_allow_html=True)

try:
    sheets = load_raw_data()
    if 'Puntos' not in sheets or 'Resumen de Apuestas' not in sheets:
        raise ValueError(f"Faltan hojas requeridas. Hojas detectadas: {list(sheets.keys())}")
    ranking, team_points = parse_puntos(sheets['Puntos'])
    resolve_participant = build_participant_details(sheets['Resumen de Apuestas'], team_points)
except Exception as e:
    st.error(f"No se pudo cargar la clasificación: {e}")
    st.stop()

if 'selected_participant_name' not in st.session_state:
    st.session_state.selected_participant_name = None

last_loaded = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

st.markdown(f"""
<div class='title-wrap'>
  <div class='title-main'>Clasificación Oficial · Porra Mundial 2026</div>
  <div class='title-sub'>Actualización automática · Última carga de datos: <b>{last_loaded}</b></div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='section-title'>🏅 Podium</div>", unsafe_allow_html=True)
podium = ranking.nsmallest(3, 'POS')[['PARTICIPANTE', 'PUNTOS_TOTALES']].reset_index(drop=True)
if len(podium) >= 3:
    c1, c2, c3 = st.columns([1.15, 1, 0.9])
    with c1:
        row = podium.iloc[0]
        st.markdown(f"""
        <div class='podium-wrap'><div class='podium-slot'><div class='podium-box podium-1'>
            <div class='podium-step-label'>🥇 1º</div>
            <div class='podium-name'>{row['PARTICIPANTE']}</div>
            <div class='podium-points'>{int(row['PUNTOS_TOTALES'])} puntos</div>
        </div></div></div>
        """, unsafe_allow_html=True)
    with c2:
        row = podium.iloc[1]
        st.markdown(f"""
        <div class='podium-wrap'><div class='podium-slot'><div class='podium-box podium-2'>
            <div class='podium-step-label'>🥈 2º</div>
            <div class='podium-name'>{row['PARTICIPANTE']}</div>
            <div class='podium-points'>{int(row['PUNTOS_TOTALES'])} puntos</div>
        </div></div></div>
        """, unsafe_allow_html=True)
    with c3:
        row = podium.iloc[2]
        st.markdown(f"""
        <div class='podium-wrap'><div class='podium-slot'><div class='podium-box podium-3'>
            <div class='podium-step-label'>🥉 3º</div>
            <div class='podium-name'>{row['PARTICIPANTE']}</div>
            <div class='podium-points'>{int(row['PUNTOS_TOTALES'])} puntos</div>
        </div></div></div>
        """, unsafe_allow_html=True)

rank_tab, teams_tab = st.tabs(['🏆 Ranking', '🌍 Equipos'])

with rank_tab:
    st.markdown("<div class='section-title'>Clasificación general</div>", unsafe_allow_html=True)
    selected_name = st.session_state.get('selected_participant_name')
    for _, row in ranking.iterrows():
        pos = int(row['POS']) if pd.notna(row['POS']) else '-'
        points = int(row['PUNTOS_TOTALES']) if pd.notna(row['PUNTOS_TOTALES']) else 0
        participant = str(row['PARTICIPANTE']).strip()
        badge_class = ''
        if pos == 1:
            badge_class = 'gold'
        elif pos == 2:
            badge_class = 'silver'
        elif pos == 3:
            badge_class = 'bronze'

        st.markdown("<div class='rank-row-bg'>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([0.7, 3.3, 1.2, 1.35])
        with col1:
            st.markdown(f"<div class='pos-badge {badge_class}'>{pos}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='rank-name'>{participant}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='rank-label'>Puntos</div><div class='rank-points'>{points}</div>", unsafe_allow_html=True)
        with col4:
            if st.button('Ver selecciones', key=f"pick_{normalize_text(participant)}"):
                if st.session_state.selected_participant_name == participant:
                    st.session_state.selected_participant_name = None
                else:
                    st.session_state.selected_participant_name = participant
        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.get('selected_participant_name') == participant:
            detail = resolve_participant(participant)
            if detail is None:
                st.warning(f"No he podido relacionar automáticamente a '{participant}' con la hoja 'Resumen de Apuestas'.")
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
                            st.markdown(team_card_html(pick['Equipo'], int(pick['Puntos acumulados']), highlight=int(pick['Puntos acumulados']) > 0, subtitle=pick['Nivel']), unsafe_allow_html=True)

with teams_tab:
    st.markdown("<div class='section-title'>Equipos</div>", unsafe_allow_html=True)
    selected_name = st.session_state.get('selected_participant_name')
    detail = resolve_participant(selected_name) if selected_name else None
    selected_team_keys = set(detail['team_keys']) if detail is not None else set()
    if detail is not None:
        st.markdown(f"<div class='highlight-note'>Equipos resaltados para <b>{detail['participante']}</b>.</div>", unsafe_allow_html=True)

    cards = team_points.copy()
    cols_per_row = 4
    for i in range(0, len(cards), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, (_, row) in zip(cols, cards.iloc[i:i+cols_per_row].iterrows()):
            with col:
                st.markdown(team_card_html(str(row['Equipo']), int(row['TOTAL']), highlight=row['TEAM_KEY'] in selected_team_keys), unsafe_allow_html=True)
