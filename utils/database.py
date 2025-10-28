
import logging
import psycopg2
from datetime import datetime, timedelta, date,time
from decimal import Decimal
import json
from datetime import datetime

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