import requests
from core.openrouter_client import call_openrouter
from core.session_manager import session_manager

CLIENT_ID = "3"
TRACKING_API_BASE = "https://app.leajlak.com/api/orders/tracking/{client_id}/{order_id}/show"


def got_order_id(session_id, order_id):
    try:
        api_url = TRACKING_API_BASE.format(client_id=CLIENT_ID, order_id=order_id)

        response = requests.get(api_url)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 404:
                return "The order ID you entered does not exist. Please check and try again."
            else:
                return f"Tracking service returned an error: {http_err}"

        # If status is OK → process the data
        api_data = response.json()
        logs = api_data.get("logs", [])

        if not logs:
            return "No tracking data found for this order."

        formatted_logs = "\n".join([
            f"Status: {log['status']}\n"
            f"Description: {log['description']}\n"
            f"Date: {log['date']} {log['time']}\n"
            for log in logs
        ])

        llm_prompt = (
            f"Here is the tracking information for order ID: {order_id}.\n\n"
            f"{formatted_logs}\n"
            f"Summarize this in a clear, simple way for the user."
        )

        llm_response = call_openrouter(
            session_id=session_id,
            user_message=llm_prompt,
            system="You are an AI assistant summarizing tracking data.",
            context="summarize the given data in a simple manner for the user."
        )

        session_manager.update_state(session_id, 'INITIAL')
        return llm_response

    except requests.exceptions.RequestException as e:
        return f"Unable to contact tracking API. Please try again later."

    except Exception as e:
        return f"An unexpected error occurred: {e}"
