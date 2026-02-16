import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import utils

st.set_page_config(layout="wide")
st.title(":material/bubble_chart: Bubble Chart")

conn = utils.get_connection()

# Load all calculated metrics
df = pd.read_sql('SELECT * FROM "Calcs"', conn)

# Selectboxes for choosing X and Y axes from available columns
xAxis = st.sidebar.selectbox(":material/line_axis: X-Axis", ['Select X-Axis'] + df.columns.tolist())
yAxis = st.sidebar.selectbox(":material/line_axis: Y-Axis", ['Select Y-Axis'] + df.columns.tolist())

fig = go.Figure()

# Show info message until both axes are selected
if xAxis == 'Select X-Axis' or yAxis == 'Select Y-Axis':
    st.info("Select Axes to Continue")
else:
    # Create scatter plot with team labels
    fig.add_trace(
        go.Scatter(
            x=df[xAxis],
            y=df[yAxis],
            mode='markers+text',
            marker=dict(size=12),
            text=df['Team Number'],
            textposition='bottom center',
            textfont=dict(size=14, color='white'),
            hovertemplate=(
                "Team: %{text}<br>"
                f"{xAxis}: " + "%{x}<br>"
                f"{yAxis}: " + "%{y}<br>"
            )
        )
    )

    fig.update_layout(
        title=f"{yAxis} vs {xAxis} Scatter Plot",
        xaxis_title=xAxis,
        yaxis_title=yAxis,
    )

    st.plotly_chart(fig, width="stretch")

conn.close()
