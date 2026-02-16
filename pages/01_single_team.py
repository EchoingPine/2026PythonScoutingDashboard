import streamlit as st
import utils
import competition_config as config

st.set_page_config(layout="wide")
st.title(":material/person_search: Single Team")

utils.init_session_state()

# Sidebar team number input
teamNumber = None
try:
    teamNumber = int(st.sidebar.text_input("Team Number", "1100"))
except ValueError:
    st.error("Please enter a valid integer team number.")
    st.stop()

# Display team scores
utils.plot_team_scores(teamNumber, show_table=True, dataType="single team")
