import streamlit as st
import db_calc as db

# Home page content
st.title(":material/owl: 2026 Scouting Dashboard")
st.markdown("""
Use the sidebar to navigate:

- :material/person: **Single Team** - View metrics for a single team
- :material/compare: **Compare** - View and compare up to 6 teams side-by-side
- :material/table: **Team Averages** - View team averages across all matches
- :material/scoreboard: **Match Reference** - View specific match details and videos
- :material/bubble_chart: **Bubble Chart** - View trends and correlations between metrics
- :material/radar: **Radar Chart** - View and compare teams across multiple metrics
- :material/live_tv: **Live Competition** - View competition status during events

---

### :material/database: Outdated Data?
""")

if st.button(":material/refresh: Refresh Values", use_container_width=True):
    with st.spinner("Refreshing..."):
        try:
            db.perform_calculations()
            st.success(":material/check: Data refreshed successfully!")
        except Exception as e:
            st.error(f":material/error: Error refreshing data: {e}")