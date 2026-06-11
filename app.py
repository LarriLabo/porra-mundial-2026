
import io
import re
import math
import urllib.request
from collections import Counter

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Bienvenid@s · Porra Mundial 2026", page_icon="🌍", layout="wide")

SOURCE_URL = "https://docs.google.com/spreadsheets/d/1q4SpZQb7_7UrX-NtReo2XS7jBMvHH0xI/edit?usp=drivesdk&ouid=105950533705571221592&rtpof=true&sd=true"
CACHE_MINUTES = 5
PRICE_PER_ENTRY = 10
TOP_TEAMS_PER_LEVEL = 5

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
    return [c for c in df.columns if str(c).strip().lower().startswith('nivel')]


def count_entries(df: pd.DataFrame) -> int:
    if 'PARTICIPANTE' not in df.columns:
        return 0
    return int(df['PARTICIPANTE'].dropna().shape[0])


def build_level_selection_chart(df: pd.DataFrame) -> bytes | None:
    levels = get_levels(df)
    if not levels:
        return None

    total = max(count_entries(df), 1)
    n_levels = len(levels)
    ncols = 2 if n_levels > 1 else 1
    nrows = math.ceil(n_levels / ncols)

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(14, 3.8 * nrows))
    if not isinstance(axes, (list, tuple)):
        try:
            axes = axes.flatten()
        except Exception:
            axes = [axes]
    else:
        axes = list(axes)

    if hasattr(axes, 'flatten'):
        axes = list(axes.flatten())

    for idx, level in enumerate(levels):
        ax = axes[idx]
        series = df[level].dropna().astype(str).str.strip()
        if series.empty:
            ax.axis('off')
            continue

        percentages = (series.value_counts(normalize=True) * 100).round(1).head(TOP_TEAMS_PER_LEVEL)
        labels = list(percentages.index)[::-1]
        values = list(percentages.values)[::-1]
        color = LEVEL_COLORS.get(str(level), C_PRIMARY_DARK)

        ax.barh(labels, values, color=color, alpha=0.95)
        ax.set_xlim(0, max(values) * 1.18 if values else 100)
        ax.set_title(str(level), fontsize=12, fontweight='bold', color=C_PRIMARY_DARK)
        ax.set_xlabel('% de porras', fontsize=10, color=C_GRAY_DARK)
        ax.tick_params(axis='y', labelsize=9)
        ax.tick_params(axis='x', labelsize=8)
        ax.grid(axis='x', linestyle='--', alpha=0.22)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_alpha(0.15)

        for y, val in enumerate(values):
            ax.text(val + (max(values) * 0.02), y, f"{val:.1f}%", va='center', ha='left', fontsize=9, color=C_GRAY_DARK, fontweight='bold')

    for extra_ax in axes[n_levels:]:
        extra_ax.axis('off')

    fig.suptitle('Equipos más seleccionados por nivel', fontsize=16, fontweight='bold', color=C_PRIMARY_DARK, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.97])

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=180, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def find_duplicate_bets(df: pd.DataFrame):
    if 'PARTICIPANTE' not in df.columns:
        return []
    levels = get_levels(df)
    if not levels:
        return []

    work = df.dropna(subset=['PARTICIPANTE']).copy()
    for level in levels:
        work[level] = work[level].fillna('').astype(str).str.strip()
    work['PARTICIPANTE'] = work['PARTICIPANTE'].astype(str).str.strip()
    work['combo_key'] = work[levels].agg(' || '.join, axis=1)

    duplicates = []
    for _, group in work.groupby('combo_key'):
        if len(group) > 1:
            teams = [t for t in group.iloc[0][levels].tolist() if str(t).strip()]
            duplicates.append({
                'participantes': group['PARTICIPANTE'].tolist(),
                'equipos': teams,
                'repeticiones': int(len(group))
            })
    duplicates.sort(key=lambda x: (-x['repeticiones'], ', '.join(x['participantes'])))
    return duplicates


try:
    resumen_df = load_resumen()
    total_porras = count_entries(resumen_df)
    recaudacion = total_porras * PRICE_PER_ENTRY
    chart_png = build_level_selection_chart(resumen_df)
    duplicate_bets = find_duplicate_bets(resumen_df)
except Exception:
    resumen_df = pd.DataFrame()
    total_porras = 0
    recaudacion = 0
    chart_png = None
    duplicate_bets = []

style = f"""
<style>
.stApp {{ background: linear-gradient(180deg, #ffffff 0%, {C_BG} 42%, #edf4f6 100%); }}
.block-container {{ max-width: 1180px; padding-top: 1.1rem; padding-bottom: 2rem; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.hero {{
  background: linear-gradient(135deg, {C_PRIMARY_DARK} 0%, {C_PRIMARY} 55%, {C_PRIMARY_LIGHT} 100%);
  border-radius: 30px;
  padding: 1.65rem 1.8rem 1.55rem;
  box-shadow: 0 22px 44px rgba(0,74,95,.22);
  color: white;
  position: relative;
  overflow: hidden;
}}
.hero::before {{
  content: "";
  position: absolute;
  width: 260px; height: 260px;
  right: -60px; top: -65px;
  background: radial-gradient(circle, rgba(255,255,255,.22) 0%, rgba(255,255,255,0) 70%);
}}
.hero::after {{
  content: "";
  position: absolute;
  width: 220px; height: 220px;
  left: -30px; bottom: -70px;
  background: radial-gradient(circle, rgba(241,200,49,.30) 0%, rgba(241,200,49,0) 72%);
}}
.hero-top {{ font-size: .96rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; opacity: .96; }}
.hero-title {{ font-size: 2.75rem; line-height: 1.03; font-weight: 900; margin-top: .45rem; margin-bottom: .45rem; }}
.hero-sub {{ font-size: 1.08rem; line-height: 1.48; font-weight: 700; max-width: 820px; opacity: .98; }}
.badge-row {{ display:flex; flex-wrap:wrap; gap:.65rem; margin-top: 1rem; }}
.badge {{ background: rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.18); color:#fff; padding:.5rem .8rem; border-radius:999px; font-weight:800; font-size:.92rem; backdrop-filter: blur(2px); }}
.card {{ background:white; border:1px solid rgba(50,125,142,.14); border-radius:22px; padding:1rem 1rem .95rem; box-shadow:0 10px 24px rgba(0,0,0,.05); height:100%; }}
.card-highlight {{ background: linear-gradient(180deg, rgba(242,142,0,.12) 0%, rgba(255,255,255,1) 50%); border:1px solid rgba(242,142,0,.22); }}
.card-icon {{ font-size:1.55rem; margin-bottom:.18rem; }}
.card-title {{ color:{C_PRIMARY_DARK}; font-size:1.02rem; font-weight:900; margin-bottom:.2rem; }}
.card-text {{ color:{C_GRAY_DARK}; font-size:.95rem; line-height:1.42; font-weight:600; }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:.85rem; margin-top: 1rem; }}
.kpi {{ background:white; border-radius:18px; border:1px solid rgba(50,125,142,.13); padding:.85rem .95rem; box-shadow:0 8px 18px rgba(0,0,0,.04); text-align:center; }}
.kpi-value {{ color:{C_SECONDARY_DARK}; font-size:1.95rem; font-weight:900; line-height:1; }}
.kpi-label {{ color:{C_PRIMARY_DARK}; font-size:.92rem; font-weight:800; margin-top:.35rem; }}
.section-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.24rem; margin:1.15rem 0 .55rem; }}
.analysis-box {{ background:white; border:1px solid rgba(50,125,142,.14); border-radius:24px; padding:1rem 1rem .9rem; box-shadow:0 10px 24px rgba(0,0,0,.05); }}
.analysis-note {{ color:{C_GRAY_DARK}; font-size:.95rem; line-height:1.45; font-weight:600; margin-bottom:.75rem; }}
.callout {{ margin-top: 1rem; background: linear-gradient(135deg, rgba(242,142,0,.98) 0%, rgba(241,200,49,.98) 100%); border-radius:22px; padding: 1rem 1.1rem; color:#fff; box-shadow:0 16px 34px rgba(204,97,0,.22); }}
.callout-title {{ font-weight:900; font-size:1.15rem; margin-bottom:.15rem; }}
.callout-text {{ font-weight:700; font-size:.97rem; line-height:1.45; }}
.dup-card {{ background:white; border:1px solid rgba(50,125,142,.14); border-left:6px solid {C_SECONDARY}; border-radius:18px; padding:.9rem 1rem; box-shadow:0 8px 18px rgba(0,0,0,.04); margin-bottom:.7rem; }}
.dup-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1rem; margin-bottom:.18rem; }}
.dup-text {{ color:{C_GRAY_DARK}; font-size:.93rem; line-height:1.42; font-weight:600; }}
.footer-note {{ margin-top: .9rem; color:{C_GRAY}; text-align:center; font-size:.88rem; font-weight:700; }}
@media (max-width: 980px) {{
  .hero-title {{ font-size: 2.2rem; }}
  .kpi-grid {{ grid-template-columns:repeat(2, 1fr); }}
}}
@media (max-width: 640px) {{
  .hero-title {{ font-size: 1.9rem; }}
  .hero-sub {{ font-size: .98rem; }}
  .kpi-grid {{ grid-template-columns:1fr 1fr; gap:.65rem; }}
}}
</style>
"""
st.markdown(style, unsafe_allow_html=True)

st.markdown(f"""
<div class='hero'>
  <div class='hero-top'>Bienvenid@s</div>
  <div class='hero-title'>Porra Mundial 2026 · Recaudación actual: {recaudacion} €</div>
  <div class='hero-sub'>¡Arranca la cuenta atrás para el Mundial más gigante, divertido y glorioso de todos! ⚽🌍 Aquí se viene emoción, piques sanos, pronósticos imposibles y alguna que otra aparición repentina del clásico “yo eso ya lo sabía”. De momento, el balón está en el punto de penalti… y <b>ya van {total_porras} porras apuntadas</b>. Si todavía falta alguien por subirse al carro, este es el momento de entrar en el juego y no quedarse viendo el torneo desde la grada.</div>
  <div class='badge-row'>
    <div class='badge'>⚽ Mundial 2026</div>
    <div class='badge'>🌎 Canadá · México · USA</div>
    <div class='badge'>🔥 {total_porras} porras realizadas</div>
    <div class='badge'>💰 {recaudacion} € en premios</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class='kpi-grid'>
  <div class='kpi'><div class='kpi-value'>48</div><div class='kpi-label'>Selecciones</div></div>
  <div class='kpi'><div class='kpi-value'>104</div><div class='kpi-label'>Partidos</div></div>
  <div class='kpi'><div class='kpi-value'>3</div><div class='kpi-label'>Países anfitriones</div></div>
  <div class='kpi'><div class='kpi-value'>{total_porras}</div><div class='kpi-label'>Porras realizadas</div></div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    <div class='card card-highlight'>
      <div class='card-icon'>🌎</div>
      <div class='card-title'>Tres países, un solo fiestón</div>
      <div class='card-text'>Canadá, México y Estados Unidos comparten escenario en una edición histórica, gigantesca y con aroma a Mundial inolvidable.</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class='card'>
      <div class='card-icon'>📅</div>
      <div class='card-title'>Un verano para la historia</div>
      <div class='card-text'>48 selecciones, 104 partidos y un calendario cargado de noches épicas, sorpresas, alegrías y mucho “te lo dije”.</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class='card'>
      <div class='card-icon'>📝</div>
      <div class='card-title'>Todavía hay sitio en la porra</div>
      <div class='card-text'>Ya hay <b>{total_porras}</b> porras registradas. Si alguien falta por apuntarse, que no se despiste: luego llegan los goles, los aciertos... y las lamentaciones.</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class='callout'>
  <div class='callout-title'>Que empiece el juego y el movimiento de gallinas</div>
  <div class='callout-text'>Aquí no hay Champions del Excel, PowerBi ni gurús invencibles: hay compis con fe ciega, pronósticos valientes y mucho comentario de pasillo. Lo bonito será vacilar con cariño, celebrar los aciertos improbables y sobrevivir con dignidad cuando falle el “favoritísimo”. Y aviso a navegantes: la IA podrá calcular mucho… pero no siempre gana. A veces el instinto del café (soluble) de media mañana también juega su partido.</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='section-title'>Radiografía de las apuestas realizadas</div>", unsafe_allow_html=True)
st.markdown("<div class='analysis-box'><div class='analysis-note'>Para quien todavía se lo está pensando: aquí va una foto rápida de por dónde van las apuestas. El gráfico muestra el porcentaje de porras que llevan a los equipos más repetidos en cada nivel, para que se vea dónde está el rebaño… y dónde puede haber hueco para una predicción valiente.</div></div>", unsafe_allow_html=True)
if chart_png:
    st.image(chart_png, use_container_width=True)
else:
    st.info("Todavía no hay datos suficientes para generar el gráfico de selecciones por nivel.")

st.markdown("<div class='section-title'>¿Hay apuestas idénticas?</div>", unsafe_allow_html=True)
if duplicate_bets:
    st.markdown(f"<div class='analysis-box'><div class='analysis-note'>Sí, ya hay <b>{len(duplicate_bets)}</b> combinación(es) de equipos repetida(s). Vamos, que algunas mentes futboleras ya están pensando exactamente igual. Esto también da pistas interesantes sobre qué selecciones se están poniendo de moda.</div></div>", unsafe_allow_html=True)
    for dup in duplicate_bets:
        participantes = ', '.join(dup['participantes'])
        equipos = ' · '.join(dup['equipos']) if dup['equipos'] else 'Sin equipos detectados'
        st.markdown(f"<div class='dup-card'><div class='dup-title'>{dup['repeticiones']} apuestas iguales</div><div class='dup-text'><b>Participantes:</b> {participantes}<br><b>Selecciones compartidas:</b> {equipos}</div></div>", unsafe_allow_html=True)
else:
    st.markdown("<div class='analysis-box'><div class='analysis-note'>De momento, no hay apuestas idénticas en la selección completa de equipos. Cada persona está tirando por su propio camino… al menos por ahora.</div></div>", unsafe_allow_html=True)

st.markdown("<div class='footer-note'>Buen rollo, alguna pulla elegante y mucho fútbol: ese es el espíritu.</div>", unsafe_allow_html=True)
