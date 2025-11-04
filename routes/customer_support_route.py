from .openrouter import call_openrouter
system="hi"


def customer_support_route(usermessage,context):
    return call_openrouter(usermessage,context,system)
