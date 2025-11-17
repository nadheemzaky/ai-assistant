import sqlite3
import uuid
import json
from datetime import datetime
from contextlib import contextmanager

class SessionManager:    
    def __init__(self, db_path='storage/sessions.db'):
        self.db_path = db_path
        self.create_tables()
    
    @contextmanager
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def create_tables(self):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Sessions table - stores session metadata
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    state TEXT DEFAULT 'INITIAL',
                    orderid TEXT,  -- JSON string
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Conversation history table - stores all messages
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,  -- 'user' or 'assistant'
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            ''')
            #sql query ssaving table - save current sql query for context.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sql_query (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    sql_query TEXT NOT NULL,
                    database TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON conversation_history(session_id)
            ''')
            
            conn.commit()
    
    def create_session(self, user_id):
        session_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (session_id, user_id, state, orderid)
                VALUES (?, ?, ?, ?)
            ''', (session_id, user_id, 'INITIAL', json.dumps({})))
        
        return session_id
    
    def get_session(self, session_id):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, user_id, state, orderid, 
                       created_at, updated_at
                FROM sessions
                WHERE session_id = ?
            ''', (session_id,))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'session_id': row['session_id'],
                    'user_id': row['user_id'],
                    'state': row['state'],
                    'orderid': row['orderid'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            return None
    
    def update_state(self, session_id, new_state):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions
                SET state = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            ''', (new_state, session_id))
        
    def update_orderid(self, session_id, orderid):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions
                SET orderid = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            ''', (orderid, session_id))


# when the sql is generATED will update to this for context
    def update_sql(self, session_id, sql_query):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sql_query
                SET sql_query = ?
                WHERE session_id = ?
            ''', (sql_query, session_id))

# the data that is accessed using the sql query goes inside
    def update_database(self, session_id, data):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sql_query
                SET database = ?
                WHERE session_id = ?
            ''', (data, session_id))
    
    def store_data(self, session_id, key, value):
        session = self.get_session(session_id)
        if session:
            collected_data = session['collected_data']
            collected_data[key] = value
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions
                    SET collected_data = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (json.dumps(collected_data), session_id))
    
    def add_to_history(self, session_id, role, message):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversation_history (session_id, role, message)
                VALUES (?, ?, ?)
            ''', (session_id, role, message))
    
    def get_conversation_history(self, session_id, limit=50):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT role, message, timestamp
                FROM conversation_history
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (session_id, limit))
            
            rows = cursor.fetchall()
            return [
                {
                    'role': row['role'],
                    'message': row['message']
                }
                for row in rows
            ]
    
    def reset_session(self, session_id):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions
                SET state = 'INITIAL', 
                    orderid = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            ''', (json.dumps({}), session_id))
    
    def delete_session(self, session_id):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Delete conversation history
            cursor.execute('''
                DELETE FROM conversation_history
                WHERE session_id = ?
            ''', (session_id,))
            
            # Delete session
            cursor.execute('''
                DELETE FROM sessions
                WHERE session_id = ?
            ''', (session_id,))
    
    def get_all_sessions_for_user(self, user_id):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, state, created_at, updated_at
                FROM sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
            ''', (user_id,))
            
            rows = cursor.fetchall()
            return [
                {
                    'session_id': row['session_id'],
                    'state': row['state'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                for row in rows
            ]
    
    def cleanup_old_sessions(self, days=30):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM conversation_history
                WHERE session_id IN (
                    SELECT session_id FROM sessions
                    WHERE datetime(updated_at) < datetime('now', '-' || ? || ' days')
                )
            ''', (days,))
            
            cursor.execute('''
                DELETE FROM sessions
                WHERE datetime(updated_at) < datetime('now', '-' || ? || ' days')
            ''', (days,))
            
            deleted = cursor.rowcount
            return deleted

# Global session manager instance
session_manager = SessionManager(db_path='storage/sessions.db')
