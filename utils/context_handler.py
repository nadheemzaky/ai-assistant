
import logging
import sqlite3
import json
from datetime import datetime
from os import path

def init_db():
    conn = sqlite3.connect('instance/chat_context.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_context (
            session_id TEXT,
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_role TEXT NOT NULL,
            message_text TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_context (
            session_id TEXT,
            data_id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()


def store_message(session_id, message_text, message_role,json_file='data/chat_context.json'):
    conn = sqlite3.connect('instance/chat_context.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO user_context (session_id, message_text, message_role)
            VALUES (?, ?, ?)
        """, (session_id, message_text, message_role))
        logging.info('context stored successfully')
    except Exception as e:
        logging.error(f'error storing info: {str(e)}')
    try:
        cursor.execute("""
            DELETE FROM user_context
            WHERE session_id = ?
            AND message_id NOT IN (
                SELECT message_id
                FROM user_context
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            )
        """, (session_id, session_id, 5))
    except Exception as e:
        logging.error(f'error deleting old context:{str(e)}')

    conn.commit()
    conn.close()
        # JSON file operations
    try:
        # Read existing JSON data
        if path.isfile(json_file):
            with open(json_file, 'r') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []
        
        # Append new message
        new_entry = {
            'session_id': session_id,
            'message_text': message_text,
            'message_role': message_role,
            'timestamp': datetime.now().isoformat()
        }
        data.append(new_entry)
        
        # Write updated data back to file
        with open(json_file, 'w') as file:
            json.dump(data, file, indent=4)
        
        logging.info('context stored to JSON successfully')
    except Exception as e:
        logging.error(f'error storing to JSON: {str(e)}')

def store_data(session_id,data):
    conn = sqlite3.connect('instance/chat_context.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO data_context (session_id, data)
            VALUES (?, ?)
        """, (session_id, data))
        logging.info('data from database stored successfully')
    except Exception as e:
        logging.error(f'error storing info: {str(e)}')

    cursor.execute("""
        DELETE FROM data_context
        WHERE session_id = ?
        AND data_id NOT IN (
            SELECT data_id
            FROM data_context
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        )
    """, (session_id, session_id, 5))

    conn.commit()
    conn.close()

def get_context_messages(session_id):
    conn = sqlite3.connect('instance/chat_context.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT message_role, message_text FROM user_context
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        logging.info('context fetched successfully')
    except Exception as e:
        logging.error(f'error getting context:{str(e)}')
        return []
    
    messages = cursor.fetchall()
    conn.close()

    return [
        {"role": role, "content": text}
        for role, text in messages
    ]

