import logging
from core.session_manager import session_manager
from . import general, data_fetch, order_tracking, customer_support

def router(session_id, intent, usermessage, context):
    try:
        get_session = session_manager.get_session(session_id)
        
        state = get_session['state']
        # ORDER TRACKING FLOW
        if intent == 'order_tracking' or state in ['verify_order_id', 'got_order_id']:

            
            if state == 'INITIAL':
                reply = order_tracking.get_order_id(session_id, usermessage)
                return reply

            elif state == 'verify_order_id':
                reply = order_tracking.verify_order_id(session_id, usermessage)
                return reply

            elif state == 'got_order_id':
                reply = order_tracking.got_order_id(session_id, usermessage, context)
                return reply


        # DATA FETCH ROUTE
        elif intent == 'data_fetch':
            return data_fetch.data_fetch_route(session_id, usermessage, context)

        # CUSTOMER SUPPORT ROUTE
        elif intent == 'customer_support':
            return customer_support.customer_support_route(session_id, usermessage, context)

        # GENERAL CHAT ROUTE
        else:
            return general.general_route(session_id, usermessage, context)



    except Exception as e:
        logging.error(f"Router error for intent={intent}: {e}", exc_info=True)
        return f"Internal error while routing: {e}"
