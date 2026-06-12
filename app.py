# ==== PATCH V3 ==== 
# Añade este bloque en el tab Clasificación

selected_participant = st.selectbox(
    "Ver detalle del participante",
    df_classification["PARTICIPANTE"].tolist(),
    key="select_clasificacion"
)

def get_participant_row(df, participant):
    row = df[df["PARTICIPANTE"] == participant]
    if row.empty:
        return None
    return row.iloc[0]

row = get_participant_row(df_apuestas, selected_participant)

if row is not None:
    render_participant_detail(
        selected_participant,
        row,
        participant_level_points.get(selected_participant, {})
    )
# ==== END PATCH ====
