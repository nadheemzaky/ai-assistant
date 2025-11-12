import logging
from core.session_manager import session_manager
from . import general, data_fetch, order_tracking, customer_support

def router(session_id, intent, usermessage, context):
    try:
        # ORDER TRACKING FLOW
        if intent == 'order_tracking':
            get_session = session_manager.get_session(session_id)
            state = get_session['state']
            print(f'inside router, before checking {state}')

            if state == 'INITIAL':
                reply = order_tracking.get_order_id(session_id, usermessage)
                return reply

            elif state == 'verify_order_id':
                reply = order_tracking.verify_order_id(session_id, usermessage)
                return reply

            elif state == 'got_order_id':
                reply = order_tracking.got_order_id(session_id, usermessage, context)
                return reply

            else:
                print(f"Unknown state: {state}")
                return "I'm not sure what step we're on with your order tracking."

        # DATA FETCH ROUTE
        elif intent == 'data_fetch':
            return data_fetch.data_fetch_route(session_id, usermessage, context)

        # CUSTOMER SUPPORT ROUTE
        elif intent == 'customer_support':
            return customer_support.customer_support_route(session_id, usermessage, context)

        # GENERAL CHAT ROUTE
        elif intent == 'general':
            return general.general_route(session_id, usermessage, context)

        # UNKNOWN ROUTE
        else:
            print(f"No matching intent found: {intent}")
            return "Sorry, I didn't understand your request."

    except Exception as e:
        logging.error(f"Router error for intent={intent}: {e}", exc_info=True)
        return f"Internal error while routing: {e}"
