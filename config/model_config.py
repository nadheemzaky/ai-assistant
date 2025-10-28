import json
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_selected_model():

    """Load the selected model from config.json"""
    if os.path.exists(CONFIG_FILE):
        print('config.json exists')
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("sql", "openai/gpt-3.5-turbo")
    return "openai/gpt-3.5-turbo"


def save_selected_model(model_name):
    """Save the selected model to config.json"""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"sql": model_name}, f, indent=4)

def load_selected_model_summary():

    """Load the selected model from config.json"""
    if os.path.exists(CONFIG_FILE):
        print('config.json exists')
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("summary", "openai/gpt-3.5-turbo")
    return "openai/gpt-3.5-turbo"
def load_selected_model_response():

    """Load the selected model from config.json"""
    if os.path.exists(CONFIG_FILE):
        print('config.json exists')
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("response", "openai/gpt-3.5-turbo")
    return "openai/gpt-3.5-turbo"


