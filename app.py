from flask import Flask, request, jsonify, render_template,Response,session,make_response
import psycopg2
import json
from datetime import datetime, timedelta, date,time
from decimal import Decimal
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
import secrets
from openai import OpenAI
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import traceback

#log
import logging
import os
import time as time_module
os.environ['TZ'] = 'Asia/Kolkata'
time_module.tzset()
os.makedirs('storage/logs', exist_ok=True)
logging.basicConfig(
    filename='storage/logs/app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

#sys
from core import prompts
from core.openrouter_client import call_openrouter
from core import database
from core import audit_logger
from core.session_manager import session_manager
from core.intent_classifier import classify_intent
from core.audit_logger import append_conversation_async
from routes.router import router
from routes import order_tracking

#def dirs
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client2 = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

DB_URL = os.getenv('DB_URL')


class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for PostgreSQL data types"""
    def default(self, obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return str(obj.total_seconds())  # Convert to seconds
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

@app.route('/chat', methods=['POST'])
def chat():
    session_id = None
    new_session = False
    
    try:
        # 1. Session Management
        session_id = request.cookies.get("session_id")
        session = session_manager.get_session(session_id)

        if session is None:
            session_id = session_manager.create_session('MC DONALDS', session_id)
            session = session_manager.get_session(session_id)
            new_session = True
            logging.info(f'New session created with session_id={session_id}')

        # 2. Request Validation
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Missing 'message' field"}), 400
        
        user_message = data['message']
 
        # 3. Context & Intent
        context = session_manager.get_conversation_history(session_id)
        intent = classify_intent(user_message, context)
        state = session['state']

        # 4. Response Generation
        reply = None
        try:
            response = router(session_id, intent, user_message, context)
            
            # Extract reply safely
            if isinstance(response, dict):
                reply = response.get("reply")
            else:
                reply = response
            
            # Fallback if no reply
            if reply is None:
                logging.warning(f"Router returned None for intent={intent}, using fallback")
                response = call_openrouter(
                    session_id, 
                    user_message, 
                    prompts.fallback_prompt, 
                    context
                )
                reply = response.get("reply") if isinstance(response, dict) else response

        except Exception as e:
            logging.error(f'Error generating response: {e}')
            reply = "I'm sorry, I encountered an error. Please try again."
        
        # Ensure we have a reply
        if reply is None:
            reply = "I'm sorry, I couldn't generate a response. Please try again."

        # 5. Save to History
        session_manager.add_to_history(session_id, 'user', user_message)
        session_manager.add_to_history(session_id, 'assistant', reply)
        append_conversation_async(user_message, reply, session_id)

        # 6. Build Response
        response_data = {
            "reply": str(reply),
            "state": state,
            "session_id": session_id
        }
        
        response = make_response(jsonify(response_data))
        
        # Set cookie for new sessions
        if new_session:
            response.set_cookie(
                "session_id",
                session_id,
                max_age=60*60*24*30,  # 30 days
                httponly=True,
                secure=True,  # Set to True in production with HTTPS
                samesite="Lax"
            )
        
        logging.info(f'Session {session_id}: intent={intent}, state={state}')
        return response

    except Exception as e:
        logging.error(f'Chat endpoint error: {traceback.format_exc()}')
        
        # Try to still return a response with error message
        error_response = {
            "error": "An error occurred processing your message",
            "reply": "I'm experiencing technical difficulties. Please try again.",
        }
        
        if session_id:
            error_response["session_id"] = session_id
            
        return jsonify(error_response), 500

@app.route('/reset-session', methods=['POST'])
def reset_session_route():
    try:
        session_id = request.cookies.get("session_id")

        if not session_id:
            return jsonify({"error": "No session_id found"}), 400

        # Call your reset function
        session_manager.reset_session(session_id)
        logging.info('------------------------reset session------------------------')

        return Response(status=204)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/')
def home():
    return render_template('index_test.html')

if __name__ == '__main__':

    app.run(port=5000, debug=True)

#ngrok http --url=shari-manipular-nonorally.ngrok-free.app 5000