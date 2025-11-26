import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
import logging
from core.session_manager import session_manager


load_dotenv()
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def classify_intent(message, context,session_id):
    normalized = message.lower().strip()
    get_session = session_manager.get_session(session_id)
    state= get_session['state']

    if normalized == "client onboarding":
        return "client_onboard"
    elif normalized == "chatbot services":
        return "service"
    elif normalized == "raise a ticket":
        return "customer_support"
    elif normalized == "track an order":
        return "order_tracking"
    elif state in ['verify_mobile','verify_name','verify_email','password_set','confirm_password']:
        return "client_onboard"

    system_prompt = (
        "You are an intent classifier for Leajlak's chatbot. "
        "Classify the user's latest message into one of four categories: "
        "'general', 'data_fetch', 'order_tracking', or 'customer_support'. "
        "Use the conversation context if provided.\n\n"
        "1. 'general' → Use this if:\n"
        "   - The message is a greeting (hello, hi, good morning),\n"
        "   - The message is asking about chatbot services or Leajlak in general,\n"
        "   - The user asks for order status but without details,\n"
        "   - The user is clarifying a previous answer.\n\n"
        "2. 'data_fetch' → Use this if:\n"
        "   - The message asks about order, shipment, delivery, or logistics requiring DB info,\n"
        "   - The message contains an order/tracking ID,\n"
        "   - It's a follow-up that needs previous context.\n\n"
        "3. 'order_tracking' → Use this if:\n"
        "   - The user wants live tracking or delivery location/time updates.\n\n"
        "   - if the user explicitly ask to track an order\n\n"
        "4. 'customer_support' → Use this if:\n"    
        "   - The user wants to raise a complaint/ticket or contact support.\n\n"
        "Return ONLY one of: 'general', 'data_fetch', 'order_tracking', 'customer_support'."
    )

    payload = {
        "model": "openai/gpt-3.5-turbo",  
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": context or ""},
            {"role": "user", "content": message},
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
        intent = (
            response_json["choices"][0]["message"]["content"]
            .strip()
            .lower()
        )
        logging.info(f"intent: {intent}")
    else:
        intent = "general"

    if intent not in ("general", "data_fetch", "order_tracking", "customer_support"):
        logging.info(f"Unexpected intent '{intent}' classified. Defaulting to 'general'.")
        intent = "general"

    return intent

