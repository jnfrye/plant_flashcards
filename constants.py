import json

SECONDS_PER_DAY = 86400
NS_PER_SECOND = 1E9

# File paths
CACHE_ROOT = "../plant_flashcards_cache"

# Dynamo DB tables
DYNAMODB_GENERA_TABLE = "plant_flashcards-genera"
DYNAMODB_GUESS_RESULTS_TABLE = "plant_flashcards-guess_results"
DYNAMODB_COMMON_NAMES_TABLE = "plant_flashcards-common_names"

# Google API
GOOGLE_API_KEY = "Google-Images-API-Key"
GOOGLE_SEARCH_ENGINE_CX = "Google-Search-Engine-CX"

with open("config.json", 'r') as f:
    CONFIG = json.load(f)
