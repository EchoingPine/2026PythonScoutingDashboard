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

    # Check if table exists and handle schema changes
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    table_exists = cursor.fetchone() is not None
    
    if table_exists:
        # Get existing columns
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        existing_cols = {row[1] for row in cursor.fetchall()}
        new_cols = set(dataframe.columns)
        
        # Add missing columns
        missing_cols = new_cols - existing_cols
        for col in missing_cols:
            cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" REAL')
        conn.commit()

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
        # RAW SCORE CALCULATIONS (Exponential Moving Average)
        # ========================================================================

        # Calculate rolling RAW scores for each team
        df['Auto RAW'] = 0.0
        df['Teleop RAW'] = 0.0
        df['Endgame RAW'] = 0.0
        df['Total RAW'] = 0.0

        for team_num in df['Team Number'].unique():
            team_matches = df[df['Team Number'] == team_num].index
            
            auto_raw = 0.0
            teleop_raw = 0.0
            endgame_raw = 0.0
            
            for idx in team_matches:
                actual_auto = df.loc[idx, 'Auto Score']
                actual_teleop = df.loc[idx, 'Teleop Score']
                actual_endgame = df.loc[idx, 'Endgame Score']
                
                # Apply EMA formula: RAW_new = RAW_old + K * (actual - RAW_old)
                auto_raw = auto_raw + config.RAW_K * (actual_auto - auto_raw)
                teleop_raw = teleop_raw + config.RAW_K * (actual_teleop - teleop_raw)
                endgame_raw = endgame_raw + config.RAW_K * (actual_endgame - endgame_raw)
                
                df.loc[idx, 'Auto RAW'] = auto_raw
                df.loc[idx, 'Teleop RAW'] = teleop_raw
                df.loc[idx, 'Endgame RAW'] = endgame_raw
                df.loc[idx, 'Total RAW'] = auto_raw + teleop_raw + endgame_raw

        # ========================================================================
        # DOMINANCE CALCULATION
        # ========================================================================

        df['Dominance'] = None
        
        if not tba_df.empty and 'match_number' in tba_df.columns:
            # Parse TBA data for match scores
            tba_match_data = []
            for _, tba_row in tba_df.iterrows():
                if tba_row.get('comp_level') != 'qm':
                    continue
                    
                match_num = tba_row.get('match_number')
                
                # Parse team keys and scores
                try:
                    blue_teams = tba_row.get('alliances.blue.team_keys', [])
                    red_teams = tba_row.get('alliances.red.team_keys', [])
                    blue_score = tba_row.get('alliances.blue.score', 0)
                    red_score = tba_row.get('alliances.red.score', 0)
                    
                    # Handle JSON-serialized data
                    if isinstance(blue_teams, str):
                        blue_teams = json.loads(blue_teams)
                    if isinstance(red_teams, str):
                        red_teams = json.loads(red_teams)
                    
                    # Extract team numbers from "frcXXXX" format
                    blue_team_nums = [int(t.replace('frc', '')) for t in blue_teams if isinstance(t, str) and t.startswith('frc')]
                    red_team_nums = [int(t.replace('frc', '')) for t in red_teams if isinstance(t, str) and t.startswith('frc')]
                    
                    # Add match data for each team
                    for team_num in blue_team_nums:
                        tba_match_data.append({
                            'Match Number': match_num,
                            'Team Number': team_num,
                            'Alliance': 'blue',
                            'Opponent Score': red_score,
                            'Team Count': len(red_team_nums) if red_team_nums else 3
                        })
                    for team_num in red_team_nums:
                        tba_match_data.append({
                            'Match Number': match_num,
                            'Team Number': team_num,
                            'Alliance': 'red',
                            'Opponent Score': blue_score,
                            'Team Count': len(blue_team_nums) if blue_team_nums else 3
                        })
                except Exception as e:
                    continue
            
            if tba_match_data:
                tba_match_df = pd.DataFrame(tba_match_data)
                
                # Merge with scouting data
                df = df.merge(
                    tba_match_df[['Match Number', 'Team Number', 'Opponent Score', 'Team Count']],
                    on=['Match Number', 'Team Number'],
                    how='left'
                )
                
                # Calculate dominance for matches with TBA data
                eps = 1e-6
                mask = df['Opponent Score'].notna()
                
                df.loc[mask, 'margin'] = df.loc[mask, 'Total Score'] - (df.loc[mask, 'Opponent Score'] / df.loc[mask, 'Team Count'])
                df.loc[mask, 'scaled_margin'] = df.loc[mask, 'margin'] / (df.loc[mask, 'Opponent Score'] + eps)
                df.loc[mask, 'norm_margin'] = (df.loc[mask, 'scaled_margin'] + 1) / 1.3
                df.loc[mask, 'Dominance'] = df.loc[mask, 'norm_margin'].clip(0.0, 1.0)
                
                # Clean up temporary columns
                df.drop(columns=['margin', 'scaled_margin', 'norm_margin', 'Opponent Score', 'Team Count'], inplace=True, errors='ignore')

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

        # Extract final RAW values for each team (from their last match)
        final_raw = df.loc[df.groupby('Team Number')['Team Match Number'].idxmax(), 
                           ['Team Number', 'Auto RAW', 'Teleop RAW', 'Endgame RAW', 'Total RAW']]
        calc_df = calc_df.merge(final_raw, on='Team Number', how='left')

        # Calculate mean Dominance for each team
        df['Dominance'] = pd.to_numeric(df['Dominance'], errors='coerce')
        dominance_avg = df.groupby('Team Number', as_index=False)['Dominance'].mean()
        dominance_avg.rename(columns={'Dominance': 'Dominance AVG'}, inplace=True)
        calc_df = calc_df.merge(dominance_avg, on='Team Number', how='left')

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

        # Calculate Confidence and ACE
        calc_df['Confidence'] = calc_df['Consistency'] * 0.5 + calc_df['Dominance AVG'].fillna(0) * 0.5
        calc_df['ACE'] = calc_df['Total RAW'] * calc_df['Confidence']

        # Add Event Key and Event Name before reordering
        event_key = config.EVENTS[competition]['Event Key']
        event_name = config.EVENTS[competition]['Name']
        competition_week = config.EVENTS[competition]['Competition Week']
        
        calc_df['Event Key'] = event_key
        calc_df['Event Name'] = event_name
        calc_df['Competition Week'] = competition_week

        # Round calculated metrics to 2 decimal places
        calc_df = calc_df.round(2)

        # Calculate rankings (higher score = lower rank number, so use ascending=False)
        calc_df['ACE Rank'] = calc_df['ACE'].rank(method='min', ascending=False).astype(int)
        calc_df['RAW Rank'] = calc_df['Total RAW'].rank(method='min', ascending=False).astype(int)
        calc_df['Confidence Rank'] = calc_df['Confidence'].rank(method='min', ascending=False).astype(int)
        calc_df['Score Rank'] = calc_df['Total Score AVG'].rank(method='min', ascending=False).astype(int)

        # Reorder columns according to config (now rankings are included)
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

        # Add Event Key and Event Name to norm_df and df
        norm_df['Event Key'] = event_key
        norm_df['Event Name'] = event_name
        norm_df['Competition Week'] = competition_week
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

    # ========================================================================
    # RAW SCORE CALCULATIONS FOR ALL COMPETITIONS
    # ========================================================================

    all_df['Auto RAW'] = 0.0
    all_df['Teleop RAW'] = 0.0
    all_df['Endgame RAW'] = 0.0
    all_df['Total RAW'] = 0.0

    for team_num in all_df['Team Number'].unique():
        team_matches = all_df[all_df['Team Number'] == team_num].index
        
        auto_raw = 0.0
        teleop_raw = 0.0
        endgame_raw = 0.0
        
        for idx in team_matches:
            actual_auto = all_df.loc[idx, 'Auto Score']
            actual_teleop = all_df.loc[idx, 'Teleop Score']
            actual_endgame = all_df.loc[idx, 'Endgame Score']
            
            # Apply EMA formula: RAW_new = RAW_old + K * (actual - RAW_old)
            auto_raw = auto_raw + config.RAW_K * (actual_auto - auto_raw)
            teleop_raw = teleop_raw + config.RAW_K * (actual_teleop - teleop_raw)
            endgame_raw = endgame_raw + config.RAW_K * (actual_endgame - endgame_raw)
            
            all_df.loc[idx, 'Auto RAW'] = auto_raw
            all_df.loc[idx, 'Teleop RAW'] = teleop_raw
            all_df.loc[idx, 'Endgame RAW'] = endgame_raw
            all_df.loc[idx, 'Total RAW'] = auto_raw + teleop_raw + endgame_raw
    
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

    # Extract final RAW values for each team (from their last match)
    all_final_raw = all_df.loc[all_df.groupby('Team Number')['Team Match Number'].idxmax(), 
                               ['Team Number', 'Auto RAW', 'Teleop RAW', 'Endgame RAW', 'Total RAW']]
    all_calc_df = all_calc_df.merge(all_final_raw, on='Team Number', how='left')

    # Calculate mean Dominance for each team (if column exists)
    if 'Dominance' in all_df.columns:
        # Convert Dominance to numeric, handling any non-numeric values
        all_df['Dominance'] = pd.to_numeric(all_df['Dominance'], errors='coerce')
        all_dominance_avg = all_df.groupby('Team Number', as_index=False)['Dominance'].mean()
        all_dominance_avg.rename(columns={'Dominance': 'Dominance AVG'}, inplace=True)
        all_calc_df = all_calc_df.merge(all_dominance_avg, on='Team Number', how='left')

    eps = 1e-6  # Small value to prevent division by zero
    all_peak = all_df['Total Score'].max()

    all_calc_df['Consistency'] = (
            1.0 - (all_calc_df['Total Score STDEV'] / (all_peak + eps))
    ).clip(lower=0.0, upper=1.0)  # Clamp between 0 and 1

    # Calculate Confidence and ACE for all competitions
    all_calc_df['Confidence'] = all_calc_df['Consistency'] * 0.5 + all_calc_df['Dominance AVG'].fillna(0) * 0.5
    all_calc_df['ACE'] = all_calc_df['Total RAW'] * all_calc_df['Confidence']

    # Add Event Key and Event Name before reordering
    all_calc_df['Event Key'] = "All Competitions"
    all_calc_df['Event Name'] = "All Competitions"
    all_calc_df['Competition Week'] = "All Weeks"

    # Round calculated metrics to 2 decimal places
    all_calc_df = all_calc_df.round(2)

    # Calculate rankings for all competitions
    all_calc_df['ACE Rank'] = all_calc_df['ACE'].rank(method='min', ascending=False).astype(int)
    all_calc_df['RAW Rank'] = all_calc_df['Total RAW'].rank(method='min', ascending=False).astype(int)
    all_calc_df['Confidence Rank'] = all_calc_df['Confidence'].rank(method='min', ascending=False).astype(int)
    all_calc_df['Score Rank'] = all_calc_df['Total Score AVG'].rank(method='min', ascending=False).astype(int)

    # Reorder columns according to config (now rankings are included)
    all_calc_df = all_calc_df[config.CALCS_COLUMN_ORDER]

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

    # Add Event Key and Event Name to other dataframes
    all_norm_df['Event Key'] = "All Competitions"
    all_norm_df['Event Name'] = "All Competitions"
    all_norm_df['Competition Week'] = "All Weeks"
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