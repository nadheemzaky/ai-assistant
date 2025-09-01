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
'''
ngrok http --url=fast-doberman-rapidly.ngrok-free.app 5000
'''

# do not touch this
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY1"))
client2 = OpenAI(api_key=os.getenv("OPENAI_API_KEY2"))

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
    


def save_messages_to_db(user_messages):
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                for msg in user_messages:
                    # Extract string content from dict
                    content = msg.get('content')
                    if content:
                        cur.execute(
                            "INSERT INTO user_messages (content) VALUES (%s)",
                            (content,)
                        )
    except Exception as e:
        logging.error(f"Error saving message: {e}")
        return False


#havent implemented yet, requires additional packages
def fetch_query_results_as_dict(DB_URL, sql_query):
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                rows = cur.fetchall()
                colnames = [desc[0] for desc in cur.description]

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

                db_data_json = json.dumps(list_of_dicts, indent=2, cls=SafeJSONEncoder)
                return db_data_json, 200
    except psycopg2.Error as e:
        logging.error(f"Database error: {str(e)}")
        return json.dumps({"reply": f"{sql_query} Data not available currently"}), 501 
           
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
    for key in ['mobile', 'name', 'summary','user_messages']:
        if not CurrentValue.query.filter_by(key=key).first():
            set_value(key, '')


def validate_sql_query(sql_query: str) -> bool:
    """
    Validates if the given string looks like a basic SQL query.
    Only allows SELECT statements for safety.
    """
    if not isinstance(sql_query, str):
        return False

    # Remove leading/trailing whitespace
    query = sql_query.strip()

    # Empty query check
    if not query:
        return False

    # Basic SQL injection prevention (block dangerous keywords)
    blocked_keywords = [
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE",
        "CREATE", "REPLACE"
    ]
    if any(re.search(rf"\b{kw}\b", query, re.IGNORECASE) for kw in blocked_keywords):
        return False

    # Must start with SELECT (we only allow read queries in your use case)
    if not re.match(r"(?i)^SELECT\b", query):
        return False

    # Very simple structure check: must contain FROM
    if "FROM" not in query.upper():
        return False

    return True


def generate_sql_with_openai(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {
                    "role":"system",
                    "content":
                        ("""
                        You are an SQL query generator for PostgreSQL using table "updated_table".
                        Columns:
                        id,
                        customer_number,
                        customer_name,
                        client_id,
                        client_name,
                        captain_name,
                        delivery_date,
                        order_status,
                        shop_to_delivery_km,
                        order_created_at,
                        order_accepted_at,
                        start_ride_at,
                        reached_shop_at,
                        order_picked_at,
                        shipped_at,
                        reached_dest_at,
                        final_status_at,
                        cancellation_reason

                        RULES (non-negotiable):
                        1.Always output a single-line SELECT query.
                        2.Use double quotes for exact-case column names.
                        3.Always append WHERE "client_name" = '{name}', except special cases.
                        4.Always include LIMIT 10
                        5.Never return all data unfiltered.
                        6.Always include column headers as the first row by using UNION ALL between a SELECT of the column names as strings and a SELECT of the data cast to VARCHAR.
                        7.Ensure the column names and their order in the header row match exactly the data columns selected.
                         
                        FORBIDDEN OUTPUT:
                        1.No markdown, backticks, SQL tags, comments, greetings, headers, or explanations.
                        2.Anything other than the pure SQL query is a failure.
                         
                        FINAL INSTRUCTION:
                        1.Output ONLY the ready-to-run SQL query as plain text.
                """ )
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
        logging.error(f"OpenAI API error: {str(e)}")
        raise
def generate_summary_with_openai(prompt):
    try:
        response = client2.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            stream=True,
            messages=[
                {
                    "role":"system",
                    "content":(            
                        "You are Leajlak's customer service assistant.\n "
                        "Provide a single-paragraph analysis (50-80 words) in simple, jargon-free language for non-experts.\n "
                        
                        "1. GREETING & SCOPE\n"
                        "- If the user only greets (e.g., “hi”, “hello”), reply with a brief greeting: “Hello! I'm your Leajlak assistant. How can I help?” and stop.  \n"
                        "- If the query is unrelated to Leajlak services, respond:  \n"
                        "  “I can only help with Leajlak-related questions. Please ask about our order management or logistics services.”  \n"
                        
                        "2. DATA ANALYSIS\n"
                        "- Analyze the user's question against the provided JSON data.  \n"
                       # "- If `db_data_json` is empty or contains no relevant records, reply: “Data not available for this request.”  \n"
                        "- Otherwise, deliver a concise analysis based solely on that data—no extra suggestions or formatting.  \n"
                        
                        "3. CONTEXT HANDLING\n"
                        "- If the user references previous conversation, integrate `previous_summary` into your analysis.  \n"
                        
                        "4. TONE & FORMAT\n"
                        "- Do not include headings, bullet points, or lists—only a single paragraph.  \n"
                        "- Do not greet or address the user in analysis.  \n"
                        "- Explain the analysis like a person explaining a data to another person in friendly polite form. \n"
                        
                        "COMPANY CONTEXT\n"
                        "Leajlak's Order Management System connects merchants and third-party logistics companies for on-demand express and scheduled deliveries, leveraging AI, IoT, and Big Data to boost efficiency, cut costs, and improve customer satisfaction."
                    )
                },
                {
                    "role":"user",
                    "content":prompt
                },
            ]
        )
        summary = response.choices[0].message.content
        logging.info(f"Generated summary: {summary}")
        return summary

    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        raise


def stream():
    try:
        def generate_stream(prompt,wpm=350):
            try:
                logging.info('generate function works')
                # Call OpenAI with stream=True, yields chunks incrementally
                response = client.chat.completions.create(
                    model="gpt-5-nano-2025-08-07",
                    stream=True,
                    messages=[
                        {
                            "role":"system",
                            "content":(            
                                "You are Leajlak's customer service assistant.\n "
                                "Provide a single-paragraph analysis (50-130 words) in simple, jargon-free language for non-experts.\n "
                                
                                "1. GREETING & SCOPE\n"
                                "- If the user only greets (e.g., “hi”, “hello”), reply with a brief greeting: “Hello! I'm your Leajlak assistant. How can I help?” and stop.  \n"
                                "- If the query is unrelated to Leajlak services, respond:  \n"
                                "  “I can only help with Leajlak-related questions. Please ask about our order management or logistics services.”  \n"
                                
                                "2. DATA ANALYSIS\n"
                                "- Analyze the user's question against the provided JSON data.  \n"
                                "- If `db_data_json` is empty or contains no relevant records, reply: “Data not available for this request.”  \n"
                                "- Otherwise, deliver a concise analysis based solely on that data—no extra suggestions or formatting.  \n"
                                
                                "3. CONTEXT HANDLING\n"
                                "- If the user references previous conversation, integrate `previous_summary` into your analysis.  \n"
                                
                                "4. TONE & FORMAT\n"
                                "- Do not include headings, bullet points, or lists—only a single paragraph.  \n"
                                "- Do not greet or address the user in analysis.  \n"
                                "- Use more words than numbers for clarity \n "
                                
                                "COMPANY CONTEXT\n"
                                "Leajlak's Order Management System connects merchants and third-party logistics companies for on-demand express and scheduled deliveries, leveraging AI, IoT, and Big Data to boost efficiency, cut costs, and improve customer satisfaction."
                            )
                        },
                        {
                            "role":"user",
                            "content":prompt
                        },
                    ]
                )
            except Exception as e:
                logging.error(f'response exists: {str(e)}')

            for chunk in response:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content'):
                    try:
                    # Yield partial content as server-sent event (SSE) data
                        yield delta.content.encode('utf-8')
                        word_count=len(delta.content.split())
                        delay = (60.0 / wpm) * word_count if word_count > 0 else 0
                        time.sleep(delay)
                    except Exception as e:
                        logging.error(f'{str(e)}')

        logging.info('cycle done')
        return Response(generate_stream(),mimetype='text/event-stream')
    except Exception as e:
        logging.error(f'{str(e)}')



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
        logging.error(f"Server error: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/names',methods=['POST'])
def names_route():
    if not get_value('name'):
        logging.error(f'names endpoint error occured')
        return jsonify({"error": "No names available"}), 404
    
    # Get the last name safely
    name = get_value('name')
    return jsonify({"name": name})


@app.route('/stream-chat', methods=['POST'])
def stream_chat():
    user_messages = request.json.get("messages", [])
    logging.info(f'{user_messages}')
    try:
        if save_messages_to_db(user_messages):
            return "Messages saved", 200
        else:
            logging.error('Failed to save messages to database')
            return "Failed to save messages", 500
    except Exception as e:
        logging.error(f'Error saving user messages: {e}')
    

    def generate(wpm=350):
        try:
            logging.info('generate function works')
            # Call OpenAI with stream=True, yields chunks incrementally
            response = client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=user_messages,
                stream=True
            )
        except Exception as e:
            logging.error(f'response exists: {str(e)}')

        for chunk in response:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content'):
                try:
                # Yield partial content as server-sent event (SSE) data
                    yield delta.content.encode('utf-8')
                    word_count=len(delta.content.split())
                    delay = (60.0 / wpm) * word_count if word_count > 0 else 0
                    timedelta.sleep(delay)
                except Exception as e:
                    logging.error(f'{str(e)}')

    logging.info('cycle done')
    # Return a streaming response with mimetype text/event-stream for chunked text
    return Response(generate(), mimetype='text/event-stream')

@app.route('/process-data', methods=['POST'])
def process_data():
    # Input validation
    name=get_value('name')
    if not name:
        logging.error(f'names list empty')  # Check if names list is empty
        return jsonify({"reply": "No users registered yet"}), 400
        
    data = request.json
    user_messages = data['message']


    #user_messages = request.json.get(str("messages"), [])
    '''    try:
        if save_messages_to_db(user_messages):
            return "Messages saved", 200
        else:
            logging.info('Failed to save messages to database')

    except Exception as e:
        logging.info(f'Error saving user messages: {e}')
    '''


    set_value('user_message', user_messages)

    if not data or 'message' not in data:
        return jsonify({"reply": "Missing 'message' in request body"}), 401
    else:
        logging.info(f"Received user message: {user_messages}")
    

    prompt_sql = f'''
    name = {name}
    user message = {user_messages}
   '''
    
    try:
        sql_query = generate_sql_with_openai(prompt_sql)
    except Exception as e:
        logging.error('sql generation error')
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
                    #logging.info(f'database fetching successfull{str(db_data_json)}')
                except Exception as e:
                    logging.error(f'db return null: {str(e)}')

                
    except psycopg2.Error as e:
        logging.error(f"Database error: {str(e)}")
        return jsonify({"reply": f"{sql_query} Data not avialable currently"}), 501

    if not rows:
        logging.error(f'the query returned null in database')
        return jsonify({
            "reply": "The data is not avialable in the database"
        }), 405

    prompt_analysis = f'''
        user message = {user_messages}
        database context = {db_data_json}
        the context of the data = {get_value('summary')}, if there is any relevant data use it for reply, otherwise ignore it
        previous question asked by the user = {get_value('user_messages')}
        '''
   

    '''try:
        summary = generate_summary_with_openai(prompt_analysis)
        set_value('summary', summary)
    except Exception as e:
        logging.error(f"Failed to generate summary: {str(e)}")
        return jsonify({"reply": "Failed to generate summary"}), 502

    return jsonify({
        "sql_query": sql_query,
        "reply": summary,
    })'''
    try:
        def generate_stream(prompt_analysis,wpm=350):
            try:
                response = client.chat.completions.create(
                    model="gpt-5-nano-2025-08-07",
                    stream=True,
                    messages=[
                        {
                            "role":"system",
                            "content":(            
                                "You are Leajlak's customer service assistant.\n "
                                "Provide a single-paragraph analysis (50-130 words) in simple, jargon-free language for non-experts.\n "
                                
                                "1. GREETING & SCOPE\n"
                                "- If the user only greets (e.g., “hi”, “hello”), reply with a brief greeting: “Hello! I'm your Leajlak assistant. How can I help?” and stop.  \n"
                                "- If the query is unrelated to Leajlak services, respond:  \n"
                                "  “I can only help with Leajlak-related questions. Please ask about our order management or logistics services.”  \n"
                                
                                "2. DATA ANALYSIS\n"
                                "- Analyze the user's question against the provided JSON data.  \n"
                                "- If `db_data_json` is empty or contains no relevant records, reply: “Data not available for this request.”  \n"
                                "- Otherwise, deliver a concise analysis based solely on that data—no extra suggestions or formatting.  \n"
                                
                                "3. CONTEXT HANDLING\n"
                                "- If the user references previous conversation, integrate `previous_summary` into your analysis.  \n"
                                
                                "4. TONE & FORMAT\n"
                                "- Do not include headings, bullet points, or lists—only a single paragraph.  \n"
                                "- Do not greet or address the user in analysis.  \n"
                                "- Use more words than numbers for clarity \n "
                                
                                "COMPANY CONTEXT\n"
                                "Leajlak's Order Management System connects merchants and third-party logistics companies for on-demand express and scheduled deliveries, leveraging AI, IoT, and Big Data to boost efficiency, cut costs, and improve customer satisfaction."
                            )
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
                #logging.info(f'delta: {delta.__dict__}')  # Log all attributes in delta
                if hasattr(delta, 'content') and delta.content:
                    try:
                        yield delta.content.encode('utf-8')
                        char_count = len(delta.content)
                        delay = (char_count * 60.0) / (wpm * 5)  # Assuming avg 5 chars per word
                        time_module.sleep(delay)
                    except Exception as e:
                        logging.error(f'streaming error{str(e)}')

        return Response(generate_stream(prompt_analysis),mimetype='text/plain')
    except Exception as e:
        logging.info(f'{str(e)}')
        return jsonify({"error": "Internal server error"}), 500
    



#requires more works
'''
@app.route("/conversation", methods=['POST'])
def conversation():
    data=request.json
    if not data or 'message' not in data:
        return {"reply": "Missing 'message' in request body"}, 400
    user_messages = data['message']
    conversation=f''you are a costomer service chatbot. you will be provided context to chat with the costomer.
    -give response within 50 words
    -do not greet or address the user
    -if the database returns empty then reply with data not available for the specific request
    -user message: {user_messages}
    in th user message if the user mentiones any thing about previous conversation then use the context below
    -context:{get_value('summary')}''
    try:
        reply = generate_summary_with_openai(conversation)
        return {
            "reply": reply,
            "message": user_messages,
            "context": get_value('summary')
        }
    except Exception as e:
        return {"reply": "Failed to generate response"}, 

'''

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
    return render_template('index2.html')

if __name__ == '__main__':

    app.run(port=5000, debug=True)
