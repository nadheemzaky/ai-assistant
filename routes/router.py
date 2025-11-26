import logging
from core.session_manager import session_manager
from . import general, data_fetch, order_tracking, customer_support,client_onboard, lead_generation

def router(session_id, intent, usermessage, context):
    try:
        get_session = session_manager.get_session(session_id)
        
        state = get_session['state']

#---------------------------------------------------------------------------------------

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
            
#---------------------------------------------------------------------------------------


        elif intent == 'client_onboard' or state in ['verify_mobile','verify_name','verify_email','password_set','confirm_password']:
            if state == 'INITIAL':
                reply = client_onboard.start_onboard(session_id, usermessage)
                return reply

            elif state == 'verify_name':
                reply = client_onboard.verify_name(session_id, usermessage)# verify name + ask mobile
                return reply
            elif state == 'verify_mobile':
                reply = client_onboard.verify_mobile(session_id, usermessage)# verify mobile + ask email
                return reply
            elif state == 'verify_email':
                reply = client_onboard.verify_email(session_id, usermessage)# verify email + ask password
                return reply
            elif state == 'password_set':
                reply = client_onboard.verify_password(session_id, usermessage)# verify password + confirm password
                return reply
            elif state == 'confirm_password':
                reply = client_onboard.confirm_password(session_id, usermessage)# confirm password + ask for CR
                return reply
        
#---------------------------------------------------------------------------------------


        elif intent == 'lead_gen' or state in ['lead_verify_name', 'lead_verify_phone', 'lead_verify_email', 'lead_verify_brand', 'lead_verify_sector', 'lead_verify_branches']:
            # LEAD GENERATION FLOW
            if state == 'INITIAL':
                reply = lead_generation.start_lead(session_id, usermessage)
                return reply

            elif state == 'lead_verify_name':
                reply = lead_generation.lead_verify_name(session_id, usermessage)
                return reply

            elif state == 'lead_verify_phone':
                logging.info('Routing to phone verification')
                reply = lead_generation.lead_verify_phone(session_id, usermessage)
                return reply

            elif state == 'lead_verify_email':
                reply = lead_generation.lead_verify_email(session_id, usermessage)
                return reply

            elif state == 'lead_verify_brand':
                reply = lead_generation.lead_verify_brand(session_id, usermessage)
                return reply

            elif state == 'lead_verify_sector':
                reply = lead_generation.lead_verify_sector(session_id, usermessage)
                return reply

            elif state == 'lead_verify_branches':
                reply = lead_generation.lead_verify_branches(session_id, usermessage)
                return reply



#---------------------------------------------------------------------------------------

        # DATA FETCH ROUTE
        elif intent == 'data_fetch':
            return data_fetch.data_fetch_route(session_id, usermessage, context)

        # CUSTOMER SUPPORT ROUTE
        elif intent == 'customer_support':
            return customer_support.customer_support_route(session_id, usermessage, context)






#---------------------------------------------------------------------------------------
        # GENERAL CHAT ROUTE
        else:

            return general.general_route(session_id, usermessage, context)



    except Exception as e:
        logging.error(f"Router error for intent={intent}: {e}", exc_info=True)
        return f"Internal error while routing: {e}"
