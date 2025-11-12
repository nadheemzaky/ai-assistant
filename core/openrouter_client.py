import logging
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load .env file from the project root
load_dotenv()

client2 = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def call_openrouter(session_id,user_message,system,context,model="openai/gpt-3.5-turbo",max_tokens=300,temperature=1.0):
    try:
        response = client2.chat.completions.create(
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
        return {
            "reply": reply,
            "session_id": session_id  # kept internally
        }
    except Exception as e:
        logging.error(f"OpenRouter API error: {e}")
        return "Sorry, something went wrong while generating the reply."
