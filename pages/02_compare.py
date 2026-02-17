import streamlit as st
import utils
import competition_config as config

st.set_page_config(layout="wide")
st.title(":material/compare: Compare Teams")

utils.init_session_state()

# Toggle display options for different score phases
st.sidebar.markdown("### Data Types")

st.session_state.showTotal = st.sidebar.checkbox(":material/score: Total", st.session_state.get("showTotal", True))
st.session_state.showAuto = st.sidebar.checkbox(":material/clock_loader_10: Auto", st.session_state.get("showAuto", True))
st.session_state.showTeleop = st.sidebar.checkbox(":material/clock_loader_80: Teleop", st.session_state.get("showTeleop", True))
st.session_state.showEndgame = st.sidebar.checkbox(":material/flag: Endgame", st.session_state.get("showEndgame", True))
st.session_state.showLegend = st.sidebar.checkbox(":material/legend_toggle: Show Legend", st.session_state.get("showLegend", True))

# Collect team numbers for comparison
teamNumbers = []
for i in range(1, 7):
    input_value = st.sidebar.text_input(f"Team {i}", "", key=f"compare_team_{i}")
    if input_value.strip():
        try:
            teamNumber = int(input_value)
            teamNumbers.append(teamNumber)
        except ValueError:
            st.error(f"Enter a valid number for Team {i}.")
            st.stop()

# Display teams in 3-column layout
for i in range(0, len(teamNumbers), 3):
    columns = st.columns(3)
    for j, teamNumber in enumerate(teamNumbers[i:i + 3]):
        with columns[j]:
            utils.plot_team_scores(teamNumber)
