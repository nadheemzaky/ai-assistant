from . import general,data_fetch,order_tracking,customer_support
import logging

def router(session_id,intent, usermessage, context,client):
    routes = {
        'general': general.general_route,
        'data_fetch': data_fetch.data_fetch_route,
        'order_tracking': order_tracking.handle_order_tracking,
        'customer_support': customer_support.customer_support_route
    }
    route_func = routes.get(intent)
    if route_func:
        try:
            logging.info(f'route_func={route_func}')
            # Pass usermessage and context as arguments to route function
            return route_func(session_id,usermessage, context,client)
        except Exception as e:
            print(f"Error in '{intent}' route: {e}")
    else:
        print("No valid route found for intent:", intent)