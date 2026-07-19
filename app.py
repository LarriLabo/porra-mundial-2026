import streamlit as st
import pandas as pd
import re
import unicodedata
from io import BytesIO
from urllib.request import Request, urlopen
from html import escape as html_escape

st.set_page_config(page_title="Final Porra Mundial 2026", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1q4SpZQb7_7UrX-NtReo2XS7jBMvHH0xI/edit?usp=sharing"
WINNER = "España"
CHAMPION_BONUS = 35
PRICE_PER_ENTRY = 10

LEVEL_COLS = [f"Nivel {i}" for i in range(1, 9)]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;700;800;900&display=swap');
html, body, [class*="css"] { font-family:'Montserrat', sans-serif; }
.stApp { background: radial-gradient(circle at top left, rgba(100,174,188,.18), transparent 32%), #EEF7F8; color:#383737; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.4rem; max-width: 1280px; }
.hero { position:relative; overflow:hidden; border-radius:32px; padding:1.7rem 1.4rem; color:white; text-align:center; box-shadow:0 24px 48px rgba(0,74,95,.20); background:linear-gradient(135deg,#64AEBC 0%,#327D8E 25%,#004A5F 52%,#327D8E 78%,#64AEBC 100%); }
.hero-logo-row { display:grid; grid-template-columns:120px 1fr 120px; gap:1rem; align-items:center; }
.logo-avatar { width:95px; height:95px; border-radius:24px; background:rgba(255,255,255,.92); margin:auto; box-shadow:0 12px 26px rgba(0,74,95,.20); display:flex; align-items:center; justify-content:center; font-weight:1000; color:#004A5F; font-size:1.15rem; }
.hero-title-1 { font-size:clamp(1.35rem, 2.4vw, 2.35rem); font-weight:1000; letter-spacing:.01em; line-height:1.02; }
.hero-title-2 { margin-top:.3rem; font-size:clamp(2.0rem, 4.8vw, 4.2rem); font-weight:1000; line-height:.98; }
.hero-kicker { display:inline-flex; align-items:center; gap:.45rem; margin-top:1rem; background:rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.25); padding:.55rem .9rem; border-radius:999px; font-weight:900; }
.final-banner { margin-top:1rem; background:white; border:1px solid rgba(100,174,188,.28); border-radius:26px; padding:1rem 1.15rem; box-shadow:0 12px 28px rgba(0,74,95,.08); }
.section-title { color:#004A5F; font-size:1.55rem; font-weight:1000; margin:1.65rem 0 .75rem; }
.section-subtitle { color:#706F6F; margin-top:-.45rem; margin-bottom:.8rem; font-weight:700; }
.metric-grid { display:grid; grid-template-columns:repeat(4, 1fr); gap:.9rem; margin-top:1rem; }
.metric-card { background:white; border:1px solid rgba(100,174,188,.28); border-radius:22px; padding:1rem; box-shadow:0 12px 24px rgba(0,74,95,.07); }
.metric-label { color:#706F6F; font-size:.78rem; font-weight:900; text-transform:uppercase; letter-spacing:.04em; }
.metric-value { color:#004A5F; font-size:1.55rem; font-weight:1000; margin-top:.25rem; }
.podium-wrap { background:white; border:1px solid rgba(100,174,188,.30); border-radius:30px; padding:1.2rem; box-shadow:0 18px 40px rgba(0,74,95,.10); }
.podium-grid { display:grid; grid-template-columns:1.05fr 1fr 1fr; gap:1rem; align-items:stretch; }
.podium-card { border-radius:26px; padding:1rem; min-height:210px; border:1px solid rgba(100,174,188,.28); background:linear-gradient(180deg,#fff,#f8fcfd); box-shadow:0 10px 24px rgba(0,74,95,.07); }
.podium-card.first { background:linear-gradient(180deg,#fff7d6,#fffdf3); border-color:#F1C831; transform:translateY(-8px); }
.podium-rank { display:inline-flex; align-items:center; justify-content:center; height:36px; min-width:36px; border-radius:999px; color:white; background:#004A5F; font-weight:1000; margin-bottom:.6rem; }
.podium-card.first .podium-rank { background:#F28E00; color:#004A5F; }
.podium-name { color:#004A5F; font-size:1.05rem; font-weight:1000; line-height:1.2; margin:.38rem 0; }
.podium-points { display:flex; align-items:center; gap:.45rem; flex-wrap:wrap; margin-top:.75rem; }
.point-pill { display:inline-flex; align-items:center; justify-content:center; border-radius:999px; padding:.25rem .55rem; font-weight:1000; color:white; background:#327D8E; font-size:.84rem; }
.prize-pill { background:#F28E00; color:white; }
.bonus-pill { background:#64AEBC; color:white; }
.rank-table { overflow:hidden; border-radius:24px; border:1px solid rgba(100,174,188,.30); box-shadow:0 14px 32px rgba(0,74,95,.08); background:white; }
.rank-head, .rank-row { display:grid; grid-template-columns:70px 1.8fr .75fr .75fr .75fr .75fr; align-items:center; gap:.5rem; }
.rank-head { background:#004A5F; color:white; font-size:.78rem; font-weight:1000; text-transform:uppercase; padding:.72rem .86rem; }
.rank-row { padding:.74rem .86rem; font-weight:850; color:#383737; }
.rank-row:nth-child(odd) { background:#f6fbfc; }
.rank-pos { color:#CC6100; font-weight:1000; }
.rank-total { color:#004A5F; font-weight:1000; }
.rank-prize { color:#F28E00; font-weight:1000; }
.participant-grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:.8rem; }
.participant-card { background:white; border:1px solid rgba(100,174,188,.28); border-radius:18px; padding:.85rem; box-shadow:0 8px 18px rgba(0,74,95,.06); }
.participant-card summary { cursor:pointer; color:#004A5F; font-weight:1000; list-style-position:outside; }
.participant-summary-line { display:inline-flex; width:calc(100% - 18px); align-items:center; justify-content:space-between; gap:.65rem; vertical-align:middle; }
.participant-total-pill { background:linear-gradient(135deg,#64AEBC,#327D8E); color:white; border-radius:999px; padding:.16rem .55rem; font-size:.78rem; font-weight:1000; flex:0 0 auto; }
.pick-grid { display:grid; grid-template-columns:repeat(2, 1fr); gap:.45rem; margin-top:.7rem; }
.pick-chip { display:flex; justify-content:space-between; gap:.45rem; align-items:center; background:#EEF7F8; border-radius:999px; padding:.35rem .55rem; color:#004A5F; font-weight:850; font-size:.72rem; }
.pick-chip b { color:#F28E00; }
@media (max-width: 980px) { .hero-logo-row { grid-template-columns:1fr; } .logo-avatar { display:none; } .metric-grid, .podium-grid, .participant-grid { grid-template-columns:1fr; } .rank-head, .rank-row { grid-template-columns:45px 1.4fr .55fr .55fr .55fr .65fr; font-size:.70rem; } }
</style>
""", unsafe_allow_html=True)

def esc(x):
    return html_escape(str(x))

def norm(x):
    s = "" if pd.isna(x) else str(x)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip().casefold()

def clean_col(x):
    return re.sub(r"\s+", " ", str(x)).strip()

def google_export_url(url):
    m = re.search(r"/spreadsheets/d/([^/]+)", url)
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx" if m else url

@st.cache_data(ttl=300, show_spinner=False)
def load_excel_bytes(url):
    req = Request(google_export_url(url), headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as resp:
        return resp.read()

def find_table(raw, required_cols):
    required_norm = [norm(c) for c in required_cols]
    for i in range(min(len(raw), 100)):
        row_vals = [norm(v) for v in raw.iloc[i].tolist()]
        if all(any(req == v or req in v for v in row_vals) for req in required_norm):
            header = [clean_col(v) for v in raw.iloc[i].tolist()]
            df = raw.iloc[i+1:].copy()
            df.columns = header
            df = df.loc[:, [c for c in df.columns if c and c.lower() != "nan"]]
            return df.dropna(how="all").reset_index(drop=True)
    raise ValueError(f"No he encontrado la tabla con columnas {required_cols}")

def first_existing_col(df, names):
    nmap = {norm(c): c for c in df.columns}
    for wanted in names:
        if norm(wanted) in nmap:
            return nmap[norm(wanted)]
    for c in df.columns:
        nc = norm(c)
        if any(norm(w) in nc for w in names):
            return c
    return None

@st.cache_data(ttl=300, show_spinner=True)
def load_data(url):
    data = load_excel_bytes(url)
    xls = pd.ExcelFile(BytesIO(data), engine="openpyxl")
    apuestas_raw = pd.read_excel(xls, sheet_name="Resumen de Apuestas", header=None)
    apuestas = find_table(apuestas_raw, ["PARTICIPANTE", "Nivel 1", "Nivel 8"])
    part_col = first_existing_col(apuestas, ["PARTICIPANTE"])
    apuestas = apuestas.rename(columns={part_col: "PARTICIPANTE"})
    level_cols = []
    for target in LEVEL_COLS:
        col = first_existing_col(apuestas, [target])
        if col:
            apuestas = apuestas.rename(columns={col: target})
            level_cols.append(target)
    apuestas = apuestas[["PARTICIPANTE"] + level_cols].copy()
    apuestas["PARTICIPANTE"] = apuestas["PARTICIPANTE"].astype(str).str.strip()
    apuestas = apuestas[apuestas["PARTICIPANTE"].ne("") & apuestas["PARTICIPANTE"].str.lower().ne("nan")].reset_index(drop=True)

    puntos_raw = pd.read_excel(xls, sheet_name="Puntos", header=None)
    puntos_tbl = find_table(puntos_raw, ["PARTICIPANTE"])
    p_col = first_existing_col(puntos_tbl, ["PARTICIPANTE"])
    total_col = first_existing_col(puntos_tbl, ["PUNTOS_TOTALES", "PUNTOS TOTALES", "TOTAL", "PUNTOS"])
    if total_col is None:
        candidates = [c for c in puntos_tbl.columns if c != p_col]
        total_col = max(candidates, key=lambda c: pd.to_numeric(puntos_tbl[c], errors="coerce").notna().sum())
    ranking = puntos_tbl[[p_col, total_col]].copy()
    ranking.columns = ["PARTICIPANTE", "PUNTOS_TOTALES"]
    ranking["PARTICIPANTE"] = ranking["PARTICIPANTE"].astype(str).str.strip()
    ranking["PUNTOS_TOTALES"] = pd.to_numeric(ranking["PUNTOS_TOTALES"], errors="coerce")
    ranking = ranking.dropna(subset=["PUNTOS_TOTALES"])
    ranking = ranking[ranking["PARTICIPANTE"].ne("") & ranking["PARTICIPANTE"].str.lower().ne("nan")]
    ranking["PUNTOS_TOTALES"] = ranking["PUNTOS_TOTALES"].astype(int)

    team_points = {}
    try:
        team_tbl = find_table(puntos_raw, ["Equipo"])
        eq_col = first_existing_col(team_tbl, ["Equipo", "Selección", "PAIS"])
        tot_col = first_existing_col(team_tbl, ["TOTAL", "PUNTOS", "Puntos"])
        if eq_col and tot_col:
            tmp = team_tbl[[eq_col, tot_col]].copy()
            tmp[tot_col] = pd.to_numeric(tmp[tot_col], errors="coerce")
            for _, r in tmp.dropna(subset=[tot_col]).iterrows():
                team_points[norm(r[eq_col])] = int(r[tot_col])
    except Exception:
        pass
    return apuestas, ranking, level_cols, team_points

def dense_rank(df, score_col):
    df = df.sort_values([score_col, "PARTICIPANTE"], ascending=[False, True]).reset_index(drop=True)
    pos, current_pos, last_score = [], 0, None
    for score in df[score_col].tolist():
        if last_score is None or score != last_score:
            current_pos += 1
            last_score = score
        pos.append(current_pos)
    df["POS"] = pos
    return df

def simulate_spain_win(ranking, apuestas, level_cols):
    spain_holders = {norm(r["PARTICIPANTE"]) for _, r in apuestas.iterrows() if any(norm(r.get(c, "")) == norm(WINNER) for c in level_cols)}
    df = ranking.copy()
    df["BONUS_FINAL"] = df["PARTICIPANTE"].map(lambda x: CHAMPION_BONUS if norm(x) in spain_holders else 0)
    df["PUNTOS_FINALES"] = df["PUNTOS_TOTALES"] + df["BONUS_FINAL"]
    return dense_rank(df, "PUNTOS_FINALES")

def assign_prizes(final_df, participants):
    pot = participants * PRICE_PER_ENTRY
    df = final_df.copy()
    df["PREMIO"] = 0.0
    first_mask, second_mask = df["POS"] == 1, df["POS"] == 2
    first_count, second_count = int(first_mask.sum()), int(second_mask.sum())
    if first_count > 1:
        df.loc[first_mask, "PREMIO"] = pot / first_count
    else:
        df.loc[first_mask, "PREMIO"] = pot * 0.70
        if second_count:
            df.loc[second_mask, "PREMIO"] = (pot * 0.30) / second_count
    return df, pot

def prize_text(v):
    if not v or pd.isna(v) or float(v) == 0:
        return ""
    return f"{int(round(float(v)))} €" if abs(float(v) - round(float(v))) < 0.01 else f"{float(v):.2f} €".replace(".", ",")

def render_podium(final_df):
    chunks = []
    for pos, label, icon in [(1, "1º puesto", "🏆"), (2, "2º puesto", "🥈"), (3, "3º puesto", "🥉")]:
        people = final_df[final_df["POS"] == pos].copy()
        cls = "podium-card first" if pos == 1 else "podium-card"
        if people.empty:
            body = "<div class='podium-name'>Sin datos</div>"
        else:
            rows = []
            for _, r in people.iterrows():
                ptxt = prize_text(r.get("PREMIO", 0))
                prize = f"<span class='point-pill prize-pill'>{ptxt}</span>" if ptxt else ""
                bonus = f"<span class='point-pill bonus-pill'>+{int(r['BONUS_FINAL'])}</span>" if int(r.get("BONUS_FINAL", 0)) else ""
                rows.append(f"<div class='podium-name'>{esc(r['PARTICIPANTE'])}</div><div class='podium-points'><span class='point-pill'>{int(r['PUNTOS_FINALES'])}</span>{bonus}{prize}</div>")
            body = "".join(rows)
        chunks.append(f"<div class='{cls}'><div class='podium-rank'>{icon}</div><div style='color:#004A5F;font-weight:1000;font-size:1.08rem'>{label}</div>{body}</div>")
    return "<div class='podium-wrap'><div class='podium-grid'>" + "".join(chunks) + "</div></div>"

def render_final_table(df):
    rows = []
    for _, r in df.iterrows():
        prize = prize_text(r.get("PREMIO", 0))
        bonus = "+" + str(int(r["BONUS_FINAL"])) if int(r.get("BONUS_FINAL", 0)) else "-"
        rows.append(
            "<div class='rank-row'>"
            f"<div class='rank-pos'>{int(r['POS'])}º</div>"
            f"<div>{esc(r['PARTICIPANTE'])}</div>"
            f"<div>{int(r['PUNTOS_TOTALES'])}</div>"
            f"<div>{bonus}</div>"
            f"<div class='rank-total'>{int(r['PUNTOS_FINALES'])}</div>"
            f"<div class='rank-prize'>{prize}</div>"
            "</div>"
        )
    return (
        "<div class='rank-table'>"
        "<div class='rank-head'><div>Pos.</div><div>Participante</div><div>Actual</div><div>Final</div><div>Total</div><div>Premio</div></div>"
        + "".join(rows)
        + "</div>"
    )


def build_final_classification_df(df):
    work = df.copy()
    work = work.sort_values(["POS", "PUNTOS_FINALES", "PARTICIPANTE"], ascending=[True, False, True]).reset_index(drop=True)
    out = pd.DataFrame({
        "Pos.": work["POS"].astype(int).astype(str) + "º",
        "Participante": work["PARTICIPANTE"].astype(str),
        "Actual": work["PUNTOS_TOTALES"].astype(int),
        "Final": work["BONUS_FINAL"].apply(lambda x: f"+{int(x)}" if int(x) else "-"),
        "Total": work["PUNTOS_FINALES"].astype(int),
        "Premio": work["PREMIO"].apply(prize_text),
    })
    return out

def render_selected_teams(apuestas, level_cols, team_points, final_totals):
    cards = []
    work = apuestas.sort_values("PARTICIPANTE", key=lambda s: s.str.casefold()).reset_index(drop=True)
    for _, row in work.iterrows():
        participant = row["PARTICIPANTE"]
        total = final_totals.get(norm(participant), "")
        total_html = f"<span class='participant-total-pill'>{int(total)}</span>" if total != "" else ""
        picks = []
        for col in level_cols:
            team = str(row[col]).strip()
            pts = team_points.get(norm(team), "")
            picks.append(f"<span class='pick-chip'><span>{esc(team)}</span><b>{pts if pts != '' else ''}</b></span>")
        cards.append("<details class='participant-card'>" + f"<summary><span class='participant-summary-line'><span>{esc(participant)}</span>{total_html}</span></summary>" + f"<div class='pick-grid'>{''.join(picks)}</div>" + "</details>")
    return "<div class='participant-grid'>" + "".join(cards) + "</div>"

try:
    apuestas, ranking, level_cols, team_points = load_data(SHEET_URL)
    final_df = simulate_spain_win(ranking, apuestas, level_cols)
    final_df, pot = assign_prizes(final_df, len(apuestas))
    final_totals = {norm(r["PARTICIPANTE"]): int(r["PUNTOS_FINALES"]) for _, r in final_df.iterrows()}
except Exception as e:
    st.error("No se han podido cargar los datos del Excel. Revisa el enlace compartido y la estructura de las hojas.")
    st.exception(e)
    st.stop()

winner_count = int((final_df["BONUS_FINAL"] > 0).sum())
leader_points = int(final_df["PUNTOS_FINALES"].max()) if not final_df.empty else 0

st.markdown(f"""
<div class='hero'>
  <div class='hero-logo-row'>
    <div class='logo-avatar'>VSDTI</div>
    <div>
      <div class='hero-title-1'>Versia Servicios Distribuidos</div>
      <div class='hero-title-2'>Porra Mundial 2026</div>
      <div class='hero-kicker'>🇪🇸 España campeona · Clasificación final de la porra</div>
    </div>
    <div class='logo-avatar'>2026</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<div class='final-banner'><b>🏁 Se acabó la calculadora.</b> Con la victoria de <b>España</b>, se suman <b>+{CHAMPION_BONUS}</b> puntos a todas las porras que llevaban España. Ahora sí: este es el cierre final de la clasificación.</div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>Resumen final</div>", unsafe_allow_html=True)
st.markdown(f"<div class='metric-grid'><div class='metric-card'><div class='metric-label'>Participaciones</div><div class='metric-value'>{len(apuestas)}</div></div><div class='metric-card'><div class='metric-label'>Bote total</div><div class='metric-value'>{pot} €</div></div><div class='metric-card'><div class='metric-label'>Porras con España</div><div class='metric-value'>{winner_count}</div></div><div class='metric-card'><div class='metric-label'>Puntos líderes</div><div class='metric-value'>{leader_points}</div></div></div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>Podium final</div>", unsafe_allow_html=True)
st.markdown(render_podium(final_df), unsafe_allow_html=True)

st.markdown("<div class='section-title'>Clasificación final</div>", unsafe_allow_html=True)
st.markdown("<div class='section-subtitle'>Ordenada por puntos finales. En caso de empate, se comparte posición y la siguiente puntuación pasa al puesto siguiente.</div>", unsafe_allow_html=True)
classification_view = build_final_classification_df(final_df)
st.dataframe(
    classification_view,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Pos.": st.column_config.TextColumn("Pos.", width="small"),
        "Participante": st.column_config.TextColumn("Participante", width="large"),
        "Actual": st.column_config.NumberColumn("Actual", width="small"),
        "Final": st.column_config.TextColumn("Final", width="small"),
        "Total": st.column_config.NumberColumn("Total", width="small"),
        "Premio": st.column_config.TextColumn("Premio", width="small"),
    },
)

st.markdown("<div class='section-title'>Selección de participantes</div>", unsafe_allow_html=True)
st.markdown("<div class='section-subtitle'>Desplegable compacto con las selecciones de cada participante y su total final.</div>", unsafe_allow_html=True)
st.markdown(render_selected_teams(apuestas, level_cols, team_points, final_totals), unsafe_allow_html=True)

if st.button("Actualizar datos"):
    st.cache_data.clear()
    st.rerun()
