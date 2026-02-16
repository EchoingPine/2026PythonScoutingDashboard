import gspread
import json
import pandas as pd
import sqlite3
import requests
from google.oauth2.service_account import Credentials
import competition_config as config

# Write a dataframe to SQLite database
def write_to_db(dataframe, table_name):
    """Store a pandas dataframe as a table in the local SQLite database."""
    conn = sqlite3.connect("Scouting_Data.db")
    dataframe.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

# Main calculation and data processing function
def perform_calculations():
    """Fetch match data from Google Sheets and store in database.
    
    This function:
    1. Authenticates with Google Sheets API
    2. Fetches raw match and pit scouting data
    3. Calculates scoring metrics
    4. Computes averages and other metrics for each team
    6. Stores results in SQLite database
    """
    # Google Sheets API scopes for authentication
    apis = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Authenticate using service account key file
    creds = Credentials.from_service_account_file(
        "data_reader_account.json",
        scopes=apis
    )

    # Connect to Google Sheets
    gc = gspread.authorize(creds)
    spreadsheet = gc.open(config.GOOGLE_SHEET)
    mdata_worksheet = spreadsheet.worksheet("Data Entry")
    pdata_worksheet = spreadsheet.worksheet("Pit Scouting")
    # Get all match and pit scouting data as dictionaries
    mdata = mdata_worksheet.get_all_records()
    pdata = pdata_worksheet.get_all_records()
    # Convert to pandas dataframes
    df = pd.DataFrame(mdata)
    pdata_df = pd.DataFrame(pdata)

    # Initialize TBA API client
    try:
        headers = {"X-TBA-Auth-Key": config.TBA_API_KEY}
        response = requests.get(
            f"https://www.thebluealliance.com/api/v3/event/{config.EVENT_KEY}/matches",
            headers=headers
        )
        response.raise_for_status()
        tba_comp_data = response.json()
        tba_df = pd.json_normalize(tba_comp_data)
    except Exception as e:
        print(f"Warning: Failed to fetch TBA data: {e}")
        # Create empty TBA dataframe if API fails
        tba_df = pd.DataFrame()
    
    # ========================================================================
    # SCORING CALCULATIONS
    # ========================================================================

    # Calculate Auto score
    df['Auto Score'] = df[config.AUTO_COLUMN].map(config.AUTO_SCORES).fillna(0)

    # Calculate Teleop score
    df['Teleop Score'] = df[list(config.TELEOP_SCORES.keys())].fillna(0).mul(config.TELEOP_SCORES)

    # Calculate Endgame score
    df['Endgame Score'] = df[config.ENDGAME_COLUMN].map(config.ENDGAME_SCORES).fillna(0)
    # Sum all scores to get Total Score
    df['Total Score'] = df['Auto Score'] + df['Teleop Score'] + df['Endgame Score']

    # Sort by team and match number
    df = df.sort_values(['Team Number', 'Match Number'])

    # Find team specific match number
    df['Team Match Number'] = df.groupby('Team Number').cumcount() + 1

    # ========================================================================
    # METRICS CALCULATION
    # ========================================================================

    # Initialize calculation dataframe with unique teams
    calc_df = pd.DataFrame()
    calc_df['Team Number'] = df['Team Number'].unique()

    # Count matches played per team
    team_counts = (
        df.groupby('Team Number')
        .size()
        .reset_index(name='Matches Played')
    )

    # Calculate team averages and statistical metrics using config definitions
    calc_df = df.groupby('Team Number', as_index=False).agg(**config.CALCULATED_METRICS)

    # Merge with match count
    calc_df = (
        calc_df
        .merge(team_counts, on='Team Number')
    )

    # ========================================================================
    # CONSISTENCY METRIC
    # ========================================================================

    # Uses Peekorobo consistency formula to calculate a score based on standard deviation of total scores
    # High consistency means a low standard deviation which results in a score closer to 1.0
    eps = 1e-6  # Small value to prevent division by zero
    peak = df['Total Score'].max()

    calc_df['Consistency'] = (
            1.0 - (calc_df['Total Score STDEV'] / (peak + eps))
    ).clip(lower=0.0, upper=1.0)  # Clamp between 0 and 1

    # Reorder columns according to config
    calc_df = calc_df[config.CALCS_COLUMN_ORDER]

    # ========================================================================
    # RADAR CHART NORMALIZATION
    # ========================================================================

    # Create normalized dataframe on a 0-100 scale for radar chart visualization
    norm_df = pd.DataFrame()
    norm_df['Team Number'] = calc_df['Team Number']
    
    # Normalize each metric to 0-100 scale based on max value
    for norm_col, source_col in config.RADAR_CHART_CONFIG['columns'].items():
        norm_df[norm_col] = calc_df[source_col] * (100 / calc_df[source_col].max())

    # Round calculated metrics to 2 decimal places
    calc_df = calc_df.round(2)

    # ========================================================================
    # DATABASE STORAGE
    # ========================================================================

    # Write all  data to SQLite database
    write_to_db(norm_df, "Normalized Data")
    write_to_db(calc_df, "Calcs")
    write_to_db(df, "Scouting_Data")
    write_to_db(pdata_df, "Pit Scouting")
    if not tba_df.empty:
        # Serialize list/dict columns so SQLite can store them
        tba_df = tba_df.applymap(
            lambda value: json.dumps(value) if isinstance(value, (list, dict)) else value
        )
        write_to_db(tba_df, "TBA Data")
    else:
        print("Warning: No TBA data to write.")
# Initial calculation run on script load
perform_calculations()