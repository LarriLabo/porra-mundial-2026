
import json
import math
import urllib.request
import urllib.parse
import unicodedata
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Versia · Porra Mundial 2026", layout="wide")

# =========================
# CONFIG
# =========================
WORLDCUP26_GAMES_URL = "https://worldcup26.ir/get/games"
API_SPORTS_FIXTURES_URL = "https://v3.football.api-sports.io/fixtures?league=1&season=2026"

LEVEL_TEAMS = {
    "Nivel 1": ["Francia", "España", "Argentina", "Inglaterra", "Portugal", "Brasil"],
    "Nivel 2": ["Países Bajos", "Marruecos", "Bélgica", "Alemania", "Croacia", "Colombia"],
    "Nivel 3": ["Uruguay", "México", "Estados Unidos", "Suiza", "Senegal", "Japón"],
    "Nivel 4": ["Canadá", "Paraguay", "Australia", "Ecuador", "Suecia", "Egipto"],
    "Nivel 5": ["Irán", "Arabia Saudí", "Túnez", "Cabo Verde", "Panamá", "Corea del Sur"],
    "Nivel 6": ["Sudáfrica", "Qatar", "Bosnia y Herzegovina", "Rep. Checa", "Escocia", "Irak"],
    "Nivel 7": ["Curazao", "Costa de Marfil", "Nueva Zelanda", "Noruega", "Argelia", "Austria"],
    "Nivel 8": ["Jordania", "R.D. Congo", "Ghana", "Turquía"],
}

LEVEL_COLORS = {
    "Nivel 1": "#0B5FFF",
    "Nivel 2": "#2E8B57",
    "Nivel 3": "#8A5CF6",
    "Nivel 4": "#E67E22",
    "Nivel 5": "#D35454",
    "Nivel 6": "#16A085",
    "Nivel 7": "#7F8C8D",
    "Nivel 8": "#34495E",
}

TEAM_ALIASES = {
    "Rep. Checa": ["Czechia", "Czech Republic", "Czech Rep.", "Rep. Checa"],
    "Corea del Sur": ["Korea Republic", "South Korea", "Corea del Sur"],
    "Turquía": ["Turkey", "Türkiye", "Turquía"],
    "Cabo Verde": ["Cape Verde", "Cabo Verde"],
    "R.D. Congo": ["DR Congo", "Congo DR", "R.D. Congo"],
    "Curazao": ["Curacao", "Curaçao", "Curazao"],
    "Bosnia y Herzegovina": ["Bosnia & Herzegovina", "Bosnia-Herzegovina", "Bosnia y Herzegovina"],
    "Irak": ["Iraq", "Irak"],
    "Países Bajos": ["Netherlands", "Países Bajos"],
    "Arabia Saudí": ["Saudi Arabia", "Arabia Saudí"],
    "Marruecos": ["Morocco", "Marruecos"],
    "Costa de Marfil": ["Ivory Coast", "Côte d'Ivoire", "Costa de Marfil"],
    "Nueva Zelanda": ["New Zealand", "Nueva Zelanda"],
    "Noruega": ["Norway", "Noruega"],
    "Argelia": ["Algeria", "Argelia"],
    "Jordania": ["Jordan", "Jordania"],
    "Croacia": ["Croatia", "Croacia"],
    "Panamá": ["Panama", "Panamá"],
    "México": ["Mexico", "México"],
    "Sudáfrica": ["South Africa", "Sudáfrica"],
    "Canadá": ["Canada", "Canadá"],
    "Suiza": ["Switzerland", "Suiza"],
    "Brasil": ["Brazil", "Brasil"],
    "Escocia": ["Scotland", "Escocia"],
    "Estados Unidos": ["United States", "USA", "Estados Unidos"],
    "Alemania": ["Germany", "Alemania"],
    "Japón": ["Japan", "Japón"],
    "Suecia": ["Sweden", "Suecia"],
    "Túnez": ["Tunisia", "Túnez"],
    "Bélgica": ["Belgium", "Bélgica"],
    "Egipto": ["Egypt", "Egipto"],
    "Irán": ["Iran", "Irán"],
    "España": ["Spain", "España"],
    "Francia": ["France", "Francia"],
    "Inglaterra": ["England", "Inglaterra"],
}

STATUS_ORDER = {
    "EN JUEGO": 0,
    "FINALIZADO": 1,
    "PROGRAMADO": 2,
    "": 3,
}

# =========================
# ESTILOS
# =========================
st.markdown(
    """
    <style>
    .block-container { max-width: 1200px; padding-top: 1rem; padding-bottom: 2rem; }
    .hero {
        background: linear-gradient(135deg, #f7f9fc 0%, #eef4ff 100%);
        border: 1px solid #dce7ff;
        border-radius: 24px;
        padding: 1.5rem 1.6rem;
        margin-bottom: 1rem;
    }
    .hero-title { font-size: 2rem; font-weight: 900; color: #083b6e; line-height: 1.1; margin-bottom: .25rem; }
    .hero-sub { font-size: 1rem; color: #41576d; }
    .mini-card {
        background: #fff;
        border: 1px solid #e6ebf2;
        border-radius: 20px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,.03);
    }
    .metric-big { font-size: 1.8rem; font-weight: 900; color: #083b6e; }
    .metric-label { color: #5b6b7e; font-size: .95rem; }
    .level-title-block { width: 100%; margin-bottom: 0.5rem; }
    .level-name { font-weight: 900; font-size: 1rem; line-height: 1.2; margin-bottom: 2px; word-break: break-word; }
    .level-teams { font-size: .80rem; font-weight: 600; color: #6b7280; line-height: 1.25; word-break: break-word; }
    .match-card {
        background: #fff;
        border: 1px solid #e6ebf2;
        border-radius: 18px;
        padding: .9rem 1rem;
        margin-bottom: .75rem;
        box-shadow: 0 2px 8px rgba(0,0,0,.02);
    }
    .match-top { display:flex; justify-content:space-between; gap: 1rem; align-items:center; }
    .match-teams { font-size: 1rem; font-weight: 800; color:#0f172a; }
    .match-meta { font-size: .83rem; color:#64748b; margin-top: .15rem; }
    .match-score { font-size: 1.2rem; font-weight: 900; color:#083b6e; white-space: nowrap; }
    .badge {
        display:inline-block; padding:.18rem .55rem; border-radius:999px; font-size:.75rem; font-weight:800;
        border:1px solid transparent;
    }
    .badge-live { background:#fff3cd; color:#8a5a00; border-color:#ffdd8a; }
    .badge-ft { background:#eaf7ec; color:#1f7a38; border-color:#b6e0bf; }
    .badge-pre { background:#eef2f7; color:#52637c; border-color:#d5dde7; }
    .tabs-help { color:#64748b; font-size:.85rem; margin-top:.25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# UTILIDADES
# =========================
def strip_accents(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalize_team_name(value: str) -> str:
    value = (value or "").strip().lower()
    value = strip_accents(value)
    value = value.replace("&", " y ").replace("-", " ").replace(".", " ")
    value = " ".join(value.split())
    return value


def all_aliases(team: str):
    aliases = TEAM_ALIASES.get(team, [team]) + [team]
    return {normalize_team_name(x) for x in aliases}


def http_get_json(url: str, headers=None, timeout: int = 20):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def extract_from_paths(obj, paths):
    for path in paths:
        cur = obj
        ok = True
        for part in path:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return None


def parse_iso_datetime(value):
    if value in (None, ""):
        return None
    try:
        txt = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(txt)
    except Exception:
        return None


def format_dt_es(dt_obj):
    if not dt_obj:
        return "Fecha pendiente"
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    local = dt_obj.astimezone()
    return local.strftime("%d/%m/%Y · %H:%M")


def format_score(home_score, away_score):
    if home_score in (None, "") and away_score in (None, ""):
        return ""
    return f"{home_score} - {away_score}"


def status_label(status: str) -> str:
    s = (status or "").upper().strip()
    if any(x in s for x in ["FT", "FINISHED", "COMPLETED"]):
        return "FINALIZADO"
    if any(x in s for x in ["LIVE", "1H", "2H", "ET", "PEN", "HT", "IN_PLAY"]):
        return "EN JUEGO"
    return "PROGRAMADO"


def status_badge_class(status_label_value: str) -> str:
    if status_label_value == "EN JUEGO":
        return "badge badge-live"
    if status_label_value == "FINALIZADO":
        return "badge badge-ft"
    return "badge badge-pre"

# =========================
# DATOS DEMO / PARTICIPANTES
# =========================
def get_demo_participants_df() -> pd.DataFrame:
    rows = [
        {"Participante": "Ane", "PUNTOS_TOTALES": 18, "Nivel 1": "España", "Nivel 2": "Alemania", "Nivel 3": "Uruguay", "Nivel 4": "Canadá"},
        {"Participante": "Iker", "PUNTOS_TOTALES": 18, "Nivel 1": "Brasil", "Nivel 2": "Croacia", "Nivel 3": "México", "Nivel 4": "Suecia"},
        {"Participante": "Leire", "PUNTOS_TOTALES": 16, "Nivel 1": "España", "Nivel 2": "Alemania", "Nivel 3": "México", "Nivel 4": "Egipto"},
        {"Participante": "Jon", "PUNTOS_TOTALES": 14, "Nivel 1": "Francia", "Nivel 2": "Bélgica", "Nivel 3": "Suiza", "Nivel 4": "Paraguay"},
        {"Participante": "Nerea", "PUNTOS_TOTALES": 14, "Nivel 1": "Portugal", "Nivel 2": "Países Bajos", "Nivel 3": "Japón", "Nivel 4": "Australia"},
        {"Participante": "Mikel", "PUNTOS_TOTALES": 12, "Nivel 1": "Argentina", "Nivel 2": "Marruecos", "Nivel 3": "Estados Unidos", "Nivel 4": "Ecuador"},
    ]
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def load_participants_df():
    # Si en futuro quieres conectar Google Sheets, este es el sitio.
    return get_demo_participants_df().copy()

# =========================
# CLASIFICACIÓN
# =========================
def build_ranking(df: pd.DataFrame) -> pd.DataFrame:
    ranking = df[["Participante", "PUNTOS_TOTALES"]].copy()
    ranking = ranking.sort_values(["PUNTOS_TOTALES", "Participante"], ascending=[False, True]).reset_index(drop=True)
    ranking["POS_ORDENADA"] = ranking["PUNTOS_TOTALES"].rank(method="dense", ascending=False).astype(int)
    return ranking


def render_ranking(df: pd.DataFrame):
    ranking = build_ranking(df)
    left, right = st.columns([1.05, 2])
    with left:
        st.markdown('<div class="mini-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-big">{len(df)}</div><div class="metric-label">Participantes</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="metric-big">{ranking["PUNTOS_TOTALES"].max()}</div><div class="metric-label">Máxima puntuación</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        display_df = ranking.rename(columns={"POS_ORDENADA": "Pos.", "Participante": "Participante", "PUNTOS_TOTALES": "Puntos"})
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# =========================
# SELECCIÓN POR NIVELES
# =========================
def render_level_selection_chart(df: pd.DataFrame):
    total = max(len(df), 1)
    for level, teams in LEVEL_TEAMS.items():
        if level not in df.columns:
            continue
        counts = df[level].value_counts()
        data = []
        for team in teams:
            pct = round((counts.get(team, 0) / total) * 100, 1)
            data.append((team, pct))
        data = sorted(data, key=lambda x: (-x[1], x[0]))

        st.markdown(
            f"""
            <div class='level-title-block'>
                <div class='level-name'>{level}</div>
                <div class='level-teams'>{' · '.join(teams)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        color = LEVEL_COLORS.get(level, "#0B5FFF")
        for team, pct in data:
            c1, c2 = st.columns([2.2, 1])
            with c1:
                st.write(team)
                st.progress(min(max(pct / 100, 0), 1))
            with c2:
                st.write(f"**{pct}%**")
        st.markdown("---")

# =========================
# PARTICIPACIONES / CURIOSIDADES
# =========================
def render_participaciones(df: pd.DataFrame):
    counts = df[[c for c in df.columns if c.startswith("Nivel")]].stack().value_counts().head(15)
    out = pd.DataFrame({"Equipo": counts.index, "Selecciones": counts.values})
    st.dataframe(out, use_container_width=True, hide_index=True)

# =========================
# RESULTADOS / CALENDARIO
# =========================
def normalize_open_worldcup26(payload):
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        candidates = []
        for key in ["games", "data", "matches", "result", "results"]:
            if isinstance(payload.get(key), list):
                candidates = payload[key]
                break
        if not candidates:
            for value in payload.values():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    candidates = value
                    break
    else:
        candidates = []

    normalized = []
    for item in candidates:
        home = extract_from_paths(item, [
            ["home_team", "name"], ["homeTeam", "name"], ["team1", "name"], ["team_home", "name"],
            ["localteam", "name"], ["home_name"], ["homeTeam"], ["home_team"], ["team1"]
        ])
        away = extract_from_paths(item, [
            ["away_team", "name"], ["awayTeam", "name"], ["team2", "name"], ["team_away", "name"],
            ["visitorteam", "name"], ["away_name"], ["awayTeam"], ["away_team"], ["team2"]
        ])
        home_score = extract_from_paths(item, [["home_score"], ["score", "home"], ["homeScore"], ["goalsHomeTeam"], ["score1"], ["team1_score"]])
        away_score = extract_from_paths(item, [["away_score"], ["score", "away"], ["awayScore"], ["goalsAwayTeam"], ["score2"], ["team2_score"]])
        status = extract_from_paths(item, [["status"], ["state"], ["match_status"], ["fixture", "status", "short"], ["phase"]])
        date_value = extract_from_paths(item, [["utc_date"], ["utcDate"], ["date"], ["kickoff_utc"], ["fixture", "date"], ["datetime"]])
        stadium = extract_from_paths(item, [["stadium", "name"], ["venue"], ["stadium"], ["location"]])
        city = extract_from_paths(item, [["stadium", "city"], ["city"]])
        round_name = extract_from_paths(item, [["round"], ["stage_name"], ["stage"], ["group"]])
        normalized.append({
            "home": str(home or "").strip(),
            "away": str(away or "").strip(),
            "home_score": home_score,
            "away_score": away_score,
            "status_raw": str(status or "").strip(),
            "status_label": status_label(str(status or "")),
            "kickoff": parse_iso_datetime(date_value),
            "stadium": str(stadium or "").strip(),
            "city": str(city or "").strip(),
            "round": str(round_name or "").strip(),
        })
    return normalized


def normalize_api_football(payload):
    normalized = []
    for item in payload.get("response", []) if isinstance(payload, dict) else []:
        home = extract_from_paths(item, [["teams", "home", "name"]])
        away = extract_from_paths(item, [["teams", "away", "name"]])
        home_score = extract_from_paths(item, [["goals", "home"]])
        away_score = extract_from_paths(item, [["goals", "away"]])
        status = extract_from_paths(item, [["fixture", "status", "short"], ["fixture", "status", "long"]])
        dt_val = extract_from_paths(item, [["fixture", "date"]])
        venue = extract_from_paths(item, [["fixture", "venue", "name"]])
        city = extract_from_paths(item, [["fixture", "venue", "city"]])
        round_name = extract_from_paths(item, [["league", "round"]])
        normalized.append({
            "home": str(home or "").strip(),
            "away": str(away or "").strip(),
            "home_score": home_score,
            "away_score": away_score,
            "status_raw": str(status or "").strip(),
            "status_label": status_label(str(status or "")),
            "kickoff": parse_iso_datetime(dt_val),
            "stadium": str(venue or "").strip(),
            "city": str(city or "").strip(),
            "round": str(round_name or "").strip(),
        })
    return normalized


@st.cache_data(ttl=300, show_spinner=False)
def fetch_worldcup_matches():
    source_name = None
    error_messages = []

    # Opción principal: API abierta sin necesidad de clave
    try:
        payload = http_get_json(WORLDCUP26_GAMES_URL)
        rows = normalize_open_worldcup26(payload)
        if rows:
            source_name = "worldcup26.ir"
            return rows, source_name, None
        error_messages.append("worldcup26.ir sin partidos")
    except Exception as exc:
        error_messages.append(f"worldcup26.ir: {exc}")

    # Fallback opcional: API-Football si hay secreto
    api_key = None
    for secret_name in ["APISPORTS_KEY", "API_FOOTBALL_KEY", "FOOTBALL_API_KEY"]:
        if secret_name in st.secrets:
            api_key = st.secrets[secret_name]
            break

    if api_key:
        try:
            payload = http_get_json(API_SPORTS_FIXTURES_URL, headers={"x-apisports-key": str(api_key)})
            rows = normalize_api_football(payload)
            if rows:
                source_name = "api-football"
                return rows, source_name, None
            error_messages.append("api-football sin partidos")
        except Exception as exc:
            error_messages.append(f"api-football: {exc}")

    return [], None, " | ".join(error_messages) if error_messages else None


def render_calendar():
    rows, source_name, err = fetch_worldcup_matches()
    if source_name:
        st.caption(f"Resultados actualizados automáticamente • fuente: {source_name} • refresco 5 min")
    elif err:
        st.caption("Resultados automáticos no disponibles temporalmente")

    if not rows:
        st.warning("No se han podido cargar los partidos del Mundial 2026.")
        return

    rounds = sorted({r["round"] for r in rows if r.get("round")})
    statuses = ["Todos", "EN JUEGO", "FINALIZADO", "PROGRAMADO"]

    c1, c2, c3 = st.columns([1.2, 1.2, 2])
    with c1:
        selected_status = st.selectbox("Estado", statuses, index=0)
    with c2:
        selected_round = st.selectbox("Fase", ["Todas"] + rounds if rounds else ["Todas"], index=0)
    with c3:
        team_query = st.text_input("Filtrar por equipo", value="")

    filtered = rows.copy()
    if selected_status != "Todos":
        filtered = [r for r in filtered if r.get("status_label") == selected_status]
    if selected_round != "Todas":
        filtered = [r for r in filtered if r.get("round") == selected_round]
    if team_query.strip():
        nq = normalize_team_name(team_query)
        filtered = [r for r in filtered if nq in normalize_team_name(r.get("home", "")) or nq in normalize_team_name(r.get("away", ""))]

    filtered = sorted(
        filtered,
        key=lambda r: (
            STATUS_ORDER.get(r.get("status_label", ""), 999),
            r.get("kickoff") or datetime.max.replace(tzinfo=timezone.utc),
            r.get("home", ""),
        ),
    )

    st.markdown(f"**{len(filtered)} partidos**")
    for match in filtered:
        score = format_score(match.get("home_score"), match.get("away_score"))
        badge = match.get("status_label", "")
        meta = []
        if match.get("kickoff"):
            meta.append(format_dt_es(match.get("kickoff")))
        if match.get("stadium"):
            place = match.get("stadium")
            if match.get("city"):
                place += f" · {match.get('city')}"
            meta.append(place)
        if match.get("round"):
            meta.append(match.get("round"))
        meta_text = " • ".join([m for m in meta if m])

        st.markdown(
            f"""
            <div class="match-card">
                <div class="match-top">
                    <div>
                        <div class="match-teams">{match.get('home','')} vs {match.get('away','')}</div>
                        <div class="match-meta">{meta_text}</div>
                    </div>
                    <div style="text-align:right;">
                        <div class="match-score">{score or '—'}</div>
                        <span class="{status_badge_class(badge)}">{badge}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# =========================
# PORTADA
# =========================
def render_hero(df_participants: pd.DataFrame):
    total_porras = len(df_participants)
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-title">Porra Mundial 2026</div>
            <div class="hero-sub">Panel de seguimiento con clasificación, participantes y calendario con resultados automáticos. Total de porras: <b>{total_porras}</b>.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================
# APP
# =========================
def main():
    df = load_participants_df()
    render_hero(df)

    tabs = st.tabs(["Clasificación", "Participantes", "Calendario", "Participaciones", "Selección nivel"])

    with tabs[0]:
        render_ranking(df)

    with tabs[1]:
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[2]:
        render_calendar()

    with tabs[3]:
        render_participaciones(df)

    with tabs[4]:
        render_level_selection_chart(df)


if __name__ == "__main__":
    main()
