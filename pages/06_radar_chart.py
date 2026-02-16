import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import utils
import competition_config as config

st.set_page_config(layout="wide")
st.title(":material/radar: Radar Chart")

conn = utils.get_connection()

# Collect team numbers for radar comparison
teamNumbers = []
for i in range(1, 7):
    input_value = st.sidebar.text_input(f"Team {i}", "")
    if input_value.strip():
        try:
            teamNumber = int(input_value)
            teamNumbers.append(teamNumber)
        except ValueError:
            st.error(f"Please enter a valid number for Team {i}.")
            st.stop()

# Get normalized team data (0-100 scale)
df = pd.read_sql(f'SELECT * FROM "Normalized Data"', conn)
df.set_index("Team Number", inplace=True)

fig = go.Figure()

# Get radar chart metrics from config
radar_columns = list(config.RADAR_CHART_CONFIG['columns'].keys())
radar_labels = [config.RADAR_CHART_CONFIG['labels'][col] for col in radar_columns]

# Add trace for each selected team
for team in teamNumbers:
    if team not in df.index:
        st.warning(f"Team {team} not found in data.")
        continue

    # Get normalized values for this team
    values = [df.loc[team, col] for col in radar_columns]
    labels = radar_labels.copy()

    # Close the polygon by adding first point again
    values.append(values[0])
    labels.append(labels[0])

    # Add team's radar trace
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels,
        fill='toself',
        name=f"Team {team}",
        mode='lines',
        line=dict(shape="spline")
    ))

# Style radar chart traces and layout
fig.update_traces(opacity=0.5)

fig.update_polars(angularaxis_dtick='')
fig.update_polars(
    radialaxis_showgrid=False,
    radialaxis_gridwidth=0,
    angularaxis_layer='above traces'
)

# Apply styling
fig.update_layout(
    plot_bgcolor="#0e1117",
    polar=dict(
        bgcolor="#0e1117",
        radialaxis=dict(
            gridcolor="rgba(255,255,255,0.15)",
            tickfont=dict(color="white"),
            linecolor="rgba(255,255,255,0.3)",
            range=[0, 100],
            showticklabels=True
        ),
        angularaxis=dict(
            gridcolor="rgba(255,255,255,0.15)",
            tickfont=dict(color="white"),
            linecolor="rgba(255,255,255,0.3)"
        )
    ),
    font=dict(color="white"),
    showlegend=True,
)

st.plotly_chart(fig, use_container_width=True)

conn.close()
