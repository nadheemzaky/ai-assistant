from flask import jsonify
from core.openrouter_client import call_openrouter
from datetime import datetime
import logging
from flask import jsonify
from core import audit_logger
from core import database
import uuid
from core import prompts
import os
from core.session_manager import session_manager
from dotenv import load_dotenv

load_dotenv()

model="openai/gpt-3.5-turbo"
max_tokens=300
temperature=1.0

#sql params
system=prompts.sql_prompt
system2=prompts.summary_prompt
now = datetime.now()
name="MC DONALDS"

#db params
DB_URL = os.getenv('DB_URL')


def data_fetch_route(session_id,usermessage,context):


#/////Generate SQL query//////
    sql_context=f'''
    name = {name}
    user message = {usermessage}
    date and time now = {now}
    context: {context}
    '''
    try:
        sql_query=call_openrouter(session_id,usermessage,system,sql_context,model,max_tokens,temperature)["reply"]
        logging.info(f'SQL generation success: {sql_query}')
        try:
            audit_logger.append_sql_async([sql_query])
            session_manager.update_sql(session_id,sql_query)
        except Exception as e:
            logging.error(f'Error saving SQL to Excel: {e}')
        if not sql_query:
            logging.error('No SQL query generated')
            return jsonify({"reply": "Failed to generate query"}), 500
    except Exception as e:
        logging.error(f'Error generating SQL: {e}')
        return jsonify({"reply": "Failed to generate query"}), 500

#//////Database Comms////////
    db_data_json, success = database.execute_query_and_get_json(DB_URL, sql_query)
    if success:
        if not db_data_json or db_data_json.strip() == "[]":
            response = call_openrouter(session_id,usermessage, prompts.nodata_prompt, context)
            logging.warning('Query executed successfully but returned no results')
            return response
        else:
            session_manager.update_database(session_id, db_data_json)
            logging.info('Database query executed successfully')
    else:
        logging.error('Database query execution failed')
        db_data_json = 'Database execution error.'  # Ensure it's None for response generation

#//////generate response///////
    try:
        summary_context=f'''
        the data that is related to the question of user= {db_data_json}.
        the sql query that is generated right now to fetch data from database = {sql_query}.
        current time = {now}
        '''
        response=call_openrouter(session_id,usermessage,system2,summary_context,model,max_tokens,temperature)
        logging.info(f'{response}')    
    except Exception as e:
        logging.error(f'Error generating response: {str(e)}')
        return jsonify({"error": "Internal server error"}), 500
    
    return response

