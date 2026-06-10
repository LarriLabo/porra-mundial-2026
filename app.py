import io
import re
import urllib.request
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Porra Mundial 2026", page_icon="⚽", layout="wide")

HISTORY_FILE = "historial_puntos.csv"
DEFAULT_CACHE_MINUTES = 5


def drive_to_direct_download(url: str) -> str:
    if not url:
        return url
    url = url.strip()
    if "drive.google.com/uc?" in url and "id=" in url:
        return url
    patterns = [r"/file/d/([a-zA-Z0-9_-]+)", r"[?&]id=([a-zA-Z0-9_-]+)"]
    file_id = None
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            file_id = m.group(1)
            break
    if not file_id:
        return url
    return f"https://drive.google.com/uc?export=download&id={file_id}"


@st.cache_data(ttl=DEFAULT_CACHE_MINUTES * 60)
def download_file(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


@st.cache_data(ttl=DEFAULT_CACHE_MINUTES * 60)
def load_workbook(file_bytes: bytes):
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, header=None, engine="openpyxl")


def parse_puntos(raw: pd.DataFrame):
    ranking_prev = raw.iloc[2:, 0:3].copy()
    ranking_prev.columns = ["POS_ANTERIOR", "PARTICIPANTE", "PUNTOS_ANTERIORES"]
    ranking_prev = ranking_prev.dropna(subset=["PARTICIPANTE"]).copy()
    ranking_prev["PARTICIPANTE"] = ranking_prev["PARTICIPANTE"].astype(str).str.strip()
    ranking_prev["POS_ANTERIOR"] = pd.to_numeric(ranking_prev["POS_ANTERIOR"], errors="coerce")
    ranking_prev["PUNTOS_ANTERIORES"] = pd.to_numeric(ranking_prev["PUNTOS_ANTERIORES"], errors="coerce")

    ranking = raw.iloc[2:, 16:19].copy()
    ranking.columns = ["POS", "PARTICIPANTE", "PUNTOS_TOTALES"]
    ranking = ranking.dropna(subset=["PARTICIPANTE"]).copy()
    ranking["PARTICIPANTE"] = ranking["PARTICIPANTE"].astype(str).str.strip()
    ranking["POS"] = pd.to_numeric(ranking["POS"], errors="coerce")
    ranking["PUNTOS_TOTALES"] = pd.to_numeric(ranking["PUNTOS_TOTALES"], errors="coerce")
    ranking = ranking.sort_values(["POS", "PARTICIPANTE"], ascending=[True, True]).reset_index(drop=True)

    ranking = ranking.merge(
        ranking_prev[["PARTICIPANTE", "POS_ANTERIOR", "PUNTOS_ANTERIORES"]],
        on="PARTICIPANTE",
        how="left",
    )
    ranking["CAMBIO_POSICION"] = ranking["POS_ANTERIOR"] - ranking["POS"]
    ranking["CAMBIO_PUNTOS"] = ranking["PUNTOS_TOTALES"] - ranking["PUNTOS_ANTERIORES"]

    def mov(v):
        if pd.isna(v):
            return "🆕"
        if v > 0:
            return f"⬆️ +{int(v)}"
        if v < 0:
            return f"⬇️ {int(v)}"
        return "➡️ 0"

    ranking["MOVIMIENTO"] = ranking["CAMBIO_POSICION"].apply(mov)

    team_points = raw.iloc[2:, 5:14].copy()
    team_points.columns = ["Equipo", "Fase_Grupos", "Dieciseisavos", "Octavos", "Cuartos", "Semis", "Final", "Campeon", "TOTAL"]
    team_points = team_points.dropna(subset=["Equipo"]).copy()
    team_points["Equipo"] = team_points["Equipo"].astype(str).str.strip()
    for col in [c for c in team_points.columns if c != "Equipo"]:
        team_points[col] = pd.to_numeric(team_points[col], errors="coerce").fillna(0)
    team_points = team_points.sort_values(["TOTAL", "Equipo"], ascending=[False, True]).reset_index(drop=True)

    return ranking, team_points


@st.cache_data
def load_history():
    path = Path(HISTORY_FILE)
    if not path.exists():
        return pd.DataFrame(columns=["fecha", "participante", "puntos_totales"])
    hist = pd.read_csv(path)
    if set(["fecha", "participante", "puntos_totales"]).issubset(hist.columns):
        hist["fecha"] = pd.to_datetime(hist["fecha"], errors="coerce")
        hist["puntos_totales"] = pd.to_numeric(hist["puntos_totales"], errors="coerce")
        hist["participante"] = hist["participante"].astype(str)
        return hist.dropna(subset=["fecha", "participante", "puntos_totales"])
    return pd.DataFrame(columns=["fecha", "participante", "puntos_totales"])


def add_snapshot(ranking: pd.DataFrame):
    path = Path(HISTORY_FILE)
    now = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    snap = ranking[["PARTICIPANTE", "PUNTOS_TOTALES"]].copy()
    snap.columns = ["participante", "puntos_totales"]
    snap.insert(0, "fecha", now)
    if path.exists():
        hist = pd.read_csv(path)
        hist = pd.concat([hist, snap], ignore_index=True)
    else:
        hist = snap
    hist.to_csv(path, index=False)
    load_history.clear()


st.title("⚽ Porra Mundial 2026")
st.caption("Web en Streamlit leyendo un Excel .xlsx desde Google Drive.")

with st.sidebar:
    st.header("Fuente de datos")
    source = st.radio("¿Desde dónde cargar el Excel?", ["Google Drive", "Subida manual"], index=0)
    uploaded = None
    drive_link = ""
    if source == "Google Drive":
        drive_link = st.text_input(
            "Pega el enlace compartido de Google Drive",
            placeholder="https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        )
        st.caption("La caché es de 5 minutos. También puedes pulsar refrescar.")
    else:
        uploaded = st.file_uploader("Sube el Excel actualizado", type=["xlsx"])

    if st.button("🔄 Refrescar datos ahora"):
        download_file.clear()
        load_workbook.clear()
        st.rerun()

if source == "Google Drive":
    if not drive_link:
        st.info("Pega el enlace compartido de Google Drive para continuar.")
        st.stop()
    direct_url = drive_to_direct_download(drive_link)
    try:
        file_bytes = download_file(direct_url)
    except Exception as e:
        st.error(f"No se pudo descargar el Excel desde Google Drive: {e}")
        st.stop()
else:
    if uploaded is None:
        st.info("Sube el Excel para continuar.")
        st.stop()
    file_bytes = uploaded.read()

try:
    sheets = load_workbook(file_bytes)
except Exception as e:
    st.error(f"No se pudo abrir el Excel: {e}")
    st.stop()

if "Puntos" not in sheets:
    st.error("El Excel no contiene una hoja llamada 'Puntos'.")
    st.stop()

ranking, team_points = parse_puntos(sheets["Puntos"])

st.success(f"Datos cargados correctamente ({pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}).")

col1, col2, col3, col4 = st.columns(4)
leader = ranking.sort_values(["POS", "PARTICIPANTE"]).iloc[0]
col1.metric("Participantes", int(ranking["PARTICIPANTE"].nunique()))
col2.metric("Líder", leader["PARTICIPANTE"])
col3.metric("Puntos del líder", int(leader["PUNTOS_TOTALES"]))
col4.metric("Máx. subida de puntos", int(ranking["CAMBIO_PUNTOS"].fillna(0).max()))

t1, t2, t3 = st.tabs(["🏆 Ranking", "📈 Evolución", "🌍 Equipos"])

with t1:
    st.subheader("Clasificación actual")
    podium = ranking.nsmallest(3, "POS")[["PARTICIPANTE", "PUNTOS_TOTALES"]].reset_index(drop=True)
    a, b, c = st.columns(3)
    medals = ["🥇", "🥈", "🥉"]
    for i, col in enumerate([a, b, c]):
        if i < len(podium):
            row = podium.iloc[i]
            col.metric(f"{medals[i]} {row['PARTICIPANTE']}", int(row["PUNTOS_TOTALES"]))

    term = st.text_input("Buscar participante")
    view = ranking.copy()
    if term:
        view = view[view["PARTICIPANTE"].str.contains(term, case=False, na=False)]

    top_n = st.slider("Top N para gráfico", 5, min(30, len(ranking)), min(10, len(ranking)))
    chart = ranking.nsmallest(top_n, "POS").sort_values(["PUNTOS_TOTALES", "PARTICIPANTE"], ascending=[False, True]).set_index("PARTICIPANTE")
    st.bar_chart(chart["PUNTOS_TOTALES"])

    show = view[["POS", "PARTICIPANTE", "PUNTOS_TOTALES", "MOVIMIENTO", "CAMBIO_PUNTOS"]].copy()
    show.columns = ["Posición", "Participante", "Puntos", "Movimiento", "Δ puntos"]
    st.dataframe(show, use_container_width=True, hide_index=True)

with t2:
    st.subheader("Evolución de puntos")
    st.write("Guarda snapshots para construir el histórico.")
    if st.button("Guardar snapshot actual"):
        add_snapshot(ranking)
        st.success("Snapshot guardado.")
    hist = load_history()
    if hist.empty:
        st.warning("Todavía no hay historial guardado.")
    else:
        selected = st.multiselect(
            "Selecciona participantes",
            sorted(hist["participante"].unique().tolist()),
            default=sorted(hist["participante"].unique().tolist())[:5],
        )
        hv = hist.copy()
        if selected:
            hv = hv[hv["participante"].isin(selected)]
        if not hv.empty:
            pivot = hv.pivot_table(index="fecha", columns="participante", values="puntos_totales", aggfunc="last").sort_index()
            st.line_chart(pivot)
            st.dataframe(hv.sort_values(["fecha", "participante"]), use_container_width=True, hide_index=True)

with t3:
    st.subheader("Tabla de puntos por equipo")
    st.bar_chart(team_points.set_index("Equipo")["TOTAL"].head(15))
    st.dataframe(team_points, use_container_width=True, hide_index=True)
