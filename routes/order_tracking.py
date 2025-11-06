STATES = {
    'INITIAL': 'waiting_for_intent',
    'COLLECTING_ORDER_ID': 'need_order_id',
    'COLLECTING_PHONE': 'need_phone',
    'COLLECTING_EMAIL': 'need_email',
    'READY_TO_FETCH': 'have_all_details',
    'FETCHING_DATA': 'calling_api',
    'SUMMARIZING': 'generating_response'
}

from flask import request, jsonify
import logging
from core.session_manager import session_manager
from core.openrouter_client import call_openrouter
from core import order_api_client

# Preset responses (no LLM needed for these)
MESSAGES = {
    'greeting': "I can help you track your order! I'll need a few details.",
    'ask_order_id': "Please provide your order ID (e.g., ORD-12345)",
    'ask_phone': "Great! Now, what's the phone number on the order?",
    'ask_email': "Perfect! Lastly, please provide your email address.",
    'fetching': "Let me check that for you... 🔍",
    'not_found': "I couldn't find that order. Please verify your details.",
    'error': "Something went wrong. Please try again later."
}

def extract_order_id(text, client):
    prompt = "Extract ONLY the order ID from this text. Return just the ID or 'NONE' if not found."
    result = call_openrouter(text, prompt, "", client, "openai/gpt-3.5-turbo", 50, 0.3)
    return None if result.upper() == 'NONE' else result.strip()

def extract_phone(text, client):
    prompt = "Extract ONLY the phone number. Return just the number or 'NONE'."
    result = call_openrouter(text, prompt, "", client, "openai/gpt-3.5-turbo", 50, 0.3)
    return None if result.upper() == 'NONE' else result.strip()

def extract_email(text, client):
    prompt = "Extract ONLY the email address. Return just the email or 'NONE'."
    result = call_openrouter(text, prompt, "", client, "openai/gpt-3.5-turbo", 50, 0.3)
    return None if result.upper() == 'NONE' else result.strip()

def detect_order_tracking_intent(text, client):
    prompt = "Does the user want to track an order? Answer only 'YES' or 'NO'."
    result = call_openrouter(text, prompt, "", client, "openai/gpt-3.5-turbo", 10, 0.3)
    return 'YES' in result.upper()


def handle_order_tracking(session_id, user_message, client):
    session = session_manager.get_session(session_id)
    state = session['state']
    collected = session['collected_data']
    
    # ==================== STATE: INITIAL ====================
    if state == 'INITIAL':
        # Check if user wants order tracking
        wants_tracking = detect_order_tracking_intent(user_message, client)
        
        if wants_tracking:
            session_manager.update_state(session_id, 'COLLECTING_ORDER_ID')
            return f"{MESSAGES['greeting']}\n\n{MESSAGES['ask_order_id']}"
        else:
            # Not order tracking - handle as general query
            return "How else can I help you today?"
    
    # ==================== STATE: COLLECTING ORDER ID ====================
    elif state == 'COLLECTING_ORDER_ID':
        order_id = extract_order_id(user_message, client)
        
        if order_id:
            # Save order ID and move to next step
            session_manager.store_data(session_id, 'order_id', order_id)
            session_manager.update_state(session_id, 'COLLECTING_PHONE')
            return MESSAGES['ask_phone']
        else:
            # Didn't understand - ask again
            return "I didn't catch the order ID. Please provide it like: ORD-12345"
    
    # ==================== STATE: COLLECTING PHONE ====================
    elif state == 'COLLECTING_PHONE':
        phone = extract_phone(user_message, client)
        
        if phone:
            session_manager.store_data(session_id, 'phone', phone)
            session_manager.update_state(session_id, 'COLLECTING_EMAIL')
            return MESSAGES['ask_email']
        else:
            return "Please provide a valid phone number."
    
    # ==================== STATE: COLLECTING EMAIL ====================
    elif state == 'COLLECTING_EMAIL':
        email = extract_email(user_message, client)
        
        if email:
            session_manager.store_data(session_id, 'email', email)
            
            # Now we have everything! Fetch and summarize
            return fetch_and_summarize(session_id, client)
        else:
            return "Please provide a valid email address."
    
    return MESSAGES['error']


def fetch_and_summarize(session_id, client):
    """
    THE MAGIC HAPPENS HERE
    1. Get data from collected info
    2. Call order API
    3. Use LLM to create friendly summary
    """
    
    session = session_manager.get_session(session_id)
    collected = session['collected_data']
    
    try:
        # Step 1: Call your order tracking API
        logging.info(f"Fetching order {collected['order_id']}")
        
        order_data = order_api_client.get_order_details(
            order_id=collected['order_id'],
            phone=collected['phone'],
            email=collected['email']
        )
        
        if not order_data:
            # Order not found
            session_manager.reset_session(session_id)
            return MESSAGES['not_found']
        
        # Step 2: Feed API response to LLM for summarization
        logging.info("Summarizing order data with LLM")
        
        summarization_prompt = f"""
        You are a friendly customer service assistant for McDonald's.
        
        The customer asked about their order. Here's the raw data from our system:
        {order_data}
        
        Create a natural, conversational summary that includes:
        - Order status (preparing, out for delivery, delivered, etc.)
        - Expected delivery time
        - Current location if in transit
        - Any important notes or delays
        
        Be warm and helpful. Keep it under 100 words.
        """
        
        summary = call_openrouter(
            user_message="Summarize this order",
            system_prompt=summarization_prompt,
            context="",
            client=client,
            model="openai/gpt-3.5-turbo",
            max_tokens=300,
            temperature=0.7
        )
        
        # Step 3: Reset session for next interaction
        session_manager.reset_session(session_id)
        
        return summary
        
    except Exception as e:
        logging.error(f"Error in fetch_and_summarize: {e}")
        session_manager.reset_session(session_id)
        return MESSAGES['error']
