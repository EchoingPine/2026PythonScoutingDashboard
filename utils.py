import sqlite3
import streamlit as st
import plotly.graph_objects as go
import competition_config as config

# Initialize database connection
def get_connection():
    """Get SQLite database connection."""
    return sqlite3.connect("Scouting_Data.db")

# Apply row styling based on alliance color (red/blue)
def color_alliance(row):
    """Style dataframe rows with alliance color background."""
    if row["Position"].startswith("RED"):
        return ["background-color: rgba(255, 0, 0, 0.15)"] * len(row)
    elif row["Position"].startswith("BLUE"):
        return ["background-color: rgba(0, 100, 255, 0.15)"] * len(row)
    return [""] * len(row)

# Retrieve specific data type from database for a given team/match
def retrieve_data(data_type, team_number, match_number=None):
    """Query scouting data from database.
    Args:
        data_type: Column name to retrieve
        team_number: Team's number
        match_number: Optional match number filter
    """
    conn = get_connection()
    cursor = conn.cursor()
    if match_number is None:
        query = f'SELECT "{data_type}" FROM Scouting_Data WHERE "Team Number" = ?'
        params = (team_number,)
    else:
        query = f'SELECT "{data_type}" FROM Scouting_Data WHERE "Team Number" = ? AND "Match Number" = ?'
        params = (team_number, match_number)
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.close()
    return result

# Generate score trend visualization and optional detailed tables for a team
def plot_team_scores(team_number, show_table=False, dataType=""):
    """Plot team performance across matches with optional detailed breakdown tables."""
    conn = get_connection()
    # Fetch all matches for the team, ordered chronologically
    team_data = sql_to_df(
        f"SELECT * FROM Scouting_Data WHERE `Team Number` = {team_number} ORDER BY `Team Match Number` ASC",
        conn
    )
    if team_data.empty:
        st.error("Please enter a valid team number.")
        return

    # Initialize line plot figure
    fig = go.Figure()

    # Add traces for selected score types based on session state
    if st.session_state.get("showTotal"):
        fig.add_trace(go.Scatter(
            x=team_data['Team Match Number'],
            y=team_data['Total Score'],
            mode='lines+markers',
            name='Total Score',
            line=dict(shape='spline')
        ))

    # Always show auto/teleop in single team view
    if st.session_state.get("showAuto") or dataType.lower() == "single team":
        fig.add_trace(go.Scatter(
            x=team_data['Team Match Number'],
            y=team_data['Auto Score'],
            mode='lines+markers',
            name='Auto Score',
            line=dict(shape='spline')
        ))

    if st.session_state.get("showTeleop") or dataType.lower() == "single team":
        fig.add_trace(go.Scatter(
            x=team_data['Team Match Number'],
            y=team_data['Teleop Score'],
            mode='lines+markers',
            name='Teleop Score',
            line=dict(shape='spline')
        ))

    if st.session_state.get("showEndgame"):
        fig.add_trace(go.Scatter(
            x=team_data['Team Match Number'],
            y=team_data['Endgame Score'],
            mode='lines+markers',
            name='Endgame Score',
            line=dict(shape='spline')
        ))

    # Change axis titles and layout
    fig.update_layout(
        legend=dict(groupclick="toggleitem"),
        title=f"Team {team_number} Score Trend",
        xaxis_title="Match Number",
        yaxis_title="Score",
        yaxis=dict(range=[0, 125]),
    )

    # Display the plot
    st.plotly_chart(fig, use_container_width=True)

    # Show detailed breakdown tables for single team view
    if show_table:
        # Fetch pit scouting data
        pit_data = sql_to_df(
            f'SELECT * FROM "Pit Scouting" WHERE "Team #" = {team_number}',
            conn
        )

        # Clean up match data
        team_data.drop(columns='Scouter Initials', inplace=True, errors='ignore')
        team_data.drop(columns='Team Number', inplace=True, errors='ignore')

        pit_data.drop(columns='Name(s)', inplace=True, errors='ignore')
        pit_data.drop(columns='Team #', inplace=True, errors='ignore')

        # Transpose pit data for display
        pit_data = pit_data.transpose()

        # Get column indices for each game phase from config
        auto = config.SINGLE_TEAM_COLUMNS['auto'] + ['Team Match Number']
        teleop = config.SINGLE_TEAM_COLUMNS['teleop'] + ['Team Match Number']
        endgame = config.SINGLE_TEAM_COLUMNS['endgame'] + ['Team Match Number']

        # Prepare and format auto phase data with averages
        auto_data = team_data[auto]
        auto_data.set_index("Team Match Number", inplace=True)
        auto_data = auto_data.transpose()
        auto_data['Averages'] = auto_data.mean(axis=1, numeric_only=True)
        auto_data.columns = auto_data.columns.astype(str)

        # Prepare and format teleop phase data with averages
        teleop_data = team_data[teleop]
        teleop_data.set_index("Team Match Number", inplace=True)
        teleop_data = teleop_data.transpose()
        teleop_data['Averages'] = teleop_data.mean(axis=1, numeric_only=True)
        teleop_data.columns = teleop_data.columns.astype(str)

        # Prepare and format endgame phase data with averages
        endgame_data = team_data[endgame]
        endgame_data.set_index("Team Match Number", inplace=True)
        endgame_data = endgame_data.transpose()
        endgame_data['Averages'] = endgame_data.mean(axis=1, numeric_only=True)
        endgame_data.columns = endgame_data.columns.astype(str)

        # Ensure pit data column names are strings for serialization
        pit_data.columns = pit_data.columns.astype(str)

        # Display phase breakdowns
        st.markdown(":material/clock_loader_10: **Auto**")
        st.dataframe(auto_data)
        st.markdown(":material/clock_loader_80: **Teleop**")
        st.dataframe(teleop_data)
        st.markdown(":material/stop_circle: **Endgame**")
        st.dataframe(endgame_data)
        st.markdown(":material/partner_exchange: **Pit Data**")
        st.dataframe(pit_data)
    
    conn.close()

def sql_to_df(query, conn):
    """Convert SQL query result to pandas DataFrame."""
    import pandas as pd
    return pd.read_sql(query, conn)

def init_session_state():
    """Initialize default session state."""
    default_states = {
        "showTotal": True,
        "showAuto": True,
        "showTeleop": True,
        "showEndgame": True,
    }
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value
