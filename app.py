
import io
import re
import urllib.request
from itertools import combinations

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Versia Servicios Distribuidos · Porra Mundial 2026", page_icon="🌍", layout="wide")

SOURCE_URL = "https://docs.google.com/spreadsheets/d/1q4SpZQb7_7UrX-NtReo2XS7jBMvHH0xI/edit?usp=drivesdk&ouid=105950533705571221592&rtpof=true&sd=true"
CACHE_MINUTES = 5
PRICE_PER_ENTRY = 10
DEADLINE_TEXT = "11/06/2026 a las 12:00am"

C_PRIMARY_DARK = "#004A5F"
C_PRIMARY = "#327D8E"
C_PRIMARY_LIGHT = "#64AEBC"
C_SECONDARY_DARK = "#CC6100"
C_SECONDARY = "#F28E00"
C_SECONDARY_LIGHT = "#F1C831"
C_GRAY_DARK = "#383737"
C_GRAY = "#706F6F"
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

LEVEL_TEAMS = {'Nivel 1': ['Francia', 'España', 'Argentina', 'Inglaterra', 'Portugal', 'Brasil'], 'Nivel 2': ['Países Bajos', 'Marruecos', 'Bélgica', 'Alemania', 'Croacia', 'Colombia'], 'Nivel 3': ['Senegal', 'México', 'EEUU', 'Uruguay', 'Japón', 'Suiza'], 'Nivel 4': ['Irán', 'Turquía', 'Ecuador', 'Austria', 'Corea del Sur', 'Australia'], 'Nivel 5': ['Argelia', 'Egipto', 'Canadá', 'Noruega', 'Panamá', 'C. de Marfil'], 'Nivel 6': ['Suecia', 'Paraguay', 'Rep. Checa', 'Escocia', 'Túnez', 'R.D. Congo'], 'Nivel 7': ['Uzbekistán', 'Catar', 'Irak', 'Sudáfrica', 'A. Saudita', 'Jordania'], 'Nivel 8': ['Bosnia', 'Cabo Verde', 'Ghana', 'Curazao', 'Haití', 'N. Zelanda']}


def make_download_url(url: str) -> str:
    url = url.strip().replace("&amp;", "&")
    m = re.search(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if m:
        sid = m.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=xlsx"
    return url


@st.cache_data(ttl=CACHE_MINUTES * 60)
def download_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


@st.cache_data(ttl=CACHE_MINUTES * 60)
def load_resumen() -> pd.DataFrame:
    url = make_download_url(SOURCE_URL)
    file_bytes = download_bytes(url)
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name='Resumen de Apuestas', engine='openpyxl')


def get_levels(df: pd.DataFrame):
    cols = [c for c in df.columns if str(c).strip().lower().startswith('nivel')]
    ordered = sorted(cols, key=lambda x: int(re.search(r'(\d+)', str(x)).group(1)) if re.search(r'(\d+)', str(x)) else 999)
    return ordered


def count_entries(df: pd.DataFrame) -> int:
    if 'PARTICIPANTE' not in df.columns:
        return 0
    return int(df['PARTICIPANTE'].dropna().shape[0])


def escape_html(text):
    text = str(text)
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))


def get_bet_records(df: pd.DataFrame):
    levels = get_levels(df)
    if 'PARTICIPANTE' not in df.columns or not levels:
        return [], levels
    work = df.dropna(subset=['PARTICIPANTE']).copy()
    work['PARTICIPANTE'] = work['PARTICIPANTE'].astype(str).str.strip()
    for level in levels:
        work[level] = work[level].fillna('').astype(str).str.strip()
    records = []
    for _, row in work[['PARTICIPANTE'] + levels].iterrows():
        records.append({
            'participante': row['PARTICIPANTE'],
            'choices': {level: row[level] for level in levels}
        })
    return records, levels


def find_duplicate_bets(df: pd.DataFrame):
    records, levels = get_bet_records(df)
    if not records or not levels:
        return []
    items = []
    for rec in records:
        combo_key = ' || '.join(rec['choices'][level] for level in levels)
        items.append((combo_key, rec['participante']))
    groups = {}
    for key, participante in items:
        groups.setdefault(key, []).append(participante)
    duplicates = []
    for participantes in groups.values():
        if len(participantes) > 1:
            duplicates.append({
                'participantes': participantes,
                'repeticiones': len(participantes)
            })
    duplicates.sort(key=lambda x: (-x['repeticiones'], ', '.join(x['participantes'])))
    return duplicates


def analyze_similarity(df: pd.DataFrame):
    records, levels = get_bet_records(df)
    if not records or not levels:
        return {
            'exact_groups': [],
            'top_pairs': [],
            'near_clone_pairs': 0,
            'max_matches': 0,
            'levels_count': len(levels)
        }

    exact_groups = find_duplicate_bets(df)
    pair_scores = []
    for left, right in combinations(records, 2):
        matches = 0
        diff_levels = []
        for level in levels:
            if left['choices'][level] == right['choices'][level]:
                matches += 1
            else:
                diff_levels.append(level)
        pair_scores.append({
            'a': left['participante'],
            'b': right['participante'],
            'matches': matches,
            'diff_levels': diff_levels,
        })

    pair_scores.sort(key=lambda x: (-x['matches'], x['a'], x['b']))
    non_exact = [p for p in pair_scores if p['matches'] < len(levels)]
    top_pairs = non_exact[:5]
    near_clone_pairs = sum(1 for p in non_exact if p['matches'] >= max(len(levels) - 1, 1))
    max_matches = pair_scores[0]['matches'] if pair_scores else 0

    return {
        'exact_groups': exact_groups,
        'top_pairs': top_pairs,
        'near_clone_pairs': near_clone_pairs,
        'max_matches': max_matches,
        'levels_count': len(levels)
    }


def render_similarity_block(insights: dict) -> str:
    levels_count = insights.get('levels_count', 0)
    exact_groups = insights.get('exact_groups', [])
    top_pairs = insights.get('top_pairs', [])
    near_clone_pairs = insights.get('near_clone_pairs', 0)
    max_matches = insights.get('max_matches', 0)

    if exact_groups:
        final_result_html = ["<div class='affinity-card'><div class='affinity-card-title'>Resultado final: porras espejo</div>"]
        final_result_html.append("<div class='affinity-item'><b>Sí, ha habido porras espejo.</b></div>")
        for dup in exact_groups[:4]:
            participantes = ', '.join(escape_html(p) for p in dup['participantes'])
            final_result_html.append(f"<div class='affinity-item'><b>{dup['repeticiones']} personas</b>: {participantes}</div>")
        final_result_html.append("</div>")
        final_result_card = ''.join(final_result_html)
    else:
        final_result_card = "<div class='affinity-card'><div class='affinity-card-title'>Resultado final: porras espejo</div><div class='affinity-item'><b>No ha habido porras espejo.</b></div><div class='affinity-item'>No se han detectado apuestas 100% idénticas entre participantes.</div></div>"

    if top_pairs:
        pair_html = ["<div class='affinity-card'><div class='affinity-card-title'>Las porras más parecidas</div>"]
        for pair in top_pairs:
            pair_names = f"{escape_html(pair['a'])} · {escape_html(pair['b'])}"
            diff_text = ', '.join(escape_html(x) for x in pair['diff_levels']) if pair['diff_levels'] else 'Ningún nivel'
            pair_html.append(
                f"<div class='affinity-item'><b>{pair_names}</b><br>Coinciden en <b>{pair['matches']}/{levels_count}</b> niveles."
                f" <span class='affinity-muted'>Difieren en: {diff_text}</span></div>"
            )
        pair_html.append("</div>")
        pair_card = ''.join(pair_html)
    else:
        pair_card = "<div class='affinity-card'><div class='affinity-card-title'>Las porras más parecidas</div><div class='affinity-item'>No hay suficientes datos para detectar afinidades destacables entre porras.</div></div>"

    return (
        "<div class='section-title'>Radar de afinidades entre participantes</div>"
        "<div class='analysis-box'>"
        "<div class='affinity-summary'>La inscripción ya se ha cerrado. Ahora toca mirar qué porras han ido por libre, cuáles se han calcado y qué parejas han rozado el déjà vu futbolero.</div>"
        "<div class='affinity-stats'>"
        f"<div class='affinity-stat'><div class='affinity-stat-value'>{len(exact_groups)}</div><div class='affinity-stat-label'>Grupos con porra idéntica</div></div>"
        f"<div class='affinity-stat'><div class='affinity-stat-value'>{near_clone_pairs}</div><div class='affinity-stat-label'>Parejas casi calcadas</div></div>"
        f"<div class='affinity-stat'><div class='affinity-stat-value'>{max_matches}/{levels_count}</div><div class='affinity-stat-label'>Coincidencia máxima detectada</div></div>"
        "</div>"
        "<div class='affinity-grid'>" + final_result_card + pair_card + "</div>"
        "</div>"
    )


def render_level_selection_chart(df: pd.DataFrame) -> str:
    levels = [lvl for lvl in get_levels(df) if lvl in LEVEL_TEAMS]
    if not levels:
        levels = list(LEVEL_TEAMS.keys())

    total_entries = max(count_entries(df), 1)
    parts = ["<div class='levels-grid'>"]
    for level in levels:
        teams = LEVEL_TEAMS.get(level, [])
        series = df[level].dropna().astype(str).str.strip() if level in df.columns else pd.Series(dtype=str)
        counts = series.value_counts()
        percentages = []
        for team in teams:
            pct = round((int(counts.get(team, 0)) / total_entries) * 100, 1)
            percentages.append((team, pct))
        percentages = sorted(percentages, key=lambda x: (-x[1], x[0]))
        color = LEVEL_COLORS.get(str(level), C_PRIMARY_DARK)
        teams_text = ' · '.join(escape_html(team) for team in teams)
        title_html = (
            f"<div class='level-name'>{escape_html(level)}</div><div class='level-teams'>({teams_text})</div>"
            if teams_text else f"<div class='level-name'>{escape_html(level)}</div>"
        )
        parts.append(f"<div class='level-card'><div class='level-card-title' style='color:{color}'>{title_html}</div>")
        for team_name, pct_value in percentages:
            pct_str = f"{pct_value:.1f}%"
            parts.append(
                f"<div class='bar-row'>"
                f"<div class='bar-top'><span class='bar-team'>{escape_html(team_name)}</span><span class='bar-pct'>{pct_str}</span></div>"
                f"<div class='bar-track'><div class='bar-fill' style='width:{min(max(pct_value,0),100)}%; background:{color};'></div></div>"
                f"</div>"
            )
        parts.append("</div>")
    parts.append("</div>")
    return ''.join(parts)


def refresh_data():
    st.cache_data.clear()
    st.rerun()


try:
    resumen_df = load_resumen()
    total_porras = count_entries(resumen_df)
    chart_html = render_level_selection_chart(resumen_df)
    similarity_html = render_similarity_block(analyze_similarity(resumen_df))
except Exception:
    total_porras = 0
    chart_html = ""
    similarity_html = ""

style = f"""
<style>
.stApp {{ background: linear-gradient(180deg, #ffffff 0%, {C_BG} 42%, #edf4f6 100%); }}
.block-container {{ max-width: 1180px; padding-top: 1.1rem; padding-bottom: 2rem; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.hero {{ background: linear-gradient(135deg, {C_PRIMARY_DARK} 0%, {C_PRIMARY} 55%, {C_PRIMARY_LIGHT} 100%); border-radius: 30px; padding: 1.65rem 1.8rem 1.55rem; box-shadow: 0 22px 44px rgba(0,74,95,.22); color: white; position: relative; overflow: hidden; text-align: center; }}
.hero::before {{ content:""; position:absolute; width:260px; height:260px; right:-60px; top:-65px; background:radial-gradient(circle, rgba(255,255,255,.22) 0%, rgba(255,255,255,0) 70%); }}
.hero::after {{ content:""; position:absolute; width:220px; height:220px; left:-30px; bottom:-70px; background:radial-gradient(circle, rgba(241,200,49,.30) 0%, rgba(241,200,49,0) 72%); }}
.hero-title-line1 {{ font-size:2.1rem; line-height:1.05; font-weight:900; margin-top:.2rem; position:relative; z-index:2; }}
.hero-title-line2 {{ font-size:2.55rem; line-height:1.02; font-weight:900; margin-top:.15rem; position:relative; z-index:2; }}
.card {{ background:white; border:1px solid rgba(50,125,142,.14); border-radius:22px; padding:1rem 1rem .95rem; box-shadow:0 10px 24px rgba(0,0,0,.05); height:100%; }}
.card-text {{ color:{C_GRAY_DARK}; font-size:.98rem; line-height:1.52; font-weight:600; }}
.section-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.24rem; margin:1.15rem 0 .55rem; }}
.callout {{ margin-top:1rem; background:linear-gradient(135deg, rgba(242,142,0,.98) 0%, rgba(241,200,49,.98) 100%); border-radius:22px; padding:1rem 1.1rem; color:#fff; box-shadow:0 16px 34px rgba(204,97,0,.22); }}
.callout-title {{ font-weight:900; font-size:1.15rem; margin-bottom:.15rem; }}
.callout-text {{ font-weight:700; font-size:.97rem; line-height:1.45; }}
.analysis-box {{ background:white; border:1px solid rgba(50,125,142,.14); border-radius:24px; padding:1rem 1rem .9rem; box-shadow:0 10px 24px rgba(0,0,0,.05); }}
.affinity-summary {{ color:{C_GRAY_DARK}; font-size:.96rem; line-height:1.5; font-weight:600; margin-bottom:.85rem; }}
.affinity-stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:.75rem; margin-bottom:.9rem; }}
.affinity-stat {{ background:rgba(50,125,142,.05); border:1px solid rgba(50,125,142,.10); border-radius:18px; padding:.8rem .9rem; text-align:center; }}
.affinity-stat-value {{ color:{C_SECONDARY_DARK}; font-size:1.6rem; font-weight:900; line-height:1; }}
.affinity-stat-label {{ color:{C_PRIMARY_DARK}; font-size:.88rem; font-weight:800; margin-top:.28rem; line-height:1.25; }}
.affinity-grid {{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:.9rem; }}
.affinity-card {{ background:white; border:1px solid rgba(50,125,142,.14); border-radius:18px; padding:.9rem 1rem; box-shadow:0 8px 18px rgba(0,0,0,.04); }}
.affinity-card-title {{ color:{C_PRIMARY_DARK}; font-size:1rem; font-weight:900; margin-bottom:.45rem; }}
.affinity-item {{ color:{C_GRAY_DARK}; font-size:.92rem; line-height:1.45; font-weight:600; margin-bottom:.55rem; }}
.affinity-item:last-child {{ margin-bottom:0; }}
.affinity-muted {{ color:{C_GRAY}; }}
.levels-grid {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:1rem; margin-top:.25rem; }}
.level-card {{ background:white; border:1px solid rgba(50,125,142,.14); border-radius:20px; padding:1rem; box-shadow:0 8px 18px rgba(0,0,0,.04); }}
.level-card-title {{ margin-bottom:.6rem; line-height:1.25; }}
.level-name {{ font-weight:900; font-size:1rem; }}
.level-teams {{ font-weight:700; font-size:.84rem; color:#706F6F; margin-top:.18rem; line-height:1.35; }}
.bar-row {{ margin-bottom:.58rem; }}
.bar-top {{ display:flex; justify-content:space-between; gap:.75rem; align-items:center; margin-bottom:.18rem; }}
.bar-team {{ color:{C_GRAY_DARK}; font-size:.9rem; font-weight:700; overflow-wrap:anywhere; }}
.bar-pct {{ color:{C_PRIMARY_DARK}; font-size:.88rem; font-weight:900; white-space:nowrap; }}
.bar-track {{ width:100%; height:12px; background:rgba(50,125,142,.09); border-radius:999px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:999px; }}
.footer-note {{ margin-top:.9rem; color:{C_GRAY}; text-align:center; font-size:.88rem; font-weight:700; }}
.refresh-wrap {{ display:flex; justify-content:center; margin-top:1.2rem; }}
.stButton > button {{ background:{C_PRIMARY_DARK}; color:white; border:none; border-radius:999px; padding:.6rem 1.2rem; font-weight:800; }}
.stButton > button:hover {{ background:{C_PRIMARY}; color:white; }}
@media (max-width: 980px) {{ .hero-title-line1 {{ font-size:1.8rem; }} .hero-title-line2 {{ font-size:2.15rem; }} .levels-grid, .affinity-grid {{ grid-template-columns:1fr; }} .affinity-stats {{ grid-template-columns:1fr; }} }}
@media (max-width: 640px) {{ .hero-title-line1 {{ font-size:1.45rem; }} .hero-title-line2 {{ font-size:1.8rem; }} }}
</style>
"""
st.markdown(style, unsafe_allow_html=True)

st.markdown("""
<div class='hero'>
  <div class='hero-title-line1'>Versia Servicios Distribuidos</div>
  <div class='hero-title-line2'>Porra Mundial 2026</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class='card' style='margin-top:1rem;'>
  <div class='card-text'>La inscripción ya se ha cerrado. Con <b>{total_porras} porras registradas</b>, ahora toca comparar pronósticos, descubrir coincidencias y ver quién se la ha jugado de verdad en esta edición.</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='callout'>
  <div class='callout-title'>Empieza la comparativa de porras</div>
  <div class='callout-text'>Se acabó el tiempo de apuntarse. Ahora llega la parte divertida: comparar apuestas, detectar duplas sospechosamente parecidas y empezar con el pique sano antes de que ruede el balón.</div>
</div>
""", unsafe_allow_html=True)

if similarity_html:
    st.markdown(similarity_html, unsafe_allow_html=True)

st.markdown("<div class='section-title'>Radiografía de las apuestas realizadas</div>", unsafe_allow_html=True)
if chart_html:
    st.markdown(chart_html, unsafe_allow_html=True)
else:
    st.info("Todavía no hay datos suficientes para generar el resumen de porcentajes por nivel.")

st.markdown("<div class='refresh-wrap'></div>", unsafe_allow_html=True)
if st.button("Actualizar"):
    refresh_data()
