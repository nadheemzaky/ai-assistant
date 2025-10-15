
import logging


def generate_openrouter_reply(prompt, client):
    try:
        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",  # pick model via OpenRouter
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Leajlak's customer service assistant (Leajlak's Order Management System connects merchants "
                        "and third-party logistics companies for on-demand express and scheduled deliveries, leveraging AI, IoT, "
                        "and Big Data to boost efficiency, cut costs, and improve customer satisfaction). "
                        "Check the user's message and send appropriate replies that are always inside the above context."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=1.0,
        )
        reply = response.choices[0].message.content.strip()
        return reply
    except Exception as e:
        logging.error(f"OpenRouter API error: {e}")
        return "Sorry, something went wrong while generating the reply."




def generate_sql_with_openrouter(prompt, client, system):
    try:
        sql_prompt = system
        logging.info('Started SQL generation')

        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": sql_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature= 0,
        )

        # Access response correctly
        sql_query = response.choices[0].message.content

 
        return sql_query

    except Exception as e:
        logging.error(f"OpenRouter API error: {str(e)}")
        raise



def generate_response(context, prompt_analysis, client, system_prompt):
    """Generate complete response without streaming."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role":"system","content": context},
        {"role": "user", "content": prompt_analysis}
    ]
    
    response = client.chat.completions.create(
        model="anthropic/claude-3.5-sonnet",
        messages=messages,
        stream=False # No streaming
    )
    
    return response.choices[0].message.content
