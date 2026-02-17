import gspread
import json
import pandas as pd
import sqlite3
import requests
from google.oauth2.service_account import Credentials
import competition_config as config
import streamlit as st
import os

# Write a dataframe to SQLite database
def write_to_db(dataframe, table_name):
    conn = sqlite3.connect("Scouting_Data.db")
    cursor = conn.cursor()
    
    # Lookup tables that should always be replaced, not appended
    lookup_tables = ["TBA Data"]
    
    if table_name in lookup_tables:
        # Replace entire table to avoid schema conflicts
        dataframe.to_sql(table_name, conn, if_exists="replace", index=False)
    elif 'Event Key' in dataframe.columns:
        # Tables with Event Key - handle per-event updates (append/replace per competition)
        try:
            events = pd.read_sql(f"SELECT DISTINCT `Event Key` FROM {table_name}", conn)
            event_exists = dataframe['Event Key'].iloc[0] in events['Event Key'].values
        except:
            # Table doesn't exist yet, so this is a new competition
            event_exists = False
        
        if event_exists:
            # Delete old data for this event and append new
            cursor.execute(f"DELETE FROM {table_name} WHERE `Event Key` = ?", (dataframe['Event Key'].iloc[0],))
            conn.commit()
        
        # Check if table exists and handle schema
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Get existing columns
            cursor.execute(f"PRAGMA table_info(`{table_name}`)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            new_cols = set(dataframe.columns)
            
            # Add missing columns
            missing_cols = new_cols - existing_cols
            for col in missing_cols:
                col_type = "TEXT"  # Default to TEXT for simplicity
                cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{col}` {col_type}")
            conn.commit()
        
        # Now append data
        dataframe.to_sql(table_name, conn, if_exists="append", index=False)
    else:
        # Default: replace
        dataframe.to_sql(table_name, conn, if_exists="replace", index=False)
    
    conn.close()

# Main calculation and data processing function
def perform_calculations():
    for competition in config.EVENTS:
    # Google Sheets API scopes for authentication
        apis = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Authenticate using service account credentials
        # Try Streamlit secrets first (for cloud deployment), then fall back to local file
        try:
            # Use Streamlit secrets (for Streamlit Cloud)
            service_account_info = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(service_account_info, scopes=apis)
        except (FileNotFoundError, KeyError):
            # Fall back to local file (for local development)
            creds = Credentials.from_service_account_file(
                "data_reader_account.json",
                scopes=apis
            )

        # Connect to Google Sheets
        gc = gspread.authorize(creds)
        spreadsheet = gc.open(config.EVENTS[competition]["Google Sheet"])
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
                f"https://www.thebluealliance.com/api/v3/event/{config.EVENTS[competition]['Event Key']}/matches",
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

        norm_df['Event Key'] = config.EVENTS[competition]['Event Key']
        norm_df['Event Name'] = config.EVENTS[competition]['Name']
        calc_df['Event Key'] = config.EVENTS[competition]['Event Key']
        calc_df['Event Name'] = config.EVENTS[competition]['Name']
        df['Event Key'] = config.EVENTS[competition]['Event Key']
        df['Event Name'] = config.EVENTS[competition]['Name']
        pdata_df['Event Key'] = config.EVENTS[competition]['Event Key']
        pdata_df['Event Name'] = config.EVENTS[competition]['Name']

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
            tba_df = tba_df.map(
                lambda value: json.dumps(value) if isinstance(value, (list, dict)) else value
            )
            write_to_db(tba_df, "TBA Data")
        else:
            print("Warning: No TBA data to write.")
# Initial calculation run on script load
perform_calculations()