import sqlite3
import uuid
import json
from datetime import datetime
from contextlib import contextmanager
import logging
import os

logging.basicConfig(level=logging.INFO)

# Custom exception for this file
class DatabaseOperationError(Exception):
    """Raised when a database operation fails"""
    pass


class SessionManager:    
    def __init__(self, db_path='storage/sessions.db'):
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.db_path = db_path
            self.create_tables()
        except Exception as e:
            logging.error(f"[INIT ERROR] Failed to initialize SessionManager: {e}")
            raise DatabaseOperationError("Initialization failed") from e
    
    @contextmanager
    def get_db_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            logging.error(f"[DB ERROR] Transaction failed: {e}")
            if conn:
                conn.rollback()
            raise DatabaseOperationError("Database transaction failed") from e
        finally:
            if conn:
                conn.close()
    
    def create_tables(self):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        state TEXT DEFAULT 'INITIAL',
                        orderid TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    )
                ''')

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

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_onboard (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL UNIQUE,
                        name TEXT,
                        mobile INTEGER,
                        email TEXT,
                        password TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS lead_gen (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL UNIQUE,
                        name TEXT,
                        mobile INTEGER,
                        email TEXT,
                        brand TEXT,
                        sector TEXT,
                        branches INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    )
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_session_id 
                    ON conversation_history(session_id)
                ''')

            logging.info("Tables ready.")
        except Exception as e:
            logging.error(f"[DB ERROR] Table creation failed: {e}")
            raise DatabaseOperationError("Failed creating database tables") from e
    
    def create_session(self, user_id, session_id=None):
        try:
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sessions (session_id, user_id, state, orderid)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, user_id, 'INITIAL', json.dumps({})))
                cursor.execute('''
                    INSERT INTO user_onboard (session_id)
                    VALUES (?)
                ''', (session_id,))
            return session_id
        except Exception as e:
            logging.error(f"[DB ERROR] create_session failed: {e}")
            raise DatabaseOperationError("Failed creating session") from e
    
    def get_session(self, session_id):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT session_id, user_id, state, orderid, created_at, updated_at
                    FROM sessions WHERE session_id = ?
                ''', (session_id,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logging.error(f"[DB ERROR] get_session failed: {e}")
            raise DatabaseOperationError("Failed retrieving session") from e
    
    def update_state(self, session_id, new_state):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions SET state=?, updated_at=CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (new_state, session_id))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] update_state failed: {e}")
            raise DatabaseOperationError("Failed updating state") from e
        
    def update_orderid(self, session_id, orderid):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions SET orderid=?, updated_at=CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (orderid, session_id))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] update_orderid failed: {e}")
            raise DatabaseOperationError("Failed updating orderid") from e
#----------------------------------------------------------
# updateing value for lead generation

    def update_value(self, session_id, item, value):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()

                # whitelist of allowed columns based on your schema
                allowed_columns = {"name", "mobile", "email", "brand", "sector", "branches"}

                if item not in allowed_columns:
                    raise ValueError(f"Invalid column name: {item}")

                # dynamically insert column name, safely bind values
                query = f"UPDATE lead_gen SET {item} = ? WHERE session_id = ?"
                cursor.execute(query, (value, session_id))
                conn.commit()

            return True

        except Exception as e:
            logging.error(f"[DB ERROR] update_value failed: {e}")
            raise DatabaseOperationError("Failed updating value") from e

#----------------------------------------------------------
    def update_name(self, session_id, name):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_onboard SET name=? WHERE session_id=?
                ''', (name, session_id))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] update_name failed: {e}")
            raise DatabaseOperationError("Failed updating name") from e

    def update_mobile(self, session_id, mobile):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_onboard SET mobile=? WHERE session_id=?
                ''', (mobile, session_id))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] update_mobile failed: {e}")
            raise DatabaseOperationError("Failed updating mobile") from e

    def update_email(self, session_id, email):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_onboard SET email=? WHERE session_id=?
                ''', (email, session_id))
            logging.info("Email updated successfully")
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] update_email failed: {e}")
            raise DatabaseOperationError("Failed updating email") from e

    def update_password(self, session_id, password):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_onboard SET password=? WHERE session_id=?
                ''', (password, session_id))
                conn.commit()  # 🔥 Force save to DB

            logging.info(f"Password updated for session_id={session_id}")
            return True

        except Exception as e:
            logging.error(f"[DB ERROR] update_password failed: {e}")
            raise DatabaseOperationError("Failed updating password") from e

    def get_onboard_data(self, session_id):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT session_id, name, mobile, email, password
                    FROM user_onboard WHERE session_id = ?
                ''', (session_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logging.error(f"[DB ERROR] get_onboard_data failed: {e}")
            raise DatabaseOperationError("Failed retrieving onboard data") from e

    def update_sql(self, session_id, sql_query):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sql_query SET sql_query=? WHERE session_id=?
                ''', (sql_query, session_id))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] update_sql failed: {e}")
            raise DatabaseOperationError("Failed updating SQL context") from e

    def update_database(self, session_id, data):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sql_query SET database=? WHERE session_id=?
                ''', (data, session_id))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] update_database failed: {e}")
            raise DatabaseOperationError("Failed updating SQL data") from e
    
    def store_data(self, session_id, key, value):
        try:
            session = self.get_session(session_id)
            if not session:
                return False

            collected_data = json.loads(session.get('orderid', '{}'))
            collected_data[key] = value

            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions SET orderid=?, updated_at=CURRENT_TIMESTAMP
                    WHERE session_id=?
                ''', (json.dumps(collected_data), session_id))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] store_data failed: {e}")
            raise DatabaseOperationError("Failed storing session data") from e
    
    def add_to_history(self, session_id, role, message):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversation_history (session_id, role, message)
                    VALUES (?, ?, ?)
                ''', (session_id, role, message))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] add_to_history failed: {e}")
            raise DatabaseOperationError("Failed adding conversation history") from e
    
    def get_conversation_history(self, session_id, limit=50):
        try:
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
                return [{'role': r['role'], 'message': r['message']} for r in rows]
        except Exception as e:
            logging.error(f"[DB ERROR] get_conversation_history failed: {e}")
            raise DatabaseOperationError("Failed fetching chat history") from e
    
    def reset_session(self, session_id):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions
                    SET state='INITIAL', orderid=?, updated_at=CURRENT_TIMESTAMP
                    WHERE session_id=?
                ''', (json.dumps({}), session_id))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] reset_session failed: {e}")
            raise DatabaseOperationError("Failed resetting session") from e
    
    def delete_session(self, session_id):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM conversation_history WHERE session_id=?', (session_id,))
                cursor.execute('DELETE FROM sessions WHERE session_id=?', (session_id,))
            return True
        except Exception as e:
            logging.error(f"[DB ERROR] delete_session failed: {e}")
            raise DatabaseOperationError("Failed deleting session") from e
    
    def get_all_sessions_for_user(self, user_id):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT session_id, state, created_at, updated_at
                    FROM sessions
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                ''', (user_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"[DB ERROR] get_all_sessions_for_user failed: {e}")
            raise DatabaseOperationError("Failed retrieving sessions for user") from e
    
    def cleanup_old_sessions(self, days=30):
        try:
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
                
                return cursor.rowcount
        except Exception as e:
            logging.error(f"[DB ERROR] cleanup_old_sessions failed: {e}")
            raise DatabaseOperationError("Failed cleaning up sessions") from e


# Global instance
session_manager = SessionManager(db_path='storage/sessions.db')

