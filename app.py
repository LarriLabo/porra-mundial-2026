# app.py versión actualizada (con detalle de participante en clasificación)
# NOTA: versión simplificada representativa con la nueva funcionalidad integrada

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Porra Mundial 2026", layout="wide")

# ---- MOCK DATA (sustituir por Google Sheets real) ----
df_classification = pd.DataFrame({
    "PARTICIPANTE": ["Iker", "Jon", "Ane"],
    "PUNTOS_TOTALES": [30, 25, 20]
})

# equipos por nivel (simulación)
df_bets = pd.DataFrame({
    "PARTICIPANTE": ["Iker", "Jon", "Ane"],
    "Nivel 1": ["Brasil, Francia", "España, Alemania", "Argentina"],
    "Nivel 2": ["Portugal", "Italia", "Inglaterra"]
})

# puntos por nivel (simulación)
level_points = {
    "Iker": {"Nivel 1": 12, "Nivel 2": 6},
    "Jon": {"Nivel 1": 10, "Nivel 2": 5},
    "Ane": {"Nivel 1": 8, "Nivel 2": 4},
}

LEVEL_COLORS = {
    "Nivel 1": "#1f77b4",
    "Nivel 2": "#ff7f0e",
}

# ---- NUEVAS FUNCIONES ----

def get_participant_teams(df_bets, participant):
    row = df_bets[df_bets["PARTICIPANTE"] == participant]
    if row.empty:
        return {}

    teams_by_level = {}
    for col in df_bets.columns:
        if "Nivel" in col:
            teams_by_level[col] = row.iloc[0][col]
    return teams_by_level


def render_participant_detail(participant, teams_by_level, points_by_level):
    st.markdown(f"### 🧾 Detalle de {participant}")

    for nivel in teams_by_level:
        equipos = teams_by_level[nivel]
        puntos = points_by_level.get(nivel, 0)
        color = LEVEL_COLORS.get(nivel, "#ccc")

        html = f"""
        <div style='border-left: 6px solid {color}; padding: 10px; margin-bottom: 10px;'>
            <b>{nivel}</b><br>
            Equipos: {equipos}<br>
            <b>Puntos: {puntos}</b>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

# ---- UI ----

st.title("🏆 Clasificación")
st.dataframe(df_classification)

selected_participant = st.selectbox(
    "Selecciona participante para ver detalle",
    df_classification["PARTICIPANTE"]
)

teams = get_participant_teams(df_bets, selected_participant)
points = level_points.get(selected_participant, {})

render_participant_detail(selected_participant, teams, points)
