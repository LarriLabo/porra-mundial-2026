
import io
import re
import urllib.request
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Bienvenid@s · Porra Mundial 2026", page_icon="🌍", layout="wide")

SOURCE_URL = "https://docs.google.com/spreadsheets/d/1q4SpZQb7_7UrX-NtReo2XS7jBMvHH0xI/edit?usp=drivesdk&ouid=105950533705571221592&rtpof=true&sd=true"
CACHE_MINUTES = 5
PRICE_PER_ENTRY = 10

C_PRIMARY_DARK = "#004A5F"
C_PRIMARY = "#327D8E"
C_PRIMARY_LIGHT = "#64AEBC"
C_SECONDARY_DARK = "#CC6100"
C_SECONDARY = "#F28E00"
C_SECONDARY_LIGHT = "#F1C831"
C_GRAY_DARK = "#383737"
C_GRAY = "#706F6F"
C_BG = "#F4F8F9"


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
def count_entries() -> int:
    url = make_download_url(SOURCE_URL)
    file_bytes = download_bytes(url)
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Resumen de Apuestas', engine='openpyxl')
    if 'PARTICIPANTE' not in df.columns:
        return 0
    return int(df['PARTICIPANTE'].dropna().shape[0])


try:
    total_porras = count_entries()
except Exception:
    total_porras = 0

recaudacion = total_porras * PRICE_PER_ENTRY

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
.section-wrap {{ margin-top: 1.15rem; }}
.card {{ background:white; border:1px solid rgba(50,125,142,.14); border-radius:22px; padding:1rem 1rem .95rem; box-shadow:0 10px 24px rgba(0,0,0,.05); height:100%; }}
.card-highlight {{ background: linear-gradient(180deg, rgba(242,142,0,.12) 0%, rgba(255,255,255,1) 50%); border:1px solid rgba(242,142,0,.22); }}
.card-icon {{ font-size:1.55rem; margin-bottom:.18rem; }}
.card-title {{ color:{C_PRIMARY_DARK}; font-size:1.02rem; font-weight:900; margin-bottom:.2rem; }}
.card-text {{ color:{C_GRAY_DARK}; font-size:.95rem; line-height:1.42; font-weight:600; }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:.85rem; margin-top: .25rem; }}
.kpi {{ background:white; border-radius:18px; border:1px solid rgba(50,125,142,.13); padding:.85rem .95rem; box-shadow:0 8px 18px rgba(0,0,0,.04); text-align:center; }}
.kpi-value {{ color:{C_SECONDARY_DARK}; font-size:1.95rem; font-weight:900; line-height:1; }}
.kpi-label {{ color:{C_PRIMARY_DARK}; font-size:.92rem; font-weight:800; margin-top:.35rem; }}
.callout {{ margin-top: 1rem; background: linear-gradient(135deg, rgba(242,142,0,.98) 0%, rgba(241,200,49,.98) 100%); border-radius:22px; padding: 1rem 1.1rem; color:#fff; box-shadow:0 16px 34px rgba(204,97,0,.22); }}
.callout-title {{ font-weight:900; font-size:1.15rem; margin-bottom:.15rem; }}
.callout-text {{ font-weight:700; font-size:.97rem; line-height:1.45; }}
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
<div class='footer-note'>Buen rollo, alguna pulla elegante y mucho fútbol: ese es el espíritu.</div>
""", unsafe_allow_html=True)
