import streamlit as st
import pandas as pd
import json
import utils
import competition_config as config

st.set_page_config(layout="wide")
st.title(":material/scoreboard: Match Reference")

conn = utils.get_connection()

# Get match number input
try:
    matchNumber = int(st.sidebar.text_input("Match Number", "1", key="match_reference_number"))
except ValueError:
    st.error("Enter a valid match number")
    st.stop()

# Fetch match lineup and videos from TBA data
test_df = pd.read_sql(
    'SELECT "alliances.blue.team_keys" AS blue_keys, "alliances.red.team_keys" AS red_keys, "videos" '
    'FROM "TBA Data" WHERE "match_number" = ? AND "comp_level" = "qm" AND "Event Name" = ?',
    conn,
    params=(matchNumber, st.session_state.comp)
)

if test_df.empty:
    st.error("Enter a valid match number")
    st.stop()

row = test_df.iloc[0]

def parse_videos(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []

def parse_team_keys(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []

def key_to_team_number(team_key):
    if not isinstance(team_key, str):
        return None
    if team_key.startswith("frc"):
        team_key = team_key[3:]
    try:
        return int(team_key)
    except ValueError:
        return None

blue_keys = parse_team_keys(row["blue_keys"])
red_keys = parse_team_keys(row["red_keys"])

positions = []
for idx, team_key in enumerate(red_keys[:3], start=1):
    team_number = key_to_team_number(team_key)
    if team_number is not None:
        positions.append({"Team Number": team_number, "Position": f"RED {idx}"})
for idx, team_key in enumerate(blue_keys[:3], start=1):
    team_number = key_to_team_number(team_key)
    if team_number is not None:
        positions.append({"Team Number": team_number, "Position": f"BLUE {idx}"})

teams_df = pd.DataFrame(positions)
if teams_df.empty:
    st.error("Match data is missing team keys.")
    st.stop()

# Fetch scores for all teams in this match
placeholders = ','.join(['?' for _ in teams_df["Team Number"]])
match_score_df = pd.read_sql(
    f'SELECT "Team Number", "Total Score", "Auto Score", "Teleop Score", "Endgame Score" FROM "Scouting_Data" WHERE "Team Number" IN ({placeholders}) AND "Match Number" = ? AND "Event Name" = ?',
    conn,
    params=list(teams_df["Team Number"]) + [matchNumber, st.session_state.comp]
)

# Merge match lineup with average scores
result_df = (
    teams_df
    .merge(match_score_df, on="Team Number", how="left")
)

result_df["Team Number"] = result_df["Team Number"].astype(str)
result_df["Position"] = result_df["Position"].str.upper()
result_df["Alliance"] = result_df["Position"].str[:4]
result_df["Slot"] = result_df["Position"].str[-1]
result_df.sort_values(by=["Alliance"], inplace=True)
result_df.drop(columns=["Alliance", "Slot"], inplace=True)

scouting_blue_score = result_df[result_df["Position"].str.contains("BLUE")][["Auto Score", "Teleop Score", "Endgame Score"]].sum().sum()
scouting_red_score = result_df[result_df["Position"].str.contains("RED")][["Auto Score", "Teleop Score", "Endgame Score"]].sum().sum()

result_df = result_df.style.apply(utils.color_alliance, axis=1).set_properties(subset=["Team Number"], **{"font-weight": "bold"})


match_df = pd.read_sql(
    'SELECT "alliances.blue.score" AS blue_score, "alliances.red.score" AS red_score FROM "TBA Data" WHERE "match_number" = ? AND "comp_level" = "qm" AND "Event Name" = ?',
    conn,
    params=(matchNumber, st.session_state.comp)
)

header = f"Match {matchNumber}"

st.header(header)

st.subheader(":material/poker_chip: Team Lineup & Averages")
st.dataframe(result_df, width="stretch")

st.subheader(":material/scoreboard: Match Scores")
st.markdown("##### As Given by TBA")
if not match_df.empty:
    tba_blue_score = match_df.iloc[0]["blue_score"]
    tba_red_score = match_df.iloc[0]["red_score"]
    st.markdown(f"**Red Alliance:** {tba_red_score}  |  **Blue Alliance:** {tba_blue_score}")
st.markdown("##### Calculated from Scouting Data")
if not match_df.empty:
    st.markdown(f"**Red Alliance:** {scouting_red_score}  |  **Blue Alliance:** {scouting_blue_score}")

# Display video if available
st.subheader(":material/youtube_activity: Video")
videos = parse_videos(row.get("videos", []))
if videos:
    for video in videos:
        video_id = video.get("key")
        st.video(f"https://www.youtube.com/watch?v={video_id}")
else:
    st.info("No video available for this match")

conn.close()
