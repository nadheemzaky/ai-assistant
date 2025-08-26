from flask import Flask, request, jsonify, render_template
import psycopg2
import requests
import json
from datetime import datetime, timedelta, date, time
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

#client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
#client2 = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY2"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
    for key in ['mobile', 'name', 'summary']:
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



'''def generate_summary_with_claude(prompt):
    try:
        response = client2.messages.create(
            model="claude-sonnet-4-20250514",  # update if needed for Claude Sonnet 3.7
            max_tokens=300,
            system=(
                "You are a customer service chatbot that provides concise analysis. "
                "Do not greet or address. No introduction but robust analysis. "
                "Use simple language, 60-70 words. "
                "If the user query is unrelated to leajlak servicesthen ask the "
                "costumer politely to enquire only about the leajlak services'" \
                "Leajlak's innovative Order Management System connects merchants and third-party logistics companies for "
                "seamless on-demand express & scheduled delivery services.In particular, our system leverages this advancement in emerging technology, "
                "like AI, IoT, Big Data, etc.,"
                " to connect the gap between merchants and logistics companies effectively. Therefore, "
                "it builds efficiency as well as helps in cost reduction with better customer satisfaction."
            ),
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        summary = response.content[0].text
        return summary
    except Exception as e:
        logging.error(f"Anthropic API error: {str(e)}")
        raise

def generate_sql_with_claude(prompt):
    try:
        # Combine system context and user prompt as required by Anthropic's SDK
        message = client.messages.create(
            model="claude-sonnet-4-20250514",  # Or latest Sonnet 3.7 ID per Anthropic docs
            max_tokens=1000,
            system = "You are an SQL query generator that only outputs the SQL query, nothing else." \
            " Also consider putting limit to first 100 rows.",
            messages = [
            {"role": "user", "content": prompt}
            ]
        )
        
        sql_query = message.content[0].text
        logging.info(f"generated sql query: {sql_query}")
        return sql_query
    except Exception as e:
        logging.error(f"Anthropic API error: {str(e)}")
        raise'''

def generate_sql_with_openai(prompt):
    try:
        response = client.responses.create(
            model="gpt-5-mini-2025-08-07",
            instructions=(
                "You are an SQL query generator for PostgreSQL using table “orders_new”. "
                "Columns: "
                "“Order ID”, “Client Order ID”, “Order Type”, “Order Payment Type”, “COD Amount”, "
                "“Client Name”, “Shop Name”, “Shop Zone”, “Shop Area”, “Shop Region”, “Captain”, "
                "“Captain Assigned Rule”, “Captain Employment Type”, “Assigned By”, “Order Status”, "
                "“Cancellation Reason”, “Cancelled By”, “Date”, “New Order (Created At)”, “Order Accepted”, "
                "“Order Accepted Time”, “Start Ride”, “Start Ride Time”, “Reached Shop”, “Reached Shop Time”, "
                "“Order Picked”, “Order Picked Time”, “Shipped”, “Shipped Time”, “Reached Destination”, "
                "“Reached Destination Time”, “Business Day”, “Final Status”, “Final Status Time”, "
                "“Acceptance Time”, “Arrival Time”, “Reached Time”, “Picked Time”, “Pickup to Delivery Time”, "
                "“Process Time In Minutes”, “Distance B/W”, “Auto Assign Attempts”.  \n\n"
                
                "RULES (non-negotiable):  \n"
                "1. Always output a single-line SELECT query.  \n"
                "2. Use double quotes for exact-case column names.  \n"
                "3. Always append WHERE “Client Name” = '{name}'.  \n"
                "4. Always include LIMIT 30.  \n"
                "5. Never return all data unfiltered.  \n\n"
                
                "FORBIDDEN OUTPUT:  \n"
                "- No markdown, backticks, SQL tags, comments, greetings, headers, or explanations.  \n"
                "- Anything other than the pure SQL query is a failure.  \n\n"
                
                "FINAL INSTRUCTION:  \n"
                "Output ONLY the ready-to-run SQL query as plain text."
            ),
            input=prompt
        )
        
        sql_query = response.output_text.strip()
        logging.info(f"Generated SQL query: {sql_query}")
        return sql_query
        
    except Exception as e:
        logging.error(f"OpenAI API error: {str(e)}")
        raise
def generate_summary_with_openai(prompt):
    try:
        response = client.responses.create(
            model="gpt-5-mini-2025-08-07",
            instructions=(
                "You are Leajlak's customer service assistant. "
                "Provide a single-paragraph analysis (50-60 words) in simple, jargon-free language for non-experts. "
                
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
                
                "COMPANY CONTEXT\n"
                "Leajlak's Order Management System connects merchants and third-party logistics companies for on-demand express and scheduled deliveries, leveraging AI, IoT, and Big Data to boost efficiency, cut costs, and improve customer satisfaction."
            ),
            input=prompt,
        )

        summary = response.output_text.strip()
        logging.info(f"Generated summary: {summary}")
        return summary

    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
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
        logging.error(f"Server error: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/names',methods=['POST'])
def names_route():
    if not get_value('name'):
        return jsonify({"error": "No names available"}), 404
    
    # Get the last name safely
    name = get_value('name')
    return jsonify({"name": name})




@app.route('/process-data', methods=['POST'])
def process_data():
    # Input validation
    name=get_value('name')
    if not name:  # Check if names list is empty
        return jsonify({"reply": "No users registered yet"}), 400
        
    data = request.json
    user_message = data['message']
    if not data or 'message' not in data:
        return jsonify({"reply": "Missing 'message' in request body"}), 401
    else:
        logging.info(f"Received user message: {user_message}")
    
    #logging.info(f"Received user message: {user_message}")
    # 1. Generate SQL with Gemini
    prompt_sql = f'''
    name = {name}
    user message = {user_message}
   '''
    
 #generate_sql_with_claude
    try:
        sql_query = generate_sql_with_openai(prompt_sql)
    except Exception as e:
        return jsonify({"reply": "Failed to generate query", "name": name}), 500

    # 2. Validate and execute SQL
    #if not validate_sql_query(sql_query):
        #return {"reply":f"Invalid query request{sql_query}"}, 400
        
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
                
                db_data_json = json.dumps(list_of_dicts, indent=2, cls=SafeJSONEncoder)
                
    except psycopg2.Error as e:
        return jsonify({"reply": f"{sql_query} Data not avialable currently"}), 501

    if not rows:
        return jsonify({
            "reply": "The data is not avialable in the database"
        }), 404

    prompt_analysis = f'''
        user message = {user_message}
        database context = {db_data_json}
        '''

    try:
        summary = generate_summary_with_openai(prompt_analysis)
        set_value('summary', summary)
    except Exception as e:
        logging.error(f"Failed to generate summary: {str(e)}")
        return jsonify({"reply": "Failed to generate summary"}), 502

    return jsonify({
        "sql_query": sql_query,
        "reply": summary,
    })


#requires more works
'''
@app.route("/conversation", methods=['POST'])
def conversation():
    data=request.json
    if not data or 'message' not in data:
        return {"reply": "Missing 'message' in request body"}, 400
    user_message = data['message']
    conversation=f''you are a costomer service chatbot. you will be provided context to chat with the costomer.
    -give response within 50 words
    -do not greet or address the user
    -if the database returns empty then reply with data not available for the specific request
    -user message: {user_message}
    in th user message if the user mentiones any thing about previous conversation then use the context below
    -context:{get_value('summary')}''
    try:
        reply = generate_summary_with_openai(conversation)
        return {
            "reply": reply,
            "message": user_message,
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
