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

def classify_intent(message,context):
    system_prompt = (
        "You are an intent classifier for Leajlak's chatbot. "
        "Classify the user's latest message into one of two categories:"
        "1. 'general' → Use this if:"
        "   - The message is a greeting (e.g., hello, hi, good morning)."
        "   - The message is asking about Leajlak or its services in general (e.g., what is Leajlak, how does Leajlak work)." \
        "   - If the user asks : 'order status / what is the order status     "
        "2. 'data_fetch' → Use this if:  "
        "   - The message asks about order, shipment, delivery, tracking, logistics, or anything requiring database information.  "
        "   - The message contains numeric IDs (like a 7-digit number such as 1823361).  "
        "   - The message is a follow-up question (e.g., 'who?', 'where?', 'when?', 'what about that order?') that depends on previous context.    "
        "Instructions:  "
        "- Always check the provided context of the conversation. If the latest message is vague but relates to earlier data (like follow-ups), classify it as 'data_fetch'.  "
        "- Return only 'general' or 'data_fetch'. No explanations, no extra words."
    )

    payload = {
        "model": "qwen/qwen3-next-80b-a3b-instruct",  # or preferred model supported by OpenRouter
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},   
            {"role":"user" , "content" : context}
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


