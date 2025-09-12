from flask import Flask, request, jsonify, render_template,Response
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
from intent_classifier import classify_intent,generate_openai_reply
import prompts
import function

# do not touch this
load_dotenv()
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
    for key in ['mobile', 'name', 'summary','user_messages','now']:
        if not CurrentValue.query.filter_by(key=key).first():
            set_value(key, '')




def generate_sql_with_openai(prompt):
    try:
        sql_prompt=prompts.sql_prompt
        logging.info('started sql generation')
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role":"system",
                    "content":sql_prompt
                },
                {
                "role":"user",
                "content":prompt
                }
            ]
        )
        sql_query = response.choices[0].message.content
        logging.info(f"Generated SQL query: {sql_query}")
        return sql_query
        
    except Exception as e:
        logging.info(f"OpenAI API error: {str(e)}")
        raise



@app.route('/number', methods=['POST'])
def number():
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

@app.route('/process-data', methods=['POST'])
def process_data():
    data = request.json
    user_messages = data['message']
    
    name=get_value('name')

# datetime handling
    try:
        now = datetime.now()
    except Exception as e:
        logging.error(f"Failed to get current datetime: {e}")
        now = None

    try:
        set_value('now', str(now))
    except Exception as e:
        logging.error(f"Failed to set or log now: {e}")
# intent classification
    try :
        intent = classify_intent(user_messages)
        if intent == 'general':
            logging.info('general intent detected')
            try:
                reply = generate_openai_reply(user_messages)
                return (str(reply))
            except Exception as e:
                logging.error(f'{e}')
        else :
            logging.info('data_fetch intent detected')
    except Exception as e:
        logging.error(f'{e}')

    if not name:
        logging.error(f'names list empty')  # Check if names list is empty
        return jsonify({"reply": "No users registered yet"}), 400
   
    set_value('user_message', user_messages)

    if not data or 'message' not in data:
        return jsonify({"reply": "Missing 'message' in request body"}), 401
    else:
        logging.info(f"Received user message: {user_messages}")
    

    prompt_sql = f'''
    name = {name}
    user message = {user_messages}
    date and time now = {now}
   '''
    
    try:
        sql_query = function.generate_sql_with_openai(prompt_sql,client)
        logging.info(f'sql generation success {prompt_sql}')

    except Exception as e:
        return jsonify({"reply": "Failed to generate query", "name": name}), 500

    try:
        #db_data_json,status_code=fetch_query_results_as_dict(DB_URL,sql_query)
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                rows = cur.fetchall()
                colnames = [desc[0] for desc in cur.description]
                
                # Convert rows to serializable format
                list_of_dicts = []
                for row in rows:
                    row_dict = {}
                    for col, val in zip(colnames, row):
                        if isinstance(val, (datetime, date)):
                            row_dict[col] = val.isoformat()
                        elif isinstance(val, timedelta):
                            row_dict[col] = val.total_seconds()
                        elif isinstance(val, Decimal):
                            row_dict[col] = float(val)
                        else:
                            row_dict[col] = val
                    list_of_dicts.append(row_dict)
                try:
                    db_data_json = json.dumps(list_of_dicts, indent=2, cls=SafeJSONEncoder)
                    logging.info(f'database fetching successfull{str(db_data_json)}')
                except Exception as e:
                    logging.info(f'db return null: {str(e)}')

                
    except psycopg2.Error as e:
        logging.info(f"Database error: {str(e)}")
        return jsonify({"reply": f"{sql_query} Data not avialable currently"}), 501

    if not rows:
        logging.info(f'the query returned null in database')
        return jsonify({
            "reply": "The data is not avialable in the database"
        }), 405


   
    try:
        prompt_analysis = f'''
            fetched data = {db_data_json}
            user message = {user_messages} 
            the previous response provided by llm = {get_value('summary')}
            previous question asked by the user = {get_value('user_messages')}
            the sql query that is generated right now = {sql_query}
            '''
        
        '''def generate_stream(prompt_analysis,wpm=350):
            try:
                summary_prompt=prompts.summary_prompt
                logging.info('started summary generation')
                response = client2.chat.completions.create(
                    model="deepseek/deepseek-chat-v3.1:free",
                    stream=True,
                    messages=[
                        {
                            "role":"system",
                            "content":summary_prompt
                        },
                        {
                            "role":"user",
                            "content":prompt_analysis
                        },
                    ]
                ) 
            except Exception as e:
                logging.error(f'response creattion failed: {str(e)}')
                return

            for chunk in response:
                delta = chunk.choices[0].delta  
                logging.info(f'delta: {delta.__dict__}')  # Log all attributes in delta
                if hasattr(delta, 'content') and delta.content:
                    try:
                        yield delta.content.encode('utf-8')
                        char_count = len(delta.content)
                        delay = (char_count * 30.0) / (wpm * 5)  # Assuming avg 5 chars per word
                        time_module.sleep(delay)
                    except Exception as e:
                        logging.error(f'streaming error{str(e)}')

        return Response(generate_stream(prompt_analysis),mimetype='text/plain')'''


        return Response(
            function.generate_streaming_response(prompt_analysis, client2, prompts),
            mimetype='text/plain'
        )
    except Exception as e:
        logging.error(f'{str(e)}')
        return jsonify({"error": "Internal server error"}), 500
    

@app.route('/deep-analysis',methods=['POST'])
def deep_analysis():
    data = request.json
    user_messages = data['message']
    
    # Return maintenance message
    return jsonify({
        "status": "The deep analysis feature is currently under maintenance. Please try again later.",
    }), 503

@app.route('/end', methods=['POST'])
def end():
    try:
        # Clear all stored values in the database
        db.session.query(CurrentValue).delete()
        db.session.commit()
        
        return jsonify({
            "message": "All data cleared",
            "status": "success"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to clear data: {str(e)}")
        return jsonify({"error": "Data clearance failed"}), 500


@app.route('/')
def home():
    return render_template('index5.html')

if __name__ == '__main__':

    app.run(port=5000, debug=True)

#ngrok http --url=shari-manipular-nonorally.ngrok-free.app 5000