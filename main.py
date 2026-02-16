import streamlit as st
import db_calc as db


# Define navigation pages
pages = {
    "Main": [
        st.Page("pages/00_home_page.py", title="Home", icon=":material/home:"),
        st.Page("pages/01_single_team.py", title="Single Team", icon=":material/person_search:"),
        st.Page("pages/02_compare.py", title="Compare Teams", icon=":material/compare:"),
        st.Page("pages/03_averages.py", title="Team Averages", icon=":material/table:"),
        st.Page("pages/04_match_reference.py", title="Match Reference", icon=":material/scoreboard:"),
        st.Page("pages/05_bubble_chart.py", title="Bubble Chart", icon=":material/bubble_chart:"),
        st.Page("pages/06_radar_chart.py", title="Radar Chart", icon=":material/radar:"),
        st.Page("pages/07_live_comp.py", title="Live Competition", icon=":material/live_tv:"),
    ],
    "Guides": [
        st.Page("pages/guides/configuration.py", title="Configuration Guide", icon=":material/settings:"),
    ],
}

# Set up navigation
nav = st.navigation(pages)

st.logo(image="assets/inverse polarity logo magnet.png", size="large")

st.set_page_config(
    page_title="Scouting Dashboard",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)
nav.run()