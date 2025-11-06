from routes import general_route, order_tracking_route,data_fetch_route, customer_support_route


def router(intent, usermessage, context,client):
    routes = {
        'general': general_route,
        'data_fetch': data_fetch_route,
        'order_tracking': order_tracking_route,
        'customer_support': customer_support_route
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
 