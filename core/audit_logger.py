#move to audit
import time as time_module
import pandas as pd 
import os
import psycopg2
from datetime import datetime, timedelta, date,time
from decimal import Decimal
import json
import sqlite3
from flask import jsonify
import threading
import logging
from datetime import datetime

def append_sql_to_excel(sql, filename='storage/data/sql.xlsx'):
    if os.path.exists(filename):
        existing_df = pd.read_excel(filename)
        new_df = pd.DataFrame({'sql': sql})
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = pd.DataFrame({'sql': sql})
    combined_df.to_excel(filename, index=False)

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


def append_conversation_to_excel(user_message, bot_response,session_id, excel_file='storage/data/conversations.xlsx'):

    data = {
        'Timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        'User Message': [user_message],
        'Bot Response': [bot_response],
        'Session ID': [session_id]
    }
    df_new = pd.DataFrame(data)
    try:
        # Check if file exists
        if os.path.exists(excel_file):
            # Read existing data
            df_existing = pd.read_excel(excel_file)
            # Append new data
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new
        
        # Save to Excel
        df_combined.to_excel(excel_file, index=False)
        logging.info(f'Conversation appended to {excel_file}')
        
    except Exception as e:
        logging.error(f'Error appending to Excel: {e}')
        raise


def append_conversation_async(user_message, bot_response, session_id):
    thread = threading.Thread(
        target=append_conversation_to_excel,
        args=(user_message, bot_response, session_id),
        daemon=True  # ensures thread won't block shutdown
    )
    thread.start()

def append_sql_async(sql):
    thread = threading.Thread(
        target=append_sql_to_excel,
        args=(sql,),
        daemon=True  # ensures thread won't block shutdown
    )
    thread.start()