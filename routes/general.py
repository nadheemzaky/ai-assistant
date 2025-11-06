from core.openrouter_client import call_openrouter
system="""
"You are Leajlak's customer service assistant (Leajlak's Order Management System connects merchants "
"and third-party logistics companies for on-demand express and scheduled deliveries, leveraging AI, IoT, "
"and Big Data to boost efficiency, cut costs, and improve customer satisfaction). "
"Check the user's message and send appropriate replies that are always inside the above context."
"""
model="openai/gpt-3.5-turbo"
max_tokens=150
temperature=1.0

def general_route(session_id,usermessage,context,client):
    return call_openrouter(session_id,usermessage,system,context,client,model,max_tokens,temperature)

# call_openrouter(user_message,system,context,client,model,max_tokens,temperature)