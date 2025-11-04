from .openrouter import call_openrouter
system="order tracking context"

def order_tracking_route(usermessage,context):
    return call_openrouter(usermessage,system,context)