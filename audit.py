
import logging
import time as time_module
import pandas as pd 
import os
import psycopg2
from datetime import datetime, timedelta, date,time
from decimal import Decimal
import json
import sqlite3
from flask import jsonify

from datetime import datetime

def append_sql_to_excel(sql, filename='data/sql.xlsx'):
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


def execute_query_and_get_json(db_url, sql_query):

    try:
        with psycopg2.connect(db_url) as conn:
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
                    logging.info(f'Database fetching successful: {str(db_data_json)}')
                    return db_data_json, True
                except Exception as json_error:
                    logging.error(f'JSON serialization error: {str(json_error)}')
                    return None, False
                    
    except psycopg2.Error as db_error:
        logging.error(f'Database error: {str(db_error)}')
        return None, False
    except Exception as general_error:
        logging.error(f'General error in query execution: {str(general_error)}')
        return None, False
    
def append_conversation_to_excel(user_message, bot_response,session_id, excel_file='data/conversations.xlsx'):
    """
    Append user message and bot response to Excel file.
    
    Args:
        user_message: User's message
        bot_response: Bot's response
        excel_file: Path to Excel file
    """

    # Prepare data
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