import logging

OPENROUTER_API_URL = "https://openrouter.ai/api/endpoint"  # Replace with actual endpoint
OPENROUTER_API_KEY = "your_api_key_here"                   # Set your API key securely


def call_openrouter(user_message,system,context, client,model="openai/gpt-3.5-turbo",max_tokens=300,temperature=1.0):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system","content": system},
                {"role": "system","content": context},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        reply = response.choices[0].message.content.strip()
        return reply
    except Exception as e:
        logging.error(f"OpenRouter API error: {e}")
        return "Sorry, something went wrong while generating the reply."
