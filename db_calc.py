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

    if 'Event Key' in dataframe.columns:
        dataframe = dataframe.drop_duplicates()

        try:
            cursor.execute(
                f'DELETE FROM "{table_name}" WHERE "Event Key" = ?',
                (dataframe['Event Key'].iloc[0],)
            )
            conn.commit()
        except Exception as e:
            print(f"Warning {table_name}: {e}")

    dataframe.to_sql(table_name, conn, if_exists='append', index=False)
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
        norm_data = {'Team Number': calc_df['Team Number']}
        
        # Normalize each metric to 0-100 scale based on max value (with division by zero protection)
        for norm_col, source_col in config.RADAR_CHART_CONFIG['columns'].items():
            max_val = calc_df[source_col].max()
            if max_val > 0:
                norm_data[norm_col] = calc_df[source_col] * (100 / max_val)
            else:
                norm_data[norm_col] = 0
        
        norm_df = pd.DataFrame(norm_data)

        # Round calculated metrics to 2 decimal places
        calc_df = calc_df.round(2)

        # Add Event Key and Event Name to all dataframes efficiently
        event_key = config.EVENTS[competition]['Event Key']
        event_name = config.EVENTS[competition]['Name']
        competition_week = config.EVENTS[competition]['Competition Week']
        
        norm_df['Event Key'] = event_key
        norm_df['Event Name'] = event_name
        norm_df['Competition Week'] = competition_week
        calc_df['Event Key'] = event_key
        calc_df['Event Name'] = event_name
        calc_df['Competition Week'] = competition_week
        df['Event Key'] = event_key
        df['Event Name'] = event_name
        df['Competition Week'] = competition_week
        pdata_df['Event Key'] = event_key
        pdata_df['Event Name'] = event_name
        pdata_df['Competition Week'] = competition_week

        # ========================================================================
        # DATABASE STORAGE
        # ========================================================================

        # Write all data to SQLite database
        write_to_db(norm_df, "Normalized Data")
        write_to_db(calc_df, "Calcs")
        write_to_db(df, "Scouting_Data")
        write_to_db(pdata_df, "Pit Scouting")
        if not tba_df.empty:
            # Drop duplicate rows BEFORE serialization (using key column to identify unique matches)
            # TBA API typically has 'key' column that uniquely identifies each match
            if 'key' in tba_df.columns:
                tba_df = tba_df.drop_duplicates(subset=['key'])
            else:
                tba_df = tba_df.drop_duplicates()
            
            # Serialize list/dict columns so SQLite can store them
            tba_df = tba_df.map(
                lambda value: json.dumps(value) if isinstance(value, (list, dict)) else value
            )
            # Add Event Key and Event Name to TBA data
            tba_df = tba_df.assign(**{'Event Key': event_key, 'Event Name': event_name})
            write_to_db(tba_df, "TBA Data")
        else:
            print("Warning: No TBA data to write.")

    all_df = pd.read_sql(
        'SELECT * FROM "Scouting_Data" WHERE "Event Name" != "All Competitions"',
        sqlite3.connect("Scouting_Data.db")
    )
    all_df = all_df.sort_values(['Team Number', 'Competition Week', 'Match Number'])
    all_df['Team Match Number'] = all_df.groupby('Team Number').cumcount() + 1
    
    all_calc_df = pd.DataFrame()
    all_calc_df['Team Number'] = all_df['Team Number'].unique()

    # Count matches played per team
    all_team_counts = (
        all_df.groupby('Team Number')
        .size()
        .reset_index(name='Team Match Number')
    )

    # Calculate team averages and statistical metrics using config definitions
    all_calc_df = all_df.groupby('Team Number', as_index=False).agg(**config.CALCULATED_METRICS)

    # Merge with match count
    all_calc_df = (
        all_calc_df
        .merge(all_team_counts, on='Team Number')
    )

    eps = 1e-6  # Small value to prevent division by zero
    all_peak = all_df['Total Score'].max()

    all_calc_df['Consistency'] = (
            1.0 - (all_calc_df['Total Score STDEV'] / (all_peak + eps))
    ).clip(lower=0.0, upper=1.0)  # Clamp between 0 and 1

    # Reorder columns according to config
    all_calc_df = all_calc_df[config.CALCS_COLUMN_ORDER]

    all_calc_df = all_calc_df.round(2)

    all_norm_data = {'Team Number': all_calc_df['Team Number']}
        
    # Normalize each metric to 0-100 scale based on max value (with division by zero protection)
    for norm_col, source_col in config.RADAR_CHART_CONFIG['columns'].items():
        max_val = all_calc_df[source_col].max()
        if max_val > 0:
            all_norm_data[norm_col] = all_calc_df[source_col] * (100 / max_val)
        else:
            all_norm_data[norm_col] = 0
    
    all_norm_df = pd.DataFrame(all_norm_data)

    # Round calculated metrics to 2 decimal places
    all_norm_df = all_norm_df.round(2)

    all_norm_df['Event Key'] = "All Competitions"
    all_norm_df['Event Name'] = "All Competitions"
    all_norm_df['Competition Week'] = "All Weeks"
    all_calc_df['Event Key'] = "All Competitions"
    all_calc_df['Event Name'] = "All Competitions"
    all_calc_df['Competition Week'] = "All Weeks"
    all_df['Event Key'] = "All Competitions"
    all_df['Event Name'] = "All Competitions"
    all_df['Competition Week'] = "All Weeks"
    pdata_df['Event Key'] = "All Competitions"
    pdata_df['Event Name'] = "All Competitions"
    pdata_df['Competition Week'] = "All Weeks"

    write_to_db(all_norm_df, "Normalized Data")
    write_to_db(all_calc_df, "Calcs")
    write_to_db(all_df, "Scouting_Data")
    write_to_db(pdata_df, "Pit Scouting")



# Initial calculation run on script load
perform_calculations()