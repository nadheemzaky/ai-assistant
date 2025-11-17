from core.openrouter_client import call_openrouter
system="hi"


def customer_support_route(session_id,usermessage,context):
    return call_openrouter(session_id,usermessage,context,system)
