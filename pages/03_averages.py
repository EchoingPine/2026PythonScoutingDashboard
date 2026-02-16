import streamlit as st
import pandas as pd
import matplotlib.colors as mc
import utils
import competition_config as config

st.set_page_config(layout="wide")
st.title(":material/table: Averages")

conn = utils.get_connection()

# Load calculated averages for all teams
df = pd.read_sql("SELECT * FROM Calcs", conn)

# Create color gradients for different scoring phases
AutoCmap = mc.LinearSegmentedColormap.from_list("BlueGray", config.AUTO_COLORS)
TeleopCmap = mc.LinearSegmentedColormap.from_list("OrangeGray", config.TELEOP_COLORS)
EndgameCmap = mc.LinearSegmentedColormap.from_list("YellowGray", config.ENDGAME_COLORS)
TotalCmap = mc.LinearSegmentedColormap.from_list("GreenGray", config.TOTAL_COLORS)

# Apply styling with color gradients for each scoring phase
df = (df.style
    .format("{:.2f}", subset=config.SCORING_AVG_COLUMNS)
    .background_gradient(cmap=AutoCmap, subset=config.AUTO_AVG_COLUMNS, axis=0)
    .background_gradient(cmap=TeleopCmap, subset=config.TELEOP_AVG_COLUMNS, axis=0)
    .background_gradient(cmap=EndgameCmap, subset=config.ENDGAME_AVG_COLUMNS, axis=0)
    .background_gradient(cmap=TotalCmap, subset=config.TOTAL_AVG_COLUMNS, axis=0)
)

st.dataframe(df, use_container_width=True)

conn.close()
