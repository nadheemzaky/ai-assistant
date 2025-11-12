import requests
from core.openrouter_client import call_openrouter
import logging
from core.session_manager import session_manager


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
    context = (
    "You are an AI assistant that can help users track their orders. "
    "Politely tell the user that you can check their order status, "
    "and ask them to share their order ID so you can look it up.")
    system=' '
    try:
        reply=call_openrouter(session_id,user_message,system,context)
        try:
            session_manager.update_state(session_id,'verify_order_id')
        except Exception as e:
            logging.error({e})
        return reply
    except Exception as e:
        logging.error(f'get order id route error:{e}')
    

def verify_order_id(session_id,user_message):
    context='you are an ai assistant and you are helping to track the order of client of leajlak using order id'
    try:
        system='you are an order id extractor who eill extract order id from the given message and then output the order id only in numerical form'
        context='only output order ID you have extracted eg : "456789" '
        order_id=call_openrouter(session_id,user_message,system,context)
        print(order_id)
        try:
            user_message1='  '
            context1='you are an ai assistant who will ask the user who have provided an order id to verify the order id'
            system1=f'this is the order id={order_id}. ask the user to verify this'
            response=call_openrouter(session_id,user_message1,context1,system1)

            session_manager.update_state(session_id,'got_order_id')
        except Exception as e:
            logging.info(f'verify order id failed{e}')
    except Exception as e:
        logging.error('error')

    return response

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