from . import general,data_fetch,order_tracking,customer_support

def router(intent, usermessage, context,client):
    routes = {
        'general': general,
        'data_fetch': data_fetch,
        'order_tracking': order_tracking,
        'customer_support': customer_support
    }
    route_func = routes.get(intent)
    if route_func:
        try:
            # Pass usermessage and context as arguments to route function
            return route_func(usermessage, context,client)
        except Exception as e:
            print(f"Error in '{intent}' route: {e}")
    else:
        print("No valid route found for intent:", intent)