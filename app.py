
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

LEVEL_COLORS = {
    'Nivel 1': '#F1C831',
    'Nivel 2': '#F28E00',
    'Nivel 3': '#CC6100',
    'Nivel 4': '#64AEBC',
    'Nivel 5': '#327D8E',
    'Nivel 6': '#004A5F',
    'Nivel 7': '#706F6F',
    'Nivel 8': '#9C9B9B',
}


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
def load_workbook():
    url = make_download_url(SOURCE_URL)
    file_bytes = download_bytes(url)
    xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    sheets = {}
    for name in xls.sheet_names:
        header = None if name == 'Puntos' else 0
        sheets[name] = pd.read_excel(io.BytesIO(file_bytes), sheet_name=name, header=header, engine='openpyxl')
    return sheets


def _find_table_start(row_values, labels, occurrence='first'):
    norm = [str(x).strip().upper() if pd.notna(x) else '' for x in row_values]
    labels_norm = [x.strip().upper() for x in labels]
    matches = []
    for i in range(len(norm) - len(labels_norm) + 1):
        if norm[i:i+len(labels_norm)] == labels_norm:
            matches.append(i)
    if not matches:
        return None
    return matches[-1] if occurrence == 'last' else matches[0]


def parse_puntos(raw: pd.DataFrame):
    header_row = raw.iloc[1].tolist()
    curr_start = _find_table_start(header_row, ['POS', 'PARTICIPANTE', 'PUNTOS TOTALES'], occurrence='last')
    team_start = _find_table_start(
        header_row,
        ['Equipo', 'Fase Grupos', '1/16 (5pts)', '1/8 (5pts)', '1/4 (5pts)', 'Semis (10pts)', 'Final (25pts)', 'Campeón (35pts)', 'TOTAL'],
        occurrence='first'
    )
    if curr_start is None:
        raise ValueError("No encuentro las columnas del ranking en la hoja 'Puntos'.")
    if team_start is None:
        raise ValueError("No encuentro la tabla de puntos por equipo en la hoja 'Puntos'.")

    ranking = raw.iloc[2:, curr_start:curr_start+3].copy()
    ranking.columns = ['POS', 'PARTICIPANTE', 'PUNTOS_TOTALES']
    ranking = ranking.dropna(subset=['PARTICIPANTE']).copy()
    ranking['PARTICIPANTE'] = ranking['PARTICIPANTE'].astype(str).str.strip()
    ranking['POS'] = pd.to_numeric(ranking['POS'], errors='coerce')
    ranking['PUNTOS_TOTALES'] = pd.to_numeric(ranking['PUNTOS_TOTALES'], errors='coerce').fillna(0)
    ranking = ranking.sort_values(['POS', 'PUNTOS_TOTALES', 'PARTICIPANTE'], ascending=[True, False, True]).reset_index(drop=True)

    team_points = raw.iloc[2:, team_start:team_start+9].copy()
    team_points.columns = ['Equipo', 'Fase_Grupos', 'Dieciseisavos', 'Octavos', 'Cuartos', 'Semis', 'Final', 'Campeon', 'TOTAL']
    team_points = team_points.dropna(subset=['Equipo']).copy()
    team_points['Equipo'] = team_points['Equipo'].astype(str).str.strip()
    for col in [c for c in team_points.columns if c != 'Equipo']:
        team_points[col] = pd.to_numeric(team_points[col], errors='coerce').fillna(0)
    team_points = team_points.sort_values(['TOTAL', 'Equipo'], ascending=[False, True]).reset_index(drop=True)
    team_points['TEAM_KEY'] = team_points['Equipo'].apply(normalize_text)
    return ranking, team_points


def build_participant_details(resumen_df: pd.DataFrame, team_points: pd.DataFrame):
    pts_by_team = dict(zip(team_points['TEAM_KEY'], team_points['TOTAL']))
    levels = [c for c in resumen_df.columns if str(c).strip().lower().startswith('nivel')]
    by_exact, names = {}, []
    for _, row in resumen_df.iterrows():
        participant = str(row['PARTICIPANTE']).strip()
        pkey = normalize_text(participant)
        picks, total = [], 0
        for lvl in levels:
            team = row[lvl]
            if pd.isna(team):
                continue
            team = str(team).strip()
            pts = int(pts_by_team.get(normalize_text(team), 0))
            total += pts
            picks.append({'Nivel': str(lvl), 'Equipo': team, 'Puntos': pts})
        info = {'participante': participant, 'total_selecciones': total, 'equipos': picks}
        by_exact[pkey] = info
        names.append((pkey, info))

    def resolve(participant_name: str):
        key = normalize_text(participant_name)
        if key in by_exact:
            return by_exact[key]
        candidates = [info for pkey, info in names if key in pkey or pkey in key]
        if len(candidates) == 1:
            return candidates[0]
        candidates = [info for pkey, info in names if pkey.startswith(key) or key.startswith(pkey)]
        if len(candidates) == 1:
            return candidates[0]
        return None
    return resolve


def build_teams_by_level(resumen_df: pd.DataFrame, team_points: pd.DataFrame):
    pts_by_team = dict(zip(team_points['TEAM_KEY'], team_points['TOTAL']))
    levels = [c for c in resumen_df.columns if str(c).strip().lower().startswith('nivel')]
    result = {}
    for lvl in levels:
        items, seen = [], set()
        for team in resumen_df[lvl].dropna().tolist():
            team = str(team).strip()
            tkey = normalize_text(team)
            if tkey in seen:
                continue
            seen.add(tkey)
            items.append({'Equipo': team, 'Puntos': int(pts_by_team.get(tkey, 0))})
        result[str(lvl)] = sorted(items, key=lambda x: (-x['Puntos'], x['Equipo']))
    return result


def calculate_prizes(ranking: pd.DataFrame):
    participantes = int(ranking['PARTICIPANTE'].nunique())
    recaudacion = participantes * 10.0
    premios = {}
    first_group = ranking[pd.to_numeric(ranking['POS'], errors='coerce') == 1].copy()
    second_group = ranking[pd.to_numeric(ranking['POS'], errors='coerce') == 2].copy()

    if len(first_group) > 1:
        premio_individual = recaudacion / len(first_group)
        for name in first_group['PARTICIPANTE'].astype(str).tolist():
            premios[name] = premio_individual
        segundo_premio_total = 0.0
    else:
        if len(first_group) == 1:
            premios[str(first_group.iloc[0]['PARTICIPANTE'])] = recaudacion * 0.70
        segundo_premio_total = recaudacion * 0.30
        if len(second_group) > 0:
            premio_segundo_individual = segundo_premio_total / len(second_group)
            for name in second_group['PARTICIPANTE'].astype(str).tolist():
                premios[name] = premio_segundo_individual

    return recaudacion, premios


def format_eur(value: float) -> str:
    if value is None or value == 0:
        return ""
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value))} €"
    return f"{value:.2f} €".replace('.', ',')


def team_card_html(team: str, points: int, accent: str, subtitle: str = ''):
    subtitle_html = f"<div style='color:{C_GRAY};font-size:.82rem;margin-top:.15rem'>{subtitle}</div>" if subtitle else ""
    return f"""
    <div style="background:white;border:1px solid {accent};border-left:6px solid {accent};border-radius:16px;padding:.9rem 1rem;box-shadow:0 6px 18px rgba(0,0,0,.05);min-height:116px;">
      <div style="color:{C_GRAY_DARK};font-weight:900;font-size:1.08rem;line-height:1.2;text-align:center;">{team}</div>
      {subtitle_html}
      <div style="color:{accent};font-weight:900;font-size:1.55rem;margin-top:.62rem;text-align:center;">{points}</div>
    </div>
    """


def podium_group_html(place_label: str, names: list[str], points: int, prize_text: str, box_class: str) -> str:
    names_html = "<br>".join(names) if names else "—"
    points_html = f"<div class='podium-points'>{points} puntos</div>" if names else ""
    prize_html = f"<div class='podium-prize'>{prize_text}</div>" if prize_text else ""
    return f"<div class='podium-wrap'><div class='podium-slot'><div class='podium-box {box_class}'><div class='podium-step-label'>{place_label}</div><div class='podium-name podium-name-multi'>{names_html}</div>{points_html}{prize_html}</div></div></div>"


style = f"""
<style>
.stApp {{ background: linear-gradient(180deg, #ffffff 0%, {C_BG} 45%, #eef5f6 100%); }}
.block-container {{ max-width: 1180px; padding-top: 1.1rem; padding-bottom: 2rem; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.title-wrap {{ background: linear-gradient(135deg, {C_PRIMARY_DARK} 0%, {C_PRIMARY} 58%, {C_PRIMARY_LIGHT} 100%); border-radius: 24px; padding: 1.25rem 1.4rem; margin-bottom: 1rem; box-shadow: 0 18px 40px rgba(0,74,95,.24); }}
.title-main {{ color:#fff; font-size:2.35rem; font-weight:900; line-height:1.05; margin:0; text-align:center; }}
.title-sub {{ color:rgba(255,255,255,.98); margin-top:.35rem; font-size:1rem; font-weight:600; text-align:center; }}
.section-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.28rem; margin-bottom:.4rem; }}
.podium-wrap {{ margin-top:.15rem; margin-bottom:.4rem; }}
.podium-slot {{ display:flex; align-items:flex-end; justify-content:center; height:220px; }}
.podium-box {{ width:100%; border-radius:18px 18px 14px 14px; padding:1rem 1rem .95rem; color:white; box-shadow:0 12px 26px rgba(0,0,0,.12); display:flex; flex-direction:column; justify-content:center; text-align:center; }}
.podium-1 {{ background: linear-gradient(135deg, {C_SECONDARY_DARK} 0%, {C_SECONDARY} 55%, {C_SECONDARY_LIGHT} 100%); min-height:210px; }}
.podium-2 {{ background: linear-gradient(135deg, {C_GRAY} 0%, #9C9B9B 60%, {C_GRAY_LIGHT} 100%); color:{C_GRAY_DARK}; min-height:165px; }}
.podium-3 {{ background: linear-gradient(135deg, #a85810 0%, {C_SECONDARY_DARK} 60%, {C_SECONDARY} 100%); min-height:145px; }}
.podium-step-label {{ font-size:2rem; font-weight:900; margin-bottom:.25rem; text-align:center; }}
.podium-name {{ font-weight:900; font-size:1.08rem; margin-top:.45rem; line-height:1.18; text-align:center; max-width:100%; overflow-wrap:anywhere; }}
.podium-name-multi {{ font-size:1rem; line-height:1.25; }}
.podium-1 .podium-name {{ font-size:1.24rem; line-height:1.22; }}
.podium-1 .podium-name-multi {{ font-size:1.12rem; line-height:1.28; }}
.podium-points {{ margin-top:.5rem; font-size:1rem; font-weight:800; text-align:center; }}
.podium-prize {{ margin-top:.35rem; font-size:.92rem; font-weight:900; text-align:center; opacity:.98; }}
.stTabs [data-baseweb="tab-list"] {{ gap:.45rem; border-bottom:2px solid rgba(0,74,95,.12); }}
.stTabs [data-baseweb="tab"] {{ color:{C_PRIMARY_DARK} !important; font-weight:900 !important; font-size:1.03rem !important; background:rgba(255,255,255,.76) !important; border-radius:12px 12px 0 0 !important; padding:.55rem 1rem !important; }}
.stTabs [aria-selected="true"] {{ color:{C_PRIMARY_DARK} !important; background:rgba(100,174,188,.18) !important; border-bottom:3px solid {C_PRIMARY_DARK} !important; }}
.stTabs [data-baseweb="tab"] p {{ font-weight:900 !important; font-size:1.03rem !important; }}
.rank-row-bg {{ background: rgba(255,255,255,.18); border-radius: 12px; padding: .14rem .28rem; margin-bottom: .08rem; box-shadow: none; }}
.rank-row-bg.open {{ animation: fadeInUp .24s ease-out; }}
@keyframes fadeInUp {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
.pos-badge {{ width:54px; height:54px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; background:{C_PRIMARY_DARK}; font-weight:900; font-size:1.2rem; box-shadow: inset 0 0 0 4px rgba(255,255,255,.15); }}
.pos-badge.gold {{ background: linear-gradient(135deg, {C_SECONDARY_DARK}, {C_SECONDARY_LIGHT}); }}
.pos-badge.silver {{ background: linear-gradient(135deg, {C_GRAY}, {C_GRAY_LIGHT}); color:{C_GRAY_DARK}; }}
.pos-badge.bronze {{ background: linear-gradient(135deg, {C_SECONDARY_DARK}, {C_SECONDARY}); }}
.rank-name {{ font-weight:900; color:{C_GRAY_DARK}; font-size:1.08rem; }}
.rank-points {{ font-weight:900; color:{C_PRIMARY_DARK}; font-size:1.4rem; text-align:center; }}
.rank-label {{ color:{C_PRIMARY_DARK}; font-size:.82rem; text-align:center; font-weight:800; }}
.rank-prize {{ color:{C_SECONDARY_DARK}; font-size:.98rem; text-align:center; font-weight:900; }}
.rank-prize-label {{ color:{C_PRIMARY_DARK}; font-size:.82rem; text-align:center; font-weight:800; }}
.stButton > button {{ background: linear-gradient(135deg, {C_SECONDARY} 0%, {C_SECONDARY_LIGHT} 100%) !important; color: #FFFFFF !important; border: 1px solid {C_SECONDARY_DARK} !important; font-weight: 900 !important; border-radius: 12px !important; box-shadow: 0 10px 22px rgba(204,97,0,.28) !important; padding: .6rem .95rem !important; }}
.stButton > button:hover {{ filter: brightness(1.03); border-color: {C_SECONDARY_DARK} !important; }}
.stButton > button p {{ color: #FFFFFF !important; font-weight: 900 !important; }}
.detail-wrap {{ background:rgba(255,255,255,.95); border:1px solid rgba(50,125,142,.16); border-radius:18px; padding:.9rem .95rem .85rem; margin:.06rem 0 .55rem; box-shadow:0 8px 18px rgba(0,0,0,.04); animation: fadeInUp .24s ease-out; }}
.detail-header {{ display:flex; justify-content:space-between; align-items:flex-end; gap:1rem; flex-wrap:wrap; }}
.detail-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.08rem; }}
.detail-total {{ color:{C_SECONDARY_DARK}; font-weight:900; font-size:1rem; }}
.level-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.02rem; margin:.3rem 0 .55rem; }}
div[data-testid="column"]:has(.refresh-anchor) [data-testid="stButton"] button {{
  width: 34px !important;
  min-width: 34px !important;
  height: 34px !important;
  padding: 0 !important;
  border-radius: 999px !important;
  background: rgba(0, 74, 95, .08) !important;
  border: 1px solid rgba(0, 74, 95, .14) !important;
  box-shadow: none !important;
  opacity: .55 !important;
  color: {C_PRIMARY_DARK} !important;
  font-size: 1rem !important;
}}
div[data-testid="column"]:has(.refresh-anchor) [data-testid="stButton"] button p {{ color: {C_PRIMARY_DARK} !important; font-size: 1rem !important; }}
div[data-testid="column"]:has(.refresh-anchor) [data-testid="stButton"] button:hover {{ opacity: .9 !important; background: rgba(0, 74, 95, .12) !important; }}
@media (max-width: 900px) {{ .title-main {{ font-size:1.85rem; }} .podium-slot {{ height:auto; }} .podium-1, .podium-2, .podium-3 {{ min-height:unset; }} }}
</style>
"""
st.markdown(style, unsafe_allow_html=True)

try:
    sheets = load_workbook()
    ranking, team_points = parse_puntos(sheets['Puntos'])
    resolve_participant = build_participant_details(sheets['Resumen de Apuestas'], team_points)
    teams_by_level = build_teams_by_level(sheets['Resumen de Apuestas'], team_points)
    recaudacion, premios = calculate_prizes(ranking)
except Exception as e:
    st.error(f"No se pudo cargar la clasificación: {e}")
    st.stop()

if 'selected_participant_name' not in st.session_state:
    st.session_state.selected_participant_name = None

participant_count = int(ranking['PARTICIPANTE'].nunique())
last_loaded = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
st.markdown(f"""
<div class='title-wrap'>
  <div class='title-main'>Clasificación Oficial · Porra Mundial 2026</div>
  <div class='title-sub'>Última actualización: <b>{last_loaded}</b></div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='section-title'>🏅 Podium</div>", unsafe_allow_html=True)
podium_groups = {}
for pos in [1, 2, 3]:
    group = ranking[pd.to_numeric(ranking['POS'], errors='coerce') == pos].copy()
    if group.empty:
        podium_groups[pos] = {'names': [], 'points': 0, 'prize_text': ''}
    else:
        names = group.sort_values(['PARTICIPANTE'])['PARTICIPANTE'].astype(str).tolist()
        points = int(group['PUNTOS_TOTALES'].max())
        if pos == 1 and len(group) > 0:
            prize_values = [premios.get(name, 0) for name in names]
            prize_text = f"Premio: {format_eur(prize_values[0])}" if prize_values and prize_values[0] > 0 else ''
        elif pos == 2 and len(group) > 0:
            prize_values = [premios.get(name, 0) for name in names]
            prize_text = f"Premio: {format_eur(prize_values[0])}" if prize_values and prize_values[0] > 0 else ''
        else:
            prize_text = ''
        podium_groups[pos] = {'names': names, 'points': points, 'prize_text': prize_text}

c1, c2, c3 = st.columns([1.15, 1, 0.9])
with c1:
    st.markdown(podium_group_html('🥇 1º', podium_groups[1]['names'], podium_groups[1]['points'], podium_groups[1]['prize_text'], 'podium-1'), unsafe_allow_html=True)
with c2:
    st.markdown(podium_group_html('🥈 2º', podium_groups[2]['names'], podium_groups[2]['points'], podium_groups[2]['prize_text'], 'podium-2'), unsafe_allow_html=True)
with c3:
    st.markdown(podium_group_html('🥉 3º', podium_groups[3]['names'], podium_groups[3]['points'], '', 'podium-3'), unsafe_allow_html=True)

rank_tab, teams_tab = st.tabs(['🏆 Ranking', '🌍 Equipos'])

with rank_tab:
    st.markdown(f"<div class='section-title'>Clasificación general ({participant_count} participantes)</div>", unsafe_allow_html=True)
    for _, row in ranking.iterrows():
        pos = int(row['POS']) if pd.notna(row['POS']) else '-'
        points = int(row['PUNTOS_TOTALES']) if pd.notna(row['PUNTOS_TOTALES']) else 0
        participant = str(row['PARTICIPANTE']).strip()
        prize_value = premios.get(participant, 0)
        badge_class = 'gold' if pos == 1 else 'silver' if pos == 2 else 'bronze' if pos == 3 else ''
        row_extra = ' open' if st.session_state.get('selected_participant_name') == participant else ''
        st.markdown(f"<div class='rank-row-bg{row_extra}'>", unsafe_allow_html=True)
        a, b, c, d, e = st.columns([0.7, 3.0, 1.1, 1.15, 1.35])
        with a:
            st.markdown(f"<div class='pos-badge {badge_class}'>{pos}</div>", unsafe_allow_html=True)
        with b:
            st.markdown(f"<div class='rank-name'>{participant}</div>", unsafe_allow_html=True)
        with c:
            st.markdown(f"<div class='rank-label'>Puntos</div><div class='rank-points'>{points}</div>", unsafe_allow_html=True)
        with d:
            if prize_value > 0 and pos in [1, 2]:
                st.markdown(f"<div class='rank-prize-label'>Premio</div><div class='rank-prize'>{format_eur(prize_value)}</div>", unsafe_allow_html=True)
        with e:
            if st.button('Ver selecciones', key=f"pick_{normalize_text(participant)}"):
                st.session_state.selected_participant_name = None if st.session_state.selected_participant_name == participant else participant
        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.get('selected_participant_name') == participant:
            detail = resolve_participant(participant)
            if detail:
                st.markdown(f"<div class='detail-wrap'><div class='detail-header'><div class='detail-title'>Selecciones de {detail['participante']}</div><div class='detail-total'>{int(detail['total_selecciones'])} puntos</div></div></div>", unsafe_allow_html=True)
                picks = detail['equipos']
                for i in range(0, len(picks), 4):
                    cols = st.columns(4)
                    for col, pick in zip(cols, picks[i:i+4]):
                        with col:
                            accent = LEVEL_COLORS.get(pick['Nivel'], C_PRIMARY_DARK)
                            st.markdown(team_card_html(pick['Equipo'], int(pick['Puntos']), accent, subtitle=pick['Nivel']), unsafe_allow_html=True)

with teams_tab:
    st.markdown("<div class='section-title'>Equipos</div>", unsafe_allow_html=True)
    for level, items in teams_by_level.items():
        accent = LEVEL_COLORS.get(level, C_PRIMARY_DARK)
        st.markdown(f"<div class='level-title' style='color:{accent}'>{level}</div>", unsafe_allow_html=True)
        for i in range(0, len(items), 4):
            cols = st.columns(4)
            for col, item in zip(cols, items[i:i+4]):
                with col:
                    st.markdown(team_card_html(item['Equipo'], int(item['Puntos']), accent), unsafe_allow_html=True)

left, mid, right = st.columns([10, 1, 10])
with mid:
    st.markdown("<div class='refresh-anchor'></div>", unsafe_allow_html=True)
    if st.button("↻", key="refresh_data", help="Actualizar datos del Excel"):
        st.cache_data.clear()
        st.rerun()
