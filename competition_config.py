# ============================================================================
# COMPETITION SETTINGS
# ============================================================================

# Google Sheet name
GOOGLE_SHEET = "Test Data"

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

# ============================================================================
# NORMALIZATION COLUMNS FOR RADAR CHART
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
