import streamlit as st
import pandas as pd
import requests
import datetime
import competition_config as config

st.set_page_config(layout="wide")
st.title(":material/live_tv: Live Competition")

my_team_number = st.sidebar.text_input("Team Number", "1100").strip()
nexus_response = requests.get(config.NEXUS_URL, headers=config.NEXUS_HEADERS)

if not nexus_response.ok:
    st.error(f"Nexus API error: {nexus_response.status_code}")
    st.stop()

try:
    data = nexus_response.json()
except ValueError:
    preview = nexus_response.text[:200].strip()
    st.error("Nexus API did not return JSON.")
    if preview:
        st.code(preview)
    st.stop()

# Show all teams at the event
matches = data.get("matches", [])
team_numbers = set()
for match in matches:
    for team in match.get("redTeams", []) + match.get("blueTeams", []):
        team_numbers.add(team)

if team_numbers:
    teams_df = pd.DataFrame(sorted(team_numbers), columns=["Team Number"])
    st.subheader("Teams in Competition")
    st.dataframe(teams_df, use_container_width=True)
else:
    st.info("No team list available from Nexus yet.")

# Find my team's next match
my_matches = list(
    filter(
        lambda m: my_team_number in m.get("redTeams", []) + m.get("blueTeams", []),
        matches,
    )
)
my_next_match = next(
    (m for m in my_matches if m.get("status") != "On field"),
    None,
)

if not my_next_match:
    st.info(f"Team {my_team_number} doesn't have any future matches scheduled yet.")
    st.stop()

st.write(
    "Team {}'s next match is {} ({})!".format(
        my_team_number, my_next_match.get("label"), my_next_match.get("status")
    )
)

alliance_color = (
    "red" if my_team_number in my_next_match.get("redTeams", []) else "blue"
)
st.write("Put on the {} bumpers".format(alliance_color))

estimated_queue_time = my_next_match.get("times", {}).get("estimatedQueueTime")
if estimated_queue_time:
    st.write(
        "We will be queued at ~{}".format(
            datetime.datetime.fromtimestamp(estimated_queue_time / 1000)
        )
    )

# Get announcements and parts requests.
for announcement in data.get("announcements", []):
    st.write("Event announcement: {}".format(announcement.get("announcement")))

for parts_request in data.get("partsRequests", []):
    st.write(
        "Parts request for team {}: {}".format(
            parts_request.get("requestedByTeam"), parts_request.get("parts")
        )
    )
