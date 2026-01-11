import gspread
import pandas as pd
import sqlite3
from google.oauth2.service_account import Credentials

googleSheet = "Test Data"

endgame_scores = {
    "L3 Climb": 30,
    "L2 Climb": 20,
    "L1 Climb": 10,
    "Nothing": 0
}

auto_scores = {
    "Yes": 15,
    "No": 0
}

teleop_scores = {
    "Fuel": 1,
}

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
    spreadsheet = gc.open(googleSheet)
    mdata_worksheet = spreadsheet.worksheet("Data Entry")
    # pdata_worksheet = spreadsheet.worksheet("Pit Scouting")
    mdata = mdata_worksheet.get_all_records()
    # pdata = pdata_worksheet.get_all_records()
    df = pd.DataFrame(mdata)
    # pdata_df = pd.DataFrame(pdata)

    print(df.columns)


    df['Auto Score'] = df['Auto Climb'].map(auto_scores).fillna(0)

    df['Teleop Score'] = df[list(teleop_scores.keys())].fillna(0).mul(teleop_scores)


    df['Endgame Score'] = df['Endgame'].map(endgame_scores).fillna(0)
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



    calc_df = df.groupby('Team Number', as_index=False).agg(
        **{
            'Auto Score AVG': ('Auto Score', 'mean'),
            'Teleop Score AVG': ('Teleop Score', 'mean'),
            'Climb Score AVG': ('Endgame Score', 'mean'),
            'Total Score AVG': ('Total Score', 'mean'),
            'Total Score STDEV': ('Total Score', 'std'),
        }
    )

    # calc_df = (
    #     calc_df
    #     .merge(auto_avg, on='Team Number')
    #     .merge(team_counts, on='Team Number')
    #     .merge(teleop_avg, on='Team Number')
    # )

    eps = 1e-6
    peak = df['Total Score'].max()

    calc_df['Consistency'] = (
            1.0 - (calc_df['Total Score STDEV'] / (peak + eps))
    ).clip(lower=0.0, upper=1.0)


    calc_df = calc_df[
        ['Team Number', 'Auto Score AVG', 'Teleop Score AVG', 'Climb Score AVG', 'Total Score AVG', 'Total Score STDEV', 'Consistency']
    ]

    norm_df = pd.DataFrame()
    norm_df['Team Number'] = calc_df['Team Number']
    norm_df['Normalized Auto'] = calc_df['Auto Score AVG'] * (100 / calc_df['Auto Score AVG'].max())
    norm_df['Normalized Teleop'] = calc_df['Teleop Score AVG'] * (100 / calc_df['Teleop Score AVG'].max())
    norm_df['Normalized Endgame'] = calc_df['Climb Score AVG'] * (100 / calc_df['Climb Score AVG'].max())
    norm_df['Normalized Total'] = calc_df['Total Score AVG'] * (100 / calc_df['Total Score AVG'].max())

    calc_df = calc_df.round(2)

    # tba_df = pd.read_csv("2025necmp2_schedule.csv", header=0)

    write_to_db(norm_df, "Normalized Data")

    # write_to_db(tba_df, "TBA Data")

    write_to_db(calc_df, "Calcs")

    write_to_db(df, "Scouting_Data")

    # write_to_db(pdata_df, "Pit Scouting")

perform_calculations()