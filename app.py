from flask import Flask, request, jsonify, render_template,Response,session
import psycopg2
import requests
import json
import time as time_module
from datetime import datetime, timedelta, date,time
from decimal import Decimal
import os
import logging
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
import secrets
from flask_sqlalchemy import SQLAlchemy
import re
from openai import OpenAI
from intent_classifier import classify_intent
import prompts
import audit
import uuid
import models
import context_handler
import database

# do not touch this
load_dotenv()
context_handler.init_db()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client2 = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)



DB_URL = os.getenv('DB_URL')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Creates 'site.db' file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db=SQLAlchemy(app)

logging.basicConfig(
    filename='logs/app.log',          # Log file path
    level=logging.INFO,          # Log messages at INFO level and above
    format='%(asctime)s %(levelname)s: %(message)s',  # Log message format including timestamp
    datefmt='%Y-%m-%d %H:%M:%S'
)
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


class CurrentValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(20), unique=True)  # 'mobile', 'name', 'summary'
    value = db.Column(db.String(255)) 
with app.app_context():
    db.create_all()
    
def set_value(key, value):
    """Store or update a single value"""
    entry = CurrentValue.query.filter_by(key=key).first()
    if entry:
        entry.value = value
    else:
        entry = CurrentValue(key=key, value=value)
        db.session.add(entry)
    db.session.commit()
                            
def get_value(key):
    """Retrieve current value"""
    entry = CurrentValue.query.filter_by(key=key).first()
    return entry.value if entry else None

with app.app_context():
    for key in ['mobile', 'name', 'summary','user_messages','now','session_id']:
        if not CurrentValue.query.filter_by(key=key).first():
            set_value(key, '')





@app.route('/number', methods=['POST'])
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
        return jsonify({"error": "Internal server error"}), 500


@app.route('/names',methods=['POST'])
def names_route():
    if not get_value('name'):
        logging.error(f'names endpoint error occured')
        return jsonify({"error": "No names available"}), 404
    
# Get the last name safely
    name = get_value('name')
    return jsonify({"name": name})



##########################################################
#   ___ ___  ___   ___ ___ ___ ___   ___   _ _____ _     #
#  | _ \ _ \/ _ \ / __| __/ __/ __| |   \ /_\_   _/_\    #
#  |  _/   / (_) | (__| _|\__ \__ \ | |) / _ \| |/ _ \   #
#  |_| |_|_\\___/ \___|___|___/___/ |___/_/ \_\_/_/ \_\  #
#                                                        #
##########################################################

@app.route('/process-data', methods=['POST'])
def process_data():
    """
    Main endpoint for processing user messages.
    Handles intent classification, SQL generation, database queries, and response generation.
    """
    
    # ========================================================================
    # 1. REQUEST VALIDATION
    # ========================================================================
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"reply": "Missing 'message' in request body"}), 400
    
    user_messages = data['message']
    set_value('user_message', user_messages)
    logging.info(f"--------------------------------------------------------------------------Received user message: {user_messages}--------------------------------------------------------------------------")

    # ========================================================================
    # 2. USER VALIDATION
    # ========================================================================
    name = get_value('name')
    if not name:
        logging.error('Names list empty - no users registered')
        return jsonify({"reply": "No users registered yet"}), 400
    
    session_id = get_value('session_id')
    logging.info(f'Session ID: {session_id}')


    # ========================================================================
    # 3. DATETIME HANDLING
    # ========================================================================
    try:
        now = datetime.now()
        set_value('now', str(now))
    except Exception as e:
        logging.error(f"Failed to handle datetime: {e}")
        return jsonify({"error": "Internal server error"}), 500

    # ========================================================================
    # 4. INTENT CLASSIFICATION
    # ========================================================================
    try:
        context = context_handler.get_context_messages(session_id)
        logging.info(f'Context retrieved: {str(context)}')
        
        intent = classify_intent(user_messages, context)
        logging.info(f'Classified intent: {intent}')
        
        # Handle general conversation intent
        if intent == 'general':
            logging.info('Processing general intent')
            try:
                reply = models.generate_openrouter_reply(user_messages, client2)
                
                # Store conversation context
                try:
                    context_handler.store_message(session_id, user_messages, 'user')
                    context_handler.store_message(session_id, reply, 'assistant')
                    logging.info(f'Context stored for session {session_id}')
                except Exception as e:
                    logging.error(f'Failed to store context: {e}')

                logging.info(f'{str(reply)}')
                return jsonify({"reply": str(reply)})
            except Exception as e:
                logging.error(f'Error generating general reply: {e}')
                return jsonify({"error": "Failed to generate response"}), 500
    
    except Exception as e:
        logging.error(f'Error in intent classification: {e}')
        return jsonify({"error": "Failed to classify intent"}), 500

    # ========================================================================
    # 5. SQL QUERY GENERATION
    # ========================================================================
    now = datetime.now()
    sql_context = f'''
    name = {name}
    user message = {user_messages}
    date and time now = {now}
    context: {context}
    '''
    
    try:
        sql_query = models.generate_sql_with_openrouter(sql_context, client2, prompts.sql_prompt)
        if not sql_query:
            logging.error('No SQL query generated')
            return jsonify({"reply": "Failed to generate query", "name": name}), 500
        
        logging.info(f'SQL generation success: {sql_query}')
        
        # Save SQL to Excel
        try:
            audit.append_sql_to_excel([sql_query])
        except Exception as e:
            logging.error(f'Error saving SQL to Excel: {e}')
    
    except Exception as e:
        logging.error(f'Error generating SQL: {e}')
        return jsonify({"reply": "Failed to generate query", "name": name}), 500

    # ========================================================================
    # 6. DATABASE QUERY EXECUTION
    # ========================================================================
    db_data_json, success = database.execute_query_and_get_json(DB_URL, sql_query)
    
    if success and db_data_json:
        try:
            context_handler.store_data(session_id, db_data_json)
            logging.info('Database query executed successfully')
        except Exception as e:
            logging.error(f'Error storing data for followup: {str(e)}')
    else:
        logging.error('Database query execution failure')
        db_data_json = None  # Ensure it's None for response generation

    # ========================================================================
    # 7. RESPONSE GENERATION
    # ========================================================================
    try:
        time = get_value('now')
        prompt_analysis = f'''
            this is what user asked : {user_messages}.
            this is the previous exchanges between user and model = {context}.
            the data that is related to the question of user= {db_data_json}.
            the sql query that is generated right now to fetch data from database = {sql_query}.
            current time = {time}
            '''
        
        # Generate complete response (no streaming)
        response = models.generate_response(
            context, prompt_analysis, client2, prompts.summary_prompt
        )
        logging.info(f'{response}')
        
        # Save conversation to Excel
        try:
            audit.append_conversation_to_excel(user_messages, response, session_id)
        except Exception as e:
            logging.error(f'{e}')
        
        # Store conversation context (only if response is valid)
        if "sorry" not in response.lower():
            try:
                context_handler.store_message(session_id, user_messages, 'user')
                context_handler.store_message(session_id, response, 'assistant')
                logging.info(f'Context stored for session {session_id}')
            except Exception as e:
                logging.error(f'Failed to store context: {e}')
        
        return jsonify({"reply": response}), 200
    
    except Exception as e:
        logging.error(f'Error generating response: {str(e)}')
        return jsonify({"error": "Internal server error"}), 500
    


################################################################
#   ___  ___ ___ ___     _   _  _   _   _ __   _____ ___ ___   #
#  |   \| __| __| _ \   /_\ | \| | /_\ | |\ \ / / __|_ _/ __|  #
#  | |) | _|| _||  _/  / _ \| .` |/ _ \| |_\ V /\__ \| |\__ \  #
#  |___/|___|___|_|   /_/ \_\_|\_/_/ \_\____|_| |___/___|___/  #
#                                                              #
################################################################


@app.route('/')
def home():
    return render_template('index6.html')

if __name__ == '__main__':

    app.run(port=5000, debug=True)

#ngrok http --url=shari-manipular-nonorally.ngrok-free.app 5000