from flask import Flask, request, jsonify, render_template,Response,session
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

#def dirs
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
session_id = session_manager.create_session('MC DONALDS')

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


def get_username_by_user_id(mobile):
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = "SELECT name FROM users WHERE mobile_number = %s"
        cursor.execute(query, (mobile,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result['name']
        else:
            return None
    except Exception as e:
        print("Error:", e)
    finally:
        if conn:
            conn.close()



logging.info('success')

'''@app.route('/number', methods=['POST'])`
def number():
    try:
        SESSION_ID = str(uuid.uuid4())
        set_value('session_id', SESSION_ID)
        logging.info(f"New session started: {SESSION_ID}")
    except Exception as e:
        logging.error(f'session initialization error: {str(e)}')
    data = request.json
    logging.info(f"Received request data: {data}")

    # Validation
    if not data or 'mobile' not in data:
        logging.warning("Missing 'mobile' in request body")
        return jsonify({"error": "Mobile number required"}), 400
    
    mobile = data['mobile']
    
    try:
        # Store mobile (overwrites previous)
        set_value('mobile', mobile)
        logging.info(f"Updated mobile: {mobile}")
        
        # Get and store name
        name = get_username_by_user_id(mobile)
        if not name:
            logging.warning(f"No user found for mobile: {mobile}")
            return jsonify({"error": "User not found"}), 404
            
        set_value('name', name)
        logging.info(f"Updated name: {name}")
        
        return jsonify({
            "mobile": get_value('mobile'),
            "name": get_value('name')
        })
        
    except Exception as e:
        logging.info(f"Server error: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500'''
'''@app.route('/names',methods=['POST'])
def names_route():
    if not get_value('name'):
        logging.error(f'names endpoint error occured')
        return jsonify({"error": "No names available"}), 404
    
# Get the last name safely
    name = get_value('name')
    return jsonify({"name": name})'''
@app.route('/chat', methods=['POST'])
def chat():

    try:
        logging.info(f'//////*chat route with session id={session_id}*///////')
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Missing 'message' field"}), 400
        
        user_messages = data['message']
        context = session_manager.get_conversation_history(session_id)

        intent = classify_intent(user_messages, context)
        print(intent)
        
        reply = router(session_id,intent, user_messages, context,client2)
        if reply is None:
            reply=call_openrouter(user_messages,prompts.fallback_prompt,context,client2)
        session_manager.add_to_history(session_id, 'user', user_messages)
        session_manager.add_to_history(session_id, 'assistant', reply)
        append_conversation_async(user_messages, reply, session_id)
        
        state=1
        return jsonify(
            {
            "reply": str(reply),
            "state":state,
            "session_id":session_id
            }
        )
    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/')
def home():
    return render_template('index_test.html')

if __name__ == '__main__':

    app.run(port=5000, debug=True)

#ngrok http --url=shari-manipular-nonorally.ngrok-free.app 5000