import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
import logging

load_dotenv()
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def classify_intent(message, context):
    system_prompt=("return 'order_tracking' only. " )
    
    '''system_prompt = (
            "You are an intent classifier for Leajlak's chatbot. "
            "Classify the user's latest message into one of four categories:"
            "1. 'general' → Use this if:"
            "   - The message is a greeting (e.g., hello, hi, good morning)."
            "   - The message is asking about Leajlak or its services in general (e.g., what is Leajlak, how does Leajlak work)."
            "   - If the user asks: 'order status' or 'what is the order status' without specifics."
            "   - If the user asks a question to clarify the answer provided by the chatbot."
            "2. 'data_fetch' → Use this if:"
            "   - The message asks about order, shipment, delivery, tracking, logistics, or anything requiring database information."
            "   - The message contains numeric IDs (like a 7-digit number such as 1823361)."
            "   - If the user has provided the details that was first missing from the context about order id."
            "   - The message is a follow-up question (e.g., 'who?', 'where?', 'when?', 'what about that order?') that depends on previous context."
            "3. 'order_tracking' → Use this if:"
            "   - The message specifically requests real-time order tracking updates (e.g., 'track my order', 'where is my order now', 'show live tracking')."
            "   - The user provides a tracking number or explicitly asks for delivery location/time updates."
            "4. 'customer_support' → Use this if:"
            "   - The message asks to raise a complaint, create a ticket, or contact customer service (e.g., 'I want to report an issue', 'open a support ticket', 'contact support')."
            "   - The user mentions issues, malfunctions, complaints, or refund requests needing human support."
            "Instructions:"
            "- Always check the provided context of the conversation. If the latest message is vague but relates to earlier data (like follow-ups), classify it accordingly."
            "- Return only one of 'general', 'data_fetch', 'order_tracking', or 'customer_support'. No explanations, no extra words."
        )'''

    payload = {
        "model": "openai/gpt-3.5-turbo",  # or your preferred model supported by OpenRouter
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},   
            {"role": "user", "content": context}
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
    if intent not in ("general", "data_fetch", "order_tracking", "customer_support"):
        logging.info(f"Unexpected intent '{intent}' classified. Defaulting to 'general'.")
        intent = "general"
    return intent
