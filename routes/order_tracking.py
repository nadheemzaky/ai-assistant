from core.openrouter_client import call_openrouter
import logging
from core.session_manager import session_manager
import random
from core.order_track_api_cli import got_order_id
import re

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


def verify_order_id(session_id, user_message):
    logging.info("Verifying order ID")

    try:
        # ✔ Regex: extract a clean number with 5 or more digits
        match = re.search(r"\b\d{5,}\b", user_message)

        if not match:
            # If no valid order ID → use preset retry replies
            preset_retry_replies = [
                "It looks like the order ID you provided isn't valid. Please check and share a correct order ID.",
                "Hmm, that doesn't seem like a valid order ID. Could you enter it again?",
                "I couldn't verify that order ID. Please make sure it's correct and resend it.",
                "That order ID didn't match our format. Please provide a valid order ID.",
                "I wasn't able to find an order with that ID. Could you check and send it again?"
            ]
            return random.choice(preset_retry_replies)

        # ✔ Extracted valid order ID
        order_id = match.group(0)
        logging.info(f"Valid order ID detected: {order_id}")

        # Continue your existing logic
        response = got_order_id(session_id, order_id)
        return response

    except Exception as e:
        logging.error(f"Error verifying order ID: {e}")
        return "Something went wrong. Please try again."


# 1757797
# 3