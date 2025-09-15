import requests
import logging
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

logging.basicConfig(
    filename='logs/app.log',          # Log file path
    level=logging.INFO,          # Log messages at INFO level and above
    format='%(asctime)s %(levelname)s: %(message)s',  # Log message format including timestamp
    datefmt='%Y-%m-%d %H:%M:%S'
)

def classify_intent(message):
    system_prompt = (
        "Classify the following user message into one of two categories: "
        "'general' = for questions that includes greetings or enquiry about chatbot's service."
        "'data_fetch'= for questions asking about anything else."
        "Return only the category name."
    )

    payload = {
        "model": "meta-llama/llama-4-maverick",  # or preferred model supported by OpenRouter
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "max_tokens": 5,
        "temperature": 0.0
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers)
    response_json = response.json()
    logging.info(f"Intent classification response: {response_json}")
    if "choices" in response_json and response_json["choices"]:
        logging.info('intent classified')
        intent = response_json["choices"][0]["message"]["content"].strip().lower()
        logging.info(f'{intent}')
    else:
        intent = "general"  # default fallback
    # Defensive assignment:
    if intent not in ("general", "data_fetch"):
        logging.info(f"Unexpected intent '{intent}' classified. Defaulting to 'general'.")
        intent = "general"
    return intent


