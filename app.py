
import streamlit as st

st.set_page_config(page_title="Bienvenid@s · Porra Mundial 2026", page_icon="🌍", layout="wide")

C_PRIMARY_DARK = "#004A5F"
C_PRIMARY = "#327D8E"
C_PRIMARY_LIGHT = "#64AEBC"
C_SECONDARY_DARK = "#CC6100"
C_SECONDARY = "#F28E00"
C_SECONDARY_LIGHT = "#F1C831"
C_GRAY_DARK = "#383737"
C_GRAY = "#706F6F"
C_BG = "#F4F8F9"

style = f"""
<style>
.stApp {{ background: linear-gradient(180deg, #ffffff 0%, {C_BG} 42%, #edf4f6 100%); }}
.block-container {{ max-width: 1180px; padding-top: 1.1rem; padding-bottom: 2rem; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.hero {{
  background: linear-gradient(135deg, {C_PRIMARY_DARK} 0%, {C_PRIMARY} 55%, {C_PRIMARY_LIGHT} 100%);
  border-radius: 30px;
  padding: 1.6rem 1.8rem 1.5rem;
  box-shadow: 0 22px 44px rgba(0,74,95,.22);
  color: white;
  position: relative;
  overflow: hidden;
}}
.hero::before {{
  content: "";
  position: absolute;
  width: 220px; height: 220px;
  right: -45px; top: -55px;
  background: radial-gradient(circle, rgba(255,255,255,.22) 0%, rgba(255,255,255,0) 70%);
}}
.hero::after {{
  content: "";
  position: absolute;
  width: 180px; height: 180px;
  left: -25px; bottom: -55px;
  background: radial-gradient(circle, rgba(241,200,49,.25) 0%, rgba(241,200,49,0) 72%);
}}
.hero-top {{ font-size: .96rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; opacity: .96; }}
.hero-title {{ font-size: 2.6rem; line-height: 1.05; font-weight: 900; margin-top: .45rem; margin-bottom: .35rem; }}
.hero-sub {{ font-size: 1.05rem; line-height: 1.45; font-weight: 600; max-width: 780px; opacity: .98; }}
.badge-row {{ display:flex; flex-wrap:wrap; gap:.65rem; margin-top: 1rem; }}
.badge {{ background: rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.18); color:#fff; padding:.5rem .8rem; border-radius:999px; font-weight:800; font-size:.92rem; backdrop-filter: blur(2px); }}
.section-wrap {{ margin-top: 1.15rem; }}
.section-title {{ color:{C_PRIMARY_DARK}; font-weight:900; font-size:1.2rem; margin-bottom:.55rem; }}
.card {{ background:white; border:1px solid rgba(50,125,142,.14); border-radius:22px; padding:1rem 1rem .95rem; box-shadow:0 10px 24px rgba(0,0,0,.05); height:100%; }}
.card-highlight {{ background: linear-gradient(180deg, rgba(242,142,0,.12) 0%, rgba(255,255,255,1) 50%); border:1px solid rgba(242,142,0,.22); }}
.card-icon {{ font-size:1.55rem; margin-bottom:.18rem; }}
.card-title {{ color:{C_PRIMARY_DARK}; font-size:1.02rem; font-weight:900; margin-bottom:.2rem; }}
.card-text {{ color:{C_GRAY_DARK}; font-size:.95rem; line-height:1.4; font-weight:600; }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:.85rem; margin-top: .25rem; }}
.kpi {{ background:white; border-radius:18px; border:1px solid rgba(50,125,142,.13); padding:.85rem .95rem; box-shadow:0 8px 18px rgba(0,0,0,.04); text-align:center; }}
.kpi-value {{ color:{C_SECONDARY_DARK}; font-size:1.95rem; font-weight:900; line-height:1; }}
.kpi-label {{ color:{C_PRIMARY_DARK}; font-size:.92rem; font-weight:800; margin-top:.35rem; }}
.callout {{ margin-top: 1rem; background: linear-gradient(135deg, rgba(242,142,0,.98) 0%, rgba(241,200,49,.98) 100%); border-radius:22px; padding: 1rem 1.1rem; color:#fff; box-shadow:0 16px 34px rgba(204,97,0,.22); }}
.callout-title {{ font-weight:900; font-size:1.15rem; margin-bottom:.15rem; }}
.callout-text {{ font-weight:700; font-size:.97rem; line-height:1.45; }}
.footer-note {{ margin-top: .9rem; color:{C_GRAY}; text-align:center; font-size:.88rem; font-weight:700; }}
@media (max-width: 980px) {{
  .hero-title {{ font-size: 2.15rem; }}
  .kpi-grid {{ grid-template-columns:repeat(2, 1fr); }}
}}
@media (max-width: 640px) {{
  .hero-title {{ font-size: 1.8rem; }}
  .hero-sub {{ font-size: .98rem; }}
  .kpi-grid {{ grid-template-columns:1fr 1fr; gap:.65rem; }}
}}
</style>
"""
st.markdown(style, unsafe_allow_html=True)

st.markdown("""
<div class='hero'>
  <div class='hero-top'>Bienvenid@s</div>
  <div class='hero-title'>Porra Mundial 2026</div>
  <div class='hero-sub'>La cuenta atrás ha comenzado. Muy pronto arrancará la porra con la clasificación oficial, el podium, los premios y todos los puntos por nivel. Mientras tanto, aquí tienes una portada de bienvenida con la esencia del Mundial 2026.</div>
  <div class='badge-row'>
    <div class='badge'>⚽ Mundial 2026</div>
    <div class='badge'>🌎 Canadá · México · USA</div>
    <div class='badge'>🏆 La porra arranca pronto</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='section-wrap'><div class='section-title'>Infograma del Mundial</div></div>", unsafe_allow_html=True)

st.markdown("""
<div class='kpi-grid'>
  <div class='kpi'><div class='kpi-value'>48</div><div class='kpi-label'>Selecciones</div></div>
  <div class='kpi'><div class='kpi-value'>104</div><div class='kpi-label'>Partidos</div></div>
  <div class='kpi'><div class='kpi-value'>3</div><div class='kpi-label'>Países anfitriones</div></div>
  <div class='kpi'><div class='kpi-value'>19 Jul</div><div class='kpi-label'>Gran final</div></div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    <div class='card card-highlight'>
      <div class='card-icon'>🌎</div>
      <div class='card-title'>Tres países, un solo Mundial</div>
      <div class='card-text'>El torneo se celebra en Canadá, México y Estados Unidos, convirtiéndose en una edición histórica por su dimensión continental.</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class='card'>
      <div class='card-icon'>📅</div>
      <div class='card-title'>Fechas clave</div>
      <div class='card-text'>La competición arranca el 11 de junio y culmina el 19 de julio, con varias semanas de emoción, grupos y eliminatorias.</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div class='card'>
      <div class='card-icon'>✨</div>
      <div class='card-title'>La porra está calentando</div>
      <div class='card-text'>En cuanto empiece oficialmente la porra, esta portada se sustituirá por la versión completa con ranking, podium, premios y detalle de selecciones.</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class='callout'>
  <div class='callout-title'>¡Bienvenid@s a la competición!</div>
  <div class='callout-text'>Gracias por participar. Muy pronto estará disponible la versión completa de la porra con toda la información en tiempo real. Hasta entonces, disfruta de esta portada especial del Mundial 2026.</div>
</div>
<div class='footer-note'>Cuando empiece la porra, solo tendrás que sustituir este <b>app.py</b> por la versión final.</div>
""", unsafe_allow_html=True)
