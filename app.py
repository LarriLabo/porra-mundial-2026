
import streamlit as st
import pandas as pd

st.set_page_config(page_title="VSDTI Porra Mundial 2026", layout="wide")

LEVEL_TEAMS = {
    'Nivel 1': ['Francia', 'España', 'Argentina', 'Inglaterra', 'Portugal', 'Brasil'],
    'Nivel 2': ['Países Bajos', 'Marruecos', 'Bélgica', 'Alemania', 'Croacia', 'Colombia'],
}

LEVEL_COLORS = {
    'Nivel 1': '#F1C831',
    'Nivel 2': '#F28E00',
}

st.markdown("""
<style>
.level-title-block { width: 100%; margin-bottom: 0.6rem; }
.level-name { font-weight:900; font-size:1rem; line-height:1.2; margin-bottom:2px; word-break:break-word; }
.level-teams { font-size:0.80rem; font-weight:600; color:#706F6F; line-height:1.25; word-break:break-word; }
.bar-track { width:100%; height:10px; background:#eee; border-radius:10px; }
.bar-fill { height:10px; border-radius:10px; }
</style>
""", unsafe_allow_html=True)


def render_level_selection_chart(df):
    parts = []
    total = max(len(df), 1)
    for level, teams in LEVEL_TEAMS.items():
        counts = df[level].value_counts() if level in df.columns else {}
        percentages = []
        for team in teams:
            pct = round((counts.get(team, 0)/total)*100,1) if counts else 0
            percentages.append((team, pct))

        percentages = sorted(percentages, key=lambda x: (-x[1], x[0]))

        teams_text = ' · '.join(teams)
        title_html = f"""
        <div class='level-title-block'>
            <div class='level-name'>{level}</div>
            <div class='level-teams'>{teams_text}</div>
        </div>
        """
        parts.append(title_html)

        for i,(_,pct) in enumerate(percentages,1):
            parts.append(f"<div>{i}ª selección - {pct}%</div>")
            parts.append(f"<div class='bar-track'><div class='bar-fill' style='width:{pct}%;background:{LEVEL_COLORS[level]}'></div></div>")
    return ''.join(parts)

# dummy data
st.title("VSDTI Porra Mundial 2026")

df = pd.DataFrame({
    'Nivel 1':['España','Brasil','España'],
    'Nivel 2':['Alemania','Croacia','Alemania']
})

st.markdown(render_level_selection_chart(df), unsafe_allow_html=True)
