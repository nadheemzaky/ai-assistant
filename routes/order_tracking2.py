import requests
from core.openrouter_client import call_openrouter
import logging
from core.session_manager import session_manager
import random


# Model configuration
system = """
You are an intelligent order tracking assistant.
Given API tracking data for an order, summarize the shipment status in a user-friendly way.
"""
model = "openai/gpt-3.5-turbo"
max_tokens = 150
temperature = 1.0

# Preset API client ID (example)
CLIENT_ID = "3"
TRACKING_API_URL = "https://app.leajlak.com/api/orders/tracking/{client_id}/{client-order-id}/show"

def get_order_id(session_id,user_message):
    preset_replies = [
        "Sure! I can help you track your order. Please share your order ID.",
        "I'd be happy to check the status for you. Could you provide your order ID?",
        "I can look up your order details — just send me the order ID.",
        "Please share your order ID so I can check the status for you.",
        "Sure! What's your order ID? I'll get the status for you."
    ]

    try:
        reply = random.choice(preset_replies)
        try:
            session_manager.update_state(session_id,'verify_order_id')
        except Exception as e:
            logging.error({e})
        return reply
    except Exception as e:
        logging.error(f'get order id route error:{e}')
    
def verify_order_id(session_id,user_message):
    context='you are an orderID extractor and classifier.' \
    ' check the user message and if the user message contains a numerical order id with minimum 5 chars' \
    'you should reply with tat number exactly nothing else ' \
    'if there is no order id then reply with "RETRY" only'
    try:
        order_verify=call_openrouter(session_id,user_message,context)
        if str(order_verify)=='RETRY':
            context='you are an ai assistant who will tell the user he has not provided with a valid order id ' \
            'please provide a valid order id'
            retry_reply=call_openrouter(session_id,user_message,context)
            return retry_reply
        else:

            print('hi')
    except Exception as e:
        logging.error({e})


def got_order_id(session_id, order_id, context):
    try:
        payload = {
            "client_id": CLIENT_ID,
            "order_id": order_id
        }
        response = requests.get(TRACKING_API_URL, json=payload)
        response.raise_for_status()

        api_data = response.json()
        logs = api_data.get("logs", [])
        if not logs:
            return "No tracking data found for this order."

        formatted_logs = "\n".join([
            f"Status: {log['status']}\nDescription: {log['description']}\nDate: {log['date']} {log['time']}\n"
            for log in logs
        ])

        llm_prompt = f"Order ID: {order_id}\nClient ID: {CLIENT_ID}\n\nTracking Data:\n{formatted_logs}\n\nSummarize this tracking history clearly."

        llm_response = call_openrouter(
            session_id=session_id,
            usermessage=llm_prompt,
            system=system,
            context=context,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        session_manager.update_state(session_id,'INITIAL')
        return llm_response

    except requests.exceptions.RequestException as e:
        return f"Error contacting tracking API: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

# 1757797
# 3