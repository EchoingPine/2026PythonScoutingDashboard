# ============================================================================
# STREAMLIT CONFIGURATIONS
# ============================================================================

import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

VIEW_OPTIONS = ["Single Team", 
                "Compare", 
                "Averages", 
                "Match Reference", 
                "Bubble Chart", 
                "Radar Chart",
                "Live Comp"]

# ============================================================================
# COMPETITION SETTINGS
# ============================================================================


EVENTS = {
    '2025necmp2': {
        "Name": "2025 New England Championship",
        "Event Key": "2025necmp2",
        "Google Sheet": "Test Data",
        "Competition Week": "Week 6"
    },
    '2025mawor': {
        "Name": "2025 WPI Regional",
        "Event Key": "2025mawor",
        "Google Sheet": "WPI Test Data",
        "Competition Week": "Week 4"
    }
}

# Google Sheet name
GOOGLE_SHEET = "Test Data"

# TBA API key - use secrets for security
try:
    TBA_API_KEY = st.secrets.get("TBA_API_KEY", os.environ.get("TBA_API_KEY", ""))
except:
    TBA_API_KEY = os.environ.get("TBA_API_KEY", "")

EVENT_KEY = "2025necmp2"

# Nexus API key - use secrets for security
try:
    NEXUS_API_KEY = st.secrets.get("NEXUS_API_KEY", os.environ.get("NEXUS_API_KEY", ""))
except:
    NEXUS_API_KEY = os.environ.get("NEXUS_API_KEY", "")

NEXUS_URL = "https://frc.nexus/api/v1/event/" + EVENT_KEY
NEXUS_HEADERS = {"Nexus-Api-Key": NEXUS_API_KEY}

# ============================================================================
# SCORING RULES
# ============================================================================

# Endgame scoring options and their point values
ENDGAME_SCORES = {
    "L3 Climb": 30,
    "L2 Climb": 20,
    "L1 Climb": 10,
    "Nothing": 0
}

# Auto scoring options and their point values
AUTO_SCORES = {
    "Yes": 15,
    "No": 0
}

# Teleop scoring - column name and point value per action
TELEOP_SCORES = {
    "Fuel": 1,
}

# ============================================================================
# COLUMN CONFIGURATIONS
# ============================================================================

# Columns to display in "Single Team" view by game phase
SINGLE_TEAM_COLUMNS = {
    "auto": ['Auto Climb'],
    "teleop": ['Fuel'],
    "endgame": ['Endgame Score']
}

# Column used for endgame scoring in the data
ENDGAME_COLUMN = "Endgame"

# Column used for auto scoring in the data
AUTO_COLUMN = "Auto Climb"

# ============================================================================
# CALCULATED METRICS
# ============================================================================

# Define which aggregations to calculate for team averages
CALCULATED_METRICS = {
    'Auto Score AVG': ('Auto Score', 'mean'),
    'Teleop Score AVG': ('Teleop Score', 'mean'),
    'Climb Score AVG': ('Endgame Score', 'mean'),
    'Total Score AVG': ('Total Score', 'mean'),
    'Total Score STDEV': ('Total Score', 'std'),
}

# Order of columns in the Calcs table
CALCS_COLUMN_ORDER = [
    'Team Number', 
    'Auto Score AVG', 
    'Teleop Score AVG', 
    'Climb Score AVG', 
    'Total Score AVG', 
    'Total Score STDEV', 
    'Consistency'
]

# Columns to apply background gradient coloring for each scoring phase
AUTO_AVG_COLUMNS = ['Auto Score AVG']
TELEOP_AVG_COLUMNS = ['Teleop Score AVG']
ENDGAME_AVG_COLUMNS = ['Climb Score AVG']
TOTAL_AVG_COLUMNS = ['Total Score AVG', 'Total Score STDEV', 'Consistency']
SCORING_AVG_COLUMNS = ['Auto Score AVG', 'Teleop Score AVG', 'Climb Score AVG', 'Total Score AVG', 'Total Score STDEV', 'Consistency']

# Color schemes for background gradients in the Averages section
AUTO_COLORS = ["#252525", "#010014"]
TELEOP_COLORS = ["#252525", "#301500"]
ENDGAME_COLORS = ["#252525", "#302d00"]
TOTAL_COLORS = ["#252525", "#003003"]

# Alternative pastel set (if you prefer softer colors):
GRAPH_LINE_COLORS_PASTEL = {
    'Line Color 1': '#F4B40B',
    'Line Color 2': '#FF6B35',
    'Line Color 3': '#FF006E',
    'Line Color 4': '#00CED1',
}

BACKGROUND_COLOR = "#190202"
TEXT_COLOR = "#F4B40B"

# ============================================================================
# COLUMNS FOR RADAR CHART
# ============================================================================

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