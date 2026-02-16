import streamlit as st

st.markdown("""
# Configuration Guide

## Quick Start

All competition-specific settings are in **`competition_config.py`**. Edit this file to set up for a new competition.

## Configuration Sections

### 1. Competition Settings

```python
GOOGLE_SHEET = "Test Data"
```

Change this to match your Google Sheet name for the competition.

### 2. Scoring Rules

#### Endgame Scoring
Define the point values for different actions:

```python
ENDGAME_SCORES = {
    "L3 Climb": 30,
    "L2 Climb": 20,
    "L1 Climb": 10,
    "Nothing": 0
}
```

#### Auto Scoring
Define autonomous scoring:

```python
AUTO_SCORES = {
    "Yes": 15,
    "No": 0
}
```

#### Teleop Scoring
Define teleoperated scoring:

```python
TELEOP_SCORES = {
    "Fuel": 1  # Add more scoring elements
}
```

### 3. Column Configurations

Specify which columns appear in different views:

```python
SINGLE_TEAM_COLUMNS = {
    "auto": ['Auto Climb'],  # Columns for auto phase
    "teleop": ['Fuel'],            # Columns for teleop phase
    "endgame": ['Endgame Score']            # Columns for endgame phase
}
```

Set the column names used for scoring calculations:

```python
ENDGAME_COLUMN = "Endgame"     # Column name in your data sheet
AUTO_COLUMN = "Auto Climb"      # Column name in your data sheet
```

### 4. Calculated Metrics

Define which stats are calculated for each team:

```python
CALCULATED_METRICS = {
    'Auto Score AVG': ('Auto Score', 'mean'),
    'Teleop Score AVG': ('Teleop Score', 'mean'),
    'Climb Score AVG': ('Endgame Score', 'mean'),
    'Total Score AVG': ('Total Score', 'mean'),
    'Total Score STDEV': ('Total Score', 'std'),
}
```

### 5. Radar Chart

Define what appears in the radar chart:

```python
RADAR_CHART_CONFIG = {
    'columns': {
        'Normalized Auto': 'Auto Score AVG',
        'Normalized Teleop': 'Teleop Score AVG',
        'Normalized Endgame': 'Climb Score AVG',
        'Normalized Total': 'Total Score AVG',
    },
    'labels': {
        'Normalized Auto': 'Auto Score',
        'Normalized Teleop': 'Teleop Score',
        'Normalized Endgame': 'Climb Score',
        'Normalized Total': 'Total Score',
    }
}
```

## Example: Switching to a New Competition

Let's say the new competition has:
- Different scoring zones (Speaker, Amp, Trap)
- Two-level climb (High, Low)
- Different auto actions

### Step 1: Update Scoring Rules

```python
ENDGAME_SCORES = {
    "High Climb": 25,
    "Low Climb": 10,
    "Park": 5,
    "Nothing": 0
}

AUTO_SCORES = {
    "Left Zone": 5,
    "No": 0
}

TELEOP_SCORES = {
    "Speaker": 2,
    "Amp": 1,
    "Trap": 5,
}
```

### Step 2: Update Column Names

```python
SINGLE_TEAM_COLUMNS = {
    "auto": ['Auto Leave', 'Auto Speaker'],
    "teleop": ['Speaker', 'Amp', 'Trap'],
    "endgame": ['Endgame Score', 'Climb Type']
}

ENDGAME_COLUMN = "Climb Type"
AUTO_COLUMN = "Auto Leave"
```

### Step 3: Save and Refresh

1. Save `competition_config.py`
2. In the dashboard, click "Refresh Values" in the sidebar
3. All calculations and displays will update automatically

## Make sure

- **Column Names**: Make sure column names in the config match exactly with your Google Sheet column headers
- **Point Values**: Make sure point values match the official game manual
""")