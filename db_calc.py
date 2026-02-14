import gspread
import pandas as pd
import sqlite3
from google.oauth2.service_account import Credentials
import competition_config as config

def write_to_db(dataframe, table_name):
    conn = sqlite3.connect("Scouting_Data.db")
    dataframe.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

def perform_calculations():
    apis = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(
        "data_reader_account.json",
        scopes=apis
    )

    gc = gspread.authorize(creds)
    spreadsheet = gc.open(config.GOOGLE_SHEET)
    mdata_worksheet = spreadsheet.worksheet("Data Entry")
    pdata_worksheet = spreadsheet.worksheet("Pit Scouting")
    mdata = mdata_worksheet.get_all_records()
    pdata = pdata_worksheet.get_all_records()
    df = pd.DataFrame(mdata)
    pdata_df = pd.DataFrame(pdata)


    df['Auto Score'] = df[config.AUTO_COLUMN].map(config.AUTO_SCORES).fillna(0)

    df['Teleop Score'] = df[list(config.TELEOP_SCORES.keys())].fillna(0).mul(config.TELEOP_SCORES)


    df['Endgame Score'] = df[config.ENDGAME_COLUMN].map(config.ENDGAME_SCORES).fillna(0)
    df['Total Score'] = df['Auto Score'] + df['Teleop Score'] + df['Endgame Score']

    df = df.sort_values(['Team Number', 'Match Number'])

    df['Team Match Number'] = df.groupby('Team Number').cumcount() + 1

    calc_df = pd.DataFrame()
    calc_df['Team Number'] = df['Team Number'].unique()

    team_counts = (
        df.groupby('Team Number')
        .size()
        .reset_index(name='Matches Played')
    )

    # auto_cols = [
    #     "Auto Score"
    # ]
    # auto_avg = (
    #     df.groupby('Team Number')[auto_cols]
    #     .mean()
    #     .sum(axis=1)
    #     .reset_index(name='Auto Climb AVG')
    # )

    # teleop_cols = ['Teleop Score']
    # teleop_avg = (
    #     df.groupby('Team Number')[teleop_cols]
    #     .mean()
    #     .sum(axis=1)
    #     .reset_index(name='Teleop Score AVG')
    # )



    calc_df = df.groupby('Team Number', as_index=False).agg(**config.CALCULATED_METRICS)

    calc_df = (
        calc_df
        # .merge(auto_avg, on='Team Number')
        .merge(team_counts, on='Team Number')
        # .merge(teleop_avg, on='Team Number')
    )

    eps = 1e-6
    peak = df['Total Score'].max()

    calc_df['Consistency'] = (
            1.0 - (calc_df['Total Score STDEV'] / (peak + eps))
    ).clip(lower=0.0, upper=1.0)


    calc_df = calc_df[config.CALCS_COLUMN_ORDER]

    norm_df = pd.DataFrame()
    norm_df['Team Number'] = calc_df['Team Number']
    
    # Create normalized columns based on config
    for norm_col, source_col in config.RADAR_CHART_CONFIG['columns'].items():
        norm_df[norm_col] = calc_df[source_col] * (100 / calc_df[source_col].max())

    calc_df = calc_df.round(2)

    # tba_df = pd.read_csv("2025necmp2_schedule.csv", header=0)

    write_to_db(norm_df, "Normalized Data")

    # write_to_db(tba_df, "TBA Data")

    write_to_db(calc_df, "Calcs")

    write_to_db(df, "Scouting_Data")

    write_to_db(pdata_df, "Pit Scouting")

perform_calculations()