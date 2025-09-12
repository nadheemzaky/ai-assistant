import prompts
import logging
import time as time_module




def generate_sql_with_openai(prompt,client):
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



def generate_streaming_response(prompt_analysis, client2, prompts, wpm=350):
    """
    Generate streaming response for analysis
    """
    try:
        summary_prompt = prompts.summary_prompt
        logging.info('Started summary generation')
        
        response = client2.chat.completions.create(
            model="deepseek/deepseek-chat-v3.1:free",
            stream=True,
            messages=[
                {
                    "role": "system",
                    "content": summary_prompt
                },
                {
                    "role": "user",
                    "content": prompt_analysis
                },
            ]
        ) 
        
        for chunk in response:
            delta = chunk.choices[0].delta  
            logging.info(f'delta: {delta.__dict__}')
            
            if hasattr(delta, 'content') and delta.content:
                try:
                    yield delta.content.encode('utf-8')
                    char_count = len(delta.content)
                    delay = (char_count * 30.0) / (wpm * 5)
                    time_module.sleep(delay)
                except Exception as e:
                    logging.error(f'Streaming error: {str(e)}')
                    
    except Exception as e:
        logging.error(f'Response creation failed: {str(e)}')
        yield f"Error: {str(e)}".encode('utf-8')
